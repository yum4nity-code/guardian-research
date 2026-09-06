#!/usr/bin/env python3
"""Automatic compact Guardian result transport to backtest-results.

This is NOT legacy AutoSync. Each completed local command may publish a compact
immutable event through an isolated temporary clone. The active research working
tree is never switched or mutated. Large MT5 files remain local and are
represented by SHA256/byte metadata when above the compact size limit.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import publisher
import runner

MAX_EVENT_FILE_BYTES = 5 * 1024 * 1024


class ResultTransportError(RuntimeError):
    pass


def _fingerprint(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _event_id(kind: str, payload: dict[str, Any]) -> str:
    if kind == "batch" and payload.get("batch_path"):
        return Path(str(payload["batch_path"])).parent.name
    if kind in {"test-one", "recover-one"} and payload.get("stats", {}).get("path"):
        return Path(str(payload["stats"]["path"])).parent.name
    if kind == "trade-path" and payload.get("run_dir"):
        return Path(str(payload["run_dir"])).name
    for key in ("verdict_path", "rich_score_path", "publish_receipt"):
        if payload.get(key):
            return Path(str(payload[key])).parent.name
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _candidate_files(payload: dict[str, Any]) -> list[Path]:
    candidates: list[Path] = []
    for key in ("batch_path", "verdict_path", "rich_score_path", "publish_receipt"):
        value = payload.get(key)
        if value:
            candidates.append(Path(str(value)))
    for key in ("stats", "trades"):
        value = payload.get(key, {}).get("path") if isinstance(payload.get(key), dict) else None
        if value:
            candidates.append(Path(str(value)))
    compact = payload.get("compact_trades")
    if isinstance(compact, dict) and compact.get("path"):
        candidates.append(Path(str(compact["path"])))
    out: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        resolved = str(path.resolve()) if path.exists() else str(path)
        if resolved not in seen:
            seen.add(resolved)
            out.append(path)
    return out


def publish_event(identifier: str, stage: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    _, _, manifest = runner.load_context(identifier)
    config = runner.load_config()
    workspace = runner._expand_path(config["workspace_dir"])
    short_id = publisher._safe_short_id(manifest["experiment_id"])
    event_id = _event_id(kind, payload)
    event_fingerprint = _fingerprint({"kind": kind, "stage": stage, "payload": payload})

    remote = publisher._run_git(["-C", str(runner.ROOT), "remote", "get-url", "origin"])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    clone_root = workspace / "result_transport"
    clone_root.mkdir(parents=True, exist_ok=True)
    clone_dir = clone_root / f"{stamp}_{short_id}_{kind.replace('-', '_')}"
    if clone_dir.exists():
        shutil.rmtree(clone_dir)

    target_rel = Path("backtests") / short_id / "live" / "events" / stage / kind / event_id
    latest_rel = Path("backtests") / short_id / "live" / "latest.json"
    published_files: list[dict[str, Any]] = []
    status = "EVENT_PUBLISH_PASS"

    try:
        publisher._run_git(["clone", "--quiet", "--depth", "1", "--single-branch", "--branch", publisher.RESULT_BRANCH, remote, str(clone_dir)], timeout=300)
        target = clone_dir / target_rel
        if target.exists():
            existing_path = target / "event.json"
            if not existing_path.is_file():
                raise ResultTransportError(f"existing event target has no event.json: {target_rel.as_posix()}")
            existing = json.loads(existing_path.read_text(encoding="utf-8"))
            if existing.get("event_fingerprint_sha256") != event_fingerprint:
                raise ResultTransportError(f"event collision with different payload: {target_rel.as_posix()}")
            status = "EVENT_PUBLISH_NOOP_ALREADY_PRESENT"
        else:
            target.mkdir(parents=True, exist_ok=False)
            for path in _candidate_files(payload):
                item: dict[str, Any] = {"local_path": str(path), "exists": path.is_file()}
                if path.is_file():
                    item["sha256"] = runner.sha256_file(path)
                    item["bytes"] = path.stat().st_size
                    if path.stat().st_size <= MAX_EVENT_FILE_BYTES:
                        dest = target / path.name
                        shutil.copy2(path, dest)
                        item["published_as"] = path.name
                    else:
                        item["published_as"] = None
                        item["reason"] = "ABOVE_COMPACT_EVENT_SIZE_LIMIT"
                published_files.append(item)

            event = {
                "schema_version": 1,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "experiment_id": manifest["experiment_id"],
                "stage": stage,
                "kind": kind,
                "event_id": event_id,
                "event_fingerprint_sha256": event_fingerprint,
                "source_sha256": manifest.get("source", {}).get("source_sha256"),
                "payload": payload,
                "files": published_files,
                "transport": "ISOLATED_GIT_CLONE_EVENT_PUBLISHER",
                "autosync_used": False,
            }
            (target / "event.json").write_text(json.dumps(event, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8", newline="\n")

        latest = {
            "schema_version": 1,
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "experiment_id": manifest["experiment_id"],
            "stage": stage,
            "kind": kind,
            "event_id": event_id,
            "event_path": target_rel.as_posix(),
            "event_fingerprint_sha256": event_fingerprint,
            "status": payload.get("status"),
            "autosync_used": False,
        }
        latest_path = clone_dir / latest_rel
        latest_path.parent.mkdir(parents=True, exist_ok=True)
        latest_path.write_text(json.dumps(latest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

        publisher._run_git(["add", "--", target_rel.as_posix(), latest_rel.as_posix()], cwd=clone_dir)
        changes = publisher._run_git(["status", "--porcelain"], cwd=clone_dir)
        if changes:
            publisher._run_git([
                "-c", "user.name=Guardian Research Runner",
                "-c", "user.email=guardian-runner@local",
                "commit", "-m", f"Record {short_id.upper()} {stage} {kind} {event_id}",
            ], cwd=clone_dir)
            commit_sha = publisher._run_git(["rev-parse", "HEAD"], cwd=clone_dir)
            publisher._run_git(["push", "origin", f"HEAD:{publisher.RESULT_BRANCH}"], cwd=clone_dir, timeout=300)
        else:
            commit_sha = publisher._run_git(["rev-parse", "HEAD"], cwd=clone_dir)
    finally:
        if clone_dir.exists():
            shutil.rmtree(clone_dir, ignore_errors=True)

    receipt = {
        "status": status,
        "branch": publisher.RESULT_BRANCH,
        "event_path": target_rel.as_posix(),
        "latest_path": latest_rel.as_posix(),
        "event_id": event_id,
        "event_fingerprint_sha256": event_fingerprint,
        "commit_sha": commit_sha,
        "autosync_used": False,
    }
    receipt_path = workspace / "result_transport_receipts" / manifest["experiment_id"] / stage / kind / f"{event_id}.json"
    runner.write_receipt(receipt_path, receipt)
    return {"receipt_path": str(receipt_path), **receipt}


def safe_publish_event(identifier: str, stage: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Publish without invalidating already-valid local science on network failure."""
    try:
        return publish_event(identifier, stage, kind, payload)
    except Exception as exc:
        return {
            "status": "EVENT_PUBLISH_FAILED_LOCAL_RESULT_PRESERVED",
            "error": str(exc),
            "branch": publisher.RESULT_BRANCH,
            "autosync_used": False,
        }
