param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v55_cftc_xls_schema.py"
$code=@'
from pathlib import Path
import pandas as pd,json,time,zipfile,tempfile,hashlib,re,os
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";SRC=DL/"raw"/"cftc"/"futures_only_reports";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v55";OUT.mkdir(parents=True,exist_ok=True)
t=time.time();rid="GEF55-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF55] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
files=sorted(SRC.glob("*.zip"));use=[p for p in files if any(str(y) in p.name for y in range(2009,2014)) and "excel" in p.name.lower()]
prog(1,8,f"excel archives={len(use)}")
rows=[];schemas=[];errors=[]
for j,p in enumerate(use,1):
 try:
  with zipfile.ZipFile(p) as z:
   members=[m for m in z.namelist() if m.lower().endswith((".xls",".xlsx"))]
   for m in members:
    with tempfile.NamedTemporaryFile(suffix=Path(m).suffix,delete=False) as tf:
     tf.write(z.read(m));tmp=tf.name
    try:
     d=pd.read_excel(tmp)
     schemas.append({"archive":str(p),"member":m,"rows":len(d),"columns":"|".join(map(str,d.columns))})
     d["__archive"]=p.name;d["__member"]=m;rows.append(d)
    finally:
     try: os.unlink(tmp)
     except: pass
 except Exception as e:errors.append({"archive":str(p),"error":repr(e)})
 if j==1 or j==len(use) or j%5==0: prog(1+j,8+len(use),f"read {j}/{len(use)}")
if not rows:
 (O/"ERRORS.json").write_text(json.dumps(errors,indent=2))
 raise RuntimeError("No Excel archive could be parsed; see ERRORS.json")
D=pd.concat(rows,ignore_index=True,sort=False)
pd.DataFrame(schemas).to_csv(O/"SCHEMA_INVENTORY.csv",index=False)
prog(3,8,f"parsed rows={len(D)} columns={len(D.columns)}")
# resolve columns by actual header text
cols=list(D.columns)
def first(preds):
 for c in cols:
  z=str(c).strip().lower()
  if any(p in z for p in preds): return c
 return None
date_col=first(["as of date in form yymmdd","report_date_as_yyyy-mm-dd","report date","as_of_date"])
market_col=first(["market and exchange names","market_and_exchange_names"])
oi_col=first(["open interest (all)","open_interest_all"])
nc_long=first(["noncommercial positions-long","noncomm_positions_long_all"])
nc_short=first(["noncommercial positions-short","noncomm_positions_short_all"])
comm_long=first(["commercial positions-long","comm_positions_long_all"])
comm_short=first(["commercial positions-short","comm_positions_short_all"])
resolved={"date":date_col,"market":market_col,"oi":oi_col,"noncomm_long":nc_long,"noncomm_short":nc_short,"comm_long":comm_long,"comm_short":comm_short}
missing=[k for k,v in resolved.items() if v is None]
(O/"RESOLVED_COLUMNS.json").write_text(json.dumps(resolved,indent=2))
if missing: raise RuntimeError("Missing columns: "+",".join(missing))
prog(4,8,"core schema resolved")
D[date_col]=pd.to_datetime(D[date_col],errors="coerce")
for c in [oi_col,nc_long,nc_short,comm_long,comm_short]:D[c]=pd.to_numeric(D[c],errors="coerce")
D=D[D[date_col].notna() & D[market_col].notna() & (D[oi_col]>0)].copy()
D["noncomm_net_pct_oi"]=(D[nc_long]-D[nc_short])/D[oi_col]
D["commercial_net_pct_oi"]=(D[comm_long]-D[comm_short])/D[oi_col]
weekday=D[date_col].dt.weekday;days=(7-weekday)%7;days=days.where(days>0,7)
D["AVAILABLE_AT"]=(D[date_col]+pd.to_timedelta(days,unit="D")).dt.normalize()
prog(5,8,"AVAILABLE_AT = next Monday after report date")
N=D[(D[date_col].dt.year>=2009)&(D[date_col].dt.year<=2013)][[date_col,"AVAILABLE_AT",market_col,"noncomm_net_pct_oi","commercial_net_pct_oi","__archive","__member"]].copy()
N=N.sort_values([market_col,date_col]).drop_duplicates([market_col,date_col],keep="last")
N.to_parquet(O/"CFTC_NORMALIZED_2009_2013.parquet",index=False)
nsha=hashlib.sha256((O/"CFTC_NORMALIZED_2009_2013.parquet").read_bytes()).hexdigest()
names=sorted(N[market_col].astype(str).unique())
patterns={"XAUUSD":["GOLD"],"XAGUSD":["SILVER"],"EURUSD":["EURO FX"],"GBPUSD":["BRITISH POUND"],"USDJPY":["JAPANESE YEN"],"AUDUSD":["AUSTRALIAN DOLLAR"],"USDCAD":["CANADIAN DOLLAR"],"SPXUSD":["S&P 500","E-MINI S&P"],"NSXUSD":["NASDAQ"],"WTIUSD":["CRUDE OIL, LIGHT SWEET","WTI"]}
maps=[]
for target,pats in patterns.items():
 for n in names:
  if any(p.lower() in n.lower() for p in pats):maps.append({"target":target,"cftc_market_name":n})
M=pd.DataFrame(maps);M.to_csv(O/"MARKET_MAPPING_CANDIDATES.csv",index=False)
prog(6,8,f"normalized rows={len(N)} unique_markets={N[market_col].nunique()} mappings={len(M)}")
receipt={"run_id":rid,"status":"COMPLETE_CFTC_XLS_SCHEMA_AVAILABLEAT","archives":len(use),"normalized_rows":len(N),"resolved_columns":resolved,"normalized_sha256":nsha,"target_returns_accessed":False,"replication_2014_2017_accessed":False,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":errors}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(7,8,"receipt written")
prog(8,8,"STOP")
print("\n=== V55 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== MAPPING CANDIDATES ===");print(M.to_string(index=False) if len(M) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V55 compile failed"}
Write-Host "=== GEF V55 - CFTC XLS SCHEMA + AVAILABLE_AT ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V55 failed"}
