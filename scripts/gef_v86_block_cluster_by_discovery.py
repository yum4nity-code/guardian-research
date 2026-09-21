from pathlib import Path
import pandas as pd
import numpy as np
import json
import time
import math
import hashlib
from datetime import datetime
from scipy.stats import t as student_t

ROOT = Path(r"D:\MT5_Backtests")
BASE = ROOT / "Research" / "Autonomous" / "guardian_edge_factory_v86"
BASE.mkdir(parents=True, exist_ok=True)

ENGINE_VERSION = "V86.0"
TRAIN_END = datetime(2013, 1, 1)
HOLD_START = datetime(2013, 1, 1)
HOLD_END = datetime(2014, 1, 1)
BLOCK_DAYS = 28
MIN_TRAIN_N = 120
MIN_TRAIN_BLOCKS = 12
MIN_HOLD_N = 40
MIN_HOLD_BLOCKS = 10
TRAIN_BY_Q = 0.05
HOLD_BY_Q = 0.10
CHECKPOINT_PAIRS = 256
STATUS_SECONDS = 45.0
MAX_FROZEN_CANDIDATES = 50000
PMAP_CHUNK = 1_000_000
STATE_NAMES = ("LO", "HI")


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def status(out, stage, message, **extra):
    payload = {
        "engine_version": ENGINE_VERSION,
        "stage": stage,
        "timestamp_utc": pd.Timestamp.now("UTC").isoformat(),
        "message": message,
        **extra,
    }
    write_json(out / "LIVE_STATUS.json", payload)
    tail = " | ".join(f"{k}={v}" for k, v in extra.items())
    print(f"[GEF86] {stage} | {message}" + (f" | {tail}" if tail else ""), flush=True)


def harmonic_number_approx(m):
    if m <= 0:
        return np.nan
    x = float(m)
    return math.log(x) + 0.5772156649015329 + 1.0/(2.0*x) - 1.0/(12.0*x*x)


def by_threshold(pmap, q):
    arr = np.asarray(pmap)
    finite = np.isfinite(arr)
    m = int(finite.sum())
    if m == 0:
        return np.nan, 0, 0, np.nan
    ps = np.array(arr[finite], dtype=np.float32, copy=True)
    ps.sort()
    cm = harmonic_number_approx(m)
    chunk = 1_000_000
    last_k = 0
    for start in range(0, m, chunk):
        stop = min(start + chunk, m)
        ranks = np.arange(start + 1, stop + 1, dtype=np.float64)
        crit = q * ranks / (float(m) * cm)
        ok = ps[start:stop].astype(np.float64) <= crit
        if ok.any():
            last_k = start + int(np.flatnonzero(ok)[-1]) + 1
    if last_k == 0:
        return np.nan, m, 0, cm
    return float(ps[last_k - 1]), m, last_k, cm


def by_threshold_array(pvalues, q):
    p = np.asarray(pvalues, dtype=np.float64)
    if p.ndim != 1:
        raise RuntimeError("BY p-value array must be one-dimensional")
    m = len(p)
    if m == 0:
        return np.nan, 0, np.nan
    ps = np.sort(p)
    cm = harmonic_number_approx(m)
    ranks = np.arange(1, m + 1, dtype=np.float64)
    ok = ps <= (q * ranks / (float(m) * cm))
    if not ok.any():
        return np.nan, 0, cm
    k = int(np.flatnonzero(ok)[-1]) + 1
    return float(ps[k-1]), k, cm


