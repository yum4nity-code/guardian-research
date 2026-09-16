#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ctypes
import json
import math
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

VERSION = "1.02"
DEFAULT_REMOTE = "git@github.com:yum4nity-code/guardian-research.git"
DEFAULT_DEPLOY = r"D:\MT5_Backtests\guardian-autonomous-main"
DEFAULT_ROOT = r"D:\MT5_Backtests\Research\Autonomous"
QUEUE_REL = Path("research/autonomous/RESEARCH_QUEUE.json")
QUEUE_APPEND_REL = Path("research/autonomous/RESEARCH_QUEUE_APPEND.json")
SELF_REL = Path("research/autonomous/guardian_research_orchestrator_v1_00.py")
PUBLISHER_REL = Path("research/phenomenon_discovery/publish_phase_result_v1_00.py")
PROTECTED_2026_EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)
WINDOW_CREATION_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def hidden_kwargs():
    return {"creationflags": WINDOW_CREATION_FLAGS} if os.name == "nt" else {}


def run(cmd, cwd, timeout=120):
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
        **hidden_kwargs(),
    )


def git(deploy, *args, timeout=120):
    cp = run(["git", *args], deploy, timeout)
    if cp.returncode:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {cp.stderr.strip() or cp.stdout.strip()}"
        )
    return cp.stdout.strip()


def sync_runtime_copy(deploy):
    """Keep the installed runtime copy current for the next task restart."""
    source = (deploy / SELF_REL).resolve()
    current = Path(__file__).resolve()
    if source == current or not source.exists():
        return False
    try:
        src = source.read_bytes()
        if current.exists() and current.read_bytes() == src:
            return False
        current.parent.mkdir(parents=True, exist_ok=True)
        tmp = current.with_suffix(current.suffix + ".next")
        tmp.write_bytes(src)
        os.replace(tmp, current)
        return True
    except OSError:
        return False


def ensure_clone(deploy, remote):
    if not (deploy / ".git").exists():
        deploy.parent.mkdir(parents=True, exist_ok=True)
        cp = run(["git", "clone", remote, str(deploy)], deploy.parent, 300)
        if cp.returncode:
            raise RuntimeError(cp.stderr.strip() or cp.stdout.strip())
    git(deploy, "fetch", "origin", "main", "backtest-results", timeout=300)
    git(deploy, "checkout", "-B", "main", "origin/main")
    git(deploy, "reset", "--hard", "origin/main")
    commit = git(deploy, "rev-parse", "HEAD")
    sync_runtime_copy(deploy)
    return commit


