param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v21_replication.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); RAW=ROOT/"DataLake"/"raw"/"histdata"; V20B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v20"; OUTB=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v21";OUTB.mkdir(parents=True,exist_ok=True)
started=time.time()
runs=sorted([p for p in V20B.glob("GEF20-*") if (p/"FROZEN_REPLICATION_CANDIDATES.csv").exists()])
if not runs: raise RuntimeError("No V20 frozen candidates found")
src=runs[-1]; F=pd.read_csv(src/"FROZEN_REPLICATION_CANDIDATES.csv")
rid="GEF21-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUTB/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-started;eta=e/i*(n-i) if i else 0
 print(f"[GEF21] {i}/{n} {100*i/n:6.2f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
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
cache={}
def get(m,years):
 k=(m,tuple(years))
 if k not in cache: cache[k]=load(m,years)
 return cache[k]
rows=[]
for i,r in F.reset_index(drop=True).iterrows():
 target=r["target"];driver=r["driver"];feature=r["feature"];h=int(r["horizon_min"]);tail=float(r["tail"]);direction=int(r["direction"]);thr=float(r["threshold_abs"])
 a=get(target,range(2014,2018));b=get(driver,range(2014,2018))
 if a is None or b is None:
  prog(i+1,len(F),f"{target}<-{driver} missing");continue
 idx=a.index.intersection(b.index);ca=a.close.reindex(idx);cb=b.close.reindex(idx);ra=np.log(ca/ca.shift(1));rb=np.log(cb/cb.shift(1))
 w=int(feature.split("_")[1][:-1])
 if feature.startswith("drvret_"): x=np.log(cb/cb.shift(w))
 elif feature.startswith("drvz_"): x=(rb-rb.rolling(w,min_periods=w).mean())/rb.rolling(w,min_periods=w).std()
 elif feature.startswith("divret_"): x=np.log(ca/ca.shift(w))-np.log(cb/cb.shift(w))
 else: raise ValueError(feature)
 ex=ca.reindex(idx+pd.Timedelta(minutes=h));ex.index=idx;y=np.log(ex/ca)*1e4
 q=pd.DataFrame({"x":x,"y":y}).dropna();z=q[q.x.abs()>=thr];p=direction*np.sign(z.x)*z.y
 yrs=p.groupby(p.index.year).mean()
 # fixed neighboring quantiles are NOT recomputed here; threshold itself stays frozen.
 rows.append({"target":target,"driver":driver,"feature":feature,"horizon_min":h,"tail":tail,"direction":direction,"threshold_abs":thr,
              "rep_n":len(p),"rep_gross_bp":float(p.mean()) if len(p) else np.nan,"rep_hit":float((p>0).mean()) if len(p) else np.nan,
              "rep_posyears":float((yrs>0).mean()) if len(yrs) else np.nan,"rep_yearly":json.dumps({int(k):float(v) for k,v in yrs.items()}),
              "discovery_gross_bp":float(r["gross_bp"])})
 prog(i+1,len(F),f"{target} <- {driver} {feature}")
R=pd.DataFrame(rows)
R["same_sign"]=np.sign(R.rep_gross_bp)==np.sign(R.discovery_gross_bp)
R["rep_pass"]=(R.rep_n>=500)&R.same_sign&(R.rep_posyears>=.75)&(R.rep_gross_bp.abs()>=.10)
R.to_csv(O/"REPLICATION_RESULTS.csv",index=False)
P=R[R.rep_pass].copy().sort_values("rep_gross_bp",key=lambda s:s.abs(),ascending=False)
P.to_csv(O/"REPLICATION_PASSES.csv",index=False)
receipt={"run_id":rid,"status":"COMPLETE","source_v20":src.name,"replication_period":"2014-2017 only","validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"frozen_candidates":len(F),"replication_passes":len(P),"pass_rule":"n>=500; same sign as discovery; >=75% positive years in signed pnl sense; |gross|>=0.10 bp/trade","important":"Cross-market timestamp/session semantics have NOT yet been independently audited. Any pass is provisional until that audit.","next_gate":"Audit time/session alignment and causal availability for replication passes before any 2018-2022 validation.","errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
print("\n=== V21 RECEIPT ===");print(json.dumps(receipt,indent=2))
print("\n=== TOP REPLICATION PASSES ===")
print(P[["target","driver","feature","horizon_min","tail","direction","rep_n","rep_gross_bp","rep_hit","rep_posyears"]].head(25).to_string(index=False) if len(P) else "NONE")
print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V21 compile failed"}
Write-Host "=== GEF V21 - CROSS-MARKET REPLICATION 2014-2017 ONLY ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V21 run failed"}