def cluster_matrix_stats(mask, y, block_ids):
    idx = np.flatnonzero(mask)
    tcount = y.shape[1]
    n = np.zeros(tcount, dtype=np.int32)
    blocks_used = np.zeros(tcount, dtype=np.int16)
    mean = np.full(tcount, np.nan, dtype=np.float64)
    p = np.full(tcount, np.nan, dtype=np.float32)

    if len(idx) == 0:
        return n, blocks_used, mean, p

    vals = y[idx, :]
    finite = np.isfinite(vals)
    n = finite.sum(axis=0).astype(np.int32)

    b = block_ids[idx]
    starts = np.r_[0, np.flatnonzero(b[1:] != b[:-1]) + 1]
    vals0 = np.where(finite, vals, 0.0)
    block_sums = np.add.reduceat(vals0, starts, axis=0).astype(np.float64)
    block_counts = np.add.reduceat(finite.astype(np.int16), starts, axis=0).astype(np.float64)

    nn = n.astype(np.float64)
    sums = block_sums.sum(axis=0)
    mean = np.divide(sums, nn, out=np.full(tcount, np.nan), where=nn > 0)

    g = (block_counts > 0).sum(axis=0).astype(np.int16)
    blocks_used[:] = g
    u = block_sums - block_counts * mean
    meat = (u * u).sum(axis=0)

    good = (
        (n >= MIN_TRAIN_N)
        & (g >= MIN_TRAIN_BLOCKS)
        & np.isfinite(mean)
        & (meat > 0)
    )
    if good.any():
        gg = g.astype(np.float64)
        se2 = np.full(tcount, np.nan, dtype=np.float64)
        se2[good] = (
            (gg[good] / (gg[good] - 1.0))
            * meat[good]
            / (nn[good] * nn[good])
        )
        good = good & np.isfinite(se2) & (se2 > 0)
        stat = np.zeros(tcount, dtype=np.float64)
        stat[good] = mean[good] / np.sqrt(se2[good])
        pv = np.full(tcount, np.nan, dtype=np.float64)
        pv[good] = 2.0 * student_t.sf(np.abs(stat[good]), df=g[good]-1)
        p[good] = pv[good].astype(np.float32)

    return n, blocks_used, mean, p


def cluster_scalar_stats(mask, y, block_ids, min_n, min_blocks):
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        return {"n": 0, "blocks": 0, "mean": np.nan, "p_two": np.nan}

    vals = y[idx]
    b = block_ids[idx]
    finite = np.isfinite(vals)
    vals = vals[finite]
    b = b[finite]
    n = len(vals)
    if n < min_n:
        return {"n": n, "blocks": 0, "mean": float(np.mean(vals)) if n else np.nan, "p_two": np.nan}

    starts = np.r_[0, np.flatnonzero(b[1:] != b[:-1]) + 1]
    block_sums = np.add.reduceat(vals.astype(np.float64), starts)
    block_counts = np.diff(np.r_[starts, len(vals)]).astype(np.float64)
    g = len(starts)
    mean = float(np.mean(vals))

    if g < min_blocks:
        return {"n": n, "blocks": g, "mean": mean, "p_two": np.nan}

    u = block_sums - block_counts * mean
    meat = float(np.sum(u*u))
    if not np.isfinite(meat) or meat <= 0:
        return {"n": n, "blocks": g, "mean": mean, "p_two": np.nan}

    se2 = (g / (g - 1.0)) * meat / (n*n)
    if not np.isfinite(se2) or se2 <= 0:
        return {"n": n, "blocks": g, "mean": mean, "p_two": np.nan}

    stat = mean / math.sqrt(se2)
    p = float(2.0 * student_t.sf(abs(stat), df=g-1))
    return {"n": n, "blocks": g, "mean": mean, "p_two": p}


