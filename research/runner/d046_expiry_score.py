#!/usr/bin/env python3
"""Frozen scorer for D046 BTC 08:00 UTC expiry reversal screening."""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import runner
import tester

SCORING_MODE = "D046_EXPIRY_PAIRED_DAY_BPS_MONTH_BLOCK_BOOTSTRAP"
DEFAULT_RESAMPLES = 20000
DEFAULT_SEED = 460800


class D046ScoreError(RuntimeError):
    pass


def _f(row: dict[str, str], field: str) -> float:
    raw = row.get(field, "")
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise D046ScoreError(f"invalid {field}: {raw!r}") from exc
    if not math.isfinite(value):
        raise D046ScoreError(f"non-finite {field}: {value}")
    return value


def _i(row: dict[str, str], field: str) -> int:
    raw = row.get(field, "")
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise D046ScoreError(f"invalid integer {field}: {raw!r}") from exc


def _profit_factor(values: list[float]) -> dict[str, Any]:
    wins = sum(x for x in values if x > 0)
    losses = abs(sum(x for x in values if x < 0))
    if losses == 0:
        return {"value": None, "infinite": wins > 0}
    return {"value": wins / losses, "infinite": False}


def _pf_pass(pf: dict[str, Any], minimum: float) -> bool:
    if pf.get("infinite"):
        return True
    value = pf.get("value")
    return value is not None and float(value) >= minimum


