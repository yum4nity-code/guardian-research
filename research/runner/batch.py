#!/usr/bin/env python3
"""Sequential multi-symbol batch orchestration for Guardian Research Runner.

A batch intentionally starts sequentially. Parallel execution is a later
optimization and must not be introduced until output isolation is proven.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import experiment
import runner
import tester


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_batch(identifier: str, stage_name: str) -> dict[str, Any]:
    _, manifest_path, manifest = runner.load_context(identifier)
    config = runner.load_config()
    config_errors = tester.validate_test_config(config)
    if config_errors:
        raise tester.TestError("invalid local config: " + "; ".join(config_errors))

    stage = manifest["stages"].get(stage_name)
    if not stage:
        raise tester.TestError(f"unknown stage: {stage_name}")

    default_stage = manifest["runner_contract"]["default_stage"]
    if stage_name != default_stage:
        raise tester.TestError(
            f"v1 batch only supports the source default stage {default_stage}; requested {stage_name}"
        )

    workspace = runner._expand_path(config["workspace_dir"])
    batch_dir = workspace / "batches" / manifest["experiment_id"] / stage_name / stamp()
    batch_dir.mkdir(parents=True, exist_ok=False)
    batch_path = batch_dir / "batch.json"

    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "RUNNING",
        "experiment_id": manifest["experiment_id"],
        "manifest_path": str(manifest_path.relative_to(runner.ROOT)),
        "stage": stage_name,
        "symbols": list(stage["symbols"]),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "execution_mode": "SEQUENTIAL",
        "tester_model": manifest["runner_contract"]["tester_model_reference"],
        "tests": [],
        "autosync_used": False,
    }
    runner.write_receipt(batch_path, payload)

    try:
        for symbol in stage["symbols"]:
            evidence = tester.run_one(identifier, stage_name, symbol)
            payload["tests"].append(evidence)
            runner.write_receipt(batch_path, payload)
    except Exception as exc:
        payload["status"] = "BATCH_INVALID_ENGINEERING"
        payload["failed_symbol"] = symbol
        payload["error"] = str(exc)
        payload["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        runner.write_receipt(batch_path, payload)
        raise

    payload["status"] = "BATCH_PASS_INTEGRITY"
    payload["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    runner.write_receipt(batch_path, payload)
    return {"batch_path": str(batch_path), **payload}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a frozen Guardian experiment stage sequentially")
    parser.add_argument("experiment", help="D037 or manifest path")
    parser.add_argument("--stage", default="development", choices=("smoke", "development", "confirmation"))
    args = parser.parse_args()

    try:
        result = run_batch(args.experiment, args.stage)
    except (tester.TestError, runner.RunnerError, experiment.ManifestError, KeyError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
