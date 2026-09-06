#!/usr/bin/env python3
"""Guardian Research Runner v1 - deterministic local core.

Current implemented boundary:
  manifest validation -> source identity -> direct local MT5 deploy -> SHA verify -> MetaEditor compile -> build receipt

No AutoSync is used. The runner works from the local repository clone on the MT5
machine. Batch Strategy Tester execution and scoring are added in later stages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import experiment
import state_tools

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "local" / "guardian_runner.json"
RESULT_RE = re.compile(r"(?P<errors>\d+)\s+errors?\s*,\s*(?P<warnings>\d+)\s+warnings?", re.IGNORECASE)
SOURCE_SHA_MODE_TEXT_LF = "UTF8_TEXT_LF_NORMALIZED"
SOURCE_SHA_MODE_RAW = "RAW_BYTES"


class RunnerError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    """Byte-for-byte SHA-256 used for deployed files, EX5 and result evidence."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text_lf(path: Path) -> str:
    """Canonical source identity SHA-256, insensitive only to UTF-8 BOM/line endings.

    Git may check out text as CRLF on Windows even when the committed logical
    source was hashed with LF on Linux. For MQL source identity we normalize
    UTF-8 text to LF before hashing. Any other text/code change still changes
    this digest.
    """
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise RunnerError(f"source is not valid UTF-8 text: {path}: {exc}") from exc
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def source_identity_sha256(path: Path, mode: str) -> str:
    if mode == SOURCE_SHA_MODE_TEXT_LF:
        return sha256_text_lf(path)
    if mode == SOURCE_SHA_MODE_RAW:
        return sha256_file(path)
    raise RunnerError(f"unsupported source_sha256_mode: {mode}")


def _expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def config_path() -> Path:
    override = os.environ.get("GUARDIAN_RUNNER_CONFIG")
    return _expand_path(override) if override else DEFAULT_CONFIG


def load_config(required: bool = True) -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        if required:
            raise RunnerError(
                f"local runner config missing: {path}. Copy research/runner/local_config.example.json "
                "to local/guardian_runner.json and edit paths."
            )
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RunnerError(f"invalid runner config JSON: {path}: {exc}") from exc
    return data


