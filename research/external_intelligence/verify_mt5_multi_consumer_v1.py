#!/usr/bin/env python3
"""Verify that two distinct, simultaneously active MT5 terminals consumed the same FILE_COMMON generations."""

from __future__ import annotations

import csv
import os
import time
from pathlib import Path

ACTIVE_SAMPLE_SECONDS = 6
MIN_COMMON_GENERATIONS = 3


def common_probe_dir() -> Path:
    appdata = os.getenv("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA unavailable")
    return Path(appdata) / "MetaQuotes" / "Terminal" / "Common" / "Files" / "GuardianSharedIntelligence" / "probes"


def read_recent_rows(path: Path, max_rows: int = 180) -> list[dict[str, str]]:
    with path.open("r", encoding="ascii", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    return rows[-max_rows:]


def snapshot_mtimes(probe_dir: Path) -> dict[Path, int]:
    return {p: p.stat().st_mtime_ns for p in probe_dir.glob("probe_*_v102.csv")}


def main() -> int:
    probe_dir = common_probe_dir()
    probe_dir.mkdir(parents=True, exist_ok=True)

    print("=== Guardian MT5 multi-consumer verifier V1.1 ===")
    print(f"probe_dir={probe_dir}")
    print(f"[VERIFY] observing active writers for {ACTIVE_SAMPLE_SECONDS}s...")

    before = snapshot_mtimes(probe_dir)
    time.sleep(ACTIVE_SAMPLE_SECONDS)
    after = snapshot_mtimes(probe_dir)

    active = [p for p, mt in after.items() if mt > before.get(p, -1)]
    active.sort(key=lambda p: p.stat().st_mtime_ns, reverse=True)

    if len(active) < 2:
        print(f"[VERIFY][REVIEW] need 2 simultaneously active v1.02 probes, found {len(active)}")
        return 2

    datasets: list[tuple[Path, list[dict[str, str]]]] = []
    for path in active:
        rows = read_recent_rows(path)
        if not rows:
            continue
        last = rows[-1]
        required = ("terminal_id", "generation_id", "btc_status", "eth_status", "server", "data_path")
        if any(not last.get(k) for k in required):
            print(f"[VERIFY][REVIEW] incomplete identity-aware row in {path.name}")
            continue
        if last.get("btc_status") != "OK" or last.get("eth_status") != "OK":
            print(f"[VERIFY][REVIEW] non-OK latest state in {path.name}: BTC={last.get('btc_status')} ETH={last.get('eth_status')}")
            continue
        datasets.append((path, rows))
        print(
            f"[VERIFY][PROBE] {path.name} terminal_id={last.get('terminal_id')} "
            f"server={last.get('server')} rows={len(rows)} latest_gen={last.get('generation_id')}"
        )

    if len(datasets) < 2:
        print(f"[VERIFY][REVIEW] fewer than 2 valid active identity-aware probes: {len(datasets)}")
        return 3

    # Find any pair that is truly distinct by both server and terminal data path
    # and that observed the same live generations during this run.
    for i in range(len(datasets)):
        for j in range(i + 1, len(datasets)):
            p1, r1 = datasets[i]
            p2, r2 = datasets[j]
            a = r1[-1]
            b = r2[-1]
            if a.get("server") == b.get("server"):
                continue
            if a.get("data_path") == b.get("data_path"):
                continue

            ids1 = {r.get("generation_id") for r in r1 if r.get("generation_id")}
            ids2 = {r.get("generation_id") for r in r2 if r.get("generation_id")}
            common = sorted(ids1 & ids2, key=int)
            if len(common) < MIN_COMMON_GENERATIONS:
                continue

            print(
                f"[VERIFY][OK] pair={p1.name} / {p2.name} "
                f"servers={a.get('server')} / {b.get('server')}"
            )
            print(f"[VERIFY][OK] distinct_active_terminals=2 common_generations={len(common)}")
            print(f"[VERIFY][OK] latest_common_generation={common[-1]}")
            print("[Guardian] FULL GATE MT5 MULTI-CONSUMER V1.1: PASS.")
            return 0

    print("[VERIFY][REVIEW] no pair proved two distinct active servers/data paths with >=3 common generations")
    return 5


if __name__ == "__main__":
    raise SystemExit(main())
