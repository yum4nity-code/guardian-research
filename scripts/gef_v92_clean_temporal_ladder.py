from pathlib import Path
import pandas as pd
import numpy as np
import json
import math
import re
import time
import hashlib
from datetime import datetime

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v92"
BASE.mkdir(parents=True,exist_ok=True)

ENGINE_VERSION="V92.0"
CONTAMINATED_OOS_MARKETS={"EURUSD","NSXUSD","XAGUSD"}
TOP_CLEAN_UNIQUE_PER_LEDGER=500
TOP_RAW_SCAN_PER_LEDGER=100_000
FINAL_PANEL_MAX=25
GENERIC_COST_BP=1.0
MIN_FAST_STATE=5000
STATUS_SECONDS=30.0

E2_START=pd.Timestamp("2014-01-01 00:00")
E2_END=pd.Timestamp("2017-12-31 23:55")
E3_START=pd.Timestamp("2018-01-01 00:00")
E3_END=pd.Timestamp("2022-12-31 23:55")
EXT_END=E3_END

SELECTION_RULE={
    "candidate_pool":"union of top 500 unique CLEAN fast-price pair hypotheses from V85 naive ledger and V86 block-cluster ledger, train 2010-2012 only",
    "clean_oos_definition":"exclude any hypothesis whose target or either feature depends on EURUSD, NSXUSD, or XAGUSD, because those 2023-2025 values were opened by V91",
    "no_global_p_guillotine":True,
    "holdout_2013_min_n":5,
    "holdout_2013_directional_mean_must_be_positive":True,
    "2014_2017_min_n":20,
    "2018_2022_min_n":30,
    "2018_2022_net_after_1bp_must_be_positive":True,
    "major_eras_with_positive_net1bp_min":2,
    "positive_years_2014_2022_min":5,
    "full_2010_2022_net_after_1bp_must_be_positive":True,
    "ranking":[
        "qualified first",
        "major eras with positive net1bp descending",
        "worst major-era net1bp descending",
        "positive years 2014-2022 descending",
        "2018-2022 net1bp descending",
        "full 2010-2022 net1bp descending",
        "best train-ledger rank ascending"
    ],
    "final_panel_max":FINAL_PANEL_MAX,
    "final_oos_multiplicity":"BH q=0.10 across frozen final panel will be diagnostic in V93; economics and year stability remain primary",
}

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def status(out,stage,msg,**extra):
    payload={"engine_version":ENGINE_VERSION,"stage":stage,"timestamp_utc":pd.Timestamp.now("UTC").isoformat(),"message":msg,**extra}
    write_json(out/"LIVE_STATUS.json",payload)
    tail=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF92] {stage} | {msg}"+(f" | {tail}" if tail else ""),flush=True)

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
    raise RuntimeError(f"Unsupported fast feature reconstruction: {name}")

def feature_market(feature):
    m=re.match(r"price_([A-Z]+)_",str(feature))
    return m.group(1) if m else None

def target_market(target):
    return str(target).split("_fwd_",1)[0]

def supported_fast(feature):
    return any(re.fullmatch(p,str(feature)) for p in [
        r"price_[A-Z]+_ret_\d+m",
        r"price_[A-Z]+_rv_\d+m",
        r"price_[A-Z]+_trend_\d+m",
        r"price_[A-Z]+_zret_\d+m",
    ])

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

def top_global_indices(pmap,k,chunk=1_000_000):
    best_i=np.empty(0,dtype=np.int64)
    best_p=np.empty(0,dtype=np.float64)
    total=len(pmap)
    for start in range(0,total,chunk):
        stop=min(start+chunk,total)
        x=np.asarray(pmap[start:stop])
        finite=np.flatnonzero(np.isfinite(x))
        if not len(finite):
            continue
        kk=min(k,len(finite))
        loc=finite[np.argpartition(x[finite],kk-1)[:kk]]
        ci=loc.astype(np.int64)+start
        cp=x[loc].astype(np.float64)
        if len(best_i):
            ci=np.concatenate([best_i,ci]); cp=np.concatenate([best_p,cp])
        if len(ci)>k:
            keep=np.argpartition(cp,k-1)[:k]
            ci=ci[keep]; cp=cp[keep]
        best_i,best_p=ci,cp
    if not len(best_i):
        return best_i,best_p
    order=np.lexsort((best_i,best_p))
    return best_i[order],best_p[order]

