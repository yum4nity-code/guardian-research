from pathlib import Path
import pandas as pd
import numpy as np
import json
import math
import re
from scipy.stats import t as student_t

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v88a"
BASE.mkdir(parents=True,exist_ok=True)

PANEL_RANK=48
TRIAL_INDEX=39930001
FEATURE_A="price_EURUSD_ret_30m"
FEATURE_B="price_NSXUSD_ret_60m"
TARGET="XAGUSD_fwd_15m"
DIRECTION="SHORT"
BLOCK_DAYS=5
MIN_FAST_STATE=5000

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def status(out,step,total,msg,**extra):
    payload={"step":step,"steps":total,"percent":round(100*step/total,1),"message":msg,**extra}
    write_json(out/"LIVE_STATUS.json",payload)
    tail=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF88A] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

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
        parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    return q.set_index("utc")["px"]

def build_feature(name,P):
    m=re.fullmatch(r"price_([A-Z]+)_ret_(\d+)m",name)
    if not m:
        raise RuntimeError(f"Unsupported V88A feature {name}")
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
    return {
        "n":len(x),
        "mean_bp":float(x.mean()*1e4) if len(x) else np.nan,
        "median_bp":float(np.median(x)*1e4) if len(x) else np.nan,
        "win_rate_pct":float((x>0).mean()*100) if len(x) else np.nan,
        "sum_pct":float(x.sum()*100) if len(x) else np.nan,
    }

# Resolve latest completed V88 replication.
runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v88_replication").glob("GEF88R-*"))
runs=[p for p in runs if (p/"RUN_RECEIPT.json").exists() and (p/"REPLICATION_2014_2017_ALL_17.csv").exists()]
if not runs:
    raise RuntimeError("No completed V88 replication")
