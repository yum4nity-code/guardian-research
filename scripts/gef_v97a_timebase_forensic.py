from pathlib import Path
import pandas as pd
import numpy as np
import json
import math
import hashlib
import re
import time

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v97a_timebase"
BASE.mkdir(parents=True,exist_ok=True)

ENGINE_VERSION="V97A.0"
START=pd.Timestamp("2023-01-01 00:00")
END=pd.Timestamp("2025-12-31 23:55")
LAGS_MIN=list(range(-720,721,5))
HORIZONS=(5,30,60,120,240)

SPEC={
    "purpose":"forensic diagnosis of HistData-vs-FTMO timestamp alignment before interpreting V97 signal disagreement",
    "data":"reuse already-materialized V97 FTMO 2023-2025 parquet plus HistData 2023-2025; no MT5 query",
    "lag_scan_minutes":[-720,720,5],
    "common_lag_selection":"maximize equal-weight mean return correlation across all 5 markets and horizons 5/30/60/120/240",
    "strategy_outcomes_used_for_alignment":False,
    "candidate_selection_changed":False,
    "2026_accessed":False,
}

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def status(out,step,total,msg,**extra):
    payload={
        "engine_version":ENGINE_VERSION,
        "step":step,"steps":total,
        "percent":round(step/total*100,1),
        "timestamp_utc":pd.Timestamp.now("UTC").isoformat(),
        "message":msg,**extra,
    }
    write_json(out/"LIVE_STATUS.json",payload)
    tail=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF97A] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

def load_histdata_m1(sym):
    parts=[]
    for year in (2023,2024,2025):
        p=ROOT/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
        if not p.exists():
            raise RuntimeError(f"Missing HistData {p}")
        d=pd.read_parquet(p)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        pc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None and isinstance(d.index,pd.DatetimeIndex):
            d=d.reset_index(); dc=d.columns[0]
        if dc is None or pc is None:
            raise RuntimeError(f"Cannot identify datetime/close in {p}")
        # Preserve the exact convention used by the research lineage.
        utc=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(hours=5)
        q=pd.DataFrame({"utc":utc,"close":pd.to_numeric(d[pc],errors="coerce")}).dropna()
        q=q[(q["utc"]>=START)&(q["utc"]<pd.Timestamp("2026-01-01"))]
        parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    return q.set_index("utc")["close"]

def load_ftmo(v97,symbol):
    p=v97/f"FTMO_{symbol.replace('.','_')}_M1_2023_2025.parquet"
    if not p.exists():
        raise RuntimeError(f"Missing V97 materialized FTMO file {p}")
    d=pd.read_parquet(p)
    if "utc" not in d.columns or "close" not in d.columns:
        raise RuntimeError(f"Bad V97 FTMO parquet schema {p}")
    d["utc"]=pd.to_datetime(d["utc"],errors="coerce")
    d=d.dropna(subset=["utc","close"]).sort_values("utc").drop_duplicates("utc",keep="last")
    if (d["utc"]>=pd.Timestamp("2026-01-01")).any():
        raise RuntimeError(f"Protected 2026 row present in {p}")
    return pd.Series(pd.to_numeric(d["close"],errors="coerce").to_numpy(),index=d["utc"],name="close").dropna()

def five_minute(s,grid):
    return s.resample("5min",label="right",closed="left").last().reindex(grid)

def ret(px,mins):
    k=mins//5
    return px/px.shift(k)-1.0

def corr_at_shift(h,f,steps):
    # Positive steps means FTMO timestamps are shifted LATER to align to HistData.
    fs=f.shift(steps)
    a=h.to_numpy(dtype=np.float64)
    b=fs.to_numpy(dtype=np.float64)
    good=np.isfinite(a)&np.isfinite(b)
    n=int(good.sum())
    if n<100:
        return n,np.nan
    aa=a[good]; bb=b[good]
    aa=aa-aa.mean(); bb=bb-bb.mean()
    den=math.sqrt(float(np.dot(aa,aa))*float(np.dot(bb,bb)))
    if den<=0:
        return n,np.nan
    return n,float(np.dot(aa,bb)/den)

