#!/usr/bin/env python3
"""Deterministic scoring of completed Guardian research batches.

The scorer does not tune anything. It computes frozen manifest gates from the
immutable CSV evidence referenced by a BATCH_PASS_INTEGRITY receipt.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import experiment
import runner
import tester


class ScoreError(RuntimeError):
    pass


def latest_batch(config: dict[str, Any], experiment_id: str, stage: str) -> Path:
    base = runner._expand_path(config["workspace_dir"]) / "batches" / experiment_id / stage
    candidates = sorted(base.glob("*/batch.json"), reverse=True) if base.exists() else []
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("status") == "BATCH_PASS_INTEGRITY":
            return path
    raise ScoreError(f"no BATCH_PASS_INTEGRITY receipt found for {experiment_id} {stage}")


def load_batch(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScoreError(f"cannot read batch receipt {path}: {exc}") from exc
    if payload.get("status") != "BATCH_PASS_INTEGRITY":
        raise ScoreError(f"batch is not integrity-passed: {payload.get('status')}")
    return payload


def parse_float(row: dict[str, str], field: str, source: Path) -> float:
    try:
        value = float(row[field])
    except (KeyError, ValueError) as exc:
        raise ScoreError(f"invalid {field} in {source}: {row.get(field)!r}") from exc
    if not math.isfinite(value):
        raise ScoreError(f"non-finite {field} in {source}: {value}")
    return value


def entry_year(value: str) -> int:
    try:
        return int(value[:4])
    except (ValueError, TypeError) as exc:
        raise ScoreError(f"cannot parse entry year from {value!r}") from exc


def profit_factor_parts(values: list[float]) -> tuple[float | None, bool]:
    gains = sum(x for x in values if x > 0)
    losses = -sum(x for x in values if x < 0)
    if losses == 0:
        return (None, gains > 0)
    return (gains / losses, False)


def collect_metrics(manifest: dict[str, Any], batch: dict[str, Any], stage: str) -> tuple[dict[str, Any], dict[int, float]]:
    expected_symbols = manifest["stages"][stage]["symbols"]
    tests = batch.get("tests", [])
    seen = [item.get("symbol") for item in tests]
    if seen != expected_symbols:
        raise ScoreError(f"batch symbol order/content mismatch: expected={expected_symbols} got={seen}")

    all_rows: list[dict[str, str]] = []
    rows_by_symbol: dict[str, list[dict[str, str]]] = {}
    integrity_events = 0

    for item in tests:
        symbol = item["symbol"]
        trades_path = Path(item["trades"]["path"])
        stats_path = Path(item["stats"]["path"])
        if not trades_path.is_file() or not stats_path.is_file():
            raise ScoreError(f"evidence file missing for {symbol}")
        if runner.sha256_file(trades_path) != item["trades"]["sha256"]:
            raise ScoreError(f"TRADES SHA mismatch for {symbol}")
        if runner.sha256_file(stats_path) != item["stats"]["sha256"]:
            raise ScoreError(f"STATS SHA mismatch for {symbol}")

        rows = tester.read_semicolon_csv(trades_path)
        rows_by_symbol[symbol] = rows
        all_rows.extend(rows)
        integ = item.get("integrity", {})
        integrity_events += int(integ.get("invalid_price", 0))
        integrity_events += int(integ.get("invalid_risk", 0))
        integrity_events += int(integ.get("pnl_calc_failures", 0))

    net_r = [parse_float(row, "net_r", Path("TRADES")) for row in all_rows]
    stress_r = [parse_float(row, "net_r_commission_x1_5", Path("TRADES")) for row in all_rows]
    pf_value, pf_infinite = profit_factor_parts(net_r)
    per_symbol_n = {symbol: len(rows_by_symbol[symbol]) for symbol in expected_symbols}
    per_symbol_total = {
        symbol: sum(parse_float(row, "net_r", Path(f"TRADES:{symbol}")) for row in rows_by_symbol[symbol])
        for symbol in expected_symbols
    }
    positive_symbols = [symbol for symbol, total in per_symbol_total.items() if total > 0]
    positive_total = sum(per_symbol_total[symbol] for symbol in positive_symbols)
    max_positive_share = (
        max((per_symbol_total[symbol] / positive_total for symbol in positive_symbols), default=0.0)
        if positive_total > 0 else 0.0
    )

    totals_by_year: dict[int, float] = defaultdict(float)
    for row in all_rows:
        totals_by_year[entry_year(row.get("entry_time", ""))] += parse_float(row, "net_r", Path("TRADES"))

    metrics = {
        "aggregate_n": len(all_rows),
        "per_symbol_n": per_symbol_n,
        "aggregate_mean_net_r": (sum(net_r) / len(net_r)) if net_r else 0.0,
        "aggregate_pf": pf_value,
        "aggregate_pf_infinite": pf_infinite,
        "positive_symbols": positive_symbols,
        "positive_symbols_n": len(positive_symbols),
        "per_symbol_total_net_r": per_symbol_total,
        "aggregate_total_net_r": sum(net_r),
        "aggregate_total_stress_net_r": sum(stress_r),
        "year_total_net_r": {str(year): value for year, value in sorted(totals_by_year.items())},
        "max_positive_symbol_contribution_share": max_positive_share,
        "integrity_events": integrity_events,
    }
    return metrics, totals_by_year


def pf_gate(metrics: dict[str, Any], minimum: float) -> bool:
    return bool(
        metrics["aggregate_pf_infinite"]
        or (metrics["aggregate_pf"] is not None and metrics["aggregate_pf"] >= minimum)
    )


def score_development(manifest: dict[str, Any], batch: dict[str, Any]) -> dict[str, Any]:
    metrics, totals_by_year = collect_metrics(manifest, batch, "development")
    gates = manifest["stages"]["development"]["gates"]
    gate_results = {
        "aggregate_n_min": metrics["aggregate_n"] >= int(gates["aggregate_n_min"]),
        "each_symbol_n_min": all(n >= int(gates["each_symbol_n_min"]) for n in metrics["per_symbol_n"].values()),
        "aggregate_mean_net_r_min": metrics["aggregate_mean_net_r"] >= float(gates["aggregate_mean_net_r_min"]),
        "aggregate_pf_min": pf_gate(metrics, float(gates["aggregate_pf_min"])),
        "positive_symbols_min": metrics["positive_symbols_n"] >= int(gates["positive_symbols_min"]),
        "aggregate_2024_positive": totals_by_year.get(2024, 0.0) > 0,
        "aggregate_2025_positive": totals_by_year.get(2025, 0.0) > 0,
        "aggregate_positive_at_commission_stress": metrics["aggregate_total_stress_net_r"] > 0,
        "max_positive_symbol_contribution_share": metrics["max_positive_symbol_contribution_share"] <= float(gates["max_positive_symbol_contribution_share"]),
        "integrity_events_max": metrics["integrity_events"] <= int(gates["integrity_events_max"]),
    }
    passed = all(gate_results.values())
    verdict = "CANDIDATE_CONFIRM" if passed else str(gates.get("failure_verdict", "REJECT_V0"))
    return {"metrics": metrics, "gates": gate_results, "all_gates_pass": passed, "verdict": verdict}


def score_confirmation(manifest: dict[str, Any], batch: dict[str, Any]) -> dict[str, Any]:
    metrics, _ = collect_metrics(manifest, batch, "confirmation")
    gates = manifest["stages"]["confirmation"]["gates"]
    gate_results = {
        "aggregate_n_min": metrics["aggregate_n"] >= int(gates["aggregate_n_min"]),
        "aggregate_mean_net_r_strictly_positive": metrics["aggregate_mean_net_r"] > 0,
        "aggregate_pf_min": pf_gate(metrics, float(gates["aggregate_pf_min"])),
        "positive_symbols_min": metrics["positive_symbols_n"] >= int(gates["positive_symbols_min"]),
        "aggregate_positive_at_commission_stress": metrics["aggregate_total_stress_net_r"] > 0,
        "integrity_events_max": metrics["integrity_events"] <= int(gates["integrity_events_max"]),
    }
    passed = all(gate_results.values())
    verdict = "CONFIRMED" if passed else str(gates.get("failure_verdict", "UNCONFIRMED"))
    return {"metrics": metrics, "gates": gate_results, "all_gates_pass": passed, "verdict": verdict}


def score(identifier: str, stage: str, batch_path: str | None) -> dict[str, Any]:
    _, manifest_path, manifest = runner.load_context(identifier)
    if stage not in {"development", "confirmation"}:
        raise ScoreError("scorer implements frozen development and confirmation gates only")

    config = runner.load_config()
    path = Path(batch_path).resolve() if batch_path else latest_batch(config, manifest["experiment_id"], stage)
    batch = load_batch(path)
    if batch.get("experiment_id") != manifest["experiment_id"] or batch.get("stage") != stage:
        raise ScoreError("batch receipt does not match experiment/stage")

    result = score_development(manifest, batch) if stage == "development" else score_confirmation(manifest, batch)
    payload = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": manifest["experiment_id"],
        "manifest_path": str(manifest_path.relative_to(runner.ROOT)),
        "manifest_source_sha256": manifest["source"]["source_sha256"],
        "batch_path": str(path),
        "stage": stage,
        **result,
        "confirmation_opened": stage == "confirmation",
        "autosync_used": False,
    }

    workspace = runner._expand_path(config["workspace_dir"])
    out_dir = workspace / "scores" / manifest["experiment_id"] / stage / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / "verdict.json"
    runner.write_receipt(out_path, payload)
    return {"verdict_path": str(out_path), **payload}


def main() -> int:
    parser = argparse.ArgumentParser(description="Score frozen Guardian development/confirmation gates")
    parser.add_argument("experiment", help="D0xx or manifest path")
    parser.add_argument("--stage", default="development", choices=("development", "confirmation"))
    parser.add_argument("--batch", help="explicit batch.json; defaults to latest integrity-passed batch")
    args = parser.parse_args()
    try:
        result = score(args.experiment, args.stage, args.batch)
    except (ScoreError, runner.RunnerError, experiment.ManifestError, KeyError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
