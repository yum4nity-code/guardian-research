from pathlib import Path
import pandas as pd
import numpy as np
import json
import hashlib
import re
import zipfile
import requests
import time
from html.parser import HTMLParser

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v93_materialize"
BASE.mkdir(parents=True,exist_ok=True)

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
    print(f"[GEF93M] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

class TokenParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.token=None
    def handle_starttag(self,tag,attrs):
        if tag.lower()!="input": return
        d={str(k).lower():v for k,v in attrs}
        if d.get("id")=="tk" and d.get("value"):
            self.token=d["value"]

def get_token(html):
    p=TokenParser(); p.feed(html)
    if p.token: return p.token
    pats=[
        r'<input[^>]*id=["\']tk["\'][^>]*value=["\']([^"\']+)["\']',
        r'<input[^>]*value=["\']([^"\']+)["\'][^>]*id=["\']tk["\']',
    ]
    for pat in pats:
        m=re.search(pat,html,re.I)
        if m: return m.group(1)
    return None

def download_year(session,pair,year,zip_path,max_attempts=6):
    referer=f"{REFERER_PREFIX}{pair.lower()}/{year}"
    last_error=None
    for attempt in range(1,max_attempts+1):
        try:
            get_headers={
                "Cache-Control":"no-cache",
                "Pragma":"no-cache",
                "Referer":"https://www.histdata.com/download-free-forex-data/",
            }
            r1=session.get(referer,headers=get_headers,timeout=60,allow_redirects=True)
            r1.raise_for_status()
            token=get_token(r1.text)
            if not token:
                title=re.search(r"<title[^>]*>(.*?)</title>",r1.text,re.I|re.S)
                title=re.sub(r"\\s+"," ",title.group(1)).strip() if title else "NO_TITLE"
                raise RuntimeError(
                    f"token missing status={r1.status_code} bytes={len(r1.content)} title={title!r}"
                )
            data={
                "tk":token,
                "date":str(year),
                "datemonth":str(year),
                "platform":"ASCII",
                "timeframe":"M1",
                "fxpair":pair,
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
                head=body[:200].decode("utf-8","replace")
                raise RuntimeError(f"non-ZIP/too-small payload bytes={len(body)} head={head!r}")
            zip_path.parent.mkdir(parents=True,exist_ok=True)
            zip_path.write_bytes(body)
            with zipfile.ZipFile(zip_path,"r") as zf:
                bad=zf.testzip()
                if bad:
                    raise RuntimeError(f"corrupt ZIP member {bad}")
            return {
                "referer":referer,
                "bytes":len(body),
                "zip_sha256":sha256(zip_path),
                "content_disposition":r.headers.get("Content-Disposition"),
                "attempts":attempt,
            }
        except Exception as e:
            last_error=repr(e)
            if attempt>=max_attempts:
                break
            delay=min(20,2**attempt)
            print(
                f"[GEF93M] {pair} {year}: attempt {attempt}/{max_attempts} failed "
                f"({last_error}); retry in {delay}s",
                flush=True,
            )
            time.sleep(delay)
            session.cookies.clear()
    raise RuntimeError(
        f"HistData download failed for {pair} {year} after {max_attempts} attempts: {last_error}"
    )

def parse_zip(zip_path,pair,year):
    with zipfile.ZipFile(zip_path,"r") as zf:
        members=[n for n in zf.namelist() if n.lower().endswith((".csv",".txt"))]
        data_members=[n for n in members if "M1" in n.upper() and not n.upper().endswith("STATUS.TXT")]
        if data_members:
            member=max(data_members,key=lambda n:zf.getinfo(n).file_size)
        else:
            candidates=[(zf.getinfo(n).file_size,n) for n in members]
            if not candidates: raise RuntimeError(f"{pair} {year}: no parseable ZIP member")
            member=max(candidates)[1]
        with zf.open(member) as fh:
            d=pd.read_csv(fh,sep=";",header=None,usecols=list(range(6)),
                          names=["datetime","open","high","low","close","volume"],
                          dtype={"datetime":"string"},engine="c")
    d["datetime"]=pd.to_datetime(d["datetime"].str.strip(),format="%Y%m%d %H%M%S",errors="coerce")
    for c in ["open","high","low","close","volume"]:
        d[c]=pd.to_numeric(d[c],errors="coerce")
    raw_rows=len(d)
    d=d.dropna(subset=["datetime","open","high","low","close"]).copy()
    d=d[d["datetime"].dt.year==int(year)].copy()
    d=d.sort_values("datetime").drop_duplicates("datetime",keep="last").reset_index(drop=True)
    if len(d)<100000:
        raise RuntimeError(f"{pair} {year}: implausibly few M1 rows {len(d)} of raw {raw_rows}")
    if d["datetime"].duplicated().any() or not d["datetime"].is_monotonic_increasing:
        raise RuntimeError(f"{pair} {year}: timestamp integrity failed")
    bad=((d["high"]<d[["open","close","low"]].max(axis=1)) |
         (d["low"]>d[["open","close","high"]].min(axis=1))).sum()
    if int(bad):
        raise RuntimeError(f"{pair} {year}: OHLC integrity failed rows={int(bad)}")
    if (d["close"]<=0).any():
        raise RuntimeError(f"{pair} {year}: nonpositive close")
    for c in ["open","high","low","close"]:
        d[c]=d[c].astype("float64")
    d["volume"]=d["volume"].fillna(0).astype("float64")
    return d,member

# ---------- load latest immutable V92 freeze ----------
runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v92").glob("GEF92-*"))
runs=[p for p in runs if (p/"RUN_RECEIPT.json").exists() and (p/"FINAL_OOS_FREEZE.json").exists()]
if not runs: raise RuntimeError("No completed V92 clean OOS freeze")
V92=runs[-1]
r92=json.loads((V92/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
freeze=json.loads((V92/"FINAL_OOS_FREEZE.json").read_text(encoding="utf-8"))
presence=json.loads((V92/"OOS_FILE_PRESENCE.json").read_text(encoding="utf-8"))
if r92.get("status")!="COMPLETE_V92_CLEAN_TEMPORAL_LADDER":
    raise RuntimeError(f"Latest V92 status {r92.get('status')}")
if r92.get("2023_plus_values_accessed") or r92.get("protected_2026_accessed"):
    raise RuntimeError("V92 OOS access assertion violated")
if freeze.get("2023_plus_values_accessed") or freeze.get("protected_2026_accessed"):
    raise RuntimeError("V92 freeze access assertion violated")
if set(freeze["contaminated_markets_excluded"])!={"EURUSD","NSXUSD","XAGUSD"}:
    raise RuntimeError("Unexpected V92 contaminated-market set")

original_missing=[Path(x) for x in presence.get("missing_files",[])]
allowed_markets=set(freeze["oos_markets"])
for p in original_missing:
    m=re.fullmatch(r"([A-Z]+)_M1_(2023|2024|2025)\.parquet",p.name)
    if not m or m.group(1) not in allowed_markets:
        raise RuntimeError(f"Unexpected missing OOS file {p}")

# Resume-safe: preserve files created by an interrupted materialization run.
missing=[p for p in original_missing if not p.exists()]
already_materialized=[p for p in original_missing if p.exists()]

RID="GEF93M-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID; OUT.mkdir(parents=True,exist_ok=False)
status(OUT,1,8,"V92 panel/freeze verified; no rule changes",source_v92=V92.name,panel_size=freeze["panel_size"],remaining_missing=len(missing),already_materialized=len(already_materialized))

if not missing:
    receipt={"run_id":RID,"status":"COMPLETE_NO_MATERIALIZATION_NEEDED","source_v92":V92.name,
             "files_materialized":0,"protected_2026_accessed":False,"next":"RUN_V93_LOCKED_OOS"}
    write_json(OUT/"RUN_RECEIPT.json",receipt)
    for step,msg in [(2,"all OOS files already present"),(3,"no downloads required"),(4,"integrity stage skipped"),
                     (5,"materialization receipt written"),(6,"V92 freeze unchanged"),(7,"2026 untouched"),(8,"DONE")]:
        status(OUT,step,8,msg)
    print("\n=== V93 MATERIALIZATION RECEIPT ==="); print(json.dumps(receipt,indent=2)); print("\nRUN:",OUT)
    raise SystemExit(0)

session=requests.Session()
session.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153 Safari/537.36",
                        "Accept-Language":"en-US,en;q=0.9"})

# 2022 medians are development data, safe to use for parsing/scale integrity.
ref_median={}
for pair in sorted({re.fullmatch(r"([A-Z]+)_M1_202[345]\.parquet",p.name).group(1) for p in missing}):
    p=ROOT/"DataLake"/"raw"/"histdata"/pair/"M1"/f"{pair}_M1_2022.parquet"
    if not p.exists(): raise RuntimeError(f"Missing 2022 continuity reference {p}")
    d=pd.read_parquet(p)
    cc=next((c for c in d.columns if str(c).lower()=="close"),None)
    if cc is None: raise RuntimeError(f"2022 reference close missing {p}")
    x=pd.to_numeric(d[cc],errors="coerce").dropna()
    if len(x)<100000: raise RuntimeError(f"2022 reference too small {pair}: {len(x)}")
    ref_median[pair]=float(x.median())
status(OUT,2,8,"2022 continuity references loaded",markets=len(ref_median))

records=[]
t0=time.time()
for idx,target in enumerate(missing,1):
    m=re.fullmatch(r"([A-Z]+)_M1_(2023|2024|2025)\.parquet",target.name)
    pair=m.group(1); year=int(m.group(2))
    zip_path=ROOT/"DataLake"/"raw"/"histdata"/"_downloads"/pair/f"HISTDATA_COM_ASCII_{pair}_M1{year}.zip"
    meta=download_year(session,pair,year,zip_path)
    d,member=parse_zip(zip_path,pair,year)
    med=float(d["close"].median())
    ratio=med/ref_median[pair] if ref_median[pair] else np.nan
    if not np.isfinite(ratio) or ratio<0.20 or ratio>5.0:
        raise RuntimeError(f"{pair} {year}: price-scale continuity failed median={med} ref={ref_median[pair]} ratio={ratio}")
    target.parent.mkdir(parents=True,exist_ok=True)
    tmp=target.with_suffix(".parquet.tmp")
    d.to_parquet(tmp,index=False)
    chk=pd.read_parquet(tmp)
    if len(chk)!=len(d): raise RuntimeError(f"{pair} {year}: parquet roundtrip row mismatch")
    tmp.replace(target)
    rec={"pair":pair,"year":year,"rows":len(d),"first_source_est":str(d["datetime"].iloc[0]),
         "last_source_est":str(d["datetime"].iloc[-1]),"median_close":med,
         "continuity_ratio_vs_2022_median":ratio,"zip_member":member,
         "zip_sha256":meta["zip_sha256"],"download_attempts":meta.get("attempts",1),"parquet_sha256":sha256(target),
         "parquet":str(target),"source_referer":meta["referer"],
         "raw_time_semantics":"HistData source EST UTC-5 fixed; research engine converts +5h exactly as older files"}
    records.append(rec)
    ref_median[pair]=med
    elapsed=time.time()-t0; rate=idx/max(elapsed,1e-9); eta=(len(missing)-idx)/max(rate,1e-9)
    print(f"[GEF93M] file {idx}/{len(missing)} {pair} {year} rows={len(d)} | elapsed={elapsed/60:.1f}m eta={eta/60:.1f}m",flush=True)

status(OUT,3,8,"all missing clean OOS files materialized",files=len(records))

# Cross-year structural audit per market. This opens OOS values only for integrity after freeze; no strategy outcomes.
audit=[]
for pair in sorted(allowed_markets):
    prev=None
    for year in (2023,2024,2025):
        p=ROOT/"DataLake"/"raw"/"histdata"/pair/"M1"/f"{pair}_M1_{year}.parquet"
        if not p.exists(): raise RuntimeError(f"Still missing {p}")
        d=pd.read_parquet(p)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        cc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None or cc is None: raise RuntimeError(f"Invalid schema {p}")
        tt=pd.to_datetime(d[dc],errors="coerce"); cl=pd.to_numeric(d[cc],errors="coerce")
        if tt.isna().any() or cl.isna().all(): raise RuntimeError(f"Invalid values {p}")
        first,last=tt.min(),tt.max()
        if prev is not None and first<=prev: raise RuntimeError(f"{pair} cross-year overlap at {year}")
        prev=last
        audit.append({"pair":pair,"year":year,"rows":len(d),"first":str(first),"last":str(last),
                      "median_close":float(cl.median()),"sha256":sha256(p)})
pd.DataFrame(audit).to_csv(OUT/"CLEAN_OOS_2023_2025_DATA_AUDIT.csv",index=False)
status(OUT,4,8,"all frozen-panel OOS source files pass structural audit",markets=len(allowed_markets),rows=sum(x["rows"] for x in audit))

receipt={"run_id":RID,"status":"COMPLETE_CLEAN_OOS_MATERIALIZATION","source_v92":V92.name,
         "panel_sha256":freeze["panel_sha256"],"files_materialized":len(records),"records":records,
         "integrity_only_oos_values_accessed":True,"strategy_outcomes_computed":False,
         "frozen_rule_changed":False,"protected_2026_accessed":False,"next":"RUN_V93_LOCKED_OOS"}
write_json(OUT/"RUN_RECEIPT.json",receipt)
status(OUT,5,8,"materialization receipt written")
status(OUT,6,8,"V92 hypothesis panel remains byte-for-byte frozen",panel_sha256=freeze["panel_sha256"][:16])
status(OUT,7,8,"2026 remains untouched")
status(OUT,8,8,"DONE")
print("\n=== V93 MATERIALIZATION RECEIPT ==="); print(json.dumps(receipt,indent=2)); print("\nRUN:",OUT)
