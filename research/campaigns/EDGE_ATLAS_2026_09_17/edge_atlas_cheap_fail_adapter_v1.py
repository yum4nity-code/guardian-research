#!/usr/bin/env python3
"""Research-only adapter from Guardian's generic Python executor to EA01."""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import subprocess
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from data_loader_v1 import AdmissionError
from preflight_v1 import PINNED_MANIFEST_SHA256, canonical_manifest_sha256, validate_manifest

TYPE = "EDGE_ATLAS_CHEAP_FAIL"
ID = "EDGE-ATLAS-2026-09-17-EA01-CHEAPFAIL-V0"
MAX_SECONDS = 300
RUNNER_REL = "research/campaigns/EDGE_ATLAS_2026_09_17/ea01_cheap_fail_v1.py"
PREREG_REL = "research/campaigns/EDGE_ATLAS_2026_09_17/EA01_CHEAP_FAIL_PREREGISTRATION.md"
MANIFEST_REL = "research/campaigns/EDGE_ATLAS_2026_09_17/ADMITTED_DATA_MANIFEST.json"
AUTH_REL = "research/campaigns/EDGE_ATLAS_2026_09_17/EA01_LAUNCH_AUTHORIZATION.json"


def file_sha256(path: Path) -> str:
    # Guardian deploys on Windows with CRLF checkout conversion. Hash the
    # canonical LF byte stream so the audited Git artifact and deployed copy
    # remain identical for admission purposes.
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk.replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def reject_production(path: Path) -> None:
    if "production" in {part.lower() for part in path.resolve().parts}:
        raise AdmissionError(f"production input forbidden: {path}")


def validate_job(job: dict, repo: Path, execution_requested: bool = False) -> dict:
    required = {"id": ID, "revision": 1, "type": TYPE, "protected_2026_opened": False}
    if any(job.get(k) != v for k, v in required.items()):
        raise AdmissionError("job identity/state is not fail-closed")
    expected_state = ("READY", True) if execution_requested else ("WAITING_CODEX", False)
    if (job.get("status"), job.get("enabled")) != expected_state:
        raise AdmissionError("job state does not authorize requested adapter mode")
    if job.get("data_window") != {"start": "2017-01-01T00:00:00Z", "end_exclusive": "2023-01-01T00:00:00Z", "partition": "discovery"}:
        raise AdmissionError("period outside frozen discovery")
    estimate = float(job.get("estimated_duration_seconds", MAX_SECONDS + 1))
    if estimate <= 0 or estimate > MAX_SECONDS:
        raise AdmissionError("estimated duration exceeds five minutes")
    executor = job.get("executor", {})
    expected_adapter = "research/campaigns/EDGE_ATLAS_2026_09_17/edge_atlas_cheap_fail_adapter_v1.py"
    if executor.get("kind") != "python" or executor.get("path") != expected_adapter:
        raise AdmissionError("unrecognized Guardian Python adapter")
    expected_paths = {"manifest": MANIFEST_REL, "runner": RUNNER_REL, "preregistration": PREREG_REL,
                      "launch_authorization": AUTH_REL}
    paths = {}
    for key, expected_rel in expected_paths.items():
        rel = job.get(key)
        if rel != expected_rel:
            raise AdmissionError(f"unexpected {key} path")
        path = (repo / rel).resolve()
        reject_production(path)
        if not path.is_file():
            raise AdmissionError(f"missing {key}: {path}")
        paths[key] = path
    for key in ("runner", "preregistration"):
        if file_sha256(paths[key]) != job.get(f"{key}_sha256"):
            raise AdmissionError(f"{key} hash mismatch")
    if canonical_manifest_sha256(paths["manifest"]) != PINNED_MANIFEST_SHA256:
        raise AdmissionError("manifest hash mismatch")
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    duka = validate_manifest(manifest)["DUKASCOPY_XAUUSD_BID_M1_BI5_2004_2025"]
    if duka.get("asset") != "XAUUSD" or duka.get("timezone") != "UTC" or duka.get("granularity") != "M1":
        raise AdmissionError("source is not XAUUSD UTC M1")
    authorization = json.loads(paths["launch_authorization"].read_text(encoding="utf-8"))
    if execution_requested and not (
        authorization.get("job_id") == ID and authorization.get("revision") == 1
        and authorization.get("launch_authorized") is True
        and authorization.get("protected_2026_opened") is False
    ):
        raise AdmissionError("checkpoint does not explicitly authorize launch")
    return paths


