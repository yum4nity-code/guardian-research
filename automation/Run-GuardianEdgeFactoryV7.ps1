param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v7.py"
$code=@'
from pathlib import Path
import pandas as pd, numpy as np, json, time
from datetime import datetime, timezone
ROOT=Path(r"D:\MT5_Backtests"); V3B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v3"
OUTB=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v7"; OUTB.mkdir(parents=True,exist_ok=True)
CACHE=V3B/"cache5"; t0=time.time(); DISC0=pd.Timestamp("2010-01-01"); DISC1=pd.Timestamp("2013-12-31 23:59:59")
SPECS={"XAUUSD":[5,15],"EURUSD":[5],"GBPUSD":[5,60]}; PCTS=[.80,.90,.95,.975,.99]; DELAYS=[0,5,10,15]

def status(out,stage,i,n,msg=""):
 e=time.time()-t0; eta=e/i*(n-i) if i else None
 d={"stage":stage,"done":i,"total":n,"pct":round(100*i/max(n,1),2),"elapsed_s":round(e,1),"eta_s":None if eta is None else round(eta,1),"message":msg}
 (out/"STATUS.json").write_text(json.dumps(d,indent=2)); print(f"[GEF7] {stage:<16} {i}/{n} {d['pct']:6.2f}% | elapsed {e/60:.1f}m | ETA {'--' if eta is None else f'{eta/60:.1f}m'} | {msg}",flush=True)

v3=[]
for p in V3B.glob("GEF3-*"):
 r=p/"RUN_RECEIPT.json"
 if r.exists():
  j=json.loads(r.read_text())
  if j.get("status")=="COMPLETE" and not j.get("locked_oos_2023_2025_accessed") and not j.get("protected_2026_accessed"): v3.append((p.stat().st_mtime,p))
if not v3: raise SystemExit("No eligible V3")
V3=sorted(v3)[-1][1]; rid="GEF7-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"); OUT=OUTB/rid; OUT.mkdir()
cross=pd.read_csv(V3/"AUTOPSY_cross_market_representatives.csv"); annual=pd.read_csv(V3/"AUTOPSY_local_annual_stability.csv")
need=set(SPECS)|set(cross.target)|set(cross.explain)
D={s:pd.read_parquet(CACHE/f"{s}_2010_2022.parquet").sort_index() for s in need if (CACHE/f"{s}_2010_2022.parquet").exists()}
for z in D.values(): z.index=pd.to_datetime(z.index)
status(OUT,"LOAD",1,1,V3.name)

def exact_back(c,mins):
 s=c.copy(); s.index=s.index+pd.Timedelta(minutes=mins); return s.reindex(c.index)
def exact_fwd(c,mins):
 f=c.copy(); f.index=f.index-pd.Timedelta(minutes=mins); return f.reindex(c.index)
