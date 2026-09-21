from pathlib import Path
import pandas as pd
import numpy as np
import json
import math
from datetime import datetime
from scipy.stats import t as student_t

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v86"
OUTBASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v86a"
OUTBASE.mkdir(parents=True,exist_ok=True)
TOP_RAW=5000
TOP_UNIQUE=100
CHUNK=1_000_000
BLOCK_DAYS=28
MIN_N=120
MIN_BLOCKS=12
Q=0.05

def H(m):
    x=float(m)
    return math.log(x)+0.5772156649015329+1/(2*x)-1/(12*x*x)

def decode_trial(trial_idx,singleton_slots,nt,pair_i,pair_j):
    if trial_idx<singleton_slots:
        block=2*nt
        fi=trial_idx//block
        rem=trial_idx%block
        return {"kind":"singleton","fi":int(fi),"fj":None,"si":int(rem//nt),"sj":None,"ti":int(rem%nt)}
    off=trial_idx-singleton_slots
    block=4*nt
    pi=off//block
    rem=off%block
    combo=rem//nt
    return {"kind":"pair","fi":int(pair_i[int(pi)]),"fj":int(pair_j[int(pi)]),
            "si":int(combo//2),"sj":int(combo%2),"ti":int(rem%nt)}

def cond_mask(d,ST):
    m=ST[d["fi"],d["si"],:]
    if d["kind"]=="pair":
        m=m & ST[d["fj"],d["sj"],:]
    return m

def cluster_stats(mask,y,blocks):
    idx=np.flatnonzero(mask)
    vals=y[idx]
    b=blocks[idx]
    finite=np.isfinite(vals)
    vals=vals[finite].astype(np.float64)
    b=b[finite]
    n=len(vals)
    if n==0:
        return {"n":0,"blocks":0,"mean":np.nan,"median":np.nan,"win_rate":np.nan,"p":np.nan,
                "sum_return":np.nan,"compound_return":np.nan}
    mean=float(vals.mean())
    median=float(np.median(vals))
    win=float((vals>0).mean())
    sumret=float(vals.sum())
    comp=float(np.expm1(np.log1p(vals).sum())) if np.all(vals>-1) else np.nan
    starts=np.r_[0,np.flatnonzero(b[1:]!=b[:-1])+1]
    g=len(starts)
    if n<MIN_N or g<MIN_BLOCKS:
        return {"n":n,"blocks":g,"mean":mean,"median":median,"win_rate":win,"p":np.nan,
                "sum_return":sumret,"compound_return":comp}
    bs=np.add.reduceat(vals,starts)
    bc=np.diff(np.r_[starts,n]).astype(np.float64)
    u=bs-bc*mean
    meat=float((u*u).sum())
    if meat<=0 or not np.isfinite(meat):
        p=np.nan
    else:
        se2=(g/(g-1.0))*meat/(n*n)
        stat=mean/math.sqrt(se2)
        p=float(2*student_t.sf(abs(stat),df=g-1))
    return {"n":n,"blocks":g,"mean":mean,"median":median,"win_rate":win,"p":p,
            "sum_return":sumret,"compound_return":comp}

runs=sorted(BASE.glob("GEF86-*"))
runs=[p for p in runs if (p/"RUN_RECEIPT.json").exists()]
if not runs:
    raise RuntimeError("No completed V86 run")
V86=runs[-1]
r86=json.loads((V86/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r86.get("status")!="COMPLETE_NO_TRAIN_BY_SURVIVORS":
    raise RuntimeError(f"Expected COMPLETE_NO_TRAIN_BY_SURVIVORS, got {r86.get('status')}")
if r86.get("2013_target_values_accessed") or r86.get("2014_plus_accessed"):
    raise RuntimeError("Unexpected holdout/later access in V86 receipt")

spec=json.loads((V86/"FROZEN_V86_SPEC.json").read_text(encoding="utf-8"))
V85=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v85"/spec["source_v85"]
design=json.loads((V85/"TRIAL_DESIGN.json").read_text(encoding="utf-8"))
catalog=pd.read_csv(V85/"FROZEN_ELIGIBLE_FEATURES.csv").reset_index(drop=True)
pairs=pd.read_parquet(V85/"FROZEN_PAIR_UNIVERSE.parquet")
state_meta=json.loads((V85/"STATE_CACHE_META.json").read_text(encoding="utf-8"))

V84C=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v84c"/design["source_v84c"]
r84=json.loads((V84C/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V83B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v83b"/r84["source_v83b"]
manifest=json.loads((V83B/"REPAIRED_ARCHITECTURE_MANIFEST.json").read_text(encoding="utf-8"))

nt=int(design["targets"])
singleton_slots=int(design["singleton_slots"])
total_slots=int(design["predeclared_trial_slots"])
pair_i=pairs["feature_i"].to_numpy(dtype=np.int64)
pair_j=pairs["feature_j"].to_numpy(dtype=np.int64)

pmap=np.memmap(V86/"TRAIN_BLOCK_PVALUES.float32.dat",mode="r",dtype=np.float32,shape=(total_slots,))

# Chunked exact top-N raw p-values, no holdout access.
cand_idx=[]
cand_p=[]
for start in range(0,total_slots,CHUNK):
    stop=min(start+CHUNK,total_slots)
    x=np.asarray(pmap[start:stop])
    finite=np.flatnonzero(np.isfinite(x))
    if not len(finite):
        continue
    k=min(TOP_RAW,len(finite))
    local=finite[np.argpartition(x[finite],k-1)[:k]]
    cand_idx.extend((local+start).tolist())
    cand_p.extend(x[local].astype(float).tolist())

order=np.argsort(np.asarray(cand_p))[:TOP_RAW]
top_idx=np.asarray(cand_idx,dtype=np.int64)[order]
top_p=np.asarray(cand_p,dtype=np.float64)[order]

# Train-only targets, same filter already proven by V86.
F=pd.read_parquet(manifest["price_state_5m_path"])
F.index=pd.to_datetime(F.index)
train_times=F.index[F.index<pd.Timestamp("2013-01-01")]
Y=pd.read_parquet(manifest["targets_5m_path"],filters=[("decision_time_utc","<",datetime(2013,1,1))])
Y.index=pd.to_datetime(Y.index)
Y=Y.reindex(train_times)
targets=[c for c in Y.columns if "_fwd_" in str(c)]
YT=np.array(Y[targets],dtype=np.float32,copy=True)
minute=(train_times.view("int64")//60_000_000_000).astype(np.int64)
horizons=[]
for ti,c in enumerate(targets):
    h=int(str(c).rsplit("_fwd_",1)[1].rstrip("m"))
    horizons.append(h)
    YT[(minute%h)!=0,ti]=np.nan
blocks=((train_times.normalize()-pd.Timestamp("2010-01-01")).days.to_numpy()//BLOCK_DAYS).astype(np.int16)

shape=tuple(state_meta["train_shape"])
ST=np.memmap(V85/"STATE_TRAIN.bool.dat",mode="r",dtype=np.bool_,shape=shape)

m=int(r86["valid_train_tests"])
hm=H(m)
rows=[]
seen=set()
for global_rank,(trial,praw) in enumerate(zip(top_idx,top_p),start=1):
    d=decode_trial(int(trial),singleton_slots,nt,pair_i,pair_j)
    mask=cond_mask(d,ST)
    ti=d["ti"]
    direction_key=1
    key=(np.packbits(mask).tobytes(),ti)
    if key in seen:
        continue
    seen.add(key)
    s=cluster_stats(mask,YT[:,ti],blocks)
    direction=1 if np.isfinite(s["mean"]) and s["mean"]>0 else -1
    bycrit=Q*global_rank/(m*hm)
    row={
      "raw_rank":global_rank,
      "trial_index":int(trial),
      "kind":d["kind"],
      "family_i":str(catalog.loc[d["fi"],"family"]),
      "feature_i":str(catalog.loc[d["fi"],"feature"]),
      "state_i":("LO","HI")[d["si"]],
      "family_j":None if d["fj"] is None else str(catalog.loc[d["fj"],"family"]),
      "feature_j":None if d["fj"] is None else str(catalog.loc[d["fj"],"feature"]),
      "state_j":None if d["sj"] is None else ("LO","HI")[d["sj"]],
      "target":targets[ti],
      "horizon_min":horizons[ti],
      "direction":"LONG" if direction>0 else "SHORT",
      "n_signals":int(s["n"]),
      "blocks":int(s["blocks"]),
      "mean_bp":float(s["mean"]*1e4),
      "median_bp":float(s["median"]*1e4),
      "win_rate_pct":float(s["win_rate"]*100),
      "cluster_p_two":float(s["p"]) if np.isfinite(s["p"]) else np.nan,
      "by_critical_at_raw_rank":float(bycrit),
      "p_over_by_critical":float(praw/bycrit) if bycrit>0 else np.nan,
      "gross_sum_return_pct":float(s["sum_return"]*100),
      "gross_compound_return_pct":float(s["compound_return"]*100) if np.isfinite(s["compound_return"]) else np.nan,
      "gross_pnl_on_10k_full_notional":float(s["sum_return"]*10000),
      "gross_pnl_on_100k_full_notional":float(s["sum_return"]*100000),
    }
    rows.append(row)
    if len(rows)>=TOP_UNIQUE:
        break

R=pd.DataFrame(rows)
RID="GEF86A-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=OUTBASE/RID
OUT.mkdir(parents=True,exist_ok=True)
R.to_csv(OUT/"TOP_RAW_UNIQUE_V86.csv",index=False)

summary={
  "run_id":RID,
  "source_v86":V86.name,
  "valid_train_tests":m,
  "global_BY_q":Q,
  "harmonic_factor":hm,
  "rank1_BY_critical_p":Q/(m*hm),
  "best_raw_p":float(top_p[0]),
  "best_raw_p_over_rank1_BY_critical":float(top_p[0]/(Q/(m*hm))),
  "top_unique_reported":len(R),
  "2013_target_values_accessed":False,
  "2014_plus_accessed":False
}
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")

print("\n=== V86A SUMMARY ===")
print(json.dumps(summary,indent=2))
print("\n=== TOP 25 RAW UNIQUE ===")
cols=["raw_rank","kind","family_i","state_i","family_j","state_j","target","direction",
      "n_signals","blocks","mean_bp","median_bp","win_rate_pct","cluster_p_two",
      "p_over_by_critical","gross_sum_return_pct","gross_pnl_on_10k_full_notional",
      "gross_pnl_on_100k_full_notional"]
print(R[cols].head(25).to_string(index=False))
print("\nRUN:",OUT)
