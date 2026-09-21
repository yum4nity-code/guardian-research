from pathlib import Path
import pandas as pd
import numpy as np
import json, time, re, math, hashlib

ROOT=Path(r"D:\MT5_Backtests")
RID="GEF84-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v84"/RID
OUT.mkdir(parents=True,exist_ok=True)
T0=time.time()

BENCH_PAIR_TARGET=128
MIN_COVERAGE=0.45
MIN_UNIQUE=10
MIN_STATE_SUPPORT=500

def status(stage,message,**extra):
    e=time.time()-T0
    payload={"run_id":RID,"stage":stage,"elapsed_s":round(e,1),"message":message,**extra}
    (OUT/"LIVE_STATUS.json").write_text(json.dumps(payload,indent=2,default=str),encoding="utf-8")
    extras=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF84] {stage} | elapsed {e/60:.1f}m | {message}"+(f" | {extras}" if extras else ""),flush=True)

def family(c):
    s=str(c)
    for pref in ["cftc_","rates_yields_","alfred_","cboe_vol_","cfe_","financial_conditions_","treasury_auctions_"]:
        if s.startswith(pref):
            return pref.rstrip("_")
    m=re.match(r"^price_([A-Z0-9]+USD)_",s)
    if m:
        return "price_"+m.group(1)
    if s.startswith("price_cross_"):
        return "price_cross"
    if s.startswith("time_"):
        return "time_state"
    return "other"

def eligible(df):
    out=[]
    for c in df.columns:
        s=pd.to_numeric(df[c],errors="coerce")
        if s.notna().mean()>=MIN_COVERAGE and s.nunique(dropna=True)>=MIN_UNIQUE:
            out.append(c)
    return out

def causal_states(s,min_periods):
    s=pd.to_numeric(s,errors="coerce")
    mu=s.expanding(min_periods=min_periods).mean().shift(1)
    sd=s.expanding(min_periods=min_periods).std().shift(1).replace(0,np.nan)
    z=((s-mu)/sd).to_numpy(dtype=np.float32)
    return np.isfinite(z)&(z<=-1.0),np.isfinite(z)&(z>=1.0)

status("1/10","locate latest completed V83; benchmark only, no candidate selection")
runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v83").glob("GEF83-*"))
runs=[p for p in runs if (p/"RUN_RECEIPT.json").exists()]
if not runs:
    raise RuntimeError("No completed V83 run found")
V83=runs[-1]
receipt83=json.loads((V83/"RUN_RECEIPT.json").read_text())
if receipt83.get("status")!="COMPLETE_CORRECTED_MULTIRESOLUTION_CAUSAL_ARCHITECTURE":
    raise RuntimeError(f"Latest V83 not complete: {receipt83.get('status')}")
if receipt83.get("2014_plus_accessed") or receipt83.get("2023_plus_accessed") or receipt83.get("protected_2026_accessed"):
    raise RuntimeError("V83 access assertions violated")

status("2/10","load corrected slow state, 5m price state, targets and as-of bridge")
S=pd.read_parquet(V83/"SLOW_CAUSAL_STATE_2010_2013.parquet")
F=pd.read_parquet(V83/"PRICE_STATE_5M_2010_2013.parquet")
Y=pd.read_parquet(V83/"FUTURE_TARGETS_5M_2010_2013.parquet")
bridge=np.load(V83/"SLOW_ROW_ASOF_FOR_5M.npy")
S.index=pd.to_datetime(S.index);F.index=pd.to_datetime(F.index);Y=Y.reindex(F.index)
if len(bridge)!=len(F):
    raise RuntimeError("Slow/fast bridge length mismatch")
targets=[c for c in Y.columns if "_fwd_" in str(c)]
YA=Y[targets].to_numpy(dtype=np.float32)
valid=np.isfinite(YA)
status("3/10","inputs loaded",slow_rows=len(S),fast_rows=len(F),slow_features=S.shape[1],fast_features=F.shape[1],return_targets=len(targets))

slow_cols=eligible(S);fast_cols=eligible(F)
catalog=pd.DataFrame(
    [{"feature":c,"layer":"slow","family":family(c),"coverage":float(S[c].notna().mean())} for c in slow_cols]+
    [{"feature":c,"layer":"fast","family":family(c),"coverage":float(F[c].notna().mean())} for c in fast_cols]
)
catalog.to_csv(OUT/"ELIGIBLE_FEATURES.csv",index=False)
fam_counts=catalog.groupby(["layer","family"]).size().to_dict()
status("4/10","eligible feature universe counted",eligible_slow=len(slow_cols),eligible_fast=len(fast_cols),families=len(set(catalog.family)))

sample_features=[]
for (layer,fam),g in catalog.groupby(["layer","family"],sort=True):
    sample_features.extend([(r.feature,layer,fam) for r in g.sort_values("feature").head(6).itertuples()])
if len(sample_features)<10:
    raise RuntimeError("Too few sampled features for benchmark")

states={}
state_meta=[]
for idx,(c,layer,fam) in enumerate(sample_features,1):
    if layer=="slow":
        lo_s,hi_s=causal_states(S[c],500)
        ok=bridge>=0
        lo=np.zeros(len(F),dtype=bool);hi=np.zeros(len(F),dtype=bool)
        lo[ok]=lo_s[bridge[ok]];hi[ok]=hi_s[bridge[ok]]
    else:
        lo,hi=causal_states(F[c],5000)
    states[(layer,c)]=(lo,hi)
    state_meta.append({"feature":c,"layer":layer,"family":fam,"lo_support":int(lo.sum()),"hi_support":int(hi.sum())})
    if idx%10==0 or idx==len(sample_features):
        status("5/10",f"causal benchmark states {idx}/{len(sample_features)}",features_done=idx,features_total=len(sample_features))
