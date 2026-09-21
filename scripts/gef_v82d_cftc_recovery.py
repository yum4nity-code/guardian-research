from pathlib import Path
import pandas as pd
import numpy as np
import json, zipfile, tempfile, os, time, hashlib

ROOT=Path(r"D:\MT5_Backtests")
DL=ROOT/"DataLake"
SRC=DL/"raw"/"cftc"/"futures_only_reports"
rid="GEF82D-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
O=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v82d"/rid
O.mkdir(parents=True,exist_ok=True)
t0=time.time()

def prog(i,n,msg):
    e=time.time()-t0
    eta=e/i*(n-i) if i else 0
    payload={"run_id":rid,"step":i,"steps":n,"percent":round(100*i/n,1),
             "elapsed_s":round(e,1),"eta_s":round(eta,1),"message":msg}
    (O/"LIVE_STATUS.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
    print(f"[GEF82D] {i}/{n} {100*i/n:.0f}% | elapsed {e:.1f}s | ETA {eta:.1f}s | {msg}",flush=True)

def find_col(cols, needles):
    for c in cols:
        z=str(c).strip().lower()
        if any(n in z for n in needles):
            return c
    return None

def parse_report_date(d, cols):
    # Prefer the already-decoded calendar date demonstrated by V82C.
    direct=find_col(cols,["report_date_as_mm_dd_yyyy","report date as mm dd yyyy","report_date_as_yyyy-mm-dd"])
    if direct is not None:
        out=pd.to_datetime(d[direct],errors="coerce")
        return out,direct,"DIRECT_REPORT_DATE"
    compact=find_col(cols,["as_of_date_in_form_yymmdd","as of date in form yymmdd"])
    if compact is not None:
        s=d[compact].astype("string").str.replace(r"\.0$","",regex=True).str.zfill(6)
        out=pd.to_datetime(s,format="%y%m%d",errors="coerce")
        return out,compact,"YYMMDD_ZFILL6_EXPLICIT"
    return pd.Series(pd.NaT,index=d.index),None,"UNRESOLVED"

prog(1,10,"validated CFTC recovery using V82C date evidence; zero edge search")
archives=[
    p for p in sorted(SRC.glob("*.zip"))
    if any(str(y) in p.name for y in range(2009,2014))
    and "excel" in p.name.lower()
]
if not archives:
    raise RuntimeError(f"No CFTC Excel ZIP archives found at {SRC}")
prog(2,10,f"archives={len(archives)}")

parts=[]
diag=[]
errors=[]
for j,p in enumerate(archives,1):
    try:
        with zipfile.ZipFile(p) as z:
            members=[m for m in z.namelist() if m.lower().endswith((".xls",".xlsx"))]
            for m in members:
                suffix=Path(m).suffix
                with tempfile.NamedTemporaryFile(suffix=suffix,delete=False) as tf:
                    tf.write(z.read(m)); tmp=tf.name
                try:
                    d=pd.read_excel(tmp)
                finally:
                    try: os.unlink(tmp)
                    except OSError: pass

                cols=list(d.columns)
                report_date,date_col,date_rule=parse_report_date(d,cols)
                market=find_col(cols,["market and exchange names","market_and_exchange_names"])
                oi=find_col(cols,["open interest (all)","open_interest_all"])
                ncl=find_col(cols,["noncommercial positions-long","noncomm_positions_long_all"])
                ncs=find_col(cols,["noncommercial positions-short","noncomm_positions_short_all"])
                cl=find_col(cols,["commercial positions-long","comm_positions_long_all"])
                cs=find_col(cols,["commercial positions-short","comm_positions_short_all"])

                resolved={"date":date_col,"market":market,"oi":oi,
                          "noncomm_long":ncl,"noncomm_short":ncs,
                          "comm_long":cl,"comm_short":cs}
                missing=[k for k,v in resolved.items() if v is None]
                diag.append({"archive":p.name,"member":m,"rows":len(d),"date_rule":date_rule,
                             "resolved":json.dumps(resolved),"missing":"|".join(missing),
                             "parsed_dates":int(report_date.notna().sum())})
                if missing:
                    continue

                q=pd.DataFrame({
                    "report_date":report_date,
                    "market":d[market].astype("string"),
                    "open_interest":pd.to_numeric(d[oi],errors="coerce"),
                    "noncomm_long":pd.to_numeric(d[ncl],errors="coerce"),
                    "noncomm_short":pd.to_numeric(d[ncs],errors="coerce"),
                    "comm_long":pd.to_numeric(d[cl],errors="coerce"),
                    "comm_short":pd.to_numeric(d[cs],errors="coerce"),
                    "archive":p.name,
                    "member":m
                })
                q=q[q["report_date"].notna() & q["market"].notna() & (q["open_interest"]>0)].copy()
                if q.empty:
                    continue
                q["noncomm_net_pct_oi"]=(q["noncomm_long"]-q["noncomm_short"])/q["open_interest"]
                q["commercial_net_pct_oi"]=(q["comm_long"]-q["comm_short"])/q["open_interest"]
                parts.append(q)
    except Exception as e:
        errors.append({"archive":str(p),"error":repr(e)})
    if j==1 or j==len(archives) or j%2==0:
        prog(3,10,f"read {j}/{len(archives)} archives; normalized parts={len(parts)}")

pd.DataFrame(diag).to_csv(O/"WORKBOOK_DIAGNOSTICS.csv",index=False)
if not parts:
    raise RuntimeError("No CFTC workbook produced normalized rows; inspect WORKBOOK_DIAGNOSTICS.csv")

D=pd.concat(parts,ignore_index=True)
D=D[D["report_date"].dt.year.between(2009,2013)].copy()
prog(4,10,f"raw normalized discovery/warmup rows={len(D):,}")

# Conservative availability: first Monday 00:00 UTC after the report/as-of date.
# This is intentionally later than normal Friday publication and avoids intraday/DST assumptions.
wd=D["report_date"].dt.weekday
days=(7-wd)%7
days=days.where(days>0,7)
D["AVAILABLE_AT"]=(D["report_date"].dt.normalize()+pd.to_timedelta(days,unit="D"))
if not (D["AVAILABLE_AT"]>D["report_date"]).all():
    raise RuntimeError("AVAILABLE_AT causality assertion failed")
prog(5,10,"AVAILABLE_AT = next Monday 00:00 UTC after report date")

N=D[["report_date","AVAILABLE_AT","market","noncomm_net_pct_oi","commercial_net_pct_oi","archive","member"]].copy()
N=N.sort_values(["market","report_date"]).drop_duplicates(["market","report_date"],keep="last")
if len(N)<1000:
    raise RuntimeError(f"Too few normalized CFTC rows: {len(N)}")
years=sorted(N["report_date"].dt.year.unique().tolist())
if years[0]>2009 or years[-1]<2013:
    raise RuntimeError(f"Unexpected CFTC year coverage: {years}")
prog(6,10,f"validated normalized rows={len(N):,}; years={years}; markets={N['market'].nunique()}")

outdir=DL/"normalized"/"cftc_pre2023"
outdir.mkdir(parents=True,exist_ok=True)
dest=outdir/"CFTC_FUTURES_ONLY_2009_2013_CAUSAL_V82D.parquet"
N.to_parquet(dest,index=False)
sha=hashlib.sha256(dest.read_bytes()).hexdigest()
prog(7,10,f"canonical parquet written sha={sha[:12]}")

names=sorted(N["market"].dropna().astype(str).unique())
patterns={
    "XAUUSD":["GOLD"],
    "XAGUSD":["SILVER"],
    "EURUSD":["EURO FX"],
    "GBPUSD":["BRITISH POUND"],
    "USDJPY":["JAPANESE YEN"],
    "AUDUSD":["AUSTRALIAN DOLLAR"],
    "USDCAD":["CANADIAN DOLLAR"],
    "USDCHF":["SWISS FRANC"],
    "SPXUSD":["S&P 500","E-MINI S&P"],
    "NSXUSD":["NASDAQ"],
    "WTIUSD":["CRUDE OIL, LIGHT SWEET","WTI"]
}
maps=[]
for target,pats in patterns.items():
    for name in names:
        if any(p.lower() in name.lower() for p in pats):
            maps.append({"target":target,"cftc_market_name":name})
M=pd.DataFrame(maps)
M.to_csv(O/"MARKET_MAPPING_CANDIDATES.csv",index=False)
if M.empty:
    raise RuntimeError("CFTC normalization succeeded but market mapping is empty")
prog(8,10,f"market mappings={len(M)} across targets={M['target'].nunique()}")

sample=N.groupby("market",as_index=False).agg(rows=("report_date","size"),first=("report_date","min"),last=("report_date","max"))
sample.to_csv(O/"MARKET_COVERAGE.csv",index=False)
prog(9,10,"coverage + mapping diagnostics written")

receipt={
    "run_id":rid,
    "status":"COMPLETE_CFTC_CAUSAL_RECOVERY_VALIDATED",
    "archives":len(archives),
    "normalized_rows":len(N),
    "unique_markets":int(N["market"].nunique()),
    "years":years,
    "mapping_rows":len(M),
    "mapping_targets":int(M["target"].nunique()),
    "canonical_path":str(dest),
    "sha256":sha,
    "date_rule":"prefer Report_Date_as_MM_DD_YYYY; fallback YYMMDD zero-fill 6 and explicit %y%m%d",
    "available_at_rule":"next Monday 00:00 UTC after report date, conservative",
    "edge_trials":0,
    "2014_plus_accessed":False,
    "2023_plus_accessed":False,
    "protected_2026_accessed":False,
    "errors":errors,
    "next":"V83_CORRECTED_CAUSAL_SOURCE_MATRIX_AND_5MIN_TARGET_LAYER"
}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
prog(10,10,"DONE")
print("\n=== V82D RECEIPT ===")
print(json.dumps(receipt,indent=2))
print("\n=== MAPPINGS ===")
print(M.to_string(index=False))
print("\n=== MARKET COVERAGE TOP ===")
print(sample.sort_values("rows",ascending=False).head(30).to_string(index=False))
print("\nRUN:",O)
