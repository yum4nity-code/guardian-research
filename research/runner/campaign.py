#!/usr/bin/env python3
"""Sequential multi-strategy campaign runner for Guardian Research.

Purpose: remove repetitive local commands while preserving experiment isolation.
A campaign may compile and run several frozen D0xx experiments in one pass.
Scientific rejection of one experiment never blocks the next. Engineering or
integrity failure is isolated to that experiment and recorded; the campaign
continues so an unattended overnight run still produces useful evidence.

MT5 execution remains SEQUENTIAL. Parallel terminals are deliberately forbidden
until FILE_COMMON/output isolation is proven under concurrent processes.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import batch
import experiment
import publisher
import result_transport
import rich_score_v2 as rich_score
import runner
import score
import tester
import trade_path_validate


class CampaignError(RuntimeError):
    pass


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _path_supported_from_manifest(manifest: dict[str, Any]) -> bool:
    """Return True only when native Trade Path is explicitly required by smoke gates."""
    smoke_gates = manifest.get("stages", {}).get("smoke", {}).get("gates", {})
    return bool(
        smoke_gates.get("trade_path_fields_present_and_parseable")
        or smoke_gates.get("opened_equals_closed_equals_trade_rows_equals_path_rows")
    )


def _compile(identifier: str) -> dict[str, Any]:
    rc = runner.cmd_compile(identifier)
    if rc != 0:
        raise CampaignError(f"compile failed for {identifier}")
    _, _, manifest = runner.load_context(identifier)
    config = runner.load_config()
    receipt_path, receipt = tester.latest_compile_receipt(config, manifest)
    return {
        "status": "COMPILE_PASS",
        "receipt": str(receipt_path),
        "source_sha256": receipt.get("deploy", {}).get("source_sha256"),
        "ex5_sha256": receipt.get("compile", {}).get("ex5_sha256"),
    }


def _validate_paths(identifier: str, stage: str, symbols: list[str]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for symbol in symbols:
        item = trade_path_validate.validate_latest(identifier, stage, symbol)
        item["github_transport"] = result_transport.safe_publish_event(identifier, stage, "trade-path", item)
        results.append(item)
    return {
        "status": "TRADE_PATH_PASS_ALL",
        "symbols": symbols,
        "results": results,
    }


def _stage_is_scored(stage: str, finalize_scored_stage: bool) -> bool:
    return finalize_scored_stage and stage in {"development", "confirmation"}


def run_experiment(identifier: str, stage: str, finalize_development: bool) -> dict[str, Any]:
    _, _, manifest = runner.load_context(identifier)
    started = datetime.now(timezone.utc).isoformat()
    result: dict[str, Any] = {
        "identifier": identifier,
        "experiment_id": manifest["experiment_id"],
        "stage": stage,
        "started_at_utc": started,
        "status": "RUNNING",
    }

    try:
        result["compile"] = _compile(identifier)
        batch_result = batch.run_batch(identifier, stage)
        batch_result["github_transport"] = result_transport.safe_publish_event(identifier, stage, "batch", batch_result)
        result["batch"] = batch_result

        stage_symbols = list(manifest["stages"][stage]["symbols"])
        if _path_supported_from_manifest(manifest):
            result["trade_path"] = _validate_paths(identifier, stage, stage_symbols)
        else:
            result["trade_path"] = {
                "status": "NOT_REQUIRED_BY_MANIFEST",
                "symbols": stage_symbols,
            }

        if _stage_is_scored(stage, finalize_development):
            decision = score.score(identifier, stage, batch_result["batch_path"])
            decision["github_transport"] = result_transport.safe_publish_event(identifier, stage, "score", decision)
            result["decision"] = {
                "verdict": decision["verdict"],
                "all_gates_pass": decision["all_gates_pass"],
                "verdict_path": decision["verdict_path"],
                "github_transport": decision["github_transport"],
            }

            # The frozen decision above is scientifically authoritative. Rich
            # analytics and bundle publication happen strictly afterwards. A
            # failure here must never be mislabeled as an MT5/integrity failure
            # or erase a valid REJECT/UNCONFIRMED/CONFIRMED verdict.
            try:
                rich = rich_score.rich_score(identifier, stage, decision["batch_path"])
                rich_event = result_transport.safe_publish_event(identifier, stage, "rich-score", rich)
                result["rich_score"] = {
                    "rich_score_path": rich["rich_score_path"],
                    "github_transport": rich_event,
                }

                published = publisher.publish_bundle(
                    identifier,
                    stage,
                    decision_path=decision["verdict_path"],
                    rich_path=rich["rich_score_path"],
                )
                result["bundle"] = published
                result["status"] = "EXPERIMENT_FINALIZED"
            except Exception as analytics_exc:
                result["status"] = "EXPERIMENT_DECISION_COMPLETE_ANALYTICS_FAILURE"
                result["post_decision_analytics_error"] = str(analytics_exc)
                result["post_decision_transport"] = result_transport.safe_publish_event(
                    identifier, stage, "post-decision-analytics-failure", result
                )
        else:
            result["status"] = "EXPERIMENT_STAGE_PASS"

    except Exception as exc:
        # This outer failure means compile/batch/path/score did not complete.
        # It is distinct from a post-decision descriptive-analytics failure.
        result["status"] = "EXPERIMENT_ENGINEERING_FAILURE"
        result["error"] = str(exc)
        try:
            result["failure_transport"] = result_transport.safe_publish_event(
                identifier, stage, "campaign-failure", result
            )
        except Exception as transport_exc:
            result["failure_transport"] = {
                "status": "TRANSPORT_FAILURE",
                "error": str(transport_exc),
            }

    result["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    return result


def run_campaign(identifiers: list[str], stage: str, finalize_development: bool = True) -> dict[str, Any]:
    if len(identifiers) < 1:
        raise CampaignError("campaign requires at least one experiment")
    if len(identifiers) != len(set(x.upper() for x in identifiers)):
        raise CampaignError("campaign experiment list contains duplicates")

    config = runner.load_config()
    workspace = runner._expand_path(config["workspace_dir"])
    campaign_id = utc_stamp()
    out_dir = workspace / "campaigns" / campaign_id
    out_dir.mkdir(parents=True, exist_ok=False)
    receipt_path = out_dir / "campaign.json"

    payload: dict[str, Any] = {
        "schema_version": 2,
        "campaign_id": campaign_id,
        "status": "RUNNING",
        "stage": stage,
        "execution_mode": "SEQUENTIAL_EXPERIMENTS_SEQUENTIAL_SYMBOLS",
        "parallel_mt5": False,
        "continue_after_scientific_reject": True,
        "continue_after_experiment_engineering_failure": True,
        "finalize_development": bool(finalize_development),
        "finalize_scored_stage": bool(finalize_development),
        "experiments_requested": identifiers,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiments": [],
        "autosync_used": False,
    }
    runner.write_receipt(receipt_path, payload)

    for identifier in identifiers:
        item = run_experiment(identifier, stage, finalize_development)
        payload["experiments"].append(item)
        runner.write_receipt(receipt_path, payload)

    failures = [x for x in payload["experiments"] if x["status"] == "EXPERIMENT_ENGINEERING_FAILURE"]
    analytics_failures = [
        x for x in payload["experiments"]
        if x["status"] == "EXPERIMENT_DECISION_COMPLETE_ANALYTICS_FAILURE"
    ]
    if failures:
        payload["status"] = "CAMPAIGN_COMPLETE_WITH_ENGINEERING_FAILURES"
    elif analytics_failures:
        payload["status"] = "CAMPAIGN_COMPLETE_WITH_POST_DECISION_ANALYTICS_FAILURES"
    else:
        payload["status"] = "CAMPAIGN_PASS"
    payload["engineering_failures"] = len(failures)
    payload["post_decision_analytics_failures"] = len(analytics_failures)
    payload["scientific_rejections"] = sum(
        1 for x in payload["experiments"] if x.get("decision", {}).get("verdict") in {"REJECT_V0", "UNCONFIRMED"}
    )
    payload["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    payload["campaign_receipt"] = str(receipt_path)
    runner.write_receipt(receipt_path, payload)

    payload["github_transport"] = result_transport.safe_publish_event(
        identifiers[0], stage, "campaign", payload
    )
    runner.write_receipt(receipt_path, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run several frozen Guardian experiments sequentially")
    parser.add_argument("experiments", nargs="+", help="D040 D041 ...")
    parser.add_argument("--stage", default="smoke", choices=("smoke", "development", "confirmation"))
    parser.add_argument(
        "--no-finalize",
        action="store_true",
        help="For development/confirmation, stop after batch/path validation instead of score/rich/publish",
    )
    args = parser.parse_args()
    try:
        result = run_campaign(args.experiments, args.stage, finalize_development=not args.no_finalize)
    except (CampaignError, runner.RunnerError, tester.TestError, experiment.ManifestError, KeyError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
