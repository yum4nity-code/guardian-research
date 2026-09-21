from pathlib import Path
import pandas as pd
import numpy as np
import json
import time
import math
import hashlib
import re
import xml.etree.ElementTree as ET
from scipy.stats import t as student_t

ROOT = Path(r"D:\MT5_Backtests")
BASE = ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v88_replication"
BASE.mkdir(parents=True, exist_ok=True)

ENGINE_VERSION = "V88.0"
START = pd.Timestamp("2014-01-01 00:00")
END = pd.Timestamp("2017-12-31 23:55")
MARKETS = ["XAUUSD","XAGUSD","UDXUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","SPXUSD","NSXUSD","WTIUSD","BCOUSD"]
COST_BPS = (0.25,0.5,1.0,2.0,5.0)
MIN_FAST_STATE = 5000
MIN_SLOW_STATE = 500
MIN_CLUSTER_BLOCKS = 8

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def status(out,step,total,msg,**extra):
    payload={"engine_version":ENGINE_VERSION,"step":step,"steps":total,
             "percent":round(100*step/total,1),"timestamp_utc":pd.Timestamp.now("UTC").isoformat(),
             "message":msg,**extra}
    write_json(out/"LIVE_STATUS.json",payload)
    tail=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF88] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def as_bool(s):
    if pd.api.types.is_bool_dtype(s):
        return s.fillna(False)
    return s.astype(str).str.strip().str.lower().eq("true")

def causal_states(s,min_periods):
    s=pd.to_numeric(s,errors="coerce")
    mu=s.expanding(min_periods=min_periods).mean().shift(1)
    sd=s.expanding(min_periods=min_periods).std().shift(1).replace(0,np.nan)
    z=((s-mu)/sd).to_numpy(dtype=np.float32)
    finite=np.isfinite(z)
    return finite&(z<=-1.0), finite&(z>=1.0)

def parse_treasury(folder,prefix,end_year):
    rows=[]
    for y in range(2009,end_year+1):
        p=ROOT/"DataLake"/"raw"/"treasury"/folder/f"{folder}_{y}.xml"
        if not p.exists():
            raise RuntimeError(f"Missing Treasury source: {p}")
        root=ET.parse(p).getroot()
        for entry in root.iter():
            vals={}
            for x in entry.iter():
                tag=x.tag.split("}")[-1]
                txt=(x.text or "").strip()
                if txt and (tag.startswith("NEW_DATE") or tag.startswith("BC_") or tag.startswith("TC_") or tag=="NEW_DATE"):
                    vals[tag]=txt
            if vals:
                rows.append(vals)
    d=pd.DataFrame(rows).drop_duplicates()
    dc=next((c for c in d.columns if "DATE" in c),None)
    if dc is None:
        raise RuntimeError(f"No date field in Treasury {folder}")
    d["obs_date"]=pd.to_datetime(d[dc],errors="coerce").dt.normalize()
    d=d.dropna(subset=["obs_date"]).sort_values("obs_date").drop_duplicates("obs_date",keep="last")
    out=pd.DataFrame(index=d["obs_date"])
    for c in d.columns:
        if c in {dc,"obs_date"}:
            continue
        v=pd.to_numeric(d[c],errors="coerce")
        if v.notna().sum()>=250:
            out[f"{prefix}_{c}"]=v.to_numpy()
    return out

def featurewise_asof(grid,source,features):
    base=pd.DataFrame({"decision_time_utc":grid})
    out=pd.DataFrame(index=grid)
    for feat in features:
        raw=feat.removeprefix("rates_yields_").removesuffix("_level")
        if raw not in source.columns:
            raise RuntimeError(f"Rate source column missing for {feat}: {raw}")
        src=pd.DataFrame({
            "AVAILABLE_AT":pd.DatetimeIndex(source.index)+pd.Timedelta(days=1),
            feat:pd.to_numeric(source[raw],errors="coerce")
        }).dropna(subset=["AVAILABLE_AT",feat]).sort_values("AVAILABLE_AT").drop_duplicates("AVAILABLE_AT",keep="last")
        z=pd.merge_asof(base,src,left_on="decision_time_utc",right_on="AVAILABLE_AT",direction="backward")
        out[feat]=z[feat].to_numpy()
    return out