def validate_config(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("metaeditor_exe", "mt5_experts_dir", "workspace_dir"):
        if not config.get(key):
            errors.append(f"runner config missing: {key}")

    if config.get("metaeditor_exe"):
        metaeditor = _expand_path(config["metaeditor_exe"])
        if not metaeditor.is_file():
            errors.append(f"MetaEditor executable not found: {metaeditor}")

    if config.get("mt5_experts_dir"):
        experts = _expand_path(config["mt5_experts_dir"])
        if not experts.exists():
            errors.append(f"MT5 experts directory not found: {experts}")

    return errors


def load_context(identifier: str) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    state = state_tools.load_state()
    state_errors = state_tools.validate_state(state)
    if state_errors:
        raise RunnerError("invalid project state: " + "; ".join(state_errors))

    manifest_path, manifest = experiment.load_manifest(identifier)
    manifest_errors = experiment.validate_manifest(manifest)
    if manifest_errors:
        raise RunnerError("invalid experiment manifest: " + "; ".join(manifest_errors))

    active = state["research"]["active_experiment"]
    if manifest["experiment_id"] != active:
        raise RunnerError(
            f"refusing non-active experiment {manifest['experiment_id']}; GUARDIAN_STATE active experiment is {active}"
        )
    return state, manifest_path, manifest


def source_readiness(manifest: dict[str, Any]) -> tuple[Path | None, list[str]]:
    blockers = experiment.execution_readiness(manifest)
    source = manifest["source"]
    canonical = source.get("canonical_path")
    source_path = ROOT / canonical if canonical else None

    if source_path and source_path.is_file() and source.get("source_sha256"):
        mode = source.get("source_sha256_mode", SOURCE_SHA_MODE_RAW)
        try:
            actual = source_identity_sha256(source_path, mode)
        except RunnerError as exc:
            blockers.append(str(exc))
        else:
            if actual.lower() != source["source_sha256"].lower():
                blockers.append(
                    f"source identity SHA mismatch: mode={mode} manifest={source['source_sha256']} "
                    f"actual={actual} raw_bytes={sha256_file(source_path)} path={canonical}"
                )
    return source_path, blockers


def direct_deploy_verified(source_path: Path, target_dir: Path, source_sha_mode: str = SOURCE_SHA_MODE_TEXT_LF) -> dict[str, str]:
    """Copy exact local bytes to MT5 and prove both logical identity and byte equality."""
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / source_path.name
    temp = target_dir / f".{source_path.name}.guardian-copy.tmp"

    source_bytes_sha = sha256_file(source_path)
    source_identity_sha = source_identity_sha256(source_path, source_sha_mode)
    if temp.exists():
        temp.unlink()
    shutil.copy2(source_path, temp)
    temp_bytes_sha = sha256_file(temp)
    if temp_bytes_sha != source_bytes_sha:
        temp.unlink(missing_ok=True)
        raise RunnerError(f"deploy temp byte SHA mismatch: source={source_bytes_sha} temp={temp_bytes_sha}")

    os.replace(temp, destination)
    destination_bytes_sha = sha256_file(destination)
    if destination_bytes_sha != source_bytes_sha:
        raise RunnerError(
            f"deploy destination byte SHA mismatch: source={source_bytes_sha} destination={destination_bytes_sha}"
        )
    destination_identity_sha = source_identity_sha256(destination, source_sha_mode)
    if destination_identity_sha != source_identity_sha:
        raise RunnerError(
            f"deploy destination identity SHA mismatch: source={source_identity_sha} destination={destination_identity_sha}"
        )

    return {
        "source": str(source_path),
        "destination": str(destination),
        "source_sha256_mode": source_sha_mode,
        "source_sha256": source_identity_sha,
        "destination_sha256": destination_identity_sha,
        "source_bytes_sha256": source_bytes_sha,
        "destination_bytes_sha256": destination_bytes_sha,
    }


def _read_metaeditor_log(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8-sig", "utf-8", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse_compile_result(log_text: str) -> tuple[int, int]:
    matches = list(RESULT_RE.finditer(log_text))
    if not matches:
        raise RunnerError("MetaEditor log does not contain a recognizable errors/warnings summary")
    match = matches[-1]
    return int(match.group("errors")), int(match.group("warnings"))


def compile_with_metaeditor(metaeditor: Path, deployed_source: Path, log_path: Path) -> dict[str, Any]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.unlink(missing_ok=True)

    command = [
        str(metaeditor),
        f"/compile:{deployed_source}",
        f"/log:{log_path}",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if not log_path.exists():
        raise RunnerError(
            f"MetaEditor produced no compile log (process exit={completed.returncode}). "
            f"stdout={completed.stdout[-1000:]} stderr={completed.stderr[-1000:]}"
        )

    log_text = _read_metaeditor_log(log_path)
    errors, warnings = parse_compile_result(log_text)
    if errors != 0 or warnings != 0:
        raise RunnerError(f"compile rejected: {errors} errors, {warnings} warnings; log={log_path}")

    ex5 = deployed_source.with_suffix(".ex5")
    if not ex5.is_file():
        raise RunnerError(f"compile reported 0/0 but EX5 is missing: {ex5}")

    return {
        "command": command,
        "process_exit_code": completed.returncode,
        "errors": errors,
        "warnings": warnings,
        "log": str(log_path),
        "ex5": str(ex5),
        "ex5_sha256": sha256_file(ex5),
    }


def build_receipt_path(config: dict[str, Any], experiment_id: str) -> Path:
    workspace = _expand_path(config["workspace_dir"])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return workspace / "builds" / experiment_id / stamp / "build.json"


def write_receipt(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def plan(identifier: str) -> dict[str, Any]:
    state, manifest_path, manifest = load_context(identifier)
    source_path, blockers = source_readiness(manifest)
    source_report: dict[str, Any] = {}
    if source_path and source_path.is_file():
        mode = manifest["source"].get("source_sha256_mode", SOURCE_SHA_MODE_RAW)
        try:
            source_report = {
                "sha256_mode": mode,
                "identity_sha256": source_identity_sha256(source_path, mode),
                "raw_bytes_sha256": sha256_file(source_path),
            }
        except RunnerError as exc:
            source_report = {"sha256_mode": mode, "identity_error": str(exc)}
    return {
        "experiment_id": manifest["experiment_id"],
        "manifest": str(manifest_path.relative_to(ROOT)),
        "source": str(source_path.relative_to(ROOT)) if source_path else None,
        "source_ready": not blockers,
        "source_identity": source_report,
        "blockers": blockers,
        "execution": manifest["execution"],
        "stages": {
            name: {
                "stage_name": stage["stage_name"],
                "from": stage["from"],
                "to": stage["to"],
                "symbols": stage["symbols"],
                "status": stage["status"],
            }
            for name, stage in manifest["stages"].items()
        },
        "autosync_used": False,
        "authoritative_state": state["authoritative"],
    }


def cmd_doctor(identifier: str) -> int:
    report = plan(identifier)
    config = load_config(required=False)
    config_errors = validate_config(config) if config else [f"runner config missing: {config_path()}"]
    report["local_config"] = str(config_path())
    report["local_environment_ready"] = not config_errors
    report["local_environment_blockers"] = config_errors
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["source_ready"] and not config_errors else 1


def cmd_prepare(identifier: str) -> int:
    _, _, manifest = load_context(identifier)
    source_path, blockers = source_readiness(manifest)
    if blockers or source_path is None:
        raise RunnerError("execution blocked: " + "; ".join(blockers))

    config = load_config()
    config_errors = validate_config(config)
    if config_errors:
        raise RunnerError("invalid local config: " + "; ".join(config_errors))

    target_dir = _expand_path(config["mt5_experts_dir"])
    mode = manifest["source"].get("source_sha256_mode", SOURCE_SHA_MODE_RAW)
    deploy = direct_deploy_verified(source_path, target_dir, mode)
    print(json.dumps(deploy, indent=2, ensure_ascii=False))
    return 0


def cmd_compile(identifier: str) -> int:
    _, manifest_path, manifest = load_context(identifier)
    source_path, blockers = source_readiness(manifest)
    if blockers or source_path is None:
        raise RunnerError("execution blocked: " + "; ".join(blockers))

    config = load_config()
    config_errors = validate_config(config)
    if config_errors:
        raise RunnerError("invalid local config: " + "; ".join(config_errors))

    mode = manifest["source"].get("source_sha256_mode", SOURCE_SHA_MODE_RAW)
    deploy = direct_deploy_verified(source_path, _expand_path(config["mt5_experts_dir"]), mode)
    receipt = build_receipt_path(config, manifest["experiment_id"])
    compile_log = receipt.parent / "metaeditor_compile.log"
    compile_result = compile_with_metaeditor(
        _expand_path(config["metaeditor_exe"]),
        Path(deploy["destination"]),
        compile_log,
    )

    payload = {
        "schema_version": 1,
        "status": "COMPILE_PASS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": manifest["experiment_id"],
        "manifest_path": str(manifest_path.relative_to(ROOT)),
        "source_version": manifest["source"]["version"],
        "source_sha256_mode": mode,
        "deploy": deploy,
        "compile": compile_result,
        "autosync_used": False,
    }
    write_receipt(receipt, payload)
    print(json.dumps({"receipt": str(receipt), **payload}, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Guardian Research Runner deterministic local core")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("doctor", "plan", "prepare", "compile"):
        command = sub.add_parser(name)
        command.add_argument("experiment", help="D037 or experiment manifest path")
    args = parser.parse_args()

    try:
        if args.command == "doctor":
            return cmd_doctor(args.experiment)
        if args.command == "plan":
            print(json.dumps(plan(args.experiment), indent=2, ensure_ascii=False))
            return 0
        if args.command == "prepare":
            return cmd_prepare(args.experiment)
        return cmd_compile(args.experiment)
    except (RunnerError, experiment.ManifestError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
