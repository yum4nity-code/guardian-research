from pathlib import Path
import pandas as pd
import numpy as np
import json
import time
import math
from datetime import datetime
from scipy.stats import t as student_t

ROOT = Path(r"D:\MT5_Backtests")
RID = "GEF85B-" + pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT = ROOT / "Research" / "Autonomous" / "guardian_edge_factory_v85b" / RID
OUT.mkdir(parents=True, exist_ok=True)
T0 = time.time()

SAMPLE_PAIR_TARGET = 128
BLOCK_DAYS = 28
MIN_N = 120
MIN_BLOCKS = 12

def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")

def status(i, n, msg, **extra):
    e = time.time() - T0
    payload = {"run_id": RID, "step": i, "steps": n, "percent": round(100*i/n,1),
               "elapsed_s": round(e,1), "message": msg, **extra}
    write_json(OUT / "LIVE_STATUS.json", payload)
    tail = " | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF85B] {i}/{n} {100*i/n:.0f}% | elapsed {e:.1f}s | {msg}" +
          (f" | {tail}" if tail else ""), flush=True)

def naive_p(y):
    y = y[np.isfinite(y)]
    n = len(y)
    if n < MIN_N:
        return np.nan
    sd = float(np.std(y, ddof=1))
    if not np.isfinite(sd) or sd <= 0:
        return np.nan
    mean = float(np.mean(y))
    stat = mean / (sd / math.sqrt(n))
    return float(2 * student_t.sf(abs(stat), df=n-1))

def cluster_p(y, blocks):
    finite = np.isfinite(y)
    y = y[finite]
    b = blocks[finite]
    n = len(y)
    if n < MIN_N:
        return np.nan, n, 0
    uniq, inv = np.unique(b, return_inverse=True)
    g = len(uniq)
    if g < MIN_BLOCKS:
        return np.nan, n, g
    mean = float(np.mean(y))
    resid = y - mean
    u = np.bincount(inv, weights=resid)
    se2 = (g / (g - 1.0)) * float(np.sum(u*u)) / (n*n)
    if not np.isfinite(se2) or se2 <= 0:
        return np.nan, n, g
    stat = mean / math.sqrt(se2)
    p = float(2 * student_t.sf(abs(stat), df=g-1))
    return p, n, g

status(1, 9, "load V85/V85A frozen diagnostics; benchmark only")

v85a_runs = sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v85a").glob("GEF85A-*"))
v85a_runs = [p for p in v85a_runs if (p/"RUN_RECEIPT.json").exists()]
if not v85a_runs:
    raise RuntimeError("No completed V85A")
