param(
  [string]$Root = "D:\MT5_Backtests",
  [switch]$SkipRun
)
$ErrorActionPreference="Stop"
$DL=Join-Path $Root "DataLake"
$RunRoot=Join-Path $Root "Research\Autonomous\guardian_edge_factory_v1"
$Tools=Join-Path $DL "tools"
$Py=Join-Path $Tools "guardian_edge_factory_v1.py"
New-Item -ItemType Directory -Force -Path $RunRoot,(Join-Path $RunRoot "runs"),(Join-Path $RunRoot "cache"),(Join-Path $RunRoot "reports") | Out-Null
if(!(Test-Path $DL)){throw "DataLake missing: $DL"}

$pycode=@'
from pathlib import Path
import pandas as pd, numpy as np, json, hashlib, sys, traceback
from datetime import datetime, timezone

ROOT=Path(r"D:\MT5_Backtests")
DL=ROOT/"DataLake"
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v1"
RUNS=BASE/"runs"; CACHE=BASE/"cache"; REPORTS=BASE/"reports"
for p in (RUNS,CACHE,REPORTS): p.mkdir(parents=True,exist_ok=True)
run_id="GEF1-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
R=RUNS/run_id; R.mkdir()
ledger=[]; errors=[]

SYMS=["XAUUSD","XAGUSD","UDXUSD","EURUSD","GBPUSD","USDJPY","USDCHF","USDCAD","AUDUSD","SPXUSD","NSXUSD","WTIUSD","BCOUSD"]
H=[5,15,30,60,120,240]
DISC=("2010-01-01","2013-12-31"); REPL=("2014-01-01","2017-12-31"); VAL=("2018-01-01","2022-12-31")
CAP=pd.Timestamp("2022-12-31 23:59:59")

def fail(kind,msg):
    errors.append({"type":kind,"message":str(msg)})
    print(kind,":",msg)

def find_files(sym):
    p=DL/"raw"/"histdata"/sym/"M1"
    return sorted(p.glob(f"{sym}_M1_*.parquet")) if p.exists() else []

def load(sym):
    fs=find_files(sym)
    if not fs: raise FileNotFoundError(sym)
    parts=[]
    for f in fs:
        y=int(f.stem[-4:])
        if y>2022: continue
        x=pd.read_parquet(f)
        x.columns=[str(c).lower().strip() for c in x.columns]
        dt=next((c for c in ["datetime","timestamp","date","time"] if c in x.columns),None)
        if dt is None:
            for c in x.columns:
                if "date" in c or "time" in c: dt=c; break
        if dt is None: raise RuntimeError(f"{sym}: no datetime column in {f.name}")
        x["ts"]=pd.to_datetime(x[dt],errors="coerce")
        need=[c for c in ["open","high","low","close","volume"] if c in x.columns]
        if "close" not in need: raise RuntimeError(f"{sym}: close missing")
        parts.append(x[["ts"]+need])
    z=pd.concat(parts,ignore_index=True).dropna(subset=["ts"]).sort_values("ts").drop_duplicates("ts")
    if z["ts"].max()>CAP: raise RuntimeError(f"{sym}: post-2022 leakage")
    return z.set_index("ts")

