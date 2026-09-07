#!/usr/bin/env python3
"""One-command resilient operator entrypoint for D053."""
from __future__ import annotations

import json
import sys

import d053_orb30_index_workflow as d053
import experiment
import runner


def preflight() -> dict:
    identities = d053.verify_frozen_repository_identity()
    state, manifest_path, manifest = runner.load_context(d053.KEY)
    if state["research"]["active_experiment"] != d053.EXPERIMENT_ID:
        raise d053.D053Error("GUARDIAN_STATE does not make D053 active")
    errors = experiment.validate_manifest(manifest)
    if errors:
        raise d053.D053Error("D053 manifest invalid: " + "; ".join(errors))
    if manifest["status"] != "READY_SMOKE":
        raise d053.D053Error(f"D053 manifest status must be READY_SMOKE, got {manifest['status']}")
    if manifest["stages"]["confirmation"]["status"] != "UNOPENED":
        raise d053.D053Error("D053 holdout is not UNOPENED")
    return {
        "status": "D053_PREFLIGHT_PASS",
        "manifest": str(manifest_path.relative_to(d053.ROOT)),
        "source_sha256": identities["source_sha256"],
        "smoke": [d053.SMOKE_FROM, d053.SMOKE_TO, d053.SMOKE_SYMBOLS],
        "development": [d053.DEV_FROM, d053.DEV_TO, d053.SYMBOLS],
        "holdout": {"status": "LOCKED_UNOPENED", "from": d053.HOLDOUT_FROM, "to": d053.HOLDOUT_TO},
        "mt5_runs_if_smoke_passes": len(d053.SMOKE_SYMBOLS) + len(d053.SYMBOLS),
        "autosync_used": False,
    }


def main() -> int:
    print(json.dumps(preflight(), indent=2, ensure_ascii=False))
    return d053.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        try:
            identities = d053.verify_frozen_repository_identity()
            failure = d053.publish_failure(
                "development", "d053-operator-incomplete", exc, identities["source_sha256"]
            )
            print(json.dumps(failure, indent=2, ensure_ascii=False), file=sys.stderr)
        except Exception as publish_exc:
            print(f"D053 OPERATOR ERROR: {exc}; failure publication also failed: {publish_exc}", file=sys.stderr)
        raise SystemExit(1)