def parse_dt(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def relpath(value):
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe path {value}")
    return path


def load_queue(deploy):
    queue = load_json(deploy / QUEUE_REL)
    append_path = deploy / QUEUE_APPEND_REL
    if append_path.exists():
        extra = load_json(append_path)
        if extra.get("schema") != 1 or not isinstance(extra.get("jobs"), list):
            raise ValueError("invalid queue append schema")
        if extra.get("replace_base_jobs"):
            base_generation = int(queue.get("generation", 0))
            supersedes = int(extra.get("supersedes_generation", -1))
            generation = int(extra.get("generation", 0))
            if supersedes != base_generation or generation <= supersedes:
                raise ValueError(
                    "replacement queue must supersede the exact base generation"
                )
            queue["jobs"] = list(extra["jobs"])
            queue["generation"] = generation
            queue["human_approved_2026"] = bool(
                extra.get("human_approved_2026", False)
            )
        else:
            queue["jobs"] = [*queue.get("jobs", []), *extra["jobs"]]
            queue["generation"] = max(
                int(queue.get("generation", 0)), int(extra.get("generation", 0))
            )
    return queue


def validate_queue(queue):
    if queue.get("schema") != 1:
        raise ValueError("queue schema")
    allow_2026 = bool(queue.get("human_approved_2026", False))
    seen = set()
    for job in queue.get("jobs", []):
        key = (job["id"], int(job["revision"]))
        if key in seen:
            raise ValueError(f"duplicate {key}")
        seen.add(key)
        executor = job.get("executor", {})
        if executor.get("kind") not in {"noop", "codex_assist"}:
            relpath(executor.get("path", "x"))
        window = job.get("data_window")
        if window and parse_dt(window["end_exclusive"]) > PROTECTED_2026_EPOCH and not allow_2026:
            raise ValueError(f"protected 2026 blocked: {key}")


def receipt_matches_job_commit(path, job_id, revision, expected_main_commit):
    if not path.exists():
        return False, f"missing {path.name}"
    try:
        obj = load_json(path)
    except Exception:
        return False, f"invalid json {path.name}"
    if obj.get("job_id") != job_id or int(obj.get("revision", -1)) != int(revision):
        return False, f"{path.name} identity mismatch"
    if obj.get("main_commit") != expected_main_commit:
        return False, f"{path.name} main_commit mismatch"
    return True, obj


def dep_ok(dep, deploy, receipts, expected_main_commit):
    kind = dep["kind"]
    if kind == "receipt":
        path = receipts / f"{dep['job_id']}__r{dep['revision']}.json"
        matches, obj = receipt_matches_job_commit(
            path, dep["job_id"], dep["revision"], expected_main_commit
        )
        if not matches:
            return False, obj
        status = obj.get("status")
        return status in dep.get("accepted_status", ["PASS"]), f"{path.name} status {status}"
    if kind == "github_result":
        ref = dep.get("ref", "origin/backtest-results")
        cp = run(["git", "show", f"{ref}:{dep['path']}"], deploy, 60)
        if cp.returncode:
            return False, f"missing {dep['path']} on {ref}"
        try:
            status = json.loads(cp.stdout).get("status")
        except Exception:
            return False, f"invalid json {dep['path']}"
        return status in dep.get("accepted_status", ["PASS"]), f"{dep['path']} status {status}"
    return False, f"unknown dependency {kind}"


def expand(value, root, deploy, job_id):
    return (
        value.replace("{ROOT}", str(root))
        .replace("{DEPLOY}", str(deploy))
        .replace("{JOB_ID}", job_id)
    )


def p95(values):
    if not values:
        return None
    ordered = sorted(values)
    pos = 0.95 * (len(ordered) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    return ordered[lo] if lo == hi else ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def history(path, key):
    if not path.exists():
        return []
    values = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except Exception:
            continue
        if (
            row.get("class_key") == key
            and row.get("status") == "PASS"
            and isinstance(row.get("duration_seconds"), (int, float))
        ):
            values.append(float(row["duration_seconds"]))
    return values


def hard_limit(policy, hist, elapsed=0, frac=None):
    values = [
        float(policy.get("min_seconds", 60)),
        float(policy.get("expected_seconds", 60)) * float(policy.get("eta_multiplier", 2.5)),
    ]
    hist95 = p95(hist)
    if hist95:
        values.append(hist95 * float(policy.get("history_p95_multiplier", 3)))
    if frac and frac > 0 and elapsed > 0:
        values.append((elapsed / frac) * float(policy.get("eta_multiplier", 2.5)))
    return max(values)


def progress(path):
    if not path or not path.exists():
        return None, None
    mtime = path.stat().st_mtime
    try:
        obj = load_json(path)
        frac = obj.get("fraction")
        if frac is None and obj.get("completed") is not None and obj.get("total"):
            frac = float(obj["completed"]) / float(obj["total"])
        return (float(frac) if frac is not None else None), mtime
    except Exception:
        return None, mtime


def kill_tree(process):
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            text=True,
            capture_output=True,
            check=False,
            **hidden_kwargs(),
        )
    else:
        try:
            os.killpg(process.pid, 15)
            time.sleep(2)
            os.killpg(process.pid, 9)
        except Exception:
            pass


@dataclass
class Result:
    status: str
    exit_code: int | None
    duration: float
    reason: str
    out: str
    err: str
    limit: float


def execute(job, deploy, root, histfile):
    executor = job["executor"]
    kind = executor["kind"]
    if kind == "noop":
        return Result("PASS", 0, 0, "noop gate satisfied", "", "", 0)
    if kind == "codex_assist":
        return Result(
            "BLOCKED",
            None,
            0,
            "Codex adapter intentionally fail-closed in v1.00",
            "",
            "",
            0,
        )

    target = (deploy / relpath(executor["path"])).resolve()
    if deploy.resolve() not in target.parents or not target.exists():
        return Result("FAIL", None, 0, f"executor missing/unsafe: {target}", "", "", 0)

    args = [expand(arg, root, deploy, job["id"]) for arg in executor.get("args", [])]
    if kind == "python":
        cmd = [sys.executable, str(target), *args]
    else:
        cmd = [
            shutil.which("powershell.exe") or shutil.which("powershell") or "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(target),
            *args,
        ]

    env = os.environ.copy()
    env.update(
        {
            "GUARDIAN_AUTONOMOUS_ROOT": str(root),
            "GUARDIAN_DEPLOY_ROOT": str(deploy),
            "GUARDIAN_JOB_ID": job["id"],
            "GUARDIAN_JOB_REVISION": str(job["revision"]),
        }
    )
    for key, value in executor.get("env", {}).items():
        env[str(key)] = expand(value, root, deploy, job["id"])

    logs = root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    out_path = logs / f"{job['id']}__r{job['revision']}.out.log"
    err_path = logs / f"{job['id']}__r{job['revision']}.err.log"

    popen_flags = (
        {"creationflags": WINDOW_CREATION_FLAGS}
        if os.name == "nt"
        else {"start_new_session": True}
    )

    with out_path.open("w", encoding="utf-8") as out, err_path.open("w", encoding="utf-8") as err:
        process = subprocess.Popen(
            cmd,
            cwd=str(deploy),
            env=env,
            text=True,
            stdout=out,
            stderr=err,
            **popen_flags,
        )
        start = time.monotonic()
        policy = job.get("timeout", {})
        hist = history(histfile, job.get("class_key", job["id"]))
        progress_file = policy.get("progress_file")
        progress_path = (
            Path(expand(progress_file, root, deploy, job["id"])) if progress_file else None
        )
        stale = float(policy.get("stale_heartbeat_seconds", 900))
        last = None
        limit = hard_limit(policy, hist, 0, None)
        timed_out = False
        reason = ""

        while process.poll() is None:
            elapsed = time.monotonic() - start
            frac, mtime = progress(progress_path)
            last = mtime if mtime and (last is None or mtime > last) else last
            limit = hard_limit(policy, hist, elapsed, frac)
            is_stale = (
                elapsed > stale
                if progress_path and last is None
                else (
                    time.time() - last > stale
                    if progress_path
                    else elapsed > limit
                )
            )
            if elapsed > limit and is_stale:
                timed_out = True
                reason = f"adaptive timeout elapsed={elapsed:.1f}s limit={limit:.1f}s"
                kill_tree(process)
                break
            time.sleep(max(1, float(policy.get("poll_seconds", 5))))

        duration = time.monotonic() - start

    out_tail = "\n".join(
        out_path.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]
    )
    err_tail = "\n".join(
        err_path.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]
    )
    if timed_out:
        return Result("TIMEOUT", process.poll(), duration, reason, out_tail, err_tail, limit)
    return Result(
        "PASS" if process.returncode == 0 else "FAIL",
        process.returncode,
        duration,
        "executor exit 0" if process.returncode == 0 else f"executor exit {process.returncode}",
        out_tail,
        err_tail,
        limit,
    )


