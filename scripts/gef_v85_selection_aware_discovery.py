from pathlib import Path
import pandas as pd
import numpy as np
import json
import time
import math
import hashlib
from scipy.special import ndtr

ROOT = Path(r"D:\MT5_Backtests")
BASE = ROOT / "Research" / "Autonomous" / "guardian_edge_factory_v85"
BASE.mkdir(parents=True, exist_ok=True)

ENGINE_VERSION = "V85.0"
Q_BH = 0.05
MIN_TRAIN_N = 120
MIN_HOLDOUT_N = 40
STATE_Z = 1.0
SLOW_MIN_PERIODS = 500
FAST_MIN_PERIODS = 5000
CHECKPOINT_PAIRS = 512
STATUS_SECONDS = 45.0
MAX_BH_CANDIDATES_FOR_HOLDOUT = 10000

MARKETS = [
    "XAUUSD", "XAGUSD", "UDXUSD", "EURUSD", "GBPUSD", "USDJPY",
    "AUDUSD", "USDCHF", "USDCAD", "SPXUSD", "NSXUSD", "WTIUSD", "BCOUSD"
]
STATE_NAMES = ["LO", "HI"]
PAIR_STATE_NAMES = ["LO_LO", "LO_HI", "HI_LO", "HI_HI"]


def sha_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


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
    print(f"[GEF85] {stage} | {message}" + (f" | {tail}" if tail else ""), flush=True)


def causal_states(series, min_periods):
    s = pd.to_numeric(series, errors="coerce")
    mu = s.expanding(min_periods=min_periods).mean().shift(1)
    sd = s.expanding(min_periods=min_periods).std().shift(1).replace(0, np.nan)
    z = ((s - mu) / sd).to_numpy(dtype=np.float32)
    finite = np.isfinite(z)
    return finite & (z <= -STATE_Z), finite & (z >= STATE_Z)


def matrix_stats(mask, y):
    idx = np.flatnonzero(mask)
    t = y.shape[1]
    p = np.full(t, np.nan, dtype=np.float32)
    n = np.zeros(t, dtype=np.int32)
    mean = np.full(t, np.nan, dtype=np.float64)
    if len(idx) == 0:
        return n, mean, p

    vals = y[idx, :]
    finite = np.isfinite(vals)
    n = finite.sum(axis=0).astype(np.int32)
    sums = np.nansum(vals, axis=0, dtype=np.float64)
    sums2 = np.nansum(vals * vals, axis=0, dtype=np.float64)

    ok_n = n >= MIN_TRAIN_N
    if not ok_n.any():
        return n, mean, p

    nn = n.astype(np.float64)
    mean = np.divide(sums, nn, out=np.full(t, np.nan), where=nn > 0)
    numer = sums2 - np.divide(sums * sums, nn, out=np.zeros(t), where=nn > 0)
    var = np.divide(numer, nn - 1.0, out=np.full(t, np.nan), where=nn > 1)
    var = np.maximum(var, 0.0)
    se = np.sqrt(np.divide(var, nn, out=np.full(t, np.nan), where=nn > 0))
    good = ok_n & np.isfinite(mean) & np.isfinite(se) & (se > 0)
    tstat = np.divide(mean, se, out=np.zeros(t), where=good)
    pv = 2.0 * ndtr(-np.abs(tstat))
    p[good] = pv[good].astype(np.float32)
    return n, mean, p


def scalar_stats(mask, y, min_n):
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        return {"n": 0, "mean": np.nan, "sd": np.nan, "p_two": np.nan}
    v = y[idx]
    v = v[np.isfinite(v)]
    n = len(v)
    if n < min_n:
        return {"n": n, "mean": float(np.mean(v)) if n else np.nan, "sd": np.nan, "p_two": np.nan}
    mean = float(np.mean(v))
    sd = float(np.std(v, ddof=1))
    if not np.isfinite(sd) or sd <= 0:
        return {"n": n, "mean": mean, "sd": sd, "p_two": np.nan}
    tstat = mean / (sd / math.sqrt(n))
    p = float(2.0 * ndtr(-abs(tstat)))
    return {"n": n, "mean": mean, "sd": sd, "p_two": p}


