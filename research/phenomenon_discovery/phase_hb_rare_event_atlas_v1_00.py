#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SYMBOLS = ("BTCUSDT", "ETHUSDT")
FEATURES = (
    "oi_change_15m_pct",
    "oi_change_1h_pct",
    "oi_accel_15m_pctpt",
    "atr_slope_3bar_pct",
    "range_atr",
    "mark_index_bps_change_15m",
    "mark_index_bps_change_1h",
    "premium_index_change_15m",
    "premium_index_change_1h",
    "taker_imbalance_diff_change_15m",
    "taker_imbalance_diff_change_1h",
    "spot_taker_imbalance_change_15m",
    "perp_taker_imbalance_change_15m",
    "perp_spot_basis_bps_change_15m",
    "perp_spot_basis_bps_change_1h",
    "spot_volume_shock_1h",
    "perp_volume_shock_1h",
    "spot_trade_shock_1h",
    "perp_trade_shock_1h",
)
TAILS = (
    ("LOW_1P", 0.01, "LOW"),
    ("LOW_2P", 0.02, "LOW"),
    ("HIGH_2P", 0.98, "HIGH"),
    ("HIGH_1P", 0.99, "HIGH"),
)
HORIZONS = ("15m", "30m", "1h", "2h", "4h")
OUTCOME_KINDS = ("return_atr", "excursion_bias_atr", "up_first_touch")
DISCOVERY_MIN_ANNUAL = 500
DISCOVERY_MIN_HALF = 180
CONFIRM_MIN_ANNUAL = 300
CONFIRM_MIN_QUARTER = 50
TOP_PER_OUTCOME_HORIZON = 5
BOOTSTRAP_PATHS = 3000
BLOCK_DAYS = 5
BH_Q_MAX = 0.10
RETENTION_FRACTION = 0.25
QUARTER_MATCH_MIN = 0.75
RNG_SEED = 20260908


def fnum(x: str | None) -> float | None:
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def year_of(row: dict[str, str]) -> int:
    return int(row["timestamp_utc"][:4])


def month_of(row: dict[str, str]) -> int:
    return int(row["timestamp_utc"][5:7])


def half_of(row: dict[str, str]) -> int:
    return 1 if month_of(row) <= 6 else 2


def quarter_of(row: dict[str, str]) -> int:
    return (month_of(row) - 1) // 3 + 1


def day_of(row: dict[str, str]) -> str:
    return row["timestamp_utc"][:10]


