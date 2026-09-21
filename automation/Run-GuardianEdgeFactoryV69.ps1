param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v69_calendar_locked_oos.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,hashlib,time
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";PREV=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v68"
runs=sorted([p for p in PREV.glob("GEF68-*") if (p/"OOS_ELIGIBLE.csv").exists()])
if not runs:raise RuntimeError("No V68 eligible file")
P=runs[-1];fp=P/"OOS_ELIGIBLE.csv";EXPECTED="b5297dc335ade9748bdecf960c830e5701b8a00e417954f1a22f474846e43824"
sha=hashlib.sha256(fp.read_bytes()).hexdigest()
if sha!=EXPECTED:raise RuntimeError(f"V68 eligible SHA mismatch {sha}")
F=pd.read_csv(fp);assert len(F)==2
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v69";rid="GEF69-"+pd.Timestamp.utcnow().strftime("%Y%m%d-%H%M%S");O=BASE/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF69] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
# Freeze OOS gate before reading any OOS target return.
gate={"window":"2023-2025","eligible_sha256":EXPECTED,"requirements":{"n_min":100,"gross_bp_gt":0,"hit_gte":0.50,"positive_year_fraction_gte":2/3,"trim_best_1pct_bp_gt":0,"trim_best_2pct_bp_gt":0,"remove_best_5_events_bp_gt":0},"no_retuning":True,"protected_2026":"DO_NOT_OPEN"}
(O/"OOS_GATE_PREDECLARED.json").write_text(json.dumps(gate,indent=2));gsha=hashlib.sha256((O/"OOS_GATE_PREDECLARED.json").read_bytes()).hexdigest()
prog(1,7,f"AUTHORIZED LOCKED OOS; eligible SHA verified {sha[:12]}; gate frozen {gsha[:12]}")
def discover(sym):
 # Only inspect metadata/content from files whose parsed rows are 2023-2025; explicitly reject 2026.
 candidates=list(DL.rglob(f"*{sym}*.parquet"));usable=[]
 for p in candidates:
  try:
   d=pd.read_parquet(p);dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None);pc=next((c for c in d.columns if str(c).lower()=="close"),None)
   if dc is None and isinstance(d.index,pd.DatetimeIndex):d=d.reset_index();dc=d.columns[0]
   if dc is None or pc is None:continue
   dt=pd.to_datetime(d[dc],errors="coerce")
   if not dt.notna().any():continue
   if (dt.dt.year>=2026).any():continue
   x=pd.DataFrame({"dt":dt,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
   x=x[(x.dt.dt.year>=2023)&(x.dt.dt.year<=2025)]
   if len(x):usable.append((p,x))
  except Exception:continue
 if not usable:raise RuntimeError(f"MISSING_OOS_DATA {sym}: no 2023-2025 parquet found. STOP without candidate metrics.")
 x=pd.concat([z for _,z in usable]).sort_values("dt").drop_duplicates("dt")
 return x,[str(p) for p,_ in usable]
# Preflight BOTH markets before calculating either candidate, avoiding partial OOS result if data missing.
loaded={}
for sym in F.market:
 x,files=discover(sym);loaded[sym]=x
 print(f"[GEF69] preflight {sym}: rows={len(x):,} files={len(files)} min={x.dt.min()} max={x.dt.max()}",flush=True)
prog(2,7,"both OOS datasets present; 2026 rejected")
def calc(ret):
 ret=pd.Series(ret).dropna();n=len(ret);a=np.sort(ret.values)
 trim=lambda p:np.mean(a[:max(1,int(np.floor((1-p)*n)))])*1e4
 byy=ret.groupby(ret.index.year).mean()*1e4
 rm=ret.drop(ret.nlargest(min(5,n)).index)
 return {"n":n,"gross_bp":ret.mean()*1e4,"hit":(ret>0).mean(),"positive_year_fraction":(byy>0).mean(),"trim1_bp":trim(.01),"trim2_bp":trim(.02),"remove_best5_bp":rm.mean()*1e4,"year_2023_bp":byy.get(2023,np.nan),"year_2024_bp":byy.get(2024,np.nan),"year_2025_bp":byy.get(2025,np.nan)}
out=[]
for i,r in F.iterrows():
 d=loaded[r.market];q=d.set_index("dt").px.resample("1D").last().dropna().to_frame("px");q["fwd"]=q.px.shift(-1)/q.px-1;q=q.dropna();g=q[q.index.dayofweek==int(r.bucket)];side=1 if r["mode"]=="long" else -1;ret=pd.Series(g.fwd.values*side,index=g.index);m=calc(ret);req=gate["requirements"]
 passed=bool(m["n"]>=req["n_min"] and m["gross_bp"]>0 and m["hit"]>=req["hit_gte"] and m["positive_year_fraction"]>=req["positive_year_fraction_gte"] and m["trim1_bp"]>0 and m["trim2_bp"]>0 and m["remove_best5_bp"]>0)
 out.append({"market":r.market,"mechanism":r.mechanism,"bucket":int(r.bucket),"mode":r["mode"],**m,"OOS_PASS":passed})
 prog(3+i,7,f"{r.market}: n={m['n']} gross={m['gross_bp']:.2f} hit={m['hit']:.3f} trim2={m['trim2_bp']:.2f} pass={passed}")
R=pd.DataFrame(out);R.to_csv(O/"LOCKED_OOS_RESULTS.csv",index=False)
receipt={"run_id":rid,"status":"COMPLETE_LOCKED_OOS_2023_2025","family":"04_INTRADAY_CALENDAR_STRUCTURE","eligible_sha256":EXPECTED,"oos_gate_sha256":gsha,"tested":len(R),"passed":int(R.OOS_PASS.sum()),"protected_2026_accessed":False,"retuning":False,"post_oos_action":"STOP_FOR_INTERPRETATION"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(6,7,f"LOCKED OOS complete passed={receipt['passed']}/{len(R)}");prog(7,7,"HARD STOP; 2026 UNTOUCHED; NO RETUNING")
print();print("=== V69 RECEIPT ===");print(json.dumps(receipt,indent=2));print();print("=== LOCKED OOS RESULTS ===");print(R.to_string(index=False));print();print("RUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V69 compile failed"}
Write-Host "=== GEF V69 - LOCKED OOS 2023-2025 ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V69 failed"}