def _percentile(values: list[float], q: float) -> float:
    if not values:
        raise D046ScoreError("empty percentile sample")
    xs = sorted(values)
    pos = (len(xs) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def _month_from_key(day_key: str) -> str:
    if len(day_key) != 8 or not day_key.isdigit():
        raise D046ScoreError(f"invalid utc_day_key: {day_key!r}")
    return f"{day_key[:4]}-{day_key[4:6]}"


def _year_from_key(day_key: str) -> str:
    if len(day_key) != 8 or not day_key.isdigit():
        raise D046ScoreError(f"invalid utc_day_key: {day_key!r}")
    return day_key[:4]


def month_block_bootstrap(
    paired_days: list[dict[str, Any]],
    *,
    resamples: int = DEFAULT_RESAMPLES,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    blocks: dict[str, list[float]] = defaultdict(list)
    for day in paired_days:
        blocks[_month_from_key(str(day["utc_day_key"]))].append(float(day["combined_net_bps"]))
    months = sorted(blocks)
    if not months:
        return {
            "blocks": 0,
            "resamples": resamples,
            "seed": seed,
            "lower_95": None,
            "median": None,
            "upper_95": None,
        }
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(resamples):
        values: list[float] = []
        for _j in range(len(months)):
            values.extend(blocks[rng.choice(months)])
        means.append(sum(values) / len(values))
    return {
        "blocks": len(months),
        "resamples": resamples,
        "seed": seed,
        "lower_95": _percentile(means, 0.025),
        "median": _percentile(means, 0.5),
        "upper_95": _percentile(means, 0.975),
    }


def pair_rows(rows: list[dict[str, str]]) -> dict[str, Any]:
    eligible: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    leg_counts = {"PRE_SHORT": 0, "POST_LONG": 0}
    ineligible_rows = 0

    for row in rows:
        leg = row.get("leg", "")
        if leg not in {"PRE_SHORT", "POST_LONG"}:
            raise D046ScoreError(f"unexpected leg: {leg!r}")
        if row.get("side") != ("SHORT" if leg == "PRE_SHORT" else "LONG"):
            raise D046ScoreError(f"side mismatch for {leg}: {row.get('side')!r}")
        if row.get("eligible") != "1":
            ineligible_rows += 1
            continue

        entry_delay = _i(row, "entry_delay_seconds")
        exit_delay = _i(row, "exit_delay_seconds")
        if entry_delay < 0 or entry_delay > 300 or exit_delay < 0 or exit_delay > 300:
            raise D046ScoreError(
                f"eligible row exceeds frozen 300s boundary delay: entry={entry_delay} exit={exit_delay}"
            )
        commission = _f(row, "commission_bps")
        if abs(commission - 8.0) > 1e-9:
            raise D046ScoreError(f"commission_bps differs from frozen 8 bps: {commission}")
        for field in ("gross_bps", "net_bps", "net_bps_commission_x1_5"):
            _f(row, field)

        day_key = str(row.get("utc_day_key", ""))
        _month_from_key(day_key)
        if leg in eligible[day_key]:
            raise D046ScoreError(f"duplicate eligible {leg} for utc_day_key={day_key}")
        eligible[day_key][leg] = row
        leg_counts[leg] += 1

    paired: list[dict[str, Any]] = []
    unpaired_days = 0
    for day_key in sorted(eligible):
        legs = eligible[day_key]
        if set(legs) != {"PRE_SHORT", "POST_LONG"}:
            unpaired_days += 1
            continue
        pre = legs["PRE_SHORT"]
        post = legs["POST_LONG"]
        pre_net = _f(pre, "net_bps")
        post_net = _f(post, "net_bps")
        pre_stress = _f(pre, "net_bps_commission_x1_5")
        post_stress = _f(post, "net_bps_commission_x1_5")
        paired.append({
            "utc_day_key": day_key,
            "pre_short_net_bps": pre_net,
            "post_long_net_bps": post_net,
            "combined_net_bps": pre_net + post_net,
            "combined_stress_net_bps": pre_stress + post_stress,
        })

    return {
        "paired_days": paired,
        "eligible_leg_counts": leg_counts,
        "ineligible_rows": ineligible_rows,
        "unpaired_eligible_days": unpaired_days,
    }


def evaluate(rows: list[dict[str, str]], gates: dict[str, Any], stage: str) -> dict[str, Any]:
    paired_info = pair_rows(rows)
    days: list[dict[str, Any]] = paired_info["paired_days"]
    pre = [float(x["pre_short_net_bps"]) for x in days]
    post = [float(x["post_long_net_bps"]) for x in days]
    combined = [float(x["combined_net_bps"]) for x in days]
    stress = [float(x["combined_stress_net_bps"]) for x in days]
    n = len(days)

    pf = _profit_factor(combined)
    resamples = int(gates.get("bootstrap_resamples", DEFAULT_RESAMPLES))
    seed = int(gates.get("bootstrap_seed", DEFAULT_SEED))
    boot = month_block_bootstrap(days, resamples=resamples, seed=seed)
    year_totals: dict[str, float] = defaultdict(float)
    for day in days:
        year_totals[_year_from_key(str(day["utc_day_key"]))] += float(day["combined_net_bps"])

    metrics = {
        "paired_days_n": n,
        "pre_short_mean_net_bps": sum(pre) / n if n else 0.0,
        "post_long_mean_net_bps": sum(post) / n if n else 0.0,
        "combined_day_mean_net_bps": sum(combined) / n if n else 0.0,
        "combined_day_total_net_bps": sum(combined),
        "combined_day_profit_factor": pf,
        "combined_stress_total_net_bps": sum(stress),
        "year_total_net_bps": dict(sorted(year_totals.items())),
        "month_block_bootstrap": boot,
        "eligible_leg_counts": paired_info["eligible_leg_counts"],
        "ineligible_rows": paired_info["ineligible_rows"],
        "unpaired_eligible_days": paired_info["unpaired_eligible_days"],
    }

    lower = boot.get("lower_95")
    gate_results: dict[str, bool] = {
        "paired_days_min": n >= int(gates["paired_days_min"]),
        "pre_short_mean_net_bps_strictly_positive": metrics["pre_short_mean_net_bps"] > 0,
        "post_long_mean_net_bps_strictly_positive": metrics["post_long_mean_net_bps"] > 0,
        "combined_day_mean_net_bps_strictly_positive": metrics["combined_day_mean_net_bps"] > 0,
        "combined_day_pf_min": _pf_pass(pf, float(gates["combined_day_pf_min"])),
        "combined_stress_total_net_bps_positive": metrics["combined_stress_total_net_bps"] > 0,
        "month_block_bootstrap_lower_95_strictly_positive": lower is not None and float(lower) > 0,
        "integrity_events_max": True,
    }
    if stage == "development":
        gate_results["year_2024_total_net_bps_positive"] = year_totals.get("2024", 0.0) > 0
        gate_results["year_2025_total_net_bps_positive"] = year_totals.get("2025", 0.0) > 0

    count_ok = gate_results["paired_days_min"]
    all_pass = all(gate_results.values())
    if not count_ok:
        verdict = str(gates.get("count_failure_verdict", "INCONCLUSIVE_COUNT"))
    elif all_pass:
        verdict = str(gates["pass_verdict"])
    else:
        verdict = str(gates["failure_verdict"])
    return {
        "metrics": metrics,
        "gates": gate_results,
        "all_gates_pass": all_pass,
        "verdict": verdict,
    }


def latest_batch(config: dict[str, Any], experiment_id: str, stage: str) -> Path:
    base = runner._expand_path(config["workspace_dir"]) / "batches" / experiment_id / stage
    candidates = sorted(base.glob("*/batch.json"), reverse=True) if base.exists() else []
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("status") == "BATCH_PASS_INTEGRITY":
            return path
    raise D046ScoreError(f"no integrity-passed batch for {experiment_id} {stage}")


def score(identifier: str, stage: str, batch_path: str | None = None) -> dict[str, Any]:
    _, manifest_path, manifest = runner.load_context(identifier)
    if manifest.get("cost_model", {}).get("scoring_mode") != SCORING_MODE:
        raise D046ScoreError("manifest scoring_mode mismatch")
    if stage not in {"development", "confirmation"}:
        raise D046ScoreError("D046 scorer supports development/confirmation only")

    config = runner.load_config()
    batch_file = Path(batch_path).resolve() if batch_path else latest_batch(config, manifest["experiment_id"], stage)
    batch = json.loads(batch_file.read_text(encoding="utf-8"))
    if batch.get("status") != "BATCH_PASS_INTEGRITY":
        raise D046ScoreError("batch is not integrity-passed")
    tests = batch.get("tests", [])
    if [x.get("symbol") for x in tests] != manifest["stages"][stage]["symbols"]:
        raise D046ScoreError("batch symbol order/content mismatch")
    if len(tests) != 1:
        raise D046ScoreError("D046 requires exactly one BTCUSD test")

    item = tests[0]
    trades_path = Path(item["trades"]["path"])
    stats_path = Path(item["stats"]["path"])
    if runner.sha256_file(trades_path) != item["trades"]["sha256"]:
        raise D046ScoreError("TRADES evidence SHA mismatch")
    if runner.sha256_file(stats_path) != item["stats"]["sha256"]:
        raise D046ScoreError("STATS evidence SHA mismatch")
    rows = tester.read_semicolon_csv(trades_path)
    result = evaluate(rows, manifest["stages"][stage]["gates"], stage)

    created = datetime.now(timezone.utc)
    out_dir = runner._expand_path(config["workspace_dir"]) / "scores" / manifest["experiment_id"] / stage / created.strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=False)
    payload = {
        "schema_version": 1,
        "created_at_utc": created.isoformat(),
        "experiment_id": manifest["experiment_id"],
        "scientific_preregistration": manifest["preregistration"]["path"],
        "scientific_role": "D046_UNCONDITIONAL_08UTC_EXPIRY_REVERSAL_SCREEN",
        "stage": stage,
        "manifest_path": str(manifest_path.relative_to(runner.ROOT)),
        "manifest_source_sha256": manifest["source"]["source_sha256"],
        "batch_path": str(batch_file),
        **result,
        "high_oi_mechanism_tested": False,
        "high_oi_mechanism_boundary": "A D046-A failure rejects only the unconditional screen and does not falsify the historical high-ATM-OI mechanism.",
        "autosync_used": False,
    }
    verdict_path = out_dir / "verdict.json"
    analytics_path = out_dir / "expiry_analytics.json"
    runner.write_receipt(verdict_path, payload)
    runner.write_receipt(analytics_path, {
        "schema_version": 1,
        "created_at_utc": created.isoformat(),
        "experiment_id": manifest["experiment_id"],
        "stage": stage,
        "status": "D046_EXPIRY_ANALYTICS_COMPLETE",
        "metrics": result["metrics"],
        "gates": result["gates"],
        "verdict": result["verdict"],
        "high_oi_mechanism_tested": False,
        "autosync_used": False,
    })
    return {
        "verdict_path": str(verdict_path),
        "analytics_path": str(analytics_path),
        **payload,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score frozen D046 BTC expiry reversal screen")
    parser.add_argument("experiment", nargs="?", default="D046")
    parser.add_argument("--stage", choices=("development", "confirmation"), default="development")
    parser.add_argument("--batch")
    args = parser.parse_args()
    try:
        result = score(args.experiment, args.stage, args.batch)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
