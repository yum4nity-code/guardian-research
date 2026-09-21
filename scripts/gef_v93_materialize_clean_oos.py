from pathlib import Path
import pandas as pd
import numpy as np
import json
import hashlib
import re
import zipfile
import requests
import time
import subprocess
import shutil
from html.parser import HTMLParser

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v93_materialize"
BASE.mkdir(parents=True,exist_ok=True)

REFERER_PREFIX="https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/"
POST_URL="https://www.histdata.com/get.php"

# HistData stops exposing a free download token for some recent commodity pages.
# We do NOT silently substitute a different feed. A Dukascopy fallback is allowed
# only after a predeclared 2022 overlap bridge passes on the same instrument.
DUKA_INSTRUMENT={"WTIUSD":"lightcmdusd"}
DUKA_BRIDGE_RULE={
    "reference_year":2022,
    "min_overlap_5m_rows":20000,
    "min_return_corr_each_horizon":0.97,
    "max_median_abs_return_diff_bp_each_horizon":3.0,
    "min_sign_agreement_each_horizon":0.80,
    "horizons_min":[5,15,60,240],
}
DUKA_DIR=ROOT/"DataLake"/"raw"/"dukascopy_bridge"
_DUKA_BRIDGE_CACHE={}

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

class TokenMissingError(RuntimeError):
    pass

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
                raise TokenMissingError(
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
        except TokenMissingError:
            raise
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

def download_month(session,pair,year,month,zip_path,max_attempts=4):
    referer=f"{REFERER_PREFIX}{pair.lower()}/{year}/{int(month)}"
    last_error=None
    for attempt in range(1,max_attempts+1):
        try:
            r1=session.get(
                referer,
                headers={
                    "Cache-Control":"no-cache",
                    "Pragma":"no-cache",
                    "Referer":"https://www.histdata.com/download-free-forex-data/",
                },
                timeout=60,
                allow_redirects=True,
            )
            r1.raise_for_status()
            token=get_token(r1.text)
            if not token:
                title=re.search(r"<title[^>]*>(.*?)</title>",r1.text,re.I|re.S)
                title=re.sub(r"\s+"," ",title.group(1)).strip() if title else "NO_TITLE"
                raise TokenMissingError(
                    f"monthly token missing {pair} {year}-{month:02d} "
                    f"status={r1.status_code} bytes={len(r1.content)} title={title!r}"
                )
            data={
                "tk":token,
                "date":str(year),
                "datemonth":f"{year}{int(month):02d}",
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
                raise RuntimeError(
                    f"monthly non-ZIP/too-small payload {pair} {year}-{month:02d} "
                    f"bytes={len(body)} head={head!r}"
                )
            zip_path.parent.mkdir(parents=True,exist_ok=True)
            zip_path.write_bytes(body)
            with zipfile.ZipFile(zip_path,"r") as zf:
                bad=zf.testzip()
                if bad:
                    raise RuntimeError(f"monthly corrupt ZIP member {bad}")
            return {
                "referer":referer,
                "bytes":len(body),
                "zip_sha256":sha256(zip_path),
                "content_disposition":r.headers.get("Content-Disposition"),
                "attempts":attempt,
                "month":int(month),
            }
        except TokenMissingError:
            raise
        except Exception as e:
            last_error=repr(e)
            if attempt>=max_attempts:
                break
            delay=min(12,2**attempt)
            print(
                f"[GEF93M] {pair} {year}-{month:02d}: attempt {attempt}/{max_attempts} "
                f"failed ({last_error}); retry in {delay}s",
                flush=True,
            )
            time.sleep(delay)
            session.cookies.clear()
    raise RuntimeError(
        f"HistData monthly download failed for {pair} {year}-{month:02d} "
        f"after {max_attempts} attempts: {last_error}"
    )

def _find_npx():
    return shutil.which("npx.cmd") or shutil.which("npx")

def download_dukascopy_m1(pair,year):
    instrument=DUKA_INSTRUMENT.get(pair)
    if not instrument:
        raise RuntimeError(f"No predeclared Dukascopy bridge instrument for {pair}")
    npx=_find_npx()
    if not npx:
        raise RuntimeError("npx not found; cannot use validated Dukascopy bridge")
    outdir=DUKA_DIR/pair
    outdir.mkdir(parents=True,exist_ok=True)
    stem=f"{pair}_DUKA_M1_{year}"
    # Reuse a previously completed raw CSV.
    existing=sorted(outdir.glob(stem+"*.csv"))
    if existing:
        csv_path=existing[-1]
    else:
        cmd=[
            npx,"--yes","dukascopy-node",
            "-i",instrument,
            "-from",f"{year}-01-01",
            "-to",f"{year+1}-01-01",
            "-t","m1",
            "-p","bid",
            "-f","csv",
            "-utc","0",
            "-dir",str(outdir),
            "-fn",stem,
            "-r","3",
            "-rp","1000",
            "-s",
        ]
        print(f"[GEF93M] {pair} {year}: Dukascopy fallback download starting",flush=True)
        proc=subprocess.run(cmd,capture_output=True,text=True,timeout=1200)
        if proc.returncode!=0:
            raise RuntimeError(
                f"Dukascopy CLI failed {pair} {year} rc={proc.returncode} "
                f"stdout={proc.stdout[-800:]!r} stderr={proc.stderr[-800:]!r}"
            )
        existing=sorted(outdir.glob(stem+"*.csv"))
        if not existing:
            raise RuntimeError(
                f"Dukascopy CLI returned success but no CSV matching {stem}*.csv in {outdir}"
            )
        csv_path=existing[-1]

    d=pd.read_csv(csv_path)
    required={"timestamp","open","high","low","close"}
    if not required.issubset(d.columns):
        raise RuntimeError(f"Dukascopy CSV schema missing {required-set(d.columns)} in {csv_path}")
    ts=pd.to_datetime(pd.to_numeric(d["timestamp"],errors="coerce"),unit="ms",utc=True,errors="coerce")
    out=pd.DataFrame({
        "datetime_utc":ts.dt.tz_convert(None),
        "open":pd.to_numeric(d["open"],errors="coerce"),
        "high":pd.to_numeric(d["high"],errors="coerce"),
        "low":pd.to_numeric(d["low"],errors="coerce"),
        "close":pd.to_numeric(d["close"],errors="coerce"),
        "volume":pd.to_numeric(d["volume"],errors="coerce") if "volume" in d.columns else 0.0,
    }).dropna(subset=["datetime_utc","open","high","low","close"])
    out=out[out["datetime_utc"].dt.year==int(year)].copy()
    out=out.sort_values("datetime_utc").drop_duplicates("datetime_utc",keep="last").reset_index(drop=True)
    if len(out)<100000:
        raise RuntimeError(f"Dukascopy {pair} {year}: implausibly few M1 rows {len(out)}")
    return out,csv_path,instrument

def validate_dukascopy_bridge(pair):
    if pair in _DUKA_BRIDGE_CACHE:
        return _DUKA_BRIDGE_CACHE[pair]

    ref_year=int(DUKA_BRIDGE_RULE["reference_year"])
    hist_path=ROOT/"DataLake"/"raw"/"histdata"/pair/"M1"/f"{pair}_M1_{ref_year}.parquet"
    if not hist_path.exists():
        raise RuntimeError(f"Dukascopy bridge reference missing {hist_path}")

    h=pd.read_parquet(hist_path)
    hdc=next((x for x in h.columns if str(x).lower() in ["datetime","timestamp","time","date"]),None)
    hcc=next((x for x in h.columns if str(x).lower()=="close"),None)
    if hdc is None or hcc is None:
        raise RuntimeError(f"Cannot parse bridge reference {hist_path}")
    hist=pd.DataFrame({
        "utc":pd.to_datetime(h[hdc],errors="coerce")+pd.Timedelta(hours=5),
        "close":pd.to_numeric(h[hcc],errors="coerce"),
    }).dropna().drop_duplicates("utc",keep="last").set_index("utc").sort_index()

    duka,csv_path,instrument=download_dukascopy_m1(pair,ref_year)
    duk=duka.set_index("datetime_utc")["close"].sort_index()

    # Reproduce research-engine 5m bar construction for both sources.
    h5=hist["close"].resample("5min",label="right",closed="left").last()
    d5=duk.resample("5min",label="right",closed="left").last()
    z=pd.concat([h5.rename("hist"),d5.rename("duka")],axis=1,join="inner").dropna()
    if len(z)<int(DUKA_BRIDGE_RULE["min_overlap_5m_rows"]):
        raise RuntimeError(f"{pair} Dukascopy bridge overlap too small: {len(z)}")

    checks=[]
    passed=True
    for mins in DUKA_BRIDGE_RULE["horizons_min"]:
        k=int(mins)//5
        rh=z["hist"]/z["hist"].shift(k)-1.0
        rd=z["duka"]/z["duka"].shift(k)-1.0
        q=pd.concat([rh.rename("hist"),rd.rename("duka")],axis=1).dropna()
        corr=float(q["hist"].corr(q["duka"])) if len(q)>2 else np.nan
        mad_bp=float(np.median(np.abs(q["hist"]-q["duka"]))*1e4) if len(q) else np.nan
        nz=(np.abs(q["hist"])>1e-12)|(np.abs(q["duka"])>1e-12)
        sign=float((np.sign(q.loc[nz,"hist"])==np.sign(q.loc[nz,"duka"])).mean()) if nz.any() else np.nan
        ok=bool(
            np.isfinite(corr)
            and corr>=DUKA_BRIDGE_RULE["min_return_corr_each_horizon"]
            and np.isfinite(mad_bp)
            and mad_bp<=DUKA_BRIDGE_RULE["max_median_abs_return_diff_bp_each_horizon"]
            and np.isfinite(sign)
            and sign>=DUKA_BRIDGE_RULE["min_sign_agreement_each_horizon"]
        )
        passed=passed and ok
        checks.append({
            "horizon_min":int(mins),
            "n":int(len(q)),
            "return_corr":corr,
            "median_abs_return_diff_bp":mad_bp,
            "sign_agreement":sign,
            "pass":ok,
        })

    receipt={
        "pair":pair,
        "reference_year":ref_year,
        "histdata_reference":str(hist_path),
        "dukascopy_reference_csv":str(csv_path),
        "dukascopy_instrument":instrument,
        "overlap_5m_rows":int(len(z)),
        "rule":DUKA_BRIDGE_RULE,
        "checks":checks,
        "pass":bool(passed),
    }
    bridge_path=BASE/f"DUKASCOPY_BRIDGE_{pair}_{ref_year}.json"
    write_json(bridge_path,receipt)
    if not passed:
        raise RuntimeError(
            f"{pair} Dukascopy bridge FAILED predeclared overlap rule; "
            f"refusing mixed-source OOS. See {bridge_path}"
        )
    print(
        f"[GEF93M] {pair}: Dukascopy bridge PASSED on {ref_year} "
        f"({len(z)} aligned 5m rows)",
        flush=True,
    )
    _DUKA_BRIDGE_CACHE[pair]=receipt
    return receipt

def load_dukascopy_year_after_bridge(pair,year):
    bridge=validate_dukascopy_bridge(pair)
    d,csv_path,instrument=download_dukascopy_m1(pair,year)
    # V93 loader expects the historical HistData convention: stored source time
    # is fixed UTC-5 and then +5h is applied. Store an equivalent fixed-UTC-5
    # timestamp so downstream time semantics remain unchanged.
    out=pd.DataFrame({
        "datetime":d["datetime_utc"]-pd.Timedelta(hours=5),
        "open":d["open"].to_numpy(dtype=np.float64),
        "high":d["high"].to_numpy(dtype=np.float64),
        "low":d["low"].to_numpy(dtype=np.float64),
        "close":d["close"].to_numpy(dtype=np.float64),
        "volume":pd.to_numeric(d["volume"],errors="coerce").fillna(0).to_numpy(dtype=np.float64),
    })
    return out,{
        "mode":"dukascopy_bridge_validated",
        "referers":["https://www.dukascopy.com/api/data/get/historical-data-export"],
        "zip_paths":[str(csv_path)],
        "zip_sha256":[sha256(csv_path)],
        "members":[csv_path.name],
        "attempts":1,
        "dukascopy_instrument":instrument,
        "bridge":bridge,
    }


def parse_zip(zip_path,pair,year,month=None,min_rows=100000):
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
    if month is not None:
        d=d[d["datetime"].dt.month==int(month)].copy()
    d=d.sort_values("datetime").drop_duplicates("datetime",keep="last").reset_index(drop=True)
    if len(d)<int(min_rows):
        suffix=f"-{int(month):02d}" if month is not None else ""
        raise RuntimeError(
            f"{pair} {year}{suffix}: implausibly few M1 rows {len(d)} of raw {raw_rows}"
        )
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

def load_histdata_year_with_fallback(session,pair,year):
    annual_zip=ROOT/"DataLake"/"raw"/"histdata"/"_downloads"/pair/f"HISTDATA_COM_ASCII_{pair}_M1{year}.zip"
    try:
        meta=download_year(session,pair,year,annual_zip,max_attempts=3)
        d,member=parse_zip(annual_zip,pair,year)
        return d,{
            "mode":"annual",
            "referers":[meta["referer"]],
            "zip_paths":[str(annual_zip)],
            "zip_sha256":[meta["zip_sha256"]],
            "members":[member],
            "attempts":meta.get("attempts",1),
        }
    except TokenMissingError:
        print(
            f"[GEF93M] {pair} {year}: annual page has no token; trying monthly HistData",
            flush=True,
        )

    parts=[]
    referers=[]
    zip_paths=[]
    zip_hashes=[]
    members=[]
    attempts=0
    try:
        for month in range(1,13):
            zp=ROOT/"DataLake"/"raw"/"histdata"/"_downloads"/pair/f"HISTDATA_COM_ASCII_{pair}_M1{year}{month:02d}.zip"
            mm=download_month(session,pair,year,month,zp,max_attempts=2)
            dm,member=parse_zip(zp,pair,year,month=month,min_rows=1000)
            parts.append(dm)
            referers.append(mm["referer"])
            zip_paths.append(str(zp))
            zip_hashes.append(mm["zip_sha256"])
            members.append(member)
            attempts+=int(mm.get("attempts",1))
            print(
                f"[GEF93M] {pair} {year}: monthly fallback {month}/12 rows={len(dm)}",
                flush=True,
            )
    except TokenMissingError as e:
        # Do not keep hammering an alternate source after a 429. Preserve the frozen panel,
        # mark this market-year unavailable, and let V93 score only hypotheses whose
        # complete original-source OOS data are present.
        raise RuntimeError(
            f"SOURCE_UNAVAILABLE {pair} {year}: HistData annual and monthly token unavailable; {e}"
        )

    d=pd.concat(parts,ignore_index=True).sort_values("datetime").drop_duplicates("datetime",keep="last").reset_index(drop=True)
    if len(d)<100000:
        raise RuntimeError(f"{pair} {year}: monthly fallback produced only {len(d)} M1 rows")
    if d["datetime"].dt.year.nunique()!=1 or int(d["datetime"].dt.year.iloc[0])!=int(year):
        raise RuntimeError(f"{pair} {year}: monthly fallback year integrity failed")
    return d,{
        "mode":"monthly_fallback",
        "referers":referers,
        "zip_paths":zip_paths,
        "zip_sha256":zip_hashes,
        "members":members,
        "attempts":attempts,
    }


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
unresolved=[]
t0=time.time()
for idx,target in enumerate(missing,1):
    m=re.fullmatch(r"([A-Z]+)_M1_(2023|2024|2025)\.parquet",target.name)
    pair=m.group(1); year=int(m.group(2))
    try:
        d,meta=load_histdata_year_with_fallback(session,pair,year)
        med=float(d["close"].median())
        ratio=med/ref_median[pair] if ref_median[pair] else np.nan
        if not np.isfinite(ratio) or ratio<0.20 or ratio>5.0:
            raise RuntimeError(
                f"{pair} {year}: price-scale continuity failed median={med} "
                f"ref={ref_median[pair]} ratio={ratio}"
            )
        target.parent.mkdir(parents=True,exist_ok=True)
        tmp=target.with_suffix(".parquet.tmp")
        d.to_parquet(tmp,index=False)
        chk=pd.read_parquet(tmp)
        if len(chk)!=len(d):
            raise RuntimeError(f"{pair} {year}: parquet roundtrip row mismatch")
        tmp.replace(target)
        rec={
            "pair":pair,"year":year,"rows":len(d),
            "first_source_est":str(d["datetime"].iloc[0]),
            "last_source_est":str(d["datetime"].iloc[-1]),
            "median_close":med,
            "continuity_ratio_vs_2022_median":ratio,
            "download_mode":meta["mode"],
            "zip_members":meta["members"],
            "zip_sha256":meta["zip_sha256"],
            "download_attempts":meta.get("attempts",1),
            "parquet_sha256":sha256(target),
            "parquet":str(target),
            "source_referers":meta["referers"],
            "raw_time_semantics":(
                "Dukascopy UTC converted to equivalent fixed UTC-5 storage so V93 +5h loader reproduces UTC"
                if meta["mode"]=="dukascopy_bridge_validated"
                else "HistData source EST UTC-5 fixed; research engine converts +5h exactly as older files"
            ),
            "source_bridge":meta.get("bridge")
        }
        records.append(rec)
        ref_median[pair]=med
        print(f"[GEF93M] file {idx}/{len(missing)} {pair} {year} rows={len(d)} MATERIALIZED",flush=True)
    except Exception as e:
        unresolved.append({"pair":pair,"year":year,"path":str(target),"error":repr(e)})
        print(
            f"[GEF93M] file {idx}/{len(missing)} {pair} {year} UNRESOLVED; "
            f"continuing without changing frozen panel | {repr(e)}",
            flush=True,
        )
    elapsed=time.time()-t0
    rate=idx/max(elapsed,1e-9)
    eta=(len(missing)-idx)/max(rate,1e-9)
    print(
        f"[GEF93M] progress {idx}/{len(missing)} | elapsed={elapsed/60:.1f}m eta={eta/60:.1f}m",
        flush=True,
    )

status(OUT,3,8,"materialization attempts complete; unresolved files will remain unscored",materialized=len(records),unresolved=len(unresolved))

# Structural audit only for files that exist. Missing market-years are availability metadata,
# not a reason to mutate or discard frozen hypotheses.
audit=[]
audit_missing=[]
for pair in sorted(allowed_markets):
    prev=None
    for year in (2023,2024,2025):
        p=ROOT/"DataLake"/"raw"/"histdata"/pair/"M1"/f"{pair}_M1_{year}.parquet"
        if not p.exists():
            audit_missing.append(str(p))
            continue
        d=pd.read_parquet(p)
        dc=next((x for x in d.columns if str(x).lower() in ["datetime","timestamp","time","date"]),None)
        cc=next((x for x in d.columns if str(x).lower()=="close"),None)
        if dc is None or cc is None:
            raise RuntimeError(f"Invalid schema {p}")
        tt=pd.to_datetime(d[dc],errors="coerce")
        cl=pd.to_numeric(d[cc],errors="coerce")
        if tt.isna().any() or cl.isna().all():
            raise RuntimeError(f"Invalid values {p}")
        first,last=tt.min(),tt.max()
        if prev is not None and first<=prev:
            raise RuntimeError(f"{pair} cross-year overlap at {year}")
        prev=last
        audit.append({
            "pair":pair,"year":year,"rows":len(d),
            "first":str(first),"last":str(last),
            "median_close":float(cl.median()),"sha256":sha256(p)
        })
pd.DataFrame(audit).to_csv(OUT/"CLEAN_OOS_2023_2025_DATA_AUDIT.csv",index=False)
write_json(OUT/"UNRESOLVED_OOS_FILES.json",{
    "unresolved_downloads":unresolved,
    "still_missing_files":audit_missing,
    "panel_changed":False
})
status(
    OUT,4,8,
    "available frozen-panel OOS source files audited; unavailable files preserved as unscored",
    audited_files=len(audit),still_missing=len(audit_missing)
)

receipt={
    "run_id":RID,
    "status":(
        "COMPLETE_CLEAN_OOS_MATERIALIZATION"
        if not audit_missing
        else "COMPLETE_PARTIAL_CLEAN_OOS_MATERIALIZATION"
    ),
    "source_v92":V92.name,
    "panel_sha256":freeze["panel_sha256"],
    "files_materialized_this_run":len(records),
    "unresolved_downloads":unresolved,
    "still_missing_files":audit_missing,
    "integrity_only_oos_values_accessed":True,
    "strategy_outcomes_computed":False,
    "frozen_rule_changed":False,
    "protected_2026_accessed":False,
    "next":"RUN_V93_LOCKED_OOS_AVAILABLE_HYPOTHESES"
}
write_json(OUT/"RUN_RECEIPT.json",receipt)
status(OUT,5,8,"materialization receipt written",status=receipt["status"],still_missing=len(audit_missing))
status(OUT,6,8,"V92 hypothesis panel remains byte-for-byte frozen",panel_sha256=freeze["panel_sha256"][:16])
status(OUT,7,8,"2026 remains untouched")
status(OUT,8,8,"DONE")
print("\n=== V93 MATERIALIZATION RECEIPT ==="); print(json.dumps(receipt,indent=2)); print("\nRUN:",OUT)
