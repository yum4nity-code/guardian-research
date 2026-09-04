#!/usr/bin/env python3
"""Timed live smoke runner for Guardian External Intelligence Bus V1.

Runs the existing read-only collector for a bounded duration, then prints a
compact quality summary of the JSONL records produced during this run.
No trading endpoint or API key is used.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from collector_v1 import BybitCollector, JsonlRecorder, default_data_dir, now_ms, utc_iso


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Guardian EIB V1 timed live smoke")
    p.add_argument("--minutes", type=float, default=35.0, help="collection duration; default 35 min")
    p.add_argument("--data-dir", type=Path, default=default_data_dir())
    p.add_argument("--poll-seconds", type=float, default=5.0)
    p.add_argument("--health-seconds", type=float, default=5.0)
    return p.parse_args(argv)


def iter_jsonl(data_dir: Path):
    for path in sorted(data_dir.glob("bybit_eib_v1_*.jsonl")):
        try:
            with path.open("r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield path, line_no, json.loads(line)
                    except json.JSONDecodeError:
                        yield path, line_no, {"_invalid_json": True}
        except OSError:
            continue


def summarize(data_dir: Path, start_ms: int, stop_ms: int) -> dict[str, Any]:
    counts = Counter()
    quality = Counter()
    event_ids: set[str] = set()
    duplicate_ids = 0
    invalid_json = 0
    future_availability = 0
    by_symbol_metric = Counter()
    first_available: int | None = None
    last_available: int | None = None
    source_lag_ms: list[int] = []

    for _path, _line_no, rec in iter_jsonl(data_dir):
        if rec.get("_invalid_json"):
            invalid_json += 1
            continue
        available = int(rec.get("available_at_ms") or 0)
        if available < start_ms or available > stop_ms + 5_000:
            continue
        eid = str(rec.get("event_id") or "")
        if eid:
            if eid in event_ids:
                duplicate_ids += 1
            event_ids.add(eid)
        symbol = str(rec.get("canonical_symbol") or "UNKNOWN")
        metric = str(rec.get("metric") or "UNKNOWN")
        market_type = str(rec.get("market_type") or "UNKNOWN")
        counts[(symbol, market_type, metric)] += 1
        by_symbol_metric[(symbol, metric)] += 1
        q = rec.get("quality") or {}
        quality[str(q.get("status") or "UNKNOWN")] += 1
        source_ts = int(rec.get("source_ts_ms") or 0)
        received_ts = int(rec.get("received_ts_ms") or 0)
        if available > stop_ms + 5_000:
            future_availability += 1
        if source_ts > 0 and received_ts >= source_ts:
            source_lag_ms.append(received_ts - source_ts)
        first_available = available if first_available is None else min(first_available, available)
        last_available = available if last_available is None else max(last_available, available)

    expected_core = {
        ("BTCUSD", "last_price"),
        ("BTCUSD", "open_interest"),
        ("BTCUSD", "funding_rate"),
        ("ETHUSD", "last_price"),
        ("ETHUSD", "open_interest"),
        ("ETHUSD", "funding_rate"),
    }
    missing_core = sorted(f"{s}:{m}" for s, m in expected_core if by_symbol_metric[(s, m)] == 0)
    duration_ms = 0 if first_available is None or last_available is None else max(0, last_available - first_available)
    lag_sorted = sorted(source_lag_ms)
    lag_p50 = lag_sorted[len(lag_sorted) // 2] if lag_sorted else None
    lag_p95 = lag_sorted[min(len(lag_sorted) - 1, int(len(lag_sorted) * 0.95))] if lag_sorted else None

    return {
        "schema_version": 1,
        "smoke_start_ms": start_ms,
        "smoke_start_utc": utc_iso(start_ms),
        "smoke_stop_ms": stop_ms,
        "smoke_stop_utc": utc_iso(stop_ms),
        "observed_duration_seconds": round(duration_ms / 1000, 3),
        "unique_events": len(event_ids),
        "duplicate_event_ids": duplicate_ids,
        "invalid_json_lines": invalid_json,
        "future_availability_violations": future_availability,
        "quality_counts": dict(quality),
        "source_to_receive_lag_ms_p50": lag_p50,
        "source_to_receive_lag_ms_p95": lag_p95,
        "missing_core_channels": missing_core,
        "counts": {
            f"{symbol}|{market_type}|{metric}": count
            for (symbol, market_type, metric), count in sorted(counts.items())
        },
        "gate": "PASS" if not missing_core and duplicate_ids == 0 and invalid_json == 0 and future_availability == 0 else "REVIEW",
        "note": "Liquidation count may legitimately be zero during a quiet smoke window; websocket health is checked separately in health.json.",
    }


async def run_smoke(args: argparse.Namespace) -> int:
    if args.minutes <= 0:
        raise ValueError("--minutes must be > 0")
    args.data_dir.mkdir(parents=True, exist_ok=True)
    start_ms = now_ms()
    recorder = JsonlRecorder(args.data_dir)
    collector = BybitCollector(["BTCUSD", "ETHUSD"], recorder, args.poll_seconds, args.health_seconds)

    print(f"Guardian EIB V1 smoke START | {utc_iso(start_ms)}")
    print(f"duration={args.minutes:.2f} min | data={args.data_dir}")
    print("Public read-only market data only. No API key. No trading endpoints.")

    collector_task = asyncio.create_task(collector.run())
    try:
        await asyncio.sleep(args.minutes * 60.0)
    finally:
        collector.stop_event.set()
        await collector_task

    stop_ms = now_ms()
    summary = summarize(args.data_dir, start_ms, stop_ms)
    summary_path = args.data_dir / f"smoke_summary_{start_ms}.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("\n=== GUARDIAN EIB V1 SMOKE SUMMARY ===")
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