def receipt(receipts, job):
    return receipts / f"{job['id']}__r{job['revision']}.json"


def append_hist(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def publish(deploy, health, rcpt, status, summary):
    publisher = deploy / PUBLISHER_REL
    if not publisher.exists():
        return
    mapped = (
        "RUNNING"
        if status in {"RUNNING", "WAITING", "IDLE"}
        else ("PASS" if status == "PASS" else "FAIL")
    )
    cmd = [
        sys.executable,
        str(publisher),
        "--phase",
        "autonomous-research-orchestrator",
        "--status",
        mapped,
        "--summary",
        summary,
        "--artifact",
        str(health),
    ]
    if rcpt and rcpt.exists():
        cmd += ["--artifact", str(rcpt)]
    run(cmd, deploy, 180)


def once(deploy, root, remote, pub=True):
    commit = ensure_clone(deploy, remote)
    queue = load_queue(deploy)
    validate_queue(queue)
    receipts = root / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    health = root / "orchestrator_health.json"
    hist = root / "history.jsonl"
    enabled = [job for job in queue.get("jobs", []) if job.get("enabled")]
    selected = None
    waits = []

    for job in sorted(
        enabled,
        key=lambda item: (
            int(item.get("priority", 100)),
            item["id"],
            int(item.get("revision", 0)),
        ),
    ):
        current_receipt = receipt(receipts, job)
        current, _ = receipt_matches_job_commit(
            current_receipt, job["id"], job["revision"], commit
        )
        if current:
            continue
        bad = []
        for dep in job.get("requires", []):
            ok, why = dep_ok(dep, deploy, receipts, commit)
            if not ok:
                bad.append(why)
        if not bad:
            selected = job
            break
        waits.append(f"{job['id']}: {'; '.join(bad)}")

    if not selected:
        status = "WAITING" if enabled else "IDLE"
        summary = "No executable job. " + (" | ".join(waits[:4]) if waits else "queue empty")
        atomic_json(
            health,
            {
                "schema": 1,
                "version": VERSION,
                "status": status,
                "updated_at_utc": now(),
                "pid": os.getpid(),
                "main_commit": commit,
                "queue_generation": queue.get("generation"),
                "wait_reasons": waits,
                "protected_2026": not queue.get("human_approved_2026", False),
            },
        )
        return status, summary

    job = selected
    atomic_json(
        health,
        {
            "schema": 1,
            "version": VERSION,
            "status": "RUNNING",
            "updated_at_utc": now(),
            "pid": os.getpid(),
            "main_commit": commit,
            "queue_generation": queue.get("generation"),
            "active_job": {"id": job["id"], "revision": job["revision"]},
            "protected_2026": not queue.get("human_approved_2026", False),
        },
    )
    if pub:
        publish(
            deploy,
            health,
            None,
            "RUNNING",
            f"Autonomous research running {job['id']} r{job['revision']} from {commit[:10]}",
        )

    started = now()
    result = execute(job, deploy, root, hist)
    receipt_obj = {
        "schema": 1,
        "orchestrator_version": VERSION,
        "job_id": job["id"],
        "revision": job["revision"],
        "class_key": job.get("class_key", job["id"]),
        "main_commit": commit,
        "started_at_utc": started,
        "finished_at_utc": now(),
        "status": result.status,
        "exit_code": result.exit_code,
        "duration_seconds": result.duration,
        "adaptive_hard_limit_seconds": result.limit,
        "reason": result.reason,
        "stdout_tail": result.out,
        "stderr_tail": result.err,
        "protected_2026_untouched": not queue.get("human_approved_2026", False),
    }
    receipt_path = receipt(receipts, job)
    atomic_json(receipt_path, receipt_obj)
    append_hist(
        hist,
        {
            key: receipt_obj[key]
            for key in (
                "job_id",
                "revision",
                "class_key",
                "status",
                "duration_seconds",
                "finished_at_utc",
            )
        },
    )
    atomic_json(
        health,
        {
            "schema": 1,
            "version": VERSION,
            "status": result.status,
            "updated_at_utc": now(),
            "pid": os.getpid(),
            "main_commit": commit,
            "last_receipt": str(receipt_path),
            "last_reason": result.reason,
        },
    )
    if pub:
        publish(
            deploy,
            health,
            receipt_path,
            result.status,
            f"Autonomous research {job['id']} r{job['revision']} -> {result.status}: {result.reason}",
        )
    return result.status, result.reason


def pid_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if handle:
        kernel32.CloseHandle(handle)
        return True
    return ctypes.get_last_error() == 5


def lock(root):
    root.mkdir(parents=True, exist_ok=True)
    path = root / "orchestrator.lock"
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, f"{os.getpid()}\n".encode())
        os.close(fd)
        return path
    except FileExistsError:
        try:
            pid = int(path.read_text(encoding="utf-8").strip())
        except (ValueError, OSError) as exc:
            raise RuntimeError(f"lock exists and is unreadable: {exc}") from exc
        if pid_alive(pid):
            raise RuntimeError(f"already running pid={pid}")
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise RuntimeError(f"stale lock could not be removed: {exc}") from exc
        return lock(root)


