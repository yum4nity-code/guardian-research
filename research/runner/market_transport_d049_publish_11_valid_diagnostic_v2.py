#!/usr/bin/env python3
"""Publish the latest already-computed D049 11-valid-market diagnostic.

No MT5 execution and no rescoring. This script only discovers the latest local
`descriptive-11-valid.json`, reconstructs the deterministic synthetic D049
transport context, and publishes that existing payload to `backtest-results`.
"""
from __future__ import annotations

import json
from pathlib import Path

import market_transport_lab_v1 as lab

PARENT = "D045"
STAGE = "development"
KIND = "market-transport-descriptive-11-valid"


def _latest_local_payload(workspace: Path, experiment_id: str) -> tuple[Path, dict]:
    base = workspace / "market_transport" / "v1" / experiment_id / STAGE
    candidates = sorted(
        base.glob("*/descriptive-11-valid.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ) if base.exists() else []
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("status") != "D049_DESCRIPTIVE_11_VALID_MARKETS":
            continue
        if payload.get("transport_id") != experiment_id:
            continue
        if payload.get("formal_status") != "MARKET_TRANSPORT_ENGINEERING_INCOMPLETE":
            continue
        return path, payload
    raise lab.MarketTransportError("no trusted local D049 11-market diagnostic found")


def main() -> int:
    generated, generated_sha, _ = lab.materialize_transport_source(PARENT)
    manifest_path, manifest = lab._manifest(PARENT, STAGE, generated, generated_sha)
    identifier = manifest["experiment_id"]
    config = lab.runner.load_config()
    workspace = lab.runner._expand_path(config["workspace_dir"])
    local_path, payload = _latest_local_payload(workspace, identifier)

    # Remove the previous failed transport receipt from the payload fingerprint.
    payload = dict(payload)
    payload.pop("github_transport", None)
    payload["local_path"] = str(local_path)

    with lab._transport_context(manifest_path, manifest):
        receipt = lab.result_transport.safe_publish_event(identifier, STAGE, KIND, payload)

    print(json.dumps({
        "status": "D049_DESCRIPTIVE_11_VALID_PUBLISH_ATTEMPT",
        "local_path": str(local_path),
        "github_transport": receipt,
    }, indent=2, ensure_ascii=False, allow_nan=False))
    return 0 if receipt.get("status") in {"EVENT_PUBLISH_PASS", "EVENT_PUBLISH_NOOP_ALREADY_PRESENT"} else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"D049 11-MARKET PUBLISH V2 ERROR: {exc}")
        raise SystemExit(1)
