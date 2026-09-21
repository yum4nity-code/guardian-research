from pathlib import Path
import pandas as pd
import numpy as np
import json
import math
import re
import hashlib
from scipy.stats import t as student_t

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v89"
BASE.mkdir(parents=True,exist_ok=True)

ENGINE_VERSION="V89.0"
PANEL_RANK=48
TRIAL_INDEX=39930001
FEATURE_A="price_EURUSD_ret_30m"
FEATURE_B="price_NSXUSD_ret_60m"
TARGET="XAGUSD_fwd_15m"
DIRECTION="SHORT"
BLOCK_DAYS=5
MIN_FAST_STATE=5000
VALID_START=pd.Timestamp("2018-01-01 00:00")
VALID_END=pd.Timestamp("2022-12-31 23:55")
KNOWN_REPL_START=pd.Timestamp("2014-01-01 00:00")
KNOWN_REPL_END=pd.Timestamp("2017-12-31 23:55")

PRIMARY_RULE={
    "endpoint":"joint condition excess return versus complement",
    "direction":"positive",
    "cluster_days":5,
    "one_sided_p_max":0.05,
    "hypothetical_cost_bp":1.0,
    "net_mean_after_cost_must_be_positive":True,
    "minimum_positive_years_of_5":3,
    "minimum_positive_incremental_years_of_5":3,
    "secondary_not_required_for_primary_pass":[
        "A x B interaction coefficient positive",
        "hour-of-week demeaned joint effect positive"
    ]
}

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def status(out,step,total,msg,**extra):
    payload={"engine_version":ENGINE_VERSION,"step":step,"steps":total,
             "percent":round(100*step/total,1),
             "timestamp_utc":pd.Timestamp.now("UTC").isoformat(),
             "message":msg,**extra}
    write_json(out/"LIVE_STATUS.json",payload)
    tail=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF89] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

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
    if not m:
        raise RuntimeError(f"Unsupported V89 feature {name}")
    sym,mins=m.group(1),int(m.group(2))
    k=mins//5
    return (P[sym]/P[sym].shift(k)-1).astype("float64")

def cluster_ols(y,X,blocks,coef_index):
    y=np.asarray(y,dtype=np.float64)
    X=np.asarray(X,dtype=np.float64)
    blocks=np.asarray(blocks)
    good=np.isfinite(y)&np.all(np.isfinite(X),axis=1)
    y=y[good]; X=X[good]; blocks=blocks[good]
    n=len(y); k=X.shape[1]
    if n<=k:
        return {"n":n,"clusters":0,"coef":np.nan,"se":np.nan,"t":np.nan,"p_one":np.nan,"p_two":np.nan}
    xtx=X.T@X
    if np.linalg.matrix_rank(xtx)<k:
        return {"n":n,"clusters":0,"coef":np.nan,"se":np.nan,"t":np.nan,"p_one":np.nan,"p_two":np.nan}
    inv=np.linalg.inv(xtx)
    beta=inv@(X.T@y)
    resid=y-X@beta
    uniq=np.unique(blocks)
    g=len(uniq)
    if g<8:
        return {"n":n,"clusters":g,"coef":float(beta[coef_index]),"se":np.nan,"t":np.nan,"p_one":np.nan,"p_two":np.nan}
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
        return {"n":n,"clusters":g,"coef":coef,"se":se,"t":np.nan,"p_one":np.nan,"p_two":np.nan}
    t=coef/se
    return {"n":n,"clusters":g,"coef":coef,"se":se,"t":float(t),
            "p_one":float(student_t.sf(t,df=g-1)),
            "p_two":float(2*student_t.sf(abs(t),df=g-1))}

