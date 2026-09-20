param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v9.py"
$code=@'
from pathlib import Path
import pandas as pd, numpy as np, json, time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); B=ROOT/"Research"/"Autonomous"; V3B=B/"guardian_edge_factory_v3"; CACHE=V3B/"cache5"; OUTB=B/"guardian_edge_factory_v9"; OUTB.mkdir(parents=True,exist_ok=True)
D0=pd.Timestamp("2010-01-01"); D1=pd.Timestamp("2013-12-31 23:59:59"); t0=time.time()
PCTS=[.80,.85,.90,.925,.95,.975,.99]; DELAYS=[0,5,10,15]; H=60
def stat(o,s,i,n,m=""):
 e=time.time()-t0; eta=e/i*(n-i) if i else 0
 print(f"[GEF9] {s:<14} {i}/{n} {100*i/n:6.2f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {m}",flush=True)
 (o/"STATUS.json").write_text(json.dumps({"stage":s,"done":i,"total":n,"pct":100*i/n,"elapsed_s":e,"eta_s":eta,"message":m},indent=2))
v=[]
for p in V3B.glob("GEF3-*"):
 r=p/"RUN_RECEIPT.json"
 if r.exists():
  j=json.loads(r.read_text())
  if j.get("status")=="COMPLETE" and not j.get("locked_oos_2023_2025_accessed") and not j.get("protected_2026_accessed"):v.append((p.stat().st_mtime,p))
