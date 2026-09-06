#!/usr/bin/env python3
"""Validate native Trade Path telemetry from already-collected Guardian runs.

This tool never launches MT5. It re-reads immutable run evidence and verifies
that path counters, schema fields, and reached-milestone values are coherent.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path
from typing import Any

import experiment
import runner
import tester

REQUIRED_PATH_COLUMNS = [
    "trade_id",
    "mfe_r", "mae_r", "mfe_time", "mae_time",
    "time_to_mfe_minutes", "time_to_mae_minutes",
    "max_retracement_from_mfe_r",
    "reached_0_5r", "first_touch_0_5r_time", "time_to_0_5r_minutes", "mae_before_0_5r",
    "reached_1r", "first_touch_1r_time", "time_to_1r_minutes", "mae_before_1r",
    "reached_2r", "first_touch_2r_time", "time_to_2r_minutes", "mae_before_2r",
    "reached_3r", "first_touch_3r_time", "time_to_3r_minutes", "mae_before_3r",
    "reached_5r", "first_touch_5r_time", "time_to_5r_minutes", "mae_before_5r",
    "min_r_after_first_1r_before_exit", "max_r_after_first_1r_before_exit",
    "min_r_after_first_2r_before_exit", "max_r_after_first_2r_before_exit",
    "min_r_after_first_3r_before_exit", "max_r_after_first_3r_before_exit",
    "path_ambiguous", "path_ambiguity_reason",
]

MILESTONES = [
    ("0_5r", "0.5R"),
    ("1r", "1R"),
    ("2r", "2R"),
    ("3r", "3R"),
    ("5r", "5R"),
]


class TradePathError(RuntimeError):
    pass


def _parse_csv(path: Path) -> tuple[list[str], list[dict[str, str]], str]:
    text, encoding = tester.decode_csv_text(path)
    with io.StringIO(text, newline="") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    return fields, rows, encoding


def _int(value: str | None, label: str) -> int:
    try:
        return int(value or "")
    except ValueError as exc:
        raise TradePathError(f"invalid integer {label}={value!r}") from exc


def _float(value: str | None, label: str, *, allow_blank: bool = False) -> float | None:
    if allow_blank and (value is None or value == ""):
        return None
    try:
        result = float(value or "")
    except ValueError as exc:
        raise TradePathError(f"invalid numeric {label}={value!r}") from exc
    if result != result or result in (float("inf"), float("-inf")):
        raise TradePathError(f"non-finite numeric {label}={value!r}")
    return result


def validate_paths(stats_path: Path, trades_path: Path) -> dict[str, Any]:
    stats_fields, stats, stats_encoding = _parse_csv(stats_path)
    trade_fields, trades, trades_encoding = _parse_csv(trades_path)
    if not stats:
        raise TradePathError("STATS CSV has no data rows")
    final = stats[-1]
    if final.get("status") != "FINAL":
        raise TradePathError(f"run final status is not FINAL: {final.get('status')}")

    for field in ("path_rows", "path_calc_failures", "csv_trade_rows", "trades_opened", "trades_closed"):
        if field not in stats_fields:
            raise TradePathError(f"STATS missing Trade Path field: {field}")

    path_rows = _int(final.get("path_rows"), "path_rows")
    path_failures = _int(final.get("path_calc_failures"), "path_calc_failures")
    csv_rows = _int(final.get("csv_trade_rows"), "csv_trade_rows")
    opened = _int(final.get("trades_opened"), "trades_opened")
    closed = _int(final.get("trades_closed"), "trades_closed")
    if not (opened == closed == csv_rows == path_rows == len(trades)):
        raise TradePathError(
            "Trade Path lifecycle mismatch: "
            f"opened={opened} closed={closed} csv_rows={csv_rows} path_rows={path_rows} parsed={len(trades)}"
        )
    if path_failures != 0:
        raise TradePathError(f"path_calc_failures must be zero, got {path_failures}")

    missing = [field for field in REQUIRED_PATH_COLUMNS if field not in trade_fields]
    if missing:
        raise TradePathError(f"TRADES missing required Trade Path columns: {missing}")

    reached_counts = {label: 0 for _, label in MILESTONES}
    ambiguous_rows = 0
    for index, row in enumerate(trades, start=1):
        trade_id = row.get("trade_id", "")
        if not trade_id:
            raise TradePathError(f"row {index}: empty trade_id")

        mfe = _float(row.get("mfe_r"), f"row {index} mfe_r")
        mae = _float(row.get("mae_r"), f"row {index} mae_r")
        retrace = _float(row.get("max_retracement_from_mfe_r"), f"row {index} max_retracement_from_mfe_r")
        if mfe is None or mfe < 0:
            raise TradePathError(f"row {index}: mfe_r must be >= 0")
        if mae is None or mae < 0:
            raise TradePathError(f"row {index}: mae_r must be >= 0")
        if retrace is None or retrace < 0:
            raise TradePathError(f"row {index}: max_retracement_from_mfe_r must be >= 0")

        for suffix, label in MILESTONES:
            reached = row.get(f"reached_{suffix}")
            if reached not in {"0", "1"}:
                raise TradePathError(f"row {index}: reached_{suffix} must be 0/1, got {reached!r}")
            if reached == "1":
                reached_counts[label] += 1
                if not row.get(f"first_touch_{suffix}_time"):
                    raise TradePathError(f"row {index}: reached {label} but first-touch timestamp is empty")
                minutes = _float(row.get(f"time_to_{suffix}_minutes"), f"row {index} time_to_{suffix}_minutes")
                before = _float(row.get(f"mae_before_{suffix}"), f"row {index} mae_before_{suffix}")
                if minutes is None or minutes < 0:
                    raise TradePathError(f"row {index}: time to {label} must be >= 0")
                if before is None or before < 0:
                    raise TradePathError(f"row {index}: MAE before {label} must be >= 0")
            else:
                _float(row.get(f"time_to_{suffix}_minutes"), f"row {index} time_to_{suffix}_minutes", allow_blank=True)
                _float(row.get(f"mae_before_{suffix}"), f"row {index} mae_before_{suffix}", allow_blank=True)

        ambiguous = row.get("path_ambiguous")
        if ambiguous not in {"0", "1"}:
            raise TradePathError(f"row {index}: path_ambiguous must be 0/1, got {ambiguous!r}")
        if ambiguous == "1":
            ambiguous_rows += 1
            if not row.get("path_ambiguity_reason"):
                raise TradePathError(f"row {index}: ambiguous path lacks reason")

    return {
        "status": "TRADE_PATH_PASS",
        "trades": len(trades),
        "path_rows": path_rows,
        "path_calc_failures": path_failures,
        "required_columns": len(REQUIRED_PATH_COLUMNS),
        "reached_counts": reached_counts,
        "path_ambiguous_rows": ambiguous_rows,
        "stats_encoding": stats_encoding,
        "trades_encoding": trades_encoding,
    }


def _latest_run_dir(identifier: str, stage: str, symbol: str) -> Path:
    _, _, manifest = runner.load_context(identifier)
    config = runner.load_config()
    base = runner._expand_path(config["workspace_dir"]) / "runs" / manifest["experiment_id"] / stage
    candidates = sorted(base.glob(f"*_{tester.clean_symbol(symbol)}_M*"), reverse=True) if base.exists() else []
    for run_dir in candidates:
        if (run_dir / "run.json").is_file():
            return run_dir
    raise TradePathError(f"no completed run found for {identifier} {stage} {symbol}")


def validate_latest(identifier: str, stage: str, symbol: str) -> dict[str, Any]:
    _, _, manifest = runner.load_context(identifier)
    run_dir = _latest_run_dir(identifier, stage, symbol)
    run_payload = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    stats = Path(run_payload["stats"]["path"])
    trades = Path(run_payload["trades"]["path"])
    result = validate_paths(stats, trades)
    return {
        "schema_version": 1,
        "experiment_id": manifest["experiment_id"],
        "stage": stage,
        "symbol": symbol,
        "run_dir": str(run_dir),
        **result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate native Guardian Trade Path telemetry without running MT5")
    parser.add_argument("experiment", help="D038 or manifest path")
    parser.add_argument("--stage", required=True, choices=("smoke", "development", "confirmation"))
    parser.add_argument("--symbol", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(validate_latest(args.experiment, args.stage, args.symbol), indent=2, ensure_ascii=False))
    except (TradePathError, tester.TestError, runner.RunnerError, experiment.ManifestError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
