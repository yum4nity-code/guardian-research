#!/usr/bin/env python3
"""Stage-generic rich descriptive analytics for Guardian research batches.

This module deliberately reuses the proven analytics primitives from rich_score.py
and only removes the old development-only stage restriction. It supports frozen
development and confirmation batches without changing scientific verdicts.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import experiment
import rich_score as base
import runner
import score
import tester

RichScoreError = base.RichScoreError
SUPPORTED_STAGES = {"development", "confirmation"}


def rich_score(identifier: str, stage: str, batch_path: str | None = None) -> dict[str, Any]:
    _, manifest_path, manifest = runner.load_context(identifier)
    if stage not in SUPPORTED_STAGES:
        raise RichScoreError(f"rich scorer supports only {sorted(SUPPORTED_STAGES)}")

    config = runner.load_config()
    batch_file = Path(batch_path).resolve() if batch_path else score.latest_batch(config, manifest["experiment_id"], stage)
    batch_payload = score.load_batch(batch_file)
    if batch_payload.get("experiment_id") != manifest["experiment_id"] or batch_payload.get("stage") != stage:
        raise RichScoreError("batch receipt does not match experiment/stage")

    rows, evidence = base.load_rows(manifest, batch_payload)
    realized_close_order = sorted(rows, key=lambda x: (x["_exit_dt"], x["symbol"], x["entry_time"]))
    net = [float(row["_net_r"]) for row in realized_close_order]
    gross = [float(row["_gross_r"]) for row in realized_close_order]
    stress = [float(row["_stress_r"]) for row in realized_close_order]
    commission = [float(row["_commission_r"]) for row in realized_close_order]
    durations = [float(row["_duration_minutes"]) for row in realized_close_order]
    risk_money = [float(row["_risk_money"]) for row in realized_close_order]

    by_symbol = base.grouped_summary(rows, "symbol")
    by_year = base.grouped_summary(rows, "_year")
    by_month = base.grouped_summary(rows, "_month")
    dd = base.max_drawdown_r(net)
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
        "net_r": base.summarize_values(net),
        "gross_r": base.summarize_values(gross),
        "commission_stress_1_5x_r": base.summarize_values(stress),
        "commission_drag": {
            "commission_r_distribution": base.distribution(commission),
            "total_commission_r": sum(commission),
            "mean_commission_r": statistics.fmean(commission) if commission else None,
            "gross_total_r": total_gross,
            "net_total_r": total_net,
            "stress_total_r": sum(stress),
            "commission_share_of_gross_total_r": (sum(commission) / total_gross) if total_gross != 0 else None,
        },
        "duration_minutes": base.distribution(durations),
        "risk_money_1lot_usd": base.distribution(risk_money),
        "realized_trade_close_curve_r": {
            "ordering": "exit_time_then_symbol",
            "note": "Realized trade-close R curve; not concurrent mark-to-market portfolio drawdown.",
            **dd,
            "ending_equity_r": total_net,
            "recovery_factor_total_r_over_max_dd": (total_net / dd["max_drawdown_r"]) if dd["max_drawdown_r"] > 0 else None,
            "longest_winning_streak": base.longest_streak(net, True),
            "longest_losing_streak": base.longest_streak(net, False),
        },
        "concentration": base.concentration(net),
        "realized_r_thresholds": base.threshold_summary(net),
        "by_symbol": by_symbol,
        "by_asset_class": base.grouped_summary(rows, "asset_class"),
        "by_side": base.grouped_summary(rows, "side"),
        "by_exit_reason": base.grouped_summary(rows, "exit_reason"),
        "by_year": by_year,
        "by_month": by_month,
        "symbol_x_year": base.two_dimensional_matrix(rows, "symbol", "_year"),
        "period_sign_counts": {
            "symbols": base.period_sign_counts(by_symbol),
            "years": base.period_sign_counts(by_year),
            "months": base.period_sign_counts(by_month),
        },
        "descriptive_only_entry_time_breakdowns": {
            "by_entry_hour": base.grouped_summary(rows, "_entry_hour"),
            "by_weekday": base.grouped_summary(rows, "_weekday"),
            "warning": "Descriptive only. These breakdowns do not authorize post-hoc filters in the originating experiment.",
        },
        "exit_reason_counts": dict(sorted(Counter(str(row["exit_reason"]) for row in rows).items())),
        "side_counts": dict(sorted(Counter(str(row["side"]) for row in rows).items())),
        "trade_path": base.trade_path_summary(rows),
    }

    workspace = runner._expand_path(config["workspace_dir"])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = workspace / "rich_scores" / manifest["experiment_id"] / stage / stamp
    out_dir.mkdir(parents=True, exist_ok=False)
    compact_path = out_dir / "trades_compact.csv"
    base.write_compact_trades(compact_path, rows)

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
    parser.add_argument("--stage", default="development", choices=("development", "confirmation"))
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
