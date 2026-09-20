param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v15_replication.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,math
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); RAW=ROOT/"DataLake"/"raw"/"histdata"; BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v14"
OUTB=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v15";OUTB.mkdir(parents=True,exist_ok=True);started=time.time()
def prog(o,s,i,n,m=""):
 e=time.time()-started;eta=e/i*(n-i) if i else 0
 print(f"[GEF15] {s:<20} {i}/{n} {100*i/n:6.2f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {m}",flush=True)
 (o/"STATUS.json").write_text(json.dumps({"stage":s,"done":i,"total":n,"pct":100*i/n,"elapsed_s":e,"eta_s":eta,"message":m},indent=2))
runs=sorted([p for p in BASE.glob("GEF14-*") if p.is_dir()])
if not runs: raise RuntimeError("No V14 run found")
v14=runs[-1]; C=pd.read_parquet(v14/"discovery_cells.parquet")
rid="GEF15-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUTB/rid;O.mkdir()
# Freeze diverse families, not arbitrary top cells: one representative per market/feature family/horizon neighborhood.
C["family"]=C.feature.str.extract(r"^([a-z]+)")[0]
eligible=C[(C.n>=1000)&(C.years_positive>=.75)&(C.gross_bp.abs()>=.20)].copy()
eligible["strength"]=eligible.gross_bp.abs()*np.sqrt(eligible.n)*eligible.years_positive
frozen=[]
used=set()
for _,r in eligible.sort_values("strength",ascending=False).iterrows():
 key=(r.market,r.family)
 if key in used: continue
 frozen.append(r)
 used.add(key)
 if len(frozen)>=24: break
FZ=pd.DataFrame(frozen)
if len(FZ)==0: raise RuntimeError("No diverse candidates to freeze")
FZ.to_csv(O/"FROZEN_CANDIDATES.csv",index=False)
# candidate computation
def load(m,years):
 ys=[]
 for y in years:
  p=RAW/m/"M1"/f"{m}_M1_{y}.parquet"
  if not p.exists(): continue
  d=pd.read_parquet(p);tc=next(c for c in d.columns if c.lower() in ("datetime","time","timestamp"))
  d.index=pd.to_datetime(d[tc]);x=d[["open","high","low","close"]].sort_index()
  g=x.resample("5min",label="right",closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()
  ys.append(g)
 return pd.concat(ys).sort_index() if ys else None
def exact_fwd(c,mins):
 f=c.reindex(c.index+pd.Timedelta(minutes=int(mins)));f.index=c.index;return np.log(f/c)*1e4
def feature(d,name):
 c=d.close.astype(float);lr=np.log(c/c.shift(1));n=int(name.split("_")[1][:-1])
 if name.startswith("ret_"): return np.log(c/c.shift(n))
 if name.startswith("zret_"):
  mu=lr.rolling(n,min_periods=n).mean();sd=lr.rolling(n,min_periods=n).std();return (lr-mu)/sd
 if name.startswith("range_"):
  lo=c.rolling(n,min_periods=n).min();hi=c.rolling(n,min_periods=n).max();return (c-lo)/(hi-lo)
 if name.startswith("vol_"): return lr.rolling(n,min_periods=n).std()
 raise ValueError(name)
results=[]; total=len(FZ)
for i,r in FZ.reset_index(drop=True).iterrows():
 m=r.market; fn=r.feature; h=int(r.horizon_min); tail=float(r.tail); rho=float(r.rho)
 disc=load(m,range(2010,2014)); rep=load(m,range(2014,2018))
 xd=feature(disc,fn); xr=feature(rep,fn); yd=exact_fwd(disc.close,h); yr=exact_fwd(rep.close,h)
 qd=pd.concat([xd,yd],axis=1).dropna();qd.columns=["x","y"];qr=pd.concat([xr,yr],axis=1).dropna();qr.columns=["x","y"]
 thr=float(qd.x.abs().quantile(tail)); s=1.0 if rho>=0 else -1.0
 def evalq(q):
  mask=q.x.abs()>=thr;p=s*np.sign(q.loc[mask,"x"])*q.loc[mask,"y"]
  yp=p.groupby(p.index.year).mean()
  return len(p),float(p.mean()),float((p>0).mean()),float((yp>0).mean()),{int(y):float(v) for y,v in yp.items()}
 nd,gd,hd,pyd,ydic=evalq(qd); nr,gr,hr,pyr,yric=evalq(qr)
 # neighboring thresholds from discovery distribution, same frozen direction
 neigh=[]
 for t2 in [max(.80,tail-.025),tail,min(.995,tail+.025)]:
  th2=float(qd.x.abs().quantile(t2));mask=qr.x.abs()>=th2;p=s*np.sign(qr.loc[mask,"x"])*qr.loc[mask,"y"];neigh.append({"tail":t2,"gross_bp":float(p.mean()),"n":len(p)})
 results.append({"market":m,"feature":fn,"horizon_min":h,"tail":tail,"direction":int(s),"threshold_abs":thr,"disc_n":nd,"disc_gross_bp":gd,"disc_hit":hd,"disc_posyears":pyd,"rep_n":nr,"rep_gross_bp":gr,"rep_hit":hr,"rep_posyears":pyr,"rep_yearly":json.dumps(yric),"neighbor_rep":json.dumps(neigh)})
 prog(O,"REPLICATION",i+1,total,f"{m} {fn} h{h} tail{tail}")
R=pd.DataFrame(results)
# Conservative replication gate: same sign as discovery gross, >=3/4 positive years, >=500 events, and center/neighbor sign coherence >=2/3.
def passrow(r):
 try: neigh=json.loads(r.neighbor_rep); coh=sum(np.sign(x["gross_bp"])==np.sign(r.rep_gross_bp) for x in neigh)>=2
 except: coh=False
 return (r.rep_n>=500 and r.rep_posyears>=.75 and np.sign(r.rep_gross_bp)==np.sign(r.disc_gross_bp) and abs(r.rep_gross_bp)>=.10 and coh)
R["replication_pass"]=R.apply(passrow,axis=1)
R.to_csv(O/"REPLICATION_RESULTS.csv",index=False)
P=R[R.replication_pass].copy();P.to_csv(O/"REPLICATION_PASSES.csv",index=False)
receipt={"run_id":rid,"status":"COMPLETE","source_v14":v14.name,"discovery_period":"2010-2013","replication_period":"2014-2017","validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"frozen_candidates":len(FZ),"replication_passes":len(P),"selection_rule":"one diverse representative per market/feature family from V14, max 24; thresholds/directions frozen from 2010-2013","next_gate":"If any pass: robustness and nulls within 2010-2017 only, then freeze before opening 2018-2022 validation. If none pass, return to new discovery families without loosening this gate.","errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(O,"COMPLETE",1,1,f"passes={len(P)}")
print("\n=== V15 RECEIPT ===");print(json.dumps(receipt,indent=2))
print("\n=== REPLICATION RESULTS ===");print(R[["market","feature","horizon_min","tail","disc_gross_bp","rep_gross_bp","rep_hit","rep_posyears","replication_pass"]].to_string(index=False))
print("\n=== PASSES ===");print(P[["market","feature","horizon_min","tail","rep_gross_bp","rep_hit","rep_posyears"]].to_string(index=False) if len(P) else "NONE")
print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V15 compile failed"}
Write-Host "=== GEF V15 - FROZEN DIVERSE REPLICATION 2014-2017 ONLY ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V15 run failed"}
