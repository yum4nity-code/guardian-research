param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v19_xag_preoos.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); RAW=ROOT/"DataLake"/"raw"/"histdata"; OUTB=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v19";OUTB.mkdir(parents=True,exist_ok=True)
started=time.time(); M="XAGUSD"; H=240; N=12; TAIL=.975; DIRECTION=-1
rid="GEF19-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUTB/rid;O.mkdir()
def prog(s,i,n,m=""):
 e=time.time()-started;eta=e/i*(n-i) if i else 0
 print(f"[GEF19] {s:<18} {i}/{n} {100*i/n:6.2f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {m}",flush=True)
 (O/"STATUS.json").write_text(json.dumps({"stage":s,"done":i,"total":n,"pct":100*i/n,"elapsed_s":e,"eta_s":eta,"message":m},indent=2))
def load(years):
 ys=[]
 for y in years:
  p=RAW/M/"M1"/f"{M}_M1_{y}.parquet"
  if not p.exists(): continue
  d=pd.read_parquet(p);tc=next(c for c in d.columns if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc])
  x=d[["open","high","low","close"]].sort_index()
  ys.append(x.resample("5min",label="right",closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna())
 return pd.concat(ys).sort_index()
prog("LOAD",1,7,"2010-2022 only")
d=load(range(2010,2023)); c=d.close.astype(float);lr=np.log(c/c.shift(1))
z=(lr-lr.rolling(N,min_periods=N).mean())/lr.rolling(N,min_periods=N).std()
disc=z[z.index.year<=2013].dropna();thr=float(disc.abs().quantile(TAIL))
sig=(DIRECTION*np.sign(z[z.abs()>=thr])).dropna()
def pnl(delay=0):
 ent=c.reindex(sig.index+pd.Timedelta(minutes=delay));ex=c.reindex(sig.index+pd.Timedelta(minutes=delay+H));ent.index=sig.index;ex.index=sig.index
 return (sig*np.log(ex/ent)*1e4).dropna()
p=pnl(0); prog("SIGNALS",2,7,f"n={len(p)} threshold={thr:.6f}")
# non-overlap sensitivity: retain first signal, then suppress entries until H elapsed
keep=[];last=None
for t in p.index:
 if last is None or t>=last+pd.Timedelta(minutes=H): keep.append(t);last=t
pn=p.loc[keep]
# concentration
year=p.groupby(p.index.year).agg(["count","mean","sum"]); month=p.groupby([p.index.year,p.index.month]).agg(["count","mean","sum"])
hour=p.groupby(p.index.hour).agg(["count","mean","sum"]); day=p.groupby(p.index.floor("D")).sum()
# extreme dependence both sides
ext=[]
for frac in [.001,.005,.01,.02,.05]:
 k=max(1,int(len(p)*frac));ext.append({"fraction":frac,"remove_best":float(p.drop(p.nlargest(k).index).mean()),"remove_worst":float(p.drop(p.nsmallest(k).index).mean()),"n_removed":k})
prog("CONCENTRATION",3,7,"year/month/hour/extremes")
# cost surface bp per completed trade
costs=[0,.25,.5,1,1.5,2,2.5,3]
costsurf=[{"cost_bp":x,"net_bp":float(p.mean()-x),"nonoverlap_net_bp":float(pn.mean()-x)} for x in costs]
# delays
delays=[{"delay_min":x,"gross_bp":float(pnl(x).mean()),"n":len(pnl(x))} for x in [0,5,10,15,30]]
prog("EXECUTION",4,7,"costs + delays + non-overlap")
# block bootstrap by day: resample days, preserving all within-day observations
blocks=[g.to_numpy() for _,g in p.groupby(p.index.floor("D"))];rng=np.random.default_rng(19001);B=5000;means=np.empty(B)
for b in range(B):
 idx=rng.integers(0,len(blocks),len(blocks));arr=np.concatenate([blocks[j] for j in idx]);means[b]=arr.mean()
ci=np.quantile(means,[.025,.05,.5,.95,.975]);probpos=float((means>0).mean())
prog("BOOTSTRAP",5,7,f"B={B} P(mean>0)={probpos:.3f}")
# leave-one-year-out descriptive stability
loyo=[]
for y in sorted(p.index.year.unique()):
 q=p[p.index.year!=y];loyo.append({"left_out":int(y),"mean_bp":float(q.mean()),"n":len(q)})
# best day concentration
total=float(p.sum()); top5=float(day.nlargest(5).sum()); top20=float(day.nlargest(20).sum())
summary={"candidate":"XAGUSD_zret12b_H240_P975_direction-1","threshold_frozen_2010_2013":thr,"period":"2010-2022","n":len(p),"gross_bp":float(p.mean()),"hit":float((p>0).mean()),"positive_year_fraction":float((year["mean"]>0).mean()),"nonoverlap_n":len(pn),"nonoverlap_gross_bp":float(pn.mean()),"bootstrap_B":B,"bootstrap_ci_95":[float(ci[0]),float(ci[4])],"bootstrap_prob_positive":probpos,"top5_days_sum_bp":top5,"top20_days_sum_bp":top20,"total_sum_bp":total}
pd.DataFrame(ext).to_csv(O/"EXTREME_DEPENDENCE.csv",index=False);pd.DataFrame(costsurf).to_csv(O/"COST_SURFACE.csv",index=False);pd.DataFrame(delays).to_csv(O/"DELAY_SURFACE.csv",index=False);year.to_csv(O/"BY_YEAR.csv");month.to_csv(O/"BY_MONTH.csv");hour.to_csv(O/"BY_HOUR.csv");pd.DataFrame(loyo).to_csv(O/"LEAVE_ONE_YEAR_OUT.csv",index=False);pd.DataFrame({"bootstrap_mean_bp":means}).to_parquet(O/"BOOTSTRAP.parquet",index=False)
prog("WRITE",6,7,"artifacts")
# Gate is intentionally demanding; no 2023+ access regardless.
ext1=next(x for x in ext if x["fraction"]==.01)
gate=bool(p.mean()>0 and pn.mean()>0 and ext1["remove_best"]>0 and probpos>=.975 and ci[0]>0 and pnl(15).mean()>0 and (year["mean"]>0).mean()>=.75)
receipt={"run_id":rid,"status":"COMPLETE","candidate":summary["candidate"],"pre_oos_period":"2010-2022","locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"summary":summary,"pre_oos_gate_pass":gate,"gate_rule":"gross>0; non-overlap>0; remove best1%>0; daily-block bootstrap P>0 >=.975 and 95% CI lower>0; delay15>0; >=75% positive years","important":"This is a pre-OOS diagnostic only. No tuning from these diagnostics is permitted before locked OOS.","next_gate":"If PASS: freeze exact rule/threshold/cost assumption and STOP for human approval before 2023-2025. If FAIL: do not open locked OOS; return to pre-2018 discovery families.","errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog("COMPLETE",7,7,f"gate={gate}")
print("\n=== V19 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== EXTREME DEPENDENCE ===");print(pd.DataFrame(ext).to_string(index=False));print("\n=== COST SURFACE ===");print(pd.DataFrame(costsurf).to_string(index=False));print("\n=== DELAYS ===");print(pd.DataFrame(delays).to_string(index=False));print("\n=== BY YEAR ===");print(year.to_string());print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V19 compile failed"}
Write-Host "=== GEF V19 - XAG PRE-OOS FORENSICS 2010-2022 ONLY ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V19 run failed"}
