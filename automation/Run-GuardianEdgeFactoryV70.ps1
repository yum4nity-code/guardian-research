param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v70_usdchf_execution_forensic.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,hashlib,time
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";SRC=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v69"
runs=sorted([p for p in SRC.glob("GEF69-*") if (p/"LOCKED_OOS_RESULTS.csv").exists()])
if not runs:raise RuntimeError("No completed V69")
V69=runs[-1];R=pd.read_csv(V69/"LOCKED_OOS_RESULTS.csv")
x=R[(R.market=="USDCHF")&(R.OOS_PASS==True)]
if len(x)!=1:raise RuntimeError("Frozen USDCHF OOS survivor not found")
# V70 is diagnostic only: no new threshold/model selection and absolutely no 2026.
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v70";rid="GEF70-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");O=BASE/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF70] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
def load():
 z=[]
 for y in range(2010,2026):
  p=DL/"raw"/"histdata"/"USDCHF"/"M1"/f"USDCHF_M1_{y}.parquet"
  if not p.exists():raise RuntimeError(f"Missing {p}")
  d=pd.read_parquet(p);dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None);pc=next((c for c in d.columns if str(c).lower()=="close"),None)
  if dc is None and isinstance(d.index,pd.DatetimeIndex):d=d.reset_index();dc=d.columns[0]
  if dc is None or pc is None:raise RuntimeError(f"Unusable {p}")
  q=pd.DataFrame({"dt":pd.to_datetime(d[dc],errors="coerce"),"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
  if (q.dt.dt.year>=2026).any():raise RuntimeError("2026 contamination")
  z.append(q)
 return pd.concat(z).sort_values("dt").drop_duplicates("dt")
prog(1,8,"frozen survivor verified; loading USDCHF 2010-2025 only")
d=load();prog(2,8,f"M1 loaded rows={len(d):,} min={d.dt.min()} max={d.dt.max()}")
# Reconstruct EXACT frozen mechanism: last observed quote of each raw timestamp calendar day;
# Friday close -> next retained daily close. Do not redefine it after OOS.
q=d.set_index("dt").px.resample("1D").last().dropna().to_frame("entry_px");q["exit_px"]=q.entry_px.shift(-1);q["exit_dt"]=q.index.to_series().shift(-1);q["ret"]=q.exit_px/q.entry_px-1
g=q[(q.index.dayofweek==4)&q.ret.notna()].copy();g["entry_dt"]=g.index
g["hold_hours"]=(g.exit_dt-g.entry_dt).dt.total_seconds()/3600
g["entry_hour"]=g.entry_dt.dt.hour;g["exit_weekday"]=g.exit_dt.dt.dayofweek;g["exit_hour"]=g.exit_dt.dt.hour
g["year"]=g.entry_dt.dt.year;g["era"]=np.where(g.year<=2022,"PRE_2010_2022","OOS_2023_2025")
prog(3,8,f"exact Friday observations={len(g)}")
# Session semantics diagnostics.
sem=g.groupby("era").agg(n=("ret","size"),gross_bp=("ret",lambda s:s.mean()*1e4),hit=("ret",lambda s:(s>0).mean()),median_hold_h=("hold_hours","median"),min_hold_h=("hold_hours","min"),max_hold_h=("hold_hours","max"),entry_hour_mode=("entry_hour",lambda s:int(s.mode().iloc[0])),exit_weekday_mode=("exit_weekday",lambda s:int(s.mode().iloc[0])),exit_hour_mode=("exit_hour",lambda s:int(s.mode().iloc[0]))).reset_index()
sem.to_csv(O/"SESSION_SEMANTICS.csv",index=False)
# Exact holding-time / boundary distributions expose weekend-gap and DST/source-boundary dependence.
pd.crosstab(g.era,g.hold_hours).to_csv(O/"HOLD_HOURS_DISTRIBUTION.csv")
pd.crosstab(g.era,[g.entry_hour,g.exit_weekday,g.exit_hour]).to_csv(O/"BOUNDARY_DISTRIBUTION.csv")
prog(4,8,"session/weekend/DST boundary distributions written")
# Delay execution by available quotes after the frozen daily close: +1,+5,+15,+60 minutes.
# Diagnostic only; these variants cannot replace the frozen OOS result.
rows=[]
idx=d.set_index("dt").px
for delay in [1,5,15,60]:
 vals=[]
 for _,r in g.iterrows():
  a=idx[idx.index>=r.entry_dt+pd.Timedelta(minutes=delay)]
  b=idx[idx.index>=r.exit_dt+pd.Timedelta(minutes=delay)]
  if len(a) and len(b):
   # cap lookup to same nearby session, preventing arbitrary far-forward fill
   ad=a.index[0];bd=b.index[0]
   if ad<=r.entry_dt+pd.Timedelta(hours=2) and bd<=r.exit_dt+pd.Timedelta(hours=2):vals.append(float(b.iloc[0]/a.iloc[0]-1))
 s=pd.Series(vals,dtype=float);rows.append({"delay_min":delay,"n":len(s),"gross_bp":s.mean()*1e4 if len(s) else np.nan,"hit":(s>0).mean() if len(s) else np.nan})
pd.DataFrame(rows).to_csv(O/"EXECUTION_DELAY_DIAGNOSTIC.csv",index=False);prog(5,8,"execution-delay diagnostics complete")
# Cost break-even, no invented broker cost assumptions.
eras=[]
for era,h in g.groupby("era"):
 gross=h.ret.mean()*1e4
 eras.append({"era":era,"n":len(h),"gross_bp":gross,"roundtrip_break_even_cost_bp":gross,"net_if_1bp_cost":gross-1,"net_if_2bp_cost":gross-2,"net_if_3bp_cost":gross-3,"net_if_5bp_cost":gross-5})
pd.DataFrame(eras).to_csv(O/"COST_SENSITIVITY.csv",index=False);prog(6,8,"cost break-even table complete")
# Source continuity / missing-minute diagnostics around Friday last quote and next retained close.
diag=[]
for era,h in g.groupby("era"):
 diag.append({"era":era,"n":len(h),"hold_gt_48h_frac":float((h.hold_hours>48).mean()),"hold_gt_60h_frac":float((h.hold_hours>60).mean()),"hold_gt_72h_frac":float((h.hold_hours>72).mean()),"unique_entry_hours":sorted(map(int,h.entry_hour.unique())),"unique_exit_weekdays":sorted(map(int,h.exit_weekday.unique())),"unique_exit_hours":sorted(map(int,h.exit_hour.unique()))})
(O/"SOURCE_BOUNDARY_DIAGNOSTIC.json").write_text(json.dumps(diag,indent=2));prog(7,8,"source-boundary diagnostic complete")
receipt={"run_id":rid,"status":"COMPLETE_POST_OOS_EXECUTION_FORENSIC","market":"USDCHF","frozen_signal":"weekday=Friday, long, raw-calendar-day last close to next retained daily close","v69_run":V69.name,"retuning":False,"protected_2026_accessed":False,"outputs":["SESSION_SEMANTICS.csv","HOLD_HOURS_DISTRIBUTION.csv","BOUNDARY_DISTRIBUTION.csv","EXECUTION_DELAY_DIAGNOSTIC.csv","COST_SENSITIVITY.csv","SOURCE_BOUNDARY_DIAGNOSTIC.json"],"next":"INTERPRET_EXECUTABILITY_BEFORE_STRATEGY_DESIGN"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(8,8,"STOP; diagnostic only; 2026 untouched")
print("\n=== V70 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== SESSION SEMANTICS ===");print(sem.to_string(index=False));print("\n=== EXECUTION DELAY ===");print(pd.DataFrame(rows).to_string(index=False));print("\n=== COST SENSITIVITY ===");print(pd.DataFrame(eras).to_string(index=False));print("\n=== SOURCE BOUNDARY ===");print(json.dumps(diag,indent=2));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V70 compile failed"}
Write-Host "=== GEF V70 - USDCHF POST-OOS EXECUTION FORENSIC ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V70 failed"}
