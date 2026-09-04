#!/usr/bin/env python3
"""Timed live smoke for Guardian Shared Intelligence Service V1."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from collector_v1 import JsonlRecorder, default_data_dir, now_ms, utc_iso
from collector_v1_healthfix import BybitCollectorHealthFixed
from market_state_v1 import MarketStateService
from smoke_v1 import summarize


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Guardian shared intelligence V1 smoke")
    p.add_argument("--minutes", type=float, default=3.0)
    p.add_argument("--data-dir", type=Path, default=default_data_dir())
    return p.parse_args(argv)


def _read_snapshot(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


async def run_smoke(args: argparse.Namespace) -> int:
    if args.minutes <= 0:
        raise ValueError("--minutes must be > 0")

    args.data_dir.mkdir(parents=True, exist_ok=True)
    start_ms = now_ms()
    recorder = JsonlRecorder(args.data_dir)
    collector = BybitCollectorHealthFixed(["BTCUSD", "ETHUSD"], recorder, 5.0, 5.0)
    state = MarketStateService(args.data_dir, interval_seconds=1.0)
    snapshot_path = args.data_dir / "market_state_v1.json"

    print(f"Guardian SHARED INTELLIGENCE V1 smoke START | {utc_iso(start_ms)}")
    print(f"duration={args.minutes:.2f} min | data={args.data_dir}")
    print("Expected: one collector, changing generation_id, fresh BTC/ETH core facts, no strategy decision output.")

    collector_task = asyncio.create_task(collector.run())
    state_task = asyncio.create_task(state.run())
    generations: list[int] = []

    try:
        deadline = asyncio.get_running_loop().time() + args.minutes * 60.0
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(5.0)
            snap = _read_snapshot(snapshot_path)
            if snap is not None:
                try:
                    generations.append(int(snap["generation_id"]))
                except (KeyError, TypeError, ValueError):
                    pass
    finally:
        collector.stop_event.set()
        state.stop_event.set()
        await asyncio.gather(collector_task, state_task, return_exceptions=True)

    stop_ms = now_ms()
    raw_summary = summarize(args.data_dir, start_ms, stop_ms)
    final = _read_snapshot(snapshot_path)

    failures: list[str] = []
    if final is None:
        failures.append("market_state_v1.json missing or invalid")
    else:
        if final.get("engine") != "guardian-market-state-v1":
            failures.append("wrong engine id")
        if int(final.get("computed_at_ms", 0)) > stop_ms:
            failures.append("market state computed in the future")
        symbols = final.get("symbols") or {}
        for symbol in ("BTCUSD", "ETHUSD"):
            row = symbols.get(symbol) or {}
            quality = row.get("quality") or {}
            raw = row.get("raw") or {}
            if quality.get("status") != "OK":
                failures.append(f"{symbol} quality not OK: {quality.get('status')}")
            if quality.get("core_age_ms") is None or int(quality["core_age_ms"]) > 20_000:
                failures.append(f"{symbol} core data stale/missing")
            for key in ("spot_last", "perp_last", "open_interest", "funding_rate"):
                if raw.get(key) is None:
                    failures.append(f"{symbol} missing {key}")
            latest = quality.get("latest_available_at_ms")
            if latest is not None and int(latest) > int(final.get("computed_at_ms", 0)):
                failures.append(f"{symbol} future availability violation")

        text = json.dumps(final).lower()
        if '"buy"' in text or '"sell"' in text or '"signal"' in text:
            failures.append("strategy decision-like field found in shared snapshot")

    unique_generations = len(set(generations))
    if unique_generations < 2:
        failures.append("generation_id did not advance")
    if raw_summary.get("gate") != "PASS":
        failures.append("underlying EIB raw collector gate failed")

    summary = {
        "schema_version": 1,
        "smoke_start_ms": start_ms,
        "smoke_start_utc": utc_iso(start_ms),
        "smoke_stop_ms": stop_ms,
        "smoke_stop_utc": utc_iso(stop_ms),
        "observed_duration_seconds": round((stop_ms - start_ms) / 1000.0, 3),
        "raw_collector_gate": raw_summary.get("gate"),
        "raw_unique_events": raw_summary.get("unique_events"),
        "raw_duplicate_event_ids": raw_summary.get("duplicate_event_ids"),
        "raw_future_availability_violations": raw_summary.get("future_availability_violations"),
        "generation_samples": len(generations),
        "unique_generations": unique_generations,
        "final_generation_id": None if final is None else final.get("generation_id"),
        "final_symbols": None if final is None else final.get("symbols"),
        "failures": failures,
        "gate": "PASS" if not failures else "REVIEW",
    }

    summary_path = args.data_dir / f"smoke_shared_state_summary_{start_ms}.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("\n=== GUARDIAN SHARED INTELLIGENCE V1 SMOKE SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"\nSummary saved: {summary_path}")
    print(f"Shared state: {snapshot_path}")
    return 0 if summary["gate"] == "PASS" else 2


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        return asyncio.run(run_smoke(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