def load_m1(sym,years):
    parts=[]
    for year in years:
        if year>2022:
            raise RuntimeError("V92 refuses to read 2023+")
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
        q=q[q["utc"].dt.year<=2022]
        parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    return q.set_index("utc")["px"]

def metrics(x):
    x=np.asarray(x,dtype=np.float64)
    x=x[np.isfinite(x)]
    if not len(x):
        return {"n":0,"mean_bp":np.nan,"net1bp_mean_bp":np.nan,"sum_return":0.0,"win_rate_pct":np.nan}
    mean_bp=float(x.mean()*1e4)
    return {
        "n":int(len(x)),
        "mean_bp":mean_bp,
        "net1bp_mean_bp":mean_bp-GENERIC_COST_BP,
        "sum_return":float(x.sum()),
        "win_rate_pct":float((x>0).mean()*100),
    }

def target_array_from_prices(P,grid,target):
    sym,rest=str(target).split("_fwd_",1)
    mins=int(rest.rstrip("m"))
    k=mins//5
    raw=P[sym].shift(-k)/P[sym]-1
    y=np.array(raw.reindex(grid),dtype=np.float32,copy=True)
    minute=(grid.view("int64")//60_000_000_000).astype(np.int64)
    y[(minute%mins)!=0]=np.nan
    return y

# ---------- immutable lineage ----------
v86runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v86").glob("GEF86-*"))
v86runs=[p for p in v86runs if (p/"RUN_RECEIPT.json").exists() and (p/"TRAIN_BLOCK_PVALUES.float32.dat").exists()]
if not v86runs:
    raise RuntimeError("No completed V86 p-value ledger")
V86=v86runs[-1]
r86=json.loads((V86/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r86.get("2013_target_values_accessed") or r86.get("2014_plus_accessed"):
    raise RuntimeError("Unexpected V86 later-window access")
spec86=json.loads((V86/"FROZEN_V86_SPEC.json").read_text(encoding="utf-8"))
V85=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v85"/spec86["source_v85"]
design=json.loads((V85/"TRIAL_DESIGN.json").read_text(encoding="utf-8"))
catalog=pd.read_csv(V85/"FROZEN_ELIGIBLE_FEATURES.csv").reset_index(drop=True)
pairs=pd.read_parquet(V85/"FROZEN_PAIR_UNIVERSE.parquet")
state_meta=json.loads((V85/"STATE_CACHE_META.json").read_text(encoding="utf-8"))

V84C=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v84c"/design["source_v84c"]
r84=json.loads((V84C/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V83B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v83b"/r84["source_v83b"]
manifest=json.loads((V83B/"REPAIRED_ARCHITECTURE_MANIFEST.json").read_text(encoding="utf-8"))

nt=int(design["targets"])
singletons=int(design["singleton_slots"])
total_slots=int(design["predeclared_trial_slots"])
pair_i=pairs["feature_i"].to_numpy(dtype=np.int64)
pair_j=pairs["feature_j"].to_numpy(dtype=np.int64)
train_shape=tuple(state_meta["train_shape"]); hold_shape=tuple(state_meta["hold_shape"])
ST=np.memmap(V85/"STATE_TRAIN.bool.dat",mode="r",dtype=np.bool_,shape=train_shape)
SH=np.memmap(V85/"STATE_HOLD.bool.dat",mode="r",dtype=np.bool_,shape=hold_shape)

# Reuse/resume run if interrupted.
current_path=BASE/"CURRENT_RUN.json"
if current_path.exists():
    current=json.loads(current_path.read_text(encoding="utf-8"))
    same=current.get("engine_version")==ENGINE_VERSION and current.get("source_v86")==V86.name and current.get("source_v85")==V85.name
    if same and current.get("status")=="RUNNING":
        OUT=BASE/current["run_id"]; RID=current["run_id"]
    elif same and current.get("status")=="COMPLETE":
        OUT=BASE/current["run_id"]
        print("=== GEF92 ALREADY COMPLETE ===")
        print((OUT/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
        raise SystemExit(0)
    else:
        RID="GEF92-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
        OUT=BASE/RID; OUT.mkdir(parents=True,exist_ok=False)
        write_json(current_path,{"engine_version":ENGINE_VERSION,"source_v86":V86.name,"source_v85":V85.name,"run_id":RID,"status":"RUNNING"})
else:
    RID="GEF92-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    OUT=BASE/RID; OUT.mkdir(parents=True,exist_ok=False)
    write_json(current_path,{"engine_version":ENGINE_VERSION,"source_v86":V86.name,"source_v85":V85.name,"run_id":RID,"status":"RUNNING"})

status(OUT,"1/12","lineage loaded; CLEAN OOS rule active; 2023+ unopened",
       source_v85=V85.name,source_v86=V86.name,contaminated_markets=sorted(CONTAMINATED_OOS_MARKETS))

# ---------- TRAIN ONLY target matrix ----------
target_path=Path(manifest["targets_5m_path"])
Ytr=pd.read_parquet(target_path,filters=[("decision_time_utc","<",datetime(2013,1,1))])
Ytr.index=pd.to_datetime(Ytr.index)
targets=[c for c in Ytr.columns if "_fwd_" in str(c)]
if len(targets)!=nt:
    raise RuntimeError(f"Target count mismatch {len(targets)} != {nt}")
YT=np.array(Ytr[targets],dtype=np.float32,copy=True)
train_times=Ytr.index
minute=(train_times.view("int64")//60_000_000_000).astype(np.int64)
horizons=[]
for ti,c in enumerate(targets):
    h=int(str(c).rsplit("_fwd_",1)[1].rstrip("m")); horizons.append(h)
    YT[(minute%h)!=0,ti]=np.nan
if YT.shape[0]!=train_shape[2]:
    raise RuntimeError("Train target/state row mismatch")

p85=np.memmap(V85/"TRAIN_PVALUES.float32.dat",mode="r",dtype=np.float32,shape=(total_slots,))
p86=np.memmap(V86/"TRAIN_BLOCK_PVALUES.float32.dat",mode="r",dtype=np.float32,shape=(total_slots,))

pool_path=OUT/"FROZEN_CLEAN_TRAIN_POOL.csv"
freeze_path=OUT/"V92_CLEAN_POOL_FREEZE.json"

if pool_path.exists() and freeze_path.exists():
    pool=pd.read_csv(pool_path)
    freeze=json.loads(freeze_path.read_text(encoding="utf-8"))
    if sha256(pool_path)!=freeze["pool_sha256"]:
        raise RuntimeError("Existing V92 frozen pool hash mismatch")
    status(OUT,"2/12","reused frozen TRAIN-only candidate pool",candidates=len(pool))
else:
    tpool=time.time()
    candidate_map={}

    def collect_from_ledger(name,pmap):
        top_i,top_p=top_global_indices(pmap,TOP_RAW_SCAN_PER_LEDGER)
        accepted=0
        ledger_seen=set()
        for global_rank,(trial,pv) in enumerate(zip(top_i,top_p),1):
            d=decode_trial(int(trial),singletons,nt,pair_i,pair_j)
            if d["kind"]!="pair":
                continue
            fi,fj,ti=d["fi"],d["fj"],d["ti"]
            ci=catalog.iloc[fi]; cj=catalog.iloc[fj]
            if str(ci["layer"])!="fast" or str(cj["layer"])!="fast":
                continue
            feat_i=str(ci["feature"]); feat_j=str(cj["feature"])
            if not supported_fast(feat_i) or not supported_fast(feat_j):
                continue
            mi=feature_market(feat_i); mj=feature_market(feat_j); mt=target_market(targets[ti])
            if mi in CONTAMINATED_OOS_MARKETS or mj in CONTAMINATED_OOS_MARKETS or mt in CONTAMINATED_OOS_MARKETS:
                continue
            mask=ST[fi,d["si"],:]&ST[fj,d["sj"],:]
            yy=YT[:,ti]
            vals=yy[mask]
            vals=vals[np.isfinite(vals)]
            if len(vals)<120:
                continue
            raw_mean=float(vals.mean())
            if not np.isfinite(raw_mean) or raw_mean==0:
                continue
            direction=1 if raw_mean>0 else -1
            keyhash=hashlib.blake2b(
                np.packbits(mask).tobytes()+str(targets[ti]).encode()+str(direction).encode(),
                digest_size=16
            ).hexdigest()
            if keyhash in ledger_seen:
                continue
            ledger_seen.add(keyhash)
            row=candidate_map.get(keyhash)
            if row is None:
                row={
                    "condition_hash":keyhash,
                    "trial_index":int(trial),
                    "feature_i_index":fi,"feature_i":feat_i,"family_i":str(ci["family"]),"state_i":("LO","HI")[d["si"]],
                    "feature_j_index":fj,"feature_j":feat_j,"family_j":str(cj["family"]),"state_j":("LO","HI")[d["sj"]],
                    "target_i":ti,"target":str(targets[ti]),"horizon_min":horizons[ti],
                    "direction":"LONG" if direction>0 else "SHORT","direction_sign":direction,
                    "train_n":int(len(vals)),"train_mean_bp":float(direction*raw_mean*1e4),
                    "train_net1bp_mean_bp":float(direction*raw_mean*1e4-GENERIC_COST_BP),
                    "v85_rank":np.nan,"v85_p_two":np.nan,"v86_rank":np.nan,"v86_p_two":np.nan,
                }
                candidate_map[keyhash]=row
            # The exact same mask+target can be represented by aliases. Keep best rank/p per ledger.
            if name=="V85":
                if not np.isfinite(row["v85_rank"]) or global_rank<row["v85_rank"]:
                    row["v85_rank"]=int(global_rank); row["v85_p_two"]=float(pv)
            else:
                if not np.isfinite(row["v86_rank"]) or global_rank<row["v86_rank"]:
                    row["v86_rank"]=int(global_rank); row["v86_p_two"]=float(pv)
            accepted+=1
            if accepted>=TOP_CLEAN_UNIQUE_PER_LEDGER:
                break
        return accepted,len(top_i)

    a85,n85=collect_from_ledger("V85",p85)
    status(OUT,"2/12","V85 train ledger mined without global-BH guillotine",accepted=a85,scanned_top=n85)
    a86,n86=collect_from_ledger("V86",p86)
    status(OUT,"2/12","V86 train ledger mined as ranking only",accepted=a86,scanned_top=n86)

    pool=pd.DataFrame(candidate_map.values())
    if pool.empty:
        raise RuntimeError("No clean fast pair candidate found in train ledgers")
    pool["best_train_rank"]=pool[["v85_rank","v86_rank"]].min(axis=1,skipna=True)
    pool["ledger_count"]=pool[["v85_rank","v86_rank"]].notna().sum(axis=1)
    pool=pool.sort_values(["best_train_rank","train_net1bp_mean_bp"],ascending=[True,False],kind="mergesort").reset_index(drop=True)
    pool["pool_rank"]=np.arange(1,len(pool)+1)
    pool.to_csv(pool_path,index=False)
    freeze={
        "run_id":RID,
        "status":"V92_CLEAN_TRAIN_POOL_FROZEN_BEFORE_2013_2022_EVALUATION",
        "source_v85":V85.name,
        "source_v86":V86.name,
        "train_window":"2010-2012 only",
        "contaminated_oos_markets_excluded":sorted(CONTAMINATED_OOS_MARKETS),
        "allowed_candidate_kind":"cross-family pair only",
        "allowed_feature_layer":"fast price features only",
        "top_clean_unique_per_ledger":TOP_CLEAN_UNIQUE_PER_LEDGER,
        "top_raw_scan_per_ledger":TOP_RAW_SCAN_PER_LEDGER,
        "union_candidates":len(pool),
        "selection_rule":SELECTION_RULE,
        "pool_sha256":sha256(pool_path),
        "2013_2022_values_accessed_at_freeze":False,
        "2023_plus_accessed":False,
        "protected_2026_accessed":False,
    }
    write_json(freeze_path,freeze)
    status(OUT,"2/12","TRAIN-only clean candidate union physically frozen",
           candidates=len(pool),elapsed_s=round(time.time()-tpool,1),pool_sha256=freeze["pool_sha256"][:16])

# ---------- 2013 temporal screen ----------
Fhist=pd.read_parquet(manifest["price_state_5m_path"])
Fhist.index=pd.to_datetime(Fhist.index)
hold_times=Fhist.index[Fhist.index.year==2013]
if len(hold_times)!=hold_shape[2]:
    raise RuntimeError("2013 state/time row mismatch")
Yh=pd.read_parquet(target_path,filters=[("decision_time_utc",">=",datetime(2013,1,1)),("decision_time_utc","<",datetime(2014,1,1))])
Yh.index=pd.to_datetime(Yh.index); Yh=Yh.reindex(hold_times)
YH=np.array(Yh[targets],dtype=np.float32,copy=True)
hm=(hold_times.view("int64")//60_000_000_000).astype(np.int64)
for ti,h in enumerate(horizons):
    YH[(hm%h)!=0,ti]=np.nan

hold_rows=[]
for k,r in enumerate(pool.itertuples(index=False),1):
    mask=SH[int(r.feature_i_index),0 if r.state_i=="LO" else 1,:]&SH[int(r.feature_j_index),0 if r.state_j=="LO" else 1,:]
    ret=float(r.direction_sign)*YH[:,int(r.target_i)]
    m=metrics(np.where(mask,ret,np.nan))
    hold_rows.append({"condition_hash":r.condition_hash,"hold2013_n":m["n"],"hold2013_mean_bp":m["mean_bp"],
                      "hold2013_net1bp_mean_bp":m["net1bp_mean_bp"],"hold2013_win_rate_pct":m["win_rate_pct"]})
H=pd.DataFrame(hold_rows)
pool=pool.merge(H,on="condition_hash",how="left",validate="one_to_one")
status(OUT,"3/12","2013 temporal behavior measured for frozen pool",positive=int((pool["hold2013_mean_bp"]>0).sum()),candidates=len(pool))

# ---------- build 2014-2022 CLEAN market continuation ----------
needed_features=sorted(set(pool["feature_i"]).union(set(pool["feature_j"])))
needed_targets=sorted(set(pool["target"]))
needed_markets=set()
for f in needed_features:
    m=feature_market(f)
    if m: needed_markets.add(m)
for t in needed_targets:
    needed_markets.add(target_market(t))
if CONTAMINATED_OOS_MARKETS & needed_markets:
    raise RuntimeError(f"Clean-pool contamination leak: {sorted(CONTAMINATED_OOS_MARKETS & needed_markets)}")

# Existence check only for development files <=2022.
missing=[]
for sym in sorted(needed_markets):
    for y in range(2013,2023):
        p=ROOT/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
        if not p.exists(): missing.append(str(p))
if missing:
    raise RuntimeError(f"Missing V92 development files: {missing}")
status(OUT,"4/12","clean development source presence confirmed",markets=len(needed_markets),features=len(needed_features),targets=len(needed_targets))

warm_grid=pd.date_range("2013-12-01 00:00",EXT_END,freq="5min")
ext_grid=pd.date_range(E2_START,EXT_END,freq="5min")
P=pd.DataFrame(index=warm_grid)
tprices=time.time()
for i,sym in enumerate(sorted(needed_markets),1):
    raw=load_m1(sym,range(2013,2023))
    P[sym]=raw.resample("5min",label="right",closed="left").last().reindex(warm_grid).astype("float64")
    elapsed=time.time()-tprices
    rate=i/max(elapsed,1e-9); eta=(len(needed_markets)-i)/max(rate,1e-9)
    print(f"[GEF92] prices {i}/{len(needed_markets)} {sym} | elapsed={elapsed/60:.1f}m eta={eta/60:.1f}m",flush=True)
status(OUT,"5/12","2014-2022 clean price continuation materialized",rows=len(ext_grid),markets=len(needed_markets))

# ---------- exact state extension with per-feature cache/resume ----------
cache_dir=OUT/"state_cache"; cache_dir.mkdir(parents=True,exist_ok=True)
state_ext={}
feature_index={str(row["feature"]):i for i,row in catalog.iterrows()}
tstates=time.time()
last_print=tstates
for i,feat in enumerate(needed_features,1):
    fi=feature_index[feat]
    lo_path=cache_dir/f"{fi:04d}_LO.npy"; hi_path=cache_dir/f"{fi:04d}_HI.npy"
    if lo_path.exists() and hi_path.exists():
        loe=np.load(lo_path,mmap_mode="r"); hie=np.load(hi_path,mmap_mode="r")
        if len(loe)!=len(ext_grid) or len(hie)!=len(ext_grid):
            raise RuntimeError(f"Cached state length mismatch {feat}")
    else:
        ext=build_fast_feature(feat,P).reindex(ext_grid)
        full=pd.concat([pd.to_numeric(Fhist[feat],errors="coerce"),pd.to_numeric(ext,errors="coerce")])
        lo,hi=causal_states(full,MIN_FAST_STATE)
        hist_rows=len(Fhist)
        expected_lo=np.concatenate([ST[fi,0,:],SH[fi,0,:]])
        expected_hi=np.concatenate([ST[fi,1,:],SH[fi,1,:]])
        ml=int(np.count_nonzero(lo[:hist_rows]!=expected_lo))
        mh=int(np.count_nonzero(hi[:hist_rows]!=expected_hi))
        if ml or mh:
            raise RuntimeError(f"State parity failed {feat}: LO={ml} HI={mh}")
        loe=np.array(lo[hist_rows:],dtype=np.bool_,copy=True)
        hie=np.array(hi[hist_rows:],dtype=np.bool_,copy=True)
        np.save(lo_path,loe,allow_pickle=False); np.save(hi_path,hie,allow_pickle=False)
        loe=np.load(lo_path,mmap_mode="r"); hie=np.load(hi_path,mmap_mode="r")
    state_ext[(feat,"LO")]=loe; state_ext[(feat,"HI")]=hie
    now=time.time()
    if i==1 or i==len(needed_features) or i%10==0 or now-last_print>=STATUS_SECONDS:
        elapsed=now-tstates; rate=i/max(elapsed,1e-9); eta=(len(needed_features)-i)/max(rate,1e-9)
        status(OUT,"6/12",f"state extension {i}/{len(needed_features)}",percent=round(100*i/len(needed_features),1),
               elapsed_min=round(elapsed/60,1),eta_min=round(eta/60,1))
        last_print=now

# ---------- evaluate 2014-2022 by target group ----------
rows=[]
teval=time.time()
processed=0
total=len(pool)
for target,grp in pool.groupby("target",sort=False):
    raw_target=target_array_from_prices(P,ext_grid,target)
    for r in grp.itertuples(index=False):
        mask=np.asarray(state_ext[(r.feature_i,r.state_i)]) & np.asarray(state_ext[(r.feature_j,r.state_j)])
        ret=float(r.direction_sign)*raw_target
        horizon=pd.Timedelta(minutes=int(r.horizon_min))
        e2_sel=np.asarray((ext_grid>=E2_START)&(ext_grid<=E2_END)&((ext_grid+horizon)<=E2_END))
        e3_sel=np.asarray((ext_grid>=E3_START)&(ext_grid<=E3_END)&((ext_grid+horizon)<=E3_END))
        e2=metrics(np.where(mask&e2_sel,ret,np.nan))
        e3=metrics(np.where(mask&e3_sel,ret,np.nan))

        yearly={}
        posyears=0
        for year in range(2014,2023):
            ys=np.asarray(ext_grid.year==year)
            ym=metrics(np.where(mask&ys,ret,np.nan))
            yearly[f"y{year}_n"]=ym["n"]
            yearly[f"y{year}_mean_bp"]=ym["mean_bp"]
            if np.isfinite(ym["mean_bp"]) and ym["mean_bp"]>0:
                posyears+=1

        # Combine all development pieces using sums/n, preserving the train-chosen direction.
        train_sum=(float(r.train_mean_bp)/1e4)*int(r.train_n)
        hold_sum=(float(r.hold2013_mean_bp)/1e4)*int(r.hold2013_n) if np.isfinite(r.hold2013_mean_bp) else 0.0
        total_n=int(r.train_n)+int(r.hold2013_n)+e2["n"]+e3["n"]
        total_sum=train_sum+hold_sum+e2["sum_return"]+e3["sum_return"]
        full_mean_bp=(total_sum/total_n*1e4) if total_n else np.nan
        full_net1=full_mean_bp-GENERIC_COST_BP if np.isfinite(full_mean_bp) else np.nan

        major=[float(r.train_net1bp_mean_bp),e2["net1bp_mean_bp"],e3["net1bp_mean_bp"]]
        major_pos=int(sum(np.isfinite(x) and x>0 for x in major))
        worst=float(np.nanmin(np.asarray(major,dtype=float))) if np.isfinite(np.asarray(major,dtype=float)).any() else np.nan

        rec={
            "condition_hash":r.condition_hash,
            "e2_2014_2017_n":e2["n"],"e2_2014_2017_mean_bp":e2["mean_bp"],"e2_2014_2017_net1bp_mean_bp":e2["net1bp_mean_bp"],
            "e3_2018_2022_n":e3["n"],"e3_2018_2022_mean_bp":e3["mean_bp"],"e3_2018_2022_net1bp_mean_bp":e3["net1bp_mean_bp"],
            "positive_years_2014_2022":posyears,
            "major_net1bp_positive_count":major_pos,
            "worst_major_net1bp_mean_bp":worst,
            "full_2010_2022_n":total_n,"full_2010_2022_mean_bp":full_mean_bp,"full_2010_2022_net1bp_mean_bp":full_net1,
            **yearly
        }
        rec["qualified_for_clean_oos"]=bool(
            int(r.hold2013_n)>=SELECTION_RULE["holdout_2013_min_n"]
            and np.isfinite(r.hold2013_mean_bp) and float(r.hold2013_mean_bp)>0
            and e2["n"]>=SELECTION_RULE["2014_2017_min_n"]
            and e3["n"]>=SELECTION_RULE["2018_2022_min_n"]
            and np.isfinite(e3["net1bp_mean_bp"]) and e3["net1bp_mean_bp"]>0
            and major_pos>=SELECTION_RULE["major_eras_with_positive_net1bp_min"]
            and posyears>=SELECTION_RULE["positive_years_2014_2022_min"]
            and np.isfinite(full_net1) and full_net1>0
        )
        rows.append(rec)
        processed+=1
        if processed==1 or processed==total or processed%100==0:
            elapsed=time.time()-teval; rate=processed/max(elapsed,1e-9); eta=(total-processed)/max(rate,1e-9)
            status(OUT,"7/12",f"development evaluation {processed}/{total}",percent=round(100*processed/total,1),
                   elapsed_min=round(elapsed/60,1),eta_min=round(eta/60,1))

E=pd.DataFrame(rows)
R=pool.merge(E,on="condition_hash",how="left",validate="one_to_one")

R=R.sort_values(
    ["qualified_for_clean_oos","major_net1bp_positive_count","worst_major_net1bp_mean_bp",
     "positive_years_2014_2022","e3_2018_2022_net1bp_mean_bp","full_2010_2022_net1bp_mean_bp","best_train_rank"],
    ascending=[False,False,False,False,False,False,True],
    kind="mergesort"
).reset_index(drop=True)
R["development_rank"]=np.arange(1,len(R)+1)
R.to_csv(OUT/"V92_CLEAN_DEVELOPMENT_ALL.csv",index=False)
qualified=R[R["qualified_for_clean_oos"]].copy()
panel=qualified.head(FINAL_PANEL_MAX).copy()
panel.to_csv(OUT/"FROZEN_CLEAN_OOS_PANEL.csv",index=False)

status(OUT,"8/12","temporal ladder complete; no p-value guillotine used",
       pool=len(R),qualified=len(qualified),frozen_panel=len(panel))

# ---------- freeze final CLEAN OOS panel before any 2023 value access ----------
if len(panel):
    oos_markets=set()
    for r in panel.itertuples(index=False):
        oos_markets.add(target_market(r.target))
        oos_markets.add(feature_market(r.feature_i))
        oos_markets.add(feature_market(r.feature_j))
    oos_markets.discard(None)
    if CONTAMINATED_OOS_MARKETS & oos_markets:
        raise RuntimeError("Frozen clean OOS panel unexpectedly contaminated")
    panel_sha=sha256(OUT/"FROZEN_CLEAN_OOS_PANEL.csv")
    final_freeze={
        "run_id":RID,
        "status":"V92_CLEAN_OOS_PANEL_FROZEN_BEFORE_2023_ACCESS",
        "source_v85":V85.name,"source_v86":V86.name,
        "panel_size":len(panel),"panel_sha256":panel_sha,
        "selection_rule":SELECTION_RULE,
        "oos_window":"2023-2025 locked",
        "oos_markets":sorted(oos_markets),
        "contaminated_markets_excluded":sorted(CONTAMINATED_OOS_MARKETS),
        "2023_plus_values_accessed":False,
        "protected_2026_accessed":False,
    }
    write_json(OUT/"FINAL_OOS_FREEZE.json",final_freeze)
    status(OUT,"9/12","clean final panel physically frozen before 2023",panel=len(panel),panel_sha256=panel_sha[:16],markets=len(oos_markets))

    # Presence only: do not read any value.
    missing_oos=[]
    for sym in sorted(oos_markets):
        for y in range(2023,2026):
            p=ROOT/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
            if not p.exists(): missing_oos.append(str(p))
    next_step="V93_MATERIALIZE_MISSING_THEN_LOCKED_OOS_2023_2025" if missing_oos else "V93_LOCKED_OOS_2023_2025"
    write_json(OUT/"OOS_FILE_PRESENCE.json",{"markets":sorted(oos_markets),"missing_files":missing_oos,"values_accessed":False})
    status(OUT,"10/12","2023-2025 file presence checked without reading values",missing_files=len(missing_oos),next=next_step)
else:
    panel_sha=None; missing_oos=[]; next_step="STOP_NO_CLEAN_HYPOTHESIS_MET_PREDECLARED_TEMPORAL_RULE"
    status(OUT,"9/12","no clean candidate met frozen temporal/economic rule; no OOS opened")
    status(OUT,"10/12","2023-2025 remains unopened",next=next_step)

receipt={
    "run_id":RID,
    "status":"COMPLETE_V92_CLEAN_TEMPORAL_LADDER",
    "engine_version":ENGINE_VERSION,
    "source_v85":V85.name,"source_v86":V86.name,
    "train_pool_candidates":len(pool),
    "qualified_clean_candidates":len(qualified),
    "frozen_clean_oos_panel":len(panel),
    "panel_sha256":panel_sha,
    "contaminated_oos_markets_excluded":sorted(CONTAMINATED_OOS_MARKETS),
    "global_pvalue_guillotine_used":False,
    "generic_cost_bp_for_selection":GENERIC_COST_BP,
    "missing_oos_files":len(missing_oos),
    "2013_2022_accessed_for_development":True,
    "2023_plus_values_accessed":False,
    "protected_2026_accessed":False,
    "next":next_step,
}
write_json(OUT/"RUN_RECEIPT.json",receipt)
current=json.loads(current_path.read_text(encoding="utf-8")); current["status"]="COMPLETE"; write_json(current_path,current)
status(OUT,"11/12","receipt written",qualified=len(qualified),panel=len(panel),next=next_step)
status(OUT,"12/12","DONE; 2023-2025 clean OOS values remain unopened")

print("\n=== V92 RECEIPT ===")
print(json.dumps(receipt,indent=2))
print("\n=== V92 FROZEN CLEAN OOS PANEL ===")
if len(panel):
    cols=[
        "development_rank","trial_index","family_i","state_i","family_j","state_j","target","direction",
        "train_n","train_mean_bp","hold2013_n","hold2013_mean_bp",
        "e2_2014_2017_n","e2_2014_2017_mean_bp","e2_2014_2017_net1bp_mean_bp",
        "e3_2018_2022_n","e3_2018_2022_mean_bp","e3_2018_2022_net1bp_mean_bp",
        "positive_years_2014_2022","major_net1bp_positive_count","worst_major_net1bp_mean_bp",
        "full_2010_2022_net1bp_mean_bp","best_train_rank","ledger_count"
    ]
    print(panel[cols].to_string(index=False))
else:
    print("NONE")
print("\nRUN:",OUT)
