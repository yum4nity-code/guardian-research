param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v55b_cftc_repair.py"
$code=@'
from pathlib import Path
import pandas as pd,json,time,zipfile,tempfile,hashlib,os,re
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";SRC=DL/"raw"/"cftc"/"futures_only_reports";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v55b";OUT.mkdir(parents=True,exist_ok=True)
t=time.time();rid="GEF55B-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF55B] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
files=sorted(SRC.glob("*excel*.zip"));use=[p for p in files if any(str(y) in p.name for y in range(2009,2014))]
rows=[];errors=[];prog(1,9,f"excel archives={len(use)}")
for j,p in enumerate(use,1):
 try:
  with zipfile.ZipFile(p) as z:
   for m in [x for x in z.namelist() if x.lower().endswith((".xls",".xlsx"))]:
    with tempfile.NamedTemporaryFile(suffix=Path(m).suffix,delete=False) as tf:tf.write(z.read(m));tmp=tf.name
    try:d=pd.read_excel(tmp);d=d.copy();d["__archive"]=p.name;d["__member"]=m;rows.append(d)
    finally:
     try:os.unlink(tmp)
     except:pass
 except Exception as e:errors.append({"archive":str(p),"error":repr(e)})
prog(2,9,f"parsed frames={len(rows)} errors={len(errors)}")
if not rows:raise RuntimeError("No Excel rows")
D=pd.concat(rows,ignore_index=True,sort=False);cols=list(D.columns)
def exact_or(pred):
 for c in cols:
  if pred(str(c).lower()):return c
 return None
date_col=exact_or(lambda z:"as_of_date_in_form_yymmdd" in z)
market_col=exact_or(lambda z:"market_and_exchange_names" in z)
oi_col=exact_or(lambda z:"open_interest_all" in z)
nc_long=exact_or(lambda z:z=="noncomm_positions_long_all")
nc_short=exact_or(lambda z:z=="noncomm_positions_short_all")
comm_long=exact_or(lambda z:z=="comm_positions_long_all")
comm_short=exact_or(lambda z:z=="comm_positions_short_all")
resolved={"date":date_col,"market":market_col,"oi":oi_col,"noncomm_long":nc_long,"noncomm_short":nc_short,"comm_long":comm_long,"comm_short":comm_short}
if any(v is None for v in resolved.values()):raise RuntimeError("Exact schema unresolved: "+json.dumps(resolved))
if comm_long==nc_long or comm_short==nc_short:raise RuntimeError("Commercial/noncommercial collision")
prog(3,9,"exact position columns resolved without collision")
# YYMMDD integers/strings must NOT be parsed by generic pd.to_datetime (nanoseconds).
raw=D[date_col]
def yymmdd(v):
 try:
  s=str(int(float(v))).zfill(6)
  yy=int(s[:2]);mm=int(s[2:4]);dd=int(s[4:6]);year=2000+yy if yy<70 else 1900+yy
  return pd.Timestamp(year,mm,dd)
 except:return pd.NaT
D["REPORT_DATE"]=raw.map(yymmdd)
for c in [oi_col,nc_long,nc_short,comm_long,comm_short]:D[c]=pd.to_numeric(D[c],errors="coerce")
valid=D["REPORT_DATE"].notna() & D[market_col].notna() & (D[oi_col]>0)
D=D.loc[valid].copy()
if D.empty:raise RuntimeError("Zero valid rows after corrected YYMMDD parsing")
yr=(int(D.REPORT_DATE.dt.year.min()),int(D.REPORT_DATE.dt.year.max()))
if yr[0]>2009 or yr[1]<2013:raise RuntimeError(f"Unexpected corrected date coverage {yr}")
prog(4,9,f"YYMMDD repaired | valid rows={len(D)} coverage={yr[0]}..{yr[1]}")
D["noncomm_net_pct_oi"]=(D[nc_long]-D[nc_short])/D[oi_col]
D["commercial_net_pct_oi"]=(D[comm_long]-D[comm_short])/D[oi_col]
weekday=D.REPORT_DATE.dt.weekday;days=(7-weekday)%7;days=days.where(days>0,7)
D["AVAILABLE_AT"]=(D.REPORT_DATE+pd.to_timedelta(days,unit="D")).dt.normalize()
# Monday rule is deliberately conservative and fixed before alpha.
N=D[(D.REPORT_DATE.dt.year>=2009)&(D.REPORT_DATE.dt.year<=2013)][["REPORT_DATE","AVAILABLE_AT",market_col,"noncomm_net_pct_oi","commercial_net_pct_oi","__archive","__member"]].copy()
N=N.sort_values([market_col,"REPORT_DATE"]).drop_duplicates([market_col,"REPORT_DATE"],keep="last")
if len(N)<1000:raise RuntimeError(f"Suspiciously few normalized rows: {len(N)}")
prog(5,9,f"normalized rows={len(N)} markets={N[market_col].nunique()}")
names=sorted(N[market_col].astype(str).unique())
patterns={"XAUUSD":["GOLD"],"XAGUSD":["SILVER"],"EURUSD":["EURO FX"],"GBPUSD":["BRITISH POUND"],"USDJPY":["JAPANESE YEN"],"AUDUSD":["AUSTRALIAN DOLLAR"],"USDCAD":["CANADIAN DOLLAR"],"SPXUSD":["S&P 500","E-MINI S&P"],"NSXUSD":["NASDAQ"],"WTIUSD":["CRUDE OIL, LIGHT SWEET","WTI"]}
maps=[]
for target,pats in patterns.items():
 for n in names:
  if any(p.lower() in n.lower() for p in pats):maps.append({"target":target,"cftc_market_name":n})
M=pd.DataFrame(maps)
if M.empty:raise RuntimeError("Zero mapping candidates after corrected parse")
N.to_parquet(O/"CFTC_NORMALIZED_2009_2013.parquet",index=False);M.to_csv(O/"MARKET_MAPPING_CANDIDATES.csv",index=False)
nsha=hashlib.sha256((O/"CFTC_NORMALIZED_2009_2013.parquet").read_bytes()).hexdigest();msha=hashlib.sha256((O/"MARKET_MAPPING_CANDIDATES.csv").read_bytes()).hexdigest()
prog(6,9,f"mapping candidates={len(M)} | normalized sha={nsha[:12]}")
receipt={"run_id":rid,"status":"COMPLETE_CFTC_SCHEMA_REPAIR","source_period":"2009-2013","resolved_columns":resolved,"date_coverage":yr,"normalized_rows":len(N),"unique_markets":int(N[market_col].nunique()),"mapping_count":len(M),"normalized_sha256":nsha,"mapping_sha256":msha,"available_at_rule":"next Monday after report date","target_returns_accessed":False,"replication_2014_2017_accessed":False,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":errors}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(7,9,"receipt written");prog(8,9,"no alpha/target returns evaluated");prog(9,9,"STOP")
print("\n=== V55B RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== MAPPING CANDIDATES ===");print(M.to_string(index=False));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V55B compile failed"}
Write-Host "=== GEF V55B - CFTC SCHEMA REPAIR ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V55B failed"}