# Latest completed V97 only.
runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v97").glob("GEF97-*"))
runs=[
    p for p in runs
    if (p/"RUN_RECEIPT.json").exists()
    and json.loads((p/"RUN_RECEIPT.json").read_text(encoding="utf-8")).get("status")=="COMPLETE_V97_FTMO_HISTORICAL_BRIDGE"
]
if not runs:
    raise RuntimeError("No completed V97 run")
V97=runs[-1]
r97=json.loads((V97/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r97.get("2026_values_requested_or_stored"):
    raise RuntimeError("V97 receipt reports 2026 access")

RID="GEF97A-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID
OUT.mkdir(parents=True,exist_ok=False)
write_json(OUT/"V97A_TIMEBASE_FORENSIC_SPEC.json",SPEC)
status(OUT,1,8,"forensic spec frozen; using only already-stored 2023-2025 data",source_v97=V97.name)

symbol_map=r97["ftmo_symbols"]
markets=sorted(symbol_map)
grid=pd.date_range(START,END,freq="5min")

H={}
F={}
for i,src in enumerate(markets,1):
    H[src]=five_minute(load_histdata_m1(src),grid)
    F[src]=five_minute(load_ftmo(V97,symbol_map[src]),grid)
    print(f"[GEF97A] loaded {i}/{len(markets)} {src}->{symbol_map[src]}",flush=True)
status(OUT,2,8,"HistData and FTMO 5m grids loaded",markets=len(markets),rows=len(grid))

# Precompute returns.
RH={(m,h):ret(H[m],h) for m in markets for h in HORIZONS}
RF={(m,h):ret(F[m],h) for m in markets for h in HORIZONS}

scan=[]
t0=time.time()
for li,lag in enumerate(LAGS_MIN,1):
    steps=lag//5
    vals=[]
    for m in markets:
        for h in HORIZONS:
            n,c=corr_at_shift(RH[(m,h)],RF[(m,h)],steps)
            scan.append({
                "lag_minutes_ftmo_index_shift":lag,
                "market":m,
                "horizon_min":h,
                "n":n,
                "corr":c,
            })
            if np.isfinite(c):
                vals.append(c)
    if li%24==0 or li==len(LAGS_MIN):
        elapsed=time.time()-t0
        eta=elapsed/li*(len(LAGS_MIN)-li)
        print(f"[GEF97A] lag {li}/{len(LAGS_MIN)} | current={lag:+d}m | elapsed={elapsed/60:.1f}m eta={eta/60:.1f}m",flush=True)

S=pd.DataFrame(scan)
S.to_csv(OUT/"TIMEBASE_LAG_SCAN.csv",index=False)
status(OUT,3,8,"full +/-12h lag scan complete",tests=len(S))

# Best by market/horizon.
best_rows=[]
for (m,h),g in S.groupby(["market","horizon_min"],sort=True):
    gg=g.dropna(subset=["corr"]).sort_values(["corr","n"],ascending=[False,False])
    if gg.empty:
        continue
    b=gg.iloc[0]
    z=g[g["lag_minutes_ftmo_index_shift"]==0]
    best_rows.append({
        "market":m,
        "horizon_min":int(h),
        "best_lag_minutes_ftmo_index_shift":int(b["lag_minutes_ftmo_index_shift"]),
        "best_corr":float(b["corr"]),
        "best_n":int(b["n"]),
        "zero_lag_corr":float(z.iloc[0]["corr"]) if len(z) and np.isfinite(z.iloc[0]["corr"]) else np.nan,
    })
B=pd.DataFrame(best_rows)
B.to_csv(OUT/"TIMEBASE_BEST_BY_MARKET_HORIZON.csv",index=False)
status(OUT,4,8,"best lag by market/horizon computed",rows=len(B))

# Common lag chosen independent of strategy outcomes.
G=S.groupby("lag_minutes_ftmo_index_shift",as_index=False).agg(
    mean_corr=("corr","mean"),
    median_corr=("corr","median"),
    min_corr=("corr","min"),
    valid_tests=("corr","count"),
)
G=G.sort_values(["mean_corr","median_corr"],ascending=[False,False]).reset_index(drop=True)
G.to_csv(OUT/"TIMEBASE_COMMON_LAG_SCORE.csv",index=False)
best_common=int(G.iloc[0]["lag_minutes_ftmo_index_shift"])
status(
    OUT,5,8,
    "common lag selected from market returns only",
    best_common_lag_minutes=best_common,
    mean_corr=float(G.iloc[0]["mean_corr"]),
    min_corr=float(G.iloc[0]["min_corr"]),
)

# Monthly 30m forensic around the common lag and zero lag, plus per-month local best.
monthly=[]
for m in markets:
    hr=RH[(m,30)]
    fr=RF[(m,30)]
    for period in pd.period_range("2023-01","2025-12",freq="M"):
        mask=(grid.to_period("M")==period)
        hs=hr.where(mask)
        fs=fr.where(mask)
        local=[]
        for lag in LAGS_MIN:
            n,c=corr_at_shift(hs,fs,lag//5)
            if np.isfinite(c):
                local.append((c,n,lag))
        local.sort(reverse=True)
        n0,c0=corr_at_shift(hs,fs,0)
        nc,cc=corr_at_shift(hs,fs,best_common//5)
        monthly.append({
            "market":m,
            "month":str(period),
            "zero_lag_corr":c0,
            "common_lag_corr":cc,
            "common_lag_minutes":best_common,
            "local_best_lag_minutes":int(local[0][2]) if local else None,
            "local_best_corr":float(local[0][0]) if local else np.nan,
            "local_best_n":int(local[0][1]) if local else 0,
        })
M=pd.DataFrame(monthly)
M.to_csv(OUT/"TIMEBASE_MONTHLY_30M.csv",index=False)
status(OUT,6,8,"monthly lag stability forensic complete",rows=len(M))

zero=G[G["lag_minutes_ftmo_index_shift"]==0]
summary={
    "run_id":RID,
    "status":"COMPLETE_V97A_TIMEBASE_FORENSIC",
    "source_v97":V97.name,
    "markets":markets,
    "best_common_lag_minutes_ftmo_index_shift":best_common,
    "best_common_mean_corr":float(G.iloc[0]["mean_corr"]),
    "best_common_median_corr":float(G.iloc[0]["median_corr"]),
    "best_common_min_corr":float(G.iloc[0]["min_corr"]),
    "zero_lag_mean_corr":float(zero.iloc[0]["mean_corr"]) if len(zero) else None,
    "zero_lag_median_corr":float(zero.iloc[0]["median_corr"]) if len(zero) else None,
    "strategy_outcomes_used_for_alignment":False,
    "candidate_set_changed":False,
    "thresholds_retuned":False,
    "2026_accessed":False,
    "next":"HUMAN_REVIEW_TIMEBASE_BEFORE_ANY_FTMO_SIGNAL_CONCLUSION",
}
write_json(OUT/"RUN_RECEIPT.json",summary)
status(OUT,7,8,"receipt written; no strategy conclusion made")
status(OUT,8,8,"DONE; 2026 untouched")

print("\n=== V97A RECEIPT ===")
print(json.dumps(summary,indent=2))
print("\n=== V97A BEST LAG BY MARKET/HORIZON ===")
print(B.to_string(index=False))
print("\n=== V97A TOP COMMON LAGS ===")
print(G.head(12).to_string(index=False))
print("\nRUN:",OUT)
