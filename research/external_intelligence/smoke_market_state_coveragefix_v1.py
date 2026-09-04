#!/usr/bin/env python3
"""Continuous live smoke for the coverage-aware Guardian market-state V1 candidate."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from collector_v1 import JsonlRecorder, default_data_dir, now_ms, utc_iso
from collector_v1_healthfix import BybitCollectorHealthFixed
from market_state_v1_coveragefix import MarketStateServiceCoverageFixed
from smoke_v1 import summarize


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Guardian coverage-aware market-state V1 smoke")
    p.add_argument("--minutes", type=float, default=6.0)
    p.add_argument("--data-dir", type=Path, default=default_data_dir())
    return p.parse_args(argv)


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


async def run_smoke(args: argparse.Namespace) -> int:
    if args.minutes < 5.5:
        raise ValueError("--minutes must be >= 5.5 so the 5m window can warm up")

    args.data_dir.mkdir(parents=True, exist_ok=True)
    start_ms = now_ms()
    recorder = JsonlRecorder(args.data_dir)
    collector = BybitCollectorHealthFixed(["BTCUSD", "ETHUSD"], recorder, 5.0, 5.0)
    service = MarketStateServiceCoverageFixed(args.data_dir, interval_seconds=1.0)
    snapshot_path = args.data_dir / "market_state_v1_coveragefix.json"

    print(f"Guardian MARKET STATE COVERAGEFIX V1 smoke START | {utc_iso(start_ms)}")
    print(f"duration={args.minutes:.2f} min | data={args.data_dir}")
    print("Expected: 1m/5m fresh anchors after warm-up; incomplete long windows must be null, not fake zero/old-anchor values.")

    collector_task = asyncio.create_task(collector.run())
    service_task = asyncio.create_task(service.run())
    generations: list[int] = []

    try:
        deadline = asyncio.get_running_loop().time() + args.minutes * 60.0
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(5.0)
            snap = _read_json(snapshot_path)
            if snap is not None:
                try:
                    generations.append(int(snap["generation_id"]))
                except (KeyError, TypeError, ValueError):
                    pass
    finally:
        collector.stop_event.set()
        service.stop_event.set()
        await asyncio.gather(collector_task, service_task, return_exceptions=True)

    stop_ms = now_ms()
    raw_summary = summarize(args.data_dir, start_ms, stop_ms)
    final = _read_json(snapshot_path)
    failures: list[str] = []

    if final is None:
        failures.append("coveragefix snapshot missing/invalid")
    else:
        if int(final.get("computed_at_ms", 0)) > stop_ms:
            failures.append("coveragefix snapshot computed in the future")
        symbols = final.get("symbols") or {}
        for symbol in ("BTCUSD", "ETHUSD"):
            row = symbols.get(symbol) or {}
            quality = row.get("quality") or {}
            coverage = row.get("coverage") or {}
            returns = row.get("returns_pct") or {}
            oi_changes = row.get("open_interest_change_pct") or {}
            liq = row.get("liquidation_notional_usdt_est") or {}

            if quality.get("status") != "OK":
                failures.append(f"{symbol} final quality not OK")
            if quality.get("core_age_ms") is None or int(quality["core_age_ms"]) > 20_000:
                failures.append(f"{symbol} core data stale/missing")

            for feature_key, value_map in (
                ("spot_return", (returns.get("spot") or {})),
                ("perpetual_return", (returns.get("perpetual") or {})),
                ("open_interest_change", oi_changes),
            ):
                cov_map = coverage.get(feature_key) or {}
                for label in ("1m", "5m", "15m", "1h"):
                    cov = cov_map.get(label) or {}
                    value = value_map.get(label)
                    if cov.get("complete") and value is None:
                        failures.append(f"{symbol} {feature_key} {label} complete but null")
                    if not cov.get("complete") and value is not None:
                        failures.append(f"{symbol} {feature_key} {label} incomplete but numeric")

            # Six continuous minutes should normally make 1m and 5m endpoint
            # features usable. If not, the gate correctly asks for review.
            for feature_key in ("spot_return", "perpetual_return", "open_interest_change"):
                cov_map = coverage.get(feature_key) or {}
                for label in ("1m", "5m"):
                    if not (cov_map.get(label) or {}).get("complete"):
                        failures.append(f"{symbol} {feature_key} {label} did not warm up continuously")

            liq_cov = coverage.get("liquidation") or {}
            long_map = liq.get("long") or {}
            short_map = liq.get("short") or {}
            net_map = liq.get("net_short_minus_long") or {}
            for label in ("1m", "5m", "15m", "1h"):
                complete = bool((liq_cov.get(label) or {}).get("complete"))
                vals = (long_map.get(label), short_map.get(label), net_map.get(label))
                if complete and any(v is None for v in vals):
                    failures.append(f"{symbol} liquidation {label} complete but null")
                if not complete and any(v is not None for v in vals):
                    failures.append(f"{symbol} liquidation {label} incomplete but numeric")

            # After a clean six-minute run, liquidation coverage should be
            # demonstrably complete for the short windows as well.
            for label in ("1m", "5m"):
                if not (liq_cov.get(label) or {}).get("complete"):
                    failures.append(f"{symbol} liquidation {label} did not obtain continuous coverage")

        text = json.dumps(final).lower()
        if '"buy"' in text or '"sell"' in text or '"signal"' in text:
            failures.append("strategy-decision-like field found")

    unique_generations = len(set(generations))
    if unique_generations < 2:
        failures.append("generation_id did not advance")
    if raw_summary.get("gate") != "PASS":
        failures.append("underlying raw collector gate failed")

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

    summary_path = args.data_dir / f"smoke_market_state_coveragefix_summary_{start_ms}.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("\n=== GUARDIAN MARKET STATE COVERAGEFIX V1 SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"\nSummary saved: {summary_path}")
    print(f"Candidate shared state: {snapshot_path}")
    return 0 if summary["gate"] == "PASS" else 2


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        return asyncio.run(run_smoke(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