V85A = v85a_runs[-1]
r85a = json.loads((V85A/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r85a.get("status") != "COMPLETE_V85_BH_EXPLOSION_DIAGNOSTIC":
    raise RuntimeError("Latest V85A not complete")

V85 = ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v85"/r85a["source_v85"]
design = json.loads((V85/"TRIAL_DESIGN.json").read_text(encoding="utf-8"))
catalog = pd.read_csv(V85/"FROZEN_ELIGIBLE_FEATURES.csv")
pairs = pd.read_parquet(V85/"FROZEN_PAIR_UNIVERSE.parquet")
state_meta = json.loads((V85/"STATE_CACHE_META.json").read_text(encoding="utf-8"))

V84C = ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v84c"/design["source_v84c"]
r84 = json.loads((V84C/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V83B = ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v83b"/r84["source_v83b"]
manifest = json.loads((V83B/"REPAIRED_ARCHITECTURE_MANIFEST.json").read_text(encoding="utf-8"))

status(2, 9, "upstream frozen artifacts resolved",
       bh_fraction=round(float(r85a["bh_fraction"]),4),
       duplicate_feature_state_excess=int(r85a["duplicate_feature_state_excess"]),
       pair_mask_sample_duplicate_fraction=round(float(r85a["pair_mask_sample_duplicate_fraction"]),4))

F = pd.read_parquet(manifest["price_state_5m_path"])
F.index = pd.to_datetime(F.index)
train_full_times = F.index[F.index.year <= 2012]
bench_positions = np.flatnonzero(train_full_times.year <= 2011)
bench_times = train_full_times[bench_positions]
if len(bench_times) == 0 or bench_times.max() >= pd.Timestamp("2012-01-01"):
    raise RuntimeError("Benchmark time slice is not strictly 2010-2011")

target_path = manifest["targets_5m_path"]
try:
    Y = pd.read_parquet(
        target_path,
        filters=[("decision_time_utc", "<", datetime(2012,1,1))]
    )
except Exception as e:
    raise RuntimeError(
        "Refusing unfiltered target read. Parquet filter on decision_time_utc failed: " + repr(e)
    )
Y.index = pd.to_datetime(Y.index)
Y = Y.reindex(bench_times)
if len(Y) != len(bench_times) or Y.index.max() >= pd.Timestamp("2012-01-01"):
    raise RuntimeError("Filtered target slice alignment failed")

targets = [c for c in Y.columns if "_fwd_" in str(c)]
if len(targets) != int(design["targets"]):
    raise RuntimeError("Target count mismatch")

YA = np.array(Y[targets], dtype=np.float32, copy=True)
if not YA.flags.writeable:
    raise RuntimeError("YA must be writable before horizon masking")
minute = (bench_times.view("int64") // 60_000_000_000).astype(np.int64)
horizons = []
for ti, c in enumerate(targets):
    h = int(str(c).rsplit("_fwd_",1)[1].rstrip("m"))
    horizons.append(h)
    YA[(minute % h) != 0, ti] = np.nan

origin = pd.Timestamp("2010-01-01")
block_ids = ((bench_times.normalize() - origin).days.to_numpy() // BLOCK_DAYS).astype(np.int32)
status(3, 9, "2010-2011 target slice loaded with 28-day blocks",
       rows=len(bench_times), targets=len(targets), blocks=int(np.unique(block_ids).size))

shape = tuple(state_meta["train_shape"])
ST = np.memmap(V85/"STATE_TRAIN.bool.dat", mode="r", dtype=np.bool_, shape=shape)
if shape[0] != len(catalog) or shape[1] != 2:
    raise RuntimeError("State cache shape mismatch")

pair_i = pairs["feature_i"].to_numpy(dtype=np.int64)
pair_j = pairs["feature_j"].to_numpy(dtype=np.int64)
families = catalog["family"].astype(str).to_numpy()

family_pairs = {}
for pi in range(len(pairs)):
    fi = pair_i[pi]
    fj = pair_j[pi]
    key = " × ".join(sorted((families[fi], families[fj])))
    family_pairs.setdefault(key, []).append(pi)

keys = sorted(family_pairs)
sample_pair_indices = []
if len(keys) <= SAMPLE_PAIR_TARGET:
    for key in keys:
        vals = family_pairs[key]
        sample_pair_indices.append(vals[len(vals)//2])
else:
    pos = np.linspace(0, len(keys)-1, SAMPLE_PAIR_TARGET, dtype=int)
    for kpos in pos:
        vals = family_pairs[keys[kpos]]
        sample_pair_indices.append(vals[len(vals)//2])

sample_pair_indices = sorted(set(sample_pair_indices))
status(4, 9, "deterministic stratified pair sample frozen",
       family_combos=len(keys), benchmark_pairs=len(sample_pair_indices))

records = []
tbench = time.time()
for done, pi in enumerate(sample_pair_indices, start=1):
    fi = pair_i[pi]
    fj = pair_j[pi]
    for si in range(2):
        for sj in range(2):
            mask = ST[fi, si, bench_positions] & ST[fj, sj, bench_positions]
            idx = np.flatnonzero(mask)
            if len(idx) < MIN_N:
                continue
            b = block_ids[idx]
            vals = YA[idx, :]
            for ti in range(len(targets)):
                y = vals[:, ti]
                p0 = naive_p(y)
                pb, nobs, g = cluster_p(y, b)
                if np.isfinite(p0) or np.isfinite(pb):
                    records.append({
                        "pair_i": int(pi),
                        "family_i": families[fi],
                        "family_j": families[fj],
                        "state_i": si,
                        "state_j": sj,
                        "target": targets[ti],
                        "n": int(nobs),
                        "blocks": int(g),
                        "p_naive": p0,
                        "p_block28d": pb
                    })
    if done == 1 or done == len(sample_pair_indices) or done % 16 == 0:
        elapsed = time.time() - tbench
        rate = done / max(elapsed, 1e-9)
        eta = (len(sample_pair_indices)-done) / max(rate, 1e-9)
        status(5, 9, f"block-null benchmark {done}/{len(sample_pair_indices)}",
               pair_progress=f"{done}/{len(sample_pair_indices)}",
               pairs_per_s=round(rate,3), eta_s=round(eta,1))

R = pd.DataFrame(records)
R.to_csv(OUT/"BLOCK_NULL_BENCHMARK_RESULTS.csv", index=False)
if R.empty:
    raise RuntimeError("Block-null benchmark produced no valid tests")

both = R[np.isfinite(R["p_naive"]) & np.isfinite(R["p_block28d"])].copy()
naive_sig = int((both["p_naive"] <= .05).sum())
block_sig = int((both["p_block28d"] <= .05).sum())
deep_naive = int((both["p_naive"] <= 1e-6).sum())
deep_block = int((both["p_block28d"] <= 1e-6).sum())
collapse = 1.0 - block_sig / max(1, naive_sig)

status(6, 9, "naive-vs-block significance compared",
       comparable_tests=len(both), naive_p05=naive_sig, block_p05=block_sig,
       collapse_fraction=round(collapse,4))

bench_seconds = time.time() - tbench
pair_rate = len(sample_pair_indices) / max(bench_seconds, 1e-9)
projected_full_minutes = len(pairs) / max(pair_rate, 1e-9) / 60.0

by_family = both.groupby(["family_i","family_j"]).agg(
    tests=("p_naive","size"),
    naive_p05=("p_naive", lambda s: int((s<=.05).sum())),
    block_p05=("p_block28d", lambda s: int((s<=.05).sum()))
).reset_index()
by_family.to_csv(OUT/"BLOCK_NULL_BY_FAMILY.csv", index=False)

status(7, 9, "runtime projection complete",
       benchmark_seconds=round(bench_seconds,1),
       projected_full_minutes=round(projected_full_minutes,1))

decision = (
    "REBUILD_FULL_DISCOVERY_WITH_BLOCK_CLUSTER_INFERENCE"
    if collapse >= .25 or deep_block < deep_naive
    else "BLOCK_EFFECT_MODEST_BUT_STILL_REQUIRE_HIERARCHICAL_DEDUP"
)

receipt = {
    "run_id": RID,
    "status": "COMPLETE_BLOCK_NULL_BENCHMARK",
    "source_v85a": V85A.name,
    "source_v85": V85.name,
    "period_used": "2010-2011 only",
    "2012_values_accessed": False,
    "2013_values_accessed": False,
    "2014_plus_accessed": False,
    "benchmark_pairs": len(sample_pair_indices),
    "comparable_tests": len(both),
    "naive_p_le_05": naive_sig,
    "block28d_p_le_05": block_sig,
    "naive_p_le_1e6": deep_naive,
    "block28d_p_le_1e6": deep_block,
    "significance_collapse_fraction": collapse,
    "pairs_per_second": pair_rate,
    "projected_full_minutes": projected_full_minutes,
    "v85a_bh_fraction": float(r85a["bh_fraction"]),
    "v85a_exact_state_duplicate_excess": int(r85a["duplicate_feature_state_excess"]),
    "v85a_pair_mask_sample_duplicate_fraction": float(r85a["pair_mask_sample_duplicate_fraction"]),
    "edge_trials": 0,
    "decision": decision,
    "next": "V86_BLOCK_CLUSTER_HIERARCHICAL_DISCOVERY_BENCHMARK_OR_FULL_ENGINE"
}
write_json(OUT/"RUN_RECEIPT.json", receipt)
status(8, 9, "receipt written", decision=decision)
status(9, 9, "STOP; no 2012/2013/later target values touched")

print("\n=== V85B RECEIPT ===")
print(json.dumps(receipt, indent=2))
print("\n=== BLOCK NULL BY FAMILY ===")
print(by_family.sort_values(["block_p05","tests"], ascending=False).head(40).to_string(index=False))
print("\nRUN:", OUT)