def daemon(deploy, root, remote, poll):
    lock_path = lock(root)
    try:
        while True:
            try:
                status, _ = once(deploy, root, remote, True)
                time.sleep(5 if status in {"PASS", "FAIL", "TIMEOUT", "BLOCKED"} else poll)
            except Exception as exc:
                atomic_json(
                    root / "orchestrator_health.json",
                    {
                        "schema": 1,
                        "version": VERSION,
                        "status": "ORCHESTRATOR_ERROR",
                        "updated_at_utc": now(),
                        "pid": os.getpid(),
                        "error": repr(exc),
                    },
                )
                time.sleep(min(max(poll, 30), 300))
    finally:
        lock_path.unlink(missing_ok=True)


percentile95 = p95
adaptive_hard_limit = hard_limit
normalize_rel_path = relpath
dependency_satisfied = dep_ok
execute_job = execute


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--deploy", default=DEFAULT_DEPLOY)
    parser.add_argument("--remote", default=DEFAULT_REMOTE)
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--no-publish", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    deploy = Path(args.deploy)
    if args.once:
        status, why = once(deploy, root, args.remote, not args.no_publish)
        print(json.dumps({"status": status, "reason": why}, indent=2))
        return 1 if status in {"FAIL", "TIMEOUT"} else 0
    return daemon(deploy, root, args.remote, args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
