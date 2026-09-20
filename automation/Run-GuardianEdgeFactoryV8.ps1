param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v8.py"
$code=@'
from pathlib import Path
import pandas as pd, numpy as np, json, time
from datetime import datetime, timezone
ROOT=Path(r"D:\MT5_Backtests"); V3B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v3"
OUTB=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v8"; OUTB.mkdir(parents=True,exist_ok=True); CACHE=V3B/"cache5"; t0=time.time()
DISC0=pd.Timestamp("2010-01-01"); DISC1=pd.Timestamp("2013-12-31 23:59:59")
SPECS={"XAUUSD":[5,15],"GBPUSD":[60]}; PCTS=[.95,.975,.99]; DELAYS=[0,5,10,15]; SLEEVES=["all","local","cross"]

def status(out,stage,i,n,msg=""):
 e=time.time()-t0; eta=e/i*(n-i) if i else None
 d={"stage":stage,"done":i,"total":n,"pct":round(100*i/max(n,1),2),"elapsed_s":round(e,1),"eta_s":None if eta is None else round(eta,1),"message":msg}
 (out/"STATUS.json").write_text(json.dumps(d,indent=2)); print(f"[GEF8] {stage:<15} {i}/{n} {d['pct']:6.2f}% | elapsed {e/60:.1f}m | ETA {'--' if eta is None else f'{eta/60:.1f}m'} | {msg}",flush=True)

v3=[]
for p in V3B.glob("GEF3-*"):
 r=p/"RUN_RECEIPT.json"
 if r.exists():
  j=json.loads(r.read_text())
  if j.get("status")=="COMPLETE" and not j.get("locked_oos_2023_2025_accessed") and not j.get("protected_2026_accessed"): v3.append((p.stat().st_mtime,p))
if not v3: raise SystemExit("No eligible V3")
V3=sorted(v3)[-1][1]; rid="GEF8-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"); OUT=OUTB/rid; OUT.mkdir()
cross=pd.read_csv(V3/"AUTOPSY_cross_market_representatives.csv"); annual=pd.read_csv(V3/"AUTOPSY_local_annual_stability.csv")
need=set(SPECS)|set(cross.target)|set(cross.explain)
D={s:pd.read_parquet(CACHE/f"{s}_2010_2022.parquet").sort_index() for s in need if (CACHE/f"{s}_2010_2022.parquet").exists()}
for z in D.values(): z.index=pd.to_datetime(z.index)
status(OUT,"LOAD",1,1,V3.name)

def exact_back(c,m):
 s=c.copy(); s.index=s.index+pd.Timedelta(minutes=m); return s.reindex(c.index)
def exact_fwd(c,m):
 s=c.copy(); s.index=s.index-pd.Timedelta(minutes=m); return s.reindex(c.index)
