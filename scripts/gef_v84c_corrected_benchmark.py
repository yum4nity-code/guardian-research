from pathlib import Path
import pandas as pd
import numpy as np
import json, re, time

ROOT=Path(r"D:\MT5_Backtests")
RID="GEF84C-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v84c"/RID
OUT.mkdir(parents=True,exist_ok=True)
T0=time.time()

MARKETS=["XAUUSD","XAGUSD","UDXUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","SPXUSD","NSXUSD","WTIUSD","BCOUSD"]
BENCH_PAIR_TARGET=128
MIN_SLOW_COVERAGE=.45
MIN_FAST_NON_NULL=50000
MIN_UNIQUE=10
MIN_STATE_SUPPORT=500

def status(stage,message,**extra):
    e=time.time()-T0
    payload={"run_id":RID,"stage":stage,"elapsed_s":round(e,1),"message":message,**extra}
    (OUT/"LIVE_STATUS.json").write_text(json.dumps(payload,indent=2,default=str),encoding="utf-8")
    extras=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF84C] {stage} | elapsed {e/60:.1f}m | {message}"+(f" | {extras}" if extras else ""),flush=True)

def family(c):
    s=str(c)
    for m in MARKETS:
        if s.startswith(f"price_{m}_"): return f"price_{m}"
        if s.startswith(f"cftc_{m}_"): return f"cftc_{m}"
    for pref in ["rates_yields_","alfred_","cboe_vol_","cfe_","financial_conditions_","treasury_auctions_"]:
        if s.startswith(pref): return pref.rstrip("_")
    if s.startswith("price_cross_"): return "price_cross"
    if s.startswith("time_"): return "time_state"
    return "other"

def causal_states(s,min_periods):
    s=pd.to_numeric(s,errors="coerce")
    mu=s.expanding(min_periods=min_periods).mean().shift(1)
    sd=s.expanding(min_periods=min_periods).std().shift(1).replace(0,np.nan)
    z=((s-mu)/sd).to_numpy(dtype=np.float32)
    return np.isfinite(z)&(z<=-1.0),np.isfinite(z)&(z>=1.0)

# Deterministic preflight for taxonomy and DataFrame-column access.
_test=pd.DataFrame({"feature":["price_USDJPY_ret_5m","cftc_EURUSD_x"],"family":["price_USDJPY","cftc_EURUSD"]})
assert any(_test["family"]=="price_USDJPY")
assert list(_test[_test["family"]=="cftc_EURUSD"]["feature"])==["cftc_EURUSD_x"]
del _test

status("1/10","load V83B repaired slow state + immutable V83 5m layers; benchmark only")
b_runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v83b").glob("GEF83B-*"))
b_runs=[p for p in b_runs if (p/"RUN_RECEIPT.json").exists()]
if not b_runs: raise RuntimeError("No completed V83B")
V83B=b_runs[-1]
rb=json.loads((V83B/"RUN_RECEIPT.json").read_text())
if rb.get("status")!="COMPLETE_V83_RATES_REPAIR": raise RuntimeError("Latest V83B not complete")
manifest=json.loads((V83B/"REPAIRED_ARCHITECTURE_MANIFEST.json").read_text())
S=pd.read_parquet(manifest["slow_state_repaired_path"])
F=pd.read_parquet(manifest["price_state_5m_path"])
Y=pd.read_parquet(manifest["targets_5m_path"])
bridge=np.load(manifest["bridge_path"])
S.index=pd.to_datetime(S.index);F.index=pd.to_datetime(F.index);Y=Y.reindex(F.index)
targets=[c for c in Y.columns if "_fwd_" in str(c)]
YA=Y[targets].to_numpy(dtype=np.float32)
status("2/10","layers loaded",slow_rows=len(S),fast_rows=len(F),slow_features=S.shape[1],fast_features=F.shape[1],return_targets=len(targets))

train_s=S.index.year<=2012
train_f=F.index.year<=2012
slow_cols=[]
for c in S.columns:
    s=pd.to_numeric(S.loc[train_s,c],errors="coerce")
    if s.notna().mean()>=MIN_SLOW_COVERAGE and s.nunique(dropna=True)>=MIN_UNIQUE:
        slow_cols.append(c)
fast_cols=[]
for c in F.columns:
    s=pd.to_numeric(F.loc[train_f,c],errors="coerce")
    if s.notna().sum()>=MIN_FAST_NON_NULL and s.nunique(dropna=True)>=MIN_UNIQUE:
        fast_cols.append(c)

catalog=pd.DataFrame(
    [{"feature":c,"layer":"slow","family":family(c),"train_non_null":int(pd.to_numeric(S.loc[train_s,c],errors="coerce").notna().sum())} for c in slow_cols]+
    [{"feature":c,"layer":"fast","family":family(c),"train_non_null":int(pd.to_numeric(F.loc[train_f,c],errors="coerce").notna().sum())} for c in fast_cols]
)
catalog.to_csv(OUT/"ELIGIBLE_FEATURES.csv",index=False)
bad=catalog[catalog["family"]=="other"]
if len(bad): raise RuntimeError(f"Unclassified eligible features remain: {bad["feature"].tolist()[:20]}")
counts=catalog.groupby(["layer","family"]).size().reset_index(name="features")
counts.to_csv(OUT/"FEATURE_FAMILY_COUNTS.csv",index=False)

missing_price=[m for m in MARKETS if not any(catalog["family"]==f"price_{m}")]
if missing_price: raise RuntimeError(f"Price families missing after active-support eligibility: {missing_price}")
if not any(catalog["family"]=="rates_yields"): raise RuntimeError("Rates still absent after V83B repair")
status("3/10","corrected eligibility passed",eligible_slow=len(slow_cols),eligible_fast=len(fast_cols),families=len(counts),missing_price_families=0)