def feature(z,name):
 c=z.close; k=int(name.split("_")[-1])
 if name.startswith("ret_"): return np.log(c/exact_back(c,k))
 # exact trailing clock window, closed at current timestamp
 if name.startswith("z_"):
  m=c.rolling(f"{k}min",min_periods=max(3,k//20)).mean(); sd=c.rolling(f"{k}min",min_periods=max(3,k//20)).std()
  return (c-m)/sd.replace(0,np.nan)
 if name.startswith("rangepos_"):
  lo=c.rolling(f"{k}min",min_periods=max(3,k//20)).min(); hi=c.rolling(f"{k}min",min_periods=max(3,k//20)).max()
  return (c-lo)/(hi-lo).replace(0,np.nan)

def frozen_ecdf(x,disc):
 a=np.sort(x.loc[disc].dropna().to_numpy())
 if not len(a): return pd.Series(np.nan,index=x.index)
 v=x.to_numpy(dtype=float); out=np.full(len(v),np.nan); ok=np.isfinite(v)
 out[ok]=np.searchsorted(a,v[ok],side="right")/len(a)-.5
 return pd.Series(out,index=x.index)

# Exact-time raw components; direction and ECDF reference frozen on Discovery only.
F={}
for tgt in SPECS:
 z=D[tgt]; dm=(z.index>=DISC0)&(z.index<=DISC1); loc=[]; cro=[]
 for _,r in annual[annual.symbol==tgt].head(3).iterrows():
  x=feature(z,r.feature); y=np.log(exact_fwd(z.close,int(r.h))/z.close)
  ic=x[dm].corr(y[dm],method="spearman"); sg=1 if ic>0 else -1
  loc.append((sg*frozen_ecdf(x,dm)).rename(str(r.feature)))
 for _,r in cross[cross.target==tgt].sort_values("min_abs_ic",ascending=False).head(3).iterrows():
  src=D[r.explain]["r5"]; delayed=src.copy(); delayed.index=delayed.index+pd.Timedelta(minutes=int(r.lag)); x=delayed.reindex(z.index)
  y=np.log(exact_fwd(z.close,int(r.h))/z.close); ic=x[dm].corr(y[dm],method="spearman"); sg=1 if ic>0 else -1
  cro.append((sg*frozen_ecdf(x,dm)).rename(f"{r.explain}@{int(r.lag)}"))
 F[tgt]={"local":pd.concat(loc,axis=1).mean(axis=1),"cross":pd.concat(cro,axis=1).mean(axis=1),
         "all":pd.concat(loc+cro,axis=1).mean(axis=1)}
status(OUT,"BUILD",1,1,"exact-time + Discovery ECDF")

rows=[]; yearly=[]; total=sum(len(v) for v in SPECS.values())*len(PCTS)*len(DELAYS); k=0
for tgt,hs in SPECS.items():
 z=D[tgt]; base=F[tgt]["all"]; dm=(base.index>=DISC0)&(base.index<=DISC1)
 for h in hs:
  future=exact_fwd(z.close,h); raw=np.log(future/z.close)*10000
  for pct in PCTS:
   thr=float(base.loc[dm].abs().quantile(pct))
   for delay in DELAYS:
    k+=1
    # Signal observed at t, entry at exact t+delay. Position direction remains frozen signal direction.
    sig=base[base.abs()>=thr].dropna()
    entry_times=sig.index+pd.Timedelta(minutes=delay)
    entries=z.close.reindex(entry_times); exits=z.close.reindex(entry_times+pd.Timedelta(minutes=h))
    rec=[]; next_ok=pd.Timestamp.min
    for st,et,s,p0,p1 in zip(sig.index,entry_times,sig.to_numpy(),entries.to_numpy(),exits.to_numpy()):
     if et<next_ok or not (np.isfinite(s) and np.isfinite(p0) and np.isfinite(p1)) or p0<=0 or p1<=0: continue
     bp=np.sign(s)*np.log(p1/p0)*10000; rec.append((et,bp)); next_ok=et+pd.Timedelta(minutes=h)
    tr=pd.DataFrame(rec,columns=["time","bp"])
    if len(tr):
     tr["year"]=pd.to_datetime(tr.time).dt.year; cut=tr.bp.quantile(.99); trim=tr[tr.bp<=cut]
     day=tr.assign(day=pd.to_datetime(tr.time).dt.date).groupby("day").bp.sum().sort_values(ascending=False)
     nobest=tr[~pd.to_datetime(tr.time).dt.date.isin(set(day.head(5).index))]
     eq=tr.bp.cumsum(); dd=float((eq-eq.cummax()).min()); ym=tr.groupby("year").bp.mean()
     rows.append({"target":tgt,"h":h,"pct":pct,"delay":delay,"trades":len(tr),"trades_per_year":len(tr)/13,
      "gross_bp_trade":float(tr.bp.mean()),"median_bp_trade":float(tr.bp.median()),"hit":float((tr.bp>0).mean()),
      "max_drawdown_bp":dd,"trim_best1pct_bp_trade":float(trim.bp.mean()),"remove_best5days_bp_trade":float(nobest.bp.mean()),
      "positive_year_fraction":float((ym>0).mean()),"break_even_allin_cost_bp":max(0,float(tr.bp.mean()))})
     for yr,g in tr.groupby("year"): yearly.append({"target":tgt,"h":h,"pct":pct,"delay":delay,"year":int(yr),"trades":len(g),"gross_bp_trade":float(g.bp.mean())})
    status(OUT,"CAUSAL TEST",k,total,f"{tgt} h={h} p={pct} d={delay}")
R=pd.DataFrame(rows); Y=pd.DataFrame(yearly); R.to_csv(OUT/"causal_tail_delay.csv",index=False); Y.to_csv(OUT/"causal_yearly.csv",index=False)

# Diagnostics: delay-0 gradient + delay survival at fixed predeclared levels. No winner selection.
grows=[]
for (t,h),g in R[R.delay==0].groupby(["target","h"]):
 g=g.sort_values("pct"); yy=g.gross_bp_trade.to_numpy()
 grows.append({"target":t,"h":h,"bp80":float(g.iloc[0].gross_bp_trade),"bp99":float(g.iloc[-1].gross_bp_trade),
  "monotone_steps":int(np.sum(np.diff(yy)>=0)),"spearman":float(pd.Series(g.pct.to_numpy()).corr(pd.Series(yy),method="spearman")),
  "trim99":float(g.iloc[-1].trim_best1pct_bp_trade),"posyears99":float(g.iloc[-1].positive_year_fraction)})
G=pd.DataFrame(grows); G.to_csv(OUT/"causal_gradient.csv",index=False)

receipt={"run_id":rid,"status":"COMPLETE","source_v3_run":V3.name,"research_max":"2022-12-31",
"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,
"corrections":["Discovery-frozen empirical CDF; no full-sample percentile ranks","exact timestamp feature lags, forward horizons and execution delays","timestamp non-overlap"],
"specs":SPECS,"percentiles":[80,90,95,97.5,99],"delays_minutes":DELAYS,"tests":len(R),"errors":[],
"next_gate":"If causal gradients survive, inspect delay robustness and strategy-level null/cost confirmation; freeze rules before any locked OOS."}
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2)); status(OUT,"COMPLETE",1,1,f"tests={len(R)}")
print("\n=== V7 RECEIPT ==="); print(json.dumps(receipt,indent=2))
print("\n=== V7 CAUSAL GRADIENT DELAY 0 ==="); print(G.to_string(index=False))
print("\n=== V7 CAUSAL RESULTS ===")
print(R[["target","h","pct","delay","trades_per_year","gross_bp_trade","hit","trim_best1pct_bp_trade","remove_best5days_bp_trade","positive_year_fraction","break_even_allin_cost_bp"]].to_string(index=False))
print("\nRUN:",OUT)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V7 compile failed"}
Write-Host "=== GUARDIAN EDGE FACTORY V7 ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V7 run failed"}
