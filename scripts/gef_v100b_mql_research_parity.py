from pathlib import Path
import pandas as pd
import numpy as np
import json
import math
import re
import hashlib
import time

ROOT=Path(r"D:\MT5_Backtests")
REPO=ROOT/"guardian-research"
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v100b_mql_parity"
BASE.mkdir(parents=True,exist_ok=True)

ENGINE_VERSION="V100B.0"
OOS_START=pd.Timestamp("2023-01-01 00:00")
OOS_END=pd.Timestamp("2025-12-31 23:55")
MIN_FAST_STATE=5000

MQ5=REPO/"mt5"/"GuardianEdgeForward"/"GuardianEdgeForward.mq5"

FEATURES={
    "price_USDJPY_zret_60m":("USDJPY","zret",60),
    "price_USDCHF_rv_60m":("USDCHF","rv",60),
    "price_XAUUSD_rv_60m":("XAUUSD","rv",60),
    "price_GBPUSD_ret_30m":("GBPUSD","ret",30),
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
    print(f"[GEF100B] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

def feature_market(feature):
    m=re.match(r"price_([A-Z]+)_",str(feature))
    return m.group(1) if m else None

def build_research_feature(name,P):
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
    raise RuntimeError(f"Unsupported feature {name}")

def mql20_feature_from_price(name,price):
    """Independent numpy emulation of GuardianEdgeForward.mq5 V100.20."""
    p=np.asarray(price,dtype=np.float64)
    n=len(p)
    out=np.full(n,np.nan,dtype=np.float64)
    sym,kind,mins=FEATURES[name]

    if kind=="ret":
        k=mins//5
        good=np.isfinite(p[k:])&np.isfinite(p[:-k])&(p[k:]>0)&(p[:-k]>0)
        vals=np.full(n-k,np.nan,dtype=np.float64)
        vals[good]=p[k:][good]/p[:-k][good]-1.0
        out[k:]=vals
        return out

    r5=np.full(n,np.nan,dtype=np.float64)
    good=np.isfinite(p[1:])&np.isfinite(p[:-1])&(p[1:]>0)&(p[:-1]>0)
    r5[1:][good]=p[1:][good]/p[:-1][good]-1.0

    # Exact V100.20 rolling semantics: last 12 r5 observations, ignore missing,
    # min_periods=6, sample standard deviation ddof=1.
    finite=np.isfinite(r5)
    z=np.where(finite,r5,0.0)
    z2=np.where(finite,r5*r5,0.0)
    cnt=np.concatenate(([0],np.cumsum(finite.astype(np.int64))))
    sm=np.concatenate(([0.0],np.cumsum(z)))
    ss=np.concatenate(([0.0],np.cumsum(z2)))

    for i in range(n):
        lo=max(0,i-11)
        hi=i+1
        c=int(cnt[hi]-cnt[lo])
        if c<6:
            continue
        s=float(sm[hi]-sm[lo])
        s2=float(ss[hi]-ss[lo])
        num=s2-(s*s)/c
        if num<=0 or not np.isfinite(num):
            continue
        sd=math.sqrt(num/(c-1))
        if kind=="rv":
            out[i]=sd
        elif kind=="zret" and finite[i]:
            mean=s/c
            out[i]=(r5[i]-mean)/sd
    return out

def causal_states_pandas(s):
    s=pd.to_numeric(s,errors="coerce")
    mu=s.expanding(min_periods=MIN_FAST_STATE).mean().shift(1)
    sd=s.expanding(min_periods=MIN_FAST_STATE).std().shift(1).replace(0,np.nan)
    z=(s-mu)/sd
    finite=np.isfinite(z.to_numpy(dtype=np.float64))
    zv=z.to_numpy(dtype=np.float64)
    return finite&(zv<=-1.0),finite&(zv>=1.0)

def welford_seed(values):
    n=0
    mean=0.0
    m2=0.0
    for x in np.asarray(values,dtype=np.float64):
        if not np.isfinite(x):
            continue
        n1=n+1
        delta=x-mean
        mean+=delta/n1
        delta2=x-mean
        m2+=delta*delta2
        n=n1
    return n,mean,m2

def welford_states(seed,values):
    n,mean,m2=seed
    lo=np.zeros(len(values),dtype=bool)
    hi=np.zeros(len(values),dtype=bool)
    for i,x in enumerate(np.asarray(values,dtype=np.float64)):
        if not np.isfinite(x):
            continue
        if n>=MIN_FAST_STATE and n>=2 and np.isfinite(m2) and m2>0:
            sd=math.sqrt(m2/(n-1))
            if np.isfinite(sd) and sd>0:
                lo[i]=(x<=mean-sd)
                hi[i]=(x>=mean+sd)
        n1=n+1
        delta=x-mean
        mean+=delta/n1
        delta2=x-mean
        m2+=delta*delta2
        n=n1
    return lo,hi,(n,mean,m2)

def load_hist(sym,years):
    parts=[]
    for year in years:
        if year>2022:
            raise RuntimeError("V100B pre-foundation loader refuses 2023+")
        p=ROOT/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
        if not p.exists():
            raise RuntimeError(f"Missing {p}")
        d=pd.read_parquet(p)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        cc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None and isinstance(d.index,pd.DatetimeIndex):
            d=d.reset_index(); dc=d.columns[0]
        if dc is None or cc is None:
            raise RuntimeError(f"Cannot identify datetime/close {p}")
        utc=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(minutes=300)
        q=pd.DataFrame({"utc":utc,"close":pd.to_numeric(d[cc],errors="coerce")}).dropna()
        parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    return q.set_index("utc")["close"]

# ---------- immutable lineage ----------
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
panel=pd.read_csv(V97E/"CORRECTED_2026_FORWARD_PANEL.csv")
if sorted(panel["development_rank"].astype(int).tolist())!=[7,9]:
    raise RuntimeError("Unexpected V97E frozen ranks")
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
bridge=pd.read_csv(V98/"CORRECTED_RANKS_7_9_FTMO_BRIDGE.csv")
if r98.get("2026_values_requested_or_stored"):
    raise RuntimeError("V98 reports 2026 access")
common_shift=int(r98["common_ftmo_index_shift_min"])
if common_shift%30!=0:
    raise RuntimeError(f"FTMO clock shift {common_shift} is not invariant for 15/30m sampling")

# latest successful V100 package receipt must reference current source hash
v100_runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v100_forward_package").glob("GEF100-*"))
v100_runs=[
    p for p in v100_runs
    if (p/"RUN_RECEIPT.json").exists()
    and json.loads((p/"RUN_RECEIPT.json").read_text(encoding="utf-8")).get("status")=="V100_FORWARD_SHADOW_PACKAGE_FROZEN"
]
if not v100_runs:
    raise RuntimeError("No successful V100 package audit for current source; run V100 wrapper first")
V100=v100_runs[-1]
r100=json.loads((V100/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r100.get("compile_status")!="PASS":
    raise RuntimeError("Latest V100 source did not compile PASS")
if r100.get("mq5_sha256")!=sha256(MQ5):
    raise RuntimeError("Latest V100 receipt does not match current MQ5; rerun V100 compile/audit")
if r100.get("2026_market_values_accessed"):
    raise RuntimeError("V100 reports 2026 access")

src=MQ5.read_text(encoding="utf-8")
for literal in (
    '#property version   "100.20"',
    "MeanStdFinite12",
    "nfinite<6",
    "double mean=prior.mean;",
):
    if literal not in src:
        raise RuntimeError(f"Current MQL source missing V100.20 contract {literal}")

# architecture
v94_runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v94").glob("GEF94-*"))
v94_runs=[p for p in v94_runs if (p/"RUN_RECEIPT.json").exists()]
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

RID="GEF100B-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID
OUT.mkdir(parents=True,exist_ok=False)
status(
    OUT,1,10,
    "V97E/V98/current compiled V100.20 lineage loaded; 2026 untouched",
    source_v97e=V97E.name,source_v98=V98.name,source_v100=V100.name,
)

# ---------- build exact V98 FTMO aligned price panel ----------
oos_grid=pd.date_range(OOS_START,OOS_END,freq="5min")
bridge_grid=pd.date_range("2022-12-01 00:00",OOS_END,freq="5min")
pre_grid=pd.date_range("2014-01-01 00:00","2022-12-31 23:55",freq="5min")
pre_warm=pd.date_range("2013-12-01 00:00","2022-12-31 23:55",freq="5min")

needed_markets={feature_market(f) for f in FEATURES}
Ppre=pd.DataFrame(index=pre_warm)
Pftmo=pd.DataFrame(index=bridge_grid)
for i,sym in enumerate(sorted(needed_markets),1):
    pre=load_hist(sym,range(2013,2023))
    Ppre[sym]=pre.resample("5min",label="right",closed="left").last().reindex(pre_warm)

    ftmo_symbol=r98["ftmo_symbols"][sym]
    fp=V98/f"FTMO_{str(ftmo_symbol).replace('.','_')}_M1_2023_2025.parquet"
    if not fp.exists():
        raise RuntimeError(f"Missing V98 FTMO artifact {fp}")
    d=pd.read_parquet(fp)
    d["utc"]=pd.to_datetime(d["utc"],errors="coerce")
    if (d["utc"]>=pd.Timestamp("2026-01-01")).any():
        raise RuntimeError(f"2026 leaked in {fp}")
    d["close"]=pd.to_numeric(d["close"],errors="coerce")
    f5=d.set_index("utc")["close"].sort_index().resample("5min",label="right",closed="left").last().reindex(oos_grid)
    f5=f5.shift(common_shift//5)

    warm=load_hist(sym,[2022]).resample("5min",label="right",closed="left").last()
    Pftmo[sym]=pd.concat([warm,f5]).sort_index().reindex(bridge_grid)
    print(f"[GEF100B] price {i}/{len(needed_markets)} {sym}",flush=True)

status(OUT,2,10,"pre-2023 foundation and 2023-2025 FTMO-aligned price panels reconstructed")

# ---------- independent feature parity ----------
research_oos={}
mql_oos={}
feature_rows=[]
for i,name in enumerate(FEATURES,1):
    rf=build_research_feature(name,Pftmo).reindex(oos_grid)
    mf=mql20_feature_from_price(name,Pftmo[FEATURES[name][0]].to_numpy(dtype=float))
    mf=pd.Series(mf,index=bridge_grid).reindex(oos_grid)

    a=rf.to_numpy(dtype=float)
    b=mf.to_numpy(dtype=float)
    finite_a=np.isfinite(a)
    finite_b=np.isfinite(b)
    mask_equal=bool(np.array_equal(finite_a,finite_b))
    both=finite_a&finite_b
    max_abs=float(np.max(np.abs(a[both]-b[both]))) if both.any() else np.nan
    tol=1e-11
    value_ok=bool(mask_equal and (not both.any() or max_abs<=tol))
    feature_rows.append({
        "feature":name,
        "research_finite":int(finite_a.sum()),
        "mql20_finite":int(finite_b.sum()),
        "finite_mask_exact":mask_equal,
        "max_abs_value_diff":max_abs,
        "tolerance":tol,
        "feature_parity_ok":value_ok,
    })
    if not value_ok:
        raise RuntimeError(
            f"V100.20 feature parity failed {name}: mask_equal={mask_equal} max_abs={max_abs}"
        )
    research_oos[name]=rf
    mql_oos[name]=mf
    print(f"[GEF100B] feature parity {i}/{len(FEATURES)} {name} max_abs={max_abs:.3e}",flush=True)

FR=pd.DataFrame(feature_rows)
FR.to_csv(OUT/"FEATURE_VALUE_PARITY.csv",index=False)
status(OUT,3,10,"V100.20 feature-value parity exact within frozen numerical tolerance",features=len(FR))

# ---------- state parity: pandas expanding vs V100.20 Welford ----------
state_research={}
state_mql={}
state_rows=[]
seed_rows=[]
t0=time.time()

for i,name in enumerate(FEATURES,1):
    pre=build_research_feature(name,Ppre).reindex(pre_grid)
    foundation=pd.concat([
        pd.to_numeric(Fhist[name],errors="coerce"),
        pd.to_numeric(pre,errors="coerce"),
    ])

    full=pd.concat([foundation,research_oos[name]])
    plo,phi=causal_states_pandas(full)
    off=len(foundation)
    plo=plo[off:]; phi=phi[off:]

    seed=welford_seed(foundation.to_numpy(dtype=float))
    if seed[0]<MIN_FAST_STATE:
        raise RuntimeError(f"Seed too short {name}: {seed[0]}")
    mlo,mhi,final_state=welford_states(seed,mql_oos[name].to_numpy(dtype=float))

    lo_mismatch=int(np.count_nonzero(plo!=mlo))
    hi_mismatch=int(np.count_nonzero(phi!=mhi))
    ok=(lo_mismatch==0 and hi_mismatch==0)
    state_rows.append({
        "feature":name,
        "seed_n":int(seed[0]),
        "seed_mean":float(seed[1]),
        "seed_m2":float(seed[2]),
        "research_lo_rows":int(plo.sum()),
        "mql20_lo_rows":int(mlo.sum()),
        "lo_mismatch_rows":lo_mismatch,
        "research_hi_rows":int(phi.sum()),
        "mql20_hi_rows":int(mhi.sum()),
        "hi_mismatch_rows":hi_mismatch,
        "state_parity_ok":bool(ok),
    })
    seed_rows.append({
        "feature":name,
        "n":int(seed[0]),
        "mean":float(seed[1]),
        "m2":float(seed[2]),
        "note":"pre-2023 parity seed only; NOT a deployable post-2026 seed",
    })
    if not ok:
        raise RuntimeError(f"V100.20 state parity failed {name}: LO={lo_mismatch} HI={hi_mismatch}")

    state_research[(name,"LO")]=plo
    state_research[(name,"HI")]=phi
    state_mql[(name,"LO")]=mlo
    state_mql[(name,"HI")]=mhi

    elapsed=time.time()-t0
    print(f"[GEF100B] state parity {i}/{len(FEATURES)} {name} | elapsed={elapsed:.1f}s",flush=True)

SR=pd.DataFrame(state_rows)
SR.to_csv(OUT/"CAUSAL_STATE_PARITY.csv",index=False)
pd.DataFrame(seed_rows).to_csv(OUT/"PRE2023_PARITY_SEED_NOT_FOR_DEPLOYMENT.csv",index=False)
status(OUT,4,10,"pandas expanding-state vs V100.20 Welford state parity exact",features=len(SR))

# ---------- frozen rank signal parity ----------
signal_rows=[]
for row in panel.to_dict("records"):
    rank=int(row["development_rank"])
    mins=int(str(row["target"]).split("_fwd_",1)[1].rstrip("m"))
    sample=((oos_grid.view("int64")//60_000_000_000)%mins)==0

    research_mask=(
        state_research[(row["feature_i"],row["state_i"])]
        & state_research[(row["feature_j"],row["state_j"])]
        & sample
    )
    mql_mask=(
        state_mql[(row["feature_i"],row["state_i"])]
        & state_mql[(row["feature_j"],row["state_j"])]
        & sample
    )

    expected=int(bridge.loc[
        bridge["development_rank"].astype(int)==rank,
        "ftmo_signal_n_full"
    ].iloc[0])
    research_n=int(research_mask.sum())
    mql_n=int(mql_mask.sum())
    mismatch=int(np.count_nonzero(research_mask!=mql_mask))
    if research_n!=expected:
        raise RuntimeError(f"V98 signal parity failed rank {rank}: rebuilt={research_n} expected={expected}")
    if mql_n!=expected or mismatch:
        raise RuntimeError(
            f"V100.20 signal parity failed rank {rank}: mql={mql_n} expected={expected} mismatch={mismatch}"
        )

    times=oos_grid[mql_mask]
    # Common shift is an exact multiple of both horizons, so aligned-vs-server
    # clock translation cannot change 15m/30m sampling membership.
    raw_server_times=times-pd.Timedelta(minutes=common_shift)
    boundary_raw=np.array([
        ((t.hour*60+t.minute)%mins)==0 for t in raw_server_times
    ],dtype=bool)
    if len(boundary_raw) and not boundary_raw.all():
        raise RuntimeError(f"Raw-server boundary invariance failed rank {rank}")

    pd.DataFrame({
        "development_rank":rank,
        "aligned_decision_time":times,
        "equivalent_ftmo_server_time":raw_server_times,
    }).to_csv(OUT/f"RANK_{rank}_PARITY_SIGNAL_TIMES.csv",index=False)

    signal_rows.append({
        "development_rank":rank,
        "expected_v98_ftmo_signal_n_full":expected,
        "rebuilt_research_signal_n":research_n,
        "mql20_signal_n":mql_n,
        "mask_mismatch_rows":mismatch,
        "clock_shift_min":common_shift,
        "sampling_boundary_invariant":True,
        "signal_parity_ok":True,
    })

SIG=pd.DataFrame(signal_rows)
SIG.to_csv(OUT/"FROZEN_SIGNAL_PARITY.csv",index=False)
status(OUT,5,10,"rank 7/9 signal masks exactly reproduce V98",rank7=int(SIG.loc[SIG.development_rank==7,"mql20_signal_n"].iloc[0]),rank9=int(SIG.loc[SIG.development_rank==9,"mql20_signal_n"].iloc[0]))

# ---------- source contract / restart semantics ----------
required_source=[
    '#property version   "100.20"',
    "#define ACTIVATION_NOT_BEFORE D'2027.01.02 00:00'",
    "GridCloseAt(",
    "MeanStdFinite12(",
    "nfinite<6",
    "double mean=prior.mean;",
    "UpdateStat(g_stats[slot],value);",
    "SaveRuntimeState()",
    "CatchUpToLatest()",
]
missing=[x for x in required_source if x not in src]
if missing:
    raise RuntimeError(f"V100.20 source contract missing {missing}")
for forbidden in ("OrderSend(","CTrade","trade.Buy(","trade.Sell(","PositionOpen("):
    if forbidden in src:
        raise RuntimeError(f"Order-sending token found: {forbidden}")
status(OUT,6,10,"current MQL source contract/restart/shadow locks verified")

# ---------- write explicit supersession ----------
supersession={
    "supersedes_v100_10_receipts":True,
    "current_mql_version":"100.20",
    "reason":[
        "V100.10 was stricter than research around missing M5 bins for rv60/zret60 and ret30 intermediate bars",
        "V100.20 now matches original pandas min_periods=6/sample-std semantics",
        "state persistence changed from sum/sumsq to numerically stable Welford n/mean/M2",
    ],
    "scientific_hypotheses_changed":False,
    "rank_set_changed":False,
    "thresholds_changed":False,
    "2026_accessed":False,
}
write_json(OUT/"V100_10_SUPERSESSION.json",supersession)
status(OUT,7,10,"V100.10 explicitly superseded by parity-verified V100.20")

receipt={
    "run_id":RID,
    "status":"COMPLETE_V100B_MQL_RESEARCH_PARITY",
    "engine_version":ENGINE_VERSION,
    "source_v97e":V97E.name,
    "source_v98":V98.name,
    "source_v100_audit":V100.name,
    "mq5_sha256":sha256(MQ5),
    "mql_version":"100.20",
    "feature_parity_all":bool(FR["feature_parity_ok"].all()),
    "state_parity_all":bool(SR["state_parity_ok"].all()),
    "signal_parity_all":bool(SIG["signal_parity_ok"].all()),
    "rank7_signal_n":int(SIG.loc[SIG["development_rank"]==7,"mql20_signal_n"].iloc[0]),
    "rank9_signal_n":int(SIG.loc[SIG["development_rank"]==9,"mql20_signal_n"].iloc[0]),
    "candidate_set_changed":False,
    "thresholds_retuned":False,
    "order_sending_code_present":False,
    "real_post2026_seed_generated":False,
    "2026_market_values_accessed":False,
    "next":"V100.20 IS PRE-2026 DEPLOYMENT-READY IN SHADOW-LOCKED FORM; DO NOT GENERATE REAL SEED OR OPEN 2026 UNTIL INTENTIONAL HOLDOUT RELEASE",
}
write_json(OUT/"RUN_RECEIPT.json",receipt)
status(OUT,8,10,"parity receipt written")
status(OUT,9,10,"2026 remained unopened")
status(OUT,10,10,"DONE")

print("\n=== V100B RECEIPT ===")
print(json.dumps(receipt,indent=2))
print("\n=== V100B FEATURE PARITY ===")
print(FR.to_string(index=False))
print("\n=== V100B STATE PARITY ===")
print(SR.to_string(index=False))
print("\n=== V100B SIGNAL PARITY ===")
print(SIG.to_string(index=False))
print("\nRUN:",OUT)
