#!/usr/bin/env python3
"""Research-only adapter from Guardian's generic Python executor to EA01."""
from __future__ import annotations

import argparse
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
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
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
    if path.exists():
        raise AdmissionError(f"refusing to overwrite status: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


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
    atomic_status(running_path, {"status": "RUNNING", "job_id": ID,
                                "recorded_at": datetime.now(timezone.utc).isoformat(), "protected_2026_opened": False})
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
