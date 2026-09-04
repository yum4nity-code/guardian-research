#!/usr/bin/env python3
"""Guardian MT5 FILE_COMMON multi-venue bridge V1.

Reads the validated Binance+Bybit multi-venue market-state snapshot and publishes
one compact, strategy-neutral CSV into MetaTrader 5 FILE_COMMON. The bridge is
read-only with respect to MT5 and has no order/trading capability.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path
from typing import Any

from mt5_common_bridge_v1 import default_common_files_dir, default_data_dir

DEFAULT_SOURCE_NAME = "market_state_multivenue_v1.json"
DEFAULT_SUBDIR = "GuardianSharedIntelligence"
DEFAULT_OUTPUT_NAME = "market_state_multivenue_v1.csv"
REPLACE_RETRY_ATTEMPTS = 25
REPLACE_RETRY_DELAY_SECONDS = 0.01

FIELDS = [
    "bridge_schema_version", "generation_id", "computed_at_ms", "symbol",
    "bybit_status", "binance_status", "both_core_ok",
    "bybit_core_age_ms", "binance_core_age_ms",
    "bybit_spot_last", "binance_spot_last", "spot_spread_pct",
    "bybit_perp_last", "binance_perp_last", "perp_spread_pct",
    "bybit_funding_rate", "binance_funding_rate", "funding_spread_fraction",
    "bybit_basis_pct", "binance_basis_pct", "basis_spread_pp",
    "oi_mean_1m", "oi_mean_5m", "oi_dispersion_1m", "oi_dispersion_5m",
    "oi_same_direction_1m", "oi_same_direction_5m",
    "spot_return_mean_1m", "spot_return_mean_5m",
    "perp_return_mean_1m", "perp_return_mean_5m",
    "dislocation_mean_1m", "dislocation_mean_5m",
    "bybit_long_liq_1m", "bybit_long_liq_5m",
    "binance_long_liq_1m", "binance_long_liq_5m",
    "bybit_short_liq_1m", "bybit_short_liq_5m",
    "binance_short_liq_1m", "binance_short_liq_5m",
    "long_active_venues_1m", "long_active_venues_5m",
    "short_active_venues_1m", "short_active_venues_5m",
    "bybit_cov_spot_1m", "bybit_cov_spot_5m",
    "binance_cov_spot_1m", "binance_cov_spot_5m",
    "bybit_cov_perp_1m", "bybit_cov_perp_5m",
    "binance_cov_perp_1m", "binance_cov_perp_5m",
    "bybit_cov_oi_1m", "bybit_cov_oi_5m",
    "binance_cov_oi_1m", "binance_cov_oi_5m",
    "bybit_cov_liq_1m", "bybit_cov_liq_5m",
    "binance_cov_liq_1m", "binance_cov_liq_5m",
]


def _get(d: dict[str, Any], *path: str) -> Any:
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def _venue_symbol(snapshot: dict[str, Any], venue: str, symbol: str) -> dict[str, Any]:
    return (((snapshot.get("venues") or {}).get(venue) or {}).get("symbols") or {}).get(symbol) or {}


def flatten_snapshot(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    generation = snapshot.get("generation_id")
    computed_at_ms = snapshot.get("computed_at_ms")
    rows: list[dict[str, str]] = []

    for symbol in ("BTCUSD", "ETHUSD"):
        bybit = _venue_symbol(snapshot, "BYBIT", symbol)
        binance = _venue_symbol(snapshot, "BINANCE", symbol)
        cross = ((snapshot.get("cross_venue") or {}).get(symbol) or {})
        liq = cross.get("liquidation_confirmation") or {}

        row = {
            "bridge_schema_version": "2",
            "generation_id": _cell(generation),
            "computed_at_ms": _cell(computed_at_ms),
            "symbol": symbol,
            "bybit_status": _cell(_get(bybit, "quality", "status")),
            "binance_status": _cell(_get(binance, "quality", "status")),
            "both_core_ok": _cell(_get(cross, "quality", "both_core_ok")),
            "bybit_core_age_ms": _cell(_get(bybit, "quality", "core_age_ms")),
            "binance_core_age_ms": _cell(_get(binance, "quality", "core_age_ms")),
            "bybit_spot_last": _cell(_get(bybit, "raw", "spot_last")),
            "binance_spot_last": _cell(_get(binance, "raw", "spot_last")),
            "spot_spread_pct": _cell(_get(cross, "price_spread_pct", "binance_minus_bybit_spot")),
            "bybit_perp_last": _cell(_get(bybit, "raw", "perp_last")),
            "binance_perp_last": _cell(_get(binance, "raw", "perp_last")),
            "perp_spread_pct": _cell(_get(cross, "price_spread_pct", "binance_minus_bybit_perp")),
            "bybit_funding_rate": _cell(_get(cross, "funding", "bybit")),
            "binance_funding_rate": _cell(_get(cross, "funding", "binance")),
            "funding_spread_fraction": _cell(_get(cross, "funding", "binance_minus_bybit_fraction")),
            "bybit_basis_pct": _cell(_get(cross, "basis", "bybit_pct")),
            "binance_basis_pct": _cell(_get(cross, "basis", "binance_pct")),
            "basis_spread_pp": _cell(_get(cross, "basis", "binance_minus_bybit_pp")),
            "oi_mean_1m": _cell(_get(cross, "open_interest_change_pct", "mean", "1m")),
            "oi_mean_5m": _cell(_get(cross, "open_interest_change_pct", "mean", "5m")),
            "oi_dispersion_1m": _cell(_get(cross, "open_interest_change_pct", "dispersion_pp", "1m")),
            "oi_dispersion_5m": _cell(_get(cross, "open_interest_change_pct", "dispersion_pp", "5m")),
            "oi_same_direction_1m": _cell(_get(cross, "open_interest_change_pct", "same_direction", "1m")),
            "oi_same_direction_5m": _cell(_get(cross, "open_interest_change_pct", "same_direction", "5m")),
            "spot_return_mean_1m": _cell(_get(cross, "returns_pct", "spot_mean", "1m")),
            "spot_return_mean_5m": _cell(_get(cross, "returns_pct", "spot_mean", "5m")),
            "perp_return_mean_1m": _cell(_get(cross, "returns_pct", "perp_mean", "1m")),
            "perp_return_mean_5m": _cell(_get(cross, "returns_pct", "perp_mean", "5m")),
            "dislocation_mean_1m": _cell(_get(cross, "returns_pct", "dislocation_mean", "1m")),
            "dislocation_mean_5m": _cell(_get(cross, "returns_pct", "dislocation_mean", "5m")),
            "bybit_long_liq_1m": _cell(_get(liq, "bybit_long_observed", "1m")),
            "bybit_long_liq_5m": _cell(_get(liq, "bybit_long_observed", "5m")),
            "binance_long_liq_1m": _cell(_get(liq, "binance_long_observed", "1m")),
            "binance_long_liq_5m": _cell(_get(liq, "binance_long_observed", "5m")),
            "bybit_short_liq_1m": _cell(_get(liq, "bybit_short_observed", "1m")),
            "bybit_short_liq_5m": _cell(_get(liq, "bybit_short_observed", "5m")),
            "binance_short_liq_1m": _cell(_get(liq, "binance_short_observed", "1m")),
            "binance_short_liq_5m": _cell(_get(liq, "binance_short_observed", "5m")),
            "long_active_venues_1m": _cell(_get(liq, "long_active_venues", "1m")),
            "long_active_venues_5m": _cell(_get(liq, "long_active_venues", "5m")),
            "short_active_venues_1m": _cell(_get(liq, "short_active_venues", "1m")),
            "short_active_venues_5m": _cell(_get(liq, "short_active_venues", "5m")),
            "bybit_cov_spot_1m": _cell(_get(bybit, "coverage", "spot_return", "1m", "complete")),
            "bybit_cov_spot_5m": _cell(_get(bybit, "coverage", "spot_return", "5m", "complete")),
            "binance_cov_spot_1m": _cell(_get(binance, "coverage", "spot_return", "1m", "complete")),
            "binance_cov_spot_5m": _cell(_get(binance, "coverage", "spot_return", "5m", "complete")),
            "bybit_cov_perp_1m": _cell(_get(bybit, "coverage", "perpetual_return", "1m", "complete")),
            "bybit_cov_perp_5m": _cell(_get(bybit, "coverage", "perpetual_return", "5m", "complete")),
            "binance_cov_perp_1m": _cell(_get(binance, "coverage", "perpetual_return", "1m", "complete")),
            "binance_cov_perp_5m": _cell(_get(binance, "coverage", "perpetual_return", "5m", "complete")),
            "bybit_cov_oi_1m": _cell(_get(bybit, "coverage", "open_interest_change", "1m", "complete")),
            "bybit_cov_oi_5m": _cell(_get(bybit, "coverage", "open_interest_change", "5m", "complete")),
            "binance_cov_oi_1m": _cell(_get(binance, "coverage", "open_interest_change", "1m", "complete")),
            "binance_cov_oi_5m": _cell(_get(binance, "coverage", "open_interest_change", "5m", "complete")),
            "bybit_cov_liq_1m": _cell(_get(bybit, "coverage", "liquidation", "1m", "complete")),
            "bybit_cov_liq_5m": _cell(_get(bybit, "coverage", "liquidation", "5m", "complete")),
            "binance_cov_liq_1m": _cell(_get(binance, "coverage", "liquidation", "1m", "complete")),
            "binance_cov_liq_5m": _cell(_get(binance, "coverage", "liquidation", "5m", "complete")),
        }
        rows.append(row)
    return rows


def _replace_with_retry(tmp: Path, path: Path) -> int:
    for attempt in range(REPLACE_RETRY_ATTEMPTS):
        try:
            os.replace(tmp, path)
            return attempt
        except PermissionError:
            if attempt + 1 >= REPLACE_RETRY_ATTEMPTS:
                raise
            time.sleep(REPLACE_RETRY_DELAY_SECONDS)
    raise RuntimeError("unreachable replace retry state")


def write_atomic_csv(path: Path, rows: list[dict[str, str]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="ascii", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, delimiter=";", lineterminator="\n", extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
        f.flush()
        os.fsync(f.fileno())
    return _replace_with_retry(tmp, path)


def publish_once(source_path: Path, output_path: Path) -> dict[str, Any]:
    snapshot = json.loads(source_path.read_text(encoding="utf-8"))
    if snapshot.get("schema_version") != 1:
        raise ValueError("unsupported multi-venue market state schema")
    if snapshot.get("engine") != "guardian-market-state-multivenue-v1":
        raise ValueError("unexpected multi-venue market state engine")
    if snapshot.get("research_guardrail") != "NO_STRATEGY_DECISION_OUTPUT":
        raise ValueError("multi-venue strategy guardrail missing")

    rows = flatten_snapshot(snapshot)
    if len(rows) != 2 or any(not row["generation_id"] for row in rows):
        raise ValueError("invalid multi-venue bridge rows")
    replace_retries = write_atomic_csv(output_path, rows)
    return {
        "generation_id": int(snapshot["generation_id"]),
        "computed_at_ms": int(snapshot["computed_at_ms"]),
        "rows": len(rows),
        "output": str(output_path),
        "replace_retries": replace_retries,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Guardian MT5 FILE_COMMON multi-venue bridge V1")
    p.add_argument("--data-dir", type=Path, default=default_data_dir())
    p.add_argument("--source-name", default=DEFAULT_SOURCE_NAME)
    p.add_argument("--common-files-dir", type=Path, default=None)
    p.add_argument("--subdir", default=DEFAULT_SUBDIR)
    p.add_argument("--output-name", default=DEFAULT_OUTPUT_NAME)
    p.add_argument("--once", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    source = args.data_dir / args.source_name
    common = args.common_files_dir or default_common_files_dir()
    output = common / args.subdir / args.output_name
    result = publish_once(source, output)
    print("Guardian MT5 Multi-Venue Common Bridge V1")
    print(f"source={source}")
    print(f"output={output}")
    print(f"generation={result['generation_id']} rows={result['rows']} replace_retries={result['replace_retries']}")
    print("READ ONLY / NO TRADING EFFECT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
