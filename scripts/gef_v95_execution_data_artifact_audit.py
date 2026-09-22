from pathlib import Path
import pandas as pd
import numpy as np
import json
import hashlib
import math
import re
import time

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v95"
BASE.mkdir(parents=True,exist_ok=True)

ENGINE_VERSION="V95.0"
MIN_FAST_STATE=5000
GENERIC_COSTS_BP=(1.0,2.0,3.0,5.0)
AUDIT_START=pd.Timestamp("2010-01-01 00:00")
EXT_START=pd.Timestamp("2014-01-01 00:00")
AUDIT_END=pd.Timestamp("2025-12-31 23:55")
OOS_START=pd.Timestamp("2023-01-01 00:00")
OOS_END=AUDIT_END

# Diagnostic only. These do NOT alter the frozen 2026 panel.
AUDIT_SPEC={
    "candidate_set":"exact V94 frozen 2026 forward panel; no additions/removals",
    "windows":"2010-2025 only; 2026 filesystem/data not inspected",
    "core_checks":[
        "exact V92/V93 parity",
        "gross/net economics at 1/2/3/5bp",
        "5m and 10m delayed-entry full-horizon returns on 2014-2025",
        "winner concentration without deleting trades",
        "UTC hour/month/year concentration",
        "pairwise signal overlap and sparse-return correlation",
        "2022-to-2023 source continuity diagnostics on all involved markets",
    ],
    "important":"No trimming, no threshold tuning, no candidate filtering, no 2026 access.",
}

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def status(out,step,total_steps,msg,**extra):
    payload={
        "engine_version":ENGINE_VERSION,
        "step":step,
        "steps":total_steps,
        "percent":round(100*step/total_steps,1),
        "timestamp_utc":pd.Timestamp.now("UTC").isoformat(),
        "message":msg,
        **extra,
    }
    write_json(out/"LIVE_STATUS.json",payload)
    tail=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(
        f"[GEF95] {step}/{total_steps} {100*step/total_steps:.0f}% | {msg}"
        +(f" | {tail}" if tail else ""),
        flush=True,
    )

def causal_states(s,min_periods):
    s=pd.to_numeric(s,errors="coerce")
    mu=s.expanding(min_periods=min_periods).mean().shift(1)
    sd=s.expanding(min_periods=min_periods).std().shift(1).replace(0,np.nan)
    z=((s-mu)/sd).to_numpy(dtype=np.float32)
    finite=np.isfinite(z)
    return finite&(z<=-1.0),finite&(z>=1.0)

