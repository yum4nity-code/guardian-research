from pathlib import Path
import pandas as pd
import numpy as np
import json
import time
import math
from datetime import datetime
from scipy.stats import t as student_t

ROOT = Path(r"D:\MT5_Backtests")
BASE = ROOT / "Research" / "Autonomous" / "guardian_edge_factory_v87"
BASE.mkdir(parents=True, exist_ok=True)

ENGINE_VERSION = "V87.0"
COST_BPS = (0.25, 0.5, 1.0, 2.0, 5.0)
SLOW_28D = {"rates_yields", "alfred", "financial_conditions"}
MIN_CLUSTER_BLOCKS = 8
STATUS_EVERY = 10


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def status(out, step, total, msg, **extra):
    elapsed = extra.pop("elapsed_s", None)
    payload = {
        "engine_version": ENGINE_VERSION,
        "step": step,
        "steps": total,
        "percent": round(100 * step / total, 1),
        "timestamp_utc": pd.Timestamp.now("UTC").isoformat(),
        "message": msg,
        **extra,
    }
    if elapsed is not None:
        payload["elapsed_s"] = round(elapsed, 1)
    write_json(out / "LIVE_STATUS.json", payload)
    tail = " | ".join(f"{k}={v}" for k, v in extra.items())
    print(
        f"[GEF87] {step}/{total} {100*step/total:.0f}% | {msg}"
        + (f" | {tail}" if tail else ""),
        flush=True,
    )


