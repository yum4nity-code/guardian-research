#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import csv
import json
from pathlib import Path

from collector_v1 import JsonlRecorder, default_data_dir, now_ms, utc_iso
from collector_v1_healthfix import BybitCollectorHealthFixed
from market_state_v1_coveragefix import MarketStateServiceCoverageFixed
from mt5_common_bridge_v1 import (
    DEFAULT_OUTPUT_NAME,
    DEFAULT_SUBDIR,
    default_common_files_dir,
    publish_once,
)
from smoke_v1 import summarize


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Guardian MT5 FILE_COMMON bridge smoke")
    p.add_argument("--minutes", type=float, default=2.0)
    p.add_argument("--data-dir", type=Path, default=default_data_dir())
    p.add_argument("--common-files-dir", type=Path, default=None)
    return p.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="ascii", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


async def run_smoke(args: argparse.Namespace) -> int:
    data = args.data_dir
    common = args.common_files_dir or default_common_files_dir()
    out = common / DEFAULT_SUBDIR / DEFAULT_OUTPUT_NAME
    start = now_ms()

    recorder = JsonlRecorder(data)
    collector = BybitCollectorHealthFixed(["BTCUSD", "ETHUSD"], recorder, 5.0, 5.0)
    state = MarketStateServiceCoverageFixed(data, interval_seconds=1.0)
    collector_task = asyncio.create_task(collector.run())
    state_task = asyncio.create_task(state.run())

    generations: list[int] = []
    invalid_reads = 0
    sample_rows = 0
    failures: list[str] = []

    print(f"Guardian MT5 COMMON BRIDGE V1 smoke START | {utc_iso(start)}")
    print(f"duration={args.minutes:.2f} min | data={data}")
    print(f"FILE_COMMON target={out}")
    print("Expected: one collector, one coverage-aware engine, atomic shared CSV, changing generation_id.")

    try:
        deadline = asyncio.get_running_loop().time() + args.minutes * 60.0
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(2.0)
            try:
                publish_once(data / "market_state_v1_coveragefix.json", out)
                rows = read_csv(out)
                if len(rows) != 2 or {r.get("symbol") for r in rows} != {"BTCUSD", "ETHUSD"}:
                    invalid_reads += 1
                    continue
                gens = {int(r["generation_id"]) for r in rows}
                if len(gens) != 1:
                    invalid_reads += 1
                    continue
                generations.extend(gens)
                sample_rows += len(rows)
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                invalid_reads += 1
    finally:
        collector.stop_event.set()
        state.stop_event.set()
        await asyncio.gather(collector_task, state_task, return_exceptions=True)

    stop = now_ms()
    raw = summarize(data, start, stop)
    final: list[dict[str, str]] = []
    try:
        final = read_csv(out)
    except OSError:
        failures.append("common CSV missing")

    if invalid_reads:
        failures.append(f"invalid/partial common reads={invalid_reads}")
    if len(set(generations)) < 2:
        failures.append("generation_id did not advance through bridge")
    if raw.get("gate") != "PASS":
        failures.append("raw collector gate failed")

    if final:
        if {r.get("symbol") for r in final} != {"BTCUSD", "ETHUSD"}:
            failures.append("final common CSV symbols invalid")
        for row in final:
            if row.get("status") != "OK":
                failures.append(f"{row.get('symbol')} status={row.get('status')}")
            try:
                if int(float(row.get("core_age_ms") or "999999")) > 20_000:
                    failures.append(f"{row.get('symbol')} core stale")
            except ValueError:
                failures.append(f"{row.get('symbol')} core age invalid")
        header = set(final[0].keys())
        if any(token in key.lower() for key in header for token in ("buy", "sell", "signal")):
            failures.append("strategy decision-like column found")

    summary = {
        "schema_version": 1,
        "smoke_start_ms": start,
        "smoke_start_utc": utc_iso(start),
        "smoke_stop_ms": stop,
        "smoke_stop_utc": utc_iso(stop),
        "observed_duration_seconds": round((stop - start) / 1000.0, 3),
        "common_files_dir": str(common),
        "common_csv": str(out),
        "generation_samples": len(generations),
        "unique_generations": len(set(generations)),
        "invalid_common_reads": invalid_reads,
        "sample_rows": sample_rows,
        "raw_collector_gate": raw.get("gate"),
        "raw_duplicate_event_ids": raw.get("duplicate_event_ids"),
        "raw_future_availability_violations": raw.get("future_availability_violations"),
        "final_rows": final,
        "failures": failures,
        "gate": "PASS" if not failures else "REVIEW",
    }

    path = data / f"smoke_mt5_common_bridge_summary_{start}.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("\n=== GUARDIAN MT5 COMMON BRIDGE V1 SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"\nSummary saved: {path}")
    print(f"MT5 FILE_COMMON CSV: {out}")
    return 0 if summary["gate"] == "PASS" else 2


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(run_smoke(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
