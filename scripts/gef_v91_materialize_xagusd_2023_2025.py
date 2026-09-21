from pathlib import Path
import pandas as pd
import numpy as np
import json
import hashlib
import re
import zipfile
import io
import requests
from html.parser import HTMLParser

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v91_materialize"
BASE.mkdir(parents=True,exist_ok=True)

PAIR="XAGUSD"
YEARS=(2023,2024,2025)
REFERER_PREFIX="https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/"
POST_URL="https://www.histdata.com/get.php"

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def status(out,step,total,msg,**extra):
    payload={"step":step,"steps":total,"percent":round(100*step/total,1),
             "timestamp_utc":pd.Timestamp.now("UTC").isoformat(),"message":msg,**extra}
    write_json(out/"LIVE_STATUS.json",payload)
    tail=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF91M] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

class TokenParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.token=None
    def handle_starttag(self,tag,attrs):
        if tag.lower()!="input":
            return
        d={str(k).lower():v for k,v in attrs}
        if d.get("id")=="tk" and d.get("value"):
            self.token=d["value"]

def get_token(html):
    p=TokenParser()
    p.feed(html)
    if p.token:
        return p.token
    # fallback for malformed HTML
    pats=[
        r'<input[^>]*id=["\']tk["\'][^>]*value=["\']([^"\']+)["\']',
        r'<input[^>]*value=["\']([^"\']+)["\'][^>]*id=["\']tk["\']',
    ]
    for pat in pats:
        m=re.search(pat,html,re.I)
        if m:
            return m.group(1)
    return None