def build_fast_feature(name,P):
    m=re.fullmatch(r"price_([A-Z]+)_ret_(\d+)m",name)
    if m:
        sym,mins=m.group(1),int(m.group(2)); k=mins//5
        return (P[sym]/P[sym].shift(k)-1).astype("float32")
    m=re.fullmatch(r"price_([A-Z]+)_rv_(\d+)m",name)
    if m:
        sym,mins=m.group(1),int(m.group(2)); k=mins//5
        r5=P[sym].pct_change(1,fill_method=None)
        return r5.rolling(k,min_periods=max(3,k//2)).std().astype("float32")
    m=re.fullmatch(r"price_([A-Z]+)_trend_(\d+)m",name)
    if m:
        sym,mins=m.group(1),int(m.group(2)); k=mins//5
        return (P[sym]/P[sym].shift(k)-1).astype("float32")
    m=re.fullmatch(r"price_([A-Z]+)_zret_(\d+)m",name)
    if m:
        sym,mins=m.group(1),int(m.group(2)); k=mins//5
        r5=P[sym].pct_change(1,fill_method=None)
        mu=r5.rolling(k,min_periods=max(3,k//2)).mean()
        sd=r5.rolling(k,min_periods=max(3,k//2)).std().replace(0,np.nan)
        return ((r5-mu)/sd).astype("float32")
    raise RuntimeError(f"Unsupported fast feature {name}")

def feature_market(feature):
    m=re.match(r"price_([A-Z]+)_",str(feature))
    return m.group(1) if m else None

def target_market(target):
    return str(target).split("_fwd_",1)[0]

def load_m1(sym,years):
    parts=[]
    for year in years:
        if year>2025:
            raise RuntimeError("V95 refuses 2026+")
        p=ROOT/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
        if not p.exists():
            raise RuntimeError(f"Missing {p}")
        d=pd.read_parquet(p)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        pc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None and isinstance(d.index,pd.DatetimeIndex):
            d=d.reset_index(); dc=d.columns[0]
        if dc is None or pc is None:
            raise RuntimeError(f"Cannot identify datetime/close in {p}")
        utc=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(hours=5)
        q=pd.DataFrame({
            "utc":utc,
            "px":pd.to_numeric(d[pc],errors="coerce"),
        }).dropna()
        q=q[q["utc"].dt.year<=2025]
        parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    return q.set_index("utc")["px"]

def metrics(x):
    x=np.asarray(x,dtype=np.float64)
    x=x[np.isfinite(x)]
    if not len(x):
        return {
            "n":0,"mean_bp":np.nan,"median_bp":np.nan,"win_rate_pct":np.nan,
            "sum_pct":np.nan,"max_drawdown_pct":np.nan,
        }
    if np.any(x<=-1):
        mdd=np.nan
    else:
        eq=np.cumprod(1+x)
        peak=np.maximum.accumulate(eq)
        mdd=float(np.min(eq/peak-1)*100)
    return {
        "n":int(len(x)),
        "mean_bp":float(x.mean()*1e4),
        "median_bp":float(np.median(x)*1e4),
        "win_rate_pct":float((x>0).mean()*100),
        "sum_pct":float(x.sum()*100),
        "max_drawdown_pct":mdd,
    }

def target_arrays(P,grid,target):
    sym,rest=str(target).split("_fwd_",1)
    mins=int(rest.rstrip("m"))
    k=mins//5
    px=P[sym]
    raw=px.shift(-k)/px-1.0
    delay5=px.shift(-(k+1))/px.shift(-1)-1.0
    delay10=px.shift(-(k+2))/px.shift(-2)-1.0
    arr=np.array(raw.reindex(grid),dtype=np.float64,copy=True)
    d5=np.array(delay5.reindex(grid),dtype=np.float64,copy=True)
    d10=np.array(delay10.reindex(grid),dtype=np.float64,copy=True)
    minute=(grid.view("int64")//60_000_000_000).astype(np.int64)
    sample=(minute%mins)==0
    arr[~sample]=np.nan
    d5[~sample]=np.nan
    d10[~sample]=np.nan
    # Do not borrow beyond 2025 for original or delayed exits.
    arr[(grid+pd.Timedelta(minutes=mins))>AUDIT_END]=np.nan
    d5[(grid+pd.Timedelta(minutes=mins+5))>AUDIT_END]=np.nan
    d10[(grid+pd.Timedelta(minutes=mins+10))>AUDIT_END]=np.nan
    return arr,d5,d10,mins

def concentration(vals,times):
    vals=np.asarray(vals,dtype=np.float64)
    good=np.isfinite(vals)
    x=vals[good]
    t=times[good]
    if not len(x):
        return {}
    pos=x[x>0]
    pos_sum=float(pos.sum())
    sorted_pos=np.sort(pos)[::-1] if len(pos) else np.empty(0)
    top1=float(sorted_pos[:1].sum()/pos_sum) if pos_sum>0 else np.nan
    k5=max(1,int(math.ceil(len(x)*0.05)))
    k10=max(1,int(math.ceil(len(x)*0.10)))
    top5=float(sorted_pos[:min(k5,len(sorted_pos))].sum()/pos_sum) if pos_sum>0 else np.nan
    top10=float(sorted_pos[:min(k10,len(sorted_pos))].sum()/pos_sum) if pos_sum>0 else np.nan

    hours=pd.Series(t.hour).value_counts(normalize=True)
    months=pd.Series(t.to_period("M").astype(str)).value_counts(normalize=True)
    years=pd.Series(t.year).value_counts(normalize=True)
    hhi_hour=float(np.square(hours.to_numpy(dtype=float)).sum()) if len(hours) else np.nan
    return {
        "top1_winner_share_of_positive_sum":top1,
        "top5pct_trades_winner_share_of_positive_sum":top5,
        "top10pct_trades_winner_share_of_positive_sum":top10,
        "max_utc_hour_signal_share":float(hours.max()) if len(hours) else np.nan,
        "utc_hour_hhi":hhi_hour,
        "max_month_signal_share":float(months.max()) if len(months) else np.nan,
        "max_year_signal_share":float(years.max()) if len(years) else np.nan,
    }

def continuity_stats(series,year):
    s=series[series.index.year==year]
    r5=s.resample("5min",label="right",closed="left").last().pct_change(fill_method=None)
    a=np.abs(r5.to_numpy(dtype=np.float64))
    a=a[np.isfinite(a)]
    return {
        "year":int(year),
        "m1_rows":int(len(s)),
        "first_utc":str(s.index.min()) if len(s) else None,
        "last_utc":str(s.index.max()) if len(s) else None,
        "median_abs_5m_return_bp":float(np.median(a)*1e4) if len(a) else np.nan,
        "p99_abs_5m_return_bp":float(np.quantile(a,0.99)*1e4) if len(a) else np.nan,
    }

# ---------- exact frozen V94 panel ----------
runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v94").glob("GEF94-*"))
runs=[
    p for p in runs
    if (p/"RUN_RECEIPT.json").exists()
    and (p/"FINAL_2026_FORWARD_FREEZE.json").exists()
    and (p/"FROZEN_2026_FORWARD_PANEL.csv").exists()
]
if not runs:
    raise RuntimeError("No completed V94 freeze")
V94=runs[-1]
r94=json.loads((V94/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
frz94=json.loads((V94/"FINAL_2026_FORWARD_FREEZE.json").read_text(encoding="utf-8"))
panel_path=V94/"FROZEN_2026_FORWARD_PANEL.csv"
panel=pd.read_csv(panel_path)
if r94.get("status")!="COMPLETE_V94_PROMOTION_AND_2026_FREEZE":
    raise RuntimeError(f"V94 status invalid: {r94.get('status')}")
if r94.get("2026_values_accessed") or frz94.get("2026_values_accessed"):
    raise RuntimeError("2026 access assertion already violated")
if sha256(panel_path)!=frz94["panel_sha256"]:
    raise RuntimeError("V94 frozen panel hash mismatch")
if len(panel)!=3:
    raise RuntimeError(f"Expected 3 promoted candidates, found {len(panel)}")

V93=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v93"/r94["source_v93"]
r93=json.loads((V93/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V92=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v92"/r94["source_v92"]
r92=json.loads((V92/"RUN_RECEIPT.json").read_text(encoding="utf-8"))

RID="GEF95-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID
OUT.mkdir(parents=True,exist_ok=False)
status(
    OUT,1,11,
    "exact V94 3-candidate panel loaded; 2026 untouched",
    source_v94=V94.name,
    development_ranks=panel["development_rank"].astype(int).tolist(),
)

spec={
    "run_id":RID,
    "status":"V95_EXECUTION_DATA_AUDIT_SPEC_FROZEN",
    "source_v94":V94.name,
    "v94_panel_sha256":frz94["panel_sha256"],
    "audit_spec":AUDIT_SPEC,
    "2026_values_accessed":False,
}
write_json(OUT/"V95_AUDIT_FREEZE.json",spec)
status(OUT,2,11,"audit specification frozen; candidate set cannot change")

# ---------- lineage ----------
V85=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v85"/r92["source_v85"]
design=json.loads((V85/"TRIAL_DESIGN.json").read_text(encoding="utf-8"))
state_meta=json.loads((V85/"STATE_CACHE_META.json").read_text(encoding="utf-8"))
catalog=pd.read_csv(V85/"FROZEN_ELIGIBLE_FEATURES.csv").reset_index(drop=True)
V84C=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v84c"/design["source_v84c"]
r84=json.loads((V84C/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V83B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v83b"/r84["source_v83b"]
manifest=json.loads((V83B/"REPAIRED_ARCHITECTURE_MANIFEST.json").read_text(encoding="utf-8"))

Fhist=pd.read_parquet(manifest["price_state_5m_path"])
Fhist.index=pd.to_datetime(Fhist.index)
Yhist=pd.read_parquet(manifest["targets_5m_path"])
Yhist.index=pd.to_datetime(Yhist.index)

train_shape=tuple(state_meta["train_shape"])
hold_shape=tuple(state_meta["hold_shape"])
ST=np.memmap(V85/"STATE_TRAIN.bool.dat",mode="r",dtype=np.bool_,shape=train_shape)
SH=np.memmap(V85/"STATE_HOLD.bool.dat",mode="r",dtype=np.bool_,shape=hold_shape)
feature_index={str(row["feature"]):i for i,row in catalog.iterrows()}

needed_features=sorted(set(panel["feature_i"]).union(set(panel["feature_j"])))
needed_targets=sorted(set(panel["target"]))
needed_markets=set()
for f in needed_features:
    needed_markets.add(feature_market(f))
for t in needed_targets:
    needed_markets.add(target_market(t))
needed_markets.discard(None)

# No 2026 checks. Require only through 2025.
missing=[]
for sym in sorted(needed_markets):
    for year in range(2013,2026):
        p=ROOT/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
        if not p.exists():
            missing.append(str(p))
if missing:
    raise RuntimeError(f"V95 missing required 2013-2025 files: {missing}")
status(
    OUT,3,11,
    "2013-2025 source presence confirmed for promoted 3",
    markets=len(needed_markets),
    files=len(needed_markets)*13,
)

# ---------- raw continuation ----------
warm_grid=pd.date_range("2013-12-01 00:00",AUDIT_END,freq="5min")
ext_grid=pd.date_range(EXT_START,AUDIT_END,freq="5min")
P=pd.DataFrame(index=warm_grid)
RAW={}
tp=time.time()
for i,sym in enumerate(sorted(needed_markets),1):
    raw=load_m1(sym,range(2013,2026))
    RAW[sym]=raw
    P[sym]=raw.resample("5min",label="right",closed="left").last().reindex(warm_grid).astype("float64")
    elapsed=time.time()-tp
    rate=i/max(elapsed,1e-9)
    eta=(len(needed_markets)-i)/max(rate,1e-9)
    print(
        f"[GEF95] market {i}/{len(needed_markets)} {sym} | "
        f"elapsed={elapsed/60:.1f}m eta={eta/60:.1f}m",
        flush=True,
    )
status(OUT,4,11,"2014-2025 causal continuation materialized",rows=len(ext_grid))

# ---------- exact state parity ----------
states={}
hist_rows=len(Fhist)
for i,feat in enumerate(needed_features,1):
    fi=feature_index[feat]
    ext=build_fast_feature(feat,P).reindex(ext_grid)
    full=pd.concat([pd.to_numeric(Fhist[feat],errors="coerce"),pd.to_numeric(ext,errors="coerce")])
    lo,hi=causal_states(full,MIN_FAST_STATE)
    exp_lo=np.concatenate([ST[fi,0,:],SH[fi,0,:]])
    exp_hi=np.concatenate([ST[fi,1,:],SH[fi,1,:]])
    ml=int(np.count_nonzero(lo[:hist_rows]!=exp_lo))
    mh=int(np.count_nonzero(hi[:hist_rows]!=exp_hi))
    if ml or mh:
        raise RuntimeError(f"State parity failed {feat}: LO={ml} HI={mh}")
    states[(feat,"LO")]=np.concatenate([exp_lo,lo[hist_rows:]])
    states[(feat,"HI")]=np.concatenate([exp_hi,hi[hist_rows:]])
    if i==1 or i==len(needed_features):
        print(f"[GEF95] state parity {i}/{len(needed_features)}",flush=True)

all_times=Fhist.index.append(ext_grid)
if len(all_times)!=len(next(iter(states.values()))):
    raise RuntimeError("Unified time/state length mismatch")
status(OUT,5,11,"2010-2013 state parity exact; unified 2010-2025 state arrays built",features=len(needed_features))

# ---------- target arrays ----------
target_full={}
target_delay5={}
target_delay10={}
for target in needed_targets:
    # Archived 2010-2013 exact target.
    yh=np.array(pd.to_numeric(Yhist[target],errors="coerce"),dtype=np.float64,copy=True)
    mins=int(str(target).rsplit("_fwd_",1)[1].rstrip("m"))
    hm=(Fhist.index.view("int64")//60_000_000_000).astype(np.int64)
    yh[(hm%mins)!=0]=np.nan

    ext_raw,d5,d10,_=target_arrays(P,ext_grid,target)
    target_full[target]=np.concatenate([yh,ext_raw])
    # Delayed execution is intentionally available only from 2014 onward.
    target_delay5[target]=d5
    target_delay10[target]=d10

# ---------- exact V93 parity before audit ----------
v93_scored=pd.read_csv(V93/"LOCKED_OOS_2023_2025_SCORED.csv")
parity=[]
for r in panel.itertuples(index=False):
    match=v93_scored[v93_scored["development_rank"].astype(int)==int(r.development_rank)]
    if len(match)!=1:
        raise RuntimeError(f"V93 parity row missing rank {r.development_rank}")
    expected=match.iloc[0]
    mask=states[(r.feature_i,r.state_i)]&states[(r.feature_j,r.state_j)]
    sign=1.0 if r.direction=="LONG" else -1.0
    ret=sign*target_full[r.target]
    oos=(all_times>=OOS_START)&(all_times<=OOS_END)
    got=metrics(np.where(mask&oos,ret,np.nan))
    ok=(
        got["n"]==int(expected["n"])
        and np.isclose(got["mean_bp"],float(expected["mean_bp"]),rtol=0,atol=1e-6)
    )
    parity.append({
        "development_rank":int(r.development_rank),
        "expected_n":int(expected["n"]),
        "got_n":got["n"],
        "expected_mean_bp":float(expected["mean_bp"]),
        "got_mean_bp":got["mean_bp"],
        "parity_ok":bool(ok),
    })
    if not ok:
        raise RuntimeError(f"V93 parity failed rank {r.development_rank}")
pd.DataFrame(parity).to_csv(OUT/"V93_OOS_PARITY.csv",index=False)
status(OUT,6,11,"V93 OOS parity exact for all promoted candidates",candidates=len(panel))

# ---------- candidate audits ----------
rows=[]
sparse_series={}
signal_masks={}
ext_offset=len(Fhist)
for idx,r in enumerate(panel.itertuples(index=False),1):
    mask=states[(r.feature_i,r.state_i)]&states[(r.feature_j,r.state_j)]
    sign=1.0 if r.direction=="LONG" else -1.0
    raw=sign*target_full[r.target]
    vals=np.where(mask,raw,np.nan)
    core=metrics(vals)
    conc=concentration(vals,all_times)

    # 2014-2025 delayed-entry diagnostics using the SAME frozen signal state at decision t.
    ext_mask=mask[ext_offset:]
    d5=sign*target_delay5[r.target]
    d10=sign*target_delay10[r.target]
    md5=metrics(np.where(ext_mask,d5,np.nan))
    md10=metrics(np.where(ext_mask,d10,np.nan))

    # OOS cost sensitivity is descriptive. No candidate is removed by this audit.
    oos=(all_times>=OOS_START)&(all_times<=OOS_END)
    oos_vals=np.where(mask&oos,raw,np.nan)
    moos=metrics(oos_vals)

    rec={
        "development_rank":int(r.development_rank),
        "trial_index":int(r.trial_index),
        "feature_i":r.feature_i,"state_i":r.state_i,
        "feature_j":r.feature_j,"state_j":r.state_j,
        "target":r.target,"direction":r.direction,
        "all_2010_2025_n":core["n"],
        "all_2010_2025_mean_bp":core["mean_bp"],
        "all_2010_2025_median_bp":core["median_bp"],
        "all_2010_2025_win_rate_pct":core["win_rate_pct"],
        "all_2010_2025_max_drawdown_pct":core["max_drawdown_pct"],
        "oos_2023_2025_n":moos["n"],
        "oos_2023_2025_mean_bp":moos["mean_bp"],
        "delay5_2014_2025_n":md5["n"],
        "delay5_2014_2025_mean_bp":md5["mean_bp"],
        "delay10_2014_2025_n":md10["n"],
        "delay10_2014_2025_mean_bp":md10["mean_bp"],
        **conc,
    }
    for cost in GENERIC_COSTS_BP:
        key=str(int(cost)) if float(cost).is_integer() else str(cost)
        rec[f"all_net_{key}bp_mean_bp"]=core["mean_bp"]-cost
        rec[f"oos_net_{key}bp_mean_bp"]=moos["mean_bp"]-cost
        rec[f"delay5_net_{key}bp_mean_bp"]=md5["mean_bp"]-cost
        rec[f"delay10_net_{key}bp_mean_bp"]=md10["mean_bp"]-cost

    # Per-year sign/count, 2010-2025.
    pos_net1_years=0
    years_with_n=0
    for year in range(2010,2026):
        sel=np.asarray(all_times.year==year)
        ym=metrics(np.where(mask&sel,raw,np.nan))
        rec[f"y{year}_n"]=ym["n"]
        rec[f"y{year}_mean_bp"]=ym["mean_bp"]
        if ym["n"]>0:
            years_with_n+=1
            if np.isfinite(ym["mean_bp"]) and ym["mean_bp"]>1.0:
                pos_net1_years+=1
    rec["years_with_signals_2010_2025"]=years_with_n
    rec["positive_net1bp_years_2010_2025"]=pos_net1_years
    rows.append(rec)

    ser=pd.Series(np.where(mask,raw,np.nan),index=all_times)
    sparse_series[int(r.development_rank)]=ser
    signal_masks[int(r.development_rank)]=pd.Series(mask,index=all_times)
    print(
        f"[GEF95] audit {idx}/{len(panel)} rank={int(r.development_rank)} "
        f"mean={core['mean_bp']:.3f}bp oos={moos['mean_bp']:.3f}bp "
        f"delay5={md5['mean_bp']:.3f}bp delay10={md10['mean_bp']:.3f}bp",
        flush=True,
    )

A=pd.DataFrame(rows).sort_values("development_rank")
A.to_csv(OUT/"PROMOTED_3_EXECUTION_AUDIT.csv",index=False)
status(OUT,7,11,"execution/concentration audit complete; no trades deleted",candidates=len(A))

# ---------- pairwise overlap/correlation ----------
pairs=[]
ranks=sorted(sparse_series)
for i in range(len(ranks)):
    for j in range(i+1,len(ranks)):
        a,b=ranks[i],ranks[j]
        ma=signal_masks[a].to_numpy(dtype=bool)
        mb=signal_masks[b].to_numpy(dtype=bool)
        overlap=int(np.count_nonzero(ma&mb))
        union=int(np.count_nonzero(ma|mb))
        jaccard=float(overlap/union) if union else np.nan

        sa=sparse_series[a]
        sb=sparse_series[b]
        both=pd.concat([sa.rename("a"),sb.rename("b")],axis=1).dropna()
        corr=float(both["a"].corr(both["b"])) if len(both)>=3 else np.nan
        pairs.append({
            "rank_a":a,"rank_b":b,
            "signal_overlap_count":overlap,
            "signal_jaccard":jaccard,
            "same_timestamp_return_pairs":int(len(both)),
            "same_timestamp_return_corr":corr,
        })
PPAIR=pd.DataFrame(pairs)
PPAIR.to_csv(OUT/"PROMOTED_3_OVERLAP.csv",index=False)
status(OUT,8,11,"pairwise overlap/correlation audit complete",pairs=len(PPAIR))

# ---------- 2022 -> 2023 data continuity ----------
continuity=[]
for sym in sorted(needed_markets):
    s=RAW[sym]
    a=continuity_stats(s,2022)
    b=continuity_stats(s,2023)
    continuity.append({
        "market":sym,
        "rows_2022":a["m1_rows"],
        "rows_2023":b["m1_rows"],
        "row_ratio_2023_vs_2022":float(b["m1_rows"]/a["m1_rows"]) if a["m1_rows"] else np.nan,
        "median_abs_5m_bp_2022":a["median_abs_5m_return_bp"],
        "median_abs_5m_bp_2023":b["median_abs_5m_return_bp"],
        "median_abs_return_ratio_2023_vs_2022":(
            float(b["median_abs_5m_return_bp"]/a["median_abs_5m_return_bp"])
            if np.isfinite(a["median_abs_5m_return_bp"]) and a["median_abs_5m_return_bp"]>0
            else np.nan
        ),
        "p99_abs_5m_bp_2022":a["p99_abs_5m_return_bp"],
        "p99_abs_5m_bp_2023":b["p99_abs_5m_return_bp"],
        "p99_abs_return_ratio_2023_vs_2022":(
            float(b["p99_abs_5m_return_bp"]/a["p99_abs_5m_return_bp"])
            if np.isfinite(a["p99_abs_5m_return_bp"]) and a["p99_abs_5m_return_bp"]>0
            else np.nan
        ),
        "first_2023_utc":b["first_utc"],
    })
C=pd.DataFrame(continuity)
C.to_csv(OUT/"SOURCE_CONTINUITY_2022_2023.csv",index=False)
status(OUT,9,11,"2022-to-2023 source continuity diagnostics written",markets=len(C))

# ---------- no selection verdict; evidence-only flags ----------
flags=[]
for r in A.itertuples(index=False):
    flags.append({
        "development_rank":int(r.development_rank),
        "delay5_net1_positive":bool(np.isfinite(r.delay5_net_1bp_mean_bp) and r.delay5_net_1bp_mean_bp>0),
        "delay10_net1_positive":bool(np.isfinite(r.delay10_net_1bp_mean_bp) and r.delay10_net_1bp_mean_bp>0),
        "oos_net2_positive":bool(np.isfinite(r.oos_net_2bp_mean_bp) and r.oos_net_2bp_mean_bp>0),
        "oos_net3_positive":bool(np.isfinite(r.oos_net_3bp_mean_bp) and r.oos_net_3bp_mean_bp>0),
        "oos_net5_positive":bool(np.isfinite(r.oos_net_5bp_mean_bp) and r.oos_net_5bp_mean_bp>0),
        "max_hour_share":float(r.max_utc_hour_signal_share),
        "top10pct_winner_share_of_positive_sum":float(r.top10pct_trades_winner_share_of_positive_sum),
        "note":"diagnostic only; V94 frozen 2026 panel is unchanged",
    })
write_json(OUT/"AUDIT_DIAGNOSTIC_FLAGS.json",flags)

receipt={
    "run_id":RID,
    "status":"COMPLETE_V95_EXECUTION_DATA_ARTIFACT_AUDIT",
    "engine_version":ENGINE_VERSION,
    "source_v94":V94.name,
    "frozen_2026_panel_sha256":frz94["panel_sha256"],
    "audited_candidates":len(A),
    "candidate_set_changed":False,
    "trades_trimmed_or_deleted":False,
    "thresholds_retuned":False,
    "2026_values_accessed":False,
    "next":"HUMAN_REVIEW_V95; KEEP_ALL_3_FROZEN; DO_NOT_OPEN_2026",
}
write_json(OUT/"RUN_RECEIPT.json",receipt)
status(OUT,10,11,"audit receipt written; frozen 3 unchanged")
status(OUT,11,11,"DONE; 2026 remains fully protected")

print("\n=== V95 RECEIPT ===")
print(json.dumps(receipt,indent=2))
print("\n=== V95 PROMOTED 3 EXECUTION AUDIT ===")
show=[
    "development_rank","target","direction",
    "all_2010_2025_n","all_2010_2025_mean_bp","all_net_1bp_mean_bp",
    "oos_2023_2025_n","oos_2023_2025_mean_bp","oos_net_1bp_mean_bp",
    "oos_net_2bp_mean_bp","oos_net_3bp_mean_bp","oos_net_5bp_mean_bp",
    "delay5_2014_2025_mean_bp","delay5_net_1bp_mean_bp",
    "delay10_2014_2025_mean_bp","delay10_net_1bp_mean_bp",
    "positive_net1bp_years_2010_2025",
    "top10pct_trades_winner_share_of_positive_sum",
    "max_utc_hour_signal_share","max_month_signal_share",
]
print(A[show].to_string(index=False))
print("\n=== V95 PAIRWISE OVERLAP ===")
print(PPAIR.to_string(index=False))
print("\n=== V95 SOURCE CONTINUITY 2022-2023 ===")
print(C.to_string(index=False))
print("\nRUN:",OUT)
