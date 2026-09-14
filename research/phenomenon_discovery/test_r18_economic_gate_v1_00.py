#!/usr/bin/env python3
from __future__ import annotations

import csv
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import r18_economic_gate_v1_00 as m


def _bar(epoch: int, px: float, close: float | None = None) -> m.Bar:
    c = px if close is None else close
    hi = max(px, c) + 0.1
    lo = min(px, c) - 0.1
    return m.Bar(epoch, datetime.fromtimestamp(epoch, tz=timezone.utc), px, hi, lo, c)


def test_nonoverlap() -> None:
    events = [
        {"shock_idx": 10, "entry_idx": 11, "gross_2b": 0.001},
        {"shock_idx": 11, "entry_idx": 12, "gross_2b": 0.001},
        {"shock_idx": 13, "entry_idx": 14, "gross_2b": 0.001},
    ]
    got = m.select_nonoverlap(events, 2)
    assert [e["shock_idx"] for e in got] == [10, 13]


def test_cost_math() -> None:
    events = [
        {"gross_1b": 0.0002, "year": 2020},
        {"gross_1b": 0.0001, "year": 2020},
    ]
    s = m.summarize(events, 1, 1.0)
    assert abs(s["gross"]["mean"] - 0.00015) < 1e-12
    assert abs(s["net"]["mean"] - 0.00005) < 1e-12


def test_next_open_entry() -> None:
    # Build 48 quiet returns, then one positive shock. Next-open differs from shock close,
    # so using shock-close accidentally would produce a different PnL.
    start = int(datetime(2019, 1, 2, tzinfo=timezone.utc).timestamp())
    bars: list[m.Bar] = []
    px = 100.0
    bars.append(_bar(start, px))
    for k in range(1, 50):
        px *= 1.0001 if k % 2 else 0.9999
        bars.append(_bar(start + k * 300, px))
    shock_i = 50
    shock_close = px * 1.01
    bars.append(_bar(start + shock_i * 300, px, shock_close))
    # next open gaps up: contrarian short should use 102, not shock close ~101
    bars.append(_bar(start + 51 * 300, 102.0, 101.5))
    bars.append(_bar(start + 52 * 300, 101.5, 101.0))
    events = m.detect_events(bars)
    assert events, "expected a shock event"
    e = events[-1]
    assert e["entry"] == 102.0
    expected_1b = -(bars[51].close / 102.0 - 1.0)
    assert abs(e["gross_1b"] - expected_1b) < 1e-12


def test_loader_never_loads_2025() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.csv"
        rows = [
            ["XAUUSD", "M5", "", int(datetime(2024, 12, 31, 23, 55, tzinfo=timezone.utc).timestamp()), 2000, 2001, 1999, 2000.5, 1],
            ["XAUUSD", "M5", "", int(datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp()), 9999, 10000, 9998, 9999.5, 1],
        ]
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["symbol", "timeframe", "server_time", "server_epoch", "open", "high", "low", "close", "volume"])
            w.writerows(rows)
        bars = m.load_pre2025_m5(p)
        assert len(bars) == 1
        assert bars[0].dt.year == 2024
        assert bars[0].open == 2000


def test_primary_gate_structure() -> None:
    assert m.PRIMARY_HORIZONS == (1, 2)
    assert m.PRIMARY_COST_BPS == 1.0
    assert m.SHOCK_THRESHOLD == 2.0
    assert m.LOOKBACK == 48


def main() -> int:
    test_nonoverlap()
    test_cost_math()
    test_next_open_entry()
    test_loader_never_loads_2025()
    test_primary_gate_structure()
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
