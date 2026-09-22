from pathlib import Path
import pandas as pd
import numpy as np
import json
import math
from collections import Counter

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v97b_time_semantics"
BASE.mkdir(parents=True,exist_ok=True)

ENGINE_VERSION="V97B.0"
START=pd.Timestamp("2023-01-01 00:00")
END=pd.Timestamp("2025-12-31 23:55")
HORIZONS=(5,30,60,120,240)
HISTDATA_STORAGE_SHIFT_CANDIDATES_MIN=(0,300)

SPEC={
    "purpose":"freeze source timestamp semantics before correcting any strategy bridge",
    "inputs":"V97 materialized FTMO 2023-2025 + V97A lag scan + raw HistData parquets",
    "strategy_outcomes_used":False,
    "candidate_set_changed":False,
    "thresholds_retuned":False,
    "2026_accessed":False,
    "histdata_documented_semantics":"source files are fixed EST UTC-5 without DST; normal research conversion is +300 minutes",
    "selection_rule":"choose source-time interpretation using market-return concordance only, never strategy PnL",
}

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def status(out,step,total,msg,**extra):
    payload={
        "engine_version":ENGINE_VERSION,
        "step":step,"steps":total,"percent":round(100*step/total,1),
        "timestamp_utc":pd.Timestamp.now("UTC").isoformat(),
        "message":msg,**extra,
    }
    write_json(out/"LIVE_STATUS.json",payload)
    tail=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF97B] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

def corr(a,b):
    q=pd.concat([a.rename("a"),b.rename("b")],axis=1).dropna()
    if len(q)<100:
        return len(q),np.nan
    return len(q),float(q["a"].corr(q["b"]))

def ret(px,mins):
    k=mins//5
    return px/px.shift(k)-1.0

def load_raw_hist(sym):
    parts=[]
    metadata=[]
    for year in (2023,2024,2025):
        p=ROOT/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
        if not p.exists():
            raise RuntimeError(f"Missing {p}")
        d=pd.read_parquet(p)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        cc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None and isinstance(d.index,pd.DatetimeIndex):
            d=d.reset_index(); dc=d.columns[0]
        if dc is None or cc is None:
            raise RuntimeError(f"Cannot identify datetime/close in {p}")
        tt=pd.to_datetime(d[dc],errors="coerce")
        cl=pd.to_numeric(d[cc],errors="coerce")
        q=pd.DataFrame({"stored_time":tt,"close":cl}).dropna()
        q=q[q["stored_time"].dt.year==year].copy()
        metadata.append({
            "market":sym,"year":year,"rows":len(q),
            "first_stored":str(q["stored_time"].min()),
            "last_stored":str(q["stored_time"].max()),
            "datetime_column":str(dc),
        })
        parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("stored_time").drop_duplicates("stored_time",keep="last")
    return q.set_index("stored_time")["close"],metadata

def load_ftmo(v97,symbol):
    p=v97/f"FTMO_{symbol.replace('.','_')}_M1_2023_2025.parquet"
    if not p.exists():
        raise RuntimeError(f"Missing {p}")
    d=pd.read_parquet(p)
    d["utc"]=pd.to_datetime(d["utc"],errors="coerce")
    d["close"]=pd.to_numeric(d["close"],errors="coerce")
    d=d.dropna(subset=["utc","close"]).sort_values("utc").drop_duplicates("utc",keep="last")
    if (d["utc"]>=pd.Timestamp("2026-01-01")).any():
        raise RuntimeError(f"Protected 2026 row in {p}")
    return pd.Series(d["close"].to_numpy(),index=d["utc"],name="close")

# Latest completed V97.
v97_runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v97").glob("GEF97-*"))
v97_runs=[
    p for p in v97_runs
    if (p/"RUN_RECEIPT.json").exists()
    and json.loads((p/"RUN_RECEIPT.json").read_text(encoding="utf-8")).get("status")=="COMPLETE_V97_FTMO_HISTORICAL_BRIDGE"
]
if not v97_runs:
    raise RuntimeError("No completed V97")
