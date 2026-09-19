param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Tools=Join-Path $Root "DataLake\tools"
$Py=Join-Path $Tools "guardian_edge_factory_v3.py"
$pycode=@'
from pathlib import Path
import pandas as pd, numpy as np, json, time, gc
from scipy.stats import spearmanr
from datetime import datetime, timezone

ROOT=Path(r"D:\MT5_Backtests")
DL=ROOT/"DataLake"; V2BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v2"
OUTBASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v3"; OUTBASE.mkdir(parents=True,exist_ok=True)
SYMS=["XAUUSD","XAGUSD","UDXUSD","EURUSD","GBPUSD","USDJPY","USDCHF","USDCAD","AUDUSD","SPXUSD","NSXUSD","WTIUSD","BCOUSD"]
H=[5,15,30,60,120,240]; LAGS=[5,15,30,60,120]
CAP=pd.Timestamp("2022-12-31 23:59:59")
t0=time.time()
def prog(stage,i,n,msg=""):
    e=time.time()-t0; eta=e/i*(n-i) if i else np.nan
    fmt=lambda x:"--:--:--" if not np.isfinite(x) else f"{int(x//3600):02d}:{int(x%3600//60):02d}:{int(x%60):02d}"
    print(f"[GEF3] {stage:<22} {i:>5}/{n:<5} {100*i/max(n,1):6.2f}% | elapsed {fmt(e)} | ETA {fmt(eta)} | {msg}",flush=True)

# latest complete V2
v2s=[]
for p in V2BASE.glob("GEF2-*"):
    q=p/"RUN_RECEIPT.json"
    if q.exists():
        j=json.loads(q.read_text())
        if j.get("status")=="COMPLETE" and not j.get("locked_oos_2023_2025_accessed") and not j.get("protected_2026_accessed"): v2s.append((p.stat().st_mtime,p,j))
if not v2s: raise SystemExit("No eligible V2")
_,V2,V2REC=sorted(v2s)[-1]
run_id="GEF3-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"); OUT=OUTBASE/run_id; OUT.mkdir()
short=pd.read_csv(V2/"PRE_OOS_SHORTLIST_NOT_PROMOTED.csv")
prog("LOAD V2",1,1,f"{V2.name}; shortlist={len(short)}")

def load5(sym):
    p=DL/"raw"/"histdata"/sym/"M1"; fs=sorted(p.glob(f"{sym}_M1_*.parquet"))
    parts=[]
    for f in fs:
        try:y=int(f.stem[-4:])
        except:continue
        if y<2010 or y>2022: continue
        x=pd.read_parquet(f); x.columns=[str(c).lower() for c in x.columns]
        dt=next((c for c in ["datetime","timestamp","date","time"] if c in x.columns),None)
        if not dt or "close" not in x: raise RuntimeError(f"{sym}/{f.name}: schema")
        ts=pd.to_datetime(x[dt],errors="coerce")
        q=pd.DataFrame({"ts":ts,"close":pd.to_numeric(x.close,errors="coerce")}).dropna()
        parts.append(q)
    if not parts: raise RuntimeError(f"{sym}: no data")
    z=pd.concat(parts).drop_duplicates("ts").sort_values("ts").set_index("ts")
    if z.index.max()>CAP: raise RuntimeError(f"{sym}: LOCK VIOLATION")
    # 5-minute causal close: last observed close in completed 5m bucket.
    z=z.resample("5min").last().dropna()
    z["r5"]=np.log(z.close).diff()
    return z

# Cache 5m close/return for restartability
cache=OUTBASE/"cache5"; cache.mkdir(exist_ok=True)
data={}
for i,s in enumerate(SYMS,1):
    cp=cache/f"{s}_2010_2022.parquet"
    if cp.exists():
        z=pd.read_parquet(cp); z.index=pd.to_datetime(z.index)
    else:
        z=load5(s); z.to_parquet(cp)
    data[s]=z
    prog("5M CACHE",i,len(SYMS),f"{s} rows={len(z):,}")

