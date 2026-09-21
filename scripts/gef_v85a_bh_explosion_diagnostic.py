from pathlib import Path
import pandas as pd
import numpy as np
import json, time, hashlib
from collections import Counter, defaultdict

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v85"
RID="GEF85A-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v85a"/RID
OUT.mkdir(parents=True,exist_ok=True)
T0=time.time()

def status(i,n,msg,**extra):
    e=time.time()-T0
    payload={"run_id":RID,"step":i,"steps":n,"percent":round(100*i/n,1),"elapsed_s":round(e,1),"message":msg,**extra}
    (OUT/"LIVE_STATUS.json").write_text(json.dumps(payload,indent=2,default=str),encoding="utf-8")
    tail=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF85A] {i}/{n} {100*i/n:.0f}% | elapsed {e:.1f}s | {msg}"+(f" | {tail}" if tail else ""),flush=True)

def hash_bool(a):
    return hashlib.sha256(np.packbits(np.asarray(a,dtype=np.bool_)).tobytes()).hexdigest()

status(1,9,"locate completed V85 safety-stop artifacts; diagnostic only")
cur=json.loads((BASE/"CURRENT_RUN.json").read_text(encoding="utf-8"))
V85=BASE/cur["run_id"]
r85=json.loads((V85/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r85.get("status")!="STOP_TOO_MANY_BH_CANDIDATES":
    raise RuntimeError(f"Expected STOP_TOO_MANY_BH_CANDIDATES, got {r85.get('status')}")
if r85.get("2014_plus_accessed") or r85.get("2023_plus_accessed") or r85.get("protected_2026_accessed"):
    raise RuntimeError("Access assertions violated")
catalog=pd.read_csv(V85/"FROZEN_ELIGIBLE_FEATURES.csv")
pairs=pd.read_parquet(V85/"FROZEN_PAIR_UNIVERSE.parquet")
design=json.loads((V85/"TRIAL_DESIGN.json").read_text(encoding="utf-8"))
status(2,9,"frozen design loaded",features=len(catalog),pairs=len(pairs),targets=design["targets"])

nf=len(catalog); nt=int(design["targets"]); singleton_slots=int(design["singleton_slots"]); total_slots=int(design["predeclared_trial_slots"])
pmap=np.memmap(V85/"TRAIN_PVALUES.float32.dat",mode="r",dtype=np.float32,shape=(total_slots,))
cut=float(r85["bh_threshold"])
sig=np.flatnonzero(np.isfinite(pmap) & (pmap<=cut))
if len(sig)!=int(r85["bh_candidates"]):
    raise RuntimeError(f"BH candidate count mismatch {len(sig)} vs {r85['bh_candidates']}")
status(3,9,"BH candidate indexes reconstructed",bh_candidates=len(sig),threshold=cut)

# Decode only the BH set; this is cheap and does not touch holdout returns.
target_names=[]
v84c=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v84c"/json.loads((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v85"/"CURRENT_RUN.json").read_text())["source_v84c"]
# target order can be reconstructed from frozen design only by reading V83 target columns.
r84=json.loads((v84c/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
v83b=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v83b"/r84["source_v83b"]
manifest=json.loads((v83b/"REPAIRED_ARCHITECTURE_MANIFEST.json").read_text(encoding="utf-8"))
Ycols=pd.read_parquet(manifest["targets_5m_path"]).columns
target_names=[c for c in Ycols if "_fwd_" in str(c)]
if len(target_names)!=nt: raise RuntimeError("Target order mismatch")

family_counter=Counter();target_counter=Counter();kind_counter=Counter();combo_counter=Counter()
rows=[]
for k,trial in enumerate(sig):
    trial=int(trial)
    if trial<singleton_slots:
        block=2*nt;fi=trial//block;rem=trial%block;st=rem//nt;ti=rem%nt
        kind="singleton";fj=None;sj=None
    else:
        off=trial-singleton_slots;block=4*nt;pi=off//block;rem=off%block;combo=rem//nt;ti=rem%nt
        fi=int(pairs.iloc[pi]["feature_i"]);fj=int(pairs.iloc[pi]["feature_j"]);st=int(combo//2);sj=int(combo%2);kind="pair"
    fami=str(catalog.iloc[fi]["family"]);fami2=fami
    famj=None if fj is None else str(catalog.iloc[fj]["family"])
    kind_counter[kind]+=1;target_counter[target_names[ti]]+=1
    key=fami if famj is None else " × ".join(sorted([fami,famj]))
    family_counter[key]+=1
    combo_counter[(kind,st,sj if sj is not None else -1)]+=1
    if k<20000:
        rows.append({"trial_index":trial,"kind":kind,"family_i":fami,"family_j":famj,"target":target_names[ti],"p_value":float(pmap[trial])})
status(4,9,"candidate concentration decoded",top_family=family_counter.most_common(1)[0] if family_counter else None,top_target=target_counter.most_common(1)[0] if target_counter else None)

pd.DataFrame(family_counter.most_common(),columns=["family_combo","bh_candidates"]).to_csv(OUT/"BH_BY_FAMILY_COMBO.csv",index=False)
pd.DataFrame(target_counter.most_common(),columns=["target","bh_candidates"]).to_csv(OUT/"BH_BY_TARGET.csv",index=False)
pd.DataFrame(kind_counter.items(),columns=["kind","bh_candidates"]).to_csv(OUT/"BH_BY_KIND.csv",index=False)

# Exact feature-state duplicate audit on training cache.
sm=json.loads((V85/"STATE_CACHE_META.json").read_text(encoding="utf-8"))
shape=tuple(sm["train_shape"])
ST=np.memmap(V85/"STATE_TRAIN.bool.dat",mode="r",dtype=np.bool_,shape=shape)
state_groups=defaultdict(list)
for fi in range(nf):
    for st in range(2):
        h=hash_bool(ST[fi,st,:])
        state_groups[h].append((fi,st))
unique_states=len(state_groups)
dup_states=sum(len(v)-1 for v in state_groups.values())
max_group=max((len(v) for v in state_groups.values()),default=0)
dups=[]
for h,v in state_groups.items():
    if len(v)>1:
        dups.append({"hash":h,"size":len(v),"members":" | ".join(f"{catalog.iloc[fi]['feature']}::{['LO','HI'][st]}" for fi,st in v[:20])})
pd.DataFrame(dups).sort_values("size",ascending=False).to_csv(OUT/"EXACT_DUPLICATE_FEATURE_STATES.csv",index=False)
status(5,9,"exact feature-state duplication audited",raw_states=nf*2,unique_states=unique_states,duplicate_excess=dup_states,max_duplicate_group=max_group)

# Sample exact pair-mask duplication to determine whether the 1.56m discoveries are largely repeated conditions.
# Deterministic evenly-spaced sample of up to 10k BH pair candidates.
pair_sig=[int(x) for x in sig if int(x)>=singleton_slots]
sample_n=min(10000,len(pair_sig))
sample_trials=[]
if sample_n:
    pos=np.linspace(0,len(pair_sig)-1,sample_n,dtype=int)
    sample_trials=[pair_sig[i] for i in pos]
pair_hash=Counter()
for idx,trial in enumerate(sample_trials,1):
    off=trial-singleton_slots;block=4*nt;pi=off//block;rem=off%block;combo=rem//nt
    fi=int(pairs.iloc[pi]["feature_i"]);fj=int(pairs.iloc[pi]["feature_j"]);si=int(combo//2);sj=int(combo%2)
    h=hash_bool(ST[fi,si,:] & ST[fj,sj,:]);pair_hash[h]+=1
    if idx%2000==0 or idx==len(sample_trials):
        status(6,9,f"pair-mask duplicate sample {idx}/{len(sample_trials)}",sampled=idx)
unique_pair_masks=len(pair_hash)
sample_dup_fraction=(1-unique_pair_masks/max(1,len(sample_trials))) if sample_trials else 0.0

# P-value bins tell us whether BH is barely permissive or whether there is a deep pile of tiny p-values.
bins=[0,1e-12,1e-10,1e-8,1e-6,1e-5,1e-4,1e-3,cut]
finite=np.asarray(pmap);finite=finite[np.isfinite(finite)]
hist=[]
for lo,hi in zip(bins[:-1],bins[1:]):
    hist.append({"lo":lo,"hi":hi,"count":int(((finite>lo)&(finite<=hi)).sum())})
pd.DataFrame(hist).to_csv(OUT/"P_VALUE_DEPTH.csv",index=False)
status(7,9,"p-value depth profiled",finite_tests=len(finite),below_1e6=int((finite<=1e-6).sum()))

top_fams=family_counter.most_common(30);top_targets=target_counter.most_common(30)
summary={
    "run_id":RID,
    "status":"COMPLETE_V85_BH_EXPLOSION_DIAGNOSTIC",
    "source_v85":V85.name,
    "valid_tests":int(r85["valid_train_tests"]),
    "bh_candidates":len(sig),
    "bh_fraction":len(sig)/int(r85["valid_train_tests"]),
    "bh_threshold":cut,
    "raw_feature_states":nf*2,
    "unique_exact_feature_states":unique_states,
    "duplicate_feature_state_excess":dup_states,
    "max_exact_feature_state_group":max_group,
    "pair_mask_sample_n":len(sample_trials),
    "pair_mask_sample_unique":unique_pair_masks,
    "pair_mask_sample_duplicate_fraction":sample_dup_fraction,
    "top_family_combos":top_fams,
    "top_targets":top_targets,
    "edge_trials":0,
    "2013_holdout_accessed":False,
    "2014_plus_accessed":False,
    "2023_plus_accessed":False,
    "protected_2026_accessed":False,
    "next":"DESIGN_V85B_HIERARCHICAL_DEDUP_BLOCK_NULL_FROM_THIS_DIAGNOSTIC"
}
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
status(8,9,"diagnostic receipt written",bh_fraction=round(summary["bh_fraction"],4),pair_mask_sample_duplicate_fraction=round(sample_dup_fraction,4))
status(9,9,"STOP; no holdout or later periods touched")
print("\n=== V85A RECEIPT ===");print(json.dumps(summary,indent=2))
print("\n=== TOP BH FAMILY COMBOS ===");print(pd.DataFrame(top_fams,columns=["family_combo","bh_candidates"]).to_string(index=False))
print("\n=== TOP BH TARGETS ===");print(pd.DataFrame(top_targets,columns=["target","bh_candidates"]).to_string(index=False))
print("\nRUN:",OUT)