sample_features=[]
for (layer,fam),g in catalog.groupby(["layer","family"],sort=True):
    sample_features.extend([(r.feature,layer,fam) for r in g.sort_values("feature").head(5).itertuples()])
states={}
for idx,(c,layer,fam) in enumerate(sample_features,1):
    if layer=="slow":
        lo_s,hi_s=causal_states(S[c],500)
        ok=bridge>=0
        lo=np.zeros(len(F),dtype=bool);hi=np.zeros(len(F),dtype=bool)
        lo[ok]=lo_s[bridge[ok]];hi[ok]=hi_s[bridge[ok]]
    else:
        lo,hi=causal_states(F[c],5000)
    states[(layer,c)]=(lo,hi)
    if idx%10==0 or idx==len(sample_features):
        status("4/10",f"states {idx}/{len(sample_features)}",features_done=idx,features_total=len(sample_features))

records=list(catalog[["feature","layer","family"]].itertuples(index=False,name=None))
total_pairs=sum(1 for i,a in enumerate(records) for b in records[i+1:] if a[2]!=b[2])
sample_pairs=[(a,b) for i,a in enumerate(sample_features) for b in sample_features[i+1:] if a[2]!=b[2]]
sample_pairs=sorted(sample_pairs,key=lambda ab:(ab[0][2],ab[1][2],ab[0][0],ab[1][0]))
if len(sample_pairs)>BENCH_PAIR_TARGET:
    step=len(sample_pairs)/BENCH_PAIR_TARGET
    sample_pairs=[sample_pairs[min(int(i*step),len(sample_pairs)-1)] for i in range(BENCH_PAIR_TARGET)]
status("5/10","benchmark pair plan",benchmark_pairs=len(sample_pairs),projected_cross_family_pairs=total_pairs)

t=time.time();ops=0;support_sum=0
for i,(a,b) in enumerate(sample_pairs,1):
    alo,ahi=states[(a[1],a[0])];blo,bhi=states[(b[1],b[0])]
    for ma in (alo,ahi):
        for mb in (blo,bhi):
            idx=np.flatnonzero(ma & mb)
            if len(idx)<MIN_STATE_SUPPORT: continue
            vals=YA[idx]
            finite=np.isfinite(vals)
            n=finite.sum(axis=0)
            sums=np.nansum(vals,axis=0,dtype=np.float64)
            pos=((vals>0)&finite).sum(axis=0)
            _means=np.divide(sums,n,out=np.full(len(targets),np.nan),where=n>0)
            _hits=np.divide(pos,n,out=np.full(len(targets),np.nan),where=n>0)
            ops+=int((n>=MIN_STATE_SUPPORT).sum());support_sum+=len(idx)
    if i%16==0 or i==len(sample_pairs):
        rate=i/max(time.time()-t,1e-9)
        status("6/10",f"kernel {i}/{len(sample_pairs)}",pair_progress=f"{i}/{len(sample_pairs)}",pairs_per_s=round(rate,3),ops=ops)

kernel=time.time()-t
rate=len(sample_pairs)/max(kernel,1e-9)
projected=total_pairs/max(rate,1e-9)/60
status("7/10","benchmark complete",pairs_per_s=round(rate,3),projected_full_minutes=round(projected,1),ops=ops)

engine_plan={
    "candidate_selection_from_benchmark":False,
    "pair_universe":"cross-source/cross-market first",
    "eligibility":{"slow":"training coverage >=45%, nunique>=10","fast_price":"training non-null >=50,000, nunique>=10; avoids penalizing market trading hours"},
    "requirements":["checkpoint/resume","LIVE_STATUS <=60s","streaming top-K","trial ledger","year holdout inside discovery","selection-aware correction before 2014-2017 replication","no 2014+ access"],
    "projected_cross_family_pairs":total_pairs,
    "pairs_per_second":rate,
    "projected_full_minutes":projected,
    "checkpoint_pairs":256 if rate>=2 else 128
}
(OUT/"ENGINE_PLAN.json").write_text(json.dumps(engine_plan,indent=2),encoding="utf-8")
status("8/10","engine plan written",checkpoint_pairs=engine_plan["checkpoint_pairs"])

family_dict={f"{r.layer}::{r.family}":int(r.features) for r in counts.itertuples()}
receipt={
    "run_id":RID,
    "status":"BENCHMARK_COMPLETE_V83B_CORRECTED_ENGINE",
    "source_v83b":V83B.name,
    "eligible_slow_features":len(slow_cols),
    "eligible_fast_features":len(fast_cols),
    "eligible_total_features":len(catalog),
    "feature_family_counts":family_dict,
    "return_targets":len(targets),
    "benchmark_pairs":len(sample_pairs),
    "benchmark_kernel_seconds":kernel,
    "pairs_per_second":rate,
    "projected_cross_family_pairs":total_pairs,
    "projected_pair_scan_minutes":projected,
    "candidate_selection_performed":False,
    "edge_trials":0,
    "2014_plus_accessed":False,
    "2023_plus_accessed":False,
    "protected_2026_accessed":False,
    "next":"V85_CHECKPOINTED_SELECTION_AWARE_DISCOVERY_ENGINE"
}
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
status("9/10","receipt written",eligible_total=len(catalog))
status("10/10","DONE; benchmark only",next=receipt["next"])
print("\n=== V84C RECEIPT ===");print(json.dumps(receipt,indent=2))
print("\n=== FEATURE FAMILY COUNTS ===");print(counts.to_string(index=False))
print("\n=== ENGINE PLAN ===");print(json.dumps(engine_plan,indent=2))
print("\nRUN:",OUT)