V88=runs[-1]
r88=json.loads((V88/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r88.get("status")!="COMPLETE_FROZEN_2014_2017_REPLICATION":
    raise RuntimeError(f"Latest V88 status {r88.get('status')}")
if r88.get("2018_plus_accessed") or r88.get("2023_plus_accessed") or r88.get("protected_2026_accessed"):
    raise RuntimeError("V88 later-window assertion violated")

R=pd.read_csv(V88/"REPLICATION_2014_2017_ALL_17.csv")
row=R.loc[R["panel_rank"]==PANEL_RANK]
if len(row)!=1:
    raise RuntimeError(f"Expected one panel {PANEL_RANK}, found {len(row)}")
row=row.iloc[0]
assert int(row["trial_index"])==TRIAL_INDEX
assert str(row["feature_i"])==FEATURE_A
assert str(row["feature_j"])==FEATURE_B
assert str(row["target"])==TARGET
assert str(row["direction"])==DIRECTION

RID="GEF88A-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID
OUT.mkdir(parents=True,exist_ok=False)
status(OUT,1,8,"panel 48 exact hypothesis locked; 2018+ still unopened",source_v88=V88.name)

# Recover archived 2010-2013 fast state and V85 cache indices for parity.
PF=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v88"/r88["source_preflight"]
frozen=pd.read_csv(PF/"FROZEN_2014_2017_REPLICATION_PANEL.csv")
fr=frozen.loc[frozen["panel_rank"]==PANEL_RANK]
if len(fr)!=1:
    raise RuntimeError("Panel 48 missing from frozen preflight")
fr=fr.iloc[0]

V87=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v87"/json.loads((PF/"RUN_RECEIPT.json").read_text())["source_v87"]
r87=json.loads((V87/"RUN_RECEIPT.json").read_text())
V86A=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v86a"/r87["source_v86a"]
r86a=json.loads((V86A/"RUN_RECEIPT.json").read_text())
V86=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v86"/r86a["source_v86"]
spec86=json.loads((V86/"FROZEN_V86_SPEC.json").read_text())
V85=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v85"/spec86["source_v85"]
design=json.loads((V85/"TRIAL_DESIGN.json").read_text())
state_meta=json.loads((V85/"STATE_CACHE_META.json").read_text())
V84C=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v84c"/design["source_v84c"]
r84=json.loads((V84C/"RUN_RECEIPT.json").read_text())
V83B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v83b"/r84["source_v83b"]
manifest=json.loads((V83B/"REPAIRED_ARCHITECTURE_MANIFEST.json").read_text())

F_hist=pd.read_parquet(manifest["price_state_5m_path"])
F_hist.index=pd.to_datetime(F_hist.index)
train_shape=tuple(state_meta["train_shape"]); hold_shape=tuple(state_meta["hold_shape"])
ST=np.memmap(V85/"STATE_TRAIN.bool.dat",mode="r",dtype=np.bool_,shape=train_shape)
SH=np.memmap(V85/"STATE_HOLD.bool.dat",mode="r",dtype=np.bool_,shape=hold_shape)
hist_rows=len(F_hist)
if train_shape[2]+hold_shape[2]!=hist_rows:
    raise RuntimeError("Historical cache row mismatch")
status(OUT,2,8,"archived 2010-2013 state lineage loaded")

# Rebuild only EURUSD, NSXUSD, XAGUSD through 2017.
warm_grid=pd.date_range("2013-12-01 00:00","2017-12-31 23:55",freq="5min")
ext_grid=pd.date_range("2014-01-01 00:00","2017-12-31 23:55",freq="5min")
P=pd.DataFrame(index=warm_grid)
for sym in ("EURUSD","NSXUSD","XAGUSD"):
    raw=load_m1(sym,range(2013,2018))
    P[sym]=raw.resample("5min",label="right",closed="left").last().reindex(warm_grid)
status(OUT,3,8,"minimal 2014-2017 market set rebuilt",markets=3,rows=len(ext_grid))

FA_ext=build_feature(FEATURE_A,P).reindex(ext_grid)
FB_ext=build_feature(FEATURE_B,P).reindex(ext_grid)

def extend_and_check(feature,feature_index,ext):
    full=pd.concat([pd.to_numeric(F_hist[feature],errors="coerce"),pd.to_numeric(ext,errors="coerce")])
    lo,hi=causal_states(full,MIN_FAST_STATE)
    hist_lo=lo[:hist_rows]; hist_hi=hi[:hist_rows]
    exp_lo=np.concatenate([ST[int(feature_index),0,:],SH[int(feature_index),0,:]])
    exp_hi=np.concatenate([ST[int(feature_index),1,:],SH[int(feature_index),1,:]])
    ml=int(np.count_nonzero(hist_lo!=exp_lo)); mh=int(np.count_nonzero(hist_hi!=exp_hi))
    if ml or mh:
        raise RuntimeError(f"Parity failed {feature}: LO={ml} HI={mh}")
    return lo[hist_rows:],hi[hist_rows:]

a_lo,a_hi=extend_and_check(FEATURE_A,int(fr["feature_i_index"]),FA_ext)
b_lo,b_hi=extend_and_check(FEATURE_B,int(fr["feature_j_index"]),FB_ext)
A=a_hi
B=b_hi
J=A&B
status(OUT,4,8,"exact state parity passed; joint mask reconstructed",joint_rows=int(J.sum()))

# Build same non-overlapping SHORT XAG 15m target.
k=15//5
raw_y=P["XAGUSD"].shift(-k)/P["XAGUSD"]-1
y=(-raw_y.reindex(ext_grid)).to_numpy(dtype=np.float64)
minute=(ext_grid.view("int64")//60_000_000_000).astype(np.int64)
y[(minute%15)!=0]=np.nan
valid=np.isfinite(y)
blocks=((ext_grid.normalize()-pd.Timestamp("2014-01-01")).days.to_numpy()//BLOCK_DAYS).astype(np.int16)

# Core descriptive attribution.
groups={
    "unconditional":valid,
    "joint_AB":valid&J,
    "A_only_state":valid&A,
    "B_only_state":valid&B,
    "not_joint":valid&(~J),
    "A1_B0":valid&A&(~B),
    "A0_B1":valid&(~A)&B,
    "A0_B0":valid&(~A)&(~B),
}
desc={k:summarize(np.where(m,y,np.nan)) for k,m in groups.items()}

# Regression 1: joint condition vs complement.
D=J.astype(np.float64)
X1=np.column_stack([np.ones(len(y)),D])
joint_excess=cluster_ols(y,X1,blocks,1)

# Regression 2: explicit interaction A + B + A*B.
X2=np.column_stack([np.ones(len(y)),A.astype(float),B.astype(float),(A&B).astype(float)])
interaction=cluster_ols(y,X2,blocks,3)

# Hour-of-week demeaning: removes stable calendar drift/seasonality.
tmp=pd.DataFrame({"y":y,"joint":J},index=ext_grid)
tmp=tmp[np.isfinite(tmp["y"].to_numpy())].copy()
tmp["how"]=tmp.index.dayofweek*24+tmp.index.hour
bucket_mean=tmp.groupby("how")["y"].transform("mean")
tmp["resid_how"]=tmp["y"]-bucket_mean
how_joint=cluster_ols(
    tmp["resid_how"].to_numpy(),
    np.column_stack([np.ones(len(tmp)),tmp["joint"].astype(float).to_numpy()]),
    ((tmp.index.normalize()-pd.Timestamp("2014-01-01")).days.to_numpy()//BLOCK_DAYS).astype(np.int16),
    1,
)

# Remove top 5% most profitable joint observations.
jr=y[valid&J]
cut=max(1,int(math.floor(len(jr)*0.05))) if len(jr) else 0
trim=np.sort(jr)[:-cut] if cut and cut<len(jr) else jr
trim_stats=summarize(trim)

# Year-by-year joint excess over unconditional mean in that same year.
yearly=[]
for year in (2014,2015,2016,2017):
    yy=np.asarray(ext_grid.year==year)
    jv=y[yy&valid&J]
    av=y[yy&valid]
    yearly.append({
        "year":year,
        "joint_n":len(jv),
        "joint_mean_bp":float(np.mean(jv)*1e4) if len(jv) else np.nan,
        "unconditional_mean_bp":float(np.mean(av)*1e4) if len(av) else np.nan,
        "joint_minus_unconditional_bp":float((np.mean(jv)-np.mean(av))*1e4) if len(jv) and len(av) else np.nan,
    })
Y=pd.DataFrame(yearly)
Y.to_csv(OUT/"YEARLY_INCREMENTAL_ATTRIBUTION.csv",index=False)
status(OUT,5,8,"incremental and parent-state attribution computed",joint_n=desc["joint_AB"]["n"])

result={
    "run_id":RID,
    "status":"COMPLETE_INCREMENTAL_ATTRIBUTION_2014_2017",
    "source_v88":V88.name,
    "panel_rank":PANEL_RANK,
    "trial_index":TRIAL_INDEX,
    "hypothesis":f"{FEATURE_A} HI AND {FEATURE_B} HI -> {DIRECTION} {TARGET}",
    "descriptive_groups":desc,
    "joint_vs_complement_cluster_5d":{
        **joint_excess,
        "coef_bp":joint_excess["coef"]*1e4 if np.isfinite(joint_excess["coef"]) else np.nan,
    },
    "interaction_AxB_cluster_5d":{
        **interaction,
        "coef_bp":interaction["coef"]*1e4 if np.isfinite(interaction["coef"]) else np.nan,
    },
    "hour_of_week_demeaned_joint_effect_cluster_5d":{
        **how_joint,
        "coef_bp":how_joint["coef"]*1e4 if np.isfinite(how_joint["coef"]) else np.nan,
    },
    "joint_trim_top5pct_profitable":trim_stats,
    "joint_net_mean_after_cost_bp":{
        "1bp":desc["joint_AB"]["mean_bp"]-1.0,
        "2bp":desc["joint_AB"]["mean_bp"]-2.0,
        "5bp":desc["joint_AB"]["mean_bp"]-5.0,
    },
    "positive_years_incremental_vs_unconditional":int((Y["joint_minus_unconditional_bp"]>0).sum()),
    "2018_plus_accessed":False,
    "2023_plus_accessed":False,
    "protected_2026_accessed":False,
    "next":"FREEZE_PRIMARY_HYPOTHESIS_THEN_OPEN_2018_2022_IF_INCREMENTAL_SIGNAL_SURVIVES",
}
write_json(OUT/"RUN_RECEIPT.json",result)
status(
    OUT,6,8,"receipt written",
    joint_mean_bp=round(desc["joint_AB"]["mean_bp"],4),
    excess_bp=round(result["joint_vs_complement_cluster_5d"]["coef_bp"],4),
    excess_p=result["joint_vs_complement_cluster_5d"]["p_one"],
)
status(OUT,7,8,"2018-2022 remains unopened")
status(OUT,8,8,"DONE")

print("\n=== V88A RECEIPT ===")
print(json.dumps(result,indent=2))
print("\n=== YEARLY INCREMENTAL ATTRIBUTION ===")
print(Y.to_string(index=False))
print("\nRUN:",OUT)
