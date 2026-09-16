#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import xau_edge_discovery_r21_r25_v1_02 as m


def B(dt, o=100.0, h=101.0, l=99.0, c=100.0):
    return m.Bar(int(dt.timestamp()), dt, "M5", o, h, l, c)


def test_absolute_m5_grid_rejects_30_second_offset():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bad.csv"
        dt = datetime(2019, 1, 15, 13, 20, 30, tzinfo=timezone.utc)
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["timeframe", "server_epoch", "open", "high", "low", "close"])
            w.writeheader()
            w.writerow({"timeframe": "M5", "server_epoch": int(dt.timestamp()), "open": 100, "high": 101, "low": 99, "close": 100})
        try:
            m.load_generated_discovery_bars(p)
        except RuntimeError as e:
            assert "off-grid M5 timestamp" in str(e)
        else:
            raise AssertionError("08:20:30-equivalent off-grid bar was accepted")


def test_jackknife_fails_closed_if_required_replication_undefined():
    bars = []
    # Three baseline days at same clock. Only day 1 has a compressed event.
    for d, ret in [(1, 0.01), (2, 0.02), (3, 0.20)]:
        t = datetime(2019, 1, d, 12, 0, tzinfo=timezone.utc)
        bars.append(B(t, c=100.0))
        bars.append(B(t + timedelta(minutes=5), o=100.0, h=130.0, l=90.0, c=100.0 * (1 + ret)))
    events = [{
        "compression_state": "bottom10",
        "cluster_day": "2019-01-01",
        "utc_minute": 720,
        "abs_fwd_1b": 0.01,
    }]
    s = m.r22_complete_estimator_day_jackknife(bars, events, "bottom10", 1)
    assert s["mean"] is not None
    assert s["cluster_se"] is None
    assert s["cluster_t"] is None
    assert s["event_days"] == 1
    assert s["baseline_days"] == 3
    assert s["required_replicates"] == 3
    assert s["valid_replicates"] == 2
    assert s["undefined_delete_days"] == ["2019-01-01"]
    assert "undefined" in s["reason"]


def test_jackknife_regular_case_still_has_variance():
    bars = []
    for d, ret in [(1, 0.01), (2, 0.02), (3, 0.20)]:
        t = datetime(2019, 1, d, 12, 0, tzinfo=timezone.utc)
        bars.append(B(t, c=100.0))
        bars.append(B(t + timedelta(minutes=5), o=100.0, h=130.0, l=90.0, c=100.0 * (1 + ret)))
    events = [
        {"compression_state": "bottom10", "cluster_day": "2019-01-01", "utc_minute": 720, "abs_fwd_1b": 0.01},
        {"compression_state": "bottom10", "cluster_day": "2019-01-02", "utc_minute": 720, "abs_fwd_1b": 0.02},
    ]
    s = m.r22_complete_estimator_day_jackknife(bars, events, "bottom10", 1)
    assert s["undefined_delete_days"] == []
    assert s["required_replicates"] == 3
    assert s["valid_replicates"] == 3
    assert s["cluster_se"] is not None and s["cluster_se"] > 0
    assert s["cluster_t"] is not None


def _r24_day(breakout_open_minute: int | None):
    # Jan 15 2019: New York is UTC-5, so 08:20 NY = 13:20 UTC.
    start = datetime(2019, 1, 15, 13, 20, tzinfo=timezone.utc)
    bars = []
    for offset in range(0, 101, 5):  # through 10:00 NY inclusive
        dt = start + timedelta(minutes=offset)
        ny_minute = 8 * 60 + 20 + offset
        if offset < 15:
            o, h, l, c = 100, 101, 99, 100
        elif breakout_open_minute is not None and ny_minute == breakout_open_minute:
            o, h, l, c = 100, 103, 99, 102
        else:
            o, h, l, c = 100, 100.8, 99.2, 100
        bars.append(B(dt, o, h, l, c))
    return bars


