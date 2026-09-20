param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v20_crossmarket.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); RAW=ROOT/"DataLake"/"raw"/"histdata"; OUTB=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v20";OUTB.mkdir(parents=True,exist_ok=True)
started=time.time(); rid="GEF20-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUTB/rid;O.mkdir()
MARKETS=["XAUUSD","XAGUSD","UDXUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","SPXUSD","NSXUSD","WTIUSD","BCOUSD"]
PAIRS=[("XAUUSD","UDXUSD"),("XAUUSD","XAGUSD"),("XAUUSD","SPXUSD"),("XAGUSD","UDXUSD"),("XAGUSD","XAUUSD"),("SPXUSD","UDXUSD"),("SPXUSD","NSXUSD"),("NSXUSD","UDXUSD"),("WTIUSD","UDXUSD"),("WTIUSD","BCOUSD"),("EURUSD","UDXUSD"),("GBPUSD","UDXUSD"),("AUDUSD","UDXUSD"),("USDJPY","UDXUSD"),("USDCAD","WTIUSD")]
H=[15,30,60,120,240]; W=[3,6,12,24,48]; T=[.95,.975,.99]
def prog(i,n,msg):
 e=time.time()-started;eta=e/i*(n-i) if i else 0
 print(f"[GEF20] {i}/{n} {100*i/n:6.2f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
 (O/"STATUS.json").write_text(json.dumps({"done":i,"total":n,"pct":100*i/n,"elapsed_s":e,"eta_s":eta,"message":msg},indent=2))
def load(m,years):
 ys=[]
 for y in years:
  p=RAW/m/"M1"/f"{m}_M1_{y}.parquet"
  if not p.exists(): continue
  d=pd.read_parquet(p);tc=next(c for c in d.columns if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc])
  x=d[["open","high","low","close"]].sort_index()
  ys.append(x.resample("5min",label="right",closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna())
 return pd.concat(ys).sort_index() if ys else None
cache={}; rows=[]; total=len(PAIRS)
for i,(target,driver) in enumerate(PAIRS,1):
 if target not in cache: cache[target]=load(target,range(2010,2014))
 if driver not in cache: cache[driver]=load(driver,range(2010,2014))
 a,b=cache[target],cache[driver]
 if a is None or b is None: prog(i,total,f"{target}<-{driver} missing");continue
 idx=a.index.intersection(b.index); ca=a.close.reindex(idx); cb=b.close.reindex(idx)
 ra=np.log(ca/ca.shift(1)); rb=np.log(cb/cb.shift(1))
 for w in W:
  # strictly contemporaneously available driver transforms at bar close
  br=np.log(cb/cb.shift(w)); bz=(rb-rb.rolling(w,min_periods=w).mean())/rb.rolling(w,min_periods=w).std()
  # divergence: target and driver cumulative return disagreement
  ar=np.log(ca/ca.shift(w)); div=ar-br
  for fname,x in [(f"drvret_{w}b",br),(f"drvz_{w}b",bz),(f"divret_{w}b",div)]:
   for h in H:
    ent=ca; ex=ca.reindex(idx+pd.Timedelta(minutes=h));ex.index=idx;y=np.log(ex/ent)*1e4
    q=pd.DataFrame({"x":x,"y":y}).dropna()
    if len(q)<1000: continue
    rho=q.corr(method="spearman").iloc[0,1]; direction=1 if rho>=0 else -1
    for tail in T:
     thr=q.x.abs().quantile(tail); z=q[q.x.abs()>=thr];p=direction*np.sign(z.x)*z.y
     yrs=p.groupby(p.index.year).mean()
     rows.append({"target":target,"driver":driver,"feature":fname,"horizon_min":h,"tail":tail,"threshold_abs":thr,"direction":direction,"rho":rho,"n":len(p),"gross_bp":p.mean(),"hit":(p>0).mean(),"posyears":(yrs>0).mean(),"min_year_bp":yrs.min()})
 prog(i,total,f"{target} <- {driver}")
R=pd.DataFrame(rows);R.to_csv(O/"DISCOVERY_CELLS.csv",index=False)
# conservative discovery screen only; one best per target-driver-feature family for later independent replication
S=R[(R.n>=500)&(R.gross_bp.abs()>=.10)&(R.posyears>=.75)].copy()
S["score"]=S.gross_bp.abs()*np.sqrt(S.n)
S=S.sort_values("score",ascending=False)
F=S.groupby(["target","driver","feature"],as_index=False).head(1).head(40).copy()
F.to_csv(O/"FROZEN_REPLICATION_CANDIDATES.csv",index=False)
receipt={"run_id":rid,"status":"COMPLETE","purpose":"new causal cross-market discovery families","discovery_period":"2010-2013 only","replication_2014_2017_accessed":False,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"pairs":len(PAIRS),"cells":len(R),"screen_survivors":len(S),"frozen_for_replication":len(F),"features":"driver return, driver z-return, target-driver return divergence; causal right-edge M5 bars","important":"Discovery screen only. No edge claim. Cross-market timestamp/session alignment remains a risk to audit before promotion.","next_gate":"Replicate frozen candidates unchanged on 2014-2017, then audit cross-market timing/session semantics before any validation.","errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));print("\n=== V20 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== TOP FROZEN ===");print(F[["target","driver","feature","horizon_min","tail","direction","n","gross_bp","hit","posyears"]].head(20).to_string(index=False));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V20 compile failed"}
Write-Host "=== GEF V20 - NEW CROSS-MARKET DISCOVERY 2010-2013 ONLY ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V20 run failed"}
