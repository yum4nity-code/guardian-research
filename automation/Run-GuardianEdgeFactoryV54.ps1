param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v54_cftc_schema_availableat.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,hashlib,time,zipfile,io,re
from datetime import datetime,timezone,timedelta
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";SRC=DL/"raw"/"cftc"/"futures_only_reports";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v54";OUT.mkdir(parents=True,exist_ok=True)
t=time.time();rid="GEF54-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF54] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
files=sorted(SRC.glob("*.zip"));use=[p for p in files if any(str(y) in p.name for y in range(2009,2014))]
prog(1,10,f"candidate archives 2009-2013={len(use)}")
rows=[];schemas=[];errors=[]
for p in use:
 try:
  with zipfile.ZipFile(p) as z:
   members=[m for m in z.namelist() if m.lower().endswith((".txt",".csv"))]
   for m in members[:3]:
    b=z.read(m)
    txt=b.decode("latin1",errors="replace")
    d=None
    for sep in [",","\t",";"]:
     try:
      x=pd.read_csv(io.StringIO(txt),sep=sep,engine="python",low_memory=False)
      if x.shape[1]>5:d=x;break
     except:pass
    if d is None:continue
    schemas.append({"archive":str(p),"member":m,"rows":len(d),"columns":"|".join(map(str,d.columns))})
    # retain raw for selected years only; no market returns accessed
    d["__archive"]=p.name;d["__member"]=m;rows.append(d)
 except Exception as e:errors.append({"path":str(p),"error":repr(e)})
prog(2,10,f"parsed members={len(schemas)} errors={len(errors)}")
if not rows:raise RuntimeError("No parsable CFTC rows")
D=pd.concat(rows,ignore_index=True,sort=False)
pd.DataFrame(schemas).to_csv(O/"SCHEMA_INVENTORY.csv",index=False)
# Detect core columns conservatively.
cols=list(D.columns)
def pick(patterns,required=True):
 for c in cols:
  z=str(c).lower()
  if all(p in z for p in patterns):return c
 if required:raise RuntimeError("Missing column matching "+str(patterns))
 return None
date_col=next((c for c in cols if "as_of_date" in str(c).lower()),None) or next((c for c in cols if "report_date" in str(c).lower()),None) or next((c for c in cols if "date" in str(c).lower()),None)
market_col=next((c for c in cols if "market_and_exchange_names" in str(c).lower()),None) or next((c for c in cols if "market" in str(c).lower()),None)
oi_col=next((c for c in cols if "open_interest_all" in str(c).lower()),None)
nc_long=next((c for c in cols if "noncomm_positions_long_all" in str(c).lower()),None)
nc_short=next((c for c in cols if "noncomm_positions_short_all" in str(c).lower()),None)
comm_long=next((c for c in cols if "comm_positions_long_all" in str(c).lower()),None)
comm_short=next((c for c in cols if "comm_positions_short_all" in str(c).lower()),None)
required={"date":date_col,"market":market_col,"oi":oi_col,"noncomm_long":nc_long,"noncomm_short":nc_short,"comm_long":comm_long,"comm_short":comm_short}
missing=[k for k,v in required.items() if v is None]
if missing:raise RuntimeError("Missing required schema fields: "+",".join(missing))
prog(3,10,"core schema resolved")
D[date_col]=pd.to_datetime(D[date_col],errors="coerce")
for c in [oi_col,nc_long,nc_short,comm_long,comm_short]:D[c]=pd.to_numeric(D[c],errors="coerce")
D=D[D[date_col].notna() & D[market_col].notna() & (D[oi_col]>0)].copy()
D["noncomm_net_pct_oi"]=(D[nc_long]-D[nc_short])/D[oi_col]
D["commercial_net_pct_oi"]=(D[comm_long]-D[comm_short])/D[oi_col]
# Conservative AVAILABLE_AT: next Monday 00:00 UTC after report Tuesday.
# This intentionally sacrifices Friday information so normal/delayed Friday publication cannot create lookahead.
weekday=D[date_col].dt.weekday
days_to_mon=(7-weekday)%7
days_to_mon=days_to_mon.where(days_to_mon>0,7)
D["AVAILABLE_AT"]=(D[date_col]+pd.to_timedelta(days_to_mon,unit="D")).dt.normalize()
prog(4,10,"AVAILABLE_AT built conservatively: next Monday after report date")
# Market mapping audit only, based on names. No alpha selection.
names=sorted(D[market_col].astype(str).dropna().unique())
patterns={"XAUUSD":["GOLD"],"XAGUSD":["SILVER"],"EURUSD":["EURO FX","EURO FX/BRITISH"],"GBPUSD":["BRITISH POUND"],"USDJPY":["JAPANESE YEN"],"AUDUSD":["AUSTRALIAN DOLLAR"],"USDCAD":["CANADIAN DOLLAR"],"SPXUSD":["S&P 500","E-MINI S&P"],"NSXUSD":["NASDAQ","NASDAQ-100"],"WTIUSD":["CRUDE OIL, LIGHT SWEET","WTI"]}
maps=[]
for target,pats in patterns.items():
 hits=[n for n in names if any(p.lower() in n.lower() for p in pats)]
 for n in hits:maps.append({"target":target,"cftc_market_name":n})
M=pd.DataFrame(maps);M.to_csv(O/"MARKET_MAPPING_CANDIDATES.csv",index=False)
prog(5,10,f"market mapping candidates={len(M)}")
# Keep only discovery-era rows in normalized audit dataset.
N=D[(D[date_col].dt.year>=2009)&(D[date_col].dt.year<=2013)][[date_col,"AVAILABLE_AT",market_col,"noncomm_net_pct_oi","commercial_net_pct_oi","__archive","__member"]].copy()
N=N.sort_values([market_col,date_col]).drop_duplicates([market_col,date_col],keep="last")
N.to_parquet(O/"CFTC_NORMALIZED_2009_2013.parquet",index=False)
nsha=hashlib.sha256((O/"CFTC_NORMALIZED_2009_2013.parquet").read_bytes()).hexdigest();msha=hashlib.sha256((O/"MARKET_MAPPING_CANDIDATES.csv").read_bytes()).hexdigest()
prog(6,10,f"normalized discovery source rows={len(N)} sha={nsha[:12]}")
summary={"run_id":rid,"status":"COMPLETE_CFTC_SCHEMA_AVAILABLEAT","source_period":"2009-2013 only","raw_archives":len(use),"normalized_rows":len(N),"unique_markets":int(N[market_col].nunique()),"resolved_columns":required,"available_at_rule":"next Monday 00:00 UTC after report reference date (conservative, avoids Friday publication timing ambiguity)","normalized_sha256":nsha,"mapping_sha256":msha,"target_returns_accessed":False,"replication_2014_2017_accessed":False,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":errors}
(O/"RUN_RECEIPT.json").write_text(json.dumps(summary,indent=2))
prog(7,10,"receipt written")
prog(8,10,"no target returns evaluated")
prog(9,10,"2014+ target windows sealed")
prog(10,10,"STOP - inspect mapping before discovery")
print("\n=== V54 RECEIPT ===");print(json.dumps(summary,indent=2));print("\n=== MAPPING CANDIDATES ===");print(M.to_string(index=False) if len(M) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V54 compile failed"}
Write-Host "=== GEF V54 - CFTC SCHEMA + AVAILABLE_AT ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V54 failed"}
