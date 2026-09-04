#!/usr/bin/env python3
"""Validate an already-completed Binance+Bybit multi-venue smoke capture.

Use this when the live smoke collected its full window but hung during shutdown
because a quiet WebSocket reader remained blocked. This validator does not
collect any new market data and does not trade. It validates the captured
records plus the last multi-venue snapshot produced during that capture.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from binance_collector_v1 import default_data_dir
from smoke_binance_multivenue_v1 import read_window, summarize_records, validate_final_state


def _latest_available(records: list[dict[str, Any]]) -> int:
    vals: list[int] = []
    for rec in records:
        try:
            vals.append(int(rec.get("available_at_ms", -1)))
        except (TypeError, ValueError):
            pass
    return max(vals) if vals else -1


def main() -> int:
    p = argparse.ArgumentParser(description="Validate an existing Guardian Binance multi-venue capture")
    p.add_argument("--start-ms", type=int, required=True)
    p.add_argument("--data-dir", type=Path, default=default_data_dir())
    p.add_argument("--min-seconds", type=float, default=165.0)
    args = p.parse_args()

    data_dir: Path = args.data_dir
    horizon_ms = args.start_ms + 5 * 60_000
    bybit = read_window(data_dir, "bybit_eib_v1", args.start_ms, horizon_ms)
    binance = read_window(data_dir, "binance_eib_v1", args.start_ms, horizon_ms)
    records = bybit + binance

    latest = _latest_available(records)
    observed_seconds = 0.0 if latest < 0 else (latest - args.start_ms) / 1000.0
    rec_summary = summarize_records(records)

    state_path = data_dir / "market_state_multivenue_v1.json"
    failures: list[str] = []
    if not state_path.exists():
        failures.append("market_state_multivenue_v1.json missing")
        state: dict[str, Any] = {}
    else:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        failures.extend(validate_final_state(state))

    if observed_seconds < args.min_seconds:
        failures.append(f"capture too short: {observed_seconds:.3f}s < {args.min_seconds:.3f}s")
    if rec_summary["duplicate_event_ids"]:
        failures.append("duplicate event ids in capture window")
    if rec_summary["availability_before_receive_violations"]:
        failures.append("availability before receive detected")
    if rec_summary["invalid_venue_records"]:
        failures.append("invalid venue records detected")
    if rec_summary["missing_core_channels"]:
        failures.append("missing core provider channels")

    result = {
        "schema_version": 1,
        "mode": "post_capture_validation",
        "start_ms": args.start_ms,
        "latest_record_ms": latest,
        "observed_duration_seconds": round(observed_seconds, 3),
        "bybit_records": len(bybit),
        "binance_records": len(binance),
        **rec_summary,
        "final_generation_id": state.get("generation_id") if state else None,
        "final_cross_venue": state.get("cross_venue") if state else None,
        "failures": failures,
        "gate": "PASS" if not failures else "REVIEW",
    }

    out = data_dir / f"validate_binance_multivenue_capture_{args.start_ms}.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("=== GUARDIAN BINANCE MULTI-VENUE POST-CAPTURE VALIDATION ===")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"\nSummary saved: {out}")
    if failures:
        print("\n[Guardian] BINANCE MULTI-VENUE POST-CAPTURE GATE: REVIEW.")
        return 2
    print("\n[Guardian] BINANCE MULTI-VENUE POST-CAPTURE GATE: PASS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