def test_r24_accepts_0955_breakout():
    ev = m.r24_comex_opening_range_breakout(_r24_day(9 * 60 + 55))
    assert len(ev) == 1
    assert datetime.fromtimestamp(ev[0]["epoch"], tz=timezone.utc).astimezone(m.base.NEW_YORK_TZ).strftime("%H:%M") == "09:55"


def test_r24_excludes_1000_open_bar():
    ev = m.r24_comex_opening_range_breakout(_r24_day(10 * 60))
    assert ev == []


def test_builder_receipt_must_match_frozen_discovery_contract():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "generated.csv"
        p.write_text("x", encoding="utf-8")
        good = {
            "status": "PASS",
            "stage": "discovery",
            "stage_start": m.DISCOVERY_START.isoformat(),
            "stage_end_inclusive": m.DISCOVERY_END.isoformat(),
            "confirmation_opened": False,
            "pre_oos_2025_opened": False,
            "protected_2026_opened": False,
            "output": str(p.resolve()),
            "last_opened_payload_date": "2019-06-28",
        }
        m._validate_builder_receipt(good, p)
        bad = dict(good)
        bad["pre_oos_2025_opened"] = True
        try:
            m._validate_builder_receipt(bad, p)
        except RuntimeError as e:
            assert "receipt mismatch" in str(e)
        else:
            raise AssertionError("unsafe builder receipt accepted")


def test_run_from_index_uses_internal_temp_builder_output_not_external_csv():
    with tempfile.TemporaryDirectory() as td:
        index = Path(td) / "master_index.csv"
        index.write_text("metadata only", encoding="utf-8")
        seen = {}
        old_build = m.sealed_builder.build

        def fake_build(index_path: Path, generated_csv: Path):
            seen["index"] = index_path
            seen["generated"] = generated_csv
            # Minimal aligned discovery bars around 08:20 NY.
            start = datetime(2019, 1, 15, 13, 20, tzinfo=timezone.utc)
            with generated_csv.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["symbol", "timeframe", "server_time", "server_epoch", "open", "high", "low", "close"])
                w.writeheader()
                for i, price in enumerate([100, 101, 102, 103]):
                    dt = start + timedelta(minutes=5 * i)
                    w.writerow({
                        "symbol": "XAUUSD", "timeframe": "M5", "server_time": dt.isoformat(),
                        "server_epoch": int(dt.timestamp()), "open": price, "high": price + .1,
                        "low": price - .1, "close": price,
                    })
            return {
                "status": "PASS", "stage": "discovery",
                "stage_start": m.DISCOVERY_START.isoformat(),
                "stage_end_inclusive": m.DISCOVERY_END.isoformat(),
                "confirmation_opened": False, "pre_oos_2025_opened": False,
                "protected_2026_opened": False,
                "output": str(generated_csv.resolve()),
                "last_opened_payload_date": "2019-01-15",
            }

        m.sealed_builder.build = fake_build
        try:
            payload = m.run_from_index(index, ["R21"])
        finally:
            m.sealed_builder.build = old_build

        assert seen["index"] == index
        assert seen["generated"].name == "sealed_discovery_m5.csv"
        assert seen["generated"].parent != index.parent
        assert payload["stage"] == "discovery"
        assert payload["confirmation_opened"] is False
        assert payload["pre_oos_2025_opened"] is False
        assert payload["protected_2026_opened"] is False
        assert payload["results"]["R21"]["summary"]["event_count"] == 1


def main():
    test_absolute_m5_grid_rejects_30_second_offset()
    test_jackknife_fails_closed_if_required_replication_undefined()
    test_jackknife_regular_case_still_has_variance()
    test_r24_accepts_0955_breakout()
    test_r24_excludes_1000_open_bar()
    test_builder_receipt_must_match_frozen_discovery_contract()
    test_run_from_index_uses_internal_temp_builder_output_not_external_csv()
    print("PASS: R21-R25 v1.02 second-audit regression tests")


if __name__ == "__main__":
    main()