V3=sorted(v)[-1][1]; rid="GEF9-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"); OUT=OUTB/rid; OUT.mkdir()
annual=pd.read_csv(V3/"AUTOPSY_local_annual_stability.csv"); z=pd.read_parquet(CACHE/"GBPUSD_2010_2022.parquet").sort_index(); z.index=pd.to_datetime(z.index); dm=(z.index>=D0)&(z.index<=D1)
def back(c,m): q=c.copy();q.index=q.index+pd.Timedelta(minutes=m);return q.reindex(c.index)
def feat(name):
 c=z.close;k=int(name.split("_")[-1]);mp=max(3,k//20)
 if name.startswith("ret_"):return np.log(c/back(c,k))
 if name.startswith("z_"):
  a=c.rolling(f"{k}min",min_periods=mp);return (c-a.mean())/a.std().replace(0,np.nan)
 if name.startswith("rangepos_"):
  a=c.rolling(f"{k}min",min_periods=mp);lo=a.min();hi=a.max();return (c-lo)/(hi-lo).replace(0,np.nan)
def ecdf(x):
 a=np.sort(x[dm].dropna().to_numpy());v=x.to_numpy(float);o=np.full(len(v),np.nan);ok=np.isfinite(v);o[ok]=np.searchsorted(a,v[ok],side="right")/len(a)-.5;return pd.Series(o,index=x.index)
def fwd(c,m):q=c.copy();q.index=q.index-pd.Timedelta(minutes=m);return q.reindex(c.index)
y=np.log(fwd(z.close,H)/z.close)
top=annual[annual.symbol=="GBPUSD"].head(3)
comps={}
for _,r in top.iterrows():
 x=feat(r.feature); ic=x[dm].corr(y[dm],method="spearman"); comps[str(r.feature)]=(1 if ic>0 else -1)*ecdf(x)
score=pd.concat(comps,axis=1).mean(axis=1)
stat(OUT,"BUILD",1,1," + ".join(comps))
def trades(sc,pct,delay):
 thr=float(sc[dm].abs().quantile(pct)); s=sc[sc.abs()>=thr].dropna(); et=s.index+pd.Timedelta(minutes=delay);p0=z.close.reindex(et);p1=z.close.reindex(et+pd.Timedelta(minutes=H))
 a=[];nxt=pd.Timestamp.min
 for t,sg,x0,x1 in zip(et,s.to_numpy(),p0.to_numpy(),p1.to_numpy()):
  if t<nxt or not np.isfinite(sg*x0*x1) or x0<=0 or x1<=0:continue
  a.append((t,np.sign(sg)*np.log(x1/x0)*10000,np.sign(sg)));nxt=t+pd.Timedelta(minutes=H)
 return pd.DataFrame(a,columns=["time","bp","side"]),thr
rows=[]; total=(len(comps)+1)*len(PCTS)*len(DELAYS);i=0
for name,sc in list(comps.items())+[("COMPOSITE",score)]:
 for p in PCTS:
  for d in DELAYS:
   i+=1;tr,thr=trades(sc,p,d)
   if len(tr):
    tr["year"]=tr.time.dt.year;day=tr.assign(day=tr.time.dt.date).groupby("day").bp.sum().sort_values(ascending=False);nb=tr[~tr.time.dt.date.isin(day.head(5).index)];cut=tr.bp.quantile(.99);tm=tr[tr.bp<=cut]
    rows.append({"component":name,"pct":p,"delay":d,"threshold":thr,"n":len(tr),"trades_year":len(tr)/13,"bp":tr.bp.mean(),"hit":(tr.bp>0).mean(),"long_fraction":(tr.side>0).mean(),"long_bp":tr.loc[tr.side>0,"bp"].mean(),"short_bp":tr.loc[tr.side<0,"bp"].mean(),"pos_years":(tr.groupby("year").bp.mean()>0).mean(),"trim1":tm.bp.mean(),"no5days":nb.bp.mean()})
   stat(OUT,"COMPONENTS",i,total,f"{name} p={p} d={d}")
R=pd.DataFrame(rows);R.to_csv(OUT/"component_threshold_delay.csv",index=False)
# Forensics on predeclared composite p90/d0 and p90/d15
forens=[]; hourly=[]; yearly=[]
for d in [0,15]:
 tr,thr=trades(score,.90,d);tr["year"]=tr.time.dt.year;tr["hour"]=tr.time.dt.hour
 for yr,g in tr.groupby("year"):yearly.append({"delay":d,"year":yr,"n":len(g),"bp":g.bp.mean(),"hit":(g.bp>0).mean()})
 for hr,g in tr.groupby("hour"):hourly.append({"delay":d,"hour":hr,"n":len(g),"bp":g.bp.mean(),"hit":(g.bp>0).mean()})
 for _,r in tr.nlargest(50,"bp").iterrows():
  forens.append({"delay":d,"time":r.time,"bp":r.bp,"side":r.side,"prev_gap_min":np.nan})
pd.DataFrame(yearly).to_csv(OUT/"p90_yearly.csv",index=False);pd.DataFrame(hourly).to_csv(OUT/"p90_hourly.csv",index=False);pd.DataFrame(forens).to_csv(OUT/"top50_winners.csv",index=False)
# matched block sign null for composite pcts/delays: 2000 reps each
rng=np.random.default_rng(2092026); nr=[]; tests=len(PCTS)*len(DELAYS);ii=0
for p in PCTS:
 for d in DELAYS:
  ii+=1;tr,_=trades(score,p,d);obs=tr.bp.mean();groups=[g.bp.to_numpy() for _,g in tr.assign(day=tr.time.dt.floor("D")).groupby("day")]; sims=[]
  for b in range(2000):
   sg=rng.choice([-1,1],len(groups));sims.append(np.concatenate([x*s for x,s in zip(groups,sg)]).mean())
  sims=np.array(sims);nr.append({"pct":p,"delay":d,"obs":obs,"null_p95":np.quantile(sims,.95),"p":(1+(sims>=obs).sum())/2001})
  stat(OUT,"MATCHED NULL",ii,tests,f"p={p} d={d}")
N=pd.DataFrame(nr);N.to_csv(OUT/"matched_null.csv",index=False)
receipt={"run_id":rid,"status":"COMPLETE","research_max":"2022-12-31","locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"target":"GBPUSD","horizon_min":60,"components":list(comps),"percentiles":[80,85,90,92.5,95,97.5,99],"delays":DELAYS,"null_reps":2000,"errors":[],"next_gate":"Choose no rule automatically. Inspect component breadth, neighboring thresholds, delays, years, long/short, hours and top winners. If robust, freeze one GBP60 local rule and perform final data-quality/cost audit before human OOS approval."}
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));stat(OUT,"COMPLETE",1,1,f"rows={len(R)}")
print("\n=== V9 RECEIPT ===");print(json.dumps(receipt,indent=2))
print("\n=== V9 COMPOSITE ===");print(R[R.component=="COMPOSITE"].to_string(index=False))
print("\n=== V9 COMPONENTS P90 ===");print(R[(R.pct==.90)&(R.delay.isin([0,15]))].to_string(index=False))
print("\n=== V9 MATCHED NULL ===");print(N.to_string(index=False))
print("\n=== V9 YEARLY P90 ===");print(pd.DataFrame(yearly).to_string(index=False))
print("\nRUN:",OUT)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V9 compile failed"}
Write-Host "=== GUARDIAN EDGE FACTORY V9 ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V9 run failed"}
