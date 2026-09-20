param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v31_xag_robustness.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");RAW=ROOT/"DataLake"/"raw"/"histdata";V30=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v30";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v31";OUT.mkdir(parents=True,exist_ok=True)
started=time.time();rid="GEF31-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-started;eta=e/i*(n-i) if i else 0;print(f"[GEF31] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
runs=sorted([p for p in V30.glob("GEF30-*") if (p/"REPLICATION_SURVIVORS.csv").exists()]);F=pd.read_csv(runs[-1]/"REPLICATION_SURVIVORS.csv")
if len(F)!=7:raise RuntimeError(f"Expected 7 V30 survivors, got {len(F)}")
prog(1,10,"loaded exactly 7 V30 survivors")
z=[]
for y in range(2014,2018):
 p=RAW/"XAGUSD"/"M1"/f"XAGUSD_M1_{y}.parquet";d=pd.read_parquet(p);tc=next(c for c in d if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc]);z.append(d[["close"]].sort_index().resample("5min",label="right",closed="left").last().dropna())
a=pd.concat(z).sort_index().close
def makep(w,h,thr,delay=0):
 x=np.log(a/a.shift(w));sel=x[x.abs()>=thr];sig=-np.sign(sel);en=a.reindex(sig.index+pd.Timedelta(minutes=delay));ex=a.reindex(sig.index+pd.Timedelta(minutes=delay+h));en.index=sig.index;ex.index=sig.index;return (sig*np.log(ex/en)*1e4).dropna()
def nonover(p,h):
 if p.empty:return p
 keep=[];last=None
 for t in p.index:
  if last is None or t>=last+pd.Timedelta(minutes=h):keep.append(t);last=t
 return p.loc[keep]
rng=np.random.default_rng(31092026);rows=[]
for j,(_,r) in enumerate(F.iterrows(),1):
 w=int(r["window_bars"]);h=int(r["horizon_min"]);thr=float(r["threshold_abs"]);p=makep(w,h,thr);d5=makep(w,h,thr,5);d15=makep(w,h,thr,15)
 k=max(1,int(len(p)*.01));trim=p.drop(p.nlargest(k).index)
 daily=p.groupby(p.index.date).sum();best5=set(daily.nlargest(min(5,len(daily))).index);rm5=p[[d not in best5 for d in p.index.date]]
 no=nonover(p,h);yrs=p.groupby(p.index.year).mean()
 # Daily-block sign flip null, B=2000, preserves within-day PnL vectors.
 vals=daily.values;obs=float(p.mean());null=[]
 for _ in range(2000):
  signs=rng.choice([-1,1],len(vals));null.append(float((vals*signs).sum()/len(p)))
 nullp=(1+sum(x>=obs for x in null))/(2001)
 row={"window_bars":w,"window_min":w*5,"horizon_min":h,"tail":float(r["tail"]),"threshold_abs":thr,"direction":-1,"feature":"XAG_ret","n":len(p),"gross_bp":obs,"delay5":float(d5.mean()),"delay15":float(d15.mean()),"trim_best1pct":float(trim.mean()),"remove_best5days":float(rm5.mean()),"nonoverlap_n":len(no),"nonoverlap_bp":float(no.mean()),"posyears":float((yrs>0).mean()),"null_p":float(nullp)}
 row["robust_pass"]=bool(len(p)>=300 and min(row["gross_bp"],row["delay5"],row["delay15"],row["trim_best1pct"],row["remove_best5days"],row["nonoverlap_bp"])>0 and row["posyears"]>=.75 and row["null_p"]<=.05)
 rows.append(row);prog(j+1,10,f"{j}/7 w={w} H={h} P{row['tail']*100:g} gross={obs:.3f} trim={row['trim_best1pct']:.3f} no={row['nonoverlap_bp']:.3f} p={nullp:.4f} {'PASS' if row['robust_pass'] else 'FAIL'}")
R=pd.DataFrame(rows);R.to_csv(O/"ROBUSTNESS_RESULTS.csv",index=False);P=R[R.robust_pass].copy();P.to_csv(O/"ROBUST_SURVIVORS.csv",index=False)
prog(9,10,f"robust survivors {len(P)}/7")
receipt={"run_id":rid,"status":"COMPLETE","source_v30":runs[-1].name,"period":"2014-2017 only","candidate_count":7,"robust_pass_count":len(P),"tests":["delay +5m","+15m","remove best 1% trades","remove best 5 days","non-overlap by horizon","year stability","2000 daily-block sign flips"],"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":[],"instruction":"STOP. Freeze robust survivors before validation."};(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(10,10,"STOP - 2018+ untouched");print("\n=== V31 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== ROBUSTNESS RESULTS ===");print(R.to_string(index=False));print("\n=== ROBUST SURVIVORS ===");print(P.to_string(index=False));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V31 compile failed"}
Write-Host "=== GEF V31 - XAG PRE-VALIDATION ROBUSTNESS ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V31 failed"}