def load_m1(sym,years):
    parts=[]
    for y in years:
        p=ROOT/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
        if not p.exists():
            raise RuntimeError(f"Missing HistData file: {p}")
        d=pd.read_parquet(p)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        pc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None and isinstance(d.index,pd.DatetimeIndex):
            d=d.reset_index()
            dc=d.columns[0]
        if dc is None or pc is None:
            raise RuntimeError(f"Cannot identify datetime/close in {p}")
        utc=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(hours=5)
        q=pd.DataFrame({"utc":utc,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
        parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    return q.set_index("utc")["px"]

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

def block_ids(times,days,origin):
    return ((times.normalize()-origin).days.to_numpy()//int(days)).astype(np.int16)

def cluster_positive(returns,blocks):
    r=np.asarray(returns,dtype=np.float64)
    b=np.asarray(blocks)
    finite=np.isfinite(r)
    r=r[finite]; b=b[finite]
    n=len(r)
    if n==0:
        return {"n":0,"blocks":0,"mean":np.nan,"p_one":np.nan}
    mean=float(r.mean())
    starts=np.r_[0,np.flatnonzero(b[1:]!=b[:-1])+1]
    g=len(starts)
    if g<MIN_CLUSTER_BLOCKS:
        return {"n":n,"blocks":g,"mean":mean,"p_one":np.nan}
    sums=np.add.reduceat(r,starts)
    counts=np.diff(np.r_[starts,n]).astype(np.float64)
    u=sums-counts*mean
    meat=float(np.sum(u*u))
    if not np.isfinite(meat) or meat<=0:
        return {"n":n,"blocks":g,"mean":mean,"p_one":np.nan}
    se2=(g/(g-1.0))*meat/(n*n)
    if not np.isfinite(se2) or se2<=0:
        return {"n":n,"blocks":g,"mean":mean,"p_one":np.nan}
    stat=mean/math.sqrt(se2)
    return {"n":n,"blocks":g,"mean":mean,"p_one":float(student_t.sf(stat,df=g-1))}

def max_drawdown_pct(r):
    x=np.asarray(r,dtype=np.float64)
    x=x[np.isfinite(x)]
    if len(x)==0 or np.any(x<=-1):
        return np.nan
    eq=np.cumprod(1+x)
    peak=np.maximum.accumulate(eq)
    return float(np.min(eq/peak-1)*100.0)

def metrics(r):
    x=np.asarray(r,dtype=np.float64)
    x=x[np.isfinite(x)]
    out={"n":len(x),"mean_bp":np.nan,"median_bp":np.nan,"win_rate_pct":np.nan,
         "gross_sum_pct":np.nan,"max_drawdown_pct":np.nan}
    if len(x):
        out.update({
            "mean_bp":float(x.mean()*1e4),
            "median_bp":float(np.median(x)*1e4),
            "win_rate_pct":float((x>0).mean()*100.0),
            "gross_sum_pct":float(x.sum()*100.0),
            "max_drawdown_pct":max_drawdown_pct(x),
        })
    for c in COST_BPS:
        tag=str(c).replace(".","p")
        if len(x):
            net=x-c*1e-4
            out[f"net_{tag}bp_mean_bp"]=float(net.mean()*1e4)
            out[f"net_{tag}bp_sum_pct"]=float(net.sum()*100.0)
            out[f"net_{tag}bp_pnl_10k"]=float(net.sum()*10000.0)
            out[f"net_{tag}bp_pnl_100k"]=float(net.sum()*100000.0)
        else:
            out[f"net_{tag}bp_mean_bp"]=np.nan
            out[f"net_{tag}bp_sum_pct"]=np.nan
            out[f"net_{tag}bp_pnl_10k"]=np.nan
            out[f"net_{tag}bp_pnl_100k"]=np.nan
    return out

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

def holm_adjust(p):
    p=np.asarray(p,dtype=np.float64)
    out=np.full(len(p),np.nan)
    idx=np.flatnonzero(np.isfinite(p))
    if not len(idx):
        return out
    vals=p[idx]; order=np.argsort(vals); ranked=vals[order]
    adj=np.maximum.accumulate(ranked*np.arange(len(ranked),0,-1,dtype=np.float64))
    adj=np.clip(adj,0,1)
    out[idx[order]]=adj
    return out

# deterministic self-test
_tm=metrics(np.array([0.01,-0.005,0.02]))
assert _tm["n"]==3 and _tm["mean_bp"]>0
assert np.isclose(_tm["net_1p0bp_mean_bp"],_tm["mean_bp"]-1.0)

# ---------- load frozen V88 preflight ----------
preflights=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v88").glob("GEF88-*"))
preflights=[p for p in preflights if (p/"RUN_RECEIPT.json").exists() and (p/"FROZEN_2014_2017_REPLICATION_PANEL.csv").exists()]
if not preflights:
    raise RuntimeError("No completed V88 preflight")
PF=preflights[-1]
rpf=json.loads((PF/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if rpf.get("status")!="COMPLETE_REPLICATION_FREEZE_PREFLIGHT":
    raise RuntimeError(f"V88 preflight status is {rpf.get('status')}")
if rpf.get("2014_2017_values_accessed"):
    raise RuntimeError("Preflight already claims 2014-2017 value access")

FROZEN=pd.read_csv(PF/"FROZEN_2014_2017_REPLICATION_PANEL.csv")
if len(FROZEN)!=int(rpf["frozen_candidates"]):
    raise RuntimeError("Frozen panel count mismatch")
if sha256(PF/"FROZEN_2014_2017_REPLICATION_PANEL.csv")!=rpf["frozen_panel_sha256"]:
    raise RuntimeError("Frozen panel hash mismatch")

RID="GEF88R-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID
OUT.mkdir(parents=True,exist_ok=False)
t0=time.time()
status(OUT,1,12,"frozen replication panel loaded; opening no later window yet", candidates=len(FROZEN), source_preflight=PF.name)

# ---------- resolve immutable architecture ----------
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

S_hist=pd.read_parquet(manifest["slow_state_repaired_path"])
F_hist=pd.read_parquet(manifest["price_state_5m_path"])
S_hist.index=pd.to_datetime(S_hist.index)
F_hist.index=pd.to_datetime(F_hist.index)
bridge_hist=np.load(manifest["bridge_path"])

train_shape=tuple(state_meta["train_shape"])
hold_shape=tuple(state_meta["hold_shape"])
ST=np.memmap(V85/"STATE_TRAIN.bool.dat",mode="r",dtype=np.bool_,shape=train_shape)
SH=np.memmap(V85/"STATE_HOLD.bool.dat",mode="r",dtype=np.bool_,shape=hold_shape)
hist_rows=len(F_hist)
if train_shape[2]+hold_shape[2]!=hist_rows:
    raise RuntimeError("Historical state cache rows do not match archived F")
status(OUT,2,12,"immutable 2010-2013 architecture loaded", fast_hist_rows=hist_rows, slow_hist_rows=len(S_hist))

# ---------- build 2014-2017 prices with 2013 warmup ----------
needed_markets=sorted(set(rpf["needed_markets"]))
warm_grid=pd.date_range("2013-12-01 00:00",END,freq="5min")
ext_grid=pd.date_range(START,END,freq="5min")
P=pd.DataFrame(index=warm_grid)
for i,sym in enumerate(needed_markets,1):
    raw=load_m1(sym,range(2013,2018))
    five=raw.resample("5min",label="right",closed="left").last().reindex(warm_grid)
    P[sym]=five.astype("float64")
    print(f"[GEF88] price {i}/{len(needed_markets)} {sym} non_null={int(five.loc[ext_grid].notna().sum())}",flush=True)
status(OUT,3,12,"2014-2017 price grid materialized", markets=len(needed_markets), rows=len(ext_grid))

# ---------- reconstruct exact required fast features ----------
feature_rows=pd.concat([FROZEN[["feature_i","layer_i"]].rename(columns={"feature_i":"feature","layer_i":"layer"}),
                       FROZEN[["feature_j","layer_j"]].rename(columns={"feature_j":"feature","layer_j":"layer"})],ignore_index=True)
feature_rows=feature_rows.dropna().drop_duplicates("feature")
fast_features=sorted(feature_rows.loc[feature_rows["layer"]=="fast","feature"].astype(str))
slow_features=sorted(feature_rows.loc[feature_rows["layer"]=="slow","feature"].astype(str))

F_ext=pd.DataFrame(index=ext_grid)
for feat in fast_features:
    built=build_fast_feature(feat,P)
    F_ext[feat]=built.reindex(ext_grid)
status(OUT,4,12,"exact fast features reconstructed", fast_features=len(fast_features))

# ---------- extend exact slow rate levels on original cadence ----------
if len(S_hist.index)<2:
    raise RuntimeError("Historical slow matrix too short")
delta=S_hist.index.to_series().diff().dropna().mode()
if len(delta)==0:
    raise RuntimeError("Cannot infer slow-grid cadence")
slow_delta=delta.iloc[0]
slow_start=S_hist.index[-1]+slow_delta
slow_end=pd.Timestamp("2017-12-31 23:00")
slow_ext_grid=pd.date_range(slow_start,slow_end,freq=slow_delta)

S_ext=pd.DataFrame(index=slow_ext_grid)
if slow_features:
    if not all(str(x).startswith("rates_yields_") and str(x).endswith("_level") for x in slow_features):
        raise RuntimeError(f"V88 replication only preflighted exact rate levels; got {slow_features}")
    nom=parse_treasury("nominal_yield_curve","NOM",2017)
    S_ext=featurewise_asof(slow_ext_grid,nom,slow_features)
status(OUT,5,12,"slow rate levels extended causally", slow_features=len(slow_features), slow_rows=len(slow_ext_grid), cadence=str(slow_delta))

# ---------- reproduce frozen 2010-2013 states exactly, then extend ----------
state_ext={}
parity=[]
feature_index_map={}
for r in FROZEN.itertuples(index=False):
    feature_index_map[str(r.feature_i)]=int(r.feature_i_index)
    if not pd.isna(r.feature_j):
        feature_index_map[str(r.feature_j)]=int(r.feature_j_index)

hist_expected_lo_cache={}
hist_expected_hi_cache={}
for feat,fi in sorted(feature_index_map.items()):
    row=feature_rows.loc[feature_rows["feature"].astype(str)==feat].iloc[0]
    layer=str(row["layer"])
    if layer=="fast":
        if feat not in F_hist.columns:
            raise RuntimeError(f"Archived fast feature missing: {feat}")
        full=pd.concat([pd.to_numeric(F_hist[feat],errors="coerce"),pd.to_numeric(F_ext[feat],errors="coerce")])
        lo,hi=causal_states(full,MIN_FAST_STATE)
        hist_lo=lo[:hist_rows]; hist_hi=hi[:hist_rows]
        ext_lo=lo[hist_rows:]; ext_hi=hi[hist_rows:]
    elif layer=="slow":
        if feat not in S_hist.columns:
            raise RuntimeError(f"Archived slow feature missing: {feat}")
        full=pd.concat([pd.to_numeric(S_hist[feat],errors="coerce"),pd.to_numeric(S_ext[feat],errors="coerce")])
        slo,shi=causal_states(full,MIN_SLOW_STATE)
        okh=bridge_hist>=0
        hist_lo=np.zeros(hist_rows,dtype=bool); hist_hi=np.zeros(hist_rows,dtype=bool)
        hist_lo[okh]=slo[bridge_hist[okh]]; hist_hi[okh]=shi[bridge_hist[okh]]
        full_slow_idx=full.index.values.astype("datetime64[ns]")
        ext_idx=ext_grid.values.astype("datetime64[ns]")
        be=np.searchsorted(full_slow_idx,ext_idx,side="right")-1
        oke=be>=0
        ext_lo=np.zeros(len(ext_grid),dtype=bool); ext_hi=np.zeros(len(ext_grid),dtype=bool)
        ext_lo[oke]=slo[be[oke]]; ext_hi[oke]=shi[be[oke]]
    else:
        raise RuntimeError(f"Unsupported layer {layer} for {feat}")

    expected_lo=np.concatenate([ST[fi,0,:],SH[fi,0,:]])
    expected_hi=np.concatenate([ST[fi,1,:],SH[fi,1,:]])
    lo_mismatch=int(np.count_nonzero(hist_lo!=expected_lo))
    hi_mismatch=int(np.count_nonzero(hist_hi!=expected_hi))
    parity.append({"feature":feat,"layer":layer,"lo_mismatch":lo_mismatch,"hi_mismatch":hi_mismatch})
    if lo_mismatch or hi_mismatch:
        raise RuntimeError(f"State parity failed for {feat}: LO={lo_mismatch} HI={hi_mismatch}")
    state_ext[(fi,0)]=ext_lo
    state_ext[(fi,1)]=ext_hi

pd.DataFrame(parity).to_csv(OUT/"STATE_PARITY_2010_2013.csv",index=False)
status(OUT,6,12,"historical state reproduction passed exactly", features=len(parity), total_mismatches=0)

# ---------- build frozen targets; no 2018 prices used ----------
target_names=sorted(FROZEN["target"].astype(str).unique())
Y_ext=pd.DataFrame(index=ext_grid)
for target in target_names:
    sym,rest=target.split("_fwd_",1)
    mins=int(rest.rstrip("m"))
    k=mins//5
    y=P[sym].shift(-k)/P[sym]-1
    Y_ext[target]=y.reindex(ext_grid).astype("float32")
    minute=(ext_grid.view("int64")//60_000_000_000).astype(np.int64)
    Y_ext.loc[(minute%mins)!=0,target]=np.nan
status(OUT,7,12,"2014-2017 targets built with non-overlap grid", targets=len(target_names), accessed_2018=False)

# ---------- evaluate every frozen candidate, nobody deleted ----------
records=[]
for idx,r in enumerate(FROZEN.itertuples(index=False),1):
    fi=int(r.feature_i_index); si=0 if str(r.state_i)=="LO" else 1
    mask=state_ext[(fi,si)].copy()
    if not pd.isna(r.feature_j):
        fj=int(r.feature_j_index); sj=0 if str(r.state_j)=="LO" else 1
        mask &= state_ext[(fj,sj)]

    sign=1.0 if str(r.direction).upper()=="LONG" else -1.0
    ret=sign*Y_ext[str(r.target)].to_numpy(dtype=np.float64)
    ret=np.where(mask,ret,np.nan)

    m=metrics(ret)
    yearly={}
    pos_years=0
    for year in (2014,2015,2016,2017):
        sel=np.asarray(ext_grid.year==year)
        yy=ret[sel]; yy=yy[np.isfinite(yy)]
        mean_bp=float(yy.mean()*1e4) if len(yy) else np.nan
        yearly[f"y{year}_n"]=len(yy)
        yearly[f"y{year}_mean_bp"]=mean_bp
        yearly[f"y{year}_win_rate_pct"]=float((yy>0).mean()*100.0) if len(yy) else np.nan
        if np.isfinite(mean_bp) and mean_bp>0:
            pos_years+=1

    primary_days=int(r.primary_block_days)
    ct=cluster_positive(ret,block_ids(ext_grid,primary_days,pd.Timestamp("2014-01-01")))
    keyhash=hashlib.blake2b(np.packbits(mask).tobytes()+str(r.target).encode()+str(r.direction).encode(),digest_size=16).hexdigest()

    rec={
        "panel_rank":int(r.panel_rank),
        "raw_rank":int(r.raw_rank),
        "trial_index":int(r.trial_index),
        "feature_i":str(r.feature_i),"state_i":str(r.state_i),"family_i":str(r.family_i),
        "feature_j":None if pd.isna(r.feature_j) else str(r.feature_j),
        "state_j":None if pd.isna(r.state_j) else str(r.state_j),
        "family_j":None if pd.isna(r.family_j) else str(r.family_j),
        "target":str(r.target),"direction":str(r.direction),
        "train_mean_bp":float(r.train_mean_bp),
        "holdout_2013_mean_bp":float(r.holdout_2013_mean_bp),
        "primary_block_days":primary_days,
        "condition_hash":keyhash,
        "replication_p_one":ct["p_one"],
        "replication_blocks":ct["blocks"],
        "positive_years_2014_2017":pos_years,
        **m,**yearly,
    }
    records.append(rec)
    print(f"[GEF88] candidate {idx}/{len(FROZEN)} panel={r.panel_rank} target={r.target} n={m['n']} mean_bp={m['mean_bp']:.4f}",flush=True)

R=pd.DataFrame(records)
status(OUT,8,12,"all frozen candidates evaluated", candidates=len(R), positive_mean=int((R["mean_bp"]>0).sum()), net1bp_positive=int((R["net_1p0bp_mean_bp"]>0).sum()))

# ---------- deduplicate only for multiplicity accounting; retain all rows ----------
groups=R.groupby("condition_hash",sort=False)
U=groups.first().reset_index()
U["aliases"]=groups.size().reindex(U["condition_hash"]).to_numpy()
p=U["replication_p_one"].to_numpy(dtype=np.float64)
U["bh_q_unique"]=bh_adjust(p)
U["holm_p_unique"]=holm_adjust(p)
map_bh=dict(zip(U["condition_hash"],U["bh_q_unique"]))
map_holm=dict(zip(U["condition_hash"],U["holm_p_unique"]))
map_alias=dict(zip(U["condition_hash"],U["aliases"]))
R["bh_q_unique"]=R["condition_hash"].map(map_bh)
R["holm_p_unique"]=R["condition_hash"].map(map_holm)
R["hypothesis_aliases"]=R["condition_hash"].map(map_alias).astype(int)
R["replicated_positive_mean"]=R["mean_bp"]>0
R["replicated_net1bp_positive"]=R["net_1p0bp_mean_bp"]>0
R["positive_3of4_years"]=R["positive_years_2014_2017"]>=3
R["nominal_p05"]=R["replication_p_one"]<=0.05
R["bh_q10_unique"]=R["bh_q_unique"]<=0.10
R["holm_p05_unique"]=R["holm_p_unique"]<=0.05

R.to_csv(OUT/"REPLICATION_2014_2017_ALL_17.csv",index=False)
U.to_csv(OUT/"REPLICATION_2014_2017_UNIQUE_HYPOTHESES.csv",index=False)
status(OUT,9,12,"unique-hypothesis multiplicity computed; no candidate deleted", unique_hypotheses=len(U), duplicate_aliases=len(R)-len(U), bh_q10_unique=int((U["bh_q_unique"]<=0.10).sum()))

# ---------- ranked reports ----------
ranked=R.sort_values(["bh_q_unique","replication_p_one","mean_bp"],ascending=[True,True,False],kind="mergesort")
ranked.to_csv(OUT/"RANKED_2014_2017_REPLICATION.csv",index=False)

receipt={
    "run_id":RID,
    "status":"COMPLETE_FROZEN_2014_2017_REPLICATION",
    "engine_version":ENGINE_VERSION,
    "source_preflight":PF.name,
    "frozen_candidates":len(R),
    "unique_hypotheses":len(U),
    "state_parity_2010_2013":"EXACT_ZERO_MISMATCH",
    "replication_window":"2014-2017",
    "replicated_positive_mean":int((R["mean_bp"]>0).sum()),
    "replicated_net1bp_positive":int((R["net_1p0bp_mean_bp"]>0).sum()),
    "positive_3of4_years":int((R["positive_years_2014_2017"]>=3).sum()),
    "nominal_p05":int((R["replication_p_one"]<=0.05).sum()),
    "bh_q10_unique_hypotheses":int((U["bh_q_unique"]<=0.10).sum()),
    "holm_p05_unique_hypotheses":int((U["holm_p_unique"]<=0.05).sum()),
    "2018_plus_accessed":False,
    "2023_plus_accessed":False,
    "protected_2026_accessed":False,
    "next":"STOP_FOR_HUMAN_REVIEW_BEFORE_2018_2022_VALIDATION"
}
write_json(OUT/"RUN_RECEIPT.json",receipt)
status(OUT,10,12,"replication receipt written", replicated_net1bp=receipt["replicated_net1bp_positive"], bh_q10_unique=receipt["bh_q10_unique_hypotheses"])
status(OUT,11,12,"2018-2022 validation remains unopened")
status(OUT,12,12,"DONE; frozen 2014-2017 replication complete")

print("\n=== V88 REPLICATION RECEIPT ===")
print(json.dumps(receipt,indent=2))
print("\n=== ALL 17 REPLICATION RESULTS ===")
cols=["panel_rank","family_i","state_i","family_j","state_j","target","direction",
      "n","mean_bp","win_rate_pct","net_1p0bp_mean_bp","net_2p0bp_mean_bp",
      "gross_sum_pct","max_drawdown_pct","positive_years_2014_2017",
      "replication_p_one","bh_q_unique","holm_p_unique","hypothesis_aliases"]
print(ranked[cols].to_string(index=False))
print("\n=== YEARLY DETAILS ===")
ycols=["panel_rank","target","direction",
       "y2014_n","y2014_mean_bp","y2015_n","y2015_mean_bp",
       "y2016_n","y2016_mean_bp","y2017_n","y2017_mean_bp"]
print(ranked[ycols].to_string(index=False))
print("\nRUN:",OUT)
