#!/usr/bin/env python3
"""R29: R27-compatible active-compression filter × frozen R6 breakouts.

Post-selection interaction diagnostic on canonical R6 2024-2025 data only.
No 2026 access. No R6 retuning. A FILTER_LEAD verdict only justifies a later
prospective shadow A/B test; it does not authorize Guardian/live changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import r6_xau_low_turnover_breakout_v1_00 as r6
import r5_pre_oos_economic_robustness_v1_00 as econ

LOOKBACK_RETURNS = 48
TRAILING_DAYS = 20
BOOTSTRAPS = 5000
BASE_SEED = 20260916

CANDIDATES = {
    "R6B-347": {
        "candidate_id": "R6B-347",
        "lookback_bars": 96,
        "buffer_atr": 0.10,
        "horizon_bars": 96,
        "session": "UTC00_08",
        "session_start": 0,
        "session_end": 8,
        "direction": 1,
        "direction_name": "LONG",
        "role": "PRIMARY",
    },
    "R6B-307": {
        "candidate_id": "R6B-307",
        "lookback_bars": 96,
        "buffer_atr": 0.00,
        "horizon_bars": 48,
        "session": "UTC00_08",
        "session_start": 0,
        "session_end": 8,
        "direction": 1,
        "direction_name": "LONG",
        "role": "REPLICATION",
    },
}


def atomic_json(path: Path, obj) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def heartbeat(path: Path | None, done: int, total: int, stage: str, extra=None) -> None:
    if path is None:
        return
    obj = {
        "completed": int(done),
        "total": int(total),
        "stage": stage,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "protected_2026_opened": False,
    }
    if extra:
        obj.update(extra)
    atomic_json(path, obj)


def nearest_rank(xs: list[float], q: float) -> float:
    ys = sorted(float(x) for x in xs)
    if not ys:
        raise RuntimeError("nearest_rank requires non-empty input")
    rank = max(1, math.ceil(q * len(ys)))
    return ys[rank - 1]


def active_bottom10_state(df: pd.DataFrame) -> list[dict | None]:
    """Exact R22 volatility-state math, without hourly event thinning.

    stdev48 uses the previous 48 contiguous close-close M5 returns and excludes
    the current bar return. q10 uses all valid stdev48 values from the prior up
    to 20 available UTC data days within the provided year slice.
    """
    n = len(df)
    times = df.time.array.as_unit("ns").asi8
    close = df.close.to_numpy(float)

    returns: list[float | None] = [None] * n
    for i in range(1, n):
        if int(times[i] - times[i - 1]) == 300 * 1_000_000_000:
            returns[i] = float(close[i] / close[i - 1] - 1.0)

    stdev: list[float | None] = [None] * n
    for i in range(LOOKBACK_RETURNS, n):
        hist = returns[i - LOOKBACK_RETURNS : i]
        if len(hist) != LOOKBACK_RETURNS or any(x is None for x in hist):
            continue
        sd = statistics.stdev(float(x) for x in hist if x is not None)
        if sd >= 0:
            stdev[i] = float(sd)

    days = [pd.Timestamp(x).date().isoformat() for x in df.time]
    by_day: dict[str, list[float]] = defaultdict(list)
    ordered: list[str] = []
    seen: set[str] = set()
    for i, day in enumerate(days):
        if stdev[i] is None:
            continue
        by_day[day].append(float(stdev[i]))
        if day not in seen:
            seen.add(day)
            ordered.append(day)

    prior: dict[str, list[float]] = {}
    for pos, day in enumerate(ordered):
        vals: list[float] = []
        for pd_day in ordered[max(0, pos - TRAILING_DAYS) : pos]:
            vals.extend(by_day[pd_day])
        prior[day] = vals

    out: list[dict | None] = [None] * n
    for i, day in enumerate(days):
        sd = stdev[i]
        hist = prior.get(day, [])
        if sd is None or not hist:
            continue
        q10 = nearest_rank(hist, 0.10)
        out[i] = {
            "active_bottom10": bool(sd <= q10),
            "stdev48": float(sd),
            "q10": float(q10),
            "trailing_distribution_n": len(hist),
        }
    return out


def classify_ledger(ledger: list[dict], state: list[dict | None]) -> list[dict]:
    out = []
    for trade in ledger:
        idx = int(trade["signal_index"])
        if idx < 0 or idx >= len(state):
            raise RuntimeError(f"signal_index out of state range: {idx}")
        s = state[idx]
        label = (
            "STATE_UNAVAILABLE"
            if s is None
            else ("ACTIVE_BOTTOM10" if s["active_bottom10"] else "NOT_BOTTOM10")
        )
        out.append(
            {
                **trade,
                "r29_state": label,
                "r29_stdev48": None if s is None else s["stdev48"],
                "r29_q10": None if s is None else s["q10"],
                "r29_trailing_distribution_n": (
                    None if s is None else s["trailing_distribution_n"]
                ),
            }
        )
    return out


def interaction_difference(trades: list[dict], profile: str) -> float | None:
    a = [
        float(t["profiles"][profile]["net"])
        for t in trades
        if t["r29_state"] == "ACTIVE_BOTTOM10"
    ]
    b = [
        float(t["profiles"][profile]["net"])
        for t in trades
        if t["r29_state"] == "NOT_BOTTOM10"
    ]
    if not a or not b:
        return None
    return float(statistics.fmean(a) - statistics.fmean(b))


def candidate_seed(candidate_id: str) -> int:
    h = int(hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:8], 16)
    return (BASE_SEED ^ h) & 0xFFFFFFFF


def day_block_bootstrap_difference(
    trades: list[dict], profile: str, candidate_id: str
) -> dict:
    by_day: dict[str, list[dict]] = defaultdict(list)
    for t in trades:
        if t["r29_state"] == "STATE_UNAVAILABLE":
            continue
        day = str(t["signal_time"])[:10]
        by_day[day].append(t)

    days = sorted(by_day)
    observed = interaction_difference(trades, profile)
    if observed is None or not days:
        return {
            "resamples": BOOTSTRAPS,
            "valid_resamples": 0,
            "observed_difference": observed,
            "p025": None,
            "p975": None,
            "reason": "missing stratum or day blocks",
        }

    rng = random.Random(candidate_seed(candidate_id))
    vals: list[float] = []
    for _ in range(BOOTSTRAPS):
        sample: list[dict] = []
        for __ in range(len(days)):
            sample.extend(by_day[days[rng.randrange(len(days))]])
        d = interaction_difference(sample, profile)
        if d is not None:
            vals.append(float(d))

    if len(vals) < 2:
        return {
            "resamples": BOOTSTRAPS,
            "valid_resamples": len(vals),
            "observed_difference": observed,
            "p025": None,
            "p975": None,
            "reason": "fewer than two valid resamples",
        }

    return {
        "resamples": BOOTSTRAPS,
        "valid_resamples": len(vals),
        "observed_difference": observed,
        "p025": float(np.quantile(vals, 0.025)),
        "p975": float(np.quantile(vals, 0.975)),
        "reason": None,
    }


def state_summary(trades: list[dict], profile: str) -> dict:
    active = [t for t in trades if t["r29_state"] == "ACTIVE_BOTTOM10"]
    normal = [t for t in trades if t["r29_state"] == "NOT_BOTTOM10"]
    unavailable = [t for t in trades if t["r29_state"] == "STATE_UNAVAILABLE"]
    available = active + normal
    return {
        "total_trades": len(trades),
        "state_available_trades": len(available),
        "state_unavailable_trades": len(unavailable),
        "state_availability_fraction": (
            len(available) / len(trades) if trades else None
        ),
        "active_bottom10_trades": len(active),
        "active_bottom10_fraction_of_available": (
            len(active) / len(available) if available else None
        ),
        "interaction_difference": interaction_difference(trades, profile),
        "active_bottom10": econ.stats(active, profile),
        "not_bottom10": econ.stats(normal, profile),
        "all_original": econ.stats(trades, profile),
        "hypothetical_veto_retained": econ.stats(
            [t for t in trades if t["r29_state"] != "ACTIVE_BOTTOM10"],
            profile,
        ),
    }


def pooled_years(years: dict[int, list[dict]]) -> list[dict]:
    return [t for y in sorted(years) for t in years[y]]


def evaluate_candidate(
    rule: dict,
    source_by_year: dict[int, pd.DataFrame],
    raw_by_year: dict[int, pd.DataFrame],
    state_by_year: dict[int, list[dict | None]],
) -> dict:
    classified_by_year: dict[int, list[dict]] = {}
    accounting = {}

    for year in (2024, 2025):
        source = source_by_year[year]
        raw = raw_by_year[year]
        atr = r6.atr14(source)
        signals = r6.breakout_signal(
            source,
            atr,
            rule["lookback_bars"],
            rule["buffer_atr"],
            rule["direction"],
            rule["session_start"],
            rule["session_end"],
        )
        ledger, acc = econ.replay(
            source,
            raw,
            signals,
            rule["horizon_bars"],
            rule["direction"],
            300,
        )
        classified_by_year[year] = classify_ledger(
            ledger, state_by_year[year]
        )
        accounting[str(year)] = acc

    pooled = pooled_years(classified_by_year)
    result = {
        "frozen_rule": rule,
        "signal_accounting": accounting,
        "years": {},
        "pooled": {},
        "bootstrap_pooled_e1": day_block_bootstrap_difference(
            pooled, "E1", rule["candidate_id"]
        ),
    }

    for year in (2024, 2025):
        result["years"][str(year)] = {
            profile: state_summary(classified_by_year[year], profile)
            for profile in econ.PROFILES
        }

    result["pooled"] = {
        profile: state_summary(pooled, profile) for profile in econ.PROFILES
    }
    result["classified_trades"] = pooled
    return result


def filter_lead_gate(results: dict) -> dict:
    r347 = results["R6B-347"]
    r307 = results["R6B-307"]
    checks = {}

    for cid, r in (("R6B-347", r347), ("R6B-307", r307)):
        for year in ("2024", "2025"):
            av = r["years"][year]["E1"]["state_availability_fraction"]
            checks[f"{cid}_availability_{year}_gte_0_90"] = (
                av is not None and av >= 0.90
            )
        n_active = r["pooled"]["E1"]["active_bottom10_trades"]
        checks[f"{cid}_pooled_active_trades_gte_12"] = n_active >= 12

    for year in ("2024", "2025"):
        d = r347["years"][year]["E1"]["interaction_difference"]
        checks[f"R6B-347_E1_diff_{year}_lt_0"] = d is not None and d < 0

    d = r347["pooled"]["E1"]["interaction_difference"]
    checks["R6B-347_E1_diff_pooled_lt_0"] = d is not None and d < 0

    boot = r347["bootstrap_pooled_e1"]
    checks["R6B-347_E1_bootstrap_valid_gte_4750"] = (
        int(boot["valid_resamples"]) >= 4750
    )
    checks["R6B-347_E1_bootstrap_upper_lt_0"] = (
        boot["p975"] is not None and float(boot["p975"]) < 0
    )

    for cid, r in (("R6B-347", r347), ("R6B-307", r307)):
        d = r["pooled"]["STRESS"]["interaction_difference"]
        checks[f"{cid}_STRESS_diff_pooled_lt_0"] = d is not None and d < 0

    d307 = r307["pooled"]["E1"]["interaction_difference"]
    checks["R6B-307_E1_diff_pooled_lt_0"] = (
        d307 is not None and d307 < 0
    )

    passed = all(checks.values())
    return {
        "status": "FILTER_LEAD" if passed else "NO_FILTER_LEAD",
        "checks": checks,
        "all_required": True,
        "interpretation": (
            "post-selection interaction diagnostic only; FILTER_LEAD requires "
            "future prospective shadow A/B before any Guardian change"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase-ib-root", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--progress-file")
    args = ap.parse_args()

    root = Path(args.phase_ib_root)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    progress = Path(args.progress_file) if args.progress_file else None
    result_path = out / "r29_r27_filter_r6_result.json"
    if result_path.exists():
        raise RuntimeError(
            "existing R29 result detected; refusing scientific overwrite"
        )

    heartbeat(progress, 0, 8, "load_canonical_inputs")
    source_all = r6.load_exact(root / "xauusd_m5_2024_2025_news_clean.csv")
    raw_all = r6.load_exact(root / "xauusd_m1_2024_2025_raw.csv")

    source_by_year = {
        y: r6.year_slice(source_all, y) for y in (2024, 2025)
    }
    raw_by_year = {y: r6.year_slice(raw_all, y) for y in (2024, 2025)}

    heartbeat(progress, 1, 8, "build_active_state_2024")
    state_by_year = {
        2024: active_bottom10_state(source_by_year[2024]),
    }
    heartbeat(progress, 2, 8, "build_active_state_2025")
    state_by_year[2025] = active_bottom10_state(source_by_year[2025])

    results = {}
    for step, cid in enumerate(("R6B-347", "R6B-307"), start=3):
        heartbeat(progress, step, 8, f"evaluate_{cid}")
        results[cid] = evaluate_candidate(
            CANDIDATES[cid],
            source_by_year,
            raw_by_year,
            state_by_year,
        )

    heartbeat(progress, 5, 8, "apply_frozen_gate")
    gate = filter_lead_gate(results)

    payload = {
        "schema": 1,
        "research": "R29",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "post_selection_interaction_diagnostic",
        "canonical_source_hashes": r6.EXPECTED,
        "protected_2026_opened": False,
        "years": [2024, 2025],
        "r27_mapping": {
            "state": "active_bottom10_without_hourly_thinning",
            "lookback_returns": LOOKBACK_RETURNS,
            "trailing_prior_days": TRAILING_DAYS,
            "quantile": 0.10,
            "current_bar_return_excluded": True,
            "year_isolated": True,
        },
        "bootstrap": {
            "resamples": BOOTSTRAPS,
            "base_seed": BASE_SEED,
            "block": "signal_calendar_day",
        },
        "results": results,
        "gate": gate,
        "interpretation": (
            "FILTER_LEAD is not independent validation and does not authorize "
            "Guardian/live modification; prospective shadow A/B required."
        ),
    }

    heartbeat(progress, 6, 8, "serialize")
    atomic_json(result_path, payload)

    rows = []
    for cid, r in results.items():
        for scope in ("2024", "2025", "pooled"):
            block = r["pooled"] if scope == "pooled" else r["years"][scope]
            for profile in econ.PROFILES:
                s = block[profile]
                rows.append(
                    {
                        "candidate_id": cid,
                        "scope": scope,
                        "profile": profile,
                        "total_trades": s["total_trades"],
                        "state_available_trades": s["state_available_trades"],
                        "active_bottom10_trades": s["active_bottom10_trades"],
                        "availability_fraction": s["state_availability_fraction"],
                        "active_fraction": s["active_bottom10_fraction_of_available"],
                        "interaction_difference": s["interaction_difference"],
                        "active_expectancy": s["active_bottom10"]["expectancy"],
                        "normal_expectancy": s["not_bottom10"]["expectancy"],
                        "original_expectancy": s["all_original"]["expectancy"],
                        "veto_expectancy": s["hypothetical_veto_retained"]["expectancy"],
                        "original_net": s["all_original"]["net"],
                        "veto_net": s["hypothetical_veto_retained"]["net"],
                        "original_pf": s["all_original"]["PF"],
                        "veto_pf": s["hypothetical_veto_retained"]["PF"],
                    }
                )
    pd.DataFrame(rows).to_csv(out / "r29_r27_filter_r6_summary.csv", index=False)

    heartbeat(
        progress,
        8,
        8,
        "complete",
        {
            "verdict": gate["status"],
            "protected_2026_opened": False,
        },
    )
    print(
        json.dumps(
            {
                "status": gate["status"],
                "R6B-347_pooled_E1_difference": results["R6B-347"]["pooled"]["E1"][
                    "interaction_difference"
                ],
                "R6B-347_bootstrap_upper": results["R6B-347"][
                    "bootstrap_pooled_e1"
                ]["p975"],
                "R6B-307_pooled_E1_difference": results["R6B-307"]["pooled"]["E1"][
                    "interaction_difference"
                ],
                "protected_2026_opened": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
