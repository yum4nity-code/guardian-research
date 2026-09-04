#!/usr/bin/env python3
"""Guardian MT5 Common Files bridge V1.

Reads the validated coverage-aware market-state JSON and publishes a compact,
strategy-neutral CSV into MetaTrader 5 FILE_COMMON so every local terminal can
read the same generation. No trading API, credentials, or order capability.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path
from typing import Any

DEFAULT_SOURCE_NAME = "market_state_v1_coveragefix.json"
DEFAULT_SUBDIR = "GuardianSharedIntelligence"
DEFAULT_OUTPUT_NAME = "market_state_v1.csv"

# Windows may briefly reject os.replace() while an MT5 reader has the destination
# file open. The reader keeps each handle only for a very short interval, so a
# bounded retry preserves atomic publication without turning a harmless sharing
# collision into a dropped generation or noisy REVIEW event.
REPLACE_RETRY_ATTEMPTS = 25
REPLACE_RETRY_DELAY_SECONDS = 0.01

FIELDS = [
    "bridge_schema_version", "generation_id", "computed_at_ms", "symbol", "status", "core_age_ms",
    "spot_last", "perp_last", "open_interest", "funding_rate", "basis_pct",
    "spot_return_1m", "spot_return_5m", "perp_return_1m", "perp_return_5m",
    "perp_minus_spot_1m", "perp_minus_spot_5m", "oi_change_1m", "oi_change_5m",
    "long_liq_1m", "long_liq_5m", "short_liq_1m", "short_liq_5m",
    "liq_net_short_minus_long_1m", "liq_net_short_minus_long_5m",
    "cov_spot_1m", "cov_spot_5m", "cov_perp_1m", "cov_perp_5m",
    "cov_oi_1m", "cov_oi_5m", "cov_liq_1m", "cov_liq_5m",
]


def default_data_dir() -> Path:
    env = os.getenv("GUARDIAN_EIB_DATA_DIR")
    if env:
        return Path(env)
    if os.name == "nt":
        return Path(r"D:\MT5_Backtests\Research\ExternalIntelligence")
    return Path("./guardian_eib_data")


def default_common_files_dir() -> Path:
    env = os.getenv("GUARDIAN_MT5_COMMON_FILES")
    if env:
        return Path(env)
    appdata = os.getenv("APPDATA")
    if os.name == "nt" and appdata:
        return Path(appdata) / "MetaQuotes" / "Terminal" / "Common" / "Files"
    raise RuntimeError("Set GUARDIAN_MT5_COMMON_FILES or pass --common-files-dir.")


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


def flatten_snapshot(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    generation = snapshot.get("generation_id")
    computed_at_ms = snapshot.get("computed_at_ms")
    rows: list[dict[str, str]] = []
    for symbol in ("BTCUSD", "ETHUSD"):
        s = (snapshot.get("symbols") or {}).get(symbol) or {}
        row = {
            "bridge_schema_version": "1",
            "generation_id": _cell(generation),
            "computed_at_ms": _cell(computed_at_ms),
            "symbol": symbol,
            "status": _cell(_get(s, "quality", "status")),
            "core_age_ms": _cell(_get(s, "quality", "core_age_ms")),
            "spot_last": _cell(_get(s, "raw", "spot_last")),
            "perp_last": _cell(_get(s, "raw", "perp_last")),
            "open_interest": _cell(_get(s, "raw", "open_interest")),
            "funding_rate": _cell(_get(s, "raw", "funding_rate")),
            "basis_pct": _cell(_get(s, "raw", "basis_pct")),
            "spot_return_1m": _cell(_get(s, "returns_pct", "spot", "1m")),
            "spot_return_5m": _cell(_get(s, "returns_pct", "spot", "5m")),
            "perp_return_1m": _cell(_get(s, "returns_pct", "perpetual", "1m")),
            "perp_return_5m": _cell(_get(s, "returns_pct", "perpetual", "5m")),
            "perp_minus_spot_1m": _cell(_get(s, "returns_pct", "perp_minus_spot_pp", "1m")),
            "perp_minus_spot_5m": _cell(_get(s, "returns_pct", "perp_minus_spot_pp", "5m")),
            "oi_change_1m": _cell(_get(s, "open_interest_change_pct", "1m")),
            "oi_change_5m": _cell(_get(s, "open_interest_change_pct", "5m")),
            "long_liq_1m": _cell(_get(s, "liquidation_notional_usdt_est", "long", "1m")),
            "long_liq_5m": _cell(_get(s, "liquidation_notional_usdt_est", "long", "5m")),
            "short_liq_1m": _cell(_get(s, "liquidation_notional_usdt_est", "short", "1m")),
            "short_liq_5m": _cell(_get(s, "liquidation_notional_usdt_est", "short", "5m")),
            "liq_net_short_minus_long_1m": _cell(_get(s, "liquidation_notional_usdt_est", "net_short_minus_long", "1m")),
            "liq_net_short_minus_long_5m": _cell(_get(s, "liquidation_notional_usdt_est", "net_short_minus_long", "5m")),
            "cov_spot_1m": _cell(_get(s, "coverage", "spot_return", "1m", "complete")),
            "cov_spot_5m": _cell(_get(s, "coverage", "spot_return", "5m", "complete")),
            "cov_perp_1m": _cell(_get(s, "coverage", "perpetual_return", "1m", "complete")),
            "cov_perp_5m": _cell(_get(s, "coverage", "perpetual_return", "5m", "complete")),
            "cov_oi_1m": _cell(_get(s, "coverage", "open_interest_change", "1m", "complete")),
            "cov_oi_5m": _cell(_get(s, "coverage", "open_interest_change", "5m", "complete")),
            "cov_liq_1m": _cell(_get(s, "coverage", "liquidation", "1m", "complete")),
            "cov_liq_5m": _cell(_get(s, "coverage", "liquidation", "5m", "complete")),
        }
        rows.append(row)
    return rows


def _replace_with_retry(tmp: Path, path: Path) -> int:
    """Atomically replace path, retrying only transient access collisions.

    Returns the number of retries used. Any persistent error still propagates so
    the runtime can surface it as REVIEW instead of silently degrading.
    """
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
        writer = csv.DictWriter(
            f,
            fieldnames=FIELDS,
            delimiter=";",
            lineterminator="\n",
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)
        f.flush()
        os.fsync(f.fileno())
    return _replace_with_retry(tmp, path)


def publish_once(source_path: Path, output_path: Path) -> dict[str, Any]:
    snapshot = json.loads(source_path.read_text(encoding="utf-8"))
    if snapshot.get("schema_version") != 1:
        raise ValueError("unsupported market state schema")
    if snapshot.get("engine") != "guardian-market-state-v1":
        raise ValueError("unexpected market state engine")
    rows = flatten_snapshot(snapshot)
    if any(not row["generation_id"] for row in rows):
        raise ValueError("missing generation_id")
    replace_retries = write_atomic_csv(output_path, rows)
    return {
        "generation_id": int(snapshot["generation_id"]),
        "computed_at_ms": int(snapshot["computed_at_ms"]),
        "rows": len(rows),
        "output": str(output_path),
        "replace_retries": replace_retries,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Guardian MT5 Common Files bridge V1")
    p.add_argument("--data-dir", type=Path, default=default_data_dir())
    p.add_argument("--source-name", default=DEFAULT_SOURCE_NAME)
    p.add_argument("--common-files-dir", type=Path, default=None)
    p.add_argument("--subdir", default=DEFAULT_SUBDIR)
    p.add_argument("--output-name", default=DEFAULT_OUTPUT_NAME)
    p.add_argument("--interval-seconds", type=float, default=1.0)
    p.add_argument("--once", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    source = args.data_dir / args.source_name
    common = args.common_files_dir or default_common_files_dir()
    output = common / args.subdir / args.output_name
    print("Guardian MT5 Common Files bridge V1 START")
    print(f"source={source}")
    print(f"output={output}")
    print("Read-only market facts. No trading endpoints. No order capability.")
    last_generation: int | None = None

    while True:
        try:
            result = publish_once(source, output)
            generation = result["generation_id"]
            if generation != last_generation:
                suffix = ""
                if result.get("replace_retries", 0):
                    suffix = f" replace_retries={result['replace_retries']}"
                print(f"[BRIDGE][OK] generation={generation} rows={result['rows']}{suffix}")
                last_generation = generation
        except FileNotFoundError:
            print(f"[BRIDGE][WAIT] source missing: {source}")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"[BRIDGE][REVIEW] {type(exc).__name__}: {exc}")

        if args.once:
            return 0 if last_generation is not None else 2
        time.sleep(max(0.25, args.interval_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
