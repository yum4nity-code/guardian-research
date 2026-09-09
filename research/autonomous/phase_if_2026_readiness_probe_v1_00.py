#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def norm(s: str) -> str:
    return os.path.normcase(os.path.normpath(str(s)))


def run_ps(script: str) -> tuple[int, str, str]:
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    cp = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
        **kwargs,
    )
    return cp.returncode, cp.stdout.strip(), cp.stderr.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-path", required=True)
    ap.add_argument("--terminal-exe", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--mandate", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    data_path = Path(args.data_path)
    terminal = Path(args.terminal_exe)
    policy_path = Path(args.policy)
    mandate_path = Path(args.mandate)
    output = Path(args.output)

    if not policy_path.exists() or not mandate_path.exists():
        raise RuntimeError("missing frozen Phase I-F policy or canonical mandate")
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    mandate = mandate_path.read_text(encoding="utf-8")
    if policy.get("schema") != 1 or policy.get("phase") != "I-F" or policy.get("status") != "PREREGISTERED_SEALED":
        raise RuntimeError("invalid Phase I-F preregistration policy")
    if "Standing authorization" not in mandate or "automatically opening preregistered protected 2026" not in mandate:
        raise RuntimeError("canonical mandate does not contain standing protected-OOS authorization")
    if norm(data_path) != norm(policy["data_provenance"]["terminal_data_path"]):
        raise RuntimeError("canonical terminal data path differs from frozen I-F provenance")
    if not terminal.exists():
        raise RuntimeError(f"canonical terminal executable missing: {terminal}")

    hcc_2026 = data_path / "Bases" / policy["data_provenance"]["terminal_server"] / "history" / "XAUUSD" / "2026.hcc"
    hcc_meta = {
        "path": str(hcc_2026),
        "exists": hcc_2026.exists(),
        "size_bytes": hcc_2026.stat().st_size if hcc_2026.exists() else 0,
        "mtime_utc": datetime.fromtimestamp(hcc_2026.stat().st_mtime, tz=timezone.utc).isoformat() if hcc_2026.exists() else None,
        "content_opened": False,
    }

    rc, stdout, stderr = run_ps(
        "$p=@(Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | "
        "Select-Object ProcessId,ExecutablePath); $p | ConvertTo-Json -Compress"
    )
    if rc != 0:
        raise RuntimeError(stderr or stdout or "terminal process inventory failed")
    procs = []
    if stdout:
        obj = json.loads(stdout)
        procs = obj if isinstance(obj, list) else [obj]
    canonical = [p for p in procs if norm(p.get("ExecutablePath", "")) == norm(terminal)]

    calendar_candidates = []
    needles = ("calendar", "economic", "news")
    roots = [data_path]
    appdata = os.environ.get("APPDATA")
    if appdata:
        roots.append(Path(appdata) / "MetaQuotes" / "Terminal" / "Common")
    seen = set()
    for root in roots:
        if not root.exists():
            continue
        try:
            for p in root.rglob("*"):
                if len(calendar_candidates) >= 100:
                    break
                if not p.is_file():
                    continue
                low = p.name.lower()
                if not any(n in low for n in needles):
                    continue
                key = norm(p)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    st = p.stat()
                    calendar_candidates.append({
                        "path": str(p),
                        "size_bytes": st.st_size,
                        "mtime_utc": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                        "content_opened": False,
                    })
                except OSError:
                    pass
        except OSError:
            pass

    out = {
        "schema": 1,
        "phase": "I-F-2026-READINESS",
        "status": "PASS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy": str(policy_path),
        "candidate_state": policy["candidate"]["state"],
        "final_oos_window": policy["final_oos_window"],
        "standing_authorization_verified": True,
        "market_hcc_2026": hcc_meta,
        "terminal_process_count": len(procs),
        "canonical_terminal_process_count": len(canonical),
        "canonical_terminal_pids": [int(p["ProcessId"]) for p in canonical if p.get("ProcessId") is not None],
        "calendar_metadata_candidates": calendar_candidates,
        "calendar_candidate_count": len(calendar_candidates),
        "protected_market_content_opened": False,
        "scientific_hypothesis_changed": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