# A) year-by-year stability for shortlist definitions, approximated on causal 5m grid.
# Only feature families representable from price are tested here.
def feat(z,name):
    c=z.close
    try:k=int(str(name).split("_")[-1])
    except:return None
    bars=max(1,k//5)
    if str(name).startswith("ret_"): return np.log(c/c.shift(bars))
    if str(name).startswith("z_"):
        m=c.rolling(bars,min_periods=max(3,bars//4)).mean(); sd=c.rolling(bars,min_periods=max(3,bars//4)).std()
        return (c-m)/sd.replace(0,np.nan)
    if str(name).startswith("rangepos_"):
        mn=c.rolling(bars,min_periods=max(3,bars//4)).min(); mx=c.rolling(bars,min_periods=max(3,bars//4)).max()
        return (c-mn)/(mx-mn).replace(0,np.nan)
    if str(name).startswith("rv_"): return z.r5.rolling(bars,min_periods=max(3,bars//4)).std()
    return None

yr=[]; tasks=short[["symbol","feature","h"]].drop_duplicates().to_dict("records")
for ti,r in enumerate(tasks,1):
    s=r["symbol"]; h=int(r["h"]); z=data.get(s)
    if z is None: continue
    f=feat(z,r["feature"])
    if f is None: continue
    y=np.log(z.close.shift(-(h//5))/z.close)
    q=pd.concat([f.rename("x"),y.rename("y")],axis=1).dropna()
    for year in range(2010,2023):
        a=q[q.index.year==year]
        if len(a)<500: continue
        ic=float(spearmanr(a.x,a.y).statistic)
        yr.append({"symbol":s,"feature":r["feature"],"h":h,"year":year,"n":len(a),"ic":ic})
    prog("YEAR STABILITY",ti,len(tasks),f"{s} {r['feature']} h={h}")
pd.DataFrame(yr).to_csv(OUT/"year_by_year_stability.csv",index=False)

# B) cross-market lead/lag discovery. Explanatory returns are strictly lagged.
# Discovery ranking is frozen before replication/validation evaluation.
splits={"D":("2010-01-01","2013-12-31"),"R":("2014-01-01","2017-12-31"),"V":("2018-01-01","2022-12-31")}
rows=[]; combos=[(t,e,l,h) for t in SYMS for e in SYMS if e!=t for l in LAGS for h in H]
for ci,(target,explain,lag,h) in enumerate(combos,1):
    a=data[target][["close"]].rename(columns={"close":"tc"})
    b=data[explain][["r5"]].rename(columns={"r5":"er"})
    q=a.join(b,how="inner")
    # lag >=5 means explanatory return known at least one completed 5m bar earlier
    q["x"]=q.er.shift(lag//5)
    q["y"]=np.log(q.tc.shift(-(h//5))/q.tc)
    for sp,(lo,hi) in splits.items():
        u=q.loc[lo:hi,["x","y"]].dropna()
        if len(u)<1000: continue
        ic=float(spearmanr(u.x,u.y).statistic)
        rows.append({"target":target,"explain":explain,"lag":lag,"h":h,"split":sp,"n":len(u),"ic":ic})
    if ci%25==0 or ci==len(combos): prog("CROSS MARKET",ci,len(combos),f"{target} <- {explain} lag={lag} h={h}")
cross=pd.DataFrame(rows); cross.to_parquet(OUT/"cross_market_all.parquet",index=False)

# Freeze candidates by Discovery only, then inspect exact definitions R/V.
d=cross[cross.split=="D"].copy(); d["score"]=d.ic.abs()*np.sqrt(d.n)
keys=d.sort_values("score",ascending=False).head(1000)[["target","explain","lag","h"]]
tri=keys.merge(cross,on=["target","explain","lag","h"],how="left")
p=tri.pivot_table(index=["target","explain","lag","h"],columns="split",values=["ic","n"],aggfunc="first").reset_index()
p.columns=["_".join([str(v) for v in c if str(v)!=""]) if isinstance(c,tuple) else c for c in p.columns]
if {"ic_D","ic_R","ic_V"}.issubset(p):
    p["same_sign_DRV"]=(np.sign(p.ic_D)==np.sign(p.ic_R))&(np.sign(p.ic_D)==np.sign(p.ic_V))
    p["min_abs_ic"]=p[["ic_D","ic_R","ic_V"]].abs().min(axis=1)
else:p["same_sign_DRV"]=False;p["min_abs_ic"]=np.nan
p.sort_values("min_abs_ic",ascending=False).to_csv(OUT/"cross_market_replication_table.csv",index=False)

# C) stronger circular block null on top 100 cross-market discovery definitions.
rng=np.random.default_rng(20260919); null=[]; top=keys.head(100).to_dict("records")
NNULL=20
for i,r in enumerate(top,1):
    q=data[r["target"]][["close"]].rename(columns={"close":"tc"}).join(data[r["explain"]][["r5"]].rename(columns={"r5":"er"}),how="inner")
    q["x"]=q.er.shift(int(r["lag"])//5); q["y"]=np.log(q.tc.shift(-(int(r["h"])//5))/q.tc)
    q=q.loc["2010-01-01":"2013-12-31",["x","y"]].dropna()
    xa=q.x.to_numpy(); ya=q.y.to_numpy(); n=len(q)
    for j in range(NNULL):
        sh=int(rng.integers(max(100,n//10),max(101,n-n//10)))
        null.append({**r,"control":j,"n":n,"abs_ic":abs(float(spearmanr(xa,np.roll(ya,sh)).statistic))})
    prog("BLOCK NULL",i,len(top),f"{r['target']}<-{r['explain']}")
pd.DataFrame(null).to_csv(OUT/"cross_market_block_null.csv",index=False)

# D) conservative summary, no OOS promotion.
stable=pd.DataFrame(yr)
ysum=[]
if not stable.empty:
    for k,g in stable.groupby(["symbol","feature","h"]):
        med=float(g.ic.median()); sign=np.sign(med)
        frac=float((np.sign(g.ic)==sign).mean()) if sign!=0 else 0
        ysum.append({"symbol":k[0],"feature":k[1],"h":k[2],"years":len(g),"median_ic":med,"sign_consistency":frac,"worst_abs_ic":float(g.ic.abs().min())})
pd.DataFrame(ysum).sort_values(["sign_consistency","worst_abs_ic"],ascending=False).to_csv(OUT/"year_stability_summary.csv",index=False)

receipt={
 "run_id":run_id,"status":"COMPLETE","source_v2_run":V2.name,
 "created_utc":datetime.now(timezone.utc).isoformat(),"research_max":"2022-12-31",
 "locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,
 "shortlist_input":len(short),"year_rows":len(yr),"cross_market_configurations":len(combos),
 "cross_market_trial_rows":len(cross),"cross_market_replicated_same_sign":int(p.same_sign_DRV.sum()),
 "block_null_trials":len(null),"errors":[],
 "warning":"PRE-OOS research only. No locked OOS access and no trading/deployment authorization.",
 "next_gate":"Inspect annual stability and cross-market real-vs-null yield; then incremental-information/composition and execution-cost stress."
}
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
prog("COMPLETE",1,1,f"cross same-sign={receipt['cross_market_replicated_same_sign']}")
print("\n=== GEF V3 RECEIPT ===");print(json.dumps(receipt,indent=2));print("RUN:",OUT)
'@
Set-Content $Py $pycode -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V3 compile failed"}
Write-Host "=== GUARDIAN EDGE FACTORY V3 ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V3 run failed"}
