param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v82b_cftc_recovery.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,zipfile,tempfile,os,re,hashlib
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";SRC=DL/"raw"/"cftc"/"futures_only_reports"
rid="GEF82B-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");O=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v82b"/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0
 (O/"LIVE_STATUS.json").write_text(json.dumps({"run_id":rid,"step":i,"steps":n,"percent":100*i/n,"elapsed_s":e,"eta_s":eta,"message":msg},indent=2))
 print(f"[GEF82B] {i}/{n} {100*i/n:.0f}% | elapsed {e:.1f}s | ETA {eta:.1f}s | {msg}",flush=True)
prog(1,8,"recover CFTC from known ZIP/Excel source; no edge search")
files=sorted(SRC.glob("*.zip"));use=[p for p in files if any(str(y) in p.name for y in range(2009,2014)) and "excel" in p.name.lower()]
if not use: raise RuntimeError(f"No 2009-2013 CFTC Excel ZIPs at {SRC}")
prog(2,8,f"archives={len(use)}")
rows=[];schemas=[];errs=[]
for j,p in enumerate(use,1):
 try:
  with zipfile.ZipFile(p) as z:
   for m in [x for x in z.namelist() if x.lower().endswith((".xls",".xlsx"))]:
    suf=Path(m).suffix
    with tempfile.NamedTemporaryFile(suffix=suf,delete=False) as tf:tf.write(z.read(m));tmp=tf.name
    try:
     d=pd.read_excel(tmp);d["__archive"]=p.name;d["__member"]=m;rows.append(d)
     schemas.append({"archive":p.name,"member":m,"rows":len(d),"columns":"|".join(map(str,d.columns))})
    except Exception as e:errs.append({"archive":p.name,"member":m,"error":repr(e)})
    finally:
     try:os.unlink(tmp)
     except:pass
 except Exception as e:errs.append({"archive":p.name,"error":repr(e)})
 if j==1 or j==len(use) or j%2==0:prog(2,8,f"read {j}/{len(use)} archives")
if not rows:raise RuntimeError("CFTC archives found but none parsed")
D=pd.concat(rows,ignore_index=True,sort=False);pd.DataFrame(schemas).to_csv(O/"SCHEMA_INVENTORY.csv",index=False)
prog(3,8,f"parsed rows={len(D):,} cols={len(D.columns)}")
cols=list(D.columns)
def first(keys):
 for c in cols:
  z=str(c).strip().lower()
  if any(k in z for k in keys):return c
date=first(["as of date in form yymmdd","report_date_as_yyyy-mm-dd","report date","as_of_date"])
market=first(["market and exchange names","market_and_exchange_names"])
oi=first(["open interest (all)","open_interest_all"])
ncl=first(["noncommercial positions-long","noncomm_positions_long_all"]);ncs=first(["noncommercial positions-short","noncomm_positions_short_all"])
cl=first(["commercial positions-long","comm_positions_long_all"]);cs=first(["commercial positions-short","comm_positions_short_all"])
resolved={"date":date,"market":market,"oi":oi,"noncomm_long":ncl,"noncomm_short":ncs,"comm_long":cl,"comm_short":cs}
if any(v is None for v in resolved.values()):raise RuntimeError("CFTC schema unresolved: "+json.dumps(resolved))
(O/"RESOLVED_COLUMNS.json").write_text(json.dumps(resolved,indent=2))
prog(4,8,"core CFTC schema resolved")
D[date]=pd.to_datetime(D[date],errors="coerce")
for c in [oi,ncl,ncs,cl,cs]:D[c]=pd.to_numeric(D[c],errors="coerce")
D=D[D[date].notna() & D[market].notna() & (D[oi]>0)].copy()
D["noncomm_net_pct_oi"]=(D[ncl]-D[ncs])/D[oi];D["commercial_net_pct_oi"]=(D[cl]-D[cs])/D[oi]
# Conservative: Tuesday report becomes usable Friday 21:00 UTC. This is later than usual publication and avoids pre-release use.
D["AVAILABLE_AT"]=D[date].dt.normalize()+pd.Timedelta(days=3,hours=21)
N=D[D[date].dt.year.between(2009,2013)][[date,"AVAILABLE_AT",market,"noncomm_net_pct_oi","commercial_net_pct_oi","__archive","__member"]].copy()
N=N.sort_values([market,date]).drop_duplicates([market,date],keep="last")
prog(5,8,f"normalized rows={len(N):,}; AVAILABLE_AT=report+3d21h")
out=DL/"normalized"/"cftc_pre2023";out.mkdir(parents=True,exist_ok=True);dest=out/"CFTC_FUTURES_ONLY_2009_2013_CAUSAL.parquet";N.to_parquet(dest,index=False)
sha=hashlib.sha256(dest.read_bytes()).hexdigest()
prog(6,8,f"canonical causal parquet written sha={sha[:12]}")
names=sorted(N[market].astype(str).unique());patterns={"XAUUSD":["GOLD"],"XAGUSD":["SILVER"],"EURUSD":["EURO FX"],"GBPUSD":["BRITISH POUND"],"USDJPY":["JAPANESE YEN"],"AUDUSD":["AUSTRALIAN DOLLAR"],"USDCAD":["CANADIAN DOLLAR"],"SPXUSD":["S&P 500","E-MINI S&P"],"NSXUSD":["NASDAQ"],"WTIUSD":["CRUDE OIL, LIGHT SWEET","WTI"]}
maps=[]
for target,pats in patterns.items():
 for n in names:
  if any(p.lower() in n.lower() for p in pats):maps.append({"target":target,"cftc_market_name":n})
pd.DataFrame(maps).to_csv(O/"MARKET_MAPPING_CANDIDATES.csv",index=False)
prog(7,8,f"market mappings={len(maps)}")
receipt={"run_id":rid,"status":"COMPLETE_CFTC_CAUSAL_RECOVERY","archives":len(use),"normalized_rows":len(N),"canonical_path":str(dest),"sha256":sha,"available_at_rule":"report_date +3d21h UTC conservative","edge_trials":0,"2014_plus_accessed":False,"2023_plus_accessed":False,"protected_2026_accessed":False,"errors":errs,"next":"V83 corrected multiresolution matrix"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(8,8,"DONE")
print("\n=== V82B RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== MAPPINGS ===");print(pd.DataFrame(maps).to_string(index=False) if maps else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V82B compile failed"}
Write-Host "=== GEF V82B - CFTC RECOVERY ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V82B failed"}
