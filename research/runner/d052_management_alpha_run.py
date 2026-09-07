#!/usr/bin/env python3
"""Resilient one-command operator entrypoint for D052.

Runs the frozen D052 workflow unchanged. If any compile/smoke/DEV/scoring step
raises, publishes a compact failure event to backtest-results without asking the
operator to rerun already-valid MT5 work merely for transport.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import d052_management_alpha_workflow as d052
import experiment
import result_transport
import runner

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_SOURCE_SHA256 = "009a4bc7a5995d5d766fe6b5bec7d61b486e88d61fad0d75b29b227fb6098275"
STATIC_MANIFEST = "research/experiments/D052.json"


def preflight() -> tuple[Path, dict[str, Any], str]:
    d052.verify_frozen_repository_identity()
    source = ROOT / d052.SOURCE
    actual = runner.source_identity_sha256(source, runner.SOURCE_SHA_MODE_TEXT_LF)
    if actual.lower() != EXPECTED_SOURCE_SHA256.lower():
        raise d052.D052Error(
            f"D052 normalized source SHA mismatch: expected={EXPECTED_SOURCE_SHA256} actual={actual}"
        )

    static_path, static = experiment.load_manifest("D052")
    errors = experiment.validate_manifest(static)
    if errors:
        raise d052.D052Error("static D052 manifest invalid: " + "; ".join(errors))
    if static["source"]["source_sha256"].lower() != actual.lower():
        raise d052.D052Error("static D052 manifest source SHA does not match committed source")
    if static["preregistration"]["git_blob_sha"].lower() != d052.PREREG_GIT_BLOB_SHA.lower():
        raise d052.D052Error("static D052 prereg blob does not match frozen runner constant")
    if static["source"]["git_blob_sha"].lower() != d052.SOURCE_GIT_BLOB_SHA.lower():
        raise d052.D052Error("static D052 source blob does not match frozen runner constant")
    if static["execution"]["symbols"] != d052.SYMBOLS:
        raise d052.D052Error("static D052 symbol universe differs from workflow")
    if static["stages"]["confirmation"]["from"] != d052.HOLDOUT_FROM or static["stages"]["confirmation"]["to"] != d052.HOLDOUT_TO:
        raise d052.D052Error("static D052 holdout window differs from workflow")
    return static_path, static, actual


def publish_failure(error: Exception) -> dict[str, Any]:
    identities = d052.verify_frozen_repository_identity()
    source_sha = runner.source_identity_sha256(ROOT / d052.SOURCE, runner.SOURCE_SHA_MODE_TEXT_LF)
    manifest_path, manifest = d052.build_manifest(source_sha)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "D052_WORKFLOW_INCOMPLETE_ENGINEERING_OR_TOOLING",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": d052.EXPERIMENT_ID,
        "error": str(error),
        "source_sha256": source_sha,
        "source_git_blob_sha": identities[d052.SOURCE],
        "preregistration_git_blob_sha": identities[d052.PREREG],
        "scientific_verdict": None,
        "holdout_opened": False,
        "rerun_policy": "DO_NOT_RERUN_VALID_MT5_EVIDENCE_SOLELY_FOR_TRANSPORT; DIAGNOSE_LOCAL_RECEIPTS FIRST",
        "autosync_used": False,
    }
    try:
        with d052.d052_context(manifest_path, manifest):
            transport = result_transport.safe_publish_event(
                d052.EXPERIMENT_ID,
                "development",
                "d052-workflow-incomplete",
                payload,
            )
        payload["github_transport"] = transport
    except Exception as transport_error:
        payload["github_transport"] = {
            "status": "EVENT_PUBLISH_FAILED_LOCAL_ERROR_PRESERVED",
            "error": str(transport_error),
            "autosync_used": False,
        }
    return payload


def main() -> int:
    static_path, static, source_sha = preflight()
    print(json.dumps({
        "status": "D052_PREFLIGHT_PASS",
        "manifest": str(static_path.relative_to(ROOT)),
        "source_sha256": source_sha,
        "smoke": [d052.SMOKE_FROM, d052.SMOKE_TO, d052.SMOKE_SYMBOLS],
        "development": [d052.DEV_FROM, d052.DEV_TO, d052.SYMBOLS],
        "holdout": {"status": "LOCKED_UNOPENED", "from": d052.HOLDOUT_FROM, "to": d052.HOLDOUT_TO},
        "management_count": len(d052.MANAGEMENTS),
        "mt5_runs_if_smoke_passes": len(d052.SMOKE_SYMBOLS) + len(d052.SYMBOLS),
        "autosync_used": False,
    }, indent=2, ensure_ascii=False))
    return d052.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        failure = publish_failure(exc)
        print(json.dumps(failure, indent=2, ensure_ascii=False, allow_nan=False), file=sys.stderr)
        raise SystemExit(1)
