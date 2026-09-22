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
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v97d_full_v93_repair"
BASE.mkdir(parents=True,exist_ok=True)

ENGINE_VERSION="V97D.0"
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
    "cluster_one_sided_p":"diagnostic only",
    "BH_q_across_corrected_scored_panel":"diagnostic only, q=0.10",
}

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
        "step":step,"steps":total,"percent":round(100*step/total,1),
        "timestamp_utc":pd.Timestamp.now("UTC").isoformat(),
        "message":msg,**extra,
    }
    write_json(out/"LIVE_STATUS.json",payload)
    tail=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF97D] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

def feature_market(feature):
    m=re.match(r"price_([A-Z]+)_",str(feature))
    return m.group(1) if m else None

def target_market(target):
    return str(target).split("_fwd_",1)[0]

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
    raise RuntimeError(f"Unsupported feature {name}")

def load_m1(sym,years,corrected):
    parts=[]
    for year in years:
        if year>2025:
            raise RuntimeError("V97D refuses 2026+")
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
        # ONLY proven anomaly: USDCHF 2023-2025 local files are already UTC-equivalent.
        shift_min=0 if (corrected and sym=="USDCHF" and year>=2023) else 300
        utc=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(minutes=shift_min)
        q=pd.DataFrame({"utc":utc,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
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

def bh_adjust(p):
    p=np.asarray(p,dtype=np.float64)
    out=np.full(len(p),np.nan)
    idx=np.flatnonzero(np.isfinite(p))
    if not len(idx):
        return out
    vals=p[idx]
    order=np.argsort(vals)
    ranked=vals[order]
    adj=ranked*len(ranked)/np.arange(1,len(ranked)+1,dtype=np.float64)
    adj=np.minimum.accumulate(adj[::-1])[::-1]
    adj=np.clip(adj,0,1)
    out[idx[order]]=adj
    return out

def pass_rule(m,year_metrics):
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

# ---------- immutable sources ----------
v94_runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v94").glob("GEF94-*"))
v94_runs=[
    p for p in v94_runs
    if (p/"RUN_RECEIPT.json").exists()
    and json.loads((p/"RUN_RECEIPT.json").read_text(encoding="utf-8")).get("status")=="COMPLETE_V94_PROMOTION_AND_2026_FREEZE"
]
if not v94_runs:
    raise RuntimeError("No completed V94")
V94=v94_runs[-1]
r94=json.loads((V94/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r94.get("2026_values_accessed"):
    raise RuntimeError("V94 reports 2026 access")

V93=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v93"/r94["source_v93"]
r93=json.loads((V93/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
old=pd.read_csv(V93/"LOCKED_OOS_2023_2025_SCORED.csv")
if not r93.get("2023_2025_strategy_outcomes_accessed") or r93.get("protected_2026_accessed"):
    raise RuntimeError("V93 access/status mismatch")
if len(old)!=int(r93["scored_hypotheses"]):
    raise RuntimeError("V93 scored row count mismatch")

V92=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v92"/r94["source_v92"]
r92=json.loads((V92/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
dev=pd.read_csv(V92/"V92_CLEAN_DEVELOPMENT_ALL.csv")
if r92.get("2023_plus_values_accessed") or r92.get("protected_2026_accessed"):
    raise RuntimeError("V92 access assertion violated")

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
if r97b.get("storage_semantics_anomalies")!={"USDCHF":0}:
    raise RuntimeError(f"Unexpected V97B anomaly set {r97b.get('storage_semantics_anomalies')}")

required_old=[
    "development_rank","trial_index","feature_i","state_i","family_i",
    "feature_j","state_j","family_j","target","direction",
    "n","mean_bp","net_1bp_mean_bp","median_bp","win_rate_pct","sum_pct",
    "max_drawdown_pct","cluster_blocks","cluster_p_one",
    "positive_net1bp_years","coverage_years_ge3signals","economic_oos_pass",
    "y2023_n","y2023_mean_bp","y2023_net1bp_mean_bp",
    "y2024_n","y2024_mean_bp","y2024_net1bp_mean_bp",
    "y2025_n","y2025_mean_bp","y2025_net1bp_mean_bp",
]
missing=[c for c in required_old if c not in old.columns]
if missing:
    raise RuntimeError(f"V93 scored schema missing {missing}")
if old["development_rank"].duplicated().any():
    raise RuntimeError("V93 scored duplicate rank")

affected=[]
for row in old.to_dict("records"):
    markets={feature_market(row["feature_i"]),feature_market(row["feature_j"]),target_market(row["target"])}
    if "USDCHF" in markets:
        affected.append(int(row["development_rank"]))
affected=sorted(affected)
if not affected:
    raise RuntimeError("No USDCHF-dependent V93 scored hypotheses found")

dev_cols=[
    "development_rank",
    "e2_2014_2017_n","e2_2014_2017_mean_bp",
    "e3_2018_2022_n","e3_2018_2022_mean_bp",
]
missing_dev=[c for c in dev_cols if c not in dev.columns]
if missing_dev:
    raise RuntimeError(f"V92 dev schema missing {missing_dev}")
dev_ref=dev[dev_cols].copy()
if dev_ref["development_rank"].duplicated().any():
    raise RuntimeError("V92 dev duplicate rank")

affected_panel=old[old["development_rank"].astype(int).isin(affected)][[
    "development_rank","trial_index","feature_i","state_i",
    "feature_j","state_j","target","direction",
]].merge(dev_ref,on="development_rank",how="left",validate="one_to_one")
if affected_panel[dev_cols[1:]].isna().any().any():
    raise RuntimeError("Missing V92 parity refs for affected hypotheses")

RID="GEF97D-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID
OUT.mkdir(parents=True,exist_ok=False)

freeze={
    "run_id":RID,
    "status":"V97D_FULL_V93_REPAIR_SPEC_FROZEN",
    "source_v93":V93.name,
    "source_v97b":V97B.name,
    "original_scored_ranks":sorted(old["development_rank"].astype(int).tolist()),
    "affected_ranks_due_to_usdchf_timestamp_anomaly":affected,
    "unaffected_rows_rule":"carry forward byte-equivalent V93 statistics; correction has no dependency path to them",
    "affected_rows_rule":"reconstruct old V93 exactly, then rescore using only USDCHF 2023-2025 +0m instead of erroneous +300m",
    "BH_rule":"recompute diagnostic BH q across all original scored hypotheses after affected-row repair",
    "economic_rule":OOS_RULE,
    "retuning":False,
    "candidate_additions":False,
    "2026_accessed":False,
}
write_json(OUT/"V97D_REPAIR_FREEZE.json",freeze)
status(
    OUT,1,11,
    "full original V93 scored-panel repair spec frozen",
    scored=len(old),affected=affected,unaffected=len(old)-len(affected),
)

# ---------- lineage only for affected hypotheses ----------
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

needed_features=sorted(set(affected_panel["feature_i"]).union(set(affected_panel["feature_j"])))
needed_targets=sorted(set(affected_panel["target"]))
needed_markets=set()
for f in needed_features:
    needed_markets.add(feature_market(f))
for t in needed_targets:
    needed_markets.add(target_market(t))
needed_markets.discard(None)
status(OUT,2,11,"affected lineage resolved",markets=len(needed_markets),features=len(needed_features),targets=len(needed_targets))

warm_grid=pd.date_range("2013-12-01 00:00",OOS_END,freq="5min")
post2013_grid=pd.date_range(E2_START,OOS_END,freq="5min")
P_old=pd.DataFrame(index=warm_grid)
P_new=pd.DataFrame(index=warm_grid)
t0=time.time()
for i,sym in enumerate(sorted(needed_markets),1):
    so=load_m1(sym,range(2013,2026),corrected=False)
    sn=load_m1(sym,range(2013,2026),corrected=True)
    P_old[sym]=so.resample("5min",label="right",closed="left").last().reindex(warm_grid).astype("float64")
    P_new[sym]=sn.resample("5min",label="right",closed="left").last().reindex(warm_grid).astype("float64")
    elapsed=time.time()-t0
    rate=i/max(elapsed,1e-9)
    eta=(len(needed_markets)-i)/max(rate,1e-9)
    print(f"[GEF97D] market {i}/{len(needed_markets)} {sym} | elapsed={elapsed/60:.1f}m eta={eta/60:.1f}m",flush=True)
status(OUT,3,11,"old and corrected affected-market continuations materialized",rows=len(post2013_grid))

def build_states(P):
    out={}
    hist_rows=len(Fhist)
    for feat in needed_features:
        fi=feature_index[feat]
        ext=build_fast_feature(feat,P).reindex(post2013_grid)
        full=pd.concat([pd.to_numeric(Fhist[feat],errors="coerce"),pd.to_numeric(ext,errors="coerce")])
        lo,hi=causal_states(full,MIN_FAST_STATE)
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
status(OUT,4,11,"2010-2013 state parity exact for all affected features")

target_old={t:target_array(P_old,post2013_grid,t) for t in needed_targets}
target_new={t:target_array(P_new,post2013_grid,t) for t in needed_targets}

# 2014-2022 must remain identical to V92.
parity=[]
for r in affected_panel.to_dict("records"):
    mask=states_new[(r["feature_i"],r["state_i"])]&states_new[(r["feature_j"],r["state_j"])]
    raw,mins=target_new[r["target"]]
    ret=(1.0 if r["direction"]=="LONG" else -1.0)*raw
    h=pd.Timedelta(minutes=mins)
    e2=(post2013_grid>=E2_START)&(post2013_grid<=E2_END)&((post2013_grid+h)<=E2_END)
    e3=(post2013_grid>=E3_START)&(post2013_grid<=E3_END)&((post2013_grid+h)<=E3_END)
    m2=metrics(np.where(mask&e2,ret,np.nan))
    m3=metrics(np.where(mask&e3,ret,np.nan))
    ok=(
        m2["n"]==int(r["e2_2014_2017_n"])
        and m3["n"]==int(r["e3_2018_2022_n"])
        and np.isclose(m2["mean_bp"],float(r["e2_2014_2017_mean_bp"]),rtol=0,atol=1e-6)
        and np.isclose(m3["mean_bp"],float(r["e3_2018_2022_mean_bp"]),rtol=0,atol=1e-6)
    )
    parity.append({
        "development_rank":int(r["development_rank"]),
        "e2_n":m2["n"],"e2_mean_bp":m2["mean_bp"],
        "e3_n":m3["n"],"e3_mean_bp":m3["mean_bp"],
        "parity_ok":bool(ok),
    })
    if not ok:
        raise RuntimeError(f"V92 development parity failed rank {r['development_rank']}")
pd.DataFrame(parity).to_csv(OUT/"AFFECTED_V92_DEVELOPMENT_PARITY.csv",index=False)
status(OUT,5,11,"2014-2022 parity exact for all affected hypotheses")

# ---------- reconstruct old + corrected affected OOS ----------
oos=(post2013_grid>=OOS_START)&(post2013_grid<=OOS_END)
oos_times=post2013_grid[oos]
blocks=((oos_times.normalize()-OOS_START.normalize()).days.to_numpy()//BLOCK_DAYS).astype(np.int16)
affected_records={}
old_parity=[]

for idx,r in enumerate(affected_panel.to_dict("records"),1):
    rank=int(r["development_rank"])
    sign=1.0 if r["direction"]=="LONG" else -1.0

    mo=states_old[(r["feature_i"],r["state_i"])]&states_old[(r["feature_j"],r["state_j"])]
    mn=states_new[(r["feature_i"],r["state_i"])]&states_new[(r["feature_j"],r["state_j"])]

    yo,mins_o=target_old[r["target"]]
    yn,mins_n=target_new[r["target"]]
    if mins_o!=mins_n:
        raise RuntimeError("Target horizon mismatch")
    h=pd.Timedelta(minutes=mins_n)
    boundary=np.asarray((oos_times+h)<=OOS_END)

    go=np.where(mo[oos]&boundary,sign*yo[oos],np.nan)
    gn=np.where(mn[oos]&boundary,sign*yn[oos],np.nan)

    om=metrics(go)
    nm=metrics(gn)
    oct=cluster_positive(go,blocks)
    nct=cluster_positive(gn,blocks)

    prior=old[old["development_rank"].astype(int)==rank]
    if len(prior)!=1:
        raise RuntimeError(f"V93 prior row missing rank {rank}")
    prior=prior.iloc[0]
    old_ok=(
        om["n"]==int(prior["n"])
        and np.isclose(om["mean_bp"],float(prior["mean_bp"]),rtol=0,atol=1e-6)
        and (
            (not np.isfinite(oct.get("p_one",np.nan)) and not np.isfinite(float(prior["cluster_p_one"])))
            or np.isclose(oct.get("p_one",np.nan),float(prior["cluster_p_one"]),rtol=0,atol=1e-8)
        )
    )
    old_parity.append({
        "development_rank":rank,
        "expected_n":int(prior["n"]),"got_n":om["n"],
        "expected_mean_bp":float(prior["mean_bp"]),"got_mean_bp":om["mean_bp"],
        "expected_cluster_p_one":float(prior["cluster_p_one"]),
        "got_cluster_p_one":oct.get("p_one",np.nan),
        "parity_ok":bool(old_ok),
    })
    if not old_ok:
        raise RuntimeError(f"Old V93 reconstruction parity failed rank {rank}")

    years={}
    for year in (2023,2024,2025):
        yy=np.asarray(oos_times.year==year)
        years[year]=metrics(gn[yy])

    passed,pos,cov=pass_rule(nm,years)

    rec=prior.to_dict()
    rec.update({
        "n":nm["n"],
        "mean_bp":nm["mean_bp"],
        "net_1bp_mean_bp":nm["net_1bp_mean_bp"],
        "median_bp":nm["median_bp"],
        "win_rate_pct":nm["win_rate_pct"],
        "sum_pct":nm["sum_pct"],
        "max_drawdown_pct":nm["max_drawdown_pct"],
        "cluster_blocks":nct["clusters"],
        "cluster_p_one":nct.get("p_one",np.nan),
        "positive_net1bp_years":pos,
        "coverage_years_ge3signals":cov,
        "economic_oos_pass":passed,
    })
    for year in (2023,2024,2025):
        rec[f"y{year}_n"]=years[year]["n"]
        rec[f"y{year}_mean_bp"]=years[year]["mean_bp"]
        rec[f"y{year}_net1bp_mean_bp"]=years[year]["net_1bp_mean_bp"]

    affected_records[rank]=rec
    print(
        f"[GEF97D] affected {idx}/{len(affected_panel)} rank={rank} | "
        f"old={om['mean_bp']:.4f}bp n={om['n']} -> corrected={nm['mean_bp']:.4f}bp n={nm['n']} | pass={passed}",
        flush=True,
    )

pd.DataFrame(old_parity).to_csv(OUT/"AFFECTED_OLD_V93_PARITY.csv",index=False)
status(OUT,6,11,"old V93 reconstructed exactly for every affected hypothesis",affected=len(affected_records))

# ---------- assemble full corrected scored panel ----------
rows=[]
for row in old.to_dict("records"):
    rank=int(row["development_rank"])
    if rank in affected_records:
        rec=affected_records[rank]
        source="CORRECTED_USDCHF_TIME"
    else:
        rec=dict(row)
        source="UNCHANGED_FROM_V93_NO_USDCHF_DEPENDENCY"
    rec["repair_source"]=source
    rows.append(rec)

R=pd.DataFrame(rows)
R["bh_q_panel"]=bh_adjust(pd.to_numeric(R["cluster_p_one"],errors="coerce").to_numpy(dtype=float))
R["bh_q10_diagnostic"]=R["bh_q_panel"]<=0.10
R=R.sort_values(
    ["economic_oos_pass","net_1bp_mean_bp","cluster_p_one"],
    ascending=[False,False,True],
    kind="mergesort",
).reset_index(drop=True)
R.to_csv(OUT/"CORRECTED_FULL_V93_SCORED_PANEL.csv",index=False)

old_pass=set(old.loc[old["economic_oos_pass"].astype(bool),"development_rank"].astype(int))
new_pass=set(R.loc[R["economic_oos_pass"].astype(bool),"development_rank"].astype(int))
changed=sorted(old_pass.symmetric_difference(new_pass))
status(
    OUT,7,11,
    "full corrected V93 scored panel assembled and BH diagnostic recomputed",
    old_pass=sorted(old_pass),corrected_pass=sorted(new_pass),changed=changed,
)

# ---------- exact diff ----------
diff=[]
old_by=old.set_index(old["development_rank"].astype(int))
new_by=R.set_index(R["development_rank"].astype(int))
for rank in sorted(old["development_rank"].astype(int)):
    o=old_by.loc[rank]
    n=new_by.loc[rank]
    diff.append({
        "development_rank":rank,
        "affected_by_timestamp_repair":bool(rank in affected),
        "old_n":int(o["n"]),
        "corrected_n":int(n["n"]),
        "old_mean_bp":float(o["mean_bp"]),
        "corrected_mean_bp":float(n["mean_bp"]),
        "delta_mean_bp":float(n["mean_bp"]-o["mean_bp"]),
        "old_cluster_p_one":float(o["cluster_p_one"]),
        "corrected_cluster_p_one":float(n["cluster_p_one"]),
        "old_bh_q":float(o["bh_q_panel"]),
        "corrected_bh_q":float(n["bh_q_panel"]),
        "old_economic_pass":bool(o["economic_oos_pass"]),
        "corrected_economic_pass":bool(n["economic_oos_pass"]),
    })
D=pd.DataFrame(diff)
D.to_csv(OUT/"OLD_VS_CORRECTED_FULL_PANEL_DIFF.csv",index=False)
status(OUT,8,11,"full-panel old-vs-corrected diff written")

receipt={
    "run_id":RID,
    "status":"COMPLETE_V97D_FULL_V93_SCORED_PANEL_REPAIR",
    "engine_version":ENGINE_VERSION,
    "source_v93":V93.name,
    "source_v97b":V97B.name,
    "original_scored_hypotheses":len(old),
    "affected_ranks":affected,
    "unchanged_ranks":sorted(set(old["development_rank"].astype(int))-set(affected)),
    "old_economic_pass_ranks":sorted(old_pass),
    "corrected_economic_pass_ranks":sorted(new_pass),
    "economic_pass_status_changed_ranks":changed,
    "corrected_nominal_cluster_p05":int((pd.to_numeric(R["cluster_p_one"],errors="coerce")<=0.05).sum()),
    "corrected_bh_q10_diagnostic":int(R["bh_q10_diagnostic"].sum()),
    "panelwide_inference_complete":bool(r93.get("panelwide_inference_complete",False)),
    "unscored_original_ranks":r93.get("unscored_development_ranks",[]),
    "candidate_set_changed_by_script":False,
    "thresholds_retuned":False,
    "strategy_outcomes_used_to_choose_time_correction":False,
    "2026_accessed":False,
    "next":"STOP_FOR_HUMAN_REVIEW; FREEZE_NEW_2026_PROMOTION_SET_FROM_CORRECTED_FULL_PANEL_ONLY_AFTER_REVIEW",
}
write_json(OUT/"RUN_RECEIPT.json",receipt)
status(OUT,9,11,"repair receipt written")
status(OUT,10,11,"2026 remains protected; V94 old promotion freeze not silently replaced")
status(OUT,11,11,"DONE")

print("\n=== V97D RECEIPT ===")
print(json.dumps(receipt,indent=2))
print("\n=== V97D CORRECTED FULL V93 SCORED PANEL ===")
cols=[
    "development_rank","feature_i","state_i","feature_j","state_j","target","direction",
    "n","mean_bp","net_1bp_mean_bp","positive_net1bp_years",
    "cluster_p_one","bh_q_panel","economic_oos_pass","repair_source",
    "y2023_n","y2023_mean_bp","y2024_n","y2024_mean_bp","y2025_n","y2025_mean_bp",
]
print(R[cols].to_string(index=False))
print("\n=== V97D OLD VS CORRECTED DIFF ===")
print(D.to_string(index=False))
print("\nRUN:",OUT)
