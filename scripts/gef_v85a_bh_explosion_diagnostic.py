from pathlib import Path
import pandas as pd
import numpy as np
import json
import time
import hashlib
import pyarrow.parquet as pq
from collections import Counter, defaultdict

ROOT = Path(r"D:\MT5_Backtests")
V85_BASE = ROOT / "Research" / "Autonomous" / "guardian_edge_factory_v85"
RID = "GEF85A-" + pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT = ROOT / "Research" / "Autonomous" / "guardian_edge_factory_v85a" / RID
OUT.mkdir(parents=True, exist_ok=True)
T0 = time.time()
SAMPLE_PAIR_MASKS = 10_000
PMAP_CHUNK = 1_000_000


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def status(i, n, msg, **extra):
    elapsed = time.time() - T0
    payload = {
        "run_id": RID,
        "step": i,
        "steps": n,
        "percent": round(100 * i / n, 1),
        "elapsed_s": round(elapsed, 1),
        "message": msg,
        **extra,
    }
    write_json(OUT / "LIVE_STATUS.json", payload)
    tail = " | ".join(f"{k}={v}" for k, v in extra.items())
    print(
        f"[GEF85A] {i}/{n} {100*i/n:.0f}% | elapsed {elapsed:.1f}s | {msg}"
        + (f" | {tail}" if tail else ""),
        flush=True,
    )


def hash_bool(mask):
    packed = np.packbits(np.asarray(mask, dtype=np.bool_))
    return hashlib.sha256(packed.tobytes()).hexdigest()


status(1, 9, "locate completed V85 safety-stop artifacts; diagnostic only")

current_path = V85_BASE / "CURRENT_RUN.json"
if not current_path.exists():
    raise RuntimeError("Missing V85 CURRENT_RUN.json")

current = json.loads(current_path.read_text(encoding="utf-8"))
V85 = V85_BASE / current["run_id"]
receipt_path = V85 / "RUN_RECEIPT.json"
if not receipt_path.exists():
    raise RuntimeError(f"Missing V85 receipt: {receipt_path}")

r85 = json.loads(receipt_path.read_text(encoding="utf-8"))
if r85.get("status") != "STOP_TOO_MANY_BH_CANDIDATES":
    raise RuntimeError(
        f"Expected STOP_TOO_MANY_BH_CANDIDATES, got {r85.get('status')}"
    )
if (
    r85.get("2014_plus_accessed")
    or r85.get("2023_plus_accessed")
    or r85.get("protected_2026_accessed")
):
    raise RuntimeError("V85 access assertions violated")

catalog = pd.read_csv(V85 / "FROZEN_ELIGIBLE_FEATURES.csv")
pairs = pd.read_parquet(V85 / "FROZEN_PAIR_UNIVERSE.parquet")
design = json.loads((V85 / "TRIAL_DESIGN.json").read_text(encoding="utf-8"))

required_catalog = {"feature", "family", "layer"}
if not required_catalog.issubset(catalog.columns):
    raise RuntimeError(
        f"Catalog missing columns: {sorted(required_catalog - set(catalog.columns))}"
    )
required_pairs = {"feature_i", "feature_j"}
if not required_pairs.issubset(pairs.columns):
    raise RuntimeError(
        f"Pair universe missing columns: {sorted(required_pairs - set(pairs.columns))}"
    )

status(
    2,
    9,
    "frozen design loaded",
    features=len(catalog),
    pairs=len(pairs),
    targets=int(design["targets"]),
)

nf = len(catalog)
nt = int(design["targets"])
singleton_slots = int(design["singleton_slots"])
total_slots = int(design["predeclared_trial_slots"])

pmap = np.memmap(
    V85 / "TRAIN_PVALUES.float32.dat",
    mode="r",
    dtype=np.float32,
    shape=(total_slots,),
)
cutoff = float(r85["bh_threshold"])
sig = np.flatnonzero(np.isfinite(pmap) & (pmap <= cutoff))
expected_bh = int(r85["bh_candidates"])
if len(sig) != expected_bh:
    raise RuntimeError(
        f"BH candidate count mismatch reconstructed={len(sig)} receipt={expected_bh}"
    )

status(
    3,
    9,
    "BH candidate indexes reconstructed",
    bh_candidates=len(sig),
    threshold=cutoff,
)

source_v84c = design.get("source_v84c")
if not source_v84c:
    raise RuntimeError("TRIAL_DESIGN.json lacks source_v84c")
V84C = ROOT / "Research" / "Autonomous" / "guardian_edge_factory_v84c" / source_v84c
r84 = json.loads((V84C / "RUN_RECEIPT.json").read_text(encoding="utf-8"))
V83B = (
    ROOT
    / "Research"
    / "Autonomous"
    / "guardian_edge_factory_v83b"
    / r84["source_v83b"]
)
manifest = json.loads(
    (V83B / "REPAIRED_ARCHITECTURE_MANIFEST.json").read_text(encoding="utf-8")
)