V97=v97_runs[-1]
r97=json.loads((V97/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r97.get("2026_values_requested_or_stored"):
    raise RuntimeError("V97 reports 2026 access")

# Latest completed V97A matching latest V97.
v97a_runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v97a_timebase").glob("GEF97A-*"))
v97a_runs=[
    p for p in v97a_runs
    if (p/"RUN_RECEIPT.json").exists()
    and json.loads((p/"RUN_RECEIPT.json").read_text(encoding="utf-8")).get("status")=="COMPLETE_V97A_TIMEBASE_FORENSIC"
    and json.loads((p/"RUN_RECEIPT.json").read_text(encoding="utf-8")).get("source_v97")==V97.name
]
if not v97a_runs:
    raise RuntimeError("No completed V97A matching latest V97")
V97A=v97a_runs[-1]
r97a=json.loads((V97A/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r97a.get("2026_accessed"):
    raise RuntimeError("V97A reports 2026 access")

RID="GEF97B-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID
OUT.mkdir(parents=True,exist_ok=False)
write_json(OUT/"V97B_SOURCE_TIME_SPEC.json",SPEC)
status(OUT,1,8,"source-time forensic spec frozen; no strategy outcomes will be used",source_v97=V97.name,source_v97a=V97A.name)

B=pd.read_csv(V97A/"TIMEBASE_BEST_BY_MARKET_HORIZON.csv")
M=pd.read_csv(V97A/"TIMEBASE_MONTHLY_30M.csv")
if len(B)!=25:
    raise RuntimeError(f"Expected 25 market/horizon lag rows, found {len(B)}")

# The modal lag across market/horizon tests identifies the common cross-feed timebase.
counts=Counter(B["best_lag_minutes_ftmo_index_shift"].astype(int))
common_lag,count=counts.most_common(1)[0]
if count<15:
    raise RuntimeError(f"No dominant common FTMO timebase lag: {counts}")
status(OUT,2,8,"dominant cross-feed lag identified independently of strategy outcomes",common_lag_minutes=common_lag,support=f"{count}/25")

# Stability by market: all horizons should point to one lag.
market_lag_rows=[]
for market,g in B.groupby("market",sort=True):
    lc=Counter(g["best_lag_minutes_ftmo_index_shift"].astype(int))
    lag,n=lc.most_common(1)[0]
    if n<4:
        raise RuntimeError(f"{market}: lag not stable across horizons {lc}")
    monthly=M[M["market"]==market]
    mc=Counter(monthly["local_best_lag_minutes"].dropna().astype(int))
    monthly_mode,monthly_n=mc.most_common(1)[0] if mc else (None,0)
    market_lag_rows.append({
        "market":market,
        "horizon_mode_lag_min":int(lag),
        "horizon_mode_support":int(n),
        "residual_vs_common_min":int(lag-common_lag),
        "monthly_30m_mode_lag_min":int(monthly_mode) if monthly_mode is not None else None,
        "monthly_mode_support":int(monthly_n),
        "monthly_rows":int(len(monthly)),
    })
L=pd.DataFrame(market_lag_rows)
L.to_csv(OUT/"MARKET_TIMEBASE_RESIDUALS.csv",index=False)
status(OUT,3,8,"per-market residual lags summarized",markets=len(L))

grid=pd.date_range(START,END,freq="5min")
symbol_map=r97["ftmo_symbols"]
sem_rows=[]
file_meta=[]
selected_map={}

# Now test the only two plausible HistData storage semantics:
# 0m = stored timestamp already UTC-equivalent;
# +300m = documented raw HistData fixed EST -> UTC conversion.
for market in sorted(symbol_map):
    raw,meta=load_raw_hist(market)
    file_meta.extend(meta)
    ftmo=load_ftmo(V97,symbol_map[market])

    f5=ftmo.resample("5min",label="right",closed="left").last().reindex(grid)
    # Apply ONE common FTMO lag obtained from the 25 market/horizon tests.
    f5=f5.shift(common_lag//5)

    option_scores=[]
    for shift_min in HISTDATA_STORAGE_SHIFT_CANDIDATES_MIN:
        h=raw.copy()
        h.index=h.index+pd.Timedelta(minutes=shift_min)
        h5=h.resample("5min",label="right",closed="left").last().reindex(grid)
        cors=[]
        row={
            "market":market,
            "histdata_stored_time_shift_min":int(shift_min),
            "common_ftmo_index_shift_min":int(common_lag),
        }
        for horizon in HORIZONS:
            n,c=corr(ret(h5,horizon),ret(f5,horizon))
            row[f"ret{horizon}_n"]=int(n)
            row[f"ret{horizon}_corr"]=c
            if np.isfinite(c):
                cors.append(c)
        row["mean_corr"]=float(np.mean(cors)) if cors else np.nan
        row["min_corr"]=float(np.min(cors)) if cors else np.nan
        option_scores.append(row)
        sem_rows.append(row)

    opts=pd.DataFrame(option_scores).sort_values(["mean_corr","min_corr"],ascending=[False,False])
    best=opts.iloc[0]
    if not np.isfinite(best["mean_corr"]) or best["min_corr"]<0.85:
        raise RuntimeError(
            f"{market}: neither source-time interpretation produces robust concordance; "
            f"best={best.to_dict()}"
        )
    selected_map[market]=int(best["histdata_stored_time_shift_min"])
    print(
        f"[GEF97B] {market}: stored->aligned shift={selected_map[market]:+d}m "
        f"mean_corr={best['mean_corr']:.4f} min_corr={best['min_corr']:.4f}",
        flush=True,
    )

S=pd.DataFrame(sem_rows)
S.to_csv(OUT/"HISTDATA_STORAGE_SEMANTICS_OPTIONS.csv",index=False)
pd.DataFrame(file_meta).to_csv(OUT/"HISTDATA_RAW_FILE_TIMESTAMP_AUDIT.csv",index=False)
status(OUT,4,8,"raw HistData storage semantics tested against common FTMO timebase",selected=selected_map)

# Cross-check expected anomaly pattern from V97A.
expected_normal_shift=300
anomalies={m:s for m,s in selected_map.items() if s!=expected_normal_shift}
write_json(OUT/"HISTDATA_TIMESTAMP_SEMANTICS_FREEZE.json",{
    "run_id":RID,
    "status":"FROZEN_BEFORE_CORRECTED_STRATEGY_RESCORING",
    "common_ftmo_index_shift_min":int(common_lag),
    "histdata_stored_to_aligned_shift_min":selected_map,
    "normal_histdata_documented_shift_min":expected_normal_shift,
    "storage_semantics_anomalies":anomalies,
    "interpretation":(
        "A market at +300m matches documented HistData fixed EST storage. "
        "A market at 0m behaves as already UTC-equivalent in these local parquets. "
        "This is a source-time correction only, selected without strategy outcomes."
    ),
    "strategy_outcomes_used":False,
    "candidate_set_changed":False,
    "2026_accessed":False,
})
status(OUT,5,8,"corrected source-time map frozen before any strategy rescore",anomalies=anomalies)

# Explicitly document the implication for V93 without recomputing it here.
affected=[]
for rank in (3,5,9):
    if rank in (3,5):
        affected.append({
            "development_rank":rank,
            "reason":"uses USDCHF feature; any 2023-2025 USDCHF storage-time anomaly can change OOS signal timestamps",
        })
    else:
        affected.append({
            "development_rank":rank,
            "reason":"does not use USDCHF; still requires common HistData-vs-FTMO bridge alignment for feed comparison",
        })
write_json(OUT/"V93_IMPLICATIONS_BEFORE_RESCORE.json",{
    "affected_candidates":affected,
    "action":"do not reinterpret V93/V97 strategy evidence until corrected-time rescore is run",
    "retuning_allowed":False,
})
status(OUT,6,8,"V93 implications recorded; no strategy result recomputed")

receipt={
    "run_id":RID,
    "status":"COMPLETE_V97B_SOURCE_TIME_SEMANTICS_FREEZE",
    "engine_version":ENGINE_VERSION,
    "source_v97":V97.name,
    "source_v97a":V97A.name,
    "common_ftmo_index_shift_min":int(common_lag),
    "common_lag_support_tests":int(count),
    "histdata_stored_to_aligned_shift_min":selected_map,
    "storage_semantics_anomalies":anomalies,
    "strategy_outcomes_used_for_alignment":False,
    "candidate_set_changed":False,
    "thresholds_retuned":False,
    "2026_accessed":False,
    "next":"RUN_CORRECTED_TIME_RESCORE_OF_FROZEN_3_ONLY; DO_NOT_RETUNE; KEEP_2026_CLOSED",
}
write_json(OUT/"RUN_RECEIPT.json",receipt)
status(OUT,7,8,"receipt written")
status(OUT,8,8,"DONE; 2026 untouched")

print("\n=== V97B RECEIPT ===")
print(json.dumps(receipt,indent=2))
print("\n=== V97B MARKET TIMEBASE RESIDUALS ===")
print(L.to_string(index=False))
print("\n=== V97B HISTDATA STORAGE SEMANTICS OPTIONS ===")
show=["market","histdata_stored_time_shift_min","mean_corr","min_corr"]+[f"ret{h}_corr" for h in HORIZONS]
print(S[show].sort_values(["market","mean_corr"],ascending=[True,False]).to_string(index=False))
print("\nRUN:",OUT)
