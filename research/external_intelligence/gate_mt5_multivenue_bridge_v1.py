#!/usr/bin/env python3
"""Offline gate for the validated multi-venue snapshot -> MT5 FILE_COMMON bridge."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from mt5_common_bridge_multivenue_v1 import default_common_files_dir, default_data_dir, publish_once


def main() -> int:
    p = argparse.ArgumentParser(description="Guardian MT5 multi-venue bridge gate")
    p.add_argument("--data-dir", type=Path, default=default_data_dir())
    p.add_argument("--common-files-dir", type=Path, default=None)
    args = p.parse_args()

    source = args.data_dir / "market_state_multivenue_v1.json"
    common = args.common_files_dir or default_common_files_dir()
    output = common / "GuardianSharedIntelligence" / "market_state_multivenue_v1.csv"

    failures: list[str] = []
    try:
        src = json.loads(source.read_text(encoding="utf-8"))
        result = publish_once(source, output)
        with output.open("r", encoding="ascii", newline="") as f:
            rows = list(csv.DictReader(f, delimiter=";"))
    except Exception as exc:
        print(f"[Guardian][BRIDGE][ERROR] {type(exc).__name__}: {exc}")
        return 2

    if result.get("rows") != 2 or len(rows) != 2:
        failures.append("bridge must publish exactly BTCUSD + ETHUSD rows")
    if {r.get("symbol") for r in rows} != {"BTCUSD", "ETHUSD"}:
        failures.append("unexpected symbol rows")
    if any(r.get("bridge_schema_version") != "2" for r in rows):
        failures.append("unexpected bridge schema version")
    if any(r.get("generation_id") != str(src.get("generation_id")) for r in rows):
        failures.append("generation mismatch")
    for row in rows:
        symbol = row.get("symbol", "?")
        if row.get("bybit_status") != "OK":
            failures.append(f"{symbol} Bybit not OK")
        if row.get("binance_status") != "OK":
            failures.append(f"{symbol} Binance not OK")
        if row.get("both_core_ok") != "1":
            failures.append(f"{symbol} both_core_ok != 1")
        for field in (
            "bybit_spot_last", "binance_spot_last", "spot_spread_pct",
            "bybit_perp_last", "binance_perp_last", "perp_spread_pct",
            "bybit_funding_rate", "binance_funding_rate", "funding_spread_fraction",
            "bybit_basis_pct", "binance_basis_pct", "basis_spread_pp",
            "oi_mean_1m", "oi_dispersion_1m", "oi_same_direction_1m",
            "spot_return_mean_1m", "perp_return_mean_1m", "dislocation_mean_1m",
        ):
            if row.get(field, "") == "":
                failures.append(f"{symbol} missing {field}")

    forbidden = {"buy", "sell", "signal", "entry", "stop_loss", "take_profit", "risk_action"}
    header_lower = {h.lower() for h in (rows[0].keys() if rows else [])}
    if forbidden & header_lower:
        failures.append("strategy/trading field leaked into neutral bridge")

    print("=== GUARDIAN MT5 MULTI-VENUE BRIDGE V1 GATE ===")
    print(f"source_generation={src.get('generation_id')}")
    print(f"output={output}")
    print(f"rows={len(rows)}")
    for row in rows:
        print(
            f"[ROW] {row['symbol']} BYBIT={row['bybit_status']} BINANCE={row['binance_status']} "
            f"both={row['both_core_ok']} spotSpread={row['spot_spread_pct']}% "
            f"oi1m={row['oi_mean_1m']}% oiAgree1m={row['oi_same_direction_1m']}"
        )
    print(f"failures={failures}")
    if failures:
        print("[Guardian] MT5 MULTI-VENUE BRIDGE V1 GATE: REVIEW.")
        return 2
    print("[Guardian] MT5 MULTI-VENUE BRIDGE V1 GATE: PASS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
