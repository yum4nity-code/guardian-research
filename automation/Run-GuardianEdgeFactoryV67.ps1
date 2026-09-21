param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v67_intraday_calendar_validation.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,time,json,hashlib
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";PREV=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v66"
runs=sorted([p for p in PREV.glob("GEF66-*") if (p/"V67_FROZEN_VALIDATION_CANDIDATES.csv").exists()])
if not runs:raise RuntimeError("No V66 freeze")
P=runs[-1];cf=P/"V67_FROZEN_VALIDATION_CANDIDATES.csv";gf=P/"V67_VALIDATION_GATE.json"
EC="e050ec17543acab6a9cff3a84f005844f18c2deef7d4b3bbea9eae01bd600dbe";EG="93eab4ef5f31b5f06a38ec1e197f29ac3c77653d705f4639293b31314afa5504"
if hashlib.sha256(cf.read_bytes()).hexdigest()!=EC:raise RuntimeError("candidate SHA mismatch")
if hashlib.sha256(gf.read_bytes()).hexdigest()!=EG:raise RuntimeError("gate SHA mismatch")
F=pd.read_csv(cf);G=json.loads(gf.read_text());BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v67";rid="GEF67-"+pd.Timestamp.utcnow().strftime("%Y%m%d-%H%M%S");O=BASE/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0
 print(f"[GEF67] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
def load(sym):
 z=[]
 for y in range(2018,2023):
  p=DL/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
  if not p.exists():continue
  d=pd.read_parquet(p);dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None);pc=next((c for c in d.columns if str(c).lower()=="close"),None)
  if dc is None and isinstance(d.index,pd.DatetimeIndex):d=d.reset_index();dc=d.columns[0]
  if dc is None or pc is None:continue
  z.append(pd.DataFrame({"dt":pd.to_datetime(d[dc],errors="coerce"),"px":pd.to_numeric(d[pc],errors="coerce")}).dropna())
 if not z:return None
 d=pd.concat(z).sort_values("dt").drop_duplicates("dt");assert d.dt.dt.year.min()>=2018 and d.dt.dt.year.max()<=2022;return d
def calc(ret):
 ret=pd.Series(ret).dropna();n=len(ret)
 if not n:return dict(n=0,gross_bp=np.nan,hit=np.nan,positive_year_fraction=0,trim1_bp=np.nan,trim2_bp=np.nan,remove_best5_bp=np.nan)
 a=np.sort(ret.values);t1=a[:max(1,int(np.floor(.99*n)))];t2=a[:max(1,int(np.floor(.98*n)))];rm=ret.drop(ret.nlargest(min(5,n)).index)
 py=ret.groupby(ret.index.year).mean()
 return dict(n=n,gross_bp=ret.mean()*1e4,hit=(ret>0).mean(),positive_year_fraction=(py>0).mean(),trim1_bp=np.mean(t1)*1e4,trim2_bp=np.mean(t2)*1e4,remove_best5_bp=rm.mean()*1e4)
prog(1,13,"SHA candidates+gate verified; VALIDATION ONLY 2018-2022")
cache={};out=[]
for i,r in F.iterrows():
 if r.market not in cache:cache[r.market]=load(r.market)
 d=cache[r.market]
 if d is None:m=calc(pd.Series(dtype=float))
 elif r.mechanism=="weekday":
  q=d.set_index("dt").px.resample("1D").last().dropna().to_frame("px");q["fwd"]=q.px.shift(-1)/q.px-1;q=q.dropna();g=q[q.index.dayofweek==int(r.bucket)];side=1 if r["mode"]=="long" else -1;m=calc(pd.Series(g.fwd.values*side,index=g.index))
 else:
  q=d.set_index("dt").px.resample("1h").last().dropna().to_frame("px");q["prev"]=q.px.pct_change();q["fwd"]=q.px.shift(-1)/q.px-1;q=q.dropna();g=q[q.index.hour==int(r.bucket)];side=1 if r["mode"]=="continuation" else -1;m=calc(pd.Series(np.sign(g.prev.values)*g.fwd.values*side,index=g.index))
 passed=bool(m["n"]>=G["n_min"] and m["gross_bp"]>0 and m["hit"]>=G["hit_gte"] and m["positive_year_fraction"]>=G["positive_year_fraction_gte"] and m["trim1_bp"]>0 and m["trim2_bp"]>0 and m["remove_best5_bp"]>0)
 out.append({**r.to_dict(),**m,"VALIDATION_PASS":passed})
 prog(i+2,13,f"{r.market} {r.mechanism} b={r.bucket}: n={m['n']} gross={m['gross_bp']:.2f} hit={m['hit']:.3f} trim2={m['trim2_bp']:.2f} pass={passed}")
R=pd.DataFrame(out);R.to_csv(O/"VALIDATION_ALL.csv",index=False);S=R[R.VALIDATION_PASS].copy();S.to_csv(O/"V68_VALIDATION_SURVIVORS.csv",index=False);ssha=hashlib.sha256((O/"V68_VALIDATION_SURVIVORS.csv").read_bytes()).hexdigest()
receipt={"run_id":rid,"status":"COMPLETE_INDEPENDENT_VALIDATION_2018_2022","family":"04_INTRADAY_CALENDAR_STRUCTURE","candidate_sha256":EC,"gate_sha256":EG,"tested":len(R),"passed":len(S),"survivor_sha256":ssha,"2023_plus_accessed":False,"next":"V68_FINAL_PREOOS_FORENSIC" if len(S) else "CLOSE_LINEAGE"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(12,13,f"validation passed={len(S)}/{len(R)} sha={ssha[:12]}");prog(13,13,"HARD STOP before 2023+")
print();print("=== V67 RECEIPT ===");print(json.dumps(receipt,indent=2));print();print("=== VALIDATION RESULTS ===");print(R.to_string(index=False));print();print("=== VALIDATION SURVIVORS ===");print(S.to_string(index=False) if len(S) else "NONE");print();print("RUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V67 compile failed"}
Write-Host "=== GEF V67 - INDEPENDENT VALIDATION 2018-2022 ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V67 failed"}
