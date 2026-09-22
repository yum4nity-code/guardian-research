from pathlib import Path
import pandas as pd
import numpy as np
import json
import re
import hashlib

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v99_execution_reality"
BASE.mkdir(parents=True,exist_ok=True)

ENGINE_VERSION="V99.0"
MIN_FAST_STATE=5000
OOS_START=pd.Timestamp("2023-01-01 00:00")
OOS_END=pd.Timestamp("2025-12-31 23:55")
EXTRA_COST_SCENARIOS_BP=(0.0,0.10,0.25,0.50,1.00)
DXY_ALL_PLATFORM_TRADABLE_FROM=pd.Timestamp("2025-02-17 00:00")

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def status(out,step,total,msg,**extra):
    payload={
        "engine_version":ENGINE_VERSION,
        "step":step,"steps":total,"percent":round(step/total*100,1),
        "timestamp_utc":pd.Timestamp.now("UTC").isoformat(),
        "message":msg,**extra,
    }
    write_json(out/"LIVE_STATUS.json",payload)
    tail=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF99] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

def feature_market(feature):
    m=re.match(r"price_([A-Z]+)_",str(feature))
    return m.group(1) if m else None

def target_market(target):
    return str(target).split("_fwd_",1)[0]

def build_feature(name,P):
    m=re.fullmatch(r"price_([A-Z]+)_ret_(\d+)m",name)
    if m:
        sym,mins=m.group(1),int(m.group(2)); k=mins//5
        return (P[sym]/P[sym].shift(k)-1).astype("float64")
    m=re.fullmatch(r"price_([A-Z]+)_rv_(\d+)m",name)
    if m:
        sym,mins=m.group(1),int(m.group(2)); k=mins//5
        r5=P[sym].pct_change(1,fill_method=None)
        return r5.rolling(k,min_periods=max(3,k//2)).std().astype("float64")
    m=re.fullmatch(r"price_([A-Z]+)_zret_(\d+)m",name)
    if m:
        sym,mins=m.group(1),int(m.group(2)); k=mins//5
        r5=P[sym].pct_change(1,fill_method=None)
        mu=r5.rolling(k,min_periods=max(3,k//2)).mean()
        sd=r5.rolling(k,min_periods=max(3,k//2)).std().replace(0,np.nan)
        return ((r5-mu)/sd).astype("float64")
    m=re.fullmatch(r"price_([A-Z]+)_trend_(\d+)m",name)
    if m:
        sym,mins=m.group(1),int(m.group(2)); k=mins//5
        return (P[sym]/P[sym].shift(k)-1).astype("float64")
    raise RuntimeError(f"Unsupported feature {name}")

def causal_states(s,min_periods):
    s=pd.to_numeric(s,errors="coerce")
    mu=s.expanding(min_periods=min_periods).mean().shift(1)
    sd=s.expanding(min_periods=min_periods).std().shift(1).replace(0,np.nan)
    z=((s-mu)/sd).to_numpy(dtype=np.float64)
    finite=np.isfinite(z)
    return finite&(z<=-1.0),finite&(z>=1.0)

def infer_point(close):
    x=pd.to_numeric(close,errors="coerce").dropna().to_numpy(dtype=np.float64)
    if len(x)<100:
        return np.nan
    sample=x[::max(1,len(x)//200000)]
    for digits in range(1,8):
        scale=10.0**digits
        err=np.abs(sample*scale-np.round(sample*scale))
        if float(np.mean(err<1e-6))>=0.999:
            return 1.0/scale
    return np.nan

def load_hist(sym,years,time_map):
    parts=[]
    for year in years:
        if year>2025:
            raise RuntimeError("V99 refuses HistData 2026+")
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
        shift=300 if year<=2022 else int(time_map[sym])
        utc=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(minutes=shift)
        q=pd.DataFrame({"utc":utc,"close":pd.to_numeric(d[cc],errors="coerce")}).dropna()
        parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    return q.set_index("utc")["close"]

def summarize(x):
    a=np.asarray(x,dtype=np.float64)
    a=a[np.isfinite(a)]
    if not len(a):
        return {"n":0,"mean_bp":np.nan,"median_bp":np.nan,"win_rate_pct":np.nan}
    return {
        "n":int(len(a)),
        "mean_bp":float(np.mean(a)),
        "median_bp":float(np.median(a)),
        "win_rate_pct":float(np.mean(a>0)*100),
    }

# ---------- immutable inputs ----------
v97e_runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v97e_corrected_2026_freeze").glob("GEF97E-*"))
v97e_runs=[
    p for p in v97e_runs
    if (p/"RUN_RECEIPT.json").exists()
    and (p/"CORRECTED_2026_FORWARD_PANEL.csv").exists()
    and json.loads((p/"RUN_RECEIPT.json").read_text(encoding="utf-8")).get("status")=="COMPLETE_V97E_CORRECTED_2026_FREEZE"
]
if not v97e_runs:
    raise RuntimeError("No completed V97E")
V97E=v97e_runs[-1]
r97e=json.loads((V97E/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
panel_path=V97E/"CORRECTED_2026_FORWARD_PANEL.csv"
panel=pd.read_csv(panel_path)
if sha256(panel_path)!=r97e["frozen_panel_sha256"]:
    raise RuntimeError("V97E panel hash mismatch")
if sorted(panel["development_rank"].astype(int).tolist())!=[7,9]:
    raise RuntimeError("V99 expects frozen ranks [7,9]")
if r97e.get("2026_values_accessed"):
    raise RuntimeError("V97E reports 2026 access")

v98_runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v98_ftmo_corrected_bridge").glob("GEF98-*"))
v98_runs=[
    p for p in v98_runs
    if (p/"RUN_RECEIPT.json").exists()
    and (p/"CORRECTED_RANKS_7_9_FTMO_BRIDGE.csv").exists()
    and json.loads((p/"RUN_RECEIPT.json").read_text(encoding="utf-8")).get("status")=="COMPLETE_V98_CORRECTED_FTMO_BRIDGE"
]
if not v98_runs:
    raise RuntimeError("No completed V98")
V98=v98_runs[-1]
r98=json.loads((V98/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r98["source_v97e"]!=V97E.name:
    raise RuntimeError("V98 does not point to latest V97E")
if r98.get("2026_values_requested_or_stored"):
    raise RuntimeError("V98 reports 2026 access")
if r98["frozen_panel_sha256"]!=r97e["frozen_panel_sha256"]:
    raise RuntimeError("V98/V97E panel hash mismatch")

bridge98=pd.read_csv(V98/"CORRECTED_RANKS_7_9_FTMO_BRIDGE.csv")
if sorted(bridge98["development_rank"].astype(int).tolist())!=[7,9]:
    raise RuntimeError("V98 bridge ranks mismatch")

time_map={str(k):int(v) for k,v in r98["histdata_time_map_2023_2025"].items()}
common_shift=int(r98["common_ftmo_index_shift_min"])
symbols={str(k):str(v) for k,v in r98["ftmo_symbols"].items()}

# architecture foundation
v94_runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v94").glob("GEF94-*"))
v94_runs=[p for p in v94_runs if (p/"RUN_RECEIPT.json").exists()]
if not v94_runs:
    raise RuntimeError("No V94 lineage")
V94=v94_runs[-1]
r94=json.loads((V94/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V92=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v92"/r94["source_v92"]
r92=json.loads((V92/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V85=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v85"/r92["source_v85"]
design=json.loads((V85/"TRIAL_DESIGN.json").read_text(encoding="utf-8"))
V84C=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v84c"/design["source_v84c"]
r84=json.loads((V84C/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V83B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v83b"/r84["source_v83b"]
manifest=json.loads((V83B/"REPAIRED_ARCHITECTURE_MANIFEST.json").read_text(encoding="utf-8"))
Fhist=pd.read_parquet(manifest["price_state_5m_path"])
Fhist.index=pd.to_datetime(Fhist.index)

RID="GEF99-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID
OUT.mkdir(parents=True,exist_ok=False)

execution_spec={
    "run_id":RID,
    "status":"V99_EXECUTION_MODEL_FROZEN_BEFORE_SCORING",
    "source_v97e":V97E.name,
    "source_v98":V98.name,
    "frozen_ranks":[7,9],
    "entry":"first exact M1 bar open at the raw FTMO clock time corresponding to the completed 5m decision timestamp",
    "exit":"exact M1 bar open target_horizon minutes after entry; no optimized holding time",
    "price_side":{
        "LONG":"enter at ask=open_bid + entry_spread*point; exit at bid=open_bid",
        "SHORT":"enter at bid=open_bid; exit at ask=open_bid + exit_spread*point",
    },
    "missing_exact_entry_or_exit_bar":"operationally unavailable; do not forward-fill",
    "rank7_tradeability_constraint":"for non-demo/all-platform historical operability, require raw FTMO entry time >= 2025-02-17",
    "extra_roundtrip_cost_scenarios_bp":list(EXTRA_COST_SCENARIOS_BP),
    "purpose_of_extra_costs":"stress test commission/slippage/other friction without selecting a favorable cost",
    "news_filter_applied_historically":False,
    "news_reason":"current FTMO compliance is frozen as a live guard, not retrofitted to select historical winners",
    "candidate_set_changed":False,
    "thresholds_retuned":False,
    "2026_accessed":False,
}
write_json(OUT/"V99_EXECUTION_SPEC_FREEZE.json",execution_spec)
status(OUT,1,10,"execution model frozen before execution scoring",source_v98=V98.name)

# ---------- load FTMO M1 artifacts ----------
needed_markets=set()
for row in panel.to_dict("records"):
    needed_markets.add(feature_market(row["feature_i"]))
    needed_markets.add(feature_market(row["feature_j"]))
    needed_markets.add(target_market(row["target"]))
needed_markets.discard(None)

raw={}
for src in sorted(needed_markets):
    p=V98/f"FTMO_{symbols[src].replace('.','_')}_M1_2023_2025.parquet"
    if not p.exists():
        raise RuntimeError(f"Missing V98 FTMO artifact {p}")
    d=pd.read_parquet(p)
    required={"utc","open","close","spread"}
    if not required.issubset(d.columns):
        raise RuntimeError(f"{p} missing {sorted(required-set(d.columns))}")
    d["utc"]=pd.to_datetime(d["utc"],errors="coerce")
    for c in ("open","close","spread"):
        d[c]=pd.to_numeric(d[c],errors="coerce")
    d=d.dropna(subset=["utc","open","close"]).sort_values("utc").drop_duplicates("utc",keep="last")
    if (d["utc"]>=pd.Timestamp("2026-01-01")).any():
        raise RuntimeError(f"2026 leaked in {p}")
    raw[src]=d.set_index("utc")
status(OUT,2,10,"V98 bounded FTMO M1 artifacts loaded",markets=len(raw))

# ---------- reconstruct exact V98 FTMO state signals ----------
oos_grid=pd.date_range(OOS_START,OOS_END,freq="5min")
pre_grid=pd.date_range("2014-01-01 00:00","2022-12-31 23:55",freq="5min")
pre_warm=pd.date_range("2013-12-01 00:00","2022-12-31 23:55",freq="5min")
bridge_grid=pd.date_range("2022-12-01 00:00",OOS_END,freq="5min")

Ppre=pd.DataFrame(index=pre_warm)
for src in sorted(needed_markets):
    s=load_hist(src,range(2013,2023),time_map)
    Ppre[src]=s.resample("5min",label="right",closed="left").last().reindex(pre_warm)

Pf=pd.DataFrame(index=bridge_grid)
for src in sorted(needed_markets):
    warm=load_hist(src,[2022],time_map).resample("5min",label="right",closed="left").last()
    f5=raw[src]["close"].resample("5min",label="right",closed="left").last().reindex(oos_grid)
    f5=f5.shift(common_shift//5)
    Pf[src]=pd.concat([warm,f5]).sort_index().reindex(bridge_grid)

needed_features=sorted(set(panel["feature_i"]).union(set(panel["feature_j"])))
state_f={}
for feat in needed_features:
    pre=build_feature(feat,Ppre).reindex(pre_grid)
    foundation=pd.concat([pd.to_numeric(Fhist[feat],errors="coerce"),pd.to_numeric(pre,errors="coerce")])
    ff=build_feature(feat,Pf).reindex(oos_grid)
    full=pd.concat([foundation,pd.to_numeric(ff,errors="coerce")])
    lo,hi=causal_states(full,MIN_FAST_STATE)
    off=len(foundation)
    state_f[(feat,"LO")]=lo[off:]
    state_f[(feat,"HI")]=hi[off:]

# parity to V98 full FTMO signal counts
signal_masks={}
for row in panel.to_dict("records"):
    rank=int(row["development_rank"])
    mins=int(str(row["target"]).split("_fwd_",1)[1].rstrip("m"))
    sample=((oos_grid.view("int64")//60_000_000_000)%mins)==0
    mask=state_f[(row["feature_i"],row["state_i"])]&state_f[(row["feature_j"],row["state_j"])]&sample
    exp=int(bridge98.loc[bridge98["development_rank"].astype(int)==rank,"ftmo_signal_n_full"].iloc[0])
    got=int(mask.sum())
    if got!=exp:
        raise RuntimeError(f"V98 signal parity failed rank {rank}: got={got} expected={exp}")
    signal_masks[rank]=mask
status(OUT,3,10,"V98 FTMO full-signal parity exact",rank7=int(signal_masks[7].sum()),rank9=int(signal_masks[9].sum()))

# ---------- exact M1 execution ----------
trade_rows=[]
summary_rows=[]
for row in panel.to_dict("records"):
    rank=int(row["development_rank"])
    direction=str(row["direction"])
    target_src=target_market(row["target"])
    horizon=int(str(row["target"]).split("_fwd_",1)[1].rstrip("m"))
    m1=raw[target_src]
    point=infer_point(m1["close"])
    if not np.isfinite(point):
        raise RuntimeError(f"Cannot infer point for {target_src}")

    times=oos_grid[signal_masks[rank]]
    local=[]
    for aligned_t in times:
        # FTMO aligned series index = raw index shifted by common_shift.
        raw_entry=aligned_t-pd.Timedelta(minutes=common_shift)
        raw_exit=raw_entry+pd.Timedelta(minutes=horizon)
        if raw_entry not in m1.index or raw_exit not in m1.index:
            continue
        er=m1.loc[raw_entry]
        xr=m1.loc[raw_exit]
        entry_bid=float(er["open"])
        exit_bid=float(xr["open"])
        entry_spread_points=float(er["spread"]) if np.isfinite(er["spread"]) else np.nan
        exit_spread_points=float(xr["spread"]) if np.isfinite(xr["spread"]) else np.nan
        if not (np.isfinite(entry_bid) and np.isfinite(exit_bid) and entry_bid>0 and exit_bid>0):
            continue

        if direction=="LONG":
            if not np.isfinite(entry_spread_points):
                continue
            entry_exec=entry_bid+entry_spread_points*point
            exit_exec=exit_bid
            bid_to_bid_bp=(exit_bid/entry_bid-1.0)*1e4
            after_spread_bp=(exit_exec/entry_exec-1.0)*1e4
            applied_spread_bp=(entry_spread_points*point/entry_bid)*1e4
        elif direction=="SHORT":
            if not np.isfinite(exit_spread_points):
                continue
            entry_exec=entry_bid
            exit_exec=exit_bid+exit_spread_points*point
            bid_to_bid_bp=-(exit_bid/entry_bid-1.0)*1e4
            after_spread_bp=((entry_exec-exit_exec)/entry_exec)*1e4
            applied_spread_bp=(exit_spread_points*point/entry_bid)*1e4
        else:
            raise RuntimeError(f"Unknown direction {direction}")

        all_platform_ok=True
        if target_src=="UDXUSD":
            all_platform_ok=bool(raw_entry>=DXY_ALL_PLATFORM_TRADABLE_FROM)

        rec={
            "development_rank":rank,
            "aligned_decision_time":aligned_t,
            "raw_ftmo_entry_time":raw_entry,
            "raw_ftmo_exit_time":raw_exit,
            "target_market":target_src,
            "ftmo_symbol":symbols[target_src],
            "direction":direction,
            "horizon_min":horizon,
            "entry_bid_open":entry_bid,
            "exit_bid_open":exit_bid,
            "entry_spread_points":entry_spread_points,
            "exit_spread_points":exit_spread_points,
            "point":point,
            "bid_to_bid_bp":bid_to_bid_bp,
            "applied_spread_bp":applied_spread_bp,
            "after_historical_spread_bp":after_spread_bp,
            "all_platform_tradeability_ok":all_platform_ok,
        }
        for cost in EXTRA_COST_SCENARIOS_BP:
            key=f"net_after_spread_plus_{str(cost).replace('.','p')}bp"
            rec[key]=after_spread_bp-cost
        local.append(rec)
        trade_rows.append(rec)

    L=pd.DataFrame(local)
    operational=L[L["all_platform_tradeability_ok"].astype(bool)].copy() if len(L) else L
    base=summarize(operational["after_historical_spread_bp"] if len(operational) else [])
    srow={
        "development_rank":rank,
        "ftmo_symbol":symbols[target_src],
        "full_ftmo_signal_n":int(signal_masks[rank].sum()),
        "exact_m1_executable_n":int(len(L)),
        "all_platform_operational_n":int(len(operational)),
        "after_historical_spread_mean_bp":base["mean_bp"],
        "after_historical_spread_median_bp":base["median_bp"],
        "after_historical_spread_win_rate_pct":base["win_rate_pct"],
        "median_applied_spread_bp":float(operational["applied_spread_bp"].median()) if len(operational) else np.nan,
        "p95_applied_spread_bp":float(operational["applied_spread_bp"].quantile(.95)) if len(operational) else np.nan,
    }
    for cost in EXTRA_COST_SCENARIOS_BP:
        key=f"net_after_spread_plus_{str(cost).replace('.','p')}bp"
        z=summarize(operational[key] if len(operational) else [])
        srow[f"{key}_mean_bp"]=z["mean_bp"]
        srow[f"{key}_win_rate_pct"]=z["win_rate_pct"]
    summary_rows.append(srow)

T=pd.DataFrame(trade_rows)
S=pd.DataFrame(summary_rows).sort_values("development_rank").reset_index(drop=True)
T.to_csv(OUT/"V99_EXECUTION_TRADES.csv",index=False)
S.to_csv(OUT/"V99_EXECUTION_SUMMARY.csv",index=False)
status(OUT,4,10,"exact-M1 bid/ask execution scored",trades=len(T))

# ---------- no-lookahead timing receipts ----------
timing=[]
for rank,g in T.groupby("development_rank",sort=True):
    timing.append({
        "development_rank":int(rank),
        "n":int(len(g)),
        "entry_min_delay_from_decision_clock":int((-common_shift)),
        "all_exit_horizons_exact":bool(
            ((pd.to_datetime(g["raw_ftmo_exit_time"])-pd.to_datetime(g["raw_ftmo_entry_time"])).dt.total_seconds()/60
             ==g["horizon_min"]).all()
        ),
        "2026_rows":int((pd.to_datetime(g["raw_ftmo_entry_time"])>=pd.Timestamp("2026-01-01")).sum()),
    })
write_json(OUT/"V99_TIMING_RECEIPT.json",timing)
if any(x["2026_rows"] for x in timing):
    raise RuntimeError("2026 execution row leaked")
status(OUT,5,10,"execution timing/no-2026 assertions passed")

# ---------- external compliance spec, frozen but not retrofitted ----------
compliance={
    "as_of":"2026-09-22",
    "sources":[
        "https://ftmo.com/faq/can-i-trade-news/",
        "https://ftmo.com/en/blog/trading-updates/trading-update-13-feb-2025/",
        "https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/",
    ],
    "evaluation_process":{
        "selected_news_restriction_applies":False,
        "instruction":"execute the frozen strategy unchanged, subject to normal market availability and forbidden-practice rules",
    },
    "funded_standard":{
        "selected_news_window":"2 minutes before through 2 minutes after restricted release",
        "open_or_close_prohibited":True,
        "rank7_DXY":"affected by listed USD restricted events",
        "rank9_GBPUSD":"affected by listed USD and GBP restricted events",
        "live_guard":"reject the entire signal before entry if either scheduled entry or scheduled fixed-horizon exit falls inside a restricted window; never delay entry or exit to rescue a signal",
        "historical_retrofit_in_v99":False,
    },
    "swing":{
        "selected_news_restriction_applies":False,
    },
    "market_closure_guard":"reject entry when the fixed-horizon exit would fall beyond an announced market closure or unavailable session; do not alter holding period",
    "cost_notes":{
        "DXY_cash_published_roundtrip_commission":"0.001% of notional (=0.10 bp) in FTMO DXY listing notice",
        "Forex_published_commission":"$2.50 per lot per side in FTMO commission revamp effective Sep 2025",
        "V99_decision_rule":"do not hard-code these published commissions into selection; use the predeclared extra-cost ladder 0/0.10/0.25/0.50/1.00 bp",
    },
    "candidate_selection_effect":"none",
}
write_json(OUT/"V99_FTMO_COMPLIANCE_SPEC.json",compliance)
status(OUT,6,10,"current FTMO compliance rules frozen as live guards; no retrospective alpha filtering")

# ---------- operational interpretation ----------
flags=[]
for row in S.to_dict("records"):
    rank=int(row["development_rank"])
    flags.append({
        "development_rank":rank,
        "all_platform_operational_n":int(row["all_platform_operational_n"]),
        "spread_only_mean_bp":row["after_historical_spread_mean_bp"],
        "net_plus_0p25bp_mean_bp":row["net_after_spread_plus_0p25bp_mean_bp"],
        "net_plus_0p50bp_mean_bp":row["net_after_spread_plus_0p5bp_mean_bp"],
        "net_plus_1p00bp_mean_bp":row["net_after_spread_plus_1p0bp_mean_bp"],
        "note":"diagnostic only; no rank can be added, removed, or retuned from V99",
    })
write_json(OUT/"V99_OPERATIONAL_FLAGS.json",flags)
status(OUT,7,10,"operational cost-stress diagnostics written; frozen ranks unchanged")

receipt={
    "run_id":RID,
    "status":"COMPLETE_V99_EXECUTION_REALITY_AUDIT",
    "engine_version":ENGINE_VERSION,
    "source_v97e":V97E.name,
    "source_v98":V98.name,
    "frozen_panel_sha256":r97e["frozen_panel_sha256"],
    "frozen_ranks":[7,9],
    "execution_model":"exact next M1 open / exact horizon M1 open with correct bid-ask side",
    "extra_cost_scenarios_bp":list(EXTRA_COST_SCENARIOS_BP),
    "rank7_all_platform_tradeability_from":"2025-02-17",
    "candidate_set_changed":False,
    "thresholds_retuned":False,
    "historical_news_filter_applied":False,
    "2026_values_requested_or_stored":False,
    "next":"HUMAN_REVIEW_V99; THEN IMPLEMENT PAPER/LIVE-SHADOW EA FOR RANKS 7/9 WITH FROZEN COMPLIANCE GUARDS; KEEP 2026 RESEARCH OOS CLOSED",
}
write_json(OUT/"RUN_RECEIPT.json",receipt)
status(OUT,8,10,"receipt written")
status(OUT,9,10,"2026 research OOS remained untouched")
status(OUT,10,10,"DONE")

print("\n=== V99 RECEIPT ===")
print(json.dumps(receipt,indent=2))
print("\n=== V99 EXECUTION SUMMARY ===")
print(S.to_string(index=False))
print("\n=== V99 OPERATIONAL FLAGS ===")
print(json.dumps(flags,indent=2))
print("\nRUN:",OUT)