def decode_trial(trial_idx, singleton_slots, tcount, pair_i, pair_j):
    if trial_idx < singleton_slots:
        block = 2 * tcount
        fi = trial_idx // block
        rem = trial_idx % block
        si = rem // tcount
        ti = rem % tcount
        return {
            "kind": "singleton",
            "feature_i": int(fi),
            "feature_j": None,
            "state_i": int(si),
            "state_j": None,
            "target_i": int(ti),
        }

    off = trial_idx - singleton_slots
    block = 4 * tcount
    pi = off // block
    rem = off % block
    combo = rem // tcount
    ti = rem % tcount
    return {
        "kind": "pair",
        "pair_i": int(pi),
        "feature_i": int(pair_i[int(pi)]),
        "feature_j": int(pair_j[int(pi)]),
        "state_i": int(combo // 2),
        "state_j": int(combo % 2),
        "target_i": int(ti),
    }


def condition_mask(decoded, states):
    fi = decoded["feature_i"]
    si = decoded["state_i"]
    if decoded["kind"] == "singleton":
        return states[fi, si, :]
    fj = decoded["feature_j"]
    sj = decoded["state_j"]
    return states[fi, si, :] & states[fj, sj, :]


def mask_hash(mask):
    return hashlib.blake2b(
        np.packbits(np.asarray(mask, dtype=np.bool_)).tobytes(),
        digest_size=16,
    ).hexdigest()


# ---------------- upstream freeze ----------------
status_dummy = None
v85b_runs = sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v85b").glob("GEF85B-*"))
v85b_runs = [p for p in v85b_runs if (p/"RUN_RECEIPT.json").exists()]
if not v85b_runs:
    raise RuntimeError("No completed V85B benchmark")
V85B = v85b_runs[-1]
r85b = json.loads((V85B/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r85b.get("status") != "COMPLETE_BLOCK_NULL_BENCHMARK":
    raise RuntimeError("Latest V85B is not complete")
if r85b.get("decision") != "REBUILD_FULL_DISCOVERY_WITH_BLOCK_CLUSTER_INFERENCE":
    raise RuntimeError("V85B did not authorize block-cluster rebuild")
if r85b.get("2012_values_accessed") or r85b.get("2013_values_accessed") or r85b.get("2014_plus_accessed"):
    raise RuntimeError("V85B access assertions violated")

V85 = ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v85"/r85b["source_v85"]
design = json.loads((V85/"TRIAL_DESIGN.json").read_text(encoding="utf-8"))
catalog = pd.read_csv(V85/"FROZEN_ELIGIBLE_FEATURES.csv").reset_index(drop=True)
pairs = pd.read_parquet(V85/"FROZEN_PAIR_UNIVERSE.parquet")
state_meta = json.loads((V85/"STATE_CACHE_META.json").read_text(encoding="utf-8"))

V84C = ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v84c"/design["source_v84c"]
r84 = json.loads((V84C/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V83B = ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v83b"/r84["source_v83b"]
manifest = json.loads((V83B/"REPAIRED_ARCHITECTURE_MANIFEST.json").read_text(encoding="utf-8"))

nf = len(catalog)
nt = int(design["targets"])
singleton_slots = int(design["singleton_slots"])
pair_slots = int(design["pair_slots"])
total_slots = int(design["predeclared_trial_slots"])
pair_i = pairs["feature_i"].to_numpy(dtype=np.int64)
pair_j = pairs["feature_j"].to_numpy(dtype=np.int64)

if len(pairs) != int(design["cross_family_pairs"]):
    raise RuntimeError("Frozen pair-universe size mismatch")
if nf != int(design["features"]):
    raise RuntimeError("Frozen feature count mismatch")

catalog_hash = str(design["catalog_hash"])
current_path = BASE/"CURRENT_RUN.json"
resume = False

if current_path.exists():
    current = json.loads(current_path.read_text(encoding="utf-8"))
    same = (
        current.get("engine_version") == ENGINE_VERSION
        and current.get("source_v85b") == V85B.name
        and current.get("catalog_hash") == catalog_hash
    )
    if same and current.get("status") == "RUNNING":
        OUT = BASE/current["run_id"]
        resume = True
    elif same and current.get("status") == "COMPLETE":
        OUT = BASE/current["run_id"]
        print("=== GEF V86 ALREADY COMPLETE ===")
        print((OUT/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
        raise SystemExit(0)

if not resume:
    run_id = "GEF86-" + pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    OUT = BASE/run_id
    OUT.mkdir(parents=True, exist_ok=False)
    write_json(current_path, {
        "engine_version": ENGINE_VERSION,
        "run_id": run_id,
        "source_v85b": V85B.name,
        "catalog_hash": catalog_hash,
        "status": "RUNNING",
    })
else:
    run_id = OUT.name

status(
    OUT, "1/13",
    "frozen V85 universe + V85B block-cluster decision loaded" + (" (RESUME)" if resume else ""),
    run_id=run_id,
    features=nf,
    pairs=len(pairs),
    total_slots=total_slots,
)

# ---------------- train targets only: 2010-2012 ----------------
F = pd.read_parquet(manifest["price_state_5m_path"])
F.index = pd.to_datetime(F.index)
train_times = F.index[F.index < pd.Timestamp(TRAIN_END)]
if len(train_times) != tuple(state_meta["train_shape"])[2]:
    raise RuntimeError("Train state cache and train time grid length mismatch")

target_path = manifest["targets_5m_path"]
try:
    YTdf = pd.read_parquet(
        target_path,
        filters=[("decision_time_utc", "<", TRAIN_END)],
    )
except Exception as e:
    raise RuntimeError(
        "Refusing unfiltered train-target read; Parquet filter failed: " + repr(e)
    )

YTdf.index = pd.to_datetime(YTdf.index)
YTdf = YTdf.reindex(train_times)
if len(YTdf) != len(train_times) or YTdf.index.max() >= pd.Timestamp(TRAIN_END):
    raise RuntimeError("Train-target alignment failed")

targets = [c for c in YTdf.columns if "_fwd_" in str(c)]
if len(targets) != nt:
    raise RuntimeError(f"Target count mismatch frozen={nt} actual={len(targets)}")

YT = np.array(YTdf[targets], dtype=np.float32, copy=True)
if not YT.flags.writeable:
    raise RuntimeError("Train target matrix unexpectedly read-only")

train_minute = (train_times.view("int64") // 60_000_000_000).astype(np.int64)
horizons = []
for ti, c in enumerate(targets):
    h = int(str(c).rsplit("_fwd_", 1)[1].rstrip("m"))
    horizons.append(h)
    YT[(train_minute % h) != 0, ti] = np.nan

train_origin = pd.Timestamp("2010-01-01")
train_blocks = ((train_times.normalize() - train_origin).days.to_numpy() // BLOCK_DAYS).astype(np.int16)

status(
    OUT, "2/13",
    "2010-2012 train targets loaded and non-overlap grid frozen",
    rows=len(train_times),
    targets=nt,
    blocks=int(np.unique(train_blocks).size),
    target_values_2013_accessed=False,
)

# ---------------- frozen states ----------------
train_shape = tuple(state_meta["train_shape"])
hold_shape = tuple(state_meta["hold_shape"])
ST = np.memmap(V85/"STATE_TRAIN.bool.dat", mode="r", dtype=np.bool_, shape=train_shape)
SH = np.memmap(V85/"STATE_HOLD.bool.dat", mode="r", dtype=np.bool_, shape=hold_shape)
if train_shape[0] != nf or train_shape[1] != 2:
    raise RuntimeError("Train state cache shape mismatch")
if hold_shape[0] != nf or hold_shape[1] != 2:
    raise RuntimeError("Holdout state cache shape mismatch")

spec = {
    "engine_version": ENGINE_VERSION,
    "source_v85b": V85B.name,
    "source_v85": V85.name,
    "train_period": "2010-2012",
    "holdout_period": "2013 only, unopened until train selection freezes",
    "block_days": BLOCK_DAYS,
    "train_inference": "28-day cluster-robust intercept test",
    "train_multiplicity": f"global Benjamini-Yekutieli q={TRAIN_BY_Q} across all finite raw tests",
    "exact_candidate_dedup": "condition-mask + target after train BY; keep smallest train p",
    "holdout_inference": "same-direction one-sided 28-day cluster-robust test",
    "holdout_multiplicity": f"Benjamini-Yekutieli q={HOLD_BY_Q} across frozen unique hypotheses",
    "singleton_slots": singleton_slots,
    "pair_slots": pair_slots,
    "predeclared_trial_slots": total_slots,
    "2013_target_values_accessed_at_freeze": False,
    "2014_plus_accessed": False,
}
write_json(OUT/"FROZEN_V86_SPEC.json", spec)
status(OUT, "3/13", "V86 inference and multiplicity specification frozen", train_by_q=TRAIN_BY_Q, hold_by_q=HOLD_BY_Q)

# ---------------- p-value ledger / resume ----------------
p_path = OUT/"TRAIN_BLOCK_PVALUES.float32.dat"
checkpoint_path = OUT/"CHECKPOINT.json"

if checkpoint_path.exists():
    cp = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    if cp.get("catalog_hash") != catalog_hash or int(cp.get("total_slots", -1)) != total_slots:
        raise RuntimeError("V86 checkpoint does not match frozen universe")
    pmap = np.memmap(p_path, mode="r+", dtype=np.float32, shape=(total_slots,))
    singleton_done = bool(cp.get("singleton_done", False))
    next_pair = int(cp.get("next_pair", 0))
    valid_tests = int(cp.get("valid_tests", 0))
    status(OUT, "4/13", "checkpoint loaded", singleton_done=singleton_done, next_pair=next_pair, valid_tests=valid_tests)
else:
    pmap = np.memmap(p_path, mode="w+", dtype=np.float32, shape=(total_slots,))
    pmap[:] = np.nan
    pmap.flush()
    singleton_done = False
    next_pair = 0
    valid_tests = 0
    write_json(checkpoint_path, {
        "catalog_hash": catalog_hash,
        "total_slots": total_slots,
        "singleton_done": False,
        "next_pair": 0,
        "valid_tests": 0,
        "status": "RUNNING",
    })
    status(OUT, "4/13", "fresh block-cluster p-value ledger initialized", slots=total_slots)

# ---------------- singleton scan ----------------
if not singleton_done:
    t0 = time.time()
    for fi in range(nf):
        for si in range(2):
            _, _, _, pv = cluster_matrix_stats(ST[fi, si, :], YT, train_blocks)
            base = fi * 2 * nt + si * nt
            pmap[base:base+nt] = pv
            valid_tests += int(np.isfinite(pv).sum())

        done = fi + 1
        if done == 1 or done == nf or done % 20 == 0:
            elapsed = time.time() - t0
            rate = done / max(elapsed, 1e-9)
            eta = (nf-done) / max(rate, 1e-9)
            status(
                OUT, "5/13", f"singleton block scan {done}/{nf}",
                percent=round(100*done/nf,1),
                elapsed_min=round(elapsed/60,1),
                eta_min=round(eta/60,1),
                valid_tests=valid_tests,
            )

    pmap.flush()
    singleton_done = True
    write_json(checkpoint_path, {
        "catalog_hash": catalog_hash,
        "total_slots": total_slots,
        "singleton_done": True,
        "next_pair": next_pair,
        "valid_tests": valid_tests,
        "status": "RUNNING",
    })

# ---------------- pair scan ----------------
scan_start = time.time()
last_status = scan_start
start_pair = next_pair

for pi in range(start_pair, len(pairs)):
    fi = int(pair_i[pi])
    fj = int(pair_j[pi])
    combo = 0

    for si in range(2):
        for sj in range(2):
            mask = ST[fi, si, :] & ST[fj, sj, :]
            _, _, _, pv = cluster_matrix_stats(mask, YT, train_blocks)
            base = singleton_slots + pi * 4 * nt + combo * nt
            pmap[base:base+nt] = pv
            valid_tests += int(np.isfinite(pv).sum())
            combo += 1

    done_pairs = pi + 1
    now = time.time()
    do_checkpoint = (
        done_pairs == len(pairs)
        or done_pairs % CHECKPOINT_PAIRS == 0
    )

    if do_checkpoint:
        pmap.flush()
        write_json(checkpoint_path, {
            "catalog_hash": catalog_hash,
            "total_slots": total_slots,
            "singleton_done": True,
            "next_pair": done_pairs,
            "valid_tests": valid_tests,
            "status": "RUNNING",
        })

    if do_checkpoint or (now-last_status) >= STATUS_SECONDS:
        elapsed = now - scan_start
        processed = done_pairs - start_pair
        rate = processed / max(elapsed, 1e-9)
        eta = (len(pairs)-done_pairs) / max(rate, 1e-9) if processed else np.nan
        status(
            OUT, "6/13", f"pair block scan {done_pairs}/{len(pairs)}",
            percent=round(100*done_pairs/len(pairs),2),
            pairs_per_s=round(rate,3),
            elapsed_min=round(elapsed/60,1),
            eta_min=round(eta/60,1) if np.isfinite(eta) else None,
            valid_tests=valid_tests,
        )
        last_status = now

pmap.flush()
write_json(checkpoint_path, {
    "catalog_hash": catalog_hash,
    "total_slots": total_slots,
    "singleton_done": True,
    "next_pair": len(pairs),
    "valid_tests": valid_tests,
    "status": "TRAIN_SCAN_COMPLETE",
})

status(
    OUT, "7/13",
    "full block-cluster discovery scan complete; computing global BY",
    valid_tests=valid_tests,
)

# ---------------- global BY ----------------
cutoff, finite_tests, by_k, by_cm = by_threshold(pmap, TRAIN_BY_Q)
valid_tests = finite_tests

if np.isfinite(cutoff):
    arr = np.asarray(pmap)
    candidate_idx = np.flatnonzero(np.isfinite(arr) & (arr <= cutoff))
else:
    candidate_idx = np.array([], dtype=np.int64)

status(
    OUT, "8/13",
    "global train BY complete",
    by_q=TRAIN_BY_Q,
    harmonic_factor=round(by_cm,4) if np.isfinite(by_cm) else None,
    by_threshold=cutoff if np.isfinite(cutoff) else None,
    by_rank_k=by_k,
    raw_candidates=len(candidate_idx),
)

# ---------------- exact candidate dedup and train effect ----------------
train_rows = []
seen = {}
t_candidates = time.time()

for ci, trial_idx in enumerate(candidate_idx, start=1):
    decoded = decode_trial(int(trial_idx), singleton_slots, nt, pair_i, pair_j)
    ti = decoded["target_i"]
    mask = condition_mask(decoded, ST)
    tr = cluster_scalar_stats(mask, YT[:, ti], train_blocks, MIN_TRAIN_N, MIN_TRAIN_BLOCKS)

    if not np.isfinite(tr["mean"]) or not np.isfinite(tr["p_two"]) or tr["mean"] == 0:
        continue

    direction = 1 if tr["mean"] > 0 else -1
    key = (mask_hash(mask), int(ti), int(direction))
    p_train = float(pmap[int(trial_idx)])

    row = {
        "trial_index": int(trial_idx),
        "kind": decoded["kind"],
        "feature_i": str(catalog.loc[decoded["feature_i"], "feature"]),
        "family_i": str(catalog.loc[decoded["feature_i"], "family"]),
        "state_i": STATE_NAMES[decoded["state_i"]],
        "feature_j": None,
        "family_j": None,
        "state_j": None,
        "target_i": int(ti),
        "target": targets[ti],
        "horizon_min": horizons[ti],
        "direction": int(direction),
        "train_n": int(tr["n"]),
        "train_blocks": int(tr["blocks"]),
        "train_mean_bp": float(tr["mean"]*1e4),
        "train_p_two": p_train,
        "condition_hash": key[0],
        "duplicate_aliases": 1,
    }

    if decoded["kind"] == "pair":
        row["feature_j"] = str(catalog.loc[decoded["feature_j"], "feature"])
        row["family_j"] = str(catalog.loc[decoded["feature_j"], "family"])
        row["state_j"] = STATE_NAMES[decoded["state_j"]]

    if key not in seen:
        seen[key] = row
    else:
        seen[key]["duplicate_aliases"] += 1
        if p_train < seen[key]["train_p_two"]:
            aliases = seen[key]["duplicate_aliases"]
            row["duplicate_aliases"] = aliases
            seen[key] = row

    if ci == 1 or ci == len(candidate_idx) or ci % 500 == 0:
        elapsed = time.time() - t_candidates
        rate = ci / max(elapsed, 1e-9)
        eta = (len(candidate_idx)-ci) / max(rate, 1e-9)
        status(
            OUT, "9/13", f"train candidate dedup {ci}/{len(candidate_idx)}",
            percent=round(100*ci/max(1,len(candidate_idx)),1),
            unique_candidates=len(seen),
            eta_s=round(eta,1),
        )

frozen = pd.DataFrame(list(seen.values()))
if len(frozen):
    frozen = frozen.sort_values(["train_p_two", "trial_index"], kind="mergesort").reset_index(drop=True)
frozen.to_csv(OUT/"FROZEN_TRAIN_BY_CANDIDATES.csv", index=False)

if len(frozen) > MAX_FROZEN_CANDIDATES:
    receipt = {
        "run_id": run_id,
        "status": "STOP_TOO_MANY_BLOCK_BY_CANDIDATES",
        "source_v85b": V85B.name,
        "valid_train_tests": valid_tests,
        "train_by_q": TRAIN_BY_Q,
        "train_by_threshold": cutoff if np.isfinite(cutoff) else None,
        "raw_train_by_candidates": len(candidate_idx),
        "unique_train_by_candidates": len(frozen),
        "2013_target_values_accessed": False,
        "2014_plus_accessed": False,
        "next": "V86A_HIERARCHICAL_FAMILY_NULL_BEFORE_2013",
    }
    write_json(OUT/"RUN_RECEIPT.json", receipt)
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current["status"] = "COMPLETE"
    write_json(current_path, current)
    status(OUT, "13/13", "SAFETY STOP before 2013; too many unique train BY candidates", candidates=len(frozen))
    print("\n=== V86 RECEIPT ===")
    print(json.dumps(receipt, indent=2))
    print("\nRUN:", OUT)
    raise SystemExit(0)

status(
    OUT, "10/13",
    "train hypotheses frozen; 2013 target values still unopened",
    raw_candidates=len(candidate_idx),
    unique_candidates=len(frozen),
)

# If train BY found nothing, finish without touching 2013.
if frozen.empty:
    receipt = {
        "run_id": run_id,
        "status": "COMPLETE_NO_TRAIN_BY_SURVIVORS",
        "source_v85b": V85B.name,
        "valid_train_tests": valid_tests,
        "train_by_q": TRAIN_BY_Q,
        "train_by_threshold": None,
        "raw_train_by_candidates": 0,
        "unique_train_by_candidates": 0,
        "2013_target_values_accessed": False,
        "2014_plus_accessed": False,
        "next": "NO_SURVIVOR_REVIEW_HIERARCHICAL_BLOCK_NULL_ARCHITECTURE",
    }
    write_json(OUT/"RUN_RECEIPT.json", receipt)
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current["status"] = "COMPLETE"
    write_json(current_path, current)
    status(OUT, "13/13", "DONE; global block-BY found no train survivor; 2013 untouched")
    print("\n=== V86 RECEIPT ===")
    print(json.dumps(receipt, indent=2))
    print("\nRUN:", OUT)
    raise SystemExit(0)

# ---------------- only now open 2013 targets ----------------
try:
    YHdf = pd.read_parquet(
        target_path,
        filters=[
            ("decision_time_utc", ">=", HOLD_START),
            ("decision_time_utc", "<", HOLD_END),
        ],
    )
except Exception as e:
    raise RuntimeError(
        "2013 hypotheses were frozen, but filtered 2013 target read failed: " + repr(e)
    )

hold_times = F.index[(F.index >= pd.Timestamp(HOLD_START)) & (F.index < pd.Timestamp(HOLD_END))]
if len(hold_times) != hold_shape[2]:
    raise RuntimeError("Holdout state cache and 2013 time grid length mismatch")

YHdf.index = pd.to_datetime(YHdf.index)
YHdf = YHdf.reindex(hold_times)
if (
    len(YHdf) != len(hold_times)
    or YHdf.index.min() < pd.Timestamp(HOLD_START)
    or YHdf.index.max() >= pd.Timestamp(HOLD_END)
):
    raise RuntimeError("2013 target alignment failed")

YH = np.array(YHdf[targets], dtype=np.float32, copy=True)
if not YH.flags.writeable:
    raise RuntimeError("2013 target matrix unexpectedly read-only")

hold_minute = (hold_times.view("int64") // 60_000_000_000).astype(np.int64)
for ti, h in enumerate(horizons):
    YH[(hold_minute % h) != 0, ti] = np.nan

hold_origin = pd.Timestamp("2013-01-01")
hold_blocks = ((hold_times.normalize() - hold_origin).days.to_numpy() // BLOCK_DAYS).astype(np.int16)

status(
    OUT, "11/13",
    "2013 holdout values opened only after train freeze",
    rows=len(hold_times),
    blocks=int(np.unique(hold_blocks).size),
    frozen_hypotheses=len(frozen),
)

# ---------------- 2013 confirmatory evaluation ----------------
hold_rows = []
hold_p = np.ones(len(frozen), dtype=np.float64)
t_hold = time.time()

for ci, row in enumerate(frozen.itertuples(index=False), start=1):
    trial_idx = int(row.trial_index)
    decoded = decode_trial(trial_idx, singleton_slots, nt, pair_i, pair_j)
    ti = int(row.target_i)
    mask = condition_mask(decoded, SH)
    ho = cluster_scalar_stats(mask, YH[:, ti], hold_blocks, MIN_HOLD_N, MIN_HOLD_BLOCKS)

    same_sign = bool(
        np.isfinite(ho["mean"])
        and ho["mean"] != 0
        and int(np.sign(ho["mean"])) == int(row.direction)
    )

    if same_sign and np.isfinite(ho["p_two"]):
        p_one = float(ho["p_two"] / 2.0)
    else:
        p_one = 1.0

    hold_p[ci-1] = p_one
    hold_rows.append({
        "trial_index": trial_idx,
        "condition_hash": row.condition_hash,
        "target": row.target,
        "direction": int(row.direction),
        "train_n": int(row.train_n),
        "train_blocks": int(row.train_blocks),
        "train_mean_bp": float(row.train_mean_bp),
        "train_p_two": float(row.train_p_two),
        "holdout_n": int(ho["n"]),
        "holdout_blocks": int(ho["blocks"]),
        "holdout_mean_bp": float(ho["mean"]*1e4) if np.isfinite(ho["mean"]) else np.nan,
        "same_sign_2013": same_sign,
        "holdout_p_one": p_one,
        "duplicate_aliases": int(row.duplicate_aliases),
        "kind": row.kind,
        "family_i": row.family_i,
        "state_i": row.state_i,
        "family_j": row.family_j,
        "state_j": row.state_j,
        "feature_i": row.feature_i,
        "feature_j": row.feature_j,
    })

    if ci == 1 or ci == len(frozen) or ci % 250 == 0:
        elapsed = time.time() - t_hold
        rate = ci / max(elapsed, 1e-9)
        eta = (len(frozen)-ci) / max(rate, 1e-9)
        status(
            OUT, "12/13", f"2013 confirmatory block test {ci}/{len(frozen)}",
            percent=round(100*ci/len(frozen),1),
            eta_s=round(eta,1),
        )

H = pd.DataFrame(hold_rows)
hold_cut, hold_k, hold_cm = by_threshold_array(hold_p, HOLD_BY_Q)
if np.isfinite(hold_cut):
    H["holdout_by_pass"] = H["holdout_p_one"] <= hold_cut
else:
    H["holdout_by_pass"] = False

H.to_csv(OUT/"FROZEN_CANDIDATES_2013_CONFIRMATION.csv", index=False)
survivors = H[H["holdout_by_pass"]].copy()
if len(survivors):
    survivors = survivors.sort_values(
        ["holdout_p_one", "train_p_two"],
        kind="mergesort",
    )
survivors.to_csv(OUT/"FROZEN_PRE_2014_SURVIVORS.csv", index=False)

receipt = {
    "run_id": run_id,
    "status": "COMPLETE_BLOCK_CLUSTER_BY_DISCOVERY",
    "engine_version": ENGINE_VERSION,
    "source_v85b": V85B.name,
    "source_v85": V85.name,
    "train_period": "2010-2012",
    "holdout_period": "2013",
    "block_days": BLOCK_DAYS,
    "valid_train_tests": valid_tests,
    "train_by_q": TRAIN_BY_Q,
    "train_by_harmonic_factor": by_cm,
    "train_by_threshold": cutoff if np.isfinite(cutoff) else None,
    "raw_train_by_candidates": len(candidate_idx),
    "unique_train_by_candidates": len(frozen),
    "holdout_by_q": HOLD_BY_Q,
    "holdout_by_harmonic_factor": hold_cm,
    "holdout_by_threshold": hold_cut if np.isfinite(hold_cut) else None,
    "holdout_by_rank_k": hold_k,
    "pre_2014_survivors": len(survivors),
    "2013_target_values_accessed": True,
    "2014_plus_accessed": False,
    "2023_plus_accessed": False,
    "protected_2026_accessed": False,
    "next": (
        "STOP_FOR_HUMAN_REVIEW_BEFORE_2014_2017_REPLICATION"
        if len(survivors)
        else "NO_SURVIVOR_REVIEW_HIERARCHICAL_BLOCK_NULL_ARCHITECTURE"
    ),
}
write_json(OUT/"RUN_RECEIPT.json", receipt)

write_json(checkpoint_path, {
    "catalog_hash": catalog_hash,
    "total_slots": total_slots,
    "singleton_done": True,
    "next_pair": len(pairs),
    "valid_tests": valid_tests,
    "status": "COMPLETE",
})

current = json.loads(current_path.read_text(encoding="utf-8"))
current["status"] = "COMPLETE"
write_json(current_path, current)

status(
    OUT, "13/13",
    "DONE; 2014+ remains untouched",
    unique_train_candidates=len(frozen),
    pre_2014_survivors=len(survivors),
    next=receipt["next"],
)

print("\n=== V86 RECEIPT ===")
print(json.dumps(receipt, indent=2))
print("\n=== FROZEN PRE-2014 SURVIVORS ===")
if len(survivors):
    cols = [
        "kind", "family_i", "state_i", "family_j", "state_j", "target",
        "train_n", "train_blocks", "train_mean_bp", "train_p_two",
        "holdout_n", "holdout_blocks", "holdout_mean_bp", "holdout_p_one",
        "duplicate_aliases",
    ]
    print(survivors[cols].head(100).to_string(index=False))
else:
    print("NONE")
print("\nRUN:", OUT)
