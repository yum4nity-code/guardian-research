param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v4.py"
$code=@'
from pathlib import Path
import pandas as pd, numpy as np, json, time
from scipy.stats import spearmanr
from datetime import datetime, timezone

ROOT=Path(r"D:\MT5_Backtests")
V3B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v3"
OUTB=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v4"; OUTB.mkdir(parents=True,exist_ok=True)
CACHE=V3B/"cache5"
t0=time.time()

def status(out,stage,i,n,msg=""):
    e=time.time()-t0; eta=e/i*(n-i) if i else None
    d={"stage":stage,"done":i,"total":n,"pct":round(100*i/max(n,1),2),"elapsed_s":round(e,1),
       "eta_s":None if eta is None else round(eta,1),"message":msg,"updated_utc":datetime.now(timezone.utc).isoformat()}
    (out/"STATUS.json").write_text(json.dumps(d,indent=2))
    print(f"[GEF4] {stage:<20} {i}/{n} {d['pct']:6.2f}% | elapsed {e/60:6.1f}m | ETA {'--' if eta is None else f'{eta/60:.1f}m'} | {msg}",flush=True)

runs=[]
for p in V3B.glob("GEF3-*"):
    r=p/"RUN_RECEIPT.json"
    if r.exists():
        j=json.loads(r.read_text())
        if j.get("status")=="COMPLETE" and not j.get("locked_oos_2023_2025_accessed") and not j.get("protected_2026_accessed"):
            runs.append((p.stat().st_mtime,p,j))
if not runs: raise SystemExit("No COMPLETE V3")
_,V3,V3REC=sorted(runs)[-1]
rid="GEF4-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"); OUT=OUTB/rid; OUT.mkdir()
status(OUT,"LOAD",0,1,V3.name)

rep=pd.read_csv(V3/"AUTOPSY_cross_market_representatives.csv").sort_values("min_abs_ic",ascending=False)
ann=pd.read_csv(V3/"AUTOPSY_local_annual_stability.csv")
# bounded candidates: strongest 15 cross-market + strongest 20 local. No fishing expansion.
cross=rep.head(15).copy(); local=ann.head(20).copy()
status(OUT,"LOAD",1,1,f"cross={len(cross)} local={len(local)}")

def load(sym):
    p=CACHE/f"{sym}_2010_2022.parquet"
    z=pd.read_parquet(p); z.index=pd.to_datetime(z.index); return z.sort_index()
syms=sorted(set(cross.target)|set(cross.explain)|set(local.symbol))
D={s:load(s) for s in syms}

# Timestamp diagnostics: grid regularity, duplicate risk, common-timestamp coverage.
td=[]
for s,z in D.items():
    dif=z.index.to_series().diff().dt.total_seconds().div(60)
    td.append({"symbol":s,"rows":len(z),"duplicate_ts":int(z.index.duplicated().sum()),
               "pct_exact_5m":float((dif==5).mean()),"median_gap_min":float(dif.median()),
               "p99_gap_min":float(dif.quantile(.99))})
pd.DataFrame(td).to_csv(OUT/"timestamp_audit.csv",index=False)

