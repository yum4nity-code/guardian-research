#!/usr/bin/env python3
"""One-command resilient operator entrypoint for D053."""
from __future__ import annotations

import json
import sys

import d053_orb30_index_workflow as d053
import experiment
import runner

# Engineering amendment v1.01 was frozen after clean smoke and before any
# completed DEV symbol. Keep the large workflow stable and override only the
# frozen source identity/version plus the result-transport identifier mapping.
d053.SOURCE_VERSION = "1.01"
d053.EXPECTED_SOURCE_BLOB = "7da58ecf8968d6814b634be0ee0043b9616fb6c6"
d053.EXPECTED_SOURCE_SHA256 = "d39182cc7bd0376322fee474ec7c321b9e1f5d4db93cdb6ff301f0fb60aba7ad"

_original_safe_publish_event = d053.result_transport.safe_publish_event

def _d053_safe_publish_event(identifier: str, stage: str, kind: str, payload: dict):
    # result_transport resolves repository manifests by short key/path. The long
    # experiment ID is evidence metadata, not a valid manifest lookup key.
    return _original_safe_publish_event(d053.KEY, stage, kind, payload)

d053.result_transport.safe_publish_event = _d053_safe_publish_event


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
        "status": "D053_PREFLIGHT_PASS_V101",
        "manifest": str(manifest_path.relative_to(d053.ROOT)),
        "source_version": d053.SOURCE_VERSION,
        "source_sha256": identities["source_sha256"],
        "engineering_amendment": "research/campaigns/D053_ENGINEERING_AMENDMENT_V101_SESSION_END_2026_09_07.md",
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
