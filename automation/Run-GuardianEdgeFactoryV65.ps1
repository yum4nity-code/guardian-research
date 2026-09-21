param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v65_intraday_calendar_robustness.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,time,json,hashlib
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";PREV=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v64"
runs=sorted([p for p in PREV.glob("GEF64-*") if (p/"V65_REPLICATION_SURVIVORS.csv").exists()])
if not runs:raise RuntimeError("No V64 survivors")
P=runs[-1];fp=P/"V65_REPLICATION_SURVIVORS.csv";EXPECTED="978eff2d4207e7b22bf1c8d661f5aa556bcd8e075ec917847cb1b99775d1fc69"
sha=hashlib.sha256(fp.read_bytes()).hexdigest()
if sha!=EXPECTED:raise RuntimeError(f"V64 survivor SHA mismatch {sha}")
F=pd.read_csv(fp);BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v65";rid="GEF65-"+pd.Timestamp.utcnow().strftime("%Y%m%d-%H%M%S");O=BASE/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0
 print(f"[GEF65] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
def load(sym):
 z=[]
 for y in range(2010,2018):
  p=DL/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
  if not p.exists():continue
  d=pd.read_parquet(p);dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None);pc=next((c for c in d.columns if str(c).lower()=="close"),None)
  if dc is None and isinstance(d.index,pd.DatetimeIndex):d=d.reset_index();dc=d.columns[0]
  if dc is None or pc is None:continue
  z.append(pd.DataFrame({"dt":pd.to_datetime(d[dc],errors="coerce"),"px":pd.to_numeric(d[pc],errors="coerce")}).dropna())
 d=pd.concat(z).sort_values("dt").drop_duplicates("dt");assert d.dt.dt.year.max()<=2017;return d
def metrics(ret):
 ret=pd.Series(ret).dropna()
 if not len(ret):return dict(n=0,mean_bp=np.nan,hit=np.nan,trim1_bp=np.nan,trim2_bp=np.nan,remove_best5_bp=np.nan)
 a=np.sort(ret.values);n=len(a);t1=a[:max(1,int(np.floor(.99*n)))];t2=a[:max(1,int(np.floor(.98*n)))]
 rm=ret.drop(ret.nlargest(min(5,len(ret))).index)
 return dict(n=n,mean_bp=ret.mean()*1e4,hit=(ret>0).mean(),trim1_bp=np.mean(t1)*1e4,trim2_bp=np.mean(t2)*1e4,remove_best5_bp=rm.mean()*1e4 if len(rm) else np.nan)
prog(1,14,f"survivor SHA verified {sha[:12]}; robustness uses 2010-2017 only")
cache={};out=[]
for i,r in F.iterrows():
 if r.market not in cache:cache[r.market]=load(r.market)
 d=cache[r.market]
 if r.mechanism=="weekday":
  q=d.set_index("dt").px.resample("1D").last().dropna().to_frame("px");q["fwd"]=q.px.shift(-1)/q.px-1;q=q.dropna();g=q[q.index.dayofweek==int(r.bucket)];side=1 if r["mode"]=="long" else -1;ret=g.fwd*side
  # Neighbor stability: adjacent weekdays must not both be strongly opposite; diagnostic, not alpha rescue.
  neigh=[]
  for b in [(int(r.bucket)-1)%7,(int(r.bucket)+1)%7]:
   gg=q[q.index.dayofweek==b];neigh.append(float((gg.fwd*side).mean()*1e4) if len(gg) else np.nan)
 else:
  q=d.set_index("dt").px.resample("1h").last().dropna().to_frame("px");q["prev"]=q.px.pct_change();q["fwd"]=q.px.shift(-1)/q.px-1;q=q.dropna();g=q[q.index.hour==int(r.bucket)];side=1 if r["mode"]=="continuation" else -1;ret=pd.Series(np.sign(g.prev.values)*g.fwd.values*side,index=g.index)
  neigh=[]
  for b in [(int(r.bucket)-1)%24,(int(r.bucket)+1)%24]:
   gg=q[q.index.hour==b];rr=np.sign(gg.prev.values)*gg.fwd.values*side;neigh.append(float(np.mean(rr)*1e4) if len(rr) else np.nan)
 m=metrics(ret)
 # Pre-validation robustness gate: tail-independent positive expectancy + hit > 50%.
 passed=bool(m["n"]>=200 and m["mean_bp"]>0 and m["hit"]>.50 and m["trim1_bp"]>0 and m["trim2_bp"]>0 and m["remove_best5_bp"]>0)
 out.append({**r.to_dict(),**m,"neighbor_minus_bp":neigh[0],"neighbor_plus_bp":neigh[1],"ROBUST_PASS":passed})
 prog(i+2,14,f"{r.market} {r.mechanism} b={r.bucket}: mean={m['mean_bp']:.2f} trim2={m['trim2_bp']:.2f} best5={m['remove_best5_bp']:.2f} pass={passed}")
R=pd.DataFrame(out);R.to_csv(O/"ROBUSTNESS_ALL.csv",index=False);S=R[R.ROBUST_PASS].copy();S.to_csv(O/"V66_PREVALIDATION_SURVIVORS.csv",index=False)
ssha=hashlib.sha256((O/"V66_PREVALIDATION_SURVIVORS.csv").read_bytes()).hexdigest()
receipt={"run_id":rid,"status":"COMPLETE_PREVALIDATION_ROBUSTNESS","family":"04_INTRADAY_CALENDAR_STRUCTURE","input_sha256":sha,"tested":len(R),"passed":len(S),"survivor_sha256":ssha,"2018_plus_accessed":False,"next":"V66_IMMUTABLE_FREEZE" if len(S) else "CLOSE_LINEAGE"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(13,14,f"robust passed={len(S)}/{len(R)} sha={ssha[:12]}");prog(14,14,"HARD STOP before 2018+")
print();print("=== V65 RECEIPT ===");print(json.dumps(receipt,indent=2));print();print("=== ROBUST SURVIVORS ===");print(S.to_string(index=False) if len(S) else "NONE");print();print("RUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V65 compile failed"}
Write-Host "=== GEF V65 - INTRADAY/CALENDAR PREVALIDATION ROBUSTNESS ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V65 failed"}