def atomic_status(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation: concurrent attempts must never replace an existing file.
    # A partial file after interruption deliberately blocks further execution.
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise AdmissionError(f"refusing to overwrite status: {path}") from exc


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise AdmissionError("status timestamp timezone absent")
    return parsed.astimezone(timezone.utc)


def _pid_absent(pid: object) -> bool:
    if type(pid) is not int or pid <= 0 or os.name != "nt":
        return False
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if handle:
        kernel.CloseHandle(handle)
        return False
    return ctypes.get_last_error() == 87  # Invalid PID; access denied stays blocked.


def recover_stale_running(running_path: Path, output_dir: Path, root: Path, job_id: str, revision: int, *, processes_absent: bool | None = None) -> dict | None:
    """Recover one stale RUNNING marker only when a finished receipt proves termination."""
    if not running_path.exists():
        return None
    # Offline recovery only; absence must be established by a fresh full process
    # inventory. Missing/ambiguous evidence is never permission to move a marker.
    if processes_absent is not True:
        raise AdmissionError("fresh process absence evidence required; BLOCKED")
    marker_hash = hashlib.sha256(running_path.read_bytes()).hexdigest()
    try:
        marker = json.loads(running_path.read_text(encoding="utf-8"))
        if marker.get("status") != "RUNNING" or marker.get("job_id") != job_id:
            raise AdmissionError("incoherent RUNNING status marker")
        recorded = _parse_utc(str(marker["recorded_at"]))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise AdmissionError("incoherent RUNNING status marker") from exc
    if "pid" in marker and not _pid_absent(marker["pid"]):
        raise AdmissionError("marker PID is live or ambiguous; BLOCKED")
    receipt_path = root / "receipts" / f"{job_id}__r{revision}.json"
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        finished = _parse_utc(str(receipt["finished_at_utc"]))
        if receipt.get("job_id") != job_id or int(receipt.get("revision", -1)) != revision:
            raise AdmissionError("receipt identity does not match RUNNING marker")
        if receipt.get("status") not in {"FAIL", "TIMEOUT", "BLOCKED"} or finished <= recorded:
            raise AdmissionError("RUNNING marker is active or receipt does not prove termination")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise AdmissionError("missing or incoherent terminal receipt for RUNNING marker") from exc
    quarantine = output_dir / "quarantine"
    quarantine.mkdir(parents=True, exist_ok=True)
    destination = quarantine / f"status_RUNNING_{marker_hash}.json"
    event_path = output_dir / f"status_RECOVERY_{marker_hash}.json"
    if destination.exists() or event_path.exists():
        raise AdmissionError("quarantine destination already exists")
    if hashlib.sha256(running_path.read_bytes()).hexdigest() != marker_hash:
        raise AdmissionError("RUNNING marker changed during recovery")
    # Windows rename refuses an existing destination; never replace/delete.
    if os.name != "nt":
        raise AdmissionError("offline recovery requires Windows no-replace rename")
    running_path.rename(destination)
    event = {"status": "RECOVERY_QUARANTINED", "job_id": job_id, "revision": revision,
             "source": str(running_path), "quarantine": str(destination), "sha256": marker_hash,
             "receipt": str(receipt_path), "protected_2026_opened": False}
    atomic_status(event_path, event)
    return event


def claim_attempt(output_dir: Path) -> None:
    atomic_status(output_dir / "status_ATTEMPT_CONSUMED.json", {
        "job_id": ID, "pid": os.getpid(), "recorded_at": datetime.now(timezone.utc).isoformat(),
        "reason": "One authorized recovery attempt; never automatically rearm",
        "protected_2026_opened": False,
    })


def validate_output_dir(output_dir: Path) -> Path:
    root_raw = os.environ.get("GUARDIAN_AUTONOMOUS_ROOT")
    if not root_raw:
        raise AdmissionError("GUARDIAN_AUTONOMOUS_ROOT absent")
    expected = (Path(root_raw) / "edge_atlas" / ID).resolve()
    if output_dir.resolve() != expected or "production" in {part.lower() for part in expected.parts}:
        raise AdmissionError("output directory is not the confined Guardian EA01 path")
    return expected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-spec", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    spec = json.loads(args.job_spec.read_text(encoding="utf-8"))
    if isinstance(spec.get("jobs"), list):
        matches = [item for item in spec["jobs"] if item.get("id") == ID]
        if len(matches) != 1:
            raise AdmissionError("proposal must contain exactly one EA01 job")
        job = matches[0]
    else:
        job = spec
    paths = validate_job(job, args.repo, execution_requested=args.execute)
    output_dir = validate_output_dir(args.output_dir)
    if not args.execute:
        print(json.dumps({"status": "VALIDATED_NOT_STARTED", "job_id": ID}))
        return 0
    running_path = output_dir / "status_RUNNING.json"
    if running_path.exists():
        raise AdmissionError("RUNNING marker requires offline recovery; BLOCKED")
    claim_attempt(output_dir)
    atomic_status(running_path, {"status": "RUNNING", "job_id": ID, "pid": os.getpid(),
                                "recorded_at": datetime.now(timezone.utc).isoformat(),
                                "protected_2026_opened": False})
    result_path = output_dir / "result.json"
    cp = subprocess.run([sys.executable, str(paths["runner"]), "--manifest", str(paths["manifest"]),
                         "--output", str(result_path), "--execute"], cwd=str(args.repo), text=True,
                        capture_output=True, timeout=MAX_SECONDS, check=False)
    if cp.returncode:
        atomic_status(output_dir / "status_INFRASTRUCTURE_ERROR.json", {"status": "INFRASTRUCTURE_ERROR", "job_id": ID,
                                    "returncode": cp.returncode, "stderr": cp.stderr[-4000:], "protected_2026_opened": False})
        return cp.returncode
    atomic_status(output_dir / "status_COMPLETE.json", {"status": "COMPLETE", "job_id": ID,
                                "result": str(result_path), "protected_2026_opened": False})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
