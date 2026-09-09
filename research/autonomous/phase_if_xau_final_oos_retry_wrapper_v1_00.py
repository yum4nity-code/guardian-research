#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,sys,time,os
from datetime import datetime,timezone
from pathlib import Path


def write_json_resilient(p: Path, obj: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    tmp = p.with_suffix(p.suffix + ".tmp")
    for _ in range(20):
        try:
            tmp.write_text(payload, encoding="utf-8")
            os.replace(tmp, p)
            return
        except PermissionError:
            time.sleep(0.1)
    p.write_text(payload, encoding="utf-8")


def heartbeat(p: Path | None, stage: str, elapsed: int, wait_seconds: int) -> None:
    if p:
        write_json_resilient(p, {
            "completed": 0,
            "total": 1,
            "stage": stage,
            "elapsed_seconds": elapsed,
            "wait_limit_seconds": wait_seconds,
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        })


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--executor", required=True)
    ap.add_argument("--hcc", required=True)
    ap.add_argument("--wait-seconds", type=int, default=10800)
    ap.add_argument("--progress-file")
    ap.add_argument("args", nargs=argparse.REMAINDER)
    a = ap.parse_args()

    hcc = Path(a.hcc)
    progress = Path(a.progress_file) if a.progress_file else None
    deadline = time.time() + a.wait_seconds
    started = time.time()

    while True:
        try:
            with hcc.open("rb") as f:
                f.read(1)
            break
        except PermissionError:
            elapsed = int(time.time() - started)
            heartbeat(progress, "waiting_for_hcc_read_access", elapsed, a.wait_seconds)
            if time.time() >= deadline:
                raise RuntimeError(f"timed out waiting for read access to HCC: {hcc}")
            time.sleep(10)
        except FileNotFoundError:
            raise RuntimeError(f"HCC missing: {hcc}")

    heartbeat(progress, "hcc_read_access_available", int(time.time() - started), a.wait_seconds)

    forwarded = list(a.args)
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    cmd = [sys.executable, a.executor, "--hcc", str(hcc)] + forwarded
    cp = subprocess.run(cmd, check=False)
    return int(cp.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