def decode_trial(trial_idx, singleton_slots, nt, pair_i, pair_j):
    if trial_idx < singleton_slots:
        block = 2 * nt
        fi = trial_idx // block
        rem = trial_idx % block
        return {
            "kind": "singleton",
            "fi": int(fi),
            "fj": None,
            "si": int(rem // nt),
            "sj": None,
            "ti": int(rem % nt),
        }

    off = trial_idx - singleton_slots
    block = 4 * nt
    pi = off // block
    rem = off % block
    combo = rem // nt
    return {
        "kind": "pair",
        "pi": int(pi),
        "fi": int(pair_i[int(pi)]),
        "fj": int(pair_j[int(pi)]),
        "si": int(combo // 2),
        "sj": int(combo % 2),
        "ti": int(rem % nt),
    }


def condition_mask(decoded, states):
    mask = np.asarray(states[decoded["fi"], decoded["si"], :], dtype=np.bool_)
    if decoded["kind"] == "pair":
        mask = mask & states[decoded["fj"], decoded["sj"], :]
    return mask


def primary_block_days(family_i, family_j):
    fams = {str(family_i)}
    if family_j is not None and not pd.isna(family_j):
        fams.add(str(family_j))
    if any(f.startswith("cftc_") for f in fams):
        return 28
    if fams & SLOW_28D:
        return 28
    return 5


def block_ids(times, block_days, origin):
    return ((times.normalize() - origin).days.to_numpy() // int(block_days)).astype(np.int16)


def cluster_test_positive(directional_returns, blocks):
    r = np.asarray(directional_returns, dtype=np.float64)
    b = np.asarray(blocks)
    finite = np.isfinite(r)
    r = r[finite]
    b = b[finite]
    n = len(r)
    if n == 0:
        return {"n": 0, "blocks": 0, "mean": np.nan, "p_one": np.nan, "p_two": np.nan}

    mean = float(r.mean())
    starts = np.r_[0, np.flatnonzero(b[1:] != b[:-1]) + 1]
    g = len(starts)

    if g < MIN_CLUSTER_BLOCKS:
        return {"n": n, "blocks": g, "mean": mean, "p_one": np.nan, "p_two": np.nan}

    sums = np.add.reduceat(r, starts)
    counts = np.diff(np.r_[starts, n]).astype(np.float64)
    u = sums - counts * mean
    meat = float(np.sum(u * u))

    if not np.isfinite(meat) or meat <= 0:
        return {"n": n, "blocks": g, "mean": mean, "p_one": np.nan, "p_two": np.nan}

    se2 = (g / (g - 1.0)) * meat / (n * n)
    if not np.isfinite(se2) or se2 <= 0:
        return {"n": n, "blocks": g, "mean": mean, "p_one": np.nan, "p_two": np.nan}

    stat = mean / math.sqrt(se2)
    p_two = float(2.0 * student_t.sf(abs(stat), df=g - 1))
    p_one = float(student_t.sf(stat, df=g - 1))
    return {"n": n, "blocks": g, "mean": mean, "p_one": p_one, "p_two": p_two}


def max_drawdown_pct(returns):
    r = np.asarray(returns, dtype=np.float64)
    r = r[np.isfinite(r)]
    if len(r) == 0:
        return np.nan
    if np.any(r <= -1.0):
        return np.nan
    equity = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(equity)
    dd = equity / peak - 1.0
    return float(dd.min() * 100.0)


def core_metrics(directional_returns):
    r = np.asarray(directional_returns, dtype=np.float64)
    r = r[np.isfinite(r)]
    if len(r) == 0:
        out = {
            "n": 0,
            "mean_bp": np.nan,
            "median_bp": np.nan,
            "win_rate_pct": np.nan,
            "gross_sum_pct": np.nan,
            "gross_compound_pct": np.nan,
            "max_drawdown_pct": np.nan,
            "trim_top5_mean_bp": np.nan,
            "break_even_cost_bp": np.nan,
        }
        for c in COST_BPS:
            tag = str(c).replace(".", "p")
            out[f"net_{tag}bp_mean_bp"] = np.nan
            out[f"net_{tag}bp_sum_pct"] = np.nan
            out[f"net_{tag}bp_pnl_10k"] = np.nan
            out[f"net_{tag}bp_pnl_100k"] = np.nan
        return out

    n = len(r)
    mean = float(r.mean())
    median = float(np.median(r))
    win = float((r > 0).mean())
    gross_sum = float(r.sum())
    compound = float(np.expm1(np.log1p(r).sum())) if np.all(r > -1) else np.nan

    cut = max(1, int(math.floor(n * 0.05)))
    order = np.sort(r)
    trimmed = order[:-cut] if cut < n else np.array([], dtype=np.float64)
    trim_mean = float(trimmed.mean()) if len(trimmed) else np.nan

    out = {
        "n": n,
        "mean_bp": mean * 1e4,
        "median_bp": median * 1e4,
        "win_rate_pct": win * 100.0,
        "gross_sum_pct": gross_sum * 100.0,
        "gross_compound_pct": compound * 100.0 if np.isfinite(compound) else np.nan,
        "max_drawdown_pct": max_drawdown_pct(r),
        "trim_top5_mean_bp": trim_mean * 1e4 if np.isfinite(trim_mean) else np.nan,
        "break_even_cost_bp": mean * 1e4,
    }

    for c in COST_BPS:
        tag = str(c).replace(".", "p")
        net = r - c * 1e-4
        out[f"net_{tag}bp_mean_bp"] = float(net.mean() * 1e4)
        out[f"net_{tag}bp_sum_pct"] = float(net.sum() * 100.0)
        out[f"net_{tag}bp_pnl_10k"] = float(net.sum() * 10_000.0)
        out[f"net_{tag}bp_pnl_100k"] = float(net.sum() * 100_000.0)

    return out


def yearly_metrics(directional_returns, times):
    r = np.asarray(directional_returns, dtype=np.float64)
    out = {}
    positive_years = 0
    valid_years = 0
    means = []

    for year in (2010, 2011, 2012):
        sel = np.asarray(times.year == year)
        vals = r[sel]
        vals = vals[np.isfinite(vals)]
        n = len(vals)
        mean_bp = float(vals.mean() * 1e4) if n else np.nan
        out[f"y{year}_n"] = n
        out[f"y{year}_mean_bp"] = mean_bp
        out[f"y{year}_win_rate_pct"] = float((vals > 0).mean() * 100.0) if n else np.nan
        if n:
            valid_years += 1
            means.append(mean_bp)
            if mean_bp > 0:
                positive_years += 1

    out["positive_years"] = positive_years
    out["valid_years"] = valid_years
    out["worst_year_mean_bp"] = min(means) if means else np.nan
    return out


def monthly_positive_fraction(directional_returns, times):
    r = np.asarray(directional_returns, dtype=np.float64)
    finite = np.isfinite(r)
    if not finite.any():
        return np.nan, 0
    s = pd.Series(r[finite], index=times[finite])
    monthly = s.groupby(s.index.to_period("M")).mean()
    if len(monthly) == 0:
        return np.nan, 0
    return float((monthly > 0).mean()), int(len(monthly))


def bh_adjust(pvalues):
    p = np.asarray(pvalues, dtype=np.float64)
    m = len(p)
    out = np.full(m, np.nan)
    finite = np.isfinite(p)
    idx = np.flatnonzero(finite)
    if not len(idx):
        return out
    vals = p[idx]
    order = np.argsort(vals)
    ranked = vals[order]
    adj = ranked * len(ranked) / np.arange(1, len(ranked) + 1, dtype=np.float64)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    adj = np.clip(adj, 0, 1)
    out[idx[order]] = adj
    return out


def holm_adjust(pvalues):
    p = np.asarray(pvalues, dtype=np.float64)
    m = len(p)
    out = np.full(m, np.nan)
    finite = np.isfinite(p)
    idx = np.flatnonzero(finite)
    if not len(idx):
        return out
    vals = p[idx]
    order = np.argsort(vals)
    ranked = vals[order]
    factors = np.arange(len(ranked), 0, -1, dtype=np.float64)
    adj = np.maximum.accumulate(ranked * factors)
    adj = np.clip(adj, 0, 1)
    out[idx[order]] = adj
    return out


# Small deterministic self-test before touching research artifacts.
_test = np.array([0.01, -0.005, 0.02], dtype=np.float64)
_tm = core_metrics(_test)
assert _tm["n"] == 3
assert _tm["mean_bp"] > 0
assert np.isclose(_tm["net_1p0bp_mean_bp"], _tm["mean_bp"] - 1.0)

# ---------------- latest frozen train-only panel ----------------
v86a_runs = sorted((ROOT / "Research" / "Autonomous" / "guardian_edge_factory_v86a").glob("GEF86A-*"))
v86a_runs = [p for p in v86a_runs if (p / "RUN_RECEIPT.json").exists()]
if not v86a_runs:
    raise RuntimeError("No completed V86A train-only panel")
V86A = v86a_runs[-1]
r86a = json.loads((V86A / "RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r86a.get("2013_target_values_accessed") or r86a.get("2014_plus_accessed"):
    raise RuntimeError("V86A unexpectedly touched holdout/later values")

panel = pd.read_csv(V86A / "TOP_RAW_UNIQUE_V86.csv")
required = {
    "raw_rank", "trial_index", "kind", "family_i", "family_j", "target",
    "direction", "cluster_p_two"
}
if not required.issubset(panel.columns):
    raise RuntimeError(f"V86A panel missing columns: {sorted(required - set(panel.columns))}")
if len(panel) == 0:
    raise RuntimeError("V86A panel is empty")

run_id = "GEF87-" + pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT = BASE / run_id
OUT.mkdir(parents=True, exist_ok=False)
t0 = time.time()

status(OUT, 1, 10, "loaded frozen train-only candidate panel", candidates=len(panel), source_v86a=V86A.name)

# ---------------- resolve immutable state/target architecture ----------------
V86 = ROOT / "Research" / "Autonomous" / "guardian_edge_factory_v86" / r86a["source_v86"]
spec86 = json.loads((V86 / "FROZEN_V86_SPEC.json").read_text(encoding="utf-8"))
V85 = ROOT / "Research" / "Autonomous" / "guardian_edge_factory_v85" / spec86["source_v85"]
design = json.loads((V85 / "TRIAL_DESIGN.json").read_text(encoding="utf-8"))
pairs = pd.read_parquet(V85 / "FROZEN_PAIR_UNIVERSE.parquet")
state_meta = json.loads((V85 / "STATE_CACHE_META.json").read_text(encoding="utf-8"))

V84C = ROOT / "Research" / "Autonomous" / "guardian_edge_factory_v84c" / design["source_v84c"]
r84 = json.loads((V84C / "RUN_RECEIPT.json").read_text(encoding="utf-8"))
V83B = ROOT / "Research" / "Autonomous" / "guardian_edge_factory_v83b" / r84["source_v83b"]
manifest = json.loads((V83B / "REPAIRED_ARCHITECTURE_MANIFEST.json").read_text(encoding="utf-8"))

nt = int(design["targets"])
singleton_slots = int(design["singleton_slots"])
pair_i = pairs["feature_i"].to_numpy(dtype=np.int64)
pair_j = pairs["feature_j"].to_numpy(dtype=np.int64)

train_shape = tuple(state_meta["train_shape"])
hold_shape = tuple(state_meta["hold_shape"])
ST = np.memmap(V85 / "STATE_TRAIN.bool.dat", mode="r", dtype=np.bool_, shape=train_shape)
SH = np.memmap(V85 / "STATE_HOLD.bool.dat", mode="r", dtype=np.bool_, shape=hold_shape)

F = pd.read_parquet(manifest["price_state_5m_path"])
F.index = pd.to_datetime(F.index)
train_times = F.index[F.index < pd.Timestamp("2013-01-01")]
hold_times = F.index[(F.index >= pd.Timestamp("2013-01-01")) & (F.index < pd.Timestamp("2014-01-01"))]

if len(train_times) != train_shape[2]:
    raise RuntimeError("Train state/time alignment mismatch")
if len(hold_times) != hold_shape[2]:
    raise RuntimeError("Holdout state/time alignment mismatch")

# ---------------- train values only ----------------
YTdf = pd.read_parquet(
    manifest["targets_5m_path"],
    filters=[("decision_time_utc", "<", datetime(2013, 1, 1))],
)
YTdf.index = pd.to_datetime(YTdf.index)
YTdf = YTdf.reindex(train_times)
targets = [c for c in YTdf.columns if "_fwd_" in str(c)]
if len(targets) != nt:
    raise RuntimeError("Frozen target count mismatch")

YT = np.array(YTdf[targets], dtype=np.float32, copy=True)
target_to_i = {str(c): i for i, c in enumerate(targets)}
horizons = [int(str(c).rsplit("_fwd_", 1)[1].rstrip("m")) for c in targets]
minute_train = (train_times.view("int64") // 60_000_000_000).astype(np.int64)
for ti, h in enumerate(horizons):
    YT[(minute_train % h) != 0, ti] = np.nan

status(OUT, 2, 10, "2010-2012 values loaded; 2013 still unopened", train_rows=len(train_times), targets=nt)

# ---------------- full train stress on frozen 100 ----------------
train_rows_out = []
for idx, row in enumerate(panel.itertuples(index=False), start=1):
    trial = int(row.trial_index)
    d = decode_trial(trial, singleton_slots, nt, pair_i, pair_j)
    ti = target_to_i[str(row.target)]
    mask = condition_mask(d, ST)
    sign = 1.0 if str(row.direction).upper() == "LONG" else -1.0

    directional = sign * YT[:, ti]
    directional = np.where(mask, directional, np.nan)

    metrics = core_metrics(directional)
    ym = yearly_metrics(directional, train_times)
    month_pos, month_n = monthly_positive_fraction(directional, train_times)

    p5 = cluster_test_positive(directional, block_ids(train_times, 5, pd.Timestamp("2010-01-01")))
    p28 = cluster_test_positive(directional, block_ids(train_times, 28, pd.Timestamp("2010-01-01")))
    primary_days = primary_block_days(row.family_i, row.family_j)
    pprimary = p28 if primary_days == 28 else p5

    robust_points = 0
    robust_points += int(ym["positive_years"] >= 2)
    robust_points += int(np.isfinite(ym["worst_year_mean_bp"]) and ym["worst_year_mean_bp"] > 0)
    robust_points += int(np.isfinite(metrics["trim_top5_mean_bp"]) and metrics["trim_top5_mean_bp"] > 0)
    robust_points += int(np.isfinite(metrics["net_1p0bp_mean_bp"]) and metrics["net_1p0bp_mean_bp"] > 0)
    robust_points += int(np.isfinite(pprimary["p_one"]) and pprimary["p_one"] <= 0.05)

    rec = {
        "panel_rank": idx,
        "raw_rank": int(row.raw_rank),
        "trial_index": trial,
        "kind": str(row.kind),
        "family_i": str(row.family_i),
        "state_i": str(row.state_i),
        "family_j": None if pd.isna(row.family_j) else str(row.family_j),
        "state_j": None if pd.isna(row.state_j) else str(row.state_j),
        "target": str(row.target),
        "direction": str(row.direction),
        "primary_block_days": primary_days,
        "train_p_block5_one": p5["p_one"],
        "train_p_block28_one": p28["p_one"],
        "train_p_primary_one": pprimary["p_one"],
        "positive_month_fraction": month_pos,
        "months_with_signals": month_n,
        "train_robustness_points_0_to_5": robust_points,
        **metrics,
        **ym,
    }
    train_rows_out.append(rec)

    if idx == 1 or idx == len(panel) or idx % STATUS_EVERY == 0:
        elapsed = time.time() - t0
        status(
            OUT, 3, 10,
            f"train stress {idx}/{len(panel)}",
            progress=f"{idx}/{len(panel)}",
            elapsed_s=elapsed,
        )

TRAIN = pd.DataFrame(train_rows_out)
TRAIN.to_csv(OUT / "TRAIN_2010_2012_STRESS.csv", index=False)

# Freeze ALL 100 before opening 2013. No train pruning.
frozen_panel = TRAIN[[
    "panel_rank", "raw_rank", "trial_index", "kind", "family_i", "state_i",
    "family_j", "state_j", "target", "direction", "primary_block_days"
]].copy()
frozen_panel.to_csv(OUT / "FROZEN_PANEL_BEFORE_2013.csv", index=False)

freeze_receipt = {
    "run_id": run_id,
    "status": "FROZEN_BEFORE_2013",
    "source_v86a": V86A.name,
    "candidates": len(frozen_panel),
    "selection_rule": "all 100 train-only V86A unique candidates; no post-hoc train pruning",
    "train_stress_is_descriptive_not_a_kill_filter": True,
    "2013_target_values_accessed": False,
    "2014_plus_accessed": False,
}
write_json(OUT / "FREEZE_RECEIPT.json", freeze_receipt)

status(
    OUT, 4, 10,
    "100-candidate panel frozen; 2013 values still unopened",
    candidates=len(frozen_panel),
)

# ---------------- NOW open 2013 ----------------
YHdf = pd.read_parquet(
    manifest["targets_5m_path"],
    filters=[
        ("decision_time_utc", ">=", datetime(2013, 1, 1)),
        ("decision_time_utc", "<", datetime(2014, 1, 1)),
    ],
)
YHdf.index = pd.to_datetime(YHdf.index)
YHdf = YHdf.reindex(hold_times)
YH = np.array(YHdf[targets], dtype=np.float32, copy=True)

minute_hold = (hold_times.view("int64") // 60_000_000_000).astype(np.int64)
for ti, h in enumerate(horizons):
    YH[(minute_hold % h) != 0, ti] = np.nan

status(OUT, 5, 10, "2013 holdout opened after freeze", holdout_rows=len(hold_times), candidates=len(frozen_panel))

# ---------------- confirm all frozen candidates ----------------
hold_rows_out = []
p_primary = np.full(len(frozen_panel), np.nan, dtype=np.float64)

for idx, row in enumerate(frozen_panel.itertuples(index=False), start=1):
    trial = int(row.trial_index)
    d = decode_trial(trial, singleton_slots, nt, pair_i, pair_j)
    ti = target_to_i[str(row.target)]
    mask = condition_mask(d, SH)
    sign = 1.0 if str(row.direction).upper() == "LONG" else -1.0

    directional = sign * YH[:, ti]
    directional = np.where(mask, directional, np.nan)

    metrics = core_metrics(directional)
    p5 = cluster_test_positive(directional, block_ids(hold_times, 5, pd.Timestamp("2013-01-01")))
    p28 = cluster_test_positive(directional, block_ids(hold_times, 28, pd.Timestamp("2013-01-01")))
    ppri = p28 if int(row.primary_block_days) == 28 else p5
    p_primary[idx - 1] = ppri["p_one"]

    rec = {
        "panel_rank": int(row.panel_rank),
        "raw_rank": int(row.raw_rank),
        "trial_index": trial,
        "kind": str(row.kind),
        "family_i": str(row.family_i),
        "state_i": str(row.state_i),
        "family_j": None if pd.isna(row.family_j) else str(row.family_j),
        "state_j": None if pd.isna(row.state_j) else str(row.state_j),
        "target": str(row.target),
        "direction": str(row.direction),
        "primary_block_days": int(row.primary_block_days),
        "holdout_p_block5_one": p5["p_one"],
        "holdout_p_block28_one": p28["p_one"],
        "holdout_p_primary_one": ppri["p_one"],
        **metrics,
    }
    hold_rows_out.append(rec)

    if idx == 1 or idx == len(frozen_panel) or idx % STATUS_EVERY == 0:
        status(
            OUT, 6, 10,
            f"2013 confirmation {idx}/{len(frozen_panel)}",
            progress=f"{idx}/{len(frozen_panel)}",
        )

HOLD = pd.DataFrame(hold_rows_out)
HOLD["bh_q_primary"] = bh_adjust(p_primary)
HOLD["holm_p_primary"] = holm_adjust(p_primary)
HOLD["replicated_positive_mean"] = HOLD["mean_bp"] > 0
HOLD["nominal_p05"] = HOLD["holdout_p_primary_one"] <= 0.05
HOLD["bh_q10"] = HOLD["bh_q_primary"] <= 0.10
HOLD["holm_p05"] = HOLD["holm_p_primary"] <= 0.05
HOLD["net_1bp_positive"] = HOLD["net_1p0bp_mean_bp"] > 0
HOLD["net_2bp_positive"] = HOLD["net_2p0bp_mean_bp"] > 0

HOLD.to_csv(OUT / "HOLDOUT_2013_ALL_100.csv", index=False)

status(
    OUT, 7, 10,
    "2013 multiplicity markers computed; nobody deleted",
    replicated_positive=int(HOLD["replicated_positive_mean"].sum()),
    nominal_p05=int(HOLD["nominal_p05"].sum()),
    bh_q10=int(HOLD["bh_q10"].sum()),
    holm_p05=int(HOLD["holm_p05"].sum()),
)

# ---------------- merged audit ----------------
MERGED = TRAIN.merge(
    HOLD,
    on=[
        "panel_rank", "raw_rank", "trial_index", "kind", "family_i", "state_i",
        "family_j", "state_j", "target", "direction", "primary_block_days"
    ],
    suffixes=("_train", "_2013"),
    how="inner",
    validate="one_to_one",
)

if len(MERGED) != len(frozen_panel):
    raise RuntimeError("Merged train/holdout candidate count mismatch")

MERGED["train_and_2013_positive"] = (
    (MERGED["mean_bp_train"] > 0) & (MERGED["mean_bp_2013"] > 0)
)
MERGED["train_and_2013_net1bp_positive"] = (
    (MERGED["net_1p0bp_mean_bp_train"] > 0) &
    (MERGED["net_1p0bp_mean_bp_2013"] > 0)
)
MERGED["holdout_to_train_mean_ratio"] = np.divide(
    MERGED["mean_bp_2013"],
    MERGED["mean_bp_train"],
    out=np.full(len(MERGED), np.nan),
    where=np.abs(MERGED["mean_bp_train"].to_numpy()) > 1e-12,
)

MERGED.to_csv(OUT / "TRAIN_PLUS_2013_EDGE_AUDIT.csv", index=False)

status(
    OUT, 8, 10,
    "train + 2013 audit merged",
    same_sign_positive=int(MERGED["train_and_2013_positive"].sum()),
    net1bp_both=int(MERGED["train_and_2013_net1bp_positive"].sum()),
)

# ---------------- report ranked views; still no 2014+ ----------------
top_hold = MERGED.sort_values(
    ["bh_q_primary", "holdout_p_primary_one", "mean_bp_2013"],
    ascending=[True, True, False],
    kind="mergesort",
).copy()
top_hold.to_csv(OUT / "RANKED_2013_CANDIDATES.csv", index=False)

summary = {
    "run_id": run_id,
    "status": "COMPLETE_100_CANDIDATE_2013_CONFIRMATION",
    "source_v86a": V86A.name,
    "candidates_frozen_before_2013": len(frozen_panel),
    "train_period": "2010-2012",
    "holdout_period": "2013",
    "adaptive_primary_blocks": {
        "28d": "CFTC, rates_yields, ALFRED, financial_conditions present",
        "5d": "all other families",
    },
    "train_descriptive_only_no_candidate_killed": True,
    "holdout_replicated_positive_mean": int(HOLD["replicated_positive_mean"].sum()),
    "holdout_nominal_p05": int(HOLD["nominal_p05"].sum()),
    "holdout_bh_q10": int(HOLD["bh_q10"].sum()),
    "holdout_holm_p05": int(HOLD["holm_p05"].sum()),
    "train_and_2013_net1bp_positive": int(MERGED["train_and_2013_net1bp_positive"].sum()),
    "2013_target_values_accessed": True,
    "2014_plus_accessed": False,
    "2023_plus_accessed": False,
    "protected_2026_accessed": False,
    "next": "STOP_FOR_HUMAN_REVIEW_BEFORE_2014_2017_REPLICATION",
}
write_json(OUT / "RUN_RECEIPT.json", summary)

status(
    OUT, 9, 10,
    "receipt written; 2014+ untouched",
    replicated_positive=summary["holdout_replicated_positive_mean"],
    bh_q10=summary["holdout_bh_q10"],
)
status(OUT, 10, 10, "DONE; candidate panel retained in full, no auto-kill")

print("\n=== V87 RECEIPT ===")
print(json.dumps(summary, indent=2))

print("\n=== TOP 30 BY 2013 CONFIRMATION ===")
show_cols = [
    "panel_rank", "raw_rank", "family_i", "state_i", "family_j", "state_j",
    "target", "direction",
    "n_train", "mean_bp_train", "positive_years", "worst_year_mean_bp",
    "trim_top5_mean_bp_train", "net_1p0bp_mean_bp_train",
    "n_2013", "mean_bp_2013", "win_rate_pct_2013",
    "holdout_p_primary_one", "bh_q_primary", "holm_p_primary",
    "net_1p0bp_mean_bp_2013", "net_2p0bp_mean_bp_2013",
    "gross_sum_pct_2013", "max_drawdown_pct_2013"
]
print(top_hold[show_cols].head(30).to_string(index=False))

print("\n=== BEST 20 ECONOMICALLY IN 2013 (GROSS MEAN BP) ===")
econ = MERGED.sort_values(
    ["mean_bp_2013", "holdout_p_primary_one"],
    ascending=[False, True],
    kind="mergesort",
)
econ_cols = [
    "panel_rank", "family_i", "family_j", "target", "direction",
    "n_2013", "mean_bp_2013", "win_rate_pct_2013",
    "gross_sum_pct_2013", "net_1p0bp_sum_pct_2013",
    "net_2p0bp_sum_pct_2013", "holdout_p_primary_one", "bh_q_primary"
]
print(econ[econ_cols].head(20).to_string(index=False))

print("\nRUN:", OUT)
