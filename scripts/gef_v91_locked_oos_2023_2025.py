from pathlib import Path
import pandas as pd
import numpy as np
import json
import math
import re
import hashlib
from scipy.stats import t as student_t

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v91"
BASE.mkdir(parents=True,exist_ok=True)

ENGINE_VERSION="V91.0"
MIN_FAST_STATE=5000
BLOCK_DAYS=5
OOS_START=pd.Timestamp("2023-01-01 00:00")
OOS_END=pd.Timestamp("2025-12-31 23:55")
DEV_START=pd.Timestamp("2014-01-01 00:00")
DEV_END=pd.Timestamp("2022-12-31 23:55")
TARGET="XAGUSD_fwd_15m"
BASE_A="price_EURUSD_ret_30m"
BASE_B="price_NSXUSD_ret_60m"
DIRECTION="SHORT"

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def status(out,step,total,msg,**extra):
    payload={"engine_version":ENGINE_VERSION,"step":step,"steps":total,
             "percent":round(100*step/total,1),"timestamp_utc":pd.Timestamp.now("UTC").isoformat(),
             "message":msg,**extra}
    write_json(out/"LIVE_STATUS.json",payload)
    tail=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF91] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

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
        if y>2025:
            raise RuntimeError("V91 refuses to load 2026+")
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
        q=q[q["utc"].dt.year<=2025]
        parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    return q.set_index("utc")["px"]

