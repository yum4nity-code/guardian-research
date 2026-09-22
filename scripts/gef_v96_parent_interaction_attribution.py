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
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v96"
BASE.mkdir(parents=True,exist_ok=True)

ENGINE_VERSION="V96.0"
MIN_FAST_STATE=5000
BLOCK_DAYS=5
AUDIT_END=pd.Timestamp("2025-12-31 23:55")

WINDOWS=[
    ("TRAIN_2010_2012",pd.Timestamp("2010-01-01 00:00"),pd.Timestamp("2012-12-31 23:55")),
    ("HOLD_2013",pd.Timestamp("2013-01-01 00:00"),pd.Timestamp("2013-12-31 23:55")),
    ("E2_2014_2017",pd.Timestamp("2014-01-01 00:00"),pd.Timestamp("2017-12-31 23:55")),
    ("E3_2018_2022",pd.Timestamp("2018-01-01 00:00"),pd.Timestamp("2022-12-31 23:55")),
    ("OOS_2023_2025",pd.Timestamp("2023-01-01 00:00"),AUDIT_END),
]

AUDIT_SPEC={
    "candidate_set":"exact V94 frozen 3; no additions/removals",
    "purpose":"determine whether the PAIR condition adds information beyond either parent state and target unconditional drift",
    "estimands":[
        "joint versus complement",
        "A x B interaction / difference-in-differences",
        "A added value conditional on B",
        "B added value conditional on A",
        "four binary-state cell means",
    ],
    "inference":"5-day cluster-robust OLS; diagnostic because 2023-2025 was already used for promotion",
    "decision_effect":"none; V94 2026 frozen panel remains all 3 regardless of V96",
    "no_2026_access":True,
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
        f"[GEF96] {step}/{total_steps} {100*step/total_steps:.0f}% | {msg}"
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
    raise RuntimeError(f"Unsupported feature {name}")

def feature_market(feature):
    m=re.match(r"price_([A-Z]+)_",str(feature))
    return m.group(1) if m else None

def target_market(target):
    return str(target).split("_fwd_",1)[0]

def load_m1(sym,years):
    parts=[]
    for year in years:
        if year>2025:
            raise RuntimeError("V96 refuses 2026+")
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
        q=pd.DataFrame({"utc":utc,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
        q=q[q["utc"].dt.year<=2025]
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
    y[(grid+pd.Timedelta(minutes=mins))>AUDIT_END]=np.nan
    return y,mins

def simple_stats(vals):
    x=np.asarray(vals,dtype=np.float64)
    x=x[np.isfinite(x)]
    if not len(x):
        return {"n":0,"mean_bp":np.nan,"win_rate_pct":np.nan}
    return {
        "n":int(len(x)),
        "mean_bp":float(x.mean()*1e4),
        "win_rate_pct":float((x>0).mean()*100),
    }

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
    uniq=np.unique(blocks); g=len(uniq)
    coef=float(beta[coef_index])
    if g<8:
        return {"n":n,"clusters":g,"coef":coef,"se":np.nan,"t":np.nan,"p_one":np.nan,"p_two":np.nan}
    meat=np.zeros((k,k),dtype=np.float64)
    for b in uniq:
        sel=blocks==b
        score=X[sel].T@resid[sel]
        meat+=np.outer(score,score)
    corr=(g/(g-1.0))*((n-1.0)/(n-k))
    vcov=corr*(inv@meat@inv)
    se=float(math.sqrt(max(vcov[coef_index,coef_index],0.0)))
    if not np.isfinite(se) or se<=0:
        return {"n":n,"clusters":g,"coef":coef,"se":se,"t":np.nan,"p_one":np.nan,"p_two":np.nan}
    t=coef/se
    return {
        "n":n,"clusters":g,"coef":coef,"se":se,"t":float(t),
        "p_one":float(student_t.sf(t,df=g-1)),
        "p_two":float(2*student_t.sf(abs(t),df=g-1)),
    }

def effect_bp(result):
    x=result.get("coef",np.nan)
    return float(x*1e4) if np.isfinite(x) else np.nan

def eval_window(times,y,A,B,start,end):
    horizon_minutes=None
    valid=np.isfinite(y)
    J=A&B
    base=np.asarray((times>=start)&(times<=end))
    m=base&valid
    blocks=((times.normalize()-pd.Timestamp("2010-01-01")).days.to_numpy()//BLOCK_DAYS).astype(np.int32)

    groups={
        "unconditional":m,
        "joint_A1B1":m&J,
        "A1B0":m&A&(~B),
        "A0B1":m&(~A)&B,
        "A0B0":m&(~A)&(~B),
        "A_state":m&A,
        "B_state":m&B,
        "not_joint":m&(~J),
    }
    desc={k:simple_stats(np.where(v,y,np.nan)) for k,v in groups.items()}

    # Joint versus complement.
    Xj=np.column_stack([np.ones(len(y)),J.astype(float)])
    joint=cluster_ols(np.where(m,y,np.nan),Xj,blocks,1)

    # Difference-in-differences interaction.
    Xi=np.column_stack([np.ones(len(y)),A.astype(float),B.astype(float),J.astype(float)])
    inter=cluster_ols(np.where(m,y,np.nan),Xi,blocks,3)

    # A's incremental value when B is already active.
    mb=m&B
    if mb.any():
        addA=cluster_ols(
            np.where(mb,y,np.nan),
            np.column_stack([np.ones(len(y)),A.astype(float)]),
            blocks,1
        )
    else:
        addA={"n":0,"clusters":0,"coef":np.nan,"se":np.nan,"t":np.nan,"p_one":np.nan,"p_two":np.nan}

    # B's incremental value when A is already active.
    ma=m&A
    if ma.any():
        addB=cluster_ols(
            np.where(ma,y,np.nan),
            np.column_stack([np.ones(len(y)),B.astype(float)]),
            blocks,1
        )
    else:
        addB={"n":0,"clusters":0,"coef":np.nan,"se":np.nan,"t":np.nan,"p_one":np.nan,"p_two":np.nan}

    return {
        "descriptive_groups":desc,
        "joint_vs_complement":{**joint,"coef_bp":effect_bp(joint)},
        "interaction_AxB":{**inter,"coef_bp":effect_bp(inter)},
        "A_added_given_B":{**addA,"coef_bp":effect_bp(addA)},
        "B_added_given_A":{**addB,"coef_bp":effect_bp(addB)},
    }

# ---------- exact V94 panel ----------
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
    raise RuntimeError("V94 incomplete")
if r94.get("2026_values_accessed") or frz94.get("2026_values_accessed"):
    raise RuntimeError("2026 access assertion violated")
if sha256(panel_path)!=frz94["panel_sha256"]:
    raise RuntimeError("V94 panel hash mismatch")
if len(panel)!=3:
    raise RuntimeError("V96 expects exact frozen 3")

V93=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v93"/r94["source_v93"]
r93=json.loads((V93/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V92=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v92"/r94["source_v92"]
r92=json.loads((V92/"RUN_RECEIPT.json").read_text(encoding="utf-8"))

RID="GEF96-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID
OUT.mkdir(parents=True,exist_ok=False)
status(
    OUT,1,10,
    "exact frozen 3 loaded; 2026 untouched",
    source_v94=V94.name,
    development_ranks=panel["development_rank"].astype(int).tolist(),
)

spec={
    "run_id":RID,
    "status":"V96_PARENT_INTERACTION_AUDIT_SPEC_FROZEN",
    "source_v94":V94.name,
    "panel_sha256":frz94["panel_sha256"],
    "audit_spec":AUDIT_SPEC,
    "2026_values_accessed":False,
}
write_json(OUT/"V96_AUDIT_FREEZE.json",spec)
status(OUT,2,10,"parent/interactions audit spec frozen; no candidate can be removed")

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

missing=[]
for sym in sorted(needed_markets):
    for year in range(2013,2026):
        p=ROOT/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
        if not p.exists():
            missing.append(str(p))
if missing:
    raise RuntimeError(f"Missing required 2013-2025 files: {missing}")
status(OUT,3,10,"2013-2025 source presence confirmed",markets=len(needed_markets))

# ---------- reconstruct ----------
warm_grid=pd.date_range("2013-12-01 00:00",AUDIT_END,freq="5min")
ext_grid=pd.date_range("2014-01-01 00:00",AUDIT_END,freq="5min")
P=pd.DataFrame(index=warm_grid)
tp=time.time()
for i,sym in enumerate(sorted(needed_markets),1):
    raw=load_m1(sym,range(2013,2026))
    P[sym]=raw.resample("5min",label="right",closed="left").last().reindex(warm_grid).astype("float64")
    elapsed=time.time()-tp
    rate=i/max(elapsed,1e-9)
    eta=(len(needed_markets)-i)/max(rate,1e-9)
    print(
        f"[GEF96] market {i}/{len(needed_markets)} {sym} | "
        f"elapsed={elapsed/60:.1f}m eta={eta/60:.1f}m",
        flush=True,
    )
status(OUT,4,10,"2014-2025 causal price continuation materialized",rows=len(ext_grid))

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
        print(f"[GEF96] state parity {i}/{len(needed_features)}",flush=True)

all_times=Fhist.index.append(ext_grid)
status(OUT,5,10,"2010-2013 state parity exact; unified 2010-2025 states ready",features=len(needed_features))

targets={}
target_horizon={}
for target in needed_targets:
    yh=np.array(pd.to_numeric(Yhist[target],errors="coerce"),dtype=np.float64,copy=True)
    mins=int(str(target).rsplit("_fwd_",1)[1].rstrip("m"))
    hm=(Fhist.index.view("int64")//60_000_000_000).astype(np.int64)
    yh[(hm%mins)!=0]=np.nan
    ye,_=target_array(P,ext_grid,target)
    targets[target]=np.concatenate([yh,ye])
    target_horizon[target]=mins

# ---------- exact V93 parity ----------
v93=pd.read_csv(V93/"LOCKED_OOS_2023_2025_SCORED.csv")
for r in panel.itertuples(index=False):
    row=v93[v93["development_rank"].astype(int)==int(r.development_rank)]
    if len(row)!=1:
        raise RuntimeError(f"V93 row missing rank {r.development_rank}")
    exp=row.iloc[0]
    A=states[(r.feature_i,r.state_i)]
    B=states[(r.feature_j,r.state_j)]
    sign=1.0 if r.direction=="LONG" else -1.0
    y=sign*targets[r.target]
    h=pd.Timedelta(minutes=target_horizon[r.target])
    m=(all_times>=pd.Timestamp("2023-01-01"))&(all_times<=AUDIT_END)&((all_times+h)<=AUDIT_END)
    got=simple_stats(np.where(A&B&m,y,np.nan))
    if got["n"]!=int(exp["n"]) or not np.isclose(got["mean_bp"],float(exp["mean_bp"]),rtol=0,atol=1e-6):
        raise RuntimeError(
            f"V93 parity failed rank {r.development_rank}: "
            f"n {got['n']}/{int(exp['n'])} mean {got['mean_bp']}/{float(exp['mean_bp'])}"
        )
status(OUT,6,10,"V93 OOS parity exact for all frozen 3")

# ---------- attribution across all pre-2026 windows ----------
rows=[]
full_detail={}
for idx,r in enumerate(panel.itertuples(index=False),1):
    A=states[(r.feature_i,r.state_i)]
    B=states[(r.feature_j,r.state_j)]
    sign=1.0 if r.direction=="LONG" else -1.0
    y=sign*targets[r.target]
    h=pd.Timedelta(minutes=target_horizon[r.target])

    detail={}
    for label,start,end in WINDOWS:
        # Explicit temporal boundary: no target crosses into the next era.
        ym=np.array(y,dtype=np.float64,copy=True)
        ym[(all_times+h)>end]=np.nan
        res=eval_window(all_times,ym,A,B,start,end)
        detail[label]=res

        d=res["descriptive_groups"]
        joint=res["joint_vs_complement"]
        inter=res["interaction_AxB"]
        addA=res["A_added_given_B"]
        addB=res["B_added_given_A"]
        rows.append({
            "development_rank":int(r.development_rank),
            "feature_A":r.feature_i,
            "state_A":r.state_i,
            "feature_B":r.feature_j,
            "state_B":r.state_j,
            "target":r.target,
            "direction":r.direction,
            "window":label,
            "joint_n":d["joint_A1B1"]["n"],
            "joint_mean_bp":d["joint_A1B1"]["mean_bp"],
            "A1B0_n":d["A1B0"]["n"],
            "A1B0_mean_bp":d["A1B0"]["mean_bp"],
            "A0B1_n":d["A0B1"]["n"],
            "A0B1_mean_bp":d["A0B1"]["mean_bp"],
            "A0B0_n":d["A0B0"]["n"],
            "A0B0_mean_bp":d["A0B0"]["mean_bp"],
            "unconditional_mean_bp":d["unconditional"]["mean_bp"],
            "joint_vs_complement_bp":joint["coef_bp"],
            "joint_vs_complement_p_one":joint["p_one"],
            "interaction_AxB_bp":inter["coef_bp"],
            "interaction_AxB_p_one":inter["p_one"],
            "A_added_given_B_bp":addA["coef_bp"],
            "A_added_given_B_p_one":addA["p_one"],
            "B_added_given_A_bp":addB["coef_bp"],
            "B_added_given_A_p_one":addB["p_one"],
        })

    full_detail[str(int(r.development_rank))]=detail
    o=detail["OOS_2023_2025"]
    print(
        f"[GEF96] {idx}/3 rank={int(r.development_rank)} "
        f"OOS joint={o['descriptive_groups']['joint_A1B1']['mean_bp']:.3f}bp "
        f"A|B={o['A_added_given_B']['coef_bp']:.3f}bp "
        f"B|A={o['B_added_given_A']['coef_bp']:.3f}bp "
        f"AxB={o['interaction_AxB']['coef_bp']:.3f}bp",
        flush=True,
    )

R=pd.DataFrame(rows)
R.to_csv(OUT/"PARENT_INTERACTION_ATTRIBUTION_ALL_WINDOWS.csv",index=False)
write_json(OUT/"PARENT_INTERACTION_DETAIL.json",full_detail)
status(OUT,7,10,"parent-state and interaction attribution complete",rows=len(R))

# ---------- compact OOS readout, still diagnostic ----------
O=R[R["window"]=="OOS_2023_2025"].copy().sort_values("development_rank")
O["A_adds_given_B_positive"]=O["A_added_given_B_bp"]>0
O["B_adds_given_A_positive"]=O["B_added_given_A_bp"]>0
O["interaction_positive"]=O["interaction_AxB_bp"]>0
O["joint_exceeds_unconditional"]=O["joint_vs_complement_bp"]>0
O.to_csv(OUT/"OOS_2023_2025_ATTRIBUTION_SUMMARY.csv",index=False)

flags=[]
for r in O.itertuples(index=False):
    flags.append({
        "development_rank":int(r.development_rank),
        "joint_mean_bp":float(r.joint_mean_bp),
        "A_added_given_B_bp":float(r.A_added_given_B_bp),
        "A_added_given_B_p_one":float(r.A_added_given_B_p_one) if np.isfinite(r.A_added_given_B_p_one) else None,
        "B_added_given_A_bp":float(r.B_added_given_A_bp),
        "B_added_given_A_p_one":float(r.B_added_given_A_p_one) if np.isfinite(r.B_added_given_A_p_one) else None,
        "interaction_AxB_bp":float(r.interaction_AxB_bp),
        "interaction_AxB_p_one":float(r.interaction_AxB_p_one) if np.isfinite(r.interaction_AxB_p_one) else None,
        "note":"diagnostic only; candidate remains in frozen 2026 panel regardless",
    })
write_json(OUT/"OOS_ATTRIBUTION_FLAGS.json",flags)
status(OUT,8,10,"OOS attribution summary written; frozen 3 unchanged")

receipt={
    "run_id":RID,
    "status":"COMPLETE_V96_PARENT_INTERACTION_ATTRIBUTION",
    "engine_version":ENGINE_VERSION,
    "source_v94":V94.name,
    "frozen_2026_panel_sha256":frz94["panel_sha256"],
    "audited_candidates":len(panel),
    "candidate_set_changed":False,
    "thresholds_retuned":False,
    "trades_deleted":False,
    "2026_values_accessed":False,
    "next":"HUMAN_REVIEW_V96; KEEP_V94_FROZEN_3; DO_NOT_OPEN_2026",
}
write_json(OUT/"RUN_RECEIPT.json",receipt)
status(OUT,9,10,"receipt written")
status(OUT,10,10,"DONE; 2026 remains fully protected")

print("\n=== V96 RECEIPT ===")
print(json.dumps(receipt,indent=2))
print("\n=== V96 OOS 2023-2025 PARENT/INTERACTION ATTRIBUTION ===")
show=[
    "development_rank","feature_A","state_A","feature_B","state_B","target","direction",
    "joint_n","joint_mean_bp","unconditional_mean_bp",
    "A1B0_mean_bp","A0B1_mean_bp","A0B0_mean_bp",
    "joint_vs_complement_bp","joint_vs_complement_p_one",
    "A_added_given_B_bp","A_added_given_B_p_one",
    "B_added_given_A_bp","B_added_given_A_p_one",
    "interaction_AxB_bp","interaction_AxB_p_one",
]
print(O[show].to_string(index=False))
print("\nRUN:",OUT)