def bh_threshold(pmap, q):
    arr = np.asarray(pmap)
    finite = np.isfinite(arr)
    m = int(finite.sum())
    if m == 0:
        return np.nan, 0, 0
    ps = np.array(arr[finite], dtype=np.float32, copy=True)
    ps.sort()
    chunk = 1_000_000
    last_k = 0
    for start in range(0, m, chunk):
        stop = min(start + chunk, m)
        ranks = np.arange(start + 1, stop + 1, dtype=np.float64)
        ok = ps[start:stop].astype(np.float64) <= (q * ranks / float(m))
        if ok.any():
            last_k = start + int(np.flatnonzero(ok)[-1]) + 1
    if last_k == 0:
        return np.nan, m, 0
    return float(ps[last_k - 1]), m, last_k


def decode_trial(trial_idx, singleton_slots, tcount, pairs):
    if trial_idx < singleton_slots:
        block = 2 * tcount
        fi = trial_idx // block
        rem = trial_idx % block
        state = rem // tcount
        ti = rem % tcount
        return {
            "kind": "singleton",
            "feature_i": int(fi),
            "feature_j": None,
            "state_i": int(state),
            "state_j": None,
            "target_i": int(ti),
        }
    off = trial_idx - singleton_slots
    block = 4 * tcount
    pi = off // block
    rem = off % block
    combo = rem // tcount
    ti = rem % tcount
    fi, fj = pairs[int(pi)]
    return {
        "kind": "pair",
        "pair_i": int(pi),
        "feature_i": int(fi),
        "feature_j": int(fj),
        "state_i": int(combo // 2),
        "state_j": int(combo % 2),
        "target_i": int(ti),
    }


def current_run_path():
    return BASE / "CURRENT_RUN.json"


_test_y = np.array([[0.01], [0.02], [0.03], [0.04]], dtype=np.float32)
_test_mask = np.array([True, True, True, True])
assert scalar_stats(_test_mask, _test_y[:, 0], 2)["n"] == 4
assert np.isfinite(scalar_stats(_test_mask, _test_y[:, 0], 2)["mean"])
del _test_y, _test_mask

v84c_runs = sorted((ROOT / "Research" / "Autonomous" / "guardian_edge_factory_v84c").glob("GEF84C-*"))
v84c_runs = [p for p in v84c_runs if (p / "RUN_RECEIPT.json").exists()]
if not v84c_runs:
    raise RuntimeError("No completed V84C receipt. Run V84C first.")
V84C = v84c_runs[-1]
r84 = json.loads((V84C / "RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r84.get("status") != "BENCHMARK_COMPLETE_V83B_CORRECTED_ENGINE":
    raise RuntimeError(f"Latest V84C is not valid: {r84.get('status')}")
if r84.get("candidate_selection_performed"):
    raise RuntimeError("V84C unexpectedly performed candidate selection")
if r84.get("2014_plus_accessed") or r84.get("2023_plus_accessed") or r84.get("protected_2026_accessed"):
    raise RuntimeError("V84C access assertions violated")

V83B = ROOT / "Research" / "Autonomous" / "guardian_edge_factory_v83b" / r84["source_v83b"]
rb = json.loads((V83B / "RUN_RECEIPT.json").read_text(encoding="utf-8"))
if rb.get("status") != "COMPLETE_V83_RATES_REPAIR":
    raise RuntimeError("Frozen V83B source is not complete")
manifest = json.loads((V83B / "REPAIRED_ARCHITECTURE_MANIFEST.json").read_text(encoding="utf-8"))

catalog = pd.read_csv(V84C / "ELIGIBLE_FEATURES.csv")
required_catalog_cols = {"feature", "layer", "family"}
if not required_catalog_cols.issubset(catalog.columns):
    raise RuntimeError(f"V84C catalog missing columns: {required_catalog_cols - set(catalog.columns)}")
if (catalog["family"] == "other").any():
    raise RuntimeError("V84C catalog contains unclassified features")
for market in MARKETS:
    if not (catalog["family"] == f"price_{market}").any():
        raise RuntimeError(f"Missing frozen price family price_{market}")
if not (catalog["family"] == "rates_yields").any():
    raise RuntimeError("Frozen catalog has no rates_yields")

catalog = catalog.reset_index(drop=True)
catalog_hash = sha_text(catalog[["feature", "layer", "family"]].to_csv(index=False))

pairs = []
families = catalog["family"].tolist()
for i in range(len(catalog)):
    for j in range(i + 1, len(catalog)):
        if families[i] != families[j]:
            pairs.append((i, j))

expected_pairs = int(r84["projected_cross_family_pairs"])
if len(pairs) != expected_pairs:
    raise RuntimeError(f"Pair-universe mismatch V84C={expected_pairs} V85={len(pairs)}")

cur_path = current_run_path()
resume = False
if cur_path.exists():
    cur = json.loads(cur_path.read_text(encoding="utf-8"))
    if (
        cur.get("engine_version") == ENGINE_VERSION
        and cur.get("source_v84c") == V84C.name
        and cur.get("catalog_hash") == catalog_hash
        and cur.get("status") == "RUNNING"
    ):
        OUT = BASE / cur["run_id"]
        resume = True
    elif (
        cur.get("engine_version") == ENGINE_VERSION
        and cur.get("source_v84c") == V84C.name
        and cur.get("catalog_hash") == catalog_hash
        and cur.get("status") == "COMPLETE"
    ):
        OUT = BASE / cur["run_id"]
        print("=== GEF V85 ALREADY COMPLETE ===")
        print((OUT / "RUN_RECEIPT.json").read_text(encoding="utf-8"))
        raise SystemExit(0)

if not resume:
    run_id = "GEF85-" + pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    OUT = BASE / run_id
    OUT.mkdir(parents=True, exist_ok=False)
    write_json(
        cur_path,
        {
            "engine_version": ENGINE_VERSION,
            "run_id": run_id,
            "source_v84c": V84C.name,
            "catalog_hash": catalog_hash,
            "status": "RUNNING",
        },
    )
else:
    run_id = OUT.name

status(
    OUT,
    "1/12",
    "upstream frozen; full discovery engine starting" + (" (RESUME)" if resume else ""),
    run_id=run_id,
    features=len(catalog),
    pairs=len(pairs),
)

S = pd.read_parquet(manifest["slow_state_repaired_path"])
F = pd.read_parquet(manifest["price_state_5m_path"])
Y = pd.read_parquet(manifest["targets_5m_path"])
bridge = np.load(manifest["bridge_path"])
S.index = pd.to_datetime(S.index)
F.index = pd.to_datetime(F.index)
Y = Y.reindex(F.index)
if len(bridge) != len(F):
    raise RuntimeError("Slow/fast bridge length mismatch")

targets = [c for c in Y.columns if "_fwd_" in str(c)]
if len(targets) != int(r84["return_targets"]):
    raise RuntimeError(f"Target-count mismatch V84C={r84['return_targets']} V85={len(targets)}")

train_rows = np.flatnonzero(F.index.year <= 2012)
hold_rows = np.flatnonzero(F.index.year == 2013)
if len(train_rows) == 0 or len(hold_rows) == 0:
    raise RuntimeError("Discovery split missing 2010-2012 or 2013 rows")

YT = Y[targets].to_numpy(dtype=np.float32)[train_rows, :].copy()
YH = Y[targets].to_numpy(dtype=np.float32)[hold_rows, :].copy()
train_times = F.index[train_rows]
hold_times = F.index[hold_rows]
train_minute = (train_times.view("int64") // 60_000_000_000).astype(np.int64)
hold_minute = (hold_times.view("int64") // 60_000_000_000).astype(np.int64)

target_horizons = []
for ti, c in enumerate(targets):
    m = pd.Series([str(c)]).str.extract(r"_fwd_(\d+)m$").iloc[0, 0]
    if pd.isna(m):
        raise RuntimeError(f"Cannot parse target horizon: {c}")
    h = int(m)
    target_horizons.append(h)
    YT[(train_minute % h) != 0, ti] = np.nan
    YH[(hold_minute % h) != 0, ti] = np.nan

status(
    OUT,
    "2/12",
    "data loaded; discovery split and non-overlap targets frozen",
    train_rows=len(train_rows),
    holdout_rows=len(hold_rows),
    targets=len(targets),
)

for row in catalog.itertuples():
    if row.layer == "slow":
        if row.feature not in S.columns:
            raise RuntimeError(f"Frozen slow feature missing: {row.feature}")
    elif row.layer == "fast":
        if row.feature not in F.columns:
            raise RuntimeError(f"Frozen fast feature missing: {row.feature}")
    else:
        raise RuntimeError(f"Unknown feature layer {row.layer}")

catalog.to_csv(OUT / "FROZEN_ELIGIBLE_FEATURES.csv", index=False)
pd.DataFrame(
    [(i, j, catalog.loc[i, "family"], catalog.loc[j, "family"]) for i, j in pairs],
    columns=["feature_i", "feature_j", "family_i", "family_j"],
).to_parquet(OUT / "FROZEN_PAIR_UNIVERSE.parquet", index=False)

nf = len(catalog)
nt = len(targets)
singleton_slots = nf * 2 * nt
pair_slots = len(pairs) * 4 * nt
total_slots = singleton_slots + pair_slots

trial_design = {
    "engine_version": ENGINE_VERSION,
    "source_v84c": V84C.name,
    "source_v83b": V83B.name,
    "catalog_hash": catalog_hash,
    "features": nf,
    "cross_family_pairs": len(pairs),
    "targets": nt,
    "target_horizons_minutes": sorted(set(target_horizons)),
    "state_rule": f"expanding z shifted one observation; LO<=-{STATE_Z}, HI>={STATE_Z}",
    "train_period": "2010-2012",
    "temporal_holdout": "2013",
    "target_sampling": "deterministic UTC grid thinning at each horizon to prevent overlapping forward-return windows",
    "singleton_slots": singleton_slots,
    "pair_slots": pair_slots,
    "predeclared_trial_slots": total_slots,
    "min_train_n": MIN_TRAIN_N,
    "min_holdout_n": MIN_HOLDOUT_N,
    "selection_correction": f"Benjamini-Hochberg q={Q_BH} across all finite singleton+pair discovery tests",
    "holdout_gate": "same direction in 2013 and one-sided p<=0.10 with n>=MIN_HOLDOUT_N",
    "2014_plus_accessed": False,
    "2023_plus_accessed": False,
    "protected_2026_accessed": False,
}
write_json(OUT / "TRIAL_DESIGN.json", trial_design)
status(OUT, "3/12", "trial universe frozen", singleton_slots=singleton_slots, pair_slots=pair_slots, total_slots=total_slots)

state_meta_path = OUT / "STATE_CACHE_META.json"
state_train_path = OUT / "STATE_TRAIN.bool.dat"
state_hold_path = OUT / "STATE_HOLD.bool.dat"

state_train_shape = (nf, 2, len(train_rows))
state_hold_shape = (nf, 2, len(hold_rows))

if state_meta_path.exists():
    sm = json.loads(state_meta_path.read_text(encoding="utf-8"))
    if (
        sm.get("catalog_hash") != catalog_hash
        or tuple(sm.get("train_shape", [])) != state_train_shape
        or tuple(sm.get("hold_shape", [])) != state_hold_shape
        or not sm.get("complete")
    ):
        raise RuntimeError("Existing state cache metadata does not match frozen design")
    ST = np.memmap(state_train_path, mode="r", dtype=np.bool_, shape=state_train_shape)
    SH = np.memmap(state_hold_path, mode="r", dtype=np.bool_, shape=state_hold_shape)
    status(OUT, "4/12", "state cache reused", features=nf)
else:
    ST = np.memmap(state_train_path, mode="w+", dtype=np.bool_, shape=state_train_shape)
    SH = np.memmap(state_hold_path, mode="w+", dtype=np.bool_, shape=state_hold_shape)
    support = []
    t_states = time.time()

    for fi, row in enumerate(catalog.itertuples(), start=0):
        if row.layer == "slow":
            lo_s, hi_s = causal_states(S[row.feature], SLOW_MIN_PERIODS)
            full_lo = np.zeros(len(F), dtype=np.bool_)
            full_hi = np.zeros(len(F), dtype=np.bool_)
            ok = bridge >= 0
            full_lo[ok] = lo_s[bridge[ok]]
            full_hi[ok] = hi_s[bridge[ok]]
        else:
            full_lo, full_hi = causal_states(F[row.feature], FAST_MIN_PERIODS)

        ST[fi, 0, :] = full_lo[train_rows]
        ST[fi, 1, :] = full_hi[train_rows]
        SH[fi, 0, :] = full_lo[hold_rows]
        SH[fi, 1, :] = full_hi[hold_rows]
        support.append(
            {
                "feature_i": fi,
                "feature": row.feature,
                "layer": row.layer,
                "family": row.family,
                "train_lo": int(ST[fi, 0, :].sum()),
                "train_hi": int(ST[fi, 1, :].sum()),
                "hold_lo": int(SH[fi, 0, :].sum()),
                "hold_hi": int(SH[fi, 1, :].sum()),
            }
        )
        done = fi + 1
        if done == 1 or done == nf or done % 20 == 0:
            e = time.time() - t_states
            rate = done / max(e, 1e-9)
            eta = (nf - done) / max(rate, 1e-9)
            status(
                OUT,
                "4/12",
                f"state cache {done}/{nf}",
                percent=round(100 * done / nf, 1),
                elapsed_s=round(e, 1),
                eta_s=round(eta, 1),
            )

    ST.flush()
    SH.flush()
    pd.DataFrame(support).to_csv(OUT / "STATE_SUPPORT.csv", index=False)
    write_json(
        state_meta_path,
        {
            "catalog_hash": catalog_hash,
            "train_shape": list(state_train_shape),
            "hold_shape": list(state_hold_shape),
            "complete": True,
        },
    )
    del ST, SH
    ST = np.memmap(state_train_path, mode="r", dtype=np.bool_, shape=state_train_shape)
    SH = np.memmap(state_hold_path, mode="r", dtype=np.bool_, shape=state_hold_shape)

p_path = OUT / "TRAIN_PVALUES.float32.dat"
checkpoint_path = OUT / "CHECKPOINT.json"

if checkpoint_path.exists():
    cp = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    if cp.get("catalog_hash") != catalog_hash or cp.get("total_slots") != total_slots:
        raise RuntimeError("Checkpoint does not match frozen trial universe")
    pmap = np.memmap(p_path, mode="r+", dtype=np.float32, shape=(total_slots,))
    singleton_done = bool(cp.get("singleton_done", False))
    next_pair = int(cp.get("next_pair", 0))
    valid_tests = int(cp.get("valid_tests", 0))
    status(OUT, "5/12", "checkpoint loaded", singleton_done=singleton_done, next_pair=next_pair, valid_tests=valid_tests)
else:
    pmap = np.memmap(p_path, mode="w+", dtype=np.float32, shape=(total_slots,))
    pmap[:] = np.nan
    pmap.flush()
    singleton_done = False
    next_pair = 0
    valid_tests = 0
    write_json(
        checkpoint_path,
        {
            "catalog_hash": catalog_hash,
            "total_slots": total_slots,
            "singleton_done": False,
            "next_pair": 0,
            "valid_tests": 0,
            "status": "RUNNING",
        },
    )
    status(OUT, "5/12", "fresh p-value ledger initialized", slots=total_slots)

if not singleton_done:
    t_single = time.time()
    for fi in range(nf):
        for st in range(2):
            _, _, pv = matrix_stats(ST[fi, st, :], YT)
            base = fi * 2 * nt + st * nt
            pmap[base:base + nt] = pv
            valid_tests += int(np.isfinite(pv).sum())
        done = fi + 1
        if done == 1 or done == nf or done % 25 == 0:
            e = time.time() - t_single
            rate = done / max(e, 1e-9)
            eta = (nf - done) / max(rate, 1e-9)
            status(
                OUT,
                "6/12",
                f"singletons {done}/{nf}",
                percent=round(100 * done / nf, 1),
                elapsed_s=round(e, 1),
                eta_s=round(eta, 1),
                valid_tests=valid_tests,
            )
    pmap.flush()
    singleton_done = True
    write_json(
        checkpoint_path,
        {
            "catalog_hash": catalog_hash,
            "total_slots": total_slots,
            "singleton_done": True,
            "next_pair": next_pair,
            "valid_tests": valid_tests,
            "status": "RUNNING",
        },
    )

scan_start = time.time()
last_status = scan_start
start_pair = next_pair
for pi in range(start_pair, len(pairs)):
    fi, fj = pairs[pi]
    combo = 0
    for si in range(2):
        for sj in range(2):
            mask = ST[fi, si, :] & ST[fj, sj, :]
            _, _, pv = matrix_stats(mask, YT)
            base = singleton_slots + pi * 4 * nt + combo * nt
            pmap[base:base + nt] = pv
            valid_tests += int(np.isfinite(pv).sum())
            combo += 1

    done_pairs = pi + 1
    now = time.time()
    do_checkpoint = done_pairs == len(pairs) or done_pairs % CHECKPOINT_PAIRS == 0
    if do_checkpoint:
        pmap.flush()
        write_json(
            checkpoint_path,
            {
                "catalog_hash": catalog_hash,
                "total_slots": total_slots,
                "singleton_done": True,
                "next_pair": done_pairs,
                "valid_tests": valid_tests,
                "status": "RUNNING",
            },
        )

    if do_checkpoint or (now - last_status) >= STATUS_SECONDS:
        elapsed = now - scan_start
        processed = done_pairs - start_pair
        rate = processed / max(elapsed, 1e-9)
        remain = len(pairs) - done_pairs
        eta = remain / max(rate, 1e-9) if processed > 0 else np.nan
        status(
            OUT,
            "7/12",
            f"pair scan {done_pairs}/{len(pairs)}",
            percent=round(100 * done_pairs / len(pairs), 2),
            pairs_per_s=round(rate, 3),
            elapsed_min=round(elapsed / 60, 1),
            eta_min=round(eta / 60, 1) if np.isfinite(eta) else None,
            valid_tests=valid_tests,
        )
        last_status = now

pmap.flush()
write_json(
    checkpoint_path,
    {
        "catalog_hash": catalog_hash,
        "total_slots": total_slots,
        "singleton_done": True,
        "next_pair": len(pairs),
        "valid_tests": valid_tests,
        "status": "SCAN_COMPLETE",
    },
)
scan_seconds = time.time() - scan_start
status(OUT, "8/12", "full discovery scan complete; computing global BH correction", valid_tests=valid_tests, scan_minutes=round(scan_seconds / 60, 1))

cutoff, finite_tests, bh_k = bh_threshold(pmap, Q_BH)
if finite_tests != valid_tests:
    valid_tests = finite_tests

if np.isfinite(cutoff):
    arr = np.asarray(pmap)
    sig_idx = np.flatnonzero(np.isfinite(arr) & (arr <= cutoff))
else:
    sig_idx = np.array([], dtype=np.int64)

if len(sig_idx) > MAX_BH_CANDIDATES_FOR_HOLDOUT:
    write_json(
        OUT / "RUN_RECEIPT.json",
        {
            "run_id": run_id,
            "status": "STOP_TOO_MANY_BH_CANDIDATES",
            "valid_train_tests": valid_tests,
            "bh_q": Q_BH,
            "bh_threshold": cutoff,
            "bh_rank_k": bh_k,
            "bh_candidates": len(sig_idx),
            "edge_trials": valid_tests,
            "2014_plus_accessed": False,
            "2023_plus_accessed": False,
            "protected_2026_accessed": False,
            "next": "REDESIGN_HOLDOUT_BATCHING_BEFORE_ANY_2014_ACCESS",
        },
    )
    cur = json.loads(cur_path.read_text(encoding="utf-8"))
    cur["status"] = "COMPLETE"
    write_json(cur_path, cur)
    print("\n=== V85 SAFETY STOP ===")
    print((OUT / "RUN_RECEIPT.json").read_text(encoding="utf-8"))
    print("\nRUN:", OUT)
    raise SystemExit(0)

status(
    OUT,
    "9/12",
    "global BH correction complete",
    bh_q=Q_BH,
    bh_threshold=cutoff if np.isfinite(cutoff) else None,
    bh_rank_k=bh_k,
    bh_candidates=len(sig_idx),
    valid_tests=valid_tests,
)

rows = []
t_hold = time.time()
for ci, trial_idx in enumerate(sig_idx, start=1):
    dec = decode_trial(int(trial_idx), singleton_slots, nt, pairs)
    ti = dec["target_i"]
    fi = dec["feature_i"]
    si = dec["state_i"]

    if dec["kind"] == "singleton":
        mt = ST[fi, si, :]
        mh = SH[fi, si, :]
        feature_j = None
        family_j = None
        state_j = None
        parent_a = np.nan
        parent_b = np.nan
    else:
        fj = dec["feature_j"]
        sj = dec["state_j"]
        mt = ST[fi, si, :] & ST[fj, sj, :]
        mh = SH[fi, si, :] & SH[fj, sj, :]
        feature_j = catalog.loc[fj, "feature"]
        family_j = catalog.loc[fj, "family"]
        state_j = STATE_NAMES[sj]
        parent_a = scalar_stats(ST[fi, si, :], YT[:, ti], MIN_TRAIN_N)["mean"]
        parent_b = scalar_stats(ST[fj, sj, :], YT[:, ti], MIN_TRAIN_N)["mean"]

    tr = scalar_stats(mt, YT[:, ti], MIN_TRAIN_N)
    ho = scalar_stats(mh, YH[:, ti], MIN_HOLDOUT_N)
    if not np.isfinite(tr["mean"]) or tr["mean"] == 0:
        direction = 0
    else:
        direction = 1 if tr["mean"] > 0 else -1

    same_sign = bool(
        direction != 0
        and np.isfinite(ho["mean"])
        and ho["mean"] != 0
        and np.sign(ho["mean"]) == direction
    )
    hold_p_one = (ho["p_two"] / 2.0) if same_sign and np.isfinite(ho["p_two"]) else np.nan
    hold_pass = bool(
        ho["n"] >= MIN_HOLDOUT_N
        and same_sign
        and np.isfinite(hold_p_one)
        and hold_p_one <= 0.10
    )

    train_bp = tr["mean"] * 1e4 if np.isfinite(tr["mean"]) else np.nan
    hold_bp = ho["mean"] * 1e4 if np.isfinite(ho["mean"]) else np.nan
    best_parent_bp = np.nan
    gain_bp = np.nan
    if dec["kind"] == "pair" and np.isfinite(parent_a) and np.isfinite(parent_b):
        best_parent_bp = max(abs(parent_a), abs(parent_b)) * 1e4
        gain_bp = abs(train_bp) - best_parent_bp

    p_train = float(pmap[int(trial_idx)])

    rows.append(
        {
            "trial_index": int(trial_idx),
            "kind": dec["kind"],
            "feature_i": catalog.loc[fi, "feature"],
            "family_i": catalog.loc[fi, "family"],
            "state_i": STATE_NAMES[si],
            "feature_j": feature_j,
            "family_j": family_j,
            "state_j": state_j,
            "target": targets[ti],
            "horizon_min": target_horizons[ti],
            "train_n": tr["n"],
            "train_mean_bp": train_bp,
            "train_p_two": p_train,
            "holdout_n": ho["n"],
            "holdout_mean_bp": hold_bp,
            "holdout_p_one_same_direction": hold_p_one,
            "same_sign_2013": same_sign,
            "holdout_pass": hold_pass,
            "best_parent_abs_mean_bp": best_parent_bp,
            "pair_incremental_abs_bp": gain_bp,
            "bh_global_q": Q_BH,
            "bh_threshold": cutoff,
            "bh_rank_k": bh_k,
        }
    )

    if ci == 1 or ci == len(sig_idx) or ci % 100 == 0:
        e = time.time() - t_hold
        rate = ci / max(e, 1e-9)
        eta = (len(sig_idx) - ci) / max(rate, 1e-9)
        status(
            OUT,
            "10/12",
            f"2013 holdout {ci}/{len(sig_idx)}",
            percent=round(100 * ci / max(1, len(sig_idx)), 1),
            elapsed_s=round(e, 1),
            eta_s=round(eta, 1),
        )

C = pd.DataFrame(rows)
C.to_csv(OUT / "BH_DISCOVERIES_WITH_2013_HOLDOUT.csv", index=False)
if len(C):
    survivors = C[C["holdout_pass"]].copy()
    survivors = survivors.sort_values(
        ["holdout_p_one_same_direction", "train_p_two"],
        ascending=[True, True],
        kind="mergesort",
    )
else:
    survivors = C.copy()
survivors.to_csv(OUT / "FROZEN_PRE_REPLICATION_SURVIVORS.csv", index=False)

status(
    OUT,
    "11/12",
    "2013 temporal screen complete",
    bh_discoveries=len(C),
    temporal_survivors=len(survivors),
)

receipt = {
    "run_id": run_id,
    "status": "COMPLETE_SELECTION_AWARE_DISCOVERY",
    "engine_version": ENGINE_VERSION,
    "source_v84c": V84C.name,
    "source_v83b": V83B.name,
    "catalog_hash": catalog_hash,
    "train_period": "2010-2012",
    "temporal_holdout": "2013",
    "features": nf,
    "cross_family_pairs": len(pairs),
    "return_targets": nt,
    "predeclared_trial_slots": total_slots,
    "valid_train_tests": valid_tests,
    "bh_q": Q_BH,
    "bh_threshold": cutoff if np.isfinite(cutoff) else None,
    "bh_rank_k": bh_k,
    "bh_discoveries": len(C),
    "temporal_survivors": len(survivors),
    "pair_scan_seconds_this_process": scan_seconds,
    "edge_trials": valid_tests,
    "2014_plus_accessed": False,
    "2023_plus_accessed": False,
    "protected_2026_accessed": False,
    "next": (
        "V86_PRE_REPLICATION_ROBUSTNESS_AND_STRUCTURAL_DEDUP"
        if len(survivors)
        else "NO_SURVIVOR_RETURN_TO_HYPOTHESIS_ARCHITECTURE"
    ),
}
write_json(OUT / "RUN_RECEIPT.json", receipt)
write_json(
    checkpoint_path,
    {
        "catalog_hash": catalog_hash,
        "total_slots": total_slots,
        "singleton_done": True,
        "next_pair": len(pairs),
        "valid_tests": valid_tests,
        "status": "COMPLETE",
    },
)
cur = json.loads(cur_path.read_text(encoding="utf-8"))
cur["status"] = "COMPLETE"
write_json(cur_path, cur)

status(
    OUT,
    "12/12",
    "DONE; no 2014+ data accessed",
    bh_discoveries=len(C),
    temporal_survivors=len(survivors),
    next=receipt["next"],
)

print("\n=== V85 RECEIPT ===")
print(json.dumps(receipt, indent=2))
print("\n=== FROZEN PRE-REPLICATION SURVIVORS ===")
if len(survivors):
    cols = [
        "kind", "family_i", "state_i", "family_j", "state_j", "target",
        "train_n", "train_mean_bp", "train_p_two",
        "holdout_n", "holdout_mean_bp", "holdout_p_one_same_direction",
        "pair_incremental_abs_bp"
    ]
    print(survivors[cols].head(100).to_string(index=False))
else:
    print("NONE")
print("\nRUN:", OUT)
