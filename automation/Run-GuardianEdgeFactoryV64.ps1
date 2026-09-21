param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v64_intraday_calendar_replication.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,time,json,hashlib
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";PREV=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v63"
runs=sorted([p for p in PREV.glob("GEF63-*") if (p/"V64_FROZEN_CANDIDATES.csv").exists()])
if not runs:raise RuntimeError("No V63 frozen candidates")
P=runs[-1];fp=P/"V64_FROZEN_CANDIDATES.csv";EXPECTED="231cc4cac62d46c64f7ecf64423b500147a67a97bd76cc546c71af3625c31029"
sha=hashlib.sha256(fp.read_bytes()).hexdigest()
if sha!=EXPECTED:raise RuntimeError(f"V63 freeze SHA mismatch {sha}")
F=pd.read_csv(fp);BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v64";rid="GEF64-"+pd.Timestamp.utcnow().strftime("%Y%m%d-%H%M%S");O=BASE/rid;O.mkdir(parents=True,exist_ok=True)
t=time.time()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0
 print(f"[GEF64] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
def load(sym):
 z=[]
 for y in range(2014,2018):
  p=DL/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
  if not p.exists():continue
  d=pd.read_parquet(p);dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None);pc=next((c for c in d.columns if str(c).lower()=="close"),None)
  if dc is None and isinstance(d.index,pd.DatetimeIndex):d=d.reset_index();dc=d.columns[0]
  if dc is None or pc is None:continue
  x=pd.DataFrame({"dt":pd.to_datetime(d[dc],errors="coerce"),"px":pd.to_numeric(d[pc],errors="coerce")}).dropna();z.append(x)
 if not z:return None
 d=pd.concat(z).sort_values("dt").drop_duplicates("dt");assert d.dt.dt.year.min()>=2014 and d.dt.dt.year.max()<=2017;return d
prog(1,28,f"freeze verified sha={sha[:12]} candidates={len(F)}; REPLICATION ONLY 2014-2017")
cache={};out=[]
for i,r in F.iterrows():
 sym=r.market
 if sym not in cache:cache[sym]=load(sym)
 d=cache[sym]
 if d is None: vals={"n":0,"mean_bp":np.nan,"hit":np.nan,"positive_year_fraction":0}
 elif r.mechanism=="weekday":
  q=d.set_index("dt").px.resample("1D").last().dropna().to_frame("px");q["fwd"]=q.px.shift(-1)/q.px-1;q=q.dropna();g=q[q.index.dayofweek==int(r.bucket)];side=1 if r["mode"]=="long" else -1;ret=g.fwd*side
  yy=ret.groupby(ret.index.year).mean()
  vals={"n":len(ret),"mean_bp":ret.mean()*1e4,"hit":(ret>0).mean(),"positive_year_fraction":(yy>0).mean()}
 else:
  q=d.set_index("dt").px.resample("1h").last().dropna().to_frame("px");q["prev"]=q.px.pct_change();q["fwd"]=q.px.shift(-1)/q.px-1;q=q.dropna();g=q[q.index.hour==int(r.bucket)];side=1 if r["mode"]=="continuation" else -1;ret=np.sign(g.prev)*g.fwd*side;yy=pd.Series(ret.values,index=g.index).groupby(g.index.year).mean()
  vals={"n":len(ret),"mean_bp":ret.mean()*1e4,"hit":(ret>0).mean(),"positive_year_fraction":(yy>0).mean()}
 passed=bool(vals["n"]>=100 and vals["mean_bp"]>0 and vals["hit"]>=.51 and vals["positive_year_fraction"]>=.5)
 out.append({**r.to_dict(),**{f"rep_{k}":v for k,v in vals.items()},"REP_PASS":passed})
 prog(i+2,28,f"{sym} {r.mechanism} b={r.bucket} {r['mode']} n={vals['n']} mean={vals['mean_bp']:.2f}bp pass={passed}")
R=pd.DataFrame(out);R.to_csv(O/"REPLICATION_ALL.csv",index=False);S=R[R.REP_PASS].copy();S.to_csv(O/"V65_REPLICATION_SURVIVORS.csv",index=False)
ssha=hashlib.sha256((O/"V65_REPLICATION_SURVIVORS.csv").read_bytes()).hexdigest()
receipt={"run_id":rid,"status":"COMPLETE_REPLICATION_2014_2017","family":"04_INTRADAY_CALENDAR_STRUCTURE","input_freeze_sha256":sha,"tested":len(R),"passed":len(S),"survivor_sha256":ssha,"2018_plus_accessed":False,"next":"V65_ROBUSTNESS_OR_CLOSE"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(27,28,f"replication passed={len(S)}/{len(R)} survivor_sha={ssha[:12]}")
prog(28,28,"HARD STOP before 2018+")
print();print("=== V64 RECEIPT ===");print(json.dumps(receipt,indent=2))
print();print("=== REPLICATION SURVIVORS ===");print(S.to_string(index=False) if len(S) else "NONE")
print();print("RUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V64 compile failed"}
Write-Host "=== GEF V64 - INTRADAY/CALENDAR REPLICATION 2014-2017 ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V64 failed"}
