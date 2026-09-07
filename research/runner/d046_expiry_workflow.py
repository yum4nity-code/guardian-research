#!/usr/bin/env python3
"""One-command workflow for frozen D046 BTC 08UTC expiry screen."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import campaign
import d046_expiry_score
import result_transport
import runner
import tester


def _first_experiment(base: dict[str, Any]) -> dict[str, Any]:
    experiments = base.get("experiments", [])
    if not experiments:
        raise RuntimeError("D046 campaign returned no experiment result")
    return experiments[0]


def _load_batch_rows(batch_path: str) -> list[dict[str, str]]:
    batch = json.loads(Path(batch_path).read_text(encoding="utf-8"))
    if batch.get("status") != "BATCH_PASS_INTEGRITY":
        raise RuntimeError("D046 batch is not integrity-passed")
    tests = batch.get("tests", [])
    if len(tests) != 1 or tests[0].get("symbol") != "BTCUSD":
        raise RuntimeError("D046 smoke expects exactly one BTCUSD test")
    trades = Path(tests[0]["trades"]["path"])
    if runner.sha256_file(trades) != tests[0]["trades"]["sha256"]:
        raise RuntimeError("D046 smoke TRADES SHA mismatch")
    return tester.read_semicolon_csv(trades)


def run(identifier: str, stage: str) -> dict[str, Any]:
    if stage not in {"smoke", "development", "confirmation"}:
        raise ValueError("D046 workflow supports smoke/development/confirmation only")

    base = campaign.run_campaign([identifier], stage, finalize_development=False)
    exp = _first_experiment(base)
    if exp.get("status") == "EXPERIMENT_ENGINEERING_FAILURE":
        return {
            "status": "D046_ENGINEERING_FAILURE",
            "stage": stage,
            "campaign": base,
        }

    batch_path = exp["batch"]["batch_path"]
    if stage == "smoke":
        _, _, manifest = runner.load_context(identifier)
        rows = _load_batch_rows(batch_path)
        paired = d046_expiry_score.pair_rows(rows)
        paired_n = len(paired["paired_days"])
        minimum = int(manifest["stages"]["smoke"]["gates"]["paired_days_min_engineering"])
        if paired_n < minimum:
            result = {
                "schema_version": 1,
                "status": "D046_SMOKE_ENGINEERING_FAIL",
                "experiment_id": manifest["experiment_id"],
                "stage": "smoke",
                "paired_days_n": paired_n,
                "paired_days_min_engineering": minimum,
                "batch_path": batch_path,
                "reason": "insufficient complete paired UTC days in engineering smoke",
                "campaign": base,
                "autosync_used": False,
            }
        else:
            result = {
                "schema_version": 1,
                "status": "D046_SMOKE_PASS",
                "experiment_id": manifest["experiment_id"],
                "stage": "smoke",
                "science_role": "ENGINEERING_ONLY_NO_ALPHA_VERDICT",
                "paired_days_n": paired_n,
                "paired_days_min_engineering": minimum,
                "eligible_leg_counts": paired["eligible_leg_counts"],
                "ineligible_rows": paired["ineligible_rows"],
                "unpaired_eligible_days": paired["unpaired_eligible_days"],
                "batch_path": batch_path,
                "campaign": base,
                "autosync_used": False,
            }
        result["github_transport"] = result_transport.safe_publish_event(identifier, "smoke", "expiry-smoke", result)
        return result

    decision = d046_expiry_score.score(identifier, stage, batch_path)
    score_transport = result_transport.safe_publish_event(identifier, stage, "score", decision)
    analytics_event = {
        "schema_version": 1,
        "status": "D046_EXPIRY_ANALYTICS_COMPLETE",
        "experiment_id": decision["experiment_id"],
        "stage": stage,
        "scientific_role": decision["scientific_role"],
        "verdict": decision["verdict"],
        "metrics": decision["metrics"],
        "gates": decision["gates"],
        "analytics_path": decision["analytics_path"],
        "high_oi_mechanism_tested": False,
        "autosync_used": False,
    }
    analytics_transport = result_transport.safe_publish_event(identifier, stage, "rich-score", analytics_event)
    final = {
        "schema_version": 1,
        "status": "D046_EXPIRY_SCREEN_COMPLETE",
        "experiment_id": decision["experiment_id"],
        "stage": stage,
        "scientific_role": decision["scientific_role"],
        "verdict": decision["verdict"],
        "all_gates_pass": decision["all_gates_pass"],
        "metrics": decision["metrics"],
        "gates": decision["gates"],
        "verdict_path": decision["verdict_path"],
        "analytics_path": decision["analytics_path"],
        "batch_path": decision["batch_path"],
        "score_transport": score_transport,
        "analytics_transport": analytics_transport,
        "high_oi_mechanism_tested": False,
        "high_oi_boundary": decision["high_oi_mechanism_boundary"],
        "generic_publisher_used": False,
        "campaign": base,
        "autosync_used": False,
    }
    final["github_transport"] = result_transport.safe_publish_event(identifier, stage, "expiry-finalize", final)
    return final


def main() -> int:
    parser = argparse.ArgumentParser(description="Run frozen D046 BTC 08UTC expiry screening")
    parser.add_argument("experiment", nargs="?", default="D046")
    parser.add_argument("--stage", choices=("smoke", "development", "confirmation"), default="smoke")
    args = parser.parse_args()
    try:
        result = run(args.experiment, args.stage)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
