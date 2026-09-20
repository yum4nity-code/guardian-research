param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v23_robustness.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");RAW=ROOT/"DataLake"/"raw"/"histdata";V22B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v22";OUTB=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v23";OUTB.mkdir(parents=True,exist_ok=True)
started=time.time();runs=sorted([p for p in V22B.glob("GEF22-*") if (p/"ALIGNMENT_CLEARED_CANDIDATES.csv").exists()])
if not runs:raise RuntimeError("No V22 cleared candidates")
src=runs[-1];F=pd.read_csv(src/"ALIGNMENT_CLEARED_CANDIDATES.csv")
rid="GEF23-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUTB/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-started;eta=e/i*(n-i) if i else 0
 print(f"[GEF23] {i}/{n} {100*i/n:6.2f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
 (O/"STATUS.json").write_text(json.dumps({"done":i,"total":n,"pct":100*i/n,"elapsed_s":e,"eta_s":eta,"message":msg},indent=2))
def load(m,years):
 ys=[]
 for y in years:
  p=RAW/m/"M1"/f"{m}_M1_{y}.parquet"
  if not p.exists():continue
  d=pd.read_parquet(p);tc=next(c for c in d.columns if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc])
  x=d[["open","high","low","close"]].sort_index();ys.append(x.resample("5min",label="right",closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna())
 return pd.concat(ys).sort_index()
cache={}
def get(m):
 if m not in cache:cache[m]=load(m,range(2010,2018))
 return cache[m]
rng=np.random.default_rng(23001);rows=[]
for i,r in F.reset_index(drop=True).iterrows():
 t,dv,fn=r["target"],r["driver"],r["feature"];h=int(r["horizon_min"]);tail=float(r["tail"]);direction=int(r["direction"]);thr=float(r["threshold_abs"])
 a,b=get(t),get(dv);idx=a.index.intersection(b.index);ca=a.close.reindex(idx);cb=b.close.reindex(idx);rb=np.log(cb/cb.shift(1));w=int(fn.split("_")[1][:-1])
 if fn.startswith("drvret_"):x=np.log(cb/cb.shift(w))
 elif fn.startswith("drvz_"):x=(rb-rb.rolling(w,min_periods=w).mean())/rb.rolling(w,min_periods=w).std()
 else:x=np.log(ca/ca.shift(w))-np.log(cb/cb.shift(w))
 mask=(idx.year>=2014)&(idx.year<=2017);x=x[mask];cc=ca[mask];sel=x[x.abs()>=thr];sig=direction*np.sign(sel)
 def pp(delay):
  ent=cc.reindex(sig.index+pd.Timedelta(minutes=delay));ex=cc.reindex(sig.index+pd.Timedelta(minutes=delay+h));ent.index=sig.index;ex.index=sig.index
  return (sig*np.log(ex/ent)*1e4).dropna()
 p=pp(0);p5=pp(5);p15=pp(15)
 k=max(1,int(len(p)*.01));trim=p.drop(p.nlargest(k).index)
 day=p.groupby(p.index.floor("D")).sum();bd=set(day.nlargest(min(5,len(day))).index);no5=p[~p.index.floor("D").isin(bd)]
 # non-overlap
 keep=[];last=None
 for tt in p.index:
  if last is None or tt>=last+pd.Timedelta(minutes=h):keep.append(tt);last=tt
 pn=p.loc[keep]
 # 2000 daily sign flips
 days=[g.to_numpy() for _,g in p.groupby(p.index.floor("D"))];obs=p.mean();null=[]
 for _ in range(2000):
  arr=np.concatenate([g*(1 if rng.random()>.5 else -1) for g in days]);null.append(arr.mean())
 nullp=(1+sum(v>=obs for v in null))/(2001)
 yrs=p.groupby(p.index.year).mean()
 passed=bool(len(p)>=500 and obs>0 and p5.mean()>0 and p15.mean()>0 and trim.mean()>0 and no5.mean()>0 and pn.mean()>0 and (yrs>0).mean()>=.75 and nullp<=.05)
 rows.append({"target":t,"driver":dv,"feature":fn,"horizon_min":h,"tail":tail,"n":len(p),"gross_bp":obs,"delay5":p5.mean(),"delay15":p15.mean(),"trim_best1pct":trim.mean(),"remove_best5days":no5.mean(),"nonoverlap_n":len(pn),"nonoverlap_bp":pn.mean(),"posyears":(yrs>0).mean(),"null_p":nullp,"robust_pass":passed})
 prog(i+1,len(F),f"{t}<-{dv} {fn} pass={passed}")
R=pd.DataFrame(rows);R.to_csv(O/"ROBUSTNESS_RESULTS.csv",index=False);P=R[R.robust_pass].copy();P.to_csv(O/"PREVALIDATION_CANDIDATES.csv",index=False)
receipt={"run_id":rid,"status":"COMPLETE","source_v22":src.name,"period":"2010-2017 only; robustness evaluated on 2014-2017 with discovery-frozen parameters","validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"candidates":len(R),"robust_passes":len(P),"gate":"n>=500; gross/delay5/delay15/remove-best1%/remove-best5days/non-overlap all >0; >=75% positive years; daily-sign-flip p<=.05","null":"2000 daily sign flips, preserving within-day observations; descriptive dependence-aware null, not full DGP","next_gate":"Human review. If survivors exist, freeze exact definitions before opening 2018-2022 validation.","errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
print("\n=== V23 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== ROBUSTNESS ===");print(R.to_string(index=False));print("\n=== PREVALIDATION CANDIDATES ===");print(P.to_string(index=False) if len(P) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V23 compile failed"}
Write-Host "=== GEF V23 - CROSS-MARKET PRE-VALIDATION ROBUSTNESS ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V23 run failed"}
