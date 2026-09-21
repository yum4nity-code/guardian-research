from pathlib import Path
import pandas as pd
import numpy as np
import json
import hashlib

ROOT = Path(r"D:\MT5_Backtests")
BASE = ROOT / "Research" / "Autonomous" / "guardian_edge_factory_v88"
BASE.mkdir(parents=True, exist_ok=True)
MARKETS = ["XAUUSD","XAGUSD","UDXUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","SPXUSD","NSXUSD","WTIUSD","BCOUSD"]
SUPPORTED_FAMILIES = {"rates_yields", "price_cross", "time_state"}

def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def status(out, step, total, msg, **extra):
    payload = {"step": step, "steps": total, "percent": round(100*step/total,1), "message": msg, **extra}
    write_json(out/"LIVE_STATUS.json", payload)
    tail = " | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF88] {step}/{total} {100*step/total:.0f}% | {msg}" + (f" | {tail}" if tail else ""), flush=True)

def as_bool(s):
    if pd.api.types.is_bool_dtype(s):
        return s.fillna(False)
    return s.astype(str).str.strip().str.lower().eq("true")

def decode_trial(trial_idx, singleton_slots, nt, pair_i, pair_j):
    if trial_idx < singleton_slots:
        block = 2 * nt
        fi = trial_idx // block
        rem = trial_idx % block
        return {"kind":"singleton","fi":int(fi),"fj":None,"si":int(rem//nt),"sj":None,"ti":int(rem%nt)}
    off = trial_idx - singleton_slots
    block = 4 * nt
    pi = off // block
    rem = off % block
    combo = rem // nt
    return {
        "kind":"pair",
        "pi":int(pi),
        "fi":int(pair_i[int(pi)]),
        "fj":int(pair_j[int(pi)]),
        "si":int(combo//2),
        "sj":int(combo%2),
        "ti":int(rem%nt),
    }

def family_supported(f):
    f = str(f)
    return f in SUPPORTED_FAMILIES or f.startswith("price_")

def market_from_price_family(f):
    f = str(f)
    if f.startswith("price_") and f not in {"price_cross"}:
        return f[len("price_"):]
    return None

status_dummy = None
runs = sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v87").glob("GEF87-*"))
runs = [p for p in runs if (p/"RUN_RECEIPT.json").exists() and (p/"TRAIN_PLUS_2013_EDGE_AUDIT.csv").exists()]
if not runs:
    raise RuntimeError("No completed V87 run")
V87 = runs[-1]
r87 = json.loads((V87/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r87.get("status") != "COMPLETE_100_CANDIDATE_2013_CONFIRMATION":
    raise RuntimeError(f"Latest V87 status is {r87.get('status')}")
if r87.get("2014_plus_accessed") or r87.get("2023_plus_accessed") or r87.get("protected_2026_accessed"):
    raise RuntimeError("V87 later-window access assertion violated")

RID = "GEF88-" + pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT = BASE/RID
OUT.mkdir(parents=True, exist_ok=False)
status(OUT,1,7,"load completed V87; 2014+ still unopened", source_v87=V87.name)

A = pd.read_csv(V87/"TRAIN_PLUS_2013_EDGE_AUDIT.csv")
if "train_and_2013_net1bp_positive" not in A.columns:
    raise RuntimeError("V87 audit missing train_and_2013_net1bp_positive")
keep = as_bool(A["train_and_2013_net1bp_positive"])
S = A.loc[keep].copy().sort_values(["panel_rank","raw_rank"], kind="mergesort").reset_index(drop=True)
expected = int(r87["train_and_2013_net1bp_positive"])
if len(S) != expected:
    raise RuntimeError(f"Replication shortlist count mismatch: audit={len(S)} receipt={expected}")
if len(S) == 0:
    raise RuntimeError("No V87 candidates meet the frozen replication rule")
status(OUT,2,7,"replication rule applied exactly", candidates=len(S), rule="train + 2013 mean remains >0 after 1 bp hypothetical cost")

# Resolve exact V85 feature identities from the immutable trial indices.
V86A = ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v86a"/r87["source_v86a"]
r86a = json.loads((V86A/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V86 = ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v86"/r86a["source_v86"]
spec86 = json.loads((V86/"FROZEN_V86_SPEC.json").read_text(encoding="utf-8"))
V85 = ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v85"/spec86["source_v85"]
design = json.loads((V85/"TRIAL_DESIGN.json").read_text(encoding="utf-8"))
catalog = pd.read_csv(V85/"FROZEN_ELIGIBLE_FEATURES.csv").reset_index(drop=True)
pairs = pd.read_parquet(V85/"FROZEN_PAIR_UNIVERSE.parquet")
pair_i = pairs["feature_i"].to_numpy(dtype=np.int64)
pair_j = pairs["feature_j"].to_numpy(dtype=np.int64)
nt = int(design["targets"])
singleton_slots = int(design["singleton_slots"])
state_names = ("LO","HI")

rows = []
for r in S.itertuples(index=False):
    d = decode_trial(int(r.trial_index), singleton_slots, nt, pair_i, pair_j)
    ci = catalog.iloc[d["fi"]]
    cj = None if d["fj"] is None else catalog.iloc[d["fj"]]
    rec = {
        "panel_rank": int(r.panel_rank),
        "raw_rank": int(r.raw_rank),
        "trial_index": int(r.trial_index),
        "kind": d["kind"],
        "feature_i_index": int(d["fi"]),
        "feature_i": str(ci["feature"]),
        "layer_i": str(ci["layer"]),
        "family_i": str(ci["family"]),
        "state_i": state_names[d["si"]],
        "feature_j_index": None if d["fj"] is None else int(d["fj"]),
        "feature_j": None if cj is None else str(cj["feature"]),
        "layer_j": None if cj is None else str(cj["layer"]),
        "family_j": None if cj is None else str(cj["family"]),
        "state_j": None if d["sj"] is None else state_names[d["sj"]],
        "target": str(r.target),
        "direction": str(r.direction),
        "train_mean_bp": float(r.mean_bp_train),
        "holdout_2013_mean_bp": float(r.mean_bp_2013),
        "train_net1bp_mean_bp": float(r.net_1p0bp_mean_bp_train),
        "holdout_2013_net1bp_mean_bp": float(r.net_1p0bp_mean_bp_2013),
        "holdout_2013_n": int(r.n_2013),
        "primary_block_days": int(r.primary_block_days),
    }
    # Integrity checks: decoded immutable trial must agree with V87 labels.
    if rec["family_i"] != str(r.family_i):
        raise RuntimeError(f"Trial {r.trial_index}: family_i mismatch {rec['family_i']} != {r.family_i}")
    rfj = None if pd.isna(r.family_j) else str(r.family_j)
    if rec["family_j"] != rfj:
        raise RuntimeError(f"Trial {r.trial_index}: family_j mismatch {rec['family_j']} != {rfj}")
    if rec["state_i"] != str(r.state_i):
        raise RuntimeError(f"Trial {r.trial_index}: state_i mismatch")
    rsj = None if pd.isna(r.state_j) else str(r.state_j)
    if rec["state_j"] != rsj:
        raise RuntimeError(f"Trial {r.trial_index}: state_j mismatch")
    rows.append(rec)

FROZEN = pd.DataFrame(rows)
freeze_path = OUT/"FROZEN_2014_2017_REPLICATION_PANEL.csv"
FROZEN.to_csv(freeze_path, index=False)
status(OUT,3,7,"exact trial definitions frozen before any 2014 value read", candidates=len(FROZEN), sha256=sha256(freeze_path)[:16])

families = sorted(set(FROZEN["family_i"].dropna().astype(str)) | set(FROZEN["family_j"].dropna().astype(str)))
unsupported = [f for f in families if not family_supported(f)]
features = sorted(set(FROZEN["feature_i"].dropna().astype(str)) | set(FROZEN["feature_j"].dropna().astype(str)))
status(OUT,4,7,"feature inventory complete", families=len(families), exact_features=len(features), unsupported_families=unsupported)

# File-existence preflight only. Do not read 2014-2017 price/rate values here.
needed_markets = set()
for f in families:
    m = market_from_price_family(f)
    if m:
        needed_markets.add(m)
if "price_cross" in families:
    needed_markets.update(MARKETS)
for target in FROZEN["target"].astype(str):
    needed_markets.add(target.split("_fwd_",1)[0])

hist_missing = []
for sym in sorted(needed_markets):
    for year in range(2014,2018):
        p = ROOT/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
        if not p.exists():
            hist_missing.append(str(p))

treasury_missing = []
if "rates_yields" in families:
    for folder in ("nominal_yield_curve","real_yield_curve"):
        for year in range(2014,2018):
            p = ROOT/"DataLake"/"raw"/"treasury"/folder/f"{folder}_{year}.xml"
            if not p.exists():
                treasury_missing.append(str(p))

status(
    OUT,5,7,"2014-2017 source presence preflight complete; values still unopened",
    needed_markets=len(needed_markets),
    missing_histdata=len(hist_missing),
    missing_treasury=len(treasury_missing),
)

preflight_ok = (not unsupported) and (not hist_missing) and (not treasury_missing)
receipt = {
    "run_id": RID,
    "status": "COMPLETE_REPLICATION_FREEZE_PREFLIGHT" if preflight_ok else "STOP_REPLICATION_PREFLIGHT",
    "source_v87": V87.name,
    "selection_rule": "all V87 candidates with positive net mean after hypothetical 1 bp cost in both 2010-2012 and 2013",
    "frozen_candidates": len(FROZEN),
    "frozen_panel_sha256": sha256(freeze_path),
    "families": families,
    "exact_features": features,
    "needed_markets": sorted(needed_markets),
    "unsupported_families": unsupported,
    "missing_histdata_files": hist_missing,
    "missing_treasury_files": treasury_missing,
    "2014_2017_values_accessed": False,
    "2018_plus_accessed": False,
    "2023_plus_accessed": False,
    "protected_2026_accessed": False,
    "next": "BUILD_AND_RUN_V88_2014_2017_REPLICATION" if preflight_ok else "REPAIR_SOURCE_MATERIALIZATION_BEFORE_REPLICATION",
}
write_json(OUT/"RUN_RECEIPT.json", receipt)
status(OUT,6,7,"preflight receipt written", status=receipt["status"], next=receipt["next"])
status(OUT,7,7,"DONE; shortlist frozen and 2014-2017 values still unopened")

print("\n=== V88 FREEZE PREFLIGHT RECEIPT ===")
print(json.dumps(receipt, indent=2))
print("\n=== FROZEN REPLICATION PANEL ===")
print(FROZEN.to_string(index=False))
print("\n=== FAMILY COUNTS ===")
print(pd.concat([FROZEN["family_i"],FROZEN["family_j"]]).dropna().value_counts().to_string())
print("\nRUN:", OUT)
