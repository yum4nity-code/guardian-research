#!/usr/bin/env python3
"""Live gate for Binance + validated Bybit EIB + multi-venue state V1.

Run only after stopping any existing Guardian shared runtime, so there is exactly
one writer per provider during this gate.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from binance_collector_v1 import BinanceCollector, BinanceJsonlRecorder, default_data_dir
from collector_v1 import JsonlRecorder
from collector_v1_healthfix import BybitCollectorHealthFixed
from market_state_multivenue_v1 import MultiVenueMarketStateService


def utc_iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()


def read_window(data_dir: Path, prefix: str, start_ms: int, stop_ms: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in sorted(data_dir.glob(f"{prefix}_*.jsonl")):
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                        ts = int(rec.get("available_at_ms", -1))
                    except (json.JSONDecodeError, TypeError, ValueError):
                        continue
                    if start_ms <= ts <= stop_ms:
                        out.append(rec)
        except OSError:
            continue
    return out


def core_key(rec: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(rec.get("venue") or ""),
        str(rec.get("canonical_symbol") or ""),
        str(rec.get("market_type") or ""),
        str(rec.get("metric") or ""),
        str(rec.get("quality", {}).get("status") or ""),
    )


def required_channels() -> set[tuple[str, str, str, str]]:
    req: set[tuple[str, str, str, str]] = set()
    for venue in ("BYBIT", "BINANCE"):
        for symbol in ("BTCUSD", "ETHUSD"):
            req.update({
                (venue, symbol, "spot", "last_price"),
                (venue, symbol, "perpetual", "last_price"),
                (venue, symbol, "perpetual", "open_interest"),
                (venue, symbol, "perpetual", "funding_rate"),
                (venue, symbol, "aggregate", "health"),
            })
    return req


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter((r.get("venue"), r.get("canonical_symbol"), r.get("market_type"), r.get("metric")) for r in records)
    ids = [str(r.get("event_id") or "") for r in records if r.get("event_id")]
    duplicate_ids = len(ids) - len(set(ids))
    availability_before_receive = 0
    invalid_venue = 0
    observed = set()
    for rec in records:
        try:
            if int(rec["available_at_ms"]) < int(rec["received_ts_ms"]):
                availability_before_receive += 1
        except (KeyError, TypeError, ValueError):
            availability_before_receive += 1
        venue = str(rec.get("venue") or "")
        if venue not in {"BYBIT", "BINANCE"}:
            invalid_venue += 1
        observed.add((venue, str(rec.get("canonical_symbol") or ""), str(rec.get("market_type") or ""), str(rec.get("metric") or "")))
    missing = sorted(required_channels() - observed)
    compact_counts = {
        "|".join(str(x) for x in k): v
        for k, v in sorted(counts.items(), key=lambda kv: tuple(str(x) for x in kv[0]))
    }
    return {
        "counts": compact_counts,
        "unique_events": len(set(ids)),
        "duplicate_event_ids": duplicate_ids,
        "availability_before_receive_violations": availability_before_receive,
        "invalid_venue_records": invalid_venue,
        "missing_core_channels": ["|".join(x) for x in missing],
    }


def load_final_state(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_final_state(state: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if state.get("engine") != "guardian-market-state-multivenue-v1":
        failures.append("unexpected multi-venue engine id")
    if state.get("research_guardrail") != "NO_STRATEGY_DECISION_OUTPUT":
        failures.append("strategy guardrail missing")
    venues = state.get("venues") or {}
    for venue in ("BYBIT", "BINANCE"):
        if venue not in venues:
            failures.append(f"missing venue snapshot {venue}")
            continue
        for symbol in ("BTCUSD", "ETHUSD"):
            sym = ((venues[venue].get("symbols") or {}).get(symbol) or {})
            if (sym.get("quality") or {}).get("status") != "OK":
                failures.append(f"{venue} {symbol} final status != OK")
            for field in ("spot_last", "perp_last", "open_interest", "funding_rate", "basis_pct"):
                if (sym.get("raw") or {}).get(field) is None:
                    failures.append(f"{venue} {symbol} missing raw {field}")
    cross = state.get("cross_venue") or {}
    for symbol in ("BTCUSD", "ETHUSD"):
        cv = cross.get(symbol) or {}
        if not (cv.get("quality") or {}).get("both_core_ok"):
            failures.append(f"{symbol} both_core_ok=false")
        spread = cv.get("price_spread_pct") or {}
        if spread.get("binance_minus_bybit_spot") is None or spread.get("binance_minus_bybit_perp") is None:
            failures.append(f"{symbol} cross-venue price spread missing")
        funding = cv.get("funding") or {}
        if funding.get("bybit") is None or funding.get("binance") is None:
            failures.append(f"{symbol} cross-venue funding missing")
        oi1 = (((cv.get("open_interest_change_pct") or {}).get("mean") or {}).get("1m"))
        if oi1 is None:
            failures.append(f"{symbol} cross-venue OI 1m mean not covered")
        liq = cv.get("liquidation_confirmation") or {}
        if ((liq.get("long_active_venues") or {}).get("1m")) is None:
            failures.append(f"{symbol} long liquidation 1m coverage incomplete")
        if ((liq.get("short_active_venues") or {}).get("1m")) is None:
            failures.append(f"{symbol} short liquidation 1m coverage incomplete")
        if "not exhaustive" not in str(liq.get("semantics") or ""):
            failures.append(f"{symbol} liquidation sampling caveat missing")
    return failures


async def run_smoke(args: argparse.Namespace) -> int:
    data_dir: Path = args.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    start_ms = time.time_ns() // 1_000_000
    print(f"Guardian BINANCE MULTI-VENUE V1 smoke START | {utc_iso(start_ms)}")
    print(f"duration={args.minutes:.2f} min | data={data_dir}")
    print("Expected: exactly one Bybit collector + one Binance collector; venue-separated state; no strategy output.")

    bybit = BybitCollectorHealthFixed(
        ["BTCUSD", "ETHUSD"], JsonlRecorder(data_dir), args.poll_seconds, args.health_seconds
    )
    binance = BinanceCollector(
        ["BTCUSD", "ETHUSD"], BinanceJsonlRecorder(data_dir), args.poll_seconds, args.health_seconds
    )
    state = MultiVenueMarketStateService(data_dir, interval_seconds=1.0)

    tasks = [
        asyncio.create_task(bybit.run(), name="bybit"),
        asyncio.create_task(binance.run(), name="binance"),
        asyncio.create_task(state.run(), name="multivenue_state"),
    ]
    try:
        await asyncio.sleep(max(120.0, args.minutes * 60.0))
    finally:
        bybit.stop_event.set()
        binance.stop_event.set()
        state.stop_event.set()
        await asyncio.gather(*tasks, return_exceptions=True)

    stop_ms = time.time_ns() // 1_000_000
    # One final deterministic state publication after both collectors have flushed.
    final = state.publish_once(stop_ms)
    records = read_window(data_dir, "bybit_eib_v1", start_ms, stop_ms)
    records += read_window(data_dir, "binance_eib_v1", start_ms, stop_ms)
    rec_summary = summarize_records(records)
    failures = validate_final_state(final)
    if rec_summary["duplicate_event_ids"]:
        failures.append("duplicate event ids in smoke window")
    if rec_summary["availability_before_receive_violations"]:
        failures.append("availability before receive detected")
    if rec_summary["invalid_venue_records"]:
        failures.append("invalid venue records detected")
    if rec_summary["missing_core_channels"]:
        failures.append("missing core provider channels")

    result = {
        "schema_version": 1,
        "smoke_start_ms": start_ms,
        "smoke_start_utc": utc_iso(start_ms),
        "smoke_stop_ms": stop_ms,
        "smoke_stop_utc": utc_iso(stop_ms),
        "observed_duration_seconds": round((stop_ms - start_ms) / 1000.0, 3),
        **rec_summary,
        "final_generation_id": final.get("generation_id"),
        "final_cross_venue": final.get("cross_venue"),
        "failures": failures,
        "gate": "PASS" if not failures else "REVIEW",
    }

    summary_path = data_dir / f"smoke_binance_multivenue_summary_{start_ms}.json"
    summary_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("\n=== GUARDIAN BINANCE MULTI-VENUE V1 SMOKE SUMMARY ===")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"\nSummary saved: {summary_path}")
    print(f"Multi-venue state: {data_dir / 'market_state_multivenue_v1.json'}")
    if not failures:
        print("\n[Guardian] FULL GATE BINANCE MULTI-VENUE V1: PASS.")
        return 0
    print("\n[Guardian] FULL GATE BINANCE MULTI-VENUE V1: REVIEW.")
    return 2


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Guardian Binance multi-venue live smoke")
    p.add_argument("--minutes", type=float, default=3.0)
    p.add_argument("--data-dir", type=Path, default=default_data_dir())
    p.add_argument("--poll-seconds", type=float, default=5.0)
    p.add_argument("--health-seconds", type=float, default=5.0)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(run_smoke(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
