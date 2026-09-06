#!/usr/bin/env python3
"""Rich descriptive analytics for an integrity-passed Guardian research batch.

score.py owns frozen decision gates. This module is descriptive only: it may
extract and summarize native Trade Path telemetry, but it MUST NOT alter an
experiment verdict or open confirmation.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import experiment
import runner
import score
import tester


class RichScoreError(RuntimeError):
    pass


TRADE_PATH_MILESTONES = [
    ("0_5r", "0.5R"),
    ("1r", "1R"),
    ("2r", "2R"),
    ("3r", "3R"),
    ("5r", "5R"),
]

TRADE_PATH_REQUIRED_FIELDS = [
    "trade_id",
    "mfe_r",
    "mae_r",
    "time_to_mfe_minutes",
    "time_to_mae_minutes",
    "max_retracement_from_mfe_r",
    "reached_0_5r",
    "first_touch_0_5r_time",
    "time_to_0_5r_minutes",
    "mae_before_0_5r",
    "reached_1r",
    "first_touch_1r_time",
    "time_to_1r_minutes",
    "mae_before_1r",
    "reached_2r",
    "first_touch_2r_time",
    "time_to_2r_minutes",
    "mae_before_2r",
    "reached_3r",
    "first_touch_3r_time",
    "time_to_3r_minutes",
    "mae_before_3r",
    "reached_5r",
    "first_touch_5r_time",
    "time_to_5r_minutes",
    "mae_before_5r",
    "path_ambiguous",
    "path_ambiguity_reason",
]


def parse_time(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y.%m.%d %H:%M")
    except (TypeError, ValueError) as exc:
        raise RichScoreError(f"cannot parse MQL5 time {value!r}") from exc


def parse_float(row: dict[str, str], field: str, source: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, ValueError) as exc:
        raise RichScoreError(f"invalid {field} in {source}: {row.get(field)!r}") from exc
    if not math.isfinite(value):
        raise RichScoreError(f"non-finite {field} in {source}: {value}")
    return value


def parse_optional_float(row: dict[str, Any], field: str, source: str) -> float | None:
    raw = row.get(field)
    if raw in (None, ""):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise RichScoreError(f"invalid {field} in {source}: {raw!r}") from exc
    if not math.isfinite(value):
        raise RichScoreError(f"non-finite {field} in {source}: {value}")
    return value


def parse_flag(row: dict[str, Any], field: str, source: str) -> bool:
    raw = str(row.get(field, ""))
    if raw not in {"0", "1"}:
        raise RichScoreError(f"{field} must be 0/1 in {source}: {raw!r}")
    return raw == "1"


def quantile(values: Iterable[float], q: float) -> float | None:
    xs = sorted(values)
    if not xs:
        return None
    if q <= 0:
        return xs[0]
    if q >= 1:
        return xs[-1]
    pos = (len(xs) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    weight = pos - lo
    return xs[lo] * (1.0 - weight) + xs[hi] * weight


def distribution(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "n": 0,
            "mean": None,
            "median": None,
            "stdev_population": None,
            "min": None,
            "p05": None,
            "p10": None,
            "p25": None,
            "p75": None,
            "p90": None,
            "p95": None,
            "max": None,
        }
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "stdev_population": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "p05": quantile(values, 0.05),
        "p10": quantile(values, 0.10),
        "p25": quantile(values, 0.25),
        "p75": quantile(values, 0.75),
        "p90": quantile(values, 0.90),
        "p95": quantile(values, 0.95),
        "max": max(values),
    }


def profit_factor(values: list[float]) -> dict[str, Any]:
    value, infinite = score.profit_factor_parts(values)
    return {"value": value, "infinite": infinite}


def max_drawdown_r(values: list[float]) -> dict[str, Any]:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    trough_equity = 0.0
    peak_index = -1
    trough_index = -1
    current_peak_index = -1
    for i, value in enumerate(values):
        equity += value
        if equity > peak:
            peak = equity
            current_peak_index = i
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
            trough_equity = equity
            peak_index = current_peak_index
            trough_index = i
    return {
        "max_drawdown_r": max_dd,
        "peak_index": peak_index,
        "trough_index": trough_index,
        "trough_equity_r": trough_equity,
    }


def longest_streak(values: list[float], positive: bool) -> int:
    best = 0
    current = 0
    for value in values:
        hit = value > 0 if positive else value < 0
        if hit:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def summarize_values(values: list[float]) -> dict[str, Any]:
    wins = [x for x in values if x > 0]
    losses = [x for x in values if x < 0]
    flats = len(values) - len(wins) - len(losses)
    avg_win = statistics.fmean(wins) if wins else None
    avg_loss = statistics.fmean(losses) if losses else None
    payoff = (avg_win / abs(avg_loss)) if avg_win is not None and avg_loss not in (None, 0.0) else None
    return {
        "distribution": distribution(values),
        "profit_factor": profit_factor(values),
        "wins": len(wins),
        "losses": len(losses),
        "flats": flats,
        "win_rate": (len(wins) / len(values)) if values else None,
        "loss_rate": (len(losses) / len(values)) if values else None,
        "average_win_r": avg_win,
        "average_loss_r": avg_loss,
        "payoff_ratio_avg_win_to_abs_avg_loss": payoff,
        "total_r": sum(values),
    }


def grouped_summary(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)
    out: dict[str, Any] = {}
    for name in sorted(groups):
        items = groups[name]
        values = [float(item["_net_r"]) for item in items]
        durations = [float(item["_duration_minutes"]) for item in items]
        out[name] = {
            **summarize_values(values),
            "duration_minutes": distribution(durations),
        }
    return out


def two_dimensional_matrix(rows: list[dict[str, Any]], first: str, second: str) -> dict[str, Any]:
    matrix: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        matrix[str(row[first])][str(row[second])].append(float(row["_net_r"]))
    return {
        outer: {
            inner: {
                "n": len(values),
                "total_net_r": sum(values),
                "mean_net_r": statistics.fmean(values) if values else None,
                "profit_factor": profit_factor(values),
            }
            for inner, values in sorted(inner_map.items())
        }
        for outer, inner_map in sorted(matrix.items())
    }


def period_sign_counts(grouped: dict[str, Any]) -> dict[str, int]:
    totals = [float(item["total_r"]) for item in grouped.values()]
    return {
        "positive": sum(1 for value in totals if value > 0),
        "negative": sum(1 for value in totals if value < 0),
        "flat": sum(1 for value in totals if value == 0),
    }


def concentration(values: list[float]) -> dict[str, Any]:
    sorted_desc = sorted(values, reverse=True)
    sorted_asc = sorted(values)
    positives = [x for x in sorted_desc if x > 0]
    negatives = [x for x in sorted_asc if x < 0]
    total_net = sum(values)
    positive_total = sum(positives)
    negative_total_abs = abs(sum(negatives))

    def top_percent(pct: float) -> dict[str, Any]:
        count = max(1, math.ceil(len(values) * pct)) if values else 0
        contribution = sum(sorted_desc[:count]) if count else 0.0
        return {
            "trade_count": count,
            "contribution_r": contribution,
            "share_of_total_net_r": (contribution / total_net) if total_net > 0 else None,
            "share_of_total_positive_r": (
                sum(x for x in sorted_desc[:count] if x > 0) / positive_total
            ) if positive_total > 0 else None,
        }

    def bottom_percent(pct: float) -> dict[str, Any]:
        count = max(1, math.ceil(len(values) * pct)) if values else 0
        contribution = sum(sorted_asc[:count]) if count else 0.0
        return {
            "trade_count": count,
            "contribution_r": contribution,
            "share_of_total_negative_r_abs": (
                abs(sum(x for x in sorted_asc[:count] if x < 0)) / negative_total_abs
            ) if negative_total_abs > 0 else None,
        }

    return {
        "total_net_r": total_net,
        "positive_r_total": positive_total,
        "negative_r_total_abs": negative_total_abs,
        "top_1pct": top_percent(0.01),
        "top_5pct": top_percent(0.05),
        "top_10pct": top_percent(0.10),
        "bottom_1pct": bottom_percent(0.01),
        "bottom_5pct": bottom_percent(0.05),
        "bottom_10pct": bottom_percent(0.10),
    }


def threshold_summary(values: list[float]) -> dict[str, Any]:
    n = len(values)
    positive_levels = (0.5, 1.0, 2.0, 3.0, 5.0)
    negative_levels = (-0.5, -1.0, -2.0)
    return {
        "note": "REALIZED exit-R thresholds only. Native intratrade touches are reported separately when Trade Path is available.",
        "realized_at_or_above": {
            f"{level:g}R": {
                "n": sum(1 for x in values if x >= level),
                "rate": (sum(1 for x in values if x >= level) / n) if n else None,
            }
            for level in positive_levels
        },
        "realized_at_or_below": {
            f"{level:g}R": {
                "n": sum(1 for x in values if x <= level),
                "rate": (sum(1 for x in values if x <= level) / n) if n else None,
            }
            for level in negative_levels
        },
    }


def _trade_path_fields_present(rows: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    if not rows:
        return False, list(TRADE_PATH_REQUIRED_FIELDS)
    missing = [
        field
        for field in TRADE_PATH_REQUIRED_FIELDS
        if any(field not in row for row in rows)
    ]
    return not missing, missing


def _path_group_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    mfe = [parse_float(row, "mfe_r", f"TRADE_PATH:{row.get('symbol')}") for row in rows]
    mae = [parse_float(row, "mae_r", f"TRADE_PATH:{row.get('symbol')}") for row in rows]
    retrace = [
        parse_float(row, "max_retracement_from_mfe_r", f"TRADE_PATH:{row.get('symbol')}")
        for row in rows
    ]
    mfe_minus_gross = [
        parse_float(row, "mfe_r", "TRADE_PATH") - float(row["_gross_r"])
        for row in rows
    ]
    capture_ratio = [
        float(row["_gross_r"]) / parse_float(row, "mfe_r", "TRADE_PATH")
        for row in rows
        if parse_float(row, "mfe_r", "TRADE_PATH") > 0
    ]
    winners = [row for row in rows if float(row["_net_r"]) > 0]
    losers = [row for row in rows if float(row["_net_r"]) < 0]

    milestones: dict[str, Any] = {}
    hit_counts: dict[str, int] = {}
    for suffix, label in TRADE_PATH_MILESTONES:
        reached_rows = [row for row in rows if parse_flag(row, f"reached_{suffix}", "TRADE_PATH")]
        not_reached_rows = [row for row in rows if not parse_flag(row, f"reached_{suffix}", "TRADE_PATH")]
        hit_counts[label] = len(reached_rows)
        times = [
            parse_float(row, f"time_to_{suffix}_minutes", "TRADE_PATH")
            for row in reached_rows
        ]
        mae_before = [
            parse_float(row, f"mae_before_{suffix}", "TRADE_PATH")
            for row in reached_rows
        ]
        post_touch: dict[str, Any] = {}
        if suffix in {"1r", "2r", "3r"}:
            mins = [
                parse_optional_float(row, f"min_r_after_first_{suffix}_before_exit", "TRADE_PATH")
                for row in reached_rows
            ]
            maxs = [
                parse_optional_float(row, f"max_r_after_first_{suffix}_before_exit", "TRADE_PATH")
                for row in reached_rows
            ]
            paired = [
                (row, low, high)
                for row, low, high in zip(reached_rows, mins, maxs)
                if low is not None and high is not None
            ]
            giveback_to_gross_exit = [
                float(high) - float(row["_gross_r"])
                for row, _low, high in paired
            ]
            post_touch = {
                "min_r_before_exit": distribution([float(low) for _row, low, _high in paired]),
                "max_r_before_exit": distribution([float(high) for _row, _low, high in paired]),
                "giveback_from_post_touch_peak_to_gross_exit_r": distribution(giveback_to_gross_exit),
            }

        milestones[label] = {
            "reached_n": len(reached_rows),
            "reached_rate": (len(reached_rows) / n) if n else None,
            "not_reached_n": len(not_reached_rows),
            "time_to_touch_minutes": distribution(times),
            "mae_before_touch_r": distribution(mae_before),
            "final_net_r_if_reached": summarize_values([float(row["_net_r"]) for row in reached_rows]),
            "final_net_r_if_not_reached": summarize_values([float(row["_net_r"]) for row in not_reached_rows]),
            "stop_after_touch_n": sum(1 for row in reached_rows if row.get("exit_reason") == "STOP"),
            "eod_after_touch_n": sum(1 for row in reached_rows if row.get("exit_reason") == "EOD"),
            **({"post_touch_path": post_touch} if post_touch else {}),
        }

    conversions: dict[str, Any] = {}
    previous_label: str | None = None
    for _suffix, label in TRADE_PATH_MILESTONES:
        if previous_label is not None:
            denom = hit_counts[previous_label]
            conversions[f"{previous_label}_to_{label}"] = hit_counts[label] / denom if denom else None
        previous_label = label

    loser_opportunity = {
        label: {
            "n": sum(1 for row in losers if parse_flag(row, f"reached_{suffix}", "TRADE_PATH")),
            "rate_of_losers": (
                sum(1 for row in losers if parse_flag(row, f"reached_{suffix}", "TRADE_PATH")) / len(losers)
                if losers else None
            ),
        }
        for suffix, label in TRADE_PATH_MILESTONES
    }

    return {
        "trades": n,
        "mfe_r": distribution(mfe),
        "mae_r": distribution(mae),
        "max_retracement_from_mfe_r": distribution(retrace),
        "mfe_minus_gross_exit_r": distribution(mfe_minus_gross),
        "gross_exit_capture_ratio_of_mfe": distribution(capture_ratio),
        "mae_r_winners": distribution([parse_float(row, "mae_r", "TRADE_PATH") for row in winners]),
        "mae_r_losers": distribution([parse_float(row, "mae_r", "TRADE_PATH") for row in losers]),
        "mfe_r_winners": distribution([parse_float(row, "mfe_r", "TRADE_PATH") for row in winners]),
        "mfe_r_losers": distribution([parse_float(row, "mfe_r", "TRADE_PATH") for row in losers]),
        "milestones": milestones,
        "milestone_conversion_rates": conversions,
        "losers_that_previously_reached_milestone": loser_opportunity,
    }


def trade_path_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    available, missing = _trade_path_fields_present(rows)
    if not available:
        return {
            "available": False,
            "reason": "required native Trade Path fields are not present in every trade row",
            "missing_fields": missing,
            "contract": "research/runner/TRADE_PATH_DATASET_SPEC.md",
        }

    ambiguous_rows = [row for row in rows if parse_flag(row, "path_ambiguous", "TRADE_PATH")]
    by_symbol = {
        symbol: _path_group_summary([row for row in rows if row["symbol"] == symbol])
        for symbol in sorted({str(row["symbol"]) for row in rows})
    }
    overall = _path_group_summary(rows)
    overall.update({
        "available": True,
        "contract": "research/runner/TRADE_PATH_DATASET_SPEC.md",
        "path_rows": len(rows),
        "path_ambiguous_rows": len(ambiguous_rows),
        "path_ambiguity_reasons": dict(sorted(Counter(str(row.get("path_ambiguity_reason", "")) for row in ambiguous_rows).items())),
        "by_symbol": by_symbol,
        "scientific_boundary": (
            "Descriptive Trade Path analytics only. They may motivate a separately preregistered Exit Lab/D0xx experiment, "
            "but cannot rescue or modify the originating experiment verdict."
        ),
    })
    return overall


def load_rows(manifest: dict[str, Any], batch_payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    expected_symbols = manifest["stages"][batch_payload["stage"]]["symbols"]
    tests = batch_payload.get("tests", [])
    if [item.get("symbol") for item in tests] != expected_symbols:
        raise RichScoreError("batch symbol order/content does not match manifest")

    rows: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    for item in tests:
        symbol = item["symbol"]
        trades_path = Path(item["trades"]["path"])
        stats_path = Path(item["stats"]["path"])
        for path, expected_sha, label in (
            (trades_path, item["trades"]["sha256"], "TRADES"),
            (stats_path, item["stats"]["sha256"], "STATS"),
        ):
            if not path.is_file():
                raise RichScoreError(f"missing {label} evidence for {symbol}: {path}")
            actual = runner.sha256_file(path)
            if actual != expected_sha:
                raise RichScoreError(f"{label} SHA mismatch for {symbol}: expected={expected_sha} actual={actual}")

        source_rows = tester.read_semicolon_csv(trades_path)
        for raw in source_rows:
            row: dict[str, Any] = dict(raw)
            entry = parse_time(row["entry_time"])
            exit_time = parse_time(row["exit_time"])
            duration = (exit_time - entry).total_seconds() / 60.0
            if duration < 0:
                raise RichScoreError(f"negative trade duration for {symbol}: {row['entry_time']} -> {row['exit_time']}")
            row["_entry_dt"] = entry
            row["_exit_dt"] = exit_time
            row["_duration_minutes"] = duration
            row["_net_r"] = parse_float(row, "net_r", f"TRADES:{symbol}")
            row["_gross_r"] = parse_float(row, "gross_r", f"TRADES:{symbol}")
            row["_commission_r"] = parse_float(row, "commission_r", f"TRADES:{symbol}")
            row["_stress_r"] = parse_float(row, "net_r_commission_x1_5", f"TRADES:{symbol}")
            row["_risk_money"] = parse_float(row, "risk_money_1lot_usd", f"TRADES:{symbol}")
            row["_year"] = entry.year
            row["_month"] = f"{entry.year:04d}-{entry.month:02d}"
            row["_entry_hour"] = f"{entry.hour:02d}"
            row["_weekday"] = entry.strftime("%A")
            rows.append(row)

        evidence.append({
            "symbol": symbol,
            "tester_model": item.get("tester_model"),
            "source_sha256": item.get("source_sha256"),
            "ex5_sha256": item.get("ex5_sha256"),
            "trades": {"name": trades_path.name, "sha256": item["trades"]["sha256"], "bytes": trades_path.stat().st_size},
            "stats": {"name": stats_path.name, "sha256": item["stats"]["sha256"], "bytes": stats_path.stat().st_size},
            "integrity": item.get("integrity", {}),
        })
    return rows, evidence


def write_compact_trades(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    original_fields = [key for key in rows[0].keys() if not key.startswith("_")]
    fields = [*original_fields, "duration_minutes"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in sorted(rows, key=lambda x: (x["_entry_dt"], x["symbol"], x["exit_time"])):
            payload = {field: row.get(field, "") for field in original_fields}
            payload["duration_minutes"] = f"{row['_duration_minutes']:.6f}"
            writer.writerow(payload)


def rich_score(identifier: str, stage: str, batch_path: str | None = None) -> dict[str, Any]:
    _, manifest_path, manifest = runner.load_context(identifier)
    if stage != "development":
        raise RichScoreError("v1 rich scorer currently supports development only")
    config = runner.load_config()
    batch_file = Path(batch_path).resolve() if batch_path else score.latest_batch(config, manifest["experiment_id"], stage)
    batch_payload = score.load_batch(batch_file)
    if batch_payload.get("experiment_id") != manifest["experiment_id"] or batch_payload.get("stage") != stage:
        raise RichScoreError("batch receipt does not match experiment/stage")

    rows, evidence = load_rows(manifest, batch_payload)
    realized_close_order = sorted(rows, key=lambda x: (x["_exit_dt"], x["symbol"], x["entry_time"]))
    net = [float(row["_net_r"]) for row in realized_close_order]
    gross = [float(row["_gross_r"]) for row in realized_close_order]
    stress = [float(row["_stress_r"]) for row in realized_close_order]
    commission = [float(row["_commission_r"]) for row in realized_close_order]
    durations = [float(row["_duration_minutes"]) for row in realized_close_order]
    risk_money = [float(row["_risk_money"]) for row in realized_close_order]

    by_symbol = grouped_summary(rows, "symbol")
    by_year = grouped_summary(rows, "_year")
    by_month = grouped_summary(rows, "_month")
    dd = max_drawdown_r(net)
    total_net = sum(net)
    total_gross = sum(gross)
    analytics = {
        "scope": {
            "trades": len(rows),
            "symbols": manifest["stages"][stage]["symbols"],
            "from": manifest["stages"][stage]["from"],
            "to": manifest["stages"][stage]["to"],
            "timeframe": manifest["execution"]["timeframe"],
            "tester_model": batch_payload.get("tester_model"),
        },
        "net_r": summarize_values(net),
        "gross_r": summarize_values(gross),
        "commission_stress_1_5x_r": summarize_values(stress),
        "commission_drag": {
            "commission_r_distribution": distribution(commission),
            "total_commission_r": sum(commission),
            "mean_commission_r": statistics.fmean(commission) if commission else None,
            "gross_total_r": total_gross,
            "net_total_r": total_net,
            "stress_total_r": sum(stress),
            "commission_share_of_gross_total_r": (sum(commission) / total_gross) if total_gross != 0 else None,
        },
        "duration_minutes": distribution(durations),
        "risk_money_1lot_usd": distribution(risk_money),
        "realized_trade_close_curve_r": {
            "ordering": "exit_time_then_symbol",
            "note": "Realized trade-close R curve; not concurrent mark-to-market portfolio drawdown.",
            **dd,
            "ending_equity_r": total_net,
            "recovery_factor_total_r_over_max_dd": (total_net / dd["max_drawdown_r"]) if dd["max_drawdown_r"] > 0 else None,
            "longest_winning_streak": longest_streak(net, True),
            "longest_losing_streak": longest_streak(net, False),
        },
        "concentration": concentration(net),
        "realized_r_thresholds": threshold_summary(net),
        "by_symbol": by_symbol,
        "by_asset_class": grouped_summary(rows, "asset_class"),
        "by_side": grouped_summary(rows, "side"),
        "by_exit_reason": grouped_summary(rows, "exit_reason"),
        "by_year": by_year,
        "by_month": by_month,
        "symbol_x_year": two_dimensional_matrix(rows, "symbol", "_year"),
        "period_sign_counts": {
            "symbols": period_sign_counts(by_symbol),
            "years": period_sign_counts(by_year),
            "months": period_sign_counts(by_month),
        },
        "descriptive_only_entry_time_breakdowns": {
            "by_entry_hour": grouped_summary(rows, "_entry_hour"),
            "by_weekday": grouped_summary(rows, "_weekday"),
            "warning": "Descriptive only. These breakdowns do not authorize post-hoc filters in the originating experiment.",
        },
        "exit_reason_counts": dict(sorted(Counter(str(row["exit_reason"]) for row in rows).items())),
        "side_counts": dict(sorted(Counter(str(row["side"]) for row in rows).items())),
        "trade_path": trade_path_summary(rows),
    }

    workspace = runner._expand_path(config["workspace_dir"])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = workspace / "rich_scores" / manifest["experiment_id"] / stage / stamp
    out_dir.mkdir(parents=True, exist_ok=False)
    compact_path = out_dir / "trades_compact.csv"
    write_compact_trades(compact_path, rows)

    payload = {
        "schema_version": 2,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": manifest["experiment_id"],
        "manifest_path": str(manifest_path.relative_to(runner.ROOT)),
        "manifest_source_sha256": manifest["source"]["source_sha256"],
        "batch_path": str(batch_file),
        "stage": stage,
        "role": "DESCRIPTIVE_ANALYTICS_ONLY_DOES_NOT_CHANGE_DECISION_VERDICT",
        "analytics": analytics,
        "evidence": evidence,
        "compact_trades": {
            "path": str(compact_path),
            "sha256": runner.sha256_file(compact_path),
            "bytes": compact_path.stat().st_size,
            "rows": len(rows),
            "includes_native_trade_path_fields": analytics["trade_path"].get("available") is True,
        },
        "autosync_used": False,
    }
    out_path = out_dir / "rich_score.json"
    runner.write_receipt(out_path, payload)
    return {"rich_score_path": str(out_path), **payload}


def main() -> int:
    parser = argparse.ArgumentParser(description="Create rich descriptive analytics from a Guardian batch")
    parser.add_argument("experiment")
    parser.add_argument("--stage", default="development", choices=("development",))
    parser.add_argument("--batch")
    args = parser.parse_args()
    try:
        result = rich_score(args.experiment, args.stage, args.batch)
    except (RichScoreError, score.ScoreError, runner.RunnerError, experiment.ManifestError, tester.TestError, KeyError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
