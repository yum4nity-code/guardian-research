#!/usr/bin/env python3
"""Timed smoke runner for the EIB V1 health-record hotfix prototype."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from collector_v1 import JsonlRecorder, default_data_dir, now_ms, utc_iso
from collector_v1_healthfix import BybitCollectorHealthFixed
from smoke_v1 import summarize


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Guardian EIB V1 healthfix smoke")
    p.add_argument("--minutes", type=float, default=3.0)
    p.add_argument("--data-dir", type=Path, default=default_data_dir())
    p.add_argument("--poll-seconds", type=float, default=5.0)
    p.add_argument("--health-seconds", type=float, default=5.0)
    return p.parse_args(argv)


async def run_smoke(args: argparse.Namespace) -> int:
    if args.minutes <= 0:
        raise ValueError("--minutes must be > 0")

    args.data_dir.mkdir(parents=True, exist_ok=True)
    start_ms = now_ms()
    recorder = JsonlRecorder(args.data_dir)
    collector = BybitCollectorHealthFixed(
        ["BTCUSD", "ETHUSD"], recorder, args.poll_seconds, args.health_seconds
    )

    print(f"Guardian EIB V1 HEALTHFIX smoke START | {utc_iso(start_ms)}")
    print(f"duration={args.minutes:.2f} min | data={args.data_dir}")
    print("Expected: core market channels ~12 records/min; health only on semantic change + 1/min heartbeat.")

    task = asyncio.create_task(collector.run())
    try:
        await asyncio.sleep(args.minutes * 60.0)
    finally:
        collector.stop_event.set()
        await task

    stop_ms = now_ms()
    summary = summarize(args.data_dir, start_ms, stop_ms)
    summary["healthfix_expectation"] = (
        "For a stable 3-minute run, aggregate health should be far below the old 36/symbol; "
        "roughly startup transitions plus ~1 heartbeat/minute/symbol."
    )
    summary_path = args.data_dir / f"smoke_healthfix_summary_{start_ms}.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("\n=== GUARDIAN EIB V1 HEALTHFIX SMOKE SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"\nSummary saved: {summary_path}")
    print(f"Health snapshot: {args.data_dir / 'health.json'}")
    return 0 if summary["gate"] == "PASS" else 2


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        return asyncio.run(run_smoke(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