pd.DataFrame(state_meta).to_csv(OUT/"BENCHMARK_STATE_SUPPORT.csv",index=False)

all_records=list(catalog[["feature","layer","family"]].itertuples(index=False,name=None))
total_pairs=sum(1 for i,a in enumerate(all_records) for b in all_records[i+1:] if a[2]!=b[2])
sample_pairs=[(a,b) for i,a in enumerate(sample_features) for b in sample_features[i+1:] if a[2]!=b[2]]
sample_pairs=sorted(sample_pairs,key=lambda ab:(ab[0][2],ab[1][2],ab[0][0],ab[1][0]))
if len(sample_pairs)>BENCH_PAIR_TARGET:
    step=len(sample_pairs)/BENCH_PAIR_TARGET
    chosen=[];used=set()
    for i in range(BENCH_PAIR_TARGET):
        j=min(int(i*step),len(sample_pairs)-1)
        if j not in used:
            used.add(j);chosen.append(sample_pairs[j])
    sample_pairs=chosen

status("6/10","pair benchmark plan frozen",sampled_features=len(sample_features),benchmark_pairs=len(sample_pairs),projected_cross_family_pairs=total_pairs)

t_kernel=time.time();ops=0;support_sum=0
for i,(a,b) in enumerate(sample_pairs,1):
    alo,ahi=states[(a[1],a[0])];blo,bhi=states[(b[1],b[0])]
    for ma in (alo,ahi):
        for mb in (blo,bhi):
            mask=ma & mb
            idx=np.flatnonzero(mask)
            if len(idx)<MIN_STATE_SUPPORT:
                continue
            vals=YA[idx]
            finite=np.isfinite(vals)
            n=finite.sum(axis=0)
            sums=np.nansum(vals,axis=0,dtype=np.float64)
            pos=((vals>0)&finite).sum(axis=0)
            _means=np.divide(sums,n,out=np.full(len(targets),np.nan),where=n>0)
            _hits=np.divide(pos,n,out=np.full(len(targets),np.nan),where=n>0)
            ops+=int((n>=MIN_STATE_SUPPORT).sum())
            support_sum+=len(idx)
    if i%16==0 or i==len(sample_pairs):
        elapsed=time.time()-t_kernel
        rate=i/max(elapsed,1e-9)
        status("7/10",f"kernel {i}/{len(sample_pairs)} pairs",pair_progress=f"{i}/{len(sample_pairs)}",pairs_per_s=round(rate,3),benchmark_ops=ops)

kernel_seconds=time.time()-t_kernel
pair_rate=len(sample_pairs)/max(kernel_seconds,1e-9)
projected_pair_minutes=total_pairs/max(pair_rate,1e-9)/60
avg_support=support_sum/max(1,4*len(sample_pairs))
status("8/10","kernel benchmark complete",pairs_per_s=round(pair_rate,3),projected_pair_minutes=round(projected_pair_minutes,1),avg_state_intersection_rows=round(avg_support,1),benchmark_ops=ops)

recommended_chunk=256 if pair_rate>=2 else 128 if pair_rate>=0.5 else 64
engine_plan={
    "candidate_selection_from_benchmark":False,
    "benchmark_pair_results_persisted":False,
    "pair_universe":"cross-source/cross-market first; within-family interactions are a later hierarchical stage, not silently omitted",
    "full_scan_requirements":["checkpoint/resume","LIVE_STATUS every <=60s","streaming top-K/no giant survivor list","trial ledger","selection-aware correction before replication","no 2014+ access"],
    "recommended_checkpoint_pairs":recommended_chunk,
    "projected_cross_family_pairs":total_pairs,
    "measured_pairs_per_second":pair_rate,
    "projected_pair_scan_minutes":projected_pair_minutes
}
(OUT/"ENGINE_PLAN.json").write_text(json.dumps(engine_plan,indent=2),encoding="utf-8")
status("9/10","full-scan engineering plan written",checkpoint_pairs=recommended_chunk)

receipt={
    "run_id":RID,
    "status":"BENCHMARK_COMPLETE_CORRECTED_5M_ENGINE",
    "source_v83":V83.name,
    "eligible_slow_features":len(slow_cols),
    "eligible_fast_features":len(fast_cols),
    "eligible_total_features":len(catalog),
    "feature_family_counts":{f"{k[0]}::{k[1]}":int(v) for k,v in fam_counts.items()},
    "return_targets":len(targets),
    "benchmark_features":len(sample_features),
    "benchmark_pairs":len(sample_pairs),
    "benchmark_kernel_seconds":kernel_seconds,
    "pairs_per_second":pair_rate,
    "projected_cross_family_pairs":total_pairs,
    "projected_pair_scan_minutes":projected_pair_minutes,
    "benchmark_ops":ops,
    "candidate_selection_performed":False,
    "edge_trials":0,
    "2014_plus_accessed":False,
    "2023_plus_accessed":False,
    "protected_2026_accessed":False,
    "next":"V85_CHECKPOINTED_SELECTION_AWARE_DISCOVERY_ENGINE"
}
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
status("10/10","DONE; benchmark only",next=receipt["next"])
print("\n=== V84 RECEIPT ===");print(json.dumps(receipt,indent=2))
print("\n=== ENGINE PLAN ===");print(json.dumps(engine_plan,indent=2))
print("\nRUN:",OUT)