def features(z):
    c=z["close"].astype(float); r=np.log(c).diff()
    f=pd.DataFrame(index=z.index)
    for k in [1,5,15,30,60,120,240,480,1440]:
        f[f"ret_{k}"]=np.log(c/c.shift(k))
    for k in [15,30,60,120,240,480,1440]:
        f[f"rv_{k}"]=r.rolling(k,min_periods=max(5,k//4)).std()*np.sqrt(k)
        m=c.rolling(k,min_periods=max(5,k//4)).mean()
        s=c.rolling(k,min_periods=max(5,k//4)).std()
        f[f"z_{k}"]=(c-m)/s.replace(0,np.nan)
    if {"high","low"}.issubset(z.columns):
        hi=z["high"].astype(float); lo=z["low"].astype(float)
        for k in [15,60,240,1440]:
            mx=hi.rolling(k,min_periods=max(5,k//4)).max(); mn=lo.rolling(k,min_periods=max(5,k//4)).min()
            f[f"rangepos_{k}"]=(c-mn)/(mx-mn).replace(0,np.nan)
    f["hour"]=f.index.hour; f["dow"]=f.index.dayofweek
    return f

def targets(z):
    c=z["close"].astype(float); t=pd.DataFrame(index=z.index)
    for h in H: t[f"fwd_{h}"]=np.log(c.shift(-h)/c)
    return t

def scan(sym,f,t):
    rows=[]
    for split,(a,b) in {"D":DISC,"R":REPL,"V":VAL}.items():
        mask=(f.index>=a)&(f.index<=b)
        for fc in [c for c in f.columns if c not in ("hour","dow")]:
            x=f.loc[mask,fc]
            for h in H:
                y=t.loc[mask,f"fwd_{h}"]
                q=pd.concat([x,y],axis=1).dropna()
                if len(q)<1000: continue
                # rank IC + extreme quintile directional effect
                ic=q.iloc[:,0].corr(q.iloc[:,1],method="spearman")
                lo,hi=q.iloc[:,0].quantile([.2,.8])
                yl=q.loc[q.iloc[:,0]<=lo].iloc[:,1]; yh=q.loc[q.iloc[:,0]>=hi].iloc[:,1]
                eff=float(yh.mean()-yl.mean())
                rows.append({"symbol":sym,"split":split,"feature":fc,"h":h,"n":len(q),"ic":float(ic) if pd.notna(ic) else np.nan,"effect":eff})
                ledger.append({"symbol":sym,"split":split,"feature":fc,"h":h,"trial_type":"univariate"})
    return rows

allrows=[]; loaded={}
for s in SYMS:
    try:
        print("LOAD",s)
        z=load(s); loaded[s]=z
        print(s,len(z),z.index.min(),z.index.max())
        f=features(z); t=targets(z)
        allrows += scan(s,f,t)
    except Exception as e:
        fail("INFRASTRUCTURE",f"{s}: {e}")

res=pd.DataFrame(allrows)
if res.empty:
    fail("INFRASTRUCTURE","No scan results")
else:
    # Freeze discovery ranking, then inspect same exact definitions in R/V.
    d=res[res.split=="D"].copy()
    d["score"]=d["ic"].abs()*np.sqrt(d["n"])
    top=d.sort_values("score",ascending=False).head(5000)
    keys=top[["symbol","feature","h"]]
    tri=keys.merge(res,on=["symbol","feature","h"],how="left")
    piv=tri.pivot_table(index=["symbol","feature","h"],columns="split",values=["ic","effect","n"],aggfunc="first").reset_index()
    piv.columns=["_".join([str(x) for x in c if str(x)!=""]) if isinstance(c,tuple) else c for c in piv.columns]
    # conservative sign replication, not a final scientific gate
    if {"ic_D","ic_R","ic_V"}.issubset(piv.columns):
        piv["same_sign_DRV"]=(np.sign(piv.ic_D)==np.sign(piv.ic_R))&(np.sign(piv.ic_D)==np.sign(piv.ic_V))
        piv["min_abs_ic"]=piv[["ic_D","ic_R","ic_V"]].abs().min(axis=1)
        surv=piv[piv.same_sign_DRV].sort_values("min_abs_ic",ascending=False)
    else: surv=piv.iloc[0:0]
    res.to_parquet(R/"all_univariate_trials.parquet",index=False)
    piv.to_csv(R/"top_discovery_replication_validation.csv",index=False)
    surv.head(1000).to_csv(R/"microedge_screen_survivors.csv",index=False)

    # Negative controls on a bounded sample: circularly shift target returns.
    null=[]
    rng=np.random.default_rng(20260919)
    for s,z in list(loaded.items())[:]:
        f=features(z)
        numeric=[c for c in f.columns if c not in ("hour","dow")]
        c=z["close"].astype(float)
        y=np.log(c.shift(-60)/c)
        m=(f.index>=DISC[0])&(f.index<=DISC[1])
        for fc in numeric[:20]:
            q=pd.concat([f.loc[m,fc],y.loc[m]],axis=1).dropna()
            if len(q)<1000: continue
            arr=q.iloc[:,1].to_numpy()
            for j in range(5):
                sh=int(rng.integers(max(100,len(arr)//10),max(101,len(arr)-100)))
                yn=np.roll(arr,sh)
                ic=pd.Series(q.iloc[:,0].to_numpy()).corr(pd.Series(yn),method="spearman")
                null.append({"symbol":s,"feature":fc,"control":j,"n":len(q),"abs_ic":abs(float(ic))})
                ledger.append({"symbol":s,"feature":fc,"h":60,"trial_type":"negative_control"})
    pd.DataFrame(null).to_csv(R/"negative_controls.csv",index=False)

pd.DataFrame(ledger).to_csv(R/"TRIAL_LEDGER.csv",index=False)
receipt={
 "run_id":run_id,"status":"COMPLETE" if not any(e["type"]=="INFRASTRUCTURE" and "No scan" in e["message"] for e in errors) else "FAILED",
 "created_utc":datetime.now(timezone.utc).isoformat(),"research_max":"2022-12-31",
 "locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,
 "symbols_requested":SYMS,"symbols_loaded":list(loaded),"horizons_minutes":H,
 "trial_count":len(ledger),"errors":errors,
 "note":"V1 broad causal own-market scanner + negative controls. Cross-market/macro composition is intentionally not claimed implemented by this bootstrap."
}
(R/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
print("\n=== GEF V1 RECEIPT ===")
print(json.dumps(receipt,indent=2))
print("RUN:",R)
print("STATUS:",receipt["status"])
'@
Set-Content -Path $Py -Value $pycode -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "GEF Python compile failed"}
$hash=(Get-FileHash $Py -Algorithm SHA256).Hash
Write-Host "GEF PY SHA256: $hash"

# pandas rank/Spearman correlation requires scipy.
# Do the probe/install in a child PowerShell so native stderr cannot trip this script's Stop policy.
$depCmd = @'
$ErrorActionPreference = "Continue"
py -c "import scipy" *> $null
if($LASTEXITCODE -ne 0){
  Write-Host "SciPy missing - installing..."
  py -m pip install --disable-pip-version-check scipy
  if($LASTEXITCODE -ne 0){ exit 31 }
}
py -c "import pandas, numpy, pyarrow, scipy; print('PYTHON DEPS OK')"
exit $LASTEXITCODE
'@
powershell -NoProfile -Command $depCmd
if($LASTEXITCODE -ne 0){ throw "Python dependency bootstrap failed with exit code $LASTEXITCODE" }

if(!$SkipRun){
  py $Py
  if($LASTEXITCODE -ne 0){throw "GEF run failed"}
}