def price_feature(z,name):
    c=z.close; k=int(str(name).split("_")[-1]); b=max(1,k//5)
    if str(name).startswith("ret_"): return np.log(c/c.shift(b))
    if str(name).startswith("z_"):
        m=c.rolling(b,min_periods=max(3,b//4)).mean(); sd=c.rolling(b,min_periods=max(3,b//4)).std()
        return (c-m)/sd.replace(0,np.nan)
    if str(name).startswith("rangepos_"):
        lo=c.rolling(b,min_periods=max(3,b//4)).min(); hi=c.rolling(b,min_periods=max(3,b//4)).max()
        return (c-lo)/(hi-lo).replace(0,np.nan)
    if str(name).startswith("rv_"): return np.log(c).diff().rolling(b,min_periods=max(3,b//4)).std()
    return None

def evaluate(x,y,years=range(2010,2023)):
    q=pd.concat([x.rename("x"),y.rename("y")],axis=1).dropna()
    if len(q)<1000:return None
    ic=float(spearmanr(q.x,q.y).statistic)
    # tails: only strongest 20% signals, direction learned from full PRE-OOS candidate sign, not optimized here
    a=q.x.abs().quantile(.80); tq=q[q.x.abs()>=a].copy()
    if len(tq):
        direction=-np.sign(tq.x) # mean-reversion interpretation for economic stress only
        gross=direction*tq.y
        med=float(gross.median()); mean=float(gross.mean()); hit=float((gross>0).mean())
    else: med=mean=hit=np.nan
    # remove best 1% absolute outcome events: anti-outlier stress
    cut=q.y.abs().quantile(.99); qr=q[q.y.abs()<=cut]
    ic_trim=float(spearmanr(qr.x,qr.y).statistic) if len(qr)>100 else np.nan
    return len(q),ic,len(tq),mean,med,hit,ic_trim

# Cross-market delay ladder. Keep candidates alive unless evidence says fragility.
delays=[5,10,15,30,60]
cr=[]; total=len(cross)*len(delays)
k=0
for _,r in cross.iterrows():
    t=D[r.target]; e=D[r.explain]
    h=int(r.h); hb=max(1,h//5)
    for delay in delays:
        k+=1
        q=t[["close"]].join(e[["r5"]],how="inner")
        # Original candidate used explanatory r5 delayed by candidate lag.
        effective=int(r.lag)+delay-5
        x=q.r5.shift(max(1,effective//5)); y=np.log(q.close.shift(-hb)/q.close)
        ev=evaluate(x,y)
        if ev:
            n,ic,nt,gm,gmed,hit,trim=ev
            cr.append({"target":r.target,"explain":r.explain,"base_lag":int(r.lag),"extra_delay":delay-5,
                       "effective_lag":effective,"h":h,"n":n,"ic":ic,"tail_n":nt,"tail_gross_mean_logret":gm,
                       "tail_gross_median_logret":gmed,"tail_hit":hit,"trim99_ic":trim})
        status(OUT,"CROSS DELAY",k,total,f"{r.target}<-{r.explain} efflag={effective}")
pd.DataFrame(cr).to_csv(OUT/"cross_delay_stress.csv",index=False)

# Local neighborhood/delay test, preserving feature definition and testing execution delay 0/5/10/15m.
lr=[]; total=len(local)*4;k=0
for _,r in local.iterrows():
    z=D[r.symbol]; f=price_feature(z,r.feature); h=int(r.h); hb=max(1,h//5)
    for d in [0,5,10,15]:
        k+=1; db=d//5
        # Signal formed at t; execution after d; outcome from execution to original horizon+d.
        x=f.shift(db); y=np.log(z.close.shift(-hb)/z.close)
        ev=evaluate(x,y)
        if ev:
            n,ic,nt,gm,gmed,hit,trim=ev
            lr.append({"symbol":r.symbol,"feature":r.feature,"h":h,"delay":d,"n":n,"ic":ic,"tail_n":nt,
                       "tail_gross_mean_logret":gm,"tail_gross_median_logret":gmed,"tail_hit":hit,"trim99_ic":trim})
        status(OUT,"LOCAL DELAY",k,total,f"{r.symbol} {r.feature} h={h} d={d}")
pd.DataFrame(lr).to_csv(OUT/"local_delay_stress.csv",index=False)

# Composite test: no parameter search. For each target where both local and cross exist,
# rank-normalize available signals and average signed mean-reversion votes.
comp=[]
targets=sorted(set(local.symbol)&set(cross.target))
for i,tgt in enumerate(targets,1):
    z=D[tgt]; signals=[]
    for _,r in local[local.symbol==tgt].head(3).iterrows():
        f=price_feature(z,r.feature)
        if f is not None: signals.append((-f.rank(pct=True)+.5).rename("s"))
    for _,r in cross[cross.target==tgt].head(3).iterrows():
        q=D[r.explain]["r5"].reindex(z.index)
        signals.append((-q.shift(max(1,int(r.lag)//5)).rank(pct=True)+.5).rename("s"))
    if len(signals)>=2:
        S=pd.concat(signals,axis=1).mean(axis=1)
        for h in [5,15,30,60]:
            y=np.log(z.close.shift(-(h//5))/z.close)
            ev=evaluate(-S,y) # evaluate() reverses sign for tails; -S restores composite vote economics
            if ev:
                n,ic,nt,gm,gmed,hit,trim=ev
                comp.append({"target":tgt,"signals":len(signals),"h":h,"n":n,"ic":ic,"tail_n":nt,
                             "tail_gross_mean_logret":gm,"tail_gross_median_logret":gmed,"tail_hit":hit,"trim99_ic":trim})
    status(OUT,"COMPOSITE",i,len(targets),tgt)
pd.DataFrame(comp).to_csv(OUT/"composite_fixed_vote.csv",index=False)

receipt={"run_id":rid,"status":"COMPLETE","source_v3_run":V3.name,"created_utc":datetime.now(timezone.utc).isoformat(),
 "research_max":"2022-12-31","locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,
 "cross_candidates":len(cross),"local_candidates":len(local),"cross_delay_tests":len(cr),"local_delay_tests":len(lr),
 "composite_tests":len(comp),"timestamp_symbols":len(td),"errors":[],
 "note":"V4 is a bounded robustness/economic-shape test. It is designed to measure survival, not to reject candidates by construction. No spread model is invented because source-specific historical bid/ask cost data is not present in this cache.",
 "next_gate":"Inspect delay decay, tail gross returns/hit rates, timestamp audit and fixed composites. Add defensible source-specific costs before any locked OOS opening."}
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
status(OUT,"COMPLETE",1,1,f"cross={len(cr)} local={len(lr)} composites={len(comp)}")
print("\n=== GEF V4 RECEIPT ===");print(json.dumps(receipt,indent=2));print("RUN:",OUT)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V4 compile failed"}
Write-Host "=== GUARDIAN EDGE FACTORY V4 ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V4 run failed"}
