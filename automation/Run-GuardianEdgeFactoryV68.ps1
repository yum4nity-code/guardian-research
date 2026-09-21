param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v68_intraday_calendar_forensic.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,hashlib,time
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";PREV=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v67"
runs=sorted([p for p in PREV.glob("GEF67-*") if (p/"V68_VALIDATION_SURVIVORS.csv").exists()])
if not runs:raise RuntimeError("No V67 survivors")
P=runs[-1];fp=P/"V68_VALIDATION_SURVIVORS.csv";EXPECTED="2a073a4d9e1bedecaad29e076213ea701185438603d0bf1d1751bda7022cc34c"
sha=hashlib.sha256(fp.read_bytes()).hexdigest()
if sha!=EXPECTED:raise RuntimeError(f"V67 survivor SHA mismatch {sha}")
F=pd.read_csv(fp);BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v68";rid="GEF68-"+pd.Timestamp.utcnow().strftime("%Y%m%d-%H%M%S");O=BASE/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF68] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
def load(sym):
 z=[]
 for y in range(2010,2023):
  p=DL/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
  if not p.exists():continue
  d=pd.read_parquet(p);dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None);pc=next((c for c in d.columns if str(c).lower()=="close"),None)
  if dc is None and isinstance(d.index,pd.DatetimeIndex):d=d.reset_index();dc=d.columns[0]
  if dc is None or pc is None:continue
  z.append(pd.DataFrame({"dt":pd.to_datetime(d[dc],errors="coerce"),"px":pd.to_numeric(d[pc],errors="coerce")}).dropna())
 d=pd.concat(z).sort_values("dt").drop_duplicates("dt");assert d.dt.dt.year.max()<=2022;return d
def m(ret):
 ret=pd.Series(ret).dropna();n=len(ret);a=np.sort(ret.values)
 trim=lambda p: np.mean(a[:max(1,int(np.floor((1-p)*n)))])*1e4
 byy=ret.groupby(ret.index.year).mean()*1e4
 # remove best 1/2% and best 10 events; yearly stability; bootstrap by year-block
 rng=np.random.default_rng(6801);years=sorted(ret.index.year.unique());boots=[]
 for _ in range(2000):
  ys=rng.choice(years,len(years),replace=True);parts=[ret[ret.index.year==y].values for y in ys];boots.append(np.mean(np.concatenate(parts))*1e4)
 return {"n":n,"gross_bp":ret.mean()*1e4,"hit":(ret>0).mean(),"trim1_bp":trim(.01),"trim2_bp":trim(.02),"trim3_bp":trim(.03),"remove_best10_bp":ret.drop(ret.nlargest(min(10,n)).index).mean()*1e4,"positive_year_fraction":(byy>0).mean(),"worst_year_bp":byy.min(),"year_bootstrap_lo_bp":float(np.quantile(boots,.025)),"year_bootstrap_hi_bp":float(np.quantile(boots,.975))}
prog(1,5,f"V67 SHA verified {sha[:12]}; forensic 2010-2022 only; 2023+ forbidden")
out=[]
for i,r in F.iterrows():
 d=load(r.market);q=d.set_index("dt").px.resample("1D").last().dropna().to_frame("px");q["fwd"]=q.px.shift(-1)/q.px-1;q=q.dropna();g=q[q.index.dayofweek==int(r.bucket)];side=1 if r["mode"]=="long" else -1;ret=pd.Series(g.fwd.values*side,index=g.index);x=m(ret)
 # deliberately stricter final gate before spending OOS
 passed=bool(x["n"]>=500 and x["gross_bp"]>0 and x["trim2_bp"]>0 and x["trim3_bp"]>0 and x["remove_best10_bp"]>0 and x["positive_year_fraction"]>=.65 and x["year_bootstrap_lo_bp"]>0)
 out.append({**r.to_dict(),**x,"FINAL_PREOOS_PASS":passed});prog(i+2,5,f"{r.market}: gross={x['gross_bp']:.2f} trim3={x['trim3_bp']:.2f} bootLO={x['year_bootstrap_lo_bp']:.2f} pass={passed}")
R=pd.DataFrame(out);R.to_csv(O/"FINAL_FORENSIC_ALL.csv",index=False);S=R[R.FINAL_PREOOS_PASS].copy();S.to_csv(O/"OOS_ELIGIBLE.csv",index=False);ssha=hashlib.sha256((O/"OOS_ELIGIBLE.csv").read_bytes()).hexdigest()
receipt={"run_id":rid,"status":"COMPLETE_FINAL_PREOOS_FORENSIC","family":"04_INTRADAY_CALENDAR_STRUCTURE","input_sha256":sha,"tested":len(R),"eligible":len(S),"eligible_sha256":ssha,"2023_plus_accessed":False,"oos_opened":False,"next":"HUMAN_REVIEW_BEFORE_LOCKED_OOS" if len(S) else "CLOSE_LINEAGE"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(4,5,f"eligible={len(S)}/{len(R)} sha={ssha[:12]}");prog(5,5,"STOP. LOCKED OOS NOT OPENED")
print();print("=== V68 RECEIPT ===");print(json.dumps(receipt,indent=2));print();print("=== FINAL FORENSIC ===");print(R.to_string(index=False));print();print("=== OOS ELIGIBLE ===");print(S.to_string(index=False) if len(S) else "NONE");print();print("RUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V68 compile failed"}
Write-Host "=== GEF V68 - FINAL PRE-OOS FORENSIC ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V68 failed"}