def summarize(vals):
    x=np.asarray(vals,dtype=np.float64)
    x=x[np.isfinite(x)]
    if not len(x):
        return {"n":0,"mean_bp":np.nan,"median_bp":np.nan,"win_rate_pct":np.nan,
                "sum_pct":np.nan,"max_drawdown_pct":np.nan,
                "net_1bp_mean_bp":np.nan,"net_2bp_mean_bp":np.nan,"net_5bp_mean_bp":np.nan}
    if np.any(x<=-1):
        mdd=np.nan
    else:
        eq=np.cumprod(1+x); peak=np.maximum.accumulate(eq); mdd=float(np.min(eq/peak-1)*100)
    mean_bp=float(x.mean()*1e4)
    return {
        "n":len(x),
        "mean_bp":mean_bp,
        "median_bp":float(np.median(x)*1e4),
        "win_rate_pct":float((x>0).mean()*100),
        "sum_pct":float(x.sum()*100),
        "max_drawdown_pct":mdd,
        "net_1bp_mean_bp":mean_bp-1.0,
        "net_2bp_mean_bp":mean_bp-2.0,
        "net_5bp_mean_bp":mean_bp-5.0,
    }

def evaluate_window(times,y,A,B,label):
    J=A&B
    valid=np.isfinite(y)
    blocks=((times.normalize()-times[0].normalize()).days.to_numpy()//BLOCK_DAYS).astype(np.int16)

    desc={}
    masks={
        "unconditional":valid,
        "joint_AB":valid&J,
        "A_state":valid&A,
        "B_state":valid&B,
        "not_joint":valid&(~J),
        "A1_B0":valid&A&(~B),
        "A0_B1":valid&(~A)&B,
        "A0_B0":valid&(~A)&(~B),
    }
    for k,m in masks.items():
        desc[k]=summarize(np.where(m,y,np.nan))

    X1=np.column_stack([np.ones(len(y)),J.astype(float)])
    joint=cluster_ols(y,X1,blocks,1)

    X2=np.column_stack([np.ones(len(y)),A.astype(float),B.astype(float),J.astype(float)])
    inter=cluster_ols(y,X2,blocks,3)

    tmp=pd.DataFrame({"y":y,"joint":J},index=times)
    tmp=tmp[np.isfinite(tmp["y"].to_numpy())].copy()
    tmp["how"]=tmp.index.dayofweek*24+tmp.index.hour
    tmp["resid_how"]=tmp["y"]-tmp.groupby("how")["y"].transform("mean")
    how_blocks=((tmp.index.normalize()-times[0].normalize()).days.to_numpy()//BLOCK_DAYS).astype(np.int16)
    how=cluster_ols(
        tmp["resid_how"].to_numpy(),
        np.column_stack([np.ones(len(tmp)),tmp["joint"].astype(float).to_numpy()]),
        how_blocks,1
    )

    yearly=[]
    for year in sorted(set(times.year)):
        yy=np.asarray(times.year==year)
        jv=y[yy&valid&J]
        uv=y[yy&valid]
        yearly.append({
            "year":int(year),
            "joint_n":int(len(jv)),
            "joint_mean_bp":float(np.mean(jv)*1e4) if len(jv) else np.nan,
            "unconditional_mean_bp":float(np.mean(uv)*1e4) if len(uv) else np.nan,
            "joint_minus_unconditional_bp":float((np.mean(jv)-np.mean(uv))*1e4) if len(jv) and len(uv) else np.nan,
        })
    Y=pd.DataFrame(yearly)
    return {
        "label":label,
        "descriptive_groups":desc,
        "joint_vs_complement":{
            **joint,
            "coef_bp":joint["coef"]*1e4 if np.isfinite(joint["coef"]) else np.nan
        },
        "interaction_AxB":{
            **inter,
            "coef_bp":inter["coef"]*1e4 if np.isfinite(inter["coef"]) else np.nan
        },
        "hour_of_week_demeaned_joint":{
            **how,
            "coef_bp":how["coef"]*1e4 if np.isfinite(how["coef"]) else np.nan
        },
        "yearly":Y.to_dict(orient="records"),
        "positive_joint_years":int((Y["joint_mean_bp"]>0).sum()),
        "positive_incremental_years":int((Y["joint_minus_unconditional_bp"]>0).sum()),
    }

# ---------- load completed V88A; freeze BEFORE 2018 file access ----------
runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v88a").glob("GEF88A-*"))
runs=[p for p in runs if (p/"RUN_RECEIPT.json").exists()]
if not runs:
    raise RuntimeError("No completed V88A")
V88A=runs[-1]
r88a=json.loads((V88A/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r88a.get("status")!="COMPLETE_INCREMENTAL_ATTRIBUTION_2014_2017":
    raise RuntimeError(f"Latest V88A status {r88a.get('status')}")
if r88a.get("2018_plus_accessed") or r88a.get("2023_plus_accessed") or r88a.get("protected_2026_accessed"):
    raise RuntimeError("V88A later-window assertion violated")
if int(r88a["panel_rank"])!=PANEL_RANK or int(r88a["trial_index"])!=TRIAL_INDEX:
    raise RuntimeError("V88A primary hypothesis identity mismatch")

RID="GEF89-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID
OUT.mkdir(parents=True,exist_ok=False)
status(OUT,1,10,"V88A primary replicated edge loaded; 2018+ still unopened",source_v88a=V88A.name)

freeze={
    "run_id":RID,
    "status":"PRIMARY_HYPOTHESIS_FROZEN_BEFORE_2018",
    "source_v88a":V88A.name,
    "panel_rank":PANEL_RANK,
    "trial_index":TRIAL_INDEX,
    "feature_A":FEATURE_A,
    "state_A":"HI",
    "feature_B":FEATURE_B,
    "state_B":"HI",
    "target":TARGET,
    "direction":DIRECTION,
    "state_definition":"expanding z-score using all causal past values, shift(1), HI >= +1.0, min_periods=5000",
    "target_sampling":"15-minute forward return sampled on UTC minute modulo 15 == 0",
    "primary_rule":PRIMARY_RULE,
    "known_2014_2017_joint_mean_bp":float(r88a["descriptive_groups"]["joint_AB"]["mean_bp"]),
    "known_2014_2017_joint_excess_bp":float(r88a["joint_vs_complement_cluster_5d"]["coef_bp"]),
    "known_2014_2017_joint_excess_p_one":float(r88a["joint_vs_complement_cluster_5d"]["p_one"]),
    "2018_2022_values_accessed":False,
    "2023_plus_accessed":False,
    "protected_2026_accessed":False,
}
write_json(OUT/"PRIMARY_HYPOTHESIS_FREEZE.json",freeze)
freeze_sha=sha256(OUT/"PRIMARY_HYPOTHESIS_FREEZE.json")
status(OUT,2,10,"primary hypothesis physically frozen before validation",freeze_sha256=freeze_sha[:16])

# ---------- source presence preflight: existence only, no values ----------
missing=[]
for sym in ("EURUSD","NSXUSD","XAGUSD"):
    for year in range(2018,2023):
        p=ROOT/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
        if not p.exists():
            missing.append(str(p))
if missing:
    write_json(OUT/"RUN_RECEIPT.json",{
        "run_id":RID,"status":"STOP_MISSING_VALIDATION_FILES","missing":missing,
        "2018_2022_values_accessed":False,"2023_plus_accessed":False,"protected_2026_accessed":False
    })
    raise RuntimeError(f"Missing 2018-2022 files: {missing}")
status(OUT,3,10,"2018-2022 file presence confirmed; values not yet read",files_checked=15)

# ---------- resolve archived lineage for exact state continuity ----------
V88=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v88_replication"/r88a["source_v88"]
r88=json.loads((V88/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
PF=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v88"/r88["source_preflight"]
rpf=json.loads((PF/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V87=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v87"/rpf["source_v87"]
r87=json.loads((V87/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V86A=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v86a"/r87["source_v86a"]
r86a=json.loads((V86A/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V86=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v86"/r86a["source_v86"]
spec86=json.loads((V86/"FROZEN_V86_SPEC.json").read_text(encoding="utf-8"))
V85=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v85"/spec86["source_v85"]
design=json.loads((V85/"TRIAL_DESIGN.json").read_text(encoding="utf-8"))
state_meta=json.loads((V85/"STATE_CACHE_META.json").read_text(encoding="utf-8"))
V84C=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v84c"/design["source_v84c"]
r84=json.loads((V84C/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V83B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v83b"/r84["source_v83b"]
manifest=json.loads((V83B/"REPAIRED_ARCHITECTURE_MANIFEST.json").read_text(encoding="utf-8"))

F_hist=pd.read_parquet(manifest["price_state_5m_path"])
F_hist.index=pd.to_datetime(F_hist.index)
frozen_panel=pd.read_csv(PF/"FROZEN_2014_2017_REPLICATION_PANEL.csv")
fr=frozen_panel.loc[frozen_panel["panel_rank"]==PANEL_RANK]
if len(fr)!=1:
    raise RuntimeError("Primary hypothesis missing from frozen V88 panel")
fr=fr.iloc[0]
fi=int(fr["feature_i_index"]); fj=int(fr["feature_j_index"])
train_shape=tuple(state_meta["train_shape"]); hold_shape=tuple(state_meta["hold_shape"])
ST=np.memmap(V85/"STATE_TRAIN.bool.dat",mode="r",dtype=np.bool_,shape=train_shape)
SH=np.memmap(V85/"STATE_HOLD.bool.dat",mode="r",dtype=np.bool_,shape=hold_shape)
hist_rows=len(F_hist)
status(OUT,4,10,"archived 2010-2013 lineage loaded")

# ---------- NOW open through 2022, never 2023 ----------
warm_grid=pd.date_range("2013-12-01 00:00",VALID_END,freq="5min")
post2013_grid=pd.date_range("2014-01-01 00:00",VALID_END,freq="5min")
P=pd.DataFrame(index=warm_grid)
for sym in ("EURUSD","NSXUSD","XAGUSD"):
    raw=load_m1(sym,range(2013,2023))
    P[sym]=raw.resample("5min",label="right",closed="left").last().reindex(warm_grid)
status(OUT,5,10,"2014-2022 causal continuation materialized",rows=len(post2013_grid),markets=3)

FA=build_feature(FEATURE_A,P).reindex(post2013_grid)
FB=build_feature(FEATURE_B,P).reindex(post2013_grid)

def full_state(feature,feature_index,ext):
    full=pd.concat([pd.to_numeric(F_hist[feature],errors="coerce"),pd.to_numeric(ext,errors="coerce")])
    lo,hi=causal_states(full,MIN_FAST_STATE)
    exp_lo=np.concatenate([ST[feature_index,0,:],SH[feature_index,0,:]])
    exp_hi=np.concatenate([ST[feature_index,1,:],SH[feature_index,1,:]])
    ml=int(np.count_nonzero(lo[:hist_rows]!=exp_lo))
    mh=int(np.count_nonzero(hi[:hist_rows]!=exp_hi))
    if ml or mh:
        raise RuntimeError(f"2010-2013 state parity failed {feature}: LO={ml}, HI={mh}")
    return lo[hist_rows:],hi[hist_rows:]

_,A_hi=full_state(FEATURE_A,fi,FA)
_,B_hi=full_state(FEATURE_B,fj,FB)

# Build directional target once, writable.
raw_y=P["XAGUSD"].shift(-(15//5))/P["XAGUSD"]-1
y=np.array(-raw_y.reindex(post2013_grid),dtype=np.float64,copy=True)
if not y.flags.writeable:
    raise RuntimeError("V89 target array unexpectedly read-only")
minute=(post2013_grid.view("int64")//60_000_000_000).astype(np.int64)
y[(minute%15)!=0]=np.nan

# ---------- parity against known 2014-2017 before scoring 2018-2022 ----------
rep_sel=np.asarray((post2013_grid>=KNOWN_REPL_START)&(post2013_grid<=KNOWN_REPL_END))
rep_times=post2013_grid[rep_sel]
rep_y=np.array(y[rep_sel],dtype=np.float64,copy=True)
# Match V88 exactly: V88 had no 2018 prices, so a 2017 decision whose +15m target crosses
# into 2018 was unavailable. Keep that boundary unavailable for the parity check.
rep_y[(rep_times+pd.Timedelta(minutes=15))>KNOWN_REPL_END]=np.nan
rep=evaluate_window(rep_times,rep_y,A_hi[rep_sel],B_hi[rep_sel],"2014-2017 parity")

known_n=int(r88a["descriptive_groups"]["joint_AB"]["n"])
known_mean=float(r88a["descriptive_groups"]["joint_AB"]["mean_bp"])
known_excess=float(r88a["joint_vs_complement_cluster_5d"]["coef_bp"])
got_n=int(rep["descriptive_groups"]["joint_AB"]["n"])
got_mean=float(rep["descriptive_groups"]["joint_AB"]["mean_bp"])
got_excess=float(rep["joint_vs_complement"]["coef_bp"])
if got_n!=known_n or not np.isclose(got_mean,known_mean,rtol=0,atol=1e-9) or not np.isclose(got_excess,known_excess,rtol=0,atol=1e-9):
    raise RuntimeError(
        f"2014-2017 parity failed n {got_n}/{known_n}, mean {got_mean}/{known_mean}, excess {got_excess}/{known_excess}"
    )
status(OUT,6,10,"2014-2017 reproduction exact before validation scoring",joint_n=got_n,joint_mean_bp=round(got_mean,6),excess_bp=round(got_excess,6))

# ---------- independent 2018-2022 validation ----------
val_sel=np.asarray((post2013_grid>=VALID_START)&(post2013_grid<=VALID_END))
val_times=post2013_grid[val_sel]
val=evaluate_window(val_times,y[val_sel],A_hi[val_sel],B_hi[val_sel],"2018-2022 validation")
Y=pd.DataFrame(val["yearly"])
Y.to_csv(OUT/"VALIDATION_2018_2022_YEARLY.csv",index=False)

joint=val["descriptive_groups"]["joint_AB"]
excess=val["joint_vs_complement"]
primary_components={
    "joint_mean_positive":bool(joint["mean_bp"]>0),
    "net_after_1bp_positive":bool(joint["net_1bp_mean_bp"]>0),
    "joint_excess_positive":bool(excess["coef_bp"]>0),
    "joint_excess_one_sided_p_le_0p05":bool(np.isfinite(excess["p_one"]) and excess["p_one"]<=0.05),
    "positive_joint_years_ge_3":bool(val["positive_joint_years"]>=3),
    "positive_incremental_years_ge_3":bool(val["positive_incremental_years"]>=3),
}
primary_pass=all(primary_components.values())

validation={
    "run_id":RID,
    "status":"COMPLETE_PRIMARY_VALIDATION_2018_2022",
    "engine_version":ENGINE_VERSION,
    "source_v88a":V88A.name,
    "freeze_sha256":freeze_sha,
    "primary_hypothesis":freeze,
    "validation_window":"2018-2022",
    "joint_AB":joint,
    "joint_vs_complement_cluster_5d":val["joint_vs_complement"],
    "interaction_AxB_cluster_5d":val["interaction_AxB"],
    "hour_of_week_demeaned_joint_cluster_5d":val["hour_of_week_demeaned_joint"],
    "positive_joint_years":val["positive_joint_years"],
    "positive_incremental_years":val["positive_incremental_years"],
    "primary_pass_components":primary_components,
    "primary_validation_pass":primary_pass,
    "2018_2022_values_accessed":True,
    "2023_plus_accessed":False,
    "protected_2026_accessed":False,
    "next":"STOP_FOR_HUMAN_REVIEW_BEFORE_LOCKED_OOS_2023_2025"
}
write_json(OUT/"RUN_RECEIPT.json",validation)
status(
    OUT,7,10,"2018-2022 primary validation complete",
    joint_n=joint["n"],joint_mean_bp=round(joint["mean_bp"],4),
    net1bp=round(joint["net_1bp_mean_bp"],4),
    excess_bp=round(excess["coef_bp"],4),
    p_one=excess["p_one"],
)
status(OUT,8,10,"pre-frozen primary criteria evaluated",primary_validation_pass=primary_pass,positive_years=val["positive_joint_years"],incremental_years=val["positive_incremental_years"])
status(OUT,9,10,"2023-2025 locked OOS remains unopened")
status(OUT,10,10,"DONE")

print("\n=== V89 VALIDATION RECEIPT ===")
print(json.dumps(validation,indent=2))
print("\n=== 2018-2022 YEARLY VALIDATION ===")
print(Y.to_string(index=False))
print("\nRUN:",OUT)
