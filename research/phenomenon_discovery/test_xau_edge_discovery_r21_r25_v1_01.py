#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import xau_edge_discovery_r21_r25_v1_01 as m


def B(dt, o, h, l, c):
    return m.Bar(int(dt.timestamp()), dt, "M5", o, h, l, c)


def test_discovery_only_lock():
    assert m._discovery_date_allowed(date(2019, 6, 30))
    try:
        m._discovery_date_allowed(date(2019, 7, 1))
    except RuntimeError as e:
        assert "discovery-only" in str(e)
    else:
        raise AssertionError("confirmation row was not blocked")
    try:
        m._discovery_date_allowed(date(2025, 1, 1))
    except RuntimeError as e:
        assert "discovery-only" in str(e)
    else:
        raise AssertionError("2025 was not blocked")
    try:
        m._discovery_date_allowed(date(2026, 1, 1))
    except RuntimeError as e:
        assert "PROTECTED 2026" in str(e)
    else:
        raise AssertionError("2026 was not blocked")


def test_loader_fails_on_2025_instead_of_filtering():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.csv"
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["timeframe", "server_epoch", "open", "high", "low", "close"])
            w.writeheader()
            dt1 = datetime(2019, 6, 28, tzinfo=timezone.utc)
            dt2 = datetime(2025, 1, 2, tzinfo=timezone.utc)
            for dt in (dt1, dt2):
                w.writerow({"timeframe": "M5", "server_epoch": int(dt.timestamp()), "open": 100, "high": 101, "low": 99, "close": 100})
        try:
            m.load_bars(p)
        except RuntimeError as e:
            assert "discovery-only" in str(e)
        else:
            raise AssertionError("2025 input was silently filtered")


def test_forward_return_checks_each_interval():
    t = datetime(2019, 1, 1, tzinfo=timezone.utc)
    bars = [
        B(t, 100, 101, 99, 100),
        B(t + timedelta(seconds=100), 100, 101, 99, 101),
        B(t + timedelta(seconds=600), 101, 102, 100, 102),
    ]
    assert m.forward_return(bars, 0, 2) is None


def test_cr1_intercept_formula_without_extra_n_factor():
    events = [
        {"cluster_day": "a", "x": 1.0},
        {"cluster_day": "a", "x": 2.0},
        {"cluster_day": "b", "x": -1.0},
        {"cluster_day": "b", "x": 0.0},
    ]
    s = m.cluster_stats(events, "x")
    mean = 0.5
    score_a = (1 - mean) + (2 - mean)
    score_b = (-1 - mean) + (0 - mean)
    expected = math.sqrt((2 / 1) * (score_a ** 2 + score_b ** 2) / 16)
    assert abs(s["cluster_se"] - expected) < 1e-15


def test_r22_keeps_zero_stdev():
    start = datetime(2019, 1, 1, tzinfo=timezone.utc)
    bars = [B(start + timedelta(minutes=5 * i), 100, 100, 100, 100) for i in range(50)]
    st = m._rolling_stdev48(bars)
    assert st[49] == 0.0


def test_r22_prior48_excludes_current_return():
    start = datetime(2019, 1, 2, tzinfo=timezone.utc)
    bars = []
    p = 100.0
    for i in range(50):
        if i == 49:
            p *= 1.10
        elif i > 0:
            p *= 1.0001 if i % 2 else 0.9999
        dt = start + timedelta(minutes=5 * i)
        bars.append(B(dt, p, p + 0.01, p - 0.01, p))
    st = m._rolling_stdev48(bars)
    assert st[49] is not None and st[49] < 0.001


def test_r21_anchor():
    start = datetime(2019, 1, 15, 13, 20, tzinfo=timezone.utc)
    bars = []
    prices = [100, 101, 102, 104]
    for k, p in enumerate(prices):
        dt = start + timedelta(minutes=5 * k)
        bars.append(B(dt, p, p + 0.2, p - 0.2, p))
    ev = m.r21_comex_unconditional_drift(bars)
    assert len(ev) == 1
    assert abs(ev[0]["post_15m"] - (104 / 100 - 1)) < 1e-15


def test_r24_1000_open_bar_not_eligible():
    start = datetime(2019, 1, 15, 13, 20, tzinfo=timezone.utc)
    bars = []
    for k in range((100 - 20) // 5 + 1):
        dt = start + timedelta(minutes=5 * k)
        local_min = 8 * 60 + 20 + 5 * k
        if k < 3:
            o, h, l, c = 100, 101, 99, 100
        elif local_min < 10 * 60:
            o, h, l, c = 100, 100.8, 99.2, 100
        else:
            o, h, l, c = 100, 103, 99, 102
        bars.append(B(dt, o, h, l, c))
    assert m.r24_comex_opening_range_breakout(bars) == []


def test_r24_gap_before_breakout_invalidates_day():
    start = datetime(2019, 1, 15, 13, 20, tzinfo=timezone.utc)
    bars = []
    for mins, c in [(0, 100), (5, 100), (10, 100), (20, 102), (25, 103)]:
        dt = start + timedelta(minutes=mins)
        bars.append(B(dt, c, max(c, 101), min(c, 99), c))
    assert m.r24_comex_opening_range_breakout(bars) == []


def test_r25_fill_summary_has_denominator():
    ev = [
        {"cluster_day": "a", "filled_by_15m": True},
        {"cluster_day": "b", "filled_by_15m": False},
        {"cluster_day": "c", "filled_by_15m": None},
    ]
    s = m._r25_fill_summary(ev)["filled_by_15m"]
    assert s == {"n_valid": 2, "filled": 1, "fill_probability": 0.5}


def test_r22_complete_estimator_includes_baseline_uncertainty():
    bars = []
    for d, ret in [(1, 0.01), (2, 0.02), (3, 0.20)]:
        t = datetime(2019, 1, d, 12, 0, tzinfo=timezone.utc)
        bars.append(B(t, 100, 101, 99, 100))
        bars.append(B(t + timedelta(minutes=5), 100, 130, 90, 100 * (1 + ret)))
    events = [
        {"compression_state": "bottom10", "cluster_day": "2019-01-01", "utc_minute": 720, "abs_fwd_1b": 0.01},
        {"compression_state": "bottom10", "cluster_day": "2019-01-02", "utc_minute": 720, "abs_fwd_1b": 0.02},
    ]
    s = m.r22_complete_estimator_day_jackknife(bars, events, "bottom10", 1)
    assert s["clusters"] == 3
    assert s["cluster_se"] is not None and s["cluster_se"] > 0


def main():
    test_discovery_only_lock()
    test_loader_fails_on_2025_instead_of_filtering()
    test_forward_return_checks_each_interval()
    test_cr1_intercept_formula_without_extra_n_factor()
    test_r22_keeps_zero_stdev()
    test_r22_prior48_excludes_current_return()
    test_r21_anchor()
    test_r24_1000_open_bar_not_eligible()
    test_r24_gap_before_breakout_invalidates_day()
    test_r25_fill_summary_has_denominator()
    test_r22_complete_estimator_includes_baseline_uncertainty()
    print("PASS: R21-R25 v1.01 synthetic audit-regression tests")


if __name__ == "__main__":
    main()
