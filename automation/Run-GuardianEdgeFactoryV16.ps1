param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v16_robustness.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); RAW=ROOT/"DataLake"/"raw"/"histdata"; V15B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v15"; OUTB=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v16";OUTB.mkdir(parents=True,exist_ok=True)
started=time.time()
def prog(o,s,i,n,m=""):
 e=time.time()-started;eta=e/i*(n-i) if i else 0
 print(f"[GEF16] {s:<18} {i}/{n} {100*i/n:6.2f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {m}",flush=True)
 (o/"STATUS.json").write_text(json.dumps({"stage":s,"done":i,"total":n,"pct":100*i/n,"elapsed_s":e,"eta_s":eta,"message":m},indent=2))
runs=sorted([p for p in V15B.glob("GEF15-*") if (p/"REPLICATION_PASSES.csv").exists()])
if not runs: raise RuntimeError("No completed V15")
src=runs[-1]; F=pd.read_csv(src/"REPLICATION_PASSES.csv")
rid="GEF16-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUTB/rid;O.mkdir()
def load(m):
 ys=[]
 for y in range(2010,2018):
  p=RAW/m/"M1"/f"{m}_M1_{y}.parquet"
  if not p.exists(): continue
  d=pd.read_parquet(p);tc=next(c for c in d.columns if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc])
  x=d[["open","high","low","close"]].sort_index()
  ys.append(x.resample("5min",label="right",closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna())
 return pd.concat(ys).sort_index()
def feat(d,name):
 c=d.close.astype(float);lr=np.log(c/c.shift(1));n=int(name.split("_")[1][:-1])
 if name.startswith("ret_"): return np.log(c/c.shift(n))
 if name.startswith("zret_"): return (lr-lr.rolling(n,min_periods=n).mean())/lr.rolling(n,min_periods=n).std()
 if name.startswith("range_"):
  lo=c.rolling(n,min_periods=n).min();hi=c.rolling(n,min_periods=n).max();return (c-lo)/(hi-lo)
 if name.startswith("vol_"): return lr.rolling(n,min_periods=n).std()
def fwd(c,h):
 q=c.reindex(c.index+pd.Timedelta(minutes=int(h)));q.index=c.index;return np.log(q/c)*1e4
rows=[]; B=1000
for ci,r in F.reset_index(drop=True).iterrows():
 m=r["market"];fn=r["feature"];h=int(r["horizon_min"]);tail=float(r["tail"])
 d=load(m);x=feat(d,fn);y=fwd(d.close,h);q=pd.concat([x,y],axis=1).dropna();q.columns=["x","y"]
 disc=q[q.index.year<=2013]; rep=q[(q.index.year>=2014)&(q.index.year<=2017)]
 thr=float(disc.x.abs().quantile(tail)); rho=float(disc.corr(method="spearman").iloc[0,1]);s=1 if rho>=0 else -1
 mask=rep.x.abs()>=thr;p=s*np.sign(rep.loc[mask,"x"])*rep.loc[mask,"y"];sig=np.sign(rep.loc[mask,"x"])*s
 # delay by exact timestamps: signal formed at t, enter t+delay, exit entry+h.
 tests={}
 for delay in [0,5,15]:
  ent=d.close.reindex(p.index+pd.Timedelta(minutes=delay));ex=d.close.reindex(p.index+pd.Timedelta(minutes=delay+h));ent.index=p.index;ex.index=p.index
  pp=sig*np.log(ex/ent)*1e4;pp=pp.dropna();tests[f"d{delay}"]={"n":len(pp),"gross":float(pp.mean()),"posyears":float((pp.groupby(pp.index.year).mean()>0).mean())}
 # tails
 ps=p.sort_values(ascending=False); k=max(1,int(len(p)*.01)); trim=p.drop(ps.index[:k]); day=p.groupby(p.index.floor("D")).sum(); bestdays=set(day.nlargest(min(5,len(day))).index); no5=p[~p.index.floor("D").isin(bestdays)]
 # day sign-flip null (dependence preserved within day)
 dayblocks=[g.to_numpy() for _,g in p.groupby(p.index.floor("D"))];obs=float(p.mean());rng=np.random.default_rng(16000+ci);null=np.empty(B)
 for b in range(B):
  vals=[a*(1 if rng.integers(0,2) else -1) for a in dayblocks];null[b]=np.concatenate(vals).mean()
 pv=float((1+np.sum(null>=obs))/(B+1))
 # neighbor thresholds
 neigh=[]
 for t2 in sorted(set([max(.80,tail-.025),tail,min(.995,tail+.025)])):
  th=float(disc.x.abs().quantile(t2));mm=rep.x.abs()>=th;z=s*np.sign(rep.loc[mm,"x"])*rep.loc[mm,"y"];neigh.append({"tail":t2,"gross":float(z.mean()),"n":len(z)})
 row={"market":m,"feature":fn,"horizon_min":h,"tail":tail,"rep_gross":obs,"rep_n":len(p),"trim_best1pct":float(trim.mean()),"remove_best5days":float(no5.mean()),"null_p":pv,"delays":json.dumps(tests),"neighbors":json.dumps(neigh)}
 # no hard alpha declaration: robustness gate for validation eligibility
 d15=tests["d15"]["gross"]; coherent=sum(np.sign(z["gross"])==np.sign(obs) for z in neigh)>=2
 row["robust_pass"]=bool(obs>0 and tests["d5"]["gross"]>0 and d15>0 and tests["d15"]["posyears"]>=.5 and no5.mean()>0 and pv<=.05 and coherent)
 rows.append(row);prog(O,"ROBUSTNESS",ci+1,len(F),f"{m} {fn} pass={row['robust_pass']}")
R=pd.DataFrame(rows);R.to_csv(O/"ROBUSTNESS_RESULTS.csv",index=False);P=R[R.robust_pass].copy();P.to_csv(O/"VALIDATION_ELIGIBLE.csv",index=False)
receipt={"run_id":rid,"status":"COMPLETE","source_v15":src.name,"data_period":"2010-2017 only","validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"candidates":len(R),"robust_passes":len(P),"null":"1000 daily block sign flips; within-day dependence preserved; not a full DGP null","tests":["delay +5m","+15m","remove best 1% trades","remove best 5 days","neighbor thresholds","daily sign-flip null"],"next_gate":"Freeze robust survivors exactly, then human review before using 2018-2022 as independent validation. Do not open 2023+.","errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(O,"COMPLETE",1,1,f"robust={len(P)}")
print("\n=== V16 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== ROBUSTNESS ===");print(R.to_string(index=False));print("\n=== VALIDATION ELIGIBLE ===");print(P[["market","feature","horizon_min","tail","rep_gross","trim_best1pct","remove_best5days","null_p"]].to_string(index=False) if len(P) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V16 compile failed"}
Write-Host "=== GEF V16 - PRE-VALIDATION ROBUSTNESS 2010-2017 ONLY ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V16 run failed"}
