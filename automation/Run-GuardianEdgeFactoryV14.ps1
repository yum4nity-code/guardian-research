param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v14_discovery.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); RAW=ROOT/"DataLake"/"raw"/"histdata"; OUTB=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v14"
OUTB.mkdir(parents=True,exist_ok=True); started=time.time()
MARKETS=["XAUUSD","XAGUSD","UDXUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","SPXUSD","NSXUSD","WTIUSD","BCOUSD"]
YEARS=range(2010,2014); H=[5,15,30,60,120,240]
def prog(o,s,i,n,m=""):
 e=time.time()-started; eta=e/i*(n-i) if i else 0
 print(f"[GEF14] {s:<18} {i}/{n} {100*i/n:6.2f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {m}",flush=True)
 (o/"STATUS.json").write_text(json.dumps({"stage":s,"done":i,"total":n,"pct":100*i/n,"elapsed_s":e,"eta_s":eta,"message":m},indent=2))
rid="GEF14-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"); O=OUTB/rid;O.mkdir()
def load(m):
 ys=[]
 for y in YEARS:
  p=RAW/m/"M1"/f"{m}_M1_{y}.parquet"
  if not p.exists(): continue
  d=pd.read_parquet(p); tc=next(c for c in d.columns if c.lower() in ("datetime","time","timestamp"))
  d.index=pd.to_datetime(d[tc]); x=d[["open","high","low","close"]].sort_index()
  # causal: [t-5,t) labelled at t, known at t
  g=x.resample("5min",label="right",closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()
  ys.append(g)
 return pd.concat(ys).sort_index() if ys else None
def exact_fwd(c,mins):
 f=c.reindex(c.index+pd.Timedelta(minutes=mins));f.index=c.index
 return np.log(f/c)*1e4
def feats(d):
 c=d.close.astype(float); lr=np.log(c/c.shift(1)); out={}
 # Explicit BARS: 3/6/12/24/48 = 15/30/60/120/240 elapsed minutes on M5.
 for n in [3,6,12,24,48]:
  out[f"ret_{n}b"]=np.log(c/c.shift(n))
  mu=lr.rolling(n,min_periods=n).mean(); sd=lr.rolling(n,min_periods=n).std()
  out[f"zret_{n}b"]=(lr-mu)/sd
  lo=c.rolling(n,min_periods=n).min(); hi=c.rolling(n,min_periods=n).max()
  out[f"range_{n}b"]=(c-lo)/(hi-lo)
  out[f"vol_{n}b"]=sd
 return pd.DataFrame(out,index=d.index).replace([np.inf,-np.inf],np.nan)
ledger=[]; cells=[]; total=len(MARKETS)
for mi,m in enumerate(MARKETS,1):
 d=load(m)
 if d is None: prog(O,"MARKETS",mi,total,m+" unavailable");continue
 F=feats(d); targets={h:exact_fwd(d.close,h) for h in H}
 for fn in F:
  x=F[fn]
  # Discovery-only unconditional rank association + tail conditional means.
  for h,y in targets.items():
   q=pd.concat([x,y],axis=1).dropna();q.columns=["x","y"];n=len(q)
   if n<5000: continue
   rho=float(q.corr(method="spearman").iloc[0,1])
   for pct in [.90,.95,.975,.99]:
    a=float(q.x.abs().quantile(pct)); mask=q.x.abs()>=a
    # direction selected only from sign of discovery association, recorded as a trial.
    s=1.0 if rho>=0 else -1.0; pnl=s*np.sign(q.loc[mask,"x"])*q.loc[mask,"y"]
    cells.append({"market":m,"feature":fn,"horizon_min":h,"tail":pct,"n":int(mask.sum()),"rho":rho,"gross_bp":float(pnl.mean()),"hit":float((pnl>0).mean()),"years_positive":float((pnl.groupby(pnl.index.year).mean()>0).mean())})
    ledger.append({"market":m,"feature":fn,"horizon_min":h,"tail":pct,"direction_from_rho":int(s),"trial_type":"discovery_tail"})
 prog(O,"MARKETS",mi,total,f"{m} cells={sum(1 for x in cells if x['market']==m)}")
C=pd.DataFrame(cells);L=pd.DataFrame(ledger)
C.to_parquet(O/"discovery_cells.parquet",index=False);L.to_csv(O/"TRIAL_LEDGER.csv",index=False)
# Broad screen only. Ranking is descriptive; no replication data touched.
if len(C):
 C["score"]=C.gross_bp.abs()*np.sqrt(C.n)*C.years_positive
 top=C.sort_values("score",ascending=False).head(100);top.to_csv(O/"TOP100_DISCOVERY_SCREEN.csv",index=False)
 survivors=C[(C.n>=500)&(C.years_positive>=.75)&(C.gross_bp.abs()>=.20)].sort_values("score",ascending=False)
 survivors.to_csv(O/"DISCOVERY_SURVIVORS.csv",index=False)
else: survivors=C
receipt={"run_id":rid,"status":"COMPLETE","period":"2010-01-01..2013-12-31","replication_2014_2017_accessed":False,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"markets_requested":MARKETS,"cells":len(C),"trials":len(L),"screen_survivors":len(survivors),"feature_semantics":"all windows explicitly bars on causal M5; targets exact timestamps","selection_note":"Discovery screen only. No survivor is an edge until independent replication/robustness.","next_gate":"Inspect survivor diversity and neighborhood stability, freeze a small preregistered set, then test 2014-2017 only.","errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(O,"COMPLETE",1,1,f"survivors={len(survivors)}")
print("\n=== V14 RECEIPT ===");print(json.dumps(receipt,indent=2))
print("\n=== TOP DISCOVERY SURVIVORS ===");print(survivors.head(30).to_string(index=False) if len(survivors) else "NONE")
print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V14 compile failed"}
Write-Host "=== GEF V14 — CAUSAL DISCOVERY 2010-2013 ONLY ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V14 run failed"}
