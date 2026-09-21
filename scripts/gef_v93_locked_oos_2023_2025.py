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
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v93"
BASE.mkdir(parents=True,exist_ok=True)

ENGINE_VERSION="V93.0"
MIN_FAST_STATE=5000
BLOCK_DAYS=5
GENERIC_COST_BP=1.0
OOS_START=pd.Timestamp("2023-01-01 00:00")
OOS_END=pd.Timestamp("2025-12-31 23:55")
E2_START=pd.Timestamp("2014-01-01 00:00")
E2_END=pd.Timestamp("2017-12-31 23:55")
E3_START=pd.Timestamp("2018-01-01 00:00")
E3_END=pd.Timestamp("2022-12-31 23:55")

OOS_RULE={
    "minimum_total_signals":20,
    "gross_mean_positive":True,
    "net_after_hypothetical_1bp_positive":True,
    "minimum_positive_net1bp_years_of_3":2,
    "minimum_years_with_at_least_3_signals":2,
    "cluster_one_sided_p":"diagnostic only, not a guillotine",
    "BH_q_across_unique_frozen_panel":"diagnostic only, q=0.10",
    "no_posthoc_candidate_or_parameter_changes":True,
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
    payload={"engine_version":ENGINE_VERSION,"step":step,"steps":total,
             "percent":round(100*step/total,1),"timestamp_utc":pd.Timestamp.now("UTC").isoformat(),
             "message":msg,**extra}
    write_json(out/"LIVE_STATUS.json",payload)
    tail=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF93] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

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
    for y in years:
        if y>2025: raise RuntimeError("V93 refuses 2026+")
        p=ROOT/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
        if not p.exists(): raise RuntimeError(f"Missing {p}")
        d=pd.read_parquet(p)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        pc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None and isinstance(d.index,pd.DatetimeIndex):
            d=d.reset_index(); dc=d.columns[0]
        if dc is None or pc is None: raise RuntimeError(f"Cannot identify datetime/close {p}")
        utc=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(hours=5)
        q=pd.DataFrame({"utc":utc,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
        q=q[q["utc"].dt.year<=2025]
        parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    return q.set_index("utc")["px"]

def target_array(P,grid,target):
    sym,rest=str(target).split("_fwd_",1)
    mins=int(rest.rstrip("m")); k=mins//5
    raw=P[sym].shift(-k)/P[sym]-1
    y=np.array(raw.reindex(grid),dtype=np.float64,copy=True)
    minute=(grid.view("int64")//60_000_000_000).astype(np.int64)
    y[(minute%mins)!=0]=np.nan
    return y,mins

def metrics(x):
    x=np.asarray(x,dtype=np.float64); x=x[np.isfinite(x)]
    if not len(x):
        return {"n":0,"mean_bp":np.nan,"median_bp":np.nan,"win_rate_pct":np.nan,
                "sum_pct":np.nan,"net_1bp_mean_bp":np.nan,"max_drawdown_pct":np.nan}
    mean_bp=float(x.mean()*1e4)
    if np.any(x<=-1): mdd=np.nan
    else:
        eq=np.cumprod(1+x); peak=np.maximum.accumulate(eq); mdd=float(np.min(eq/peak-1)*100)
    return {"n":int(len(x)),"mean_bp":mean_bp,"median_bp":float(np.median(x)*1e4),
            "win_rate_pct":float((x>0).mean()*100),"sum_pct":float(x.sum()*100),
            "net_1bp_mean_bp":mean_bp-GENERIC_COST_BP,"max_drawdown_pct":mdd}

def cluster_positive(ret,blocks):
    r=np.asarray(ret,dtype=np.float64); b=np.asarray(blocks)
    good=np.isfinite(r); r=r[good]; b=b[good]; n=len(r)
    if n==0: return {"n":0,"clusters":0,"mean":np.nan,"p_one":np.nan}
    mean=float(r.mean())
    uniq=np.unique(b); g=len(uniq)
    if g<8: return {"n":n,"clusters":g,"mean":mean,"p_one":np.nan}
    # Robust score aggregation does not assume rows are adjacent by block.
    u=[]
    for k in uniq:
        x=r[b==k]
        u.append(float(np.sum(x-mean)))
    meat=float(np.sum(np.square(u)))
    if meat<=0 or not np.isfinite(meat): return {"n":n,"clusters":g,"mean":mean,"p_one":np.nan}
    se2=(g/(g-1.0))*meat/(n*n)
    if se2<=0 or not np.isfinite(se2): return {"n":n,"clusters":g,"mean":mean,"p_one":np.nan}
    t=mean/math.sqrt(se2)
    return {"n":n,"clusters":g,"mean":mean,"t":float(t),"p_one":float(student_t.sf(t,df=g-1))}

def bh_adjust(p):
    p=np.asarray(p,dtype=np.float64)
    out=np.full(len(p),np.nan); idx=np.flatnonzero(np.isfinite(p))
    if not len(idx): return out
    vals=p[idx]; order=np.argsort(vals); ranked=vals[order]
    adj=ranked*len(ranked)/np.arange(1,len(ranked)+1,dtype=np.float64)
    adj=np.minimum.accumulate(adj[::-1])[::-1]; adj=np.clip(adj,0,1)
    out[idx[order]]=adj
    return out

# ---------- immutable V92 panel ----------
runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v92").glob("GEF92-*"))
runs=[p for p in runs if (p/"RUN_RECEIPT.json").exists() and (p/"FINAL_OOS_FREEZE.json").exists()]
if not runs: raise RuntimeError("No completed V92 freeze")
V92=runs[-1]
r92=json.loads((V92/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
frz=json.loads((V92/"FINAL_OOS_FREEZE.json").read_text(encoding="utf-8"))
panel_path=V92/"FROZEN_CLEAN_OOS_PANEL.csv"
panel=pd.read_csv(panel_path)
if r92.get("status")!="COMPLETE_V92_CLEAN_TEMPORAL_LADDER": raise RuntimeError("V92 incomplete")
if r92.get("2023_plus_values_accessed") or r92.get("protected_2026_accessed"): raise RuntimeError("V92 access assertion violated")
if sha256(panel_path)!=frz["panel_sha256"]: raise RuntimeError("V92 panel hash mismatch")
if len(panel)!=int(frz["panel_size"]): raise RuntimeError("V92 panel size mismatch")
if set(frz["contaminated_markets_excluded"])!={"EURUSD","NSXUSD","XAGUSD"}: raise RuntimeError("Unexpected contamination set")

RID="GEF93-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID; OUT.mkdir(parents=True,exist_ok=False)
status(OUT,1,11,"frozen V92 panel loaded; OOS scoring spec not yet applied",source_v92=V92.name,panel=len(panel))

spec={"run_id":RID,"status":"V93_LOCKED_OOS_SCORING_SPEC_FROZEN","source_v92":V92.name,
      "panel_sha256":frz["panel_sha256"],"oos_window":"2023-2025","generic_cost_bp":GENERIC_COST_BP,
      "oos_rule":OOS_RULE,"2023_2025_strategy_outcomes_accessed":False,"protected_2026_accessed":False}
write_json(OUT/"V93_LOCKED_OOS_SCORING_FREEZE.json",spec)
spec_sha=sha256(OUT/"V93_LOCKED_OOS_SCORING_FREEZE.json")
status(OUT,2,11,"OOS scoring/economic criteria physically frozen",freeze_sha256=spec_sha[:16])

# ---------- lineage ----------
V85=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v85"/r92["source_v85"]
design=json.loads((V85/"TRIAL_DESIGN.json").read_text())
state_meta=json.loads((V85/"STATE_CACHE_META.json").read_text())
catalog=pd.read_csv(V85/"FROZEN_ELIGIBLE_FEATURES.csv").reset_index(drop=True)
V84C=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v84c"/design["source_v84c"]
r84=json.loads((V84C/"RUN_RECEIPT.json").read_text())
V83B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v83b"/r84["source_v83b"]
manifest=json.loads((V83B/"REPAIRED_ARCHITECTURE_MANIFEST.json").read_text())
Fhist=pd.read_parquet(manifest["price_state_5m_path"]); Fhist.index=pd.to_datetime(Fhist.index)
train_shape=tuple(state_meta["train_shape"]); hold_shape=tuple(state_meta["hold_shape"])
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
if {"EURUSD","NSXUSD","XAGUSD"} & needed_markets: raise RuntimeError("Contaminated market leaked into V93")
if sorted(needed_markets)!=sorted(frz["oos_markets"]): raise RuntimeError("V93 market set != V92 frozen market set")
status(OUT,3,11,"original architecture and exact frozen market set resolved",markets=len(needed_markets),features=len(needed_features),targets=len(needed_targets))

# all OOS files must exist before any scoring
missing=[]
for sym in sorted(needed_markets):
    for year in range(2023,2026):
        p=ROOT/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
        if not p.exists(): missing.append(str(p))
if missing: raise RuntimeError(f"Missing V93 OOS files after materialization: {missing}")
status(OUT,4,11,"all 2023-2025 frozen-panel files present",files=len(needed_markets)*3)

# ---------- causal continuation through 2025 ----------
warm_grid=pd.date_range("2013-12-01 00:00",OOS_END,freq="5min")
post2013_grid=pd.date_range(E2_START,OOS_END,freq="5min")
P=pd.DataFrame(index=warm_grid)
tp=time.time()
for i,sym in enumerate(sorted(needed_markets),1):
    raw=load_m1(sym,range(2013,2026))
    P[sym]=raw.resample("5min",label="right",closed="left").last().reindex(warm_grid).astype("float64")
    elapsed=time.time()-tp; rate=i/max(elapsed,1e-9); eta=(len(needed_markets)-i)/max(rate,1e-9)
    print(f"[GEF93] market {i}/{len(needed_markets)} {sym} | elapsed={elapsed/60:.1f}m eta={eta/60:.1f}m",flush=True)
status(OUT,5,11,"2014-2025 causal price continuation materialized; 2026 untouched",rows=len(post2013_grid))

states={}
for i,feat in enumerate(needed_features,1):
    fi=feature_index[feat]
    ext=build_fast_feature(feat,P).reindex(post2013_grid)
    full=pd.concat([pd.to_numeric(Fhist[feat],errors="coerce"),pd.to_numeric(ext,errors="coerce")])
    lo,hi=causal_states(full,MIN_FAST_STATE)
    hist_rows=len(Fhist)
    exp_lo=np.concatenate([ST[fi,0,:],SH[fi,0,:]])
    exp_hi=np.concatenate([ST[fi,1,:],SH[fi,1,:]])
    ml=int(np.count_nonzero(lo[:hist_rows]!=exp_lo)); mh=int(np.count_nonzero(hi[:hist_rows]!=exp_hi))
    if ml or mh: raise RuntimeError(f"State parity failed {feat}: LO={ml} HI={mh}")
    states[(feat,"LO")]=lo[hist_rows:]; states[(feat,"HI")]=hi[hist_rows:]
    if i==1 or i==len(needed_features) or i%10==0:
        print(f"[GEF93] state parity {i}/{len(needed_features)}",flush=True)
status(OUT,6,11,"2010-2013 state parity exact for every frozen feature",features=len(needed_features))

# ---------- reproduce V92 E2/E3 exactly before OOS scoring ----------
target_cache={}
for t in needed_targets:
    target_cache[t]=target_array(P,post2013_grid,t)

parity=[]
for r in panel.itertuples(index=False):
    mask=np.asarray(states[(r.feature_i,r.state_i)]) & np.asarray(states[(r.feature_j,r.state_j)])
    raw,mins=target_cache[r.target]
    ret=(1.0 if r.direction=="LONG" else -1.0)*raw
    h=pd.Timedelta(minutes=mins)
    e2=np.asarray((post2013_grid>=E2_START)&(post2013_grid<=E2_END)&((post2013_grid+h)<=E2_END))
    e3=np.asarray((post2013_grid>=E3_START)&(post2013_grid<=E3_END)&((post2013_grid+h)<=E3_END))
    m2=metrics(np.where(mask&e2,ret,np.nan)); m3=metrics(np.where(mask&e3,ret,np.nan))
    ok=(m2["n"]==int(r.e2_2014_2017_n) and m3["n"]==int(r.e3_2018_2022_n)
        and np.isclose(m2["mean_bp"],float(r.e2_2014_2017_mean_bp),rtol=0,atol=1e-6)
        and np.isclose(m3["mean_bp"],float(r.e3_2018_2022_mean_bp),rtol=0,atol=1e-6))
    parity.append({"development_rank":int(r.development_rank),"e2_n":m2["n"],"e2_mean_bp":m2["mean_bp"],
                   "e3_n":m3["n"],"e3_mean_bp":m3["mean_bp"],"parity_ok":bool(ok)})
    if not ok:
        raise RuntimeError(f"V92 parity failed development_rank={r.development_rank}")
pd.DataFrame(parity).to_csv(OUT/"V92_DEVELOPMENT_PARITY.csv",index=False)
status(OUT,7,11,"all 15 frozen hypotheses reproduce V92 development exactly",hypotheses=len(panel))

# ---------- locked OOS ----------
oos=np.asarray((post2013_grid>=OOS_START)&(post2013_grid<=OOS_END))
oos_times=post2013_grid[oos]
blocks=((oos_times.normalize()-OOS_START.normalize()).days.to_numpy()//BLOCK_DAYS).astype(np.int16)
records=[]
for idx,r in enumerate(panel.itertuples(index=False),1):
    mask=np.asarray(states[(r.feature_i,r.state_i)]) & np.asarray(states[(r.feature_j,r.state_j)])
    raw,mins=target_cache[r.target]
    ret=(1.0 if r.direction=="LONG" else -1.0)*raw
    h=pd.Timedelta(minutes=mins)
    rv=np.array(ret[oos],dtype=np.float64,copy=True)
    mv=np.asarray(mask[oos],dtype=bool)
    boundary_ok=np.asarray((oos_times+h)<=OOS_END)
    rv[~boundary_ok]=np.nan
    gated=np.where(mv,rv,np.nan)
    m=metrics(gated)
    ct=cluster_positive(gated,blocks)

    rec={"development_rank":int(r.development_rank),"trial_index":int(r.trial_index),
         "feature_i":r.feature_i,"state_i":r.state_i,"family_i":r.family_i,
         "feature_j":r.feature_j,"state_j":r.state_j,"family_j":r.family_j,
         "target":r.target,"direction":r.direction,"n":m["n"],"mean_bp":m["mean_bp"],
         "net_1bp_mean_bp":m["net_1bp_mean_bp"],"median_bp":m["median_bp"],
         "win_rate_pct":m["win_rate_pct"],"sum_pct":m["sum_pct"],"max_drawdown_pct":m["max_drawdown_pct"],
         "cluster_blocks":ct["clusters"],"cluster_p_one":ct.get("p_one",np.nan)}

    pos_net_years=0; coverage_years=0
    for year in (2023,2024,2025):
        yy=np.asarray(oos_times.year==year)
        ym=metrics(gated[yy])
        rec[f"y{year}_n"]=ym["n"]; rec[f"y{year}_mean_bp"]=ym["mean_bp"]; rec[f"y{year}_net1bp_mean_bp"]=ym["net_1bp_mean_bp"]
        if ym["n"]>=3: coverage_years+=1
        if ym["n"]>=3 and np.isfinite(ym["net_1bp_mean_bp"]) and ym["net_1bp_mean_bp"]>0: pos_net_years+=1
    rec["coverage_years_ge3signals"]=coverage_years
    rec["positive_net1bp_years"]=pos_net_years
    rec["economic_oos_pass"]=bool(
        m["n"]>=OOS_RULE["minimum_total_signals"]
        and np.isfinite(m["mean_bp"]) and m["mean_bp"]>0
        and np.isfinite(m["net_1bp_mean_bp"]) and m["net_1bp_mean_bp"]>0
        and pos_net_years>=OOS_RULE["minimum_positive_net1bp_years_of_3"]
        and coverage_years>=OOS_RULE["minimum_years_with_at_least_3_signals"]
    )
    records.append(rec)
    print(f"[GEF93] OOS {idx}/{len(panel)} rank={r.development_rank} n={m['n']} mean_bp={m['mean_bp']:.4f} net1={m['net_1bp_mean_bp']:.4f}",flush=True)

R=pd.DataFrame(records)
R["bh_q_panel"]=bh_adjust(R["cluster_p_one"].to_numpy(dtype=float))
R["bh_q10_diagnostic"]=R["bh_q_panel"]<=0.10
R=R.sort_values(["economic_oos_pass","net_1bp_mean_bp","cluster_p_one"],ascending=[False,False,True],kind="mergesort").reset_index(drop=True)
R.to_csv(OUT/"LOCKED_OOS_2023_2025_ALL_15.csv",index=False)

status(OUT,8,11,"locked OOS scored for entire frozen panel",economic_pass=int(R["economic_oos_pass"].sum()),bh_q10=int(R["bh_q10_diagnostic"].sum()))

receipt={"run_id":RID,"status":"COMPLETE_V93_LOCKED_OOS_2023_2025","engine_version":ENGINE_VERSION,
         "source_v92":V92.name,"panel_sha256":frz["panel_sha256"],"scoring_freeze_sha256":spec_sha,
         "frozen_hypotheses":len(R),"economic_oos_pass":int(R["economic_oos_pass"].sum()),
         "nominal_cluster_p05":int((R["cluster_p_one"]<=0.05).sum()),
         "bh_q10_diagnostic":int(R["bh_q10_diagnostic"].sum()),
         "best_net1bp_mean_bp":float(R["net_1bp_mean_bp"].max()) if len(R) else None,
         "2023_2025_strategy_outcomes_accessed":True,"protected_2026_accessed":False,
         "next":"STOP_FOR_HUMAN_REVIEW_DO_NOT_RETUNE_ON_2023_2025"}
write_json(OUT/"RUN_RECEIPT.json",receipt)
status(OUT,9,11,"OOS receipt written",economic_pass=receipt["economic_oos_pass"],bh_q10=receipt["bh_q10_diagnostic"])
status(OUT,10,11,"2026 remains protected and unopened")
status(OUT,11,11,"DONE")

print("\n=== V93 LOCKED OOS RECEIPT ==="); print(json.dumps(receipt,indent=2))
print("\n=== V93 LOCKED OOS ALL 15 ===")
cols=["development_rank","family_i","state_i","family_j","state_j","target","direction","n","mean_bp","net_1bp_mean_bp",
      "positive_net1bp_years","coverage_years_ge3signals","cluster_p_one","bh_q_panel","economic_oos_pass",
      "y2023_n","y2023_mean_bp","y2024_n","y2024_mean_bp","y2025_n","y2025_mean_bp"]
print(R[cols].to_string(index=False))
print("\nRUN:",OUT)
