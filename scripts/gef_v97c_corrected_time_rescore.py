from pathlib import Path
import pandas as pd
import numpy as np
import json
import math
import re
import hashlib
import time
from scipy.stats import t as student_t

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v97c_corrected_rescore"
BASE.mkdir(parents=True,exist_ok=True)

ENGINE_VERSION="V97C.0"
MIN_FAST_STATE=5000
BLOCK_DAYS=5
GENERIC_COST_BP=1.0
E2_START=pd.Timestamp("2014-01-01 00:00")
E2_END=pd.Timestamp("2017-12-31 23:55")
E3_START=pd.Timestamp("2018-01-01 00:00")
E3_END=pd.Timestamp("2022-12-31 23:55")
OOS_START=pd.Timestamp("2023-01-01 00:00")
OOS_END=pd.Timestamp("2025-12-31 23:55")

OOS_RULE={
    "minimum_total_signals":20,
    "gross_mean_positive":True,
    "net_after_hypothetical_1bp_positive":True,
    "minimum_positive_net1bp_years_of_3":2,
    "minimum_years_with_at_least_3_signals":2,
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
        f"[GEF97C] {step}/{total_steps} {100*step/total_steps:.0f}% | {msg}"
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

def feature_market(feature):
    m=re.match(r"price_([A-Z]+)_",str(feature))
    return m.group(1) if m else None

def target_market(target):
    return str(target).split("_fwd_",1)[0]

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
    raise RuntimeError(f"Unsupported feature {name}")

def load_m1(sym,years,oos_shift_map,force_old_oos=False):
    parts=[]
    for year in years:
        if year>2025:
            raise RuntimeError("V97C refuses 2026+")
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
        if year<=2022 or force_old_oos:
            shift_min=300
        else:
            if sym not in oos_shift_map:
                raise RuntimeError(f"No frozen V97B 2023-2025 source-time shift for {sym}")
            shift_min=int(oos_shift_map[sym])
        utc=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(minutes=shift_min)
        q=pd.DataFrame({"utc":utc,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
        q=q[(q["utc"]>=pd.Timestamp(f"{year}-01-01")-pd.Timedelta(hours=6))
            &(q["utc"]<pd.Timestamp(f"{year+1}-01-01")+pd.Timedelta(hours=6))]
        parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    return q.set_index("utc")["px"]

def target_array(P,grid,target):
    sym,rest=str(target).split("_fwd_",1)
    mins=int(rest.rstrip("m")); k=mins//5
    raw=P[sym].shift(-k)/P[sym]-1.0
    y=np.array(raw.reindex(grid),dtype=np.float64,copy=True)
    minute=(grid.view("int64")//60_000_000_000).astype(np.int64)
    y[(minute%mins)!=0]=np.nan
    return y,mins

def metrics(x):
    x=np.asarray(x,dtype=np.float64)
    x=x[np.isfinite(x)]
    if not len(x):
        return {
            "n":0,"mean_bp":np.nan,"median_bp":np.nan,"win_rate_pct":np.nan,
            "sum_pct":np.nan,"net_1bp_mean_bp":np.nan,"max_drawdown_pct":np.nan,
        }
    mean_bp=float(x.mean()*1e4)
    if np.any(x<=-1):
        mdd=np.nan
    else:
        eq=np.cumprod(1+x)
        peak=np.maximum.accumulate(eq)
        mdd=float(np.min(eq/peak-1)*100)
    return {
        "n":int(len(x)),
        "mean_bp":mean_bp,
        "median_bp":float(np.median(x)*1e4),
        "win_rate_pct":float((x>0).mean()*100),
        "sum_pct":float(x.sum()*100),
        "net_1bp_mean_bp":mean_bp-GENERIC_COST_BP,
        "max_drawdown_pct":mdd,
    }

def cluster_positive(ret,blocks):
    r=np.asarray(ret,dtype=np.float64)
    b=np.asarray(blocks)
    good=np.isfinite(r)
    r=r[good]; b=b[good]
    n=len(r)
    if n==0:
        return {"n":0,"clusters":0,"mean":np.nan,"p_one":np.nan}
    mean=float(r.mean())
    uniq=np.unique(b); g=len(uniq)
    if g<8:
        return {"n":n,"clusters":g,"mean":mean,"p_one":np.nan}
    u=[]
    for k in uniq:
        x=r[b==k]
        u.append(float(np.sum(x-mean)))
    meat=float(np.sum(np.square(u)))
    if meat<=0 or not np.isfinite(meat):
        return {"n":n,"clusters":g,"mean":mean,"p_one":np.nan}
    se2=(g/(g-1.0))*meat/(n*n)
    if se2<=0 or not np.isfinite(se2):
        return {"n":n,"clusters":g,"mean":mean,"p_one":np.nan}
    t=mean/math.sqrt(se2)
    return {
        "n":n,"clusters":g,"mean":mean,"t":float(t),
        "p_one":float(student_t.sf(t,df=g-1)),
    }

def economic_pass(m,year_metrics):
    coverage=sum(v["n"]>=3 for v in year_metrics.values())
    positive=sum(
        v["n"]>=3
        and np.isfinite(v["net_1bp_mean_bp"])
        and v["net_1bp_mean_bp"]>0
        for v in year_metrics.values()
    )
    passed=bool(
        m["n"]>=OOS_RULE["minimum_total_signals"]
        and np.isfinite(m["mean_bp"]) and m["mean_bp"]>0
        and np.isfinite(m["net_1bp_mean_bp"]) and m["net_1bp_mean_bp"]>0
        and positive>=OOS_RULE["minimum_positive_net1bp_years_of_3"]
        and coverage>=OOS_RULE["minimum_years_with_at_least_3_signals"]
    )
    return passed,int(positive),int(coverage)

# ---------- source freezes ----------
v94_runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v94").glob("GEF94-*"))
v94_runs=[
    p for p in v94_runs
    if (p/"RUN_RECEIPT.json").exists()
    and (p/"FROZEN_2026_FORWARD_PANEL.csv").exists()
    and json.loads((p/"RUN_RECEIPT.json").read_text(encoding="utf-8")).get("status")=="COMPLETE_V94_PROMOTION_AND_2026_FREEZE"
]
if not v94_runs:
    raise RuntimeError("No completed V94")
V94=v94_runs[-1]
r94=json.loads((V94/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
panel_path=V94/"FROZEN_2026_FORWARD_PANEL.csv"
panel=pd.read_csv(panel_path)
if len(panel)!=3:
    raise RuntimeError(f"Expected frozen 3, found {len(panel)}")
if sha256(panel_path)!=r94["frozen_2026_panel_sha256"]:
    raise RuntimeError("V94 frozen panel hash mismatch")
if r94.get("2026_values_accessed"):
    raise RuntimeError("V94 reports 2026 access")

v97b_runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v97b_time_semantics").glob("GEF97B-*"))
v97b_runs=[
    p for p in v97b_runs
    if (p/"RUN_RECEIPT.json").exists()
    and json.loads((p/"RUN_RECEIPT.json").read_text(encoding="utf-8")).get("status")=="COMPLETE_V97B_SOURCE_TIME_SEMANTICS_FREEZE"
]
if not v97b_runs:
    raise RuntimeError("No completed V97B")
V97B=v97b_runs[-1]
r97b=json.loads((V97B/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r97b.get("2026_accessed"):
    raise RuntimeError("V97B reports 2026 access")
shift_map={str(k):int(v) for k,v in r97b["histdata_stored_to_aligned_shift_min"].items()}

expected_markets=set()
for r in panel.itertuples(index=False):
    expected_markets.add(feature_market(r.feature_i))
    expected_markets.add(feature_market(r.feature_j))
    expected_markets.add(target_market(r.target))
expected_markets.discard(None)
if not expected_markets.issubset(set(shift_map)):
    raise RuntimeError(f"V97B map incomplete for frozen3: {sorted(expected_markets-set(shift_map))}")

# Only the empirically demonstrated source-time anomaly may differ from documented +300m.
anomalies={m:s for m,s in shift_map.items() if s!=300}
if anomalies!={"USDCHF":0}:
    raise RuntimeError(f"Unexpected V97B anomaly map: {anomalies}")

V93=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v93"/r94["source_v93"]
old_v93=pd.read_csv(V93/"LOCKED_OOS_2023_2025_SCORED.csv")
V92=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v92"/r94["source_v92"]
r92=json.loads((V92/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r92.get("2023_plus_values_accessed") or r92.get("protected_2026_accessed"):
    raise RuntimeError("V92 access assertion violated")

# V94's FROZEN_2026_FORWARD_PANEL.csv intentionally contains only the exact
# hypothesis identity columns. Development-era parity references live in the
# immutable V92 development ledger and MUST be joined explicitly.
dev_path=V92/"V92_CLEAN_DEVELOPMENT_ALL.csv"
if not dev_path.exists():
    raise RuntimeError(f"Missing V92 development ledger: {dev_path}")
dev=pd.read_csv(dev_path)

identity_cols=[
    "development_rank","trial_index","feature_i","state_i",
    "feature_j","state_j","target","direction",
]
dev_parity_cols=[
    "development_rank",
    "e2_2014_2017_n","e2_2014_2017_mean_bp",
    "e3_2018_2022_n","e3_2018_2022_mean_bp",
]
required_old_v93_cols=[
    "development_rank","n","mean_bp","economic_oos_pass",
]

missing_panel=[x for x in identity_cols if x not in panel.columns]
missing_dev=[x for x in dev_parity_cols if x not in dev.columns]
missing_old=[x for x in required_old_v93_cols if x not in old_v93.columns]
if missing_panel or missing_dev or missing_old:
    raise RuntimeError(
        "V97C schema preflight failed before any reconstruction: "
        f"panel_missing={missing_panel} dev_missing={missing_dev} old_v93_missing={missing_old}"
    )
if panel["development_rank"].duplicated().any():
    raise RuntimeError("V94 frozen panel has duplicate development_rank")
if dev["development_rank"].duplicated().any():
    raise RuntimeError("V92 development ledger has duplicate development_rank")
if old_v93["development_rank"].duplicated().any():
    raise RuntimeError("V93 scored ledger has duplicate development_rank")

panel=panel.merge(
    dev[dev_parity_cols],
    on="development_rank",
    how="left",
    validate="one_to_one",
)
if panel[dev_parity_cols[1:]].isna().any().any():
    bad=panel.loc[
        panel[dev_parity_cols[1:]].isna().any(axis=1),
        "development_rank",
    ].astype(int).tolist()
    raise RuntimeError(f"V92 parity reference missing after merge for ranks {bad}")

# Static contract: all attributes later read from panel.itertuples() are now
# guaranteed to exist before the expensive market reconstruction begins.
later_panel_attrs={
    "development_rank","feature_i","state_i","feature_j","state_j","target","direction",
    "e2_2014_2017_n","e2_2014_2017_mean_bp",
    "e3_2018_2022_n","e3_2018_2022_mean_bp",
}
missing_later=sorted(later_panel_attrs-set(panel.columns))
if missing_later:
    raise RuntimeError(f"V97C internal panel contract incomplete: {missing_later}")

RID="GEF97C-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID
OUT.mkdir(parents=True,exist_ok=False)
status(
    OUT,1,11,
    "V94 frozen3 + V97B source-time map loaded; 2026 untouched",
    source_v94=V94.name,
    source_v97b=V97B.name,
    anomaly_map=anomalies,
)

freeze={
    "run_id":RID,
    "status":"V97C_CORRECTED_TIME_RESCORE_SPEC_FROZEN",
    "source_v94":V94.name,
    "source_v93":V93.name,
    "source_v97b":V97B.name,
    "frozen_candidates":panel["development_rank"].astype(int).tolist(),
    "source_time_map_2023_2025":shift_map,
    "correction_reason":"V97A/V97B market-return forensic proved USDCHF 2023-2025 local parquet timestamps are already UTC-equivalent while V93 added +300m",
    "scoring_rule":"exact V93 economic OOS rule",
    "retuning":False,
    "candidate_additions":False,
    "strategy_outcomes_used_to_choose_timestamp_correction":False,
    "2026_accessed":False,
}
write_json(OUT/"V97C_RESCORE_FREEZE.json",freeze)
status(OUT,2,11,"corrected-time rescore specification physically frozen")

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
status(OUT,3,11,"lineage resolved",markets=len(needed_markets),features=len(needed_features),targets=len(needed_targets))

# ---------- build old and corrected continuations ----------
warm_grid=pd.date_range("2013-12-01 00:00",OOS_END,freq="5min")
post2013_grid=pd.date_range(E2_START,OOS_END,freq="5min")

P_old=pd.DataFrame(index=warm_grid)
P_new=pd.DataFrame(index=warm_grid)
t0=time.time()
for i,sym in enumerate(sorted(needed_markets),1):
    raw_old=load_m1(sym,range(2013,2026),shift_map,force_old_oos=True)
    raw_new=load_m1(sym,range(2013,2026),shift_map,force_old_oos=False)
    P_old[sym]=raw_old.resample("5min",label="right",closed="left").last().reindex(warm_grid).astype("float64")
    P_new[sym]=raw_new.resample("5min",label="right",closed="left").last().reindex(warm_grid).astype("float64")
    elapsed=time.time()-t0
    rate=i/max(elapsed,1e-9)
    eta=(len(needed_markets)-i)/max(rate,1e-9)
    print(
        f"[GEF97C] market {i}/{len(needed_markets)} {sym} | elapsed={elapsed/60:.1f}m eta={eta/60:.1f}m",
        flush=True,
    )
status(OUT,4,11,"old-V93 and corrected-time price continuations materialized",rows=len(post2013_grid))

def build_states(P):
    out={}
    for feat in needed_features:
        fi=feature_index[feat]
        ext=build_fast_feature(feat,P).reindex(post2013_grid)
        full=pd.concat([pd.to_numeric(Fhist[feat],errors="coerce"),pd.to_numeric(ext,errors="coerce")])
        lo,hi=causal_states(full,MIN_FAST_STATE)
        hist_rows=len(Fhist)
        exp_lo=np.concatenate([ST[fi,0,:],SH[fi,0,:]])
        exp_hi=np.concatenate([ST[fi,1,:],SH[fi,1,:]])
        ml=int(np.count_nonzero(lo[:hist_rows]!=exp_lo))
        mh=int(np.count_nonzero(hi[:hist_rows]!=exp_hi))
        if ml or mh:
            raise RuntimeError(f"2010-2013 state parity failed {feat}: LO={ml} HI={mh}")
        out[(feat,"LO")]=lo[hist_rows:]
        out[(feat,"HI")]=hi[hist_rows:]
    return out

states_old=build_states(P_old)
states_new=build_states(P_new)
status(OUT,5,11,"2010-2013 state parity exact for old and corrected reconstructions")

target_old={t:target_array(P_old,post2013_grid,t) for t in needed_targets}
target_new={t:target_array(P_new,post2013_grid,t) for t in needed_targets}

# V92 2014-2022 parity must remain EXACT under corrected pipeline.
parity=[]
for r in panel.itertuples(index=False):
    mask=states_new[(r.feature_i,r.state_i)]&states_new[(r.feature_j,r.state_j)]
    raw,mins=target_new[r.target]
    ret=(1.0 if r.direction=="LONG" else -1.0)*raw
    h=pd.Timedelta(minutes=mins)
    e2=(post2013_grid>=E2_START)&(post2013_grid<=E2_END)&((post2013_grid+h)<=E2_END)
    e3=(post2013_grid>=E3_START)&(post2013_grid<=E3_END)&((post2013_grid+h)<=E3_END)
    m2=metrics(np.where(mask&e2,ret,np.nan))
    m3=metrics(np.where(mask&e3,ret,np.nan))
    ok=(
        m2["n"]==int(r.e2_2014_2017_n)
        and m3["n"]==int(r.e3_2018_2022_n)
        and np.isclose(m2["mean_bp"],float(r.e2_2014_2017_mean_bp),rtol=0,atol=1e-6)
        and np.isclose(m3["mean_bp"],float(r.e3_2018_2022_mean_bp),rtol=0,atol=1e-6)
    )
    parity.append({
        "development_rank":int(r.development_rank),
        "e2_n":m2["n"],"e2_mean_bp":m2["mean_bp"],
        "e3_n":m3["n"],"e3_mean_bp":m3["mean_bp"],
        "parity_ok":bool(ok),
    })
    if not ok:
        raise RuntimeError(f"V92 2014-2022 parity failed rank {r.development_rank}")
pd.DataFrame(parity).to_csv(OUT/"V92_PRE2023_PARITY.csv",index=False)
status(OUT,6,11,"2014-2022 parity exact; correction is confined to 2023-2025")

# ---------- score old and corrected OOS side by side ----------
oos=(post2013_grid>=OOS_START)&(post2013_grid<=OOS_END)
oos_times=post2013_grid[oos]
blocks=((oos_times.normalize()-OOS_START.normalize()).days.to_numpy()//BLOCK_DAYS).astype(np.int16)

records=[]
signal_compare=[]
for idx,r in enumerate(panel.itertuples(index=False),1):
    sign=1.0 if r.direction=="LONG" else -1.0

    old_mask=states_old[(r.feature_i,r.state_i)]&states_old[(r.feature_j,r.state_j)]
    old_raw,mins_old=target_old[r.target]
    old_ret=sign*old_raw

    new_mask=states_new[(r.feature_i,r.state_i)]&states_new[(r.feature_j,r.state_j)]
    new_raw,mins_new=target_new[r.target]
    new_ret=sign*new_raw
    if mins_old!=mins_new:
        raise RuntimeError("target horizon mismatch")
    h=pd.Timedelta(minutes=mins_new)
    boundary=np.asarray((oos_times+h)<=OOS_END)

    old_gate=np.where(old_mask[oos]&boundary,old_ret[oos],np.nan)
    new_gate=np.where(new_mask[oos]&boundary,new_ret[oos],np.nan)

    old_m=metrics(old_gate)
    new_m=metrics(new_gate)
    old_ct=cluster_positive(old_gate,blocks)
    new_ct=cluster_positive(new_gate,blocks)

    old_year={}
    new_year={}
    for year in (2023,2024,2025):
        yy=np.asarray(oos_times.year==year)
        old_year[year]=metrics(old_gate[yy])
        new_year[year]=metrics(new_gate[yy])

    old_pass,old_pos,old_cov=economic_pass(old_m,old_year)
    new_pass,new_pos,new_cov=economic_pass(new_m,new_year)

    # Exact old-V93 reconstruction check.
    prior=old_v93[old_v93["development_rank"].astype(int)==int(r.development_rank)]
    if len(prior)!=1:
        raise RuntimeError(f"Old V93 row missing rank {r.development_rank}")
    prior=prior.iloc[0]
    old_parity=(
        old_m["n"]==int(prior["n"])
        and np.isclose(old_m["mean_bp"],float(prior["mean_bp"]),rtol=0,atol=1e-6)
    )
    if not old_parity:
        raise RuntimeError(
            f"Old V93 reconstruction parity failed rank {r.development_rank}: "
            f"got n={old_m['n']} mean={old_m['mean_bp']} expected n={prior['n']} mean={prior['mean_bp']}"
        )

    old_trade=np.isfinite(old_gate)
    new_trade=np.isfinite(new_gate)
    inter=int(np.count_nonzero(old_trade&new_trade))
    union=int(np.count_nonzero(old_trade|new_trade))

    rec={
        "development_rank":int(r.development_rank),
        "feature_i":r.feature_i,"state_i":r.state_i,
        "feature_j":r.feature_j,"state_j":r.state_j,
        "target":r.target,"direction":r.direction,
        "old_v93_n":old_m["n"],
        "old_v93_mean_bp":old_m["mean_bp"],
        "old_v93_net1bp_mean_bp":old_m["net_1bp_mean_bp"],
        "old_v93_cluster_p_one":old_ct.get("p_one",np.nan),
        "old_v93_economic_pass":old_pass,
        "corrected_n":new_m["n"],
        "corrected_mean_bp":new_m["mean_bp"],
        "corrected_net1bp_mean_bp":new_m["net_1bp_mean_bp"],
        "corrected_median_bp":new_m["median_bp"],
        "corrected_win_rate_pct":new_m["win_rate_pct"],
        "corrected_sum_pct":new_m["sum_pct"],
        "corrected_max_drawdown_pct":new_m["max_drawdown_pct"],
        "corrected_cluster_p_one":new_ct.get("p_one",np.nan),
        "corrected_positive_net1bp_years":new_pos,
        "corrected_coverage_years_ge3signals":new_cov,
        "corrected_economic_oos_pass":new_pass,
        "delta_n":new_m["n"]-old_m["n"],
        "delta_mean_bp":new_m["mean_bp"]-old_m["mean_bp"],
        "old_vs_corrected_signal_intersection":inter,
        "old_vs_corrected_signal_union":union,
        "old_vs_corrected_signal_jaccard":float(inter/union) if union else np.nan,
    }
    for year in (2023,2024,2025):
        rec[f"old_y{year}_n"]=old_year[year]["n"]
        rec[f"old_y{year}_mean_bp"]=old_year[year]["mean_bp"]
        rec[f"corrected_y{year}_n"]=new_year[year]["n"]
        rec[f"corrected_y{year}_mean_bp"]=new_year[year]["mean_bp"]
        rec[f"corrected_y{year}_net1bp_mean_bp"]=new_year[year]["net_1bp_mean_bp"]

    records.append(rec)
    signal_compare.append({
        "development_rank":int(r.development_rank),
        "old_signal_n":int(old_trade.sum()),
        "corrected_signal_n":int(new_trade.sum()),
        "intersection":inter,
        "union":union,
        "jaccard":float(inter/union) if union else np.nan,
    })
    print(
        f"[GEF97C] {idx}/3 rank={int(r.development_rank)} | "
        f"old={old_m['mean_bp']:.4f}bp n={old_m['n']} -> "
        f"corrected={new_m['mean_bp']:.4f}bp n={new_m['n']} | "
        f"pass={new_pass}",
        flush=True,
    )

R=pd.DataFrame(records).sort_values("development_rank").reset_index(drop=True)
R.to_csv(OUT/"CORRECTED_TIME_RESCORE_FROZEN3.csv",index=False)
pd.DataFrame(signal_compare).to_csv(OUT/"OLD_VS_CORRECTED_SIGNAL_OVERLAP.csv",index=False)
status(
    OUT,7,11,
    "old V93 parity exact and corrected 2023-2025 rescore complete",
    corrected_passes=int(R["corrected_economic_oos_pass"].sum()),
)

# ---------- scientific status ----------
affected=[int(x) for x in R.loc[R["old_vs_corrected_signal_jaccard"]<0.999999,"development_rank"].tolist()]
changed_pass=[
    int(x) for x in R.loc[
        R["old_v93_economic_pass"].astype(bool)!=R["corrected_economic_oos_pass"].astype(bool),
        "development_rank"
    ].tolist()
]
repair_status={
    "source_time_anomaly":"USDCHF 2023-2025 stored timestamp already UTC-equivalent; V93 incorrectly added +300m",
    "affected_frozen3_ranks":affected,
    "economic_pass_status_changed_ranks":changed_pass,
    "corrected_pass_ranks":R.loc[R["corrected_economic_oos_pass"],"development_rank"].astype(int).tolist(),
    "important":"This is a data-quality repair of already-opened 2023-2025 OOS, not a new independent validation.",
    "v94_original_promotion_should_be_treated_as_superseded_if_pass_set_changed":bool(changed_pass),
    "retuning_performed":False,
    "2026_accessed":False,
}
write_json(OUT/"SCIENTIFIC_REPAIR_STATUS.json",repair_status)
status(OUT,8,11,"scientific repair status written",affected=affected,pass_changed=changed_pass)

# Do NOT silently replace V94. Any new final 2026 freeze requires human review first.
receipt={
    "run_id":RID,
    "status":"COMPLETE_V97C_CORRECTED_TIME_RESCORE_FROZEN3",
    "engine_version":ENGINE_VERSION,
    "source_v94":V94.name,
    "source_v93":V93.name,
    "source_v97b":V97B.name,
    "original_v94_panel_sha256":r94["frozen_2026_panel_sha256"],
    "audited_candidates":3,
    "corrected_pass_ranks":repair_status["corrected_pass_ranks"],
    "economic_pass_status_changed_ranks":changed_pass,
    "candidate_set_changed_by_script":False,
    "thresholds_retuned":False,
    "strategy_outcomes_used_to_choose_time_correction":False,
    "2026_accessed":False,
    "next":"STOP_FOR_HUMAN_REVIEW; IF PROMOTION SET CHANGED, REPAIR FULL ORIGINAL V93 SCORED PANEL BEFORE ANY NEW 2026 FREEZE",
}
write_json(OUT/"RUN_RECEIPT.json",receipt)
status(OUT,9,11,"receipt written; V94 not silently replaced")
status(OUT,10,11,"2026 remains protected")
status(OUT,11,11,"DONE")

print("\n=== V97C RECEIPT ===")
print(json.dumps(receipt,indent=2))
print("\n=== V97C CORRECTED-TIME RESCORE FROZEN 3 ===")
cols=[
    "development_rank","feature_i","state_i","feature_j","state_j","target","direction",
    "old_v93_n","old_v93_mean_bp","old_v93_net1bp_mean_bp","old_v93_economic_pass",
    "corrected_n","corrected_mean_bp","corrected_net1bp_mean_bp",
    "corrected_cluster_p_one","corrected_positive_net1bp_years",
    "corrected_economic_oos_pass","delta_n","delta_mean_bp",
    "old_vs_corrected_signal_jaccard",
    "corrected_y2023_n","corrected_y2023_mean_bp",
    "corrected_y2024_n","corrected_y2024_mean_bp",
    "corrected_y2025_n","corrected_y2025_mean_bp",
]
print(R[cols].to_string(index=False))
print("\nRUN:",OUT)