def build_feature(name,P):
    m=re.fullmatch(r"price_([A-Z]+)_ret_(\d+)m",name)
    if m:
        sym,mins=m.group(1),int(m.group(2)); k=mins//5
        return (P[sym]/P[sym].shift(k)-1).astype("float64")
    m=re.fullmatch(r"price_([A-Z]+)_trend_(\d+)m",name)
    if m:
        sym,mins=m.group(1),int(m.group(2)); k=mins//5
        return (P[sym]/P[sym].shift(k)-1).astype("float64")
    m=re.fullmatch(r"price_([A-Z]+)_rv_(\d+)m",name)
    if m:
        sym,mins=m.group(1),int(m.group(2)); k=mins//5
        r5=P[sym].pct_change(1,fill_method=None)
        return r5.rolling(k,min_periods=max(3,k//2)).std().astype("float64")
    raise RuntimeError(f"Unsupported feature {name}")

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

def summarize(x):
    x=np.asarray(x,dtype=np.float64)
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
    return {"n":int(len(x)),"mean_bp":mean_bp,"median_bp":float(np.median(x)*1e4),
            "win_rate_pct":float((x>0).mean()*100),"sum_pct":float(x.sum()*100),
            "max_drawdown_pct":mdd,"net_1bp_mean_bp":mean_bp-1.0,
            "net_2bp_mean_bp":mean_bp-2.0,"net_5bp_mean_bp":mean_bp-5.0}

def eval_window(times,y,base,gate):
    valid=np.isfinite(y)
    joint=base&gate&valid
    base_valid=base&valid
    blocks=((times.normalize()-times[0].normalize()).days.to_numpy()//BLOCK_DAYS).astype(np.int16)

    stats=summarize(np.where(joint,y,np.nan))
    yb=y[base_valid]
    gb=gate[base_valid].astype(float)
    bb=blocks[base_valid]
    inc=cluster_ols(yb,np.column_stack([np.ones(len(yb)),gb]),bb,1)

    yearly=[]
    for year in sorted(set(times.year)):
        yy=np.asarray(times.year==year)
        gv=y[yy&joint]
        bv=y[yy&base_valid]
        yearly.append({
            "year":int(year),
            "n":int(len(gv)),
            "mean_bp":float(np.mean(gv)*1e4) if len(gv) else np.nan,
            "net_1bp_mean_bp":float(np.mean(gv)*1e4-1.0) if len(gv) else np.nan,
            "base_mean_bp":float(np.mean(bv)*1e4) if len(bv) else np.nan,
            "incremental_vs_base_bp":float((np.mean(gv)-np.mean(bv))*1e4) if len(gv) and len(bv) else np.nan,
        })
    Y=pd.DataFrame(yearly)
    return {
        "joint_stats":stats,
        "incremental_within_base":{
            **inc,
            "coef_bp":inc["coef"]*1e4 if np.isfinite(inc["coef"]) else np.nan,
        },
        "yearly":Y,
        "positive_years":int((Y["mean_bp"]>0).sum()),
        "positive_net1bp_years":int((Y["net_1bp_mean_bp"]>0).sum()),
        "positive_incremental_years":int((Y["incremental_vs_base_bp"]>0).sum()),
    }

# ---------- read exact V90 selected freeze ----------
runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v90").glob("GEF90-*"))
runs=[p for p in runs if (p/"RUN_RECEIPT.json").exists() and (p/"SELECTED_GATE_FREEZE_BEFORE_2023.json").exists()]
if not runs:
    raise RuntimeError("No V90 run with frozen selected gate")
V90=runs[-1]
r90=json.loads((V90/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
sel=json.loads((V90/"SELECTED_GATE_FREEZE_BEFORE_2023.json").read_text(encoding="utf-8"))
if r90.get("status")!="COMPLETE_V90_REGIME_GATE_DEVELOPMENT":
    raise RuntimeError(f"Latest V90 status {r90.get('status')}")
if r90.get("2023_plus_accessed") or r90.get("protected_2026_accessed"):
    raise RuntimeError("V90 later-window access assertion violated")
if sel.get("status")!="V90_REGIME_GATE_SELECTED_AND_FROZEN_FOR_LOCKED_OOS":
    raise RuntimeError("V90 selected gate freeze status invalid")
if int(sel.get("development_rank",-1))!=1:
    raise RuntimeError("V91 only accepts pre-frozen V90 rank-1 selected gate")

GATE_FEATURE=str(sel["selected_gate_feature"])
GATE_STATE=str(sel["selected_gate_state"])
if GATE_STATE not in {"LO","HI"}:
    raise RuntimeError("Invalid gate state")

RID="GEF91-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID
OUT.mkdir(parents=True,exist_ok=False)
status(OUT,1,11,"V90 selected gate loaded; locked OOS values still unopened",
       source_v90=V90.name,gate=f"{GATE_FEATURE} {GATE_STATE}")

freeze={
    "run_id":RID,
    "status":"V91_LOCKED_OOS_SPEC_FROZEN_BEFORE_2023",
    "source_v90":V90.name,
    "selected_gate_freeze_sha256":sha256(V90/"SELECTED_GATE_FREEZE_BEFORE_2023.json"),
    "base_condition":sel["base_condition"],
    "gate_feature":GATE_FEATURE,
    "gate_state":GATE_STATE,
    "target":TARGET,
    "direction":DIRECTION,
    "oos_window":"2023-2025",
    "no_parameter_changes":True,
    "primary_readout":[
        "gross mean bp",
        "net mean after hypothetical 1bp",
        "year-by-year sign",
        "incremental effect inside base opportunities",
        "5-day cluster-robust one-sided p-value"
    ],
    "2023_2025_values_accessed":False,
    "protected_2026_accessed":False,
}
write_json(OUT/"LOCKED_OOS_FREEZE_BEFORE_2023.json",freeze)
freeze_sha=sha256(OUT/"LOCKED_OOS_FREEZE_BEFORE_2023.json")
status(OUT,2,11,"locked OOS specification physically frozen",freeze_sha256=freeze_sha[:16])

# ---------- file-existence preflight only ----------
needed_features=[BASE_A,BASE_B,GATE_FEATURE]
symbols=set()
for feat in needed_features:
    m=re.match(r"price_([A-Z]+)_",feat)
    if m:
        symbols.add(m.group(1))
symbols.add("XAGUSD")
missing=[]
for sym in sorted(symbols):
    for year in range(2023,2026):
        p=ROOT/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
        if not p.exists():
            missing.append(str(p))
if missing:
    receipt={
        "run_id":RID,
        "status":"STOP_MISSING_LOCKED_OOS_FILES",
        "source_v90":V90.name,
        "missing_files":missing,
        "2023_2025_values_accessed":False,
        "protected_2026_accessed":False,
        "next":"MATERIALIZE_MISSING_2023_2025_FILES_WITHOUT_CHANGING_FROZEN_RULE"
    }
    write_json(OUT/"RUN_RECEIPT.json",receipt)
    status(OUT,3,11,"STOP: locked OOS files missing; no 2023 values read",missing=len(missing))
    print("\n=== V91 RECEIPT ===")
    print(json.dumps(receipt,indent=2))
    print("\nRUN:",OUT)
    raise SystemExit(0)
status(OUT,3,11,"2023-2025 source presence confirmed; values still unopened",files_checked=len(symbols)*3)

# ---------- recover V90/V85 lineage ----------
r89=json.loads((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v89"/r90["source_v89"]/"RUN_RECEIPT.json").read_text())
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
F_hist.index=pd.to_datetime(F_hist.index)
train_shape=tuple(state_meta["train_shape"]); hold_shape=tuple(state_meta["hold_shape"])
ST=np.memmap(V85/"STATE_TRAIN.bool.dat",mode="r",dtype=np.bool_,shape=train_shape)
SH=np.memmap(V85/"STATE_HOLD.bool.dat",mode="r",dtype=np.bool_,shape=hold_shape)
hist_rows=len(F_hist)
feature_to_index={str(r.feature):i for i,r in catalog.iterrows()}
for feat in needed_features:
    if feat not in feature_to_index:
        raise RuntimeError(f"Feature missing from frozen V85 catalog: {feat}")
status(OUT,4,11,"original architecture lineage loaded")

# ---------- NOW read through 2025, never 2026 ----------
warm_grid=pd.date_range("2013-12-01 00:00",OOS_END,freq="5min")
post2013_grid=pd.date_range("2014-01-01 00:00",OOS_END,freq="5min")
P=pd.DataFrame(index=warm_grid)
for i,sym in enumerate(sorted(symbols),1):
    raw=load_m1(sym,range(2013,2026))
    P[sym]=raw.resample("5min",label="right",closed="left").last().reindex(warm_grid)
    print(f"[GEF91] market {i}/{len(symbols)} {sym}",flush=True)
status(OUT,5,11,"2014-2025 causal continuation materialized; 2026 untouched",
       rows=len(post2013_grid),markets=len(symbols))

states={}
for feat in needed_features:
    ext=build_feature(feat,P).reindex(post2013_grid)
    fi=feature_to_index[feat]
    full=pd.concat([pd.to_numeric(F_hist[feat],errors="coerce"),pd.to_numeric(ext,errors="coerce")])
    lo,hi=causal_states(full,MIN_FAST_STATE)
    exp_lo=np.concatenate([ST[fi,0,:],SH[fi,0,:]])
    exp_hi=np.concatenate([ST[fi,1,:],SH[fi,1,:]])
    ml=int(np.count_nonzero(lo[:hist_rows]!=exp_lo))
    mh=int(np.count_nonzero(hi[:hist_rows]!=exp_hi))
    if ml or mh:
        raise RuntimeError(f"Historical state parity failed {feat}: LO={ml}, HI={mh}")
    states[(feat,"LO")]=lo[hist_rows:]
    states[(feat,"HI")]=hi[hist_rows:]
status(OUT,6,11,"2010-2013 state parity exact for base + gate",features=len(needed_features))

base=states[(BASE_A,"HI")]&states[(BASE_B,"HI")]
gate=states[(GATE_FEATURE,GATE_STATE)]

raw_y=P["XAGUSD"].shift(-(15//5))/P["XAGUSD"]-1
y=np.array(-raw_y.reindex(post2013_grid),dtype=np.float64,copy=True)
if not y.flags.writeable:
    raise RuntimeError("V91 target array unexpectedly read-only")
minute=(post2013_grid.view("int64")//60_000_000_000).astype(np.int64)
y[(minute%15)!=0]=np.nan
# Never borrow 2026 to close a 2025 trade.
y[(post2013_grid+pd.Timedelta(minutes=15))>OOS_END]=np.nan

# ---------- reproduce selected V90 development metrics before reading OOS report ----------
dev_sel=np.asarray((post2013_grid>=DEV_START)&(post2013_grid<=DEV_END))
dev=eval_window(post2013_grid[dev_sel],y[dev_sel],base[dev_sel],gate[dev_sel])

dev_metrics=sel["development_metrics"]
expected_e2=float(dev_metrics["E2_2014_2017_mean_bp"])
expected_e3=float(dev_metrics["E3_2018_2022_mean_bp"])
Ydev=dev["yearly"]
got_e2=float(Ydev[Ydev["year"].between(2014,2017)].apply(
    lambda _: 0,axis=1
).sum()) if False else None
# Exact aggregate parity is checked directly by recomputing the two eras below.
def subset_eval(start,end):
    s=np.asarray((post2013_grid>=start)&(post2013_grid<=end))
    return eval_window(post2013_grid[s],y[s],base[s],gate[s])
dev_e2=subset_eval(pd.Timestamp("2014-01-01"),pd.Timestamp("2017-12-31 23:55"))
dev_e3=subset_eval(pd.Timestamp("2018-01-01"),pd.Timestamp("2022-12-31 23:55"))
got_e2=float(dev_e2["joint_stats"]["mean_bp"])
got_e3=float(dev_e3["joint_stats"]["mean_bp"])
if not np.isclose(got_e2,expected_e2,rtol=0,atol=1e-9):
    raise RuntimeError(f"V90 E2 parity failed {got_e2} != {expected_e2}")
if not np.isclose(got_e3,expected_e3,rtol=0,atol=1e-9):
    raise RuntimeError(f"V90 E3 parity failed {got_e3} != {expected_e3}")
status(OUT,7,11,"V90 selected-gate development parity exact before OOS scoring",
       E2_mean_bp=round(got_e2,6),E3_mean_bp=round(got_e3,6))

# ---------- locked OOS 2023-2025 ----------
oos_sel=np.asarray((post2013_grid>=OOS_START)&(post2013_grid<=OOS_END))
oos=eval_window(post2013_grid[oos_sel],y[oos_sel],base[oos_sel],gate[oos_sel])
Y=oos["yearly"]
Y.to_csv(OUT/"LOCKED_OOS_2023_2025_YEARLY.csv",index=False)

j=oos["joint_stats"]; inc=oos["incremental_within_base"]
readout={
    "run_id":RID,
    "status":"COMPLETE_LOCKED_OOS_2023_2025",
    "engine_version":ENGINE_VERSION,
    "source_v90":V90.name,
    "lock_freeze_sha256":freeze_sha,
    "gate_feature":GATE_FEATURE,
    "gate_state":GATE_STATE,
    "oos_window":"2023-2025",
    "joint_stats":j,
    "incremental_within_base_cluster_5d":inc,
    "positive_years":oos["positive_years"],
    "positive_net1bp_years":oos["positive_net1bp_years"],
    "positive_incremental_years":oos["positive_incremental_years"],
    "2023_2025_values_accessed":True,
    "protected_2026_accessed":False,
    "next":"STOP_FOR_HUMAN_REVIEW_NO_FURTHER_PARAMETER_TUNING_ON_2023_2025"
}
write_json(OUT/"RUN_RECEIPT.json",readout)
status(OUT,8,11,"locked OOS scored",
       n=j["n"],mean_bp=round(j["mean_bp"],4),net1bp=round(j["net_1bp_mean_bp"],4),
       incremental_bp=round(inc["coef_bp"],4),p_one=inc["p_one"])
status(OUT,9,11,"year-by-year OOS written",positive_years=oos["positive_years"],
       positive_net1bp_years=oos["positive_net1bp_years"],positive_incremental_years=oos["positive_incremental_years"])
status(OUT,10,11,"2026 remains protected and unopened")
status(OUT,11,11,"DONE")

print("\n=== V91 LOCKED OOS RECEIPT ===")
print(json.dumps(readout,indent=2))
print("\n=== V91 2023-2025 YEARLY ===")
print(Y.to_string(index=False))
print("\nRUN:",OUT)