# Read only the Parquet schema. Do not materialize 2013 target values.
target_columns = pq.ParquetFile(manifest["targets_5m_path"]).schema.names
target_names = [c for c in target_columns if "_fwd_" in str(c)]
if len(target_names) != nt:
    raise RuntimeError(
        f"Target-order mismatch schema={len(target_names)} frozen={nt}"
    )

family_names = catalog["family"].astype(str).to_numpy()
pair_i = pairs["feature_i"].to_numpy(dtype=np.int64)
pair_j = pairs["feature_j"].to_numpy(dtype=np.int64)

kind_counter = Counter()
target_counter = Counter()
family_counter = Counter()

single_sig = sig[sig < singleton_slots]
pair_sig = sig[sig >= singleton_slots]

if len(single_sig):
    block = 2 * nt
    single_fi = single_sig // block
    single_ti = single_sig % nt
    kind_counter["singleton"] = int(len(single_sig))
    for ti, count in enumerate(np.bincount(single_ti, minlength=nt)):
        if count:
            target_counter[target_names[ti]] += int(count)
    for fi, count in Counter(single_fi.tolist()).items():
        family_counter[family_names[int(fi)]] += int(count)

if len(pair_sig):
    off = pair_sig - singleton_slots
    pair_block = 4 * nt
    pair_index = off // pair_block
    pair_ti = off % nt
    kind_counter["pair"] = int(len(pair_sig))

    for ti, count in enumerate(np.bincount(pair_ti, minlength=nt)):
        if count:
            target_counter[target_names[ti]] += int(count)

    family_pair_counts = Counter()
    for pi, count in Counter(pair_index.tolist()).items():
        fi = pair_i[int(pi)]
        fj = pair_j[int(pi)]
        a = family_names[fi]
        b = family_names[fj]
        key = " × ".join(sorted((a, b)))
        family_pair_counts[key] += int(count)
    family_counter.update(family_pair_counts)

pd.DataFrame(
    family_counter.most_common(),
    columns=["family_combo", "bh_candidates"],
).to_csv(OUT / "BH_BY_FAMILY_COMBO.csv", index=False)

pd.DataFrame(
    target_counter.most_common(),
    columns=["target", "bh_candidates"],
).to_csv(OUT / "BH_BY_TARGET.csv", index=False)

pd.DataFrame(
    kind_counter.items(),
    columns=["kind", "bh_candidates"],
).to_csv(OUT / "BH_BY_KIND.csv", index=False)

status(
    4,
    9,
    "candidate concentration decoded",
    top_family=family_counter.most_common(1)[0] if family_counter else None,
    top_target=target_counter.most_common(1)[0] if target_counter else None,
)

state_meta = json.loads((V85 / "STATE_CACHE_META.json").read_text(encoding="utf-8"))
train_shape = tuple(state_meta["train_shape"])
ST = np.memmap(
    V85 / "STATE_TRAIN.bool.dat",
    mode="r",
    dtype=np.bool_,
    shape=train_shape,
)
if train_shape[0] != nf or train_shape[1] != 2:
    raise RuntimeError(f"Unexpected state-cache shape: {train_shape}")

state_groups = defaultdict(list)
for fi in range(nf):
    for st in range(2):
        h = hash_bool(ST[fi, st, :])
        state_groups[h].append((fi, st))

raw_states = nf * 2
unique_states = len(state_groups)
duplicate_excess = sum(len(v) - 1 for v in state_groups.values())
max_group = max((len(v) for v in state_groups.values()), default=0)

dup_rows = []
for h, members in state_groups.items():
    if len(members) <= 1:
        continue
    labels = [
        f"{catalog.iloc[fi]['feature']}::{('LO', 'HI')[st]}"
        for fi, st in members[:20]
    ]
    dup_rows.append(
        {
            "hash": h,
            "size": len(members),
            "members": " | ".join(labels),
        }
    )

dup_df = pd.DataFrame(dup_rows, columns=["hash", "size", "members"])
if not dup_df.empty:
    dup_df = dup_df.sort_values("size", ascending=False)
dup_df.to_csv(OUT / "EXACT_DUPLICATE_FEATURE_STATES.csv", index=False)

status(
    5,
    9,
    "exact feature-state duplication audited",
    raw_states=raw_states,
    unique_states=unique_states,
    duplicate_excess=duplicate_excess,
    max_duplicate_group=max_group,
)

