#!/usr/bin/env python3
"""Publish small Phenomenon Discovery run artifacts to backtest-results.

Uses a dedicated disposable writer clone. Never mutates the human/research clone.
ASCII-only source for Windows compatibility.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BRANCH = "backtest-results"
WRITER = Path(r"D:\MT5_Backtests\guardian-phenomenon-results-writer")
SPOOL = Path(r"D:\MT5_Backtests\Research\PhenomenonDiscovery\publish_spool")
REMOTE_FALLBACK = "https://github.com/yum4nity-code/guardian-research.git"


def run(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(args, cwd=str(cwd) if cwd else None, text=True, capture_output=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(args)}\n{p.stdout}\n{p.stderr}")
    return p


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def remote_url(root: Path) -> str:
    p = run(["git", "-C", str(root), "remote", "get-url", "origin"], check=False)
    u = p.stdout.strip()
    return u or REMOTE_FALLBACK


def ensure_writer(root: Path) -> None:
    remote = remote_url(root)
    if not (WRITER / ".git").exists():
        if WRITER.exists():
            backup = WRITER.with_name(WRITER.name + ".bad." + datetime.now().strftime("%Y%m%d_%H%M%S"))
            WRITER.rename(backup)
        WRITER.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--quiet", "--branch", BRANCH, "--single-branch", remote, str(WRITER)])
    run(["git", "-C", str(WRITER), "fetch", "--quiet", "origin", BRANCH])
    run(["git", "-C", str(WRITER), "reset", "--hard", f"origin/{BRANCH}"])
    run(["git", "-C", str(WRITER), "clean", "-fd"])


def copy_run_to_writer(spool_run: Path, phase: str, run_id: str) -> tuple[Path, Path]:
    rel = Path("phenomenon-discovery") / phase / "runs" / run_id
    dest = WRITER / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(spool_run, dest)
    latest = WRITER / "phenomenon-discovery" / phase / "LATEST.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest_src = spool_run / "status.json"
    payload = json.loads(latest_src.read_text(encoding="utf-8"))
    payload["published_run_path"] = rel.as_posix()
    latest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rel, latest


def publish(spool_run: Path, phase: str, run_id: str, root: Path) -> str:
    last_err = None
    for attempt in range(1, 4):
        try:
            ensure_writer(root)
            rel, latest = copy_run_to_writer(spool_run, phase, run_id)
            run(["git", "-C", str(WRITER), "add", "--", rel.as_posix(), latest.relative_to(WRITER).as_posix()])
            c = run([
                "git", "-C", str(WRITER),
                "-c", "user.name=Guardian Phenomenon Bot",
                "-c", "user.email=guardian-phenomenon@local.invalid",
                "commit", "-m", f"Publish Phenomenon Discovery {phase} {run_id}",
            ], check=False)
            if c.returncode != 0:
                st = run(["git", "-C", str(WRITER), "status", "--porcelain"], check=False).stdout.strip()
                if st:
                    raise RuntimeError(c.stderr or c.stdout)
            local_sha = run(["git", "-C", str(WRITER), "rev-parse", "HEAD"]).stdout.strip()
            p = run(["git", "-C", str(WRITER), "push", "origin", f"HEAD:{BRANCH}"], check=False)
            if p.returncode != 0:
                raise RuntimeError(p.stderr or p.stdout)
            remote_sha = run(["git", "-C", str(WRITER), "ls-remote", "origin", f"refs/heads/{BRANCH}"]).stdout.split()[0]
            if remote_sha != local_sha:
                raise RuntimeError(f"remote verification mismatch local={local_sha} remote={remote_sha}")
            return local_sha
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(attempt * 2)
    raise RuntimeError(f"publish failed after 3 attempts: {last_err}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True)
    ap.add_argument("--status", required=True, choices=["RUNNING", "PASS", "FAIL"])
    ap.add_argument("--summary", default="")
    ap.add_argument("--artifact", action="append", default=[])
    args = ap.parse_args()

    root = repo_root()
    now = datetime.now(timezone.utc)
    safe_phase = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in args.phase.lower())
    run_id = now.strftime("%Y%m%dT%H%M%SZ") + "_" + safe_phase
    spool_run = SPOOL / safe_phase / run_id
    spool_run.mkdir(parents=True, exist_ok=False)

    artifacts = []
    for raw in args.artifact:
        src = Path(raw)
        if not src.exists() or not src.is_file():
            continue
        dst = spool_run / src.name
        shutil.copy2(src, dst)
        artifacts.append({"name": dst.name, "size_bytes": dst.stat().st_size, "sha256": sha256(dst)})

    source_commit = run(["git", "-C", str(root), "rev-parse", "HEAD"], check=False).stdout.strip() or None
    status = {
        "schema": 1,
        "phase": args.phase,
        "status": args.status,
        "summary": args.summary,
        "generated_at_utc": now.isoformat(),
        "source_commit": source_commit,
        "artifacts": artifacts,
    }
    (spool_run / "status.json").write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    commit = publish(spool_run, safe_phase, run_id, root)
    print(f"PUBLISHED {args.phase} {args.status} commit={commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
