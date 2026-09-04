#!/usr/bin/env python3
"""Verify that two distinct MT5 terminals consumed the same FILE_COMMON generations."""

from __future__ import annotations

import csv
import os
import time
from pathlib import Path


def common_probe_dir() -> Path:
    appdata = os.getenv("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA unavailable")
    return Path(appdata) / "MetaQuotes" / "Terminal" / "Common" / "Files" / "GuardianSharedIntelligence" / "probes"


def read_recent_rows(path: Path, max_rows: int = 120) -> list[dict[str, str]]:
    with path.open("r", encoding="ascii", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    return rows[-max_rows:]


def main() -> int:
    probe_dir = common_probe_dir()
    now = time.time()
    files = [p for p in probe_dir.glob("probe_*.csv") if now - p.stat().st_mtime <= 120]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    print("=== Guardian MT5 multi-consumer verifier V1 ===")
    print(f"probe_dir={probe_dir}")

    if len(files) < 2:
        print(f"[VERIFY][REVIEW] need 2 recent terminal probes, found {len(files)}")
        return 2

    selected = files[:2]
    datasets: list[tuple[Path, list[dict[str, str]]]] = []
    for path in selected:
        rows = read_recent_rows(path)
        if not rows:
            print(f"[VERIFY][REVIEW] empty probe: {path.name}")
            return 3
        last = rows[-1]
        if last.get("btc_status") != "OK" or last.get("eth_status") != "OK":
            print(f"[VERIFY][REVIEW] non-OK latest state in {path.name}: BTC={last.get('btc_status')} ETH={last.get('eth_status')}")
            return 4
        datasets.append((path, rows))
        print(f"[VERIFY][PROBE] {path.name} terminal_id={last.get('terminal_id')} rows={len(rows)} latest_gen={last.get('generation_id')}")

    ids1 = {r.get("generation_id") for r in datasets[0][1] if r.get("generation_id")}
    ids2 = {r.get("generation_id") for r in datasets[1][1] if r.get("generation_id")}
    common = sorted(ids1 & ids2, key=int)

    if len(common) < 3:
        print(f"[VERIFY][REVIEW] only {len(common)} common generation(s) observed by both terminals")
        return 5

    print(f"[VERIFY][OK] distinct_probe_files=2 common_generations={len(common)}")
    print(f"[VERIFY][OK] latest_common_generation={common[-1]}")
    print("[Guardian] FULL GATE MT5 MULTI-CONSUMER V1: PASS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
