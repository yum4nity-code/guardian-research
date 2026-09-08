#!/usr/bin/env python3
from __future__ import annotations

"""Phase I-B HCC recovery v1.02.

Deterministic infrastructure repair only. Reuses the frozen v1.01 HCC parser,
provenance checks, 2024/2025 window, news mask, builder, checker and publisher.
The sole change is removal of an over-strict pre-check that required every
synthetic M5 bucket boundary to have an exact M1 row. Normal session/data gaps
can produce a valid five-minute bucket whose first available M1 observation is
after the boundary. The canonical Phase I-B integrity checker already records
this condition as a diagnostic rather than a failure.
"""

from datetime import datetime, timezone
from typing import Any

import phase_ib_hcc_recovery_v1_01 as base


def aggregate_m5_repaired(m1: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    current_key: int | None = None
    bucket: list[dict[str, Any]] = []

    def flush(key: int, items: list[dict[str, Any]]) -> None:
        if not items:
            return
        wall = datetime.fromtimestamp(key, tz=timezone.utc)
        out.append({
            "symbol": "XAUUSD",
            "timeframe": "M5",
            "server_time": wall.strftime("%Y.%m.%d %H:%M:%S"),
            "server_epoch": key,
            "open": float(items[0]["open"]),
            "high": max(float(x["high"]) for x in items),
            "low": min(float(x["low"]) for x in items),
            "close": float(items[-1]["close"]),
            "tick_volume": sum(int(x["tick_volume"]) for x in items),
            "spread": int(items[-1]["spread"]),
            "real_volume": sum(int(x["real_volume"]) for x in items),
        })

    for r in m1:
        key = (int(r["server_epoch"]) // 300) * 300
        if current_key is None:
            current_key = key
        if key != current_key:
            flush(current_key, bucket)
            bucket = []
            current_key = key
        bucket.append(r)
    if current_key is not None:
        flush(current_key, bucket)

    if len(out) < 100000:
        raise RuntimeError(f"M5 total coverage too small before checker: {len(out)}")

    # Do not reject M5 bucket boundaries missing an exact M1 open. The canonical
    # checker reports m5_timestamps_without_exact_m1_open_timestamp and does not
    # classify it as an integrity error; weekend/session/holiday gaps are
    # explicitly expected there. All other v1.01 checks remain unchanged.
    return out


def main() -> int:
    base.aggregate_m5 = aggregate_m5_repaired
    return base.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        import sys
        print(f"PHASE I-B HCC RECOVERY v1.02 FAIL: {exc}", file=sys.stderr)
        raise
