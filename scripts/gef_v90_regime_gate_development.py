from pathlib import Path
import pandas as pd
import numpy as np
import json
import math
import re
import hashlib
from scipy.stats import t as student_t

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v90"
BASE.mkdir(parents=True,exist_ok=True)

ENGINE_VERSION="V90.0"
MIN_FAST_STATE=5000
BLOCK_DAYS=5
TARGET="XAGUSD_fwd_15m"
DIRECTION="SHORT"
BASE_A="price_EURUSD_ret_30m"
BASE_B="price_NSXUSD_ret_60m"

ERAS=[
    ("E1_2010_2013",pd.Timestamp("2010-01-01"),pd.Timestamp("2013-12-31 23:55")),
    ("E2_2014_2017",pd.Timestamp("2014-01-01"),pd.Timestamp("2017-12-31 23:55")),
    ("E3_2018_2022",pd.Timestamp("2018-01-01"),pd.Timestamp("2022-12-31 23:55")),
]

# Frozen before the new development search. Single third-state gates only: 12 features x LO/HI = 24.
GATE_FEATURES=[
    "price_XAGUSD_rv_240m",
    "price_XAGUSD_trend_240m",
    "price_XAUUSD_rv_240m",
    "price_XAUUSD_trend_240m",
    "price_UDXUSD_rv_240m",
    "price_UDXUSD_trend_240m",
    "price_NSXUSD_rv_240m",
    "price_NSXUSD_trend_240m",
    "price_SPXUSD_rv_240m",
    "price_SPXUSD_trend_240m",
    "price_EURUSD_rv_240m",
    "price_EURUSD_trend_240m",
]
GATE_STATES=("LO","HI")

# Selection rule is frozen before outcomes are computed. P-values are reported, not used as a guillotine.
SELECTION_RULE={
    "min_gated_signals_each_era":10,
    "min_gated_signals_total":60,
    "full_development_net_after_1bp_positive":True,
    "latest_era_2018_2022_net_after_1bp_positive":True,
    "gross_mean_positive_all_3_eras":True,
    "incremental_gate_effect_positive_in_latest_era":True,
    "incremental_gate_effect_positive_in_at_least_2_of_3_eras":True,
    "ranking_if_multiple_eligible":[
        "maximize worst-era net-after-1bp mean",
        "then maximize full-development within-base incremental t-stat",
        "then maximize total gated signal count"
    ],
    "multiplicity":"BH q-values across the 24 within-base gate tests are diagnostic only; no candidate is killed solely by q-value",
    "if_none_eligible":"STOP. Do not relax thresholds post-hoc. Report near-misses only."
}

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def status(out,step,total,msg,**extra):
    payload={"engine_version":ENGINE_VERSION,"step":step,"steps":total,
             "percent":round(100*step/total,1),"timestamp_utc":pd.Timestamp.now("UTC").isoformat(),
             "message":msg,**extra}
    write_json(out/"LIVE_STATUS.json",payload)
    tail=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF90] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def causal_states(s,min_periods):
    s=pd.to_numeric(s,errors="coerce")
    mu=s.expanding(min_periods=min_periods).mean().shift(1)
    sd=s.expanding(min_periods=min_periods).std().shift(1).replace(0,np.nan)
    z=((s-mu)/sd).to_numpy(dtype=np.float64)
    finite=np.isfinite(z)
    return finite&(z<=-1.0),finite&(z>=1.0)

