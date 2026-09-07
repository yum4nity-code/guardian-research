#!/usr/bin/env python3
"""Resume D049 Market Transport V1 without replaying its 11 completed symbols.

The latest invalid D049 development batch is expected to contain 11 valid tests
and to have stopped on XPTUSD. This recovery:
- preserves those 11 immutable test evidences;
- recompiles the unchanged deterministic D049 transport source;
- retries XPTUSD only;
- if XPTUSD passes, writes/publishes a recovered 12-symbol batch and the normal
  frozen Market Transport V1 score;
- if XPTUSD fails again, publishes an engineering-incomplete event so the next
  assistant can diagnose from GitHub without asking the operator for console
  logs.

No parent source, signal, management rule, cost rule, date window, or gate is
changed here.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import market_transport_lab_v1 as lab


PARENT = "D045"
STAGE = "development"
FAILED_SYMBOL = "XPTUSD"
EXPECTED_REUSED = 11


def _latest_invalid_batch(workspace: Path, experiment_id: str) -> tuple[Path, dict]:
    base = workspace / "batches" / experiment_id / STAGE
    candidates = sorted(base.glob("*/batch.json"), key=lambda p: p.stat().st_mtime, reverse=True) if base.exists() else []
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("status") != "BATCH_INVALID_ENGINEERING":
            continue
        if payload.get("failed_symbol") != FAILED_SYMBOL:
            continue
        tests = payload.get("tests", [])
        if len(tests) != EXPECTED_REUSED:
            continue
        symbols = [item.get("symbol") for item in tests]
        if len(symbols) != len(set(symbols)):
            continue
        if FAILED_SYMBOL in symbols:
            continue
        return path, payload
    raise lab.MarketTransportError(
        f"no trusted partial D049 batch found with {EXPECTED_REUSED} completed tests and failed_symbol={FAILED_SYMBOL}"
    )


def _write_recovery_batch(workspace: Path, manifest: dict, prior_path: Path, prior: dict, xpt_evidence: dict) -> dict:
    experiment_id = manifest["experiment_id"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    batch_dir = workspace / "batches" / experiment_id / STAGE / f"{stamp}_RECOVERED_XPTUSD"
    batch_dir.mkdir(parents=True, exist_ok=False)
    batch_path = batch_dir / "batch.json"

    reused = list(prior["tests"])
    combined = reused + [xpt_evidence]
    expected = list(lab.NEW_SYMBOLS)
    actual = [item.get("symbol") for item in combined]
    if actual != expected:
        raise lab.MarketTransportError(f"recovered D049 symbol order mismatch: expected={expected} got={actual}")

    payload = {
        "schema_version": 1,
        "status": "BATCH_PASS_INTEGRITY",
        "experiment_id": experiment_id,
        "manifest_path": str(manifest.get("_manifest_path", "local market-transport manifest")),
        "stage": STAGE,
        "symbols": expected,
        "started_at_utc": prior.get("started_at_utc"),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "execution_mode": "SEQUENTIAL_RECOVERY_REUSE_11_PLUS_XPTUSD_ONLY",
        "tester_model": manifest["runner_contract"]["tester_model_reference"],
        "tests": combined,
        "recovery": {
            "source_partial_batch": str(prior_path),
            "reused_completed_tests": EXPECTED_REUSED,
            "rerun_symbols": [FAILED_SYMBOL],
            "reason": "prior exact-source run stopped on XPTUSD FINAL_INVALID_REFERENCE",
            "scientific_semantics_changed": False,
        },
        "autosync_used": False,
    }
    lab.runner.write_receipt(batch_path, payload)
    return {"batch_path": str(batch_path), **payload}


def main() -> int:
    generated, generated_sha, provenance = lab.materialize_transport_source(PARENT)
    manifest_path, manifest = lab._manifest(PARENT, STAGE, generated, generated_sha)
    manifest["_manifest_path"] = str(manifest_path)
    identifier = manifest["experiment_id"]
    config = lab.runner.load_config()
    workspace = lab.runner._expand_path(config["workspace_dir"])

    prior_path, prior = _latest_invalid_batch(workspace, identifier)

    with lab._transport_context(manifest_path, manifest):
        compile_rc = lab.runner.cmd_compile(identifier)
        if compile_rc != 0:
            raise lab.MarketTransportError("D049 recovery compile failed")

        try:
            xpt = lab.tester.run_one(identifier, STAGE, FAILED_SYMBOL)
        except Exception as exc:
            failure = {
                "schema_version": 1,
                "status": "MARKET_TRANSPORT_ENGINEERING_INCOMPLETE",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "lab": "MARKET_TRANSPORT_V1",
                "parent": PARENT,
                "transport_id": identifier,
                "stage": STAGE,
                "failed_symbol": FAILED_SYMBOL,
                "reused_completed_tests_available": EXPECTED_REUSED,
                "source_partial_batch": str(prior_path),
                "error": str(exc),
                "source_provenance": provenance,
                "parent_verdict_unchanged": True,
                "scientific_semantics_changed": False,
                "autosync_used": False,
            }
            local = lab._write_local_result(PARENT, STAGE, "engineering-incomplete", failure)
            failure["local_path"] = str(local)
            failure["github_transport"] = lab.result_transport.safe_publish_event(
                identifier, STAGE, "market-transport-engineering-incomplete", failure
            )
            print(json.dumps(failure, indent=2, ensure_ascii=False, allow_nan=False))
            return 2

        batch_result = _write_recovery_batch(workspace, manifest, prior_path, prior, xpt)
        batch_transport = lab.result_transport.safe_publish_event(
            identifier, STAGE, "market-transport-batch-recovery", batch_result
        )

        score = lab._score(PARENT, batch_result)
        score["source_provenance"] = provenance
        score["batch_path"] = batch_result["batch_path"]
        score["batch_transport"] = batch_transport
        score["recovery"] = batch_result["recovery"]
        local = lab._write_local_result(PARENT, STAGE, "score", score)
        score["verdict_path"] = str(local)
        score["github_transport"] = lab.result_transport.safe_publish_event(
            identifier, STAGE, "market-transport-score", score
        )
        print(json.dumps(score, indent=2, ensure_ascii=False, allow_nan=False))
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"D049 XPTUSD RECOVERY V2 ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