def feature(z,name):
 c=z.close; k=int(name.split("_")[-1]); mp=max(3,k//20)
 if name.startswith("ret_"): return np.log(c/exact_back(c,k))
 if name.startswith("z_"):
  a=c.rolling(f"{k}min",min_periods=mp); return (c-a.mean())/a.std().replace(0,np.nan)
 if name.startswith("rangepos_"):
  a=c.rolling(f"{k}min",min_periods=mp); lo=a.min(); hi=a.max(); return (c-lo)/(hi-lo).replace(0,np.nan)
def ecdf(x,dm):
 a=np.sort(x.loc[dm].dropna().to_numpy()); v=x.to_numpy(float); o=np.full(len(v),np.nan); ok=np.isfinite(v)
 o[ok]=np.searchsorted(a,v[ok],side="right")/len(a)-.5; return pd.Series(o,index=x.index)

F={}
for tgt in SPECS:
 z=D[tgt]; dm=(z.index>=DISC0)&(z.index<=DISC1); L=[]; C=[]
 for _,r in annual[annual.symbol==tgt].head(3).iterrows():
  x=feature(z,r.feature); y=np.log(exact_fwd(z.close,int(r.h))/z.close); sg=1 if x[dm].corr(y[dm],method="spearman")>0 else -1
  L.append((sg*ecdf(x,dm)).rename(str(r.feature)))
 for _,r in cross[cross.target==tgt].sort_values("min_abs_ic",ascending=False).head(3).iterrows():
  x=D[r.explain]["r5"].copy(); x.index=x.index+pd.Timedelta(minutes=int(r.lag)); x=x.reindex(z.index)
  y=np.log(exact_fwd(z.close,int(r.h))/z.close); sg=1 if x[dm].corr(y[dm],method="spearman")>0 else -1
  C.append((sg*ecdf(x,dm)).rename(f"{r.explain}@{int(r.lag)}"))
 F[tgt]={"local":pd.concat(L,axis=1).mean(axis=1),"cross":pd.concat(C,axis=1).mean(axis=1),"all":pd.concat(L+C,axis=1).mean(axis=1)}
status(OUT,"BUILD",1,1,"causal sleeves ready")

def trades_for(z,score,h,pct,delay):
 dm=(score.index>=DISC0)&(score.index<=DISC1); thr=float(score.loc[dm].abs().quantile(pct)); sig=score[score.abs()>=thr].dropna()
 ets=sig.index+pd.Timedelta(minutes=delay); p0=z.close.reindex(ets); p1=z.close.reindex(ets+pd.Timedelta(minutes=h))
 rec=[]; nxt=pd.Timestamp.min
 for et,s,a,b in zip(ets,sig.to_numpy(),p0.to_numpy(),p1.to_numpy()):
  if et<nxt or not(np.isfinite(s*a*b)) or a<=0 or b<=0: continue
  rec.append((et,np.sign(s)*np.log(b/a)*10000,np.sign(s))); nxt=et+pd.Timedelta(minutes=h)
 return pd.DataFrame(rec,columns=["time","bp","side"]),thr

rows=[]; contrib=[]; yearly=[]; total=sum(len(v) for v in SPECS.values())*len(SLEEVES)*len(PCTS)*len(DELAYS); k=0
for tgt,hs in SPECS.items():
 z=D[tgt]
 for h in hs:
  for sleeve in SLEEVES:
   score=F[tgt][sleeve]
   for pct in PCTS:
    for delay in DELAYS:
     k+=1; tr,thr=trades_for(z,score,h,pct,delay)
     if len(tr):
      tr["year"]=pd.to_datetime(tr.time).dt.year; tr["hour"]=pd.to_datetime(tr.time).dt.hour; eq=tr.bp.cumsum(); dd=float((eq-eq.cummax()).min())
      day=tr.assign(day=pd.to_datetime(tr.time).dt.date).groupby("day").bp.sum().sort_values(ascending=False); nob=tr[~pd.to_datetime(tr.time).dt.date.isin(set(day.head(5).index))]
      cut=tr.bp.quantile(.99); trim=tr[tr.bp<=cut]; ym=tr.groupby("year").bp.mean()
      rows.append({"target":tgt,"h":h,"sleeve":sleeve,"pct":pct,"delay":delay,"threshold":thr,"trades":len(tr),"trades_per_year":len(tr)/13,
       "gross_bp_trade":float(tr.bp.mean()),"median_bp":float(tr.bp.median()),"hit":float((tr.bp>0).mean()),"max_drawdown_bp":dd,
       "trim_best1pct_bp_trade":float(trim.bp.mean()),"remove_best5days_bp_trade":float(nob.bp.mean()),"positive_year_fraction":float((ym>0).mean())})
      for yr,g in tr.groupby("year"): yearly.append({"target":tgt,"h":h,"sleeve":sleeve,"pct":pct,"delay":delay,"year":int(yr),"n":len(g),"bp":float(g.bp.mean())})
      if delay==0 and sleeve=="all":
       totalbp=float(tr.bp.sum())
       for q in [.001,.005,.01,.02,.05]:
        n=max(1,int(np.ceil(len(tr)*q))); top=float(tr.nlargest(n,"bp").bp.sum())
        contrib.append({"target":tgt,"h":h,"pct":pct,"top_fraction":q,"n_top":n,"share_total_pnl":np.nan if totalbp==0 else top/totalbp,
                        "mean_without_top_bp":float(tr.drop(tr.nlargest(n,"bp").index).bp.mean())})
     status(OUT,"ROBUSTNESS",k,total,f"{tgt} h={h} {sleeve} p={pct} d={delay}")
R=pd.DataFrame(rows); Y=pd.DataFrame(yearly); Cn=pd.DataFrame(contrib)
R.to_csv(OUT/"robustness_grid.csv",index=False); Y.to_csv(OUT/"yearly.csv",index=False); Cn.to_csv(OUT/"tail_contribution.csv",index=False)

# Strategy-level circular block sign null: preserve absolute PnL/time clustering, randomize signs by 1-day blocks.
# Diagnostic only; 1000 reps per focal rule. Deterministic seed.
nullrows=[]; focals=[("XAUUSD",5,.99,0),("XAUUSD",15,.99,0),("XAUUSD",15,.99,5),("GBPUSD",60,.90,0),("GBPUSD",60,.90,15),("GBPUSD",60,.99,15)]
rng=np.random.default_rng(26092026)
for ii,(t,h,p,d) in enumerate(focals,1):
 tr,_=trades_for(D[t],F[t]["all"],h,p,d)
 if not len(tr): continue
 obs=float(tr.bp.mean()); dates=pd.to_datetime(tr.time).dt.floor("D"); groups=[g.bp.to_numpy() for _,g in tr.assign(day=dates).groupby("day")]
 sims=[]
 for b in range(1000):
  signs=rng.choice([-1,1],size=len(groups)); sims.append(float(np.concatenate([a*s for a,s in zip(groups,signs)]).mean()))
 sims=np.asarray(sims); pval=float((1+np.sum(sims>=obs))/(len(sims)+1))
 nullrows.append({"target":t,"h":h,"pct":p,"delay":d,"obs_bp":obs,"null_mean":float(sims.mean()),"null_p95":float(np.quantile(sims,.95)),"one_sided_p":pval})
 status(OUT,"BLOCK NULL",ii,len(focals),f"{t} h={h} p={p} d={d}")
N=pd.DataFrame(nullrows); N.to_csv(OUT/"strategy_block_null.csv",index=False)

receipt={"run_id":rid,"status":"COMPLETE","source_v3_run":V3.name,"research_max":"2022-12-31","locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,
"focus":["XAUUSD 5/15","GBPUSD 60"],"sleeves":SLEEVES,"percentiles":[95,97.5,99],"delays":[0,5,10,15],"robustness_tests":len(R),"null_reps_per_focal":1000,"errors":[],
"note":"Pre-OOS autopsy only. No rule promoted automatically.","next_gate":"Use sleeve attribution, delay stability, yearly stability, tail concentration and block-null diagnostics to predeclare at most 1-2 final rules. Then run one final cost/data-quality confirmation before human approval to open locked OOS."}
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2)); status(OUT,"COMPLETE",1,1,f"tests={len(R)}")
print("\n=== V8 RECEIPT ==="); print(json.dumps(receipt,indent=2))
print("\n=== V8 ALL-SLEEVE SUMMARY ==="); print(R[(R.sleeve=="all")][["target","h","pct","delay","trades_per_year","gross_bp_trade","hit","trim_best1pct_bp_trade","remove_best5days_bp_trade","positive_year_fraction"]].to_string(index=False))
print("\n=== V8 SLEEVE ATTRIBUTION delay0 ==="); print(R[(R.delay==0)&(R.pct==.99)][["target","h","sleeve","gross_bp_trade","hit","positive_year_fraction"]].to_string(index=False))
print("\n=== V8 TAIL CONTRIBUTION ==="); print(Cn.to_string(index=False))
print("\n=== V8 STRATEGY BLOCK NULL ==="); print(N.to_string(index=False))
print("\nRUN:",OUT)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V8 compile failed"}
Write-Host "=== GUARDIAN EDGE FACTORY V8 ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V8 run failed"}