def load_m1(sym,years):
    parts=[]
    for y in years:
        if y>2022:
            raise RuntimeError("V90 refuses to load 2023+")
        p=ROOT/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
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
        q=pd.DataFrame({"utc":utc,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
        q=q[q["utc"].dt.year<=2022]
        parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    return q.set_index("utc")["px"]

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
    m=re.fullmatch(r"price_([A-Z]+)_trend_(\d+)m",name)
    if m:
        sym,mins=m.group(1),int(m.group(2)); k=mins//5
        return (P[sym]/P[sym].shift(k)-1).astype("float64")
    raise RuntimeError(f"Unsupported feature {name}")

def cluster_ols(y,X,blocks,coef_index):
    y=np.asarray(y,dtype=np.float64)
    X=np.asarray(X,dtype=np.float64)
    blocks=np.asarray(blocks)
    good=np.isfinite(y)&np.all(np.isfinite(X),axis=1)
    y=y[good]; X=X[good]; blocks=blocks[good]
    n=len(y); k=X.shape[1]
    if n<=k:
        return {"n":n,"clusters":0,"coef":np.nan,"se":np.nan,"t":np.nan,"p_one":np.nan}
    xtx=X.T@X
    if np.linalg.matrix_rank(xtx)<k:
        return {"n":n,"clusters":0,"coef":np.nan,"se":np.nan,"t":np.nan,"p_one":np.nan}
    inv=np.linalg.inv(xtx)
    beta=inv@(X.T@y)
    resid=y-X@beta
    uniq=np.unique(blocks)
    g=len(uniq)
    if g<8:
        return {"n":n,"clusters":g,"coef":float(beta[coef_index]),"se":np.nan,"t":np.nan,"p_one":np.nan}
    meat=np.zeros((k,k),dtype=np.float64)
    for b in uniq:
        sel=blocks==b
        score=X[sel].T@resid[sel]
        meat+=np.outer(score,score)
    corr=(g/(g-1.0))*((n-1.0)/(n-k))
    vcov=corr*(inv@meat@inv)
    se=float(math.sqrt(max(vcov[coef_index,coef_index],0.0)))
    coef=float(beta[coef_index])
    if not np.isfinite(se) or se<=0:
        return {"n":n,"clusters":g,"coef":coef,"se":se,"t":np.nan,"p_one":np.nan}
    t=coef/se
    return {"n":n,"clusters":g,"coef":coef,"se":se,"t":float(t),
            "p_one":float(student_t.sf(t,df=g-1))}

def summarize(x):
    x=np.asarray(x,dtype=np.float64)
    x=x[np.isfinite(x)]
    if not len(x):
        return {"n":0,"mean_bp":np.nan,"win_rate_pct":np.nan,"sum_pct":np.nan,"net1bp_mean_bp":np.nan}
    mean_bp=float(x.mean()*1e4)
    return {"n":int(len(x)),"mean_bp":mean_bp,"win_rate_pct":float((x>0).mean()*100),
            "sum_pct":float(x.sum()*100),"net1bp_mean_bp":mean_bp-1.0}

def bh_adjust(p):
    p=np.asarray(p,dtype=np.float64)
    out=np.full(len(p),np.nan)
    idx=np.flatnonzero(np.isfinite(p))
    if not len(idx):
        return out
    vals=p[idx]; order=np.argsort(vals); ranked=vals[order]
    adj=ranked*len(ranked)/np.arange(1,len(ranked)+1,dtype=np.float64)
    adj=np.minimum.accumulate(adj[::-1])[::-1]
    adj=np.clip(adj,0,1)
    out[idx[order]]=adj
    return out

# ---------- lineage + freeze before new outcomes ----------
runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v89").glob("GEF89-*"))
runs=[p for p in runs if (p/"RUN_RECEIPT.json").exists()]
if not runs:
    raise RuntimeError("No completed V89")
V89=runs[-1]
r89=json.loads((V89/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r89.get("status")!="COMPLETE_PRIMARY_VALIDATION_2018_2022":
    raise RuntimeError(f"Latest V89 status {r89.get('status')}")
if r89.get("2023_plus_accessed") or r89.get("protected_2026_accessed"):
    raise RuntimeError("V89 later-window access assertion violated")

RID="GEF90-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID
OUT.mkdir(parents=True,exist_ok=False)
status(OUT,1,12,"V89 loaded; 2023-2025 still locked",source_v89=V89.name)

freeze={
    "run_id":RID,
    "status":"V90_GATE_SEARCH_SPEC_FROZEN_BEFORE_SEARCH",
    "base_condition":f"{BASE_A} HI AND {BASE_B} HI -> {DIRECTION} {TARGET}",
    "development_window":"2010-2022 only",
    "eras":[x[0] for x in ERAS],
    "candidate_gate_features":GATE_FEATURES,
    "candidate_gate_states":list(GATE_STATES),
    "candidate_count":len(GATE_FEATURES)*len(GATE_STATES),
    "gate_definition":"same causal expanding z-score as original engine; LO <= -1, HI >= +1, shift(1), min_periods=5000",
    "incremental_test":"within base-edge opportunities, gated returns versus base-edge opportunities with gate off; 5-day cluster-robust OLS",
    "selection_rule":SELECTION_RULE,
    "2023_plus_accessed":False,
    "protected_2026_accessed":False,
}
write_json(OUT/"V90_GATE_SEARCH_FREEZE.json",freeze)
freeze_sha=sha256(OUT/"V90_GATE_SEARCH_FREEZE.json")
status(OUT,2,12,"gate universe + selection rule physically frozen",candidates=freeze["candidate_count"],freeze_sha256=freeze_sha[:16])

# Resolve original architecture/cache.
r88a=json.loads((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v88a"/r89["source_v88a"]/"RUN_RECEIPT.json").read_text())
V88=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v88_replication"/r88a["source_v88"]
r88=json.loads((V88/"RUN_RECEIPT.json").read_text())
PF=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v88"/r88["source_preflight"]
rpf=json.loads((PF/"RUN_RECEIPT.json").read_text())
V87=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v87"/rpf["source_v87"]
r87=json.loads((V87/"RUN_RECEIPT.json").read_text())
V86A=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v86a"/r87["source_v86a"]
r86a=json.loads((V86A/"RUN_RECEIPT.json").read_text())
V86=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v86"/r86a["source_v86"]
spec86=json.loads((V86/"FROZEN_V86_SPEC.json").read_text())
V85=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v85"/spec86["source_v85"]
design=json.loads((V85/"TRIAL_DESIGN.json").read_text())
state_meta=json.loads((V85/"STATE_CACHE_META.json").read_text())
catalog=pd.read_csv(V85/"FROZEN_ELIGIBLE_FEATURES.csv").reset_index(drop=True)
V84C=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v84c"/design["source_v84c"]
r84=json.loads((V84C/"RUN_RECEIPT.json").read_text())
V83B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v83b"/r84["source_v83b"]
manifest=json.loads((V83B/"REPAIRED_ARCHITECTURE_MANIFEST.json").read_text())

F_hist=pd.read_parquet(manifest["price_state_5m_path"])
Y_hist=pd.read_parquet(manifest["targets_5m_path"])
F_hist.index=pd.to_datetime(F_hist.index); Y_hist.index=pd.to_datetime(Y_hist.index)
train_shape=tuple(state_meta["train_shape"]); hold_shape=tuple(state_meta["hold_shape"])
ST=np.memmap(V85/"STATE_TRAIN.bool.dat",mode="r",dtype=np.bool_,shape=train_shape)
SH=np.memmap(V85/"STATE_HOLD.bool.dat",mode="r",dtype=np.bool_,shape=hold_shape)
hist_rows=len(F_hist)
if train_shape[2]+hold_shape[2]!=hist_rows:
    raise RuntimeError("Historical cache row mismatch")

feature_to_index={str(r.feature):i for i,r in catalog.iterrows()}
needed_features=[BASE_A,BASE_B]+GATE_FEATURES
missing_catalog=[f for f in needed_features if f not in feature_to_index]
if missing_catalog:
    raise RuntimeError(f"Frozen V85 catalog missing gate features: {missing_catalog}")
status(OUT,3,12,"original feature lineage resolved",features=len(needed_features))

# File presence only before reading later development data.
symbols=set()
for feat in needed_features:
    m=re.match(r"price_([A-Z]+)_",feat)
    if m:
        symbols.add(m.group(1))
symbols.add("XAGUSD")
missing=[]
for sym in sorted(symbols):
    for year in range(2014,2023):
        p=ROOT/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
        if not p.exists():
            missing.append(str(p))
if missing:
    raise RuntimeError(f"Missing V90 development files: {missing}")
status(OUT,4,12,"2014-2022 source presence confirmed",markets=len(symbols),files_checked=len(symbols)*9)

# ---------- reconstruct 2014-2022 features and require exact 2010-2013 parity ----------
warm_grid=pd.date_range("2013-12-01 00:00","2022-12-31 23:55",freq="5min")
ext_grid=pd.date_range("2014-01-01 00:00","2022-12-31 23:55",freq="5min")
P=pd.DataFrame(index=warm_grid)
for i,sym in enumerate(sorted(symbols),1):
    raw=load_m1(sym,range(2013,2023))
    P[sym]=raw.resample("5min",label="right",closed="left").last().reindex(warm_grid)
    print(f"[GEF90] market {i}/{len(symbols)} {sym}",flush=True)
status(OUT,5,12,"2014-2022 price continuation materialized",rows=len(ext_grid))

ext_features={}
state_hist={}
state_ext={}
parity=[]
for idx,feat in enumerate(needed_features,1):
    ext=build_feature(feat,P).reindex(ext_grid)
    ext_features[feat]=ext
    fi=feature_to_index[feat]
    full=pd.concat([pd.to_numeric(F_hist[feat],errors="coerce"),pd.to_numeric(ext,errors="coerce")])
    lo,hi=causal_states(full,MIN_FAST_STATE)
    expected_lo=np.concatenate([ST[fi,0,:],SH[fi,0,:]])
    expected_hi=np.concatenate([ST[fi,1,:],SH[fi,1,:]])
    ml=int(np.count_nonzero(lo[:hist_rows]!=expected_lo))
    mh=int(np.count_nonzero(hi[:hist_rows]!=expected_hi))
    parity.append({"feature":feat,"lo_mismatch":ml,"hi_mismatch":mh})
    if ml or mh:
        raise RuntimeError(f"State parity failed {feat}: LO={ml}, HI={mh}")
    state_hist[(feat,"LO")]=expected_lo
    state_hist[(feat,"HI")]=expected_hi
    state_ext[(feat,"LO")]=lo[hist_rows:]
    state_ext[(feat,"HI")]=hi[hist_rows:]
    if idx%4==0 or idx==len(needed_features):
        print(f"[GEF90] state parity {idx}/{len(needed_features)}",flush=True)
pd.DataFrame(parity).to_csv(OUT/"STATE_PARITY_2010_2013.csv",index=False)
status(OUT,6,12,"all base + gate states reproduce 2010-2013 exactly",features=len(parity),mismatches=0)

# ---------- unified 2010-2022 base edge target ----------
hist_times=F_hist.index
all_times=hist_times.append(ext_grid)
base_hist=state_hist[(BASE_A,"HI")] & state_hist[(BASE_B,"HI")]
base_ext=state_ext[(BASE_A,"HI")] & state_ext[(BASE_B,"HI")]
base=np.concatenate([base_hist,base_ext])

yh=np.array(-pd.to_numeric(Y_hist[TARGET],errors="coerce"),dtype=np.float64,copy=True)
minute_h=(hist_times.view("int64")//60_000_000_000).astype(np.int64)
yh[(minute_h%15)!=0]=np.nan

raw_ext=P["XAGUSD"].shift(-(15//5))/P["XAGUSD"]-1
ye=np.array(-raw_ext.reindex(ext_grid),dtype=np.float64,copy=True)
minute_e=(ext_grid.view("int64")//60_000_000_000).astype(np.int64)
ye[(minute_e%15)!=0]=np.nan
y=np.concatenate([yh,ye])
valid=np.isfinite(y)
status(OUT,7,12,"unified 2010-2022 base-edge panel built",base_opportunities=int((base&valid).sum()))

# ---------- evaluate frozen 24 regime gates ----------
records=[]
full_blocks=((all_times.normalize()-pd.Timestamp("2010-01-01")).days.to_numpy()//BLOCK_DAYS).astype(np.int16)

for feat in GATE_FEATURES:
    for st in GATE_STATES:
        gate=np.concatenate([state_hist[(feat,st)],state_ext[(feat,st)]])
        gated=base&gate&valid
        gateoff=base&(~gate)&valid

        full_stats=summarize(np.where(gated,y,np.nan))

        # Incremental gate effect strictly inside base-edge opportunities.
        base_valid=base&valid
        yb=y[base_valid]
        gb=gate[base_valid].astype(float)
        bb=full_blocks[base_valid]
        inc=cluster_ols(yb,np.column_stack([np.ones(len(yb)),gb]),bb,1)

        rec={
            "gate_feature":feat,
            "gate_state":st,
            "total_n":full_stats["n"],
            "full_mean_bp":full_stats["mean_bp"],
            "full_net1bp_mean_bp":full_stats["net1bp_mean_bp"],
            "full_win_rate_pct":full_stats["win_rate_pct"],
            "full_sum_pct":full_stats["sum_pct"],
            "incremental_coef_bp":inc["coef"]*1e4 if np.isfinite(inc["coef"]) else np.nan,
            "incremental_t":inc["t"],
            "incremental_p_one":inc["p_one"],
            "incremental_clusters":inc["clusters"],
        }

        positive_gross_eras=0
        positive_inc_eras=0
        era_net=[]
        era_ns=[]
        for label,start,end in ERAS:
            sel=np.asarray((all_times>=start)&(all_times<=end))
            gs=summarize(np.where(sel&gated,y,np.nan))
            era_net.append(gs["net1bp_mean_bp"])
            era_ns.append(gs["n"])

            bv=sel&base&valid
            yy=y[bv]
            gg=gate[bv].astype(float)
            blocks=((all_times[bv].normalize()-start.normalize()).days.to_numpy()//BLOCK_DAYS).astype(np.int16)
            ei=cluster_ols(yy,np.column_stack([np.ones(len(yy)),gg]),blocks,1) if len(yy) else {"coef":np.nan}
            eibp=ei["coef"]*1e4 if np.isfinite(ei.get("coef",np.nan)) else np.nan

            rec[f"{label}_n"]=gs["n"]
            rec[f"{label}_mean_bp"]=gs["mean_bp"]
            rec[f"{label}_net1bp_mean_bp"]=gs["net1bp_mean_bp"]
            rec[f"{label}_incremental_bp"]=eibp
            if np.isfinite(gs["mean_bp"]) and gs["mean_bp"]>0:
                positive_gross_eras+=1
            if np.isfinite(eibp) and eibp>0:
                positive_inc_eras+=1

        rec["positive_gross_eras"]=positive_gross_eras
        rec["positive_incremental_eras"]=positive_inc_eras
        rec["worst_era_net1bp_mean_bp"]=float(np.nanmin(era_net)) if np.isfinite(np.asarray(era_net,dtype=float)).any() else np.nan
        rec["min_era_n"]=int(min(era_ns))

        rec["eligible"]=bool(
            rec["total_n"]>=SELECTION_RULE["min_gated_signals_total"]
            and rec["min_era_n"]>=SELECTION_RULE["min_gated_signals_each_era"]
            and np.isfinite(rec["full_net1bp_mean_bp"]) and rec["full_net1bp_mean_bp"]>0
            and np.isfinite(rec["E3_2018_2022_net1bp_mean_bp"]) and rec["E3_2018_2022_net1bp_mean_bp"]>0
            and rec["positive_gross_eras"]==3
            and np.isfinite(rec["E3_2018_2022_incremental_bp"]) and rec["E3_2018_2022_incremental_bp"]>0
            and rec["positive_incremental_eras"]>=2
        )
        records.append(rec)

R=pd.DataFrame(records)
R["bh_q_incremental"]=bh_adjust(R["incremental_p_one"].to_numpy(dtype=float))
status(OUT,8,12,"24 frozen regime gates evaluated",eligible=int(R["eligible"].sum()))

# Fixed ranking: eligible first; worst-era net1bp; t-stat; n.
R=R.sort_values(
    ["eligible","worst_era_net1bp_mean_bp","incremental_t","total_n"],
    ascending=[False,False,False,False],
    kind="mergesort"
).reset_index(drop=True)
R["development_rank"]=np.arange(1,len(R)+1)
R.to_csv(OUT/"V90_GATE_RESULTS_2010_2022.csv",index=False)

eligible=R[R["eligible"]].copy()
selected=None
if len(eligible):
    selected=eligible.iloc[0].to_dict()
    freeze_selected={
        "run_id":RID,
        "status":"V90_REGIME_GATE_SELECTED_AND_FROZEN_FOR_LOCKED_OOS",
        "source_v89":V89.name,
        "base_condition":freeze["base_condition"],
        "selected_gate_feature":selected["gate_feature"],
        "selected_gate_state":selected["gate_state"],
        "selection_rule":SELECTION_RULE,
        "development_rank":int(selected["development_rank"]),
        "development_metrics":selected,
        "2023_plus_accessed":False,
        "protected_2026_accessed":False,
    }
    write_json(OUT/"SELECTED_GATE_FREEZE_BEFORE_2023.json",freeze_selected)
    selected_sha=sha256(OUT/"SELECTED_GATE_FREEZE_BEFORE_2023.json")
    next_step="V91_LOCKED_OOS_2023_2025_ON_FROZEN_REGIME_GATED_EDGE"
    status(OUT,9,12,"one regime gate frozen for locked OOS",gate=f"{selected['gate_feature']} {selected['gate_state']}",freeze_sha256=selected_sha[:16])
else:
    selected_sha=None
    next_step="STOP_NO_PREDEFINED_GATE_ELIGIBLE_DO_NOT_RELAX_THRESHOLDS"
    status(OUT,9,12,"no gate met frozen economic/temporal rule; thresholds not relaxed")

# Near-miss score only for diagnosis; not selection if none eligible.
def count_conditions(row):
    checks=[
        row["total_n"]>=SELECTION_RULE["min_gated_signals_total"],
        row["min_era_n"]>=SELECTION_RULE["min_gated_signals_each_era"],
        np.isfinite(row["full_net1bp_mean_bp"]) and row["full_net1bp_mean_bp"]>0,
        np.isfinite(row["E3_2018_2022_net1bp_mean_bp"]) and row["E3_2018_2022_net1bp_mean_bp"]>0,
        row["positive_gross_eras"]==3,
        np.isfinite(row["E3_2018_2022_incremental_bp"]) and row["E3_2018_2022_incremental_bp"]>0,
        row["positive_incremental_eras"]>=2,
    ]
    return int(sum(checks))
R["criteria_met_0_to_7"]=R.apply(count_conditions,axis=1)
R.to_csv(OUT/"V90_GATE_RESULTS_2010_2022.csv",index=False)

receipt={
    "run_id":RID,
    "status":"COMPLETE_V90_REGIME_GATE_DEVELOPMENT",
    "engine_version":ENGINE_VERSION,
    "source_v89":V89.name,
    "gate_search_freeze_sha256":freeze_sha,
    "candidate_gates":len(R),
    "eligible_gates":int(R["eligible"].sum()),
    "selected_gate":None if selected is None else {
        "feature":selected["gate_feature"],
        "state":selected["gate_state"],
        "development_rank":int(selected["development_rank"]),
        "full_net1bp_mean_bp":float(selected["full_net1bp_mean_bp"]),
        "E1_net1bp_mean_bp":float(selected["E1_2010_2013_net1bp_mean_bp"]),
        "E2_net1bp_mean_bp":float(selected["E2_2014_2017_net1bp_mean_bp"]),
        "E3_net1bp_mean_bp":float(selected["E3_2018_2022_net1bp_mean_bp"]),
        "incremental_coef_bp":float(selected["incremental_coef_bp"]),
        "incremental_p_one":float(selected["incremental_p_one"]) if np.isfinite(selected["incremental_p_one"]) else None,
        "bh_q_incremental":float(selected["bh_q_incremental"]) if np.isfinite(selected["bh_q_incremental"]) else None,
        "selected_freeze_sha256":selected_sha,
    },
    "pvalues_are_diagnostic_not_guillotine":True,
    "2023_plus_accessed":False,
    "protected_2026_accessed":False,
    "next":next_step,
}
write_json(OUT/"RUN_RECEIPT.json",receipt)
status(OUT,10,12,"receipt written",eligible=receipt["eligible_gates"],next=next_step)
status(OUT,11,12,"2023-2025 locked OOS remains unopened")
status(OUT,12,12,"DONE")

print("\n=== V90 RECEIPT ===")
print(json.dumps(receipt,indent=2))
print("\n=== V90 TOP 12 REGIME GATES ===")
show=[
    "development_rank","eligible","gate_feature","gate_state","total_n",
    "full_mean_bp","full_net1bp_mean_bp","worst_era_net1bp_mean_bp",
    "E1_2010_2013_n","E1_2010_2013_mean_bp","E1_2010_2013_net1bp_mean_bp","E1_2010_2013_incremental_bp",
    "E2_2014_2017_n","E2_2014_2017_mean_bp","E2_2014_2017_net1bp_mean_bp","E2_2014_2017_incremental_bp",
    "E3_2018_2022_n","E3_2018_2022_mean_bp","E3_2018_2022_net1bp_mean_bp","E3_2018_2022_incremental_bp",
    "incremental_coef_bp","incremental_p_one","bh_q_incremental","criteria_met_0_to_7"
]
print(R[show].head(12).to_string(index=False))
print("\nRUN:",OUT)
