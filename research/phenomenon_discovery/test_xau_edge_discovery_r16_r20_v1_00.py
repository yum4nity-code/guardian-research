#!/usr/bin/env python3
"""Cold-audit smoke tests for R16-R20 v1.00. No external framework required."""
from __future__ import annotations

import csv
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import xau_edge_discovery_r16_r20_v1_00 as batch


def write_csv(path: Path, start: datetime, bars: int, tf: str = "M5") -> None:
    step = batch.ALLOWED_TIMEFRAMES[tf]
    fields = ["symbol", "timeframe", "server_time", "server_epoch", "open", "high", "low", "close"]
    price = 2000.0
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i in range(bars):
            epoch = int(start.timestamp()) + i * step
            dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
            move = 0.6 if i % 7 else -1.0
            o = price
            c = price + move
            h = max(o, c) + 0.2
            l = min(o, c) - 0.2
            w.writerow({"symbol": "XAUUSD", "timeframe": tf,
                        "server_time": dt.strftime("%Y.%m.%d %H:%M"),
                        "server_epoch": epoch, "open": o, "high": h, "low": l, "close": c})
            price = c


def test_protected_2026_rejected(tmp: Path) -> None:
    p = tmp / "protected.csv"
    write_csv(p, datetime(2026, 1, 2, tzinfo=timezone.utc), 10)
    try:
        batch.load_bars(p, stage="preoos")
    except RuntimeError as e:
        assert "PROTECTED 2026" in str(e)
    else:
        raise AssertionError("2026 was not rejected")


def test_2025_stage_gate(tmp: Path) -> None:
    p = tmp / "gate.csv"
    write_csv(p, datetime(2024, 12, 31, 23, 0, tzinfo=timezone.utc), 40)
    discovery = batch.load_bars(p, stage="discovery")
    preoos = batch.load_bars(p, stage="preoos")
    assert discovery and all(b.dt.year < 2025 for b in discovery)
    assert preoos and all(b.dt.year == 2025 for b in preoos)


def test_round_math() -> None:
    assert batch._nearest_round(2037.0, 10.0) == 2040.0
    assert batch._nearest_round(2037.0, 25.0) == 2025.0
    assert batch._nearest_round(2037.0, 50.0) == 2050.0
    assert batch._nearest_round(2037.0, 100.0) == 2000.0


def test_forward_gap_rejected() -> None:
    B = batch.Bar
    a = B(0, datetime(2024, 1, 1, tzinfo=timezone.utc), "M5", 100, 101, 99, 100)
    b = B(600, datetime(2024, 1, 1, 0, 10, tzinfo=timezone.utc), "M5", 100, 102, 99, 101)
    assert batch.forward_return([a, b], 0, 1) is None


def test_dst_local_clock() -> None:
    B = batch.Bar
    winter = B(int(datetime(2024, 1, 15, 8, 0, tzinfo=timezone.utc).timestamp()), datetime(2024, 1, 15, 8, 0, tzinfo=timezone.utc), "M5", 1, 1, 1, 1)
    summer = B(int(datetime(2024, 7, 15, 7, 0, tzinfo=timezone.utc).timestamp()), datetime(2024, 7, 15, 7, 0, tzinfo=timezone.utc), "M5", 1, 1, 1, 1)
    assert winter.local_minute(batch.LONDON_TZ) == 8 * 60
    assert summer.local_minute(batch.LONDON_TZ) == 8 * 60


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        test_protected_2026_rejected(tmp)
        test_2025_stage_gate(tmp)
    test_round_math()
    test_forward_gap_rejected()
    test_dst_local_clock()
    print("PASS: R16-R20 cold-audit smoke tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