def download_year(session,year,zip_path):
    referer=f"{REFERER_PREFIX}{PAIR.lower()}/{year}"
    print(f"[GEF91M] download {PAIR} {year} GET token",flush=True)
    r1=session.get(referer,timeout=60,allow_redirects=True)
    r1.raise_for_status()
    token=get_token(r1.text)
    if not token:
        raise RuntimeError(f"HistData token not found for {PAIR} {year}; page may have changed")
    data={
        "tk":token,
        "date":str(year),
        "datemonth":str(year),
        "platform":"ASCII",
        "timeframe":"M1",
        "fxpair":PAIR,
    }
    headers={
        "Referer":referer,
        "Origin":"https://www.histdata.com",
        "Content-Type":"application/x-www-form-urlencoded",
        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    r=session.post(POST_URL,data=data,headers=headers,timeout=180)
    r.raise_for_status()
    body=r.content
    if len(body)<1000 or not body.startswith(b"PK"):
        snippet=body[:200].decode("utf-8","replace")
        raise RuntimeError(f"HistData returned non-ZIP/too-small payload for {year}: bytes={len(body)} head={snippet!r}")
    zip_path.parent.mkdir(parents=True,exist_ok=True)
    zip_path.write_bytes(body)
    with zipfile.ZipFile(zip_path,"r") as zf:
        bad=zf.testzip()
        if bad:
            raise RuntimeError(f"Corrupt ZIP member {bad} in {zip_path}")
    return {
        "referer":referer,
        "bytes":len(body),
        "content_disposition":r.headers.get("Content-Disposition"),
        "zip_sha256":sha256(zip_path),
    }

def parse_zip(zip_path,year):
    with zipfile.ZipFile(zip_path,"r") as zf:
        members=[n for n in zf.namelist() if n.lower().endswith((".csv",".txt"))]
        # Prefer the actual ASCII data file, not status/readme text.
        data_members=[n for n in members if "M1" in n.upper() and not n.upper().endswith("STATUS.TXT")]
        if not data_members:
            # Fallback: choose the largest text-like member.
            candidates=[(zf.getinfo(n).file_size,n) for n in members]
            if not candidates:
                raise RuntimeError(f"No parseable data member in {zip_path}")
            data_member=max(candidates)[1]
        else:
            data_member=max(data_members,key=lambda n:zf.getinfo(n).file_size)

        with zf.open(data_member) as fh:
            d=pd.read_csv(
                fh,sep=";",header=None,usecols=list(range(6)),
                names=["datetime","open","high","low","close","volume"],
                dtype={"datetime":"string"},
                engine="c",
            )

    d["datetime"]=pd.to_datetime(d["datetime"].str.strip(),format="%Y%m%d %H%M%S",errors="coerce")
    for c in ["open","high","low","close","volume"]:
        d[c]=pd.to_numeric(d[c],errors="coerce")
    before=len(d)
    d=d.dropna(subset=["datetime","open","high","low","close"]).copy()
    d=d[d["datetime"].dt.year==int(year)].copy()
    d=d.sort_values("datetime").drop_duplicates("datetime",keep="last").reset_index(drop=True)
    if len(d)<100000:
        raise RuntimeError(f"{PAIR} {year}: implausibly few valid M1 rows ({len(d)}) from {before} raw")
    if not d["datetime"].is_monotonic_increasing or d["datetime"].duplicated().any():
        raise RuntimeError(f"{PAIR} {year}: timestamp integrity failed")
    bad_ohlc=((d["high"]<d[["open","close","low"]].max(axis=1)) |
              (d["low"]>d[["open","close","high"]].min(axis=1))).sum()
    if int(bad_ohlc)>0:
        raise RuntimeError(f"{PAIR} {year}: OHLC integrity failed rows={int(bad_ohlc)}")
    if (d["close"]<=0).any():
        raise RuntimeError(f"{PAIR} {year}: nonpositive close found")

    d["open"]=d["open"].astype("float64")
    d["high"]=d["high"].astype("float64")
    d["low"]=d["low"].astype("float64")
    d["close"]=d["close"].astype("float64")
    d["volume"]=d["volume"].fillna(0).astype("float64")
    return d,data_member

# Find latest STOP receipt and verify the freeze remains untouched.
v91runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v91").glob("GEF91-*"))
v91runs=[p for p in v91runs if (p/"RUN_RECEIPT.json").exists()]
if not v91runs:
    raise RuntimeError("No V91 receipt found")
STOP=v91runs[-1]
rstop=json.loads((STOP/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if rstop.get("status")!="STOP_MISSING_LOCKED_OOS_FILES":
    raise RuntimeError(f"Latest V91 is not missing-file stop: {rstop.get('status')}")
if rstop.get("2023_2025_values_accessed") or rstop.get("protected_2026_accessed"):
    raise RuntimeError("Stopped V91 unexpectedly accessed locked values")
expected_missing={
    str(ROOT/"DataLake"/"raw"/"histdata"/PAIR/"M1"/f"{PAIR}_M1_{y}.parquet")
    for y in YEARS
}
actual_missing=set(rstop.get("missing_files",[]))
if actual_missing!=expected_missing:
    raise RuntimeError(f"Unexpected V91 missing-file set: {sorted(actual_missing)}")

RID="GEF91M-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID
OUT.mkdir(parents=True,exist_ok=False)
status(OUT,1,8,"V91 missing-file stop verified; frozen OOS rule unchanged",source_v91_stop=STOP.name)

# Baseline continuity reference from 2022 only.
ref_path=ROOT/"DataLake"/"raw"/"histdata"/PAIR/"M1"/f"{PAIR}_M1_2022.parquet"
if not ref_path.exists():
    raise RuntimeError(f"Missing continuity reference {ref_path}")
ref=pd.read_parquet(ref_path)
ref_dt_col=next((c for c in ref.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
ref_close_col=next((c for c in ref.columns if str(c).lower()=="close"),None)
if ref_dt_col is None or ref_close_col is None:
    raise RuntimeError("2022 XAG parquet schema not understood")
ref_close=pd.to_numeric(ref[ref_close_col],errors="coerce").dropna()
if len(ref_close)<100000:
    raise RuntimeError("2022 XAG reference unexpectedly small")
ref_median=float(ref_close.median())
status(OUT,2,8,"2022 XAG continuity reference loaded",rows=len(ref),median_close=round(ref_median,6))

session=requests.Session()
session.headers.update({
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153 Safari/537.36",
    "Accept-Language":"en-US,en;q=0.9",
})
download_dir=ROOT/"DataLake"/"raw"/"histdata"/"_downloads"/PAIR
target_dir=ROOT/"DataLake"/"raw"/"histdata"/PAIR/"M1"
target_dir.mkdir(parents=True,exist_ok=True)
records=[]

for i,year in enumerate(YEARS,1):
    target=target_dir/f"{PAIR}_M1_{year}.parquet"
    zip_path=download_dir/f"HISTDATA_COM_ASCII_{PAIR}_M1{year}.zip"
    if target.exists():
        # Do not silently overwrite a newly materialized file.
        d=pd.read_parquet(target)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        cc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None or cc is None:
            raise RuntimeError(f"Existing target has invalid schema: {target}")
        records.append({
            "year":year,"status":"ALREADY_PRESENT","parquet":str(target),
            "rows":len(d),"parquet_sha256":sha256(target)
        })
        print(f"[GEF91M] {i}/3 {year}: already present, verified basic schema",flush=True)
        continue

    meta=download_year(session,year,zip_path)
    print(f"[GEF91M] {i}/3 {year}: downloaded {meta['bytes']/1024/1024:.1f} MiB",flush=True)
    d,member=parse_zip(zip_path,year)

    # Scale sanity relative to prior year. Silver cannot plausibly jump by 10x merely because of parsing.
    med=float(d["close"].median())
    ratio=med/ref_median if ref_median else np.nan
    if not np.isfinite(ratio) or ratio<0.25 or ratio>4.0:
        raise RuntimeError(f"{PAIR} {year}: price-scale continuity failed median={med} ref={ref_median} ratio={ratio}")

    tmp=target.with_suffix(".parquet.tmp")
    d.to_parquet(tmp,index=False)
    check=pd.read_parquet(tmp)
    if len(check)!=len(d):
        raise RuntimeError(f"{PAIR} {year}: parquet row count changed on roundtrip")
    tmp.replace(target)

    rec={
        "year":year,
        "status":"MATERIALIZED",
        "source":"HistData.com Generic ASCII M1 yearly",
        "source_referer":meta["referer"],
        "zip_path":str(zip_path),
        "zip_sha256":meta["zip_sha256"],
        "zip_member":member,
        "parquet":str(target),
        "parquet_sha256":sha256(target),
        "rows":len(d),
        "first_source_est":str(d["datetime"].iloc[0]),
        "last_source_est":str(d["datetime"].iloc[-1]),
        "median_close":med,
        "continuity_ratio_vs_2022_median":ratio,
        "raw_time_semantics":"HistData timestamps are stored as source EST (UTC-5 fixed); V91 adds +5h exactly as for older files",
    }
    records.append(rec)
    ref_median=med
    print(f"[GEF91M] {i}/3 {year}: parquet rows={len(d)} sha={rec['parquet_sha256'][:12]}",flush=True)

status(OUT,3,8,"three XAG OOS years downloaded/materialized or verified",years=len(records))

# Full local preflight identical to what V91 needs.
missing_after=[]
for year in YEARS:
    p=target_dir/f"{PAIR}_M1_{year}.parquet"
    if not p.exists():
        missing_after.append(str(p))
if missing_after:
    raise RuntimeError(f"Materialization incomplete: {missing_after}")

# Cross-year timestamp/order audit without touching any other 2023-25 market data.
audit=[]
prev_last=None
for year in YEARS:
    p=target_dir/f"{PAIR}_M1_{year}.parquet"
    d=pd.read_parquet(p)
    dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
    cc=next((c for c in d.columns if str(c).lower()=="close"),None)
    t=pd.to_datetime(d[dc],errors="coerce")
    close=pd.to_numeric(d[cc],errors="coerce")
    if t.isna().any() or close.isna().all():
        raise RuntimeError(f"{year}: audit found invalid datetime/close")
    first=t.min(); last=t.max()
    if prev_last is not None and first<=prev_last:
        raise RuntimeError(f"{year}: cross-year ordering overlap {first} <= {prev_last}")
    prev_last=last
    audit.append({"year":year,"rows":len(d),"first":str(first),"last":str(last),
                  "median_close":float(close.median()),"sha256":sha256(p)})
pd.DataFrame(audit).to_csv(OUT/"XAGUSD_2023_2025_AUDIT.csv",index=False)
status(OUT,4,8,"cross-year XAG audit passed",rows=sum(x["rows"] for x in audit))

receipt={
    "run_id":RID,
    "status":"COMPLETE_XAGUSD_2023_2025_MATERIALIZATION",
    "source_v91_stop":STOP.name,
    "pair":PAIR,
    "years":list(YEARS),
    "records":records,
    "audit":audit,
    "frozen_rule_changed":False,
    "other_2023_2025_market_values_accessed":False,
    "protected_2026_accessed":False,
    "next":"RERUN_FROZEN_V91_LOCKED_OOS_WITHOUT_PARAMETER_CHANGES",
}
write_json(OUT/"RUN_RECEIPT.json",receipt)
status(OUT,5,8,"materialization receipt written")
status(OUT,6,8,"V91 frozen rule remains unchanged")
status(OUT,7,8,"2026 remains untouched")
status(OUT,8,8,"DONE")

print("\n=== V91 MATERIALIZATION RECEIPT ===")
print(json.dumps(receipt,indent=2))
print("\nRUN:",OUT)
