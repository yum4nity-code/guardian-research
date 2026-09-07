#!/usr/bin/env python3
"""One-command D053 audit -> D054 Core-3 confirmation program."""
from __future__ import annotations

import json
import sys

import d053_orb30_deep_audit as audit053
import d054_orb30_core3_workflow as d054
import experiment
import runner


def preflight() -> dict:
    identities = d054.verify_frozen_repository_identity()
    state, manifest_path, manifest = runner.load_context(d054.KEY)
    if state["research"]["active_experiment"] != d054.EXPERIMENT_ID:
        raise d054.D054Error("GUARDIAN_STATE does not make D054 active")
    errors = experiment.validate_manifest(manifest)
    if errors:
        raise d054.D054Error("D054 manifest invalid: " + "; ".join(errors))
    if manifest["status"] != "CANDIDATE_CONFIRM":
        raise d054.D054Error(f"D054 manifest status must be CANDIDATE_CONFIRM, got {manifest['status']}")
    if manifest["stages"]["confirmation"]["status"] != "UNOPENED":
        raise d054.D054Error("D054 confirmation must be UNOPENED at preflight")
    return {
        "status": "D054_PROGRAM_PREFLIGHT_PASS",
        "manifest": str(manifest_path.relative_to(d054.ROOT)),
        "preregistration_git_blob_sha": identities["prereg_blob"],
        "source_git_blob_sha": identities["source_blob"],
        "source_sha256": identities["source_sha256"],
        "d053_audit": "existing 2024-2025 CSV only; zero MT5 runs",
        "smoke": [d054.SMOKE_FROM, d054.SMOKE_TO, d054.SYMBOLS],
        "confirmation": [d054.HOLDOUT_FROM, d054.HOLDOUT_TO, d054.SYMBOLS],
        "mt5_runs": 6,
        "development_2024_2025_rerun": False,
        "autosync_used": False,
    }


def main() -> int:
    print(json.dumps(preflight(), indent=2, ensure_ascii=False))

    # D054 is already frozen in Git before this descriptive audit executes.
    audit = audit053.run_audit()
    print(json.dumps({
        "status": audit["status"],
        "aggregate": audit["aggregate"],
        "positive_months": audit["positive_months"],
        "negative_months": audit["negative_months"],
        "worst_5_months": audit["worst_5_months"],
        "dst_alignment_proxy": audit["dst_alignment_proxy"],
        "github_transport": audit.get("github_transport"),
    }, indent=2, ensure_ascii=False, allow_nan=False))

    return d054.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"D054 PROGRAM ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