def quantile(values: list[float], q: float) -> float:
    if not values:
        raise RuntimeError("empty quantile input")
    xs = sorted(values)
    pos = q * (len(xs) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    w = pos - lo
    return xs[lo] * (1.0 - w) + xs[hi] * w


def event_hit(value: float | None, threshold: float, side: str) -> bool:
    if value is None:
        return False
    return value <= threshold if side == "LOW" else value >= threshold


def outcome_value(row: dict[str, str], horizon: str, kind: str) -> float | None:
    if kind == "return_atr":
        return fnum(row.get(f"future_return_{horizon}_atr"))
    if kind == "excursion_bias_atr":
        return fnum(row.get(f"future_excursion_bias_{horizon}_atr"))
    if kind == "up_first_touch":
        touch = row.get(f"future_first_touch_1atr_{horizon}", "")
        if touch == "UP":
            return 1.0
        if touch == "DOWN":
            return 0.0
        return None
    raise ValueError(kind)


def load_year(path: Path, target_year: int) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            y = year_of(row)
            if y == target_year:
                out.append(row)
            elif y > target_year:
                break
    return out


def effect_for_rows(rows: list[dict[str, str]], feature: str, threshold: float, side: str, horizon: str, kind: str) -> tuple[int, float | None, int, float | None]:
    base_vals: list[float] = []
    event_vals: list[float] = []
    for row in rows:
        y = outcome_value(row, horizon, kind)
        if y is None:
            continue
        base_vals.append(y)
        if event_hit(fnum(row.get(feature)), threshold, side):
            event_vals.append(y)
    if not base_vals or not event_vals:
        return len(event_vals), None, len(base_vals), None
    base_mean = sum(base_vals) / len(base_vals)
    event_mean = sum(event_vals) / len(event_vals)
    return len(event_vals), event_mean - base_mean, len(base_vals), base_mean


def signed_same(values: list[float | None]) -> int:
    vals = [v for v in values if v is not None and v != 0]
    if len(vals) != len(values):
        return 0
    if all(v > 0 for v in vals):
        return 1
    if all(v < 0 for v in vals):
        return -1
    return 0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def bh_qvalues(pvals: list[float]) -> list[float]:
    n = len(pvals)
    order = sorted(range(n), key=lambda i: pvals[i])
    out = [1.0] * n
    running = 1.0
    for rank_idx in range(n - 1, -1, -1):
        i = order[rank_idx]
        rank = rank_idx + 1
        running = min(running, pvals[i] * n / rank)
        out[i] = min(1.0, running)
    return out


def daily_stats(rows: list[dict[str, str]], candidate: dict) -> dict[str, tuple[float, int, float, int]]:
    stats: dict[str, list[float | int]] = {}
    for row in rows:
        y = outcome_value(row, candidate["horizon"], candidate["outcome_kind"])
        if y is None:
            continue
        day = day_of(row)
        if day not in stats:
            stats[day] = [0.0, 0, 0.0, 0]
        s = stats[day]
        s[0] += y
        s[1] += 1
        if event_hit(fnum(row.get(candidate["feature"])), float(candidate["threshold"]), candidate["side"]):
            s[2] += y
            s[3] += 1
    return {k: (float(v[0]), int(v[1]), float(v[2]), int(v[3])) for k, v in stats.items()}


def bootstrap_one_sided(rows: list[dict[str, str]], candidate: dict, expected_sign: int, seed: int) -> float:
    stats = daily_stats(rows, candidate)
    days = sorted(stats)
    if len(days) < 20:
        return 1.0
    rng = random.Random(seed)
    n = len(days)
    blocks_needed = int(math.ceil(n / BLOCK_DAYS))
    bad = 0
    valid = 0
    for _ in range(BOOTSTRAP_PATHS):
        bs = bc = es = ec = 0.0
        for _b in range(blocks_needed):
            start = rng.randrange(n)
            for j in range(BLOCK_DAYS):
                d = days[(start + j) % n]
                x = stats[d]
                bs += x[0]
                bc += x[1]
                es += x[2]
                ec += x[3]
        if bc <= 0 or ec <= 0:
            continue
        eff = es / ec - bs / bc
        valid += 1
        if expected_sign > 0 and eff <= 0:
            bad += 1
        elif expected_sign < 0 and eff >= 0:
            bad += 1
    if valid == 0:
        return 1.0
    return (bad + 1.0) / (valid + 1.0)


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0].keys()) if rows else ["empty"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        if rows:
            w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\event_shock_v1")
    ap.add_argument("--output-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_hb_v1")
    args = ap.parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {sym: input_dir / f"{sym}_event_shock_matrix_2024-01-01_2026-01-01.csv" for sym in SYMBOLS}
    for sym, path in paths.items():
        if not path.exists():
            raise RuntimeError(f"missing H-A matrix for {sym}: {path}")

    # Hard chronology: load 2024 only first. 2025 is not read until shortlist is written and hashed.
    rows_2024 = {sym: load_year(paths[sym], 2024) for sym in SYMBOLS}
    if any(len(rows_2024[sym]) < 100000 for sym in SYMBOLS):
        raise RuntimeError("unexpectedly short 2024 dataset")

    thresholds: dict[str, dict[str, dict[str, float | str]]] = {sym: {} for sym in SYMBOLS}
    for sym in SYMBOLS:
        for feature in FEATURES:
            vals = [v for row in rows_2024[sym] if (v := fnum(row.get(feature))) is not None]
            if len(vals) < 100000:
                raise RuntimeError(f"insufficient 2024 feature coverage {sym} {feature}: {len(vals)}")
            thresholds[sym][feature] = {}
            for tail_name, q, side in TAILS:
                thresholds[sym][feature][tail_name] = quantile(vals, q)

    universe: list[dict] = []
    for feature in FEATURES:
        for tail_name, _q, side in TAILS:
            for horizon in HORIZONS:
                for kind in OUTCOME_KINDS:
                    blocks: dict[str, dict[str, float | int | None]] = {}
                    effects_for_sign: list[float | None] = []
                    support_ok = True
                    for sym in SYMBOLS:
                        th = float(thresholds[sym][feature][tail_name])
                        annual_n, annual_eff, _bn, _bm = effect_for_rows(rows_2024[sym], feature, th, side, horizon, kind)
                        half_data = []
                        for half in (1, 2):
                            subset = [r for r in rows_2024[sym] if half_of(r) == half]
                            hn, he, _hbn, _hbm = effect_for_rows(subset, feature, th, side, horizon, kind)
                            half_data.append((hn, he))
                            effects_for_sign.append(he)
                            if hn < DISCOVERY_MIN_HALF:
                                support_ok = False
                        effects_for_sign.append(annual_eff)
                        if annual_n < DISCOVERY_MIN_ANNUAL:
                            support_ok = False
                        blocks[sym] = {
                            "threshold": th,
                            "annual_n": annual_n,
                            "annual_effect": annual_eff,
                            "h1_n": half_data[0][0],
                            "h1_effect": half_data[0][1],
                            "h2_n": half_data[1][0],
                            "h2_effect": half_data[1][1],
                        }
                    expected_sign = signed_same(effects_for_sign)
                    eligible = support_ok and expected_sign != 0
                    abs_effects = [abs(float(blocks[s]["annual_effect"])) for s in SYMBOLS if blocks[s]["annual_effect"] is not None]
                    worst_abs = min(abs_effects) if len(abs_effects) == len(SYMBOLS) else 0.0
                    universe.append({
                        "candidate_id": f"{feature}|{tail_name}|{horizon}|{kind}",
                        "feature": feature,
                        "tail": tail_name,
                        "side": side,
                        "horizon": horizon,
                        "outcome_kind": kind,
                        "expected_sign": expected_sign,
                        "discovery_eligible": eligible,
                        "discovery_worst_abs_effect": worst_abs,
                        "btcusdt_threshold": blocks["BTCUSDT"]["threshold"],
                        "btcusdt_annual_n": blocks["BTCUSDT"]["annual_n"],
                        "btcusdt_annual_effect": blocks["BTCUSDT"]["annual_effect"],
                        "btcusdt_h1_n": blocks["BTCUSDT"]["h1_n"],
                        "btcusdt_h1_effect": blocks["BTCUSDT"]["h1_effect"],
                        "btcusdt_h2_n": blocks["BTCUSDT"]["h2_n"],
                        "btcusdt_h2_effect": blocks["BTCUSDT"]["h2_effect"],
                        "ethusdt_threshold": blocks["ETHUSDT"]["threshold"],
                        "ethusdt_annual_n": blocks["ETHUSDT"]["annual_n"],
                        "ethusdt_annual_effect": blocks["ETHUSDT"]["annual_effect"],
                        "ethusdt_h1_n": blocks["ETHUSDT"]["h1_n"],
                        "ethusdt_h1_effect": blocks["ETHUSDT"]["h1_effect"],
                        "ethusdt_h2_n": blocks["ETHUSDT"]["h2_n"],
                        "ethusdt_h2_effect": blocks["ETHUSDT"]["h2_effect"],
                    })

    universe_path = output_dir / "phase_hb_2024_universe.csv"
    write_csv(universe_path, universe)

    shortlist: list[dict] = []
    for horizon in HORIZONS:
        for kind in OUTCOME_KINDS:
            group = [r for r in universe if r["horizon"] == horizon and r["outcome_kind"] == kind and r["discovery_eligible"]]
            group.sort(key=lambda r: (-float(r["discovery_worst_abs_effect"]), r["candidate_id"]))
            shortlist.extend(group[:TOP_PER_OUTCOME_HORIZON])
    shortlist.sort(key=lambda r: r["candidate_id"])

    frozen_path = output_dir / "phase_hb_frozen_shortlist_2024.json"
    frozen_payload = {
        "schema": 1,
        "phase": "H-B",
        "frozen_before_2025_read": True,
        "protected_2026_untouched": True,
        "news_mask_applied": False,
        "propfirm_tradability_authorized": False,
        "feature_count": len(FEATURES),
        "raw_hypotheses": len(universe),
        "shortlist_count": len(shortlist),
        "top_per_outcome_horizon": TOP_PER_OUTCOME_HORIZON,
        "candidates": shortlist,
    }
    frozen_path.write_text(json.dumps(frozen_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    frozen_hash = sha256(frozen_path)

    # Only now may 2025 be read.
    rows_2025 = {sym: load_year(paths[sym], 2025) for sym in SYMBOLS}
    if any(len(rows_2025[sym]) < 100000 for sym in SYMBOLS):
        raise RuntimeError("unexpectedly short 2025 dataset")

    confirmations: list[dict] = []
    p_for_bh: list[float] = []
    for idx, cand in enumerate(shortlist):
        rec = dict(cand)
        all_same = True
        retain = True
        quarter_matches = 0
        quarter_eligible = 0
        pvals = []
        confirm_abs: list[float] = []
        for sidx, sym in enumerate(SYMBOLS):
            th = float(cand[f"{sym.lower()}_threshold"])
            annual_n, annual_eff, _bn, _bm = effect_for_rows(rows_2025[sym], cand["feature"], th, cand["side"], cand["horizon"], cand["outcome_kind"])
            rec[f"{sym.lower()}_2025_n"] = annual_n
            rec[f"{sym.lower()}_2025_effect"] = annual_eff
            same = annual_eff is not None and int(cand["expected_sign"]) * annual_eff > 0
            all_same = all_same and same and annual_n >= CONFIRM_MIN_ANNUAL
            if annual_eff is not None:
                confirm_abs.append(abs(annual_eff))
            else:
                retain = False
            for q in (1, 2, 3, 4):
                subset = [r for r in rows_2025[sym] if quarter_of(r) == q]
                qn, qe, _qbn, _qbm = effect_for_rows(subset, cand["feature"], th, cand["side"], cand["horizon"], cand["outcome_kind"])
                rec[f"{sym.lower()}_2025_q{q}_n"] = qn
                rec[f"{sym.lower()}_2025_q{q}_effect"] = qe
                if qn >= CONFIRM_MIN_QUARTER and qe is not None:
                    quarter_eligible += 1
                    if int(cand["expected_sign"]) * qe > 0:
                        quarter_matches += 1
            local_cand = dict(cand)
            local_cand["threshold"] = th
            p = bootstrap_one_sided(rows_2025[sym], local_cand, int(cand["expected_sign"]), RNG_SEED + idx * 17 + sidx)
            rec[f"{sym.lower()}_block_p"] = p
            pvals.append(p)
        worst_confirm_abs = min(confirm_abs) if len(confirm_abs) == len(SYMBOLS) else 0.0
        retain = retain and worst_confirm_abs >= RETENTION_FRACTION * float(cand["discovery_worst_abs_effect"])
        qrate = quarter_matches / quarter_eligible if quarter_eligible else 0.0
        quarter_stable = quarter_eligible >= 6 and qrate >= QUARTER_MATCH_MIN
        worst_p = max(pvals) if pvals else 1.0
        rec["confirm_same_sign_both"] = all_same
        rec["confirm_worst_abs_effect"] = worst_confirm_abs
        rec["confirm_retains_effect"] = retain
        rec["quarter_eligible"] = quarter_eligible
        rec["quarter_match"] = quarter_matches
        rec["quarter_match_rate"] = qrate
        rec["quarter_stable"] = quarter_stable
        rec["worst_symbol_p"] = worst_p
        confirmations.append(rec)
        p_for_bh.append(worst_p)

    qvals = bh_qvalues(p_for_bh) if p_for_bh else []
    for rec, qv in zip(confirmations, qvals):
        rec["worst_symbol_bh_q"] = qv
        rec["phase_hb_screen_pass"] = bool(
            rec["confirm_same_sign_both"]
            and rec["confirm_retains_effect"]
            and rec["quarter_stable"]
            and qv <= BH_Q_MAX
        )

    confirmation_path = output_dir / "phase_hb_2025_confirmation.csv"
    write_csv(confirmation_path, confirmations)
    passes = [r for r in confirmations if r["phase_hb_screen_pass"]]
    passes_path = output_dir / "phase_hb_distinct_passes.csv"
    write_csv(passes_path, passes, list(confirmations[0].keys()) if confirmations else ["empty"])

    by_kind = {kind: 0 for kind in OUTCOME_KINDS}
    by_horizon = {h: 0 for h in HORIZONS}
    for r in passes:
        by_kind[r["outcome_kind"]] += 1
        by_horizon[r["horizon"]] += 1

    summary = {
        "schema": 1,
        "phase": "H-B",
        "status": "DISCOVERY_ROBUSTNESS_ONLY",
        "method": "rare 1%-2% single-feature event atlas; 2024 discovery/freeze then 2025 confirmation",
        "feature_count": len(FEATURES),
        "tails_per_feature": len(TAILS),
        "horizons": list(HORIZONS),
        "outcome_kinds": list(OUTCOME_KINDS),
        "raw_hypotheses": len(universe),
        "discovery_eligible_count": sum(1 for r in universe if r["discovery_eligible"]),
        "frozen_shortlist_count": len(shortlist),
        "frozen_shortlist_sha256": frozen_hash,
        "phase_hb_screen_pass_count": len(passes),
        "passes_by_outcome_kind": by_kind,
        "passes_by_horizon": by_horizon,
        "gates": {
            "discovery_min_annual": DISCOVERY_MIN_ANNUAL,
            "discovery_min_half": DISCOVERY_MIN_HALF,
            "confirmation_min_annual": CONFIRM_MIN_ANNUAL,
            "confirmation_min_quarter": CONFIRM_MIN_QUARTER,
            "effect_retention_fraction": RETENTION_FRACTION,
            "quarter_match_min": QUARTER_MATCH_MIN,
            "bootstrap_paths": BOOTSTRAP_PATHS,
            "circular_block_days": BLOCK_DAYS,
            "bh_q_max": BH_Q_MAX,
        },
        "protected_2026_untouched": True,
        "news_mask_applied": False,
        "propfirm_tradability_authorized": False,
        "news_policy": "No candidate may be promoted as prop-firm tradable until a historical news mask matching the target prop-firm rule is applied.",
        "independent_validation": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = output_dir / "phase_hb_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