sample_n = min(SAMPLE_PAIR_MASKS, len(pair_sig))
sample_trials = np.array([], dtype=np.int64)
if sample_n:
    sample_positions = np.linspace(
        0, len(pair_sig) - 1, sample_n, dtype=np.int64
    )
    sample_trials = pair_sig[sample_positions]

pair_mask_hashes = Counter()
for idx, trial in enumerate(sample_trials, start=1):
    off = int(trial) - singleton_slots
    pair_block = 4 * nt
    pi = off // pair_block
    rem = off % pair_block
    combo = rem // nt
    si = combo // 2
    sj = combo % 2
    fi = pair_i[pi]
    fj = pair_j[pi]

    mask = ST[fi, si, :] & ST[fj, sj, :]
    pair_mask_hashes[hash_bool(mask)] += 1

    if idx % 2000 == 0 or idx == len(sample_trials):
        status(
            6,
            9,
            f"pair-mask duplicate sample {idx}/{len(sample_trials)}",
            sampled=idx,
        )

unique_pair_masks = len(pair_mask_hashes)
sample_duplicate_fraction = (
    1.0 - unique_pair_masks / len(sample_trials)
    if len(sample_trials)
    else 0.0
)

# Profile p-value depth in chunks to avoid allocating a second ~170 MB array.
bins = np.array(
    [0.0, 1e-12, 1e-10, 1e-8, 1e-6, 1e-5, 1e-4, 1e-3, cutoff],
    dtype=np.float64,
)
hist_counts = np.zeros(len(bins) - 1, dtype=np.int64)
finite_tests = 0
below_1e6 = 0

for start in range(0, total_slots, PMAP_CHUNK):
    stop = min(start + PMAP_CHUNK, total_slots)
    chunk = np.asarray(pmap[start:stop])
    chunk = chunk[np.isfinite(chunk)]
    finite_tests += len(chunk)
    below_1e6 += int((chunk <= 1e-6).sum())
    for bi, (lo, hi) in enumerate(zip(bins[:-1], bins[1:])):
        hist_counts[bi] += int(((chunk > lo) & (chunk <= hi)).sum())

hist = pd.DataFrame(
    {
        "lo": bins[:-1],
        "hi": bins[1:],
        "count": hist_counts,
    }
)
hist.to_csv(OUT / "P_VALUE_DEPTH.csv", index=False)

if finite_tests != int(r85["valid_train_tests"]):
    raise RuntimeError(
        f"Finite-test mismatch reconstructed={finite_tests} receipt={r85['valid_train_tests']}"
    )

status(
    7,
    9,
    "p-value depth profiled",
    finite_tests=finite_tests,
    below_1e6=below_1e6,
)

top_families = family_counter.most_common(30)
top_targets = target_counter.most_common(30)

summary = {
    "run_id": RID,
    "status": "COMPLETE_V85_BH_EXPLOSION_DIAGNOSTIC",
    "source_v85": V85.name,
    "valid_tests": int(r85["valid_train_tests"]),
    "bh_candidates": len(sig),
    "bh_fraction": len(sig) / int(r85["valid_train_tests"]),
    "bh_threshold": cutoff,
    "raw_feature_states": raw_states,
    "unique_exact_feature_states": unique_states,
    "duplicate_feature_state_excess": duplicate_excess,
    "max_exact_feature_state_group": max_group,
    "pair_mask_sample_n": len(sample_trials),
    "pair_mask_sample_unique": unique_pair_masks,
    "pair_mask_sample_duplicate_fraction": sample_duplicate_fraction,
    "p_values_le_1e6": below_1e6,
    "top_family_combos": top_families,
    "top_targets": top_targets,
    "edge_trials": 0,
    "2013_holdout_values_accessed": False,
    "2014_plus_accessed": False,
    "2023_plus_accessed": False,
    "protected_2026_accessed": False,
    "next": "DESIGN_V85B_HIERARCHICAL_DEDUP_BLOCK_NULL_FROM_THIS_DIAGNOSTIC",
}
write_json(OUT / "RUN_RECEIPT.json", summary)

status(
    8,
    9,
    "diagnostic receipt written",
    bh_fraction=round(summary["bh_fraction"], 4),
    pair_mask_sample_duplicate_fraction=round(sample_duplicate_fraction, 4),
)
status(9, 9, "STOP; no holdout values or later periods touched")

print("\n=== V85A RECEIPT ===")
print(json.dumps(summary, indent=2))
print("\n=== TOP BH FAMILY COMBOS ===")
print(
    pd.DataFrame(
        top_families, columns=["family_combo", "bh_candidates"]
    ).to_string(index=False)
)
print("\n=== TOP BH TARGETS ===")
print(
    pd.DataFrame(
        top_targets, columns=["target", "bh_candidates"]
    ).to_string(index=False)
)
print("\nRUN:", OUT)
