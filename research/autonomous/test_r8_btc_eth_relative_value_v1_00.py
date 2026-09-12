#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("r8", HERE / "r8_btc_eth_relative_value_v1_00.py")
r8 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(r8)


def frame(n=20, start="2024-01-01T00:00:00Z"):
    t = pd.date_range(start, periods=n, freq="1h", tz="UTC")
    return pd.DataFrame({
        "time": t,
        "btc_open": np.full(n, 100.0), "btc_high": np.full(n, 101.0), "btc_low": np.full(n, 99.0), "btc_close": np.full(n, 100.0),
        "eth_open": np.full(n, 50.0), "eth_high": np.full(n, 51.0), "eth_low": np.full(n, 49.0), "eth_close": np.full(n, 50.0),
    })


def test_next_open_and_pair_pnl():
    df = frame(10)
    # high spread at close[1] -> short BTC / long ETH, entry at open[2]. Revert at close[3] -> exit open[4].
    z = np.array([0.0, 2.5, 2.0, 0.2, 0, 0, 0, 0, 0, 0], dtype=float)
    df.loc[2, "btc_open"] = 100.0; df.loc[4, "btc_open"] = 90.0
    df.loc[2, "eth_open"] = 50.0; df.loc[4, "eth_open"] = 55.0
    tr = r8.simulate(df, z, 2.0, 0.5, 8)
    assert len(tr) == 1
    x = tr[0]
    assert x["entry_time"] == df.time.iloc[2]
    assert x["exit_time"] == df.time.iloc[4]
    expected = 0.5 * (-1) * (90/100 - 1) + 0.5 * (1) * (55/50 - 1)
    assert abs(x["gross"] - expected) < 1e-12
    assert abs(x["E1"] - (expected - 0.001)) < 1e-12
    assert abs(x["STRESS"] - (expected - 0.002)) < 1e-12


def test_exit_zero_means_mean_cross():
    assert r8.exit_condition(-0.01, -1, 0.0)
    assert not r8.exit_condition(0.01, -1, 0.0)
    assert r8.exit_condition(0.01, 1, 0.0)
    assert not r8.exit_condition(-0.01, 1, 0.0)


def test_missing_hour_fails_closed():
    df = frame(10)
    df.loc[3:, "time"] = df.loc[3:, "time"] + pd.Timedelta(hours=1)
    z = np.array([0.0, 2.5, 2.0, 0.2, 0, 0, 0, 0, 0, 0], dtype=float)
    tr = r8.simulate(df, z, 2.0, 0.5, 8)
    assert len(tr) == 0


def test_year_boundary_trade_rejected():
    df = frame(8, "2024-12-31T20:00:00Z")
    z = np.array([0.0, 2.5, 2.0, 2.0, 0.2, 0, 0, 0], dtype=float)
    tr = r8.simulate(df, z, 2.0, 0.5, 6)
    assert len(tr) == 0


def test_prior_bar_only_zscore():
    df = frame(8)
    # Vary only BTC closes. With lookback=3, z at index 3 must use closes 0..2, not include index 3.
    vals = np.array([100, 101, 102, 120, 104, 105, 106, 107], dtype=float)
    df["btc_close"] = vals
    z = r8.add_zscore(df, 3)
    spread_prev = np.log(vals[:3]) - np.log(50.0)
    expected = (np.log(vals[3]) - np.log(50.0) - spread_prev.mean()) / spread_prev.std(ddof=1)
    assert abs(z[3] - expected) < 1e-12


def test_protected_row_rejected():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "market.csv"
        pd.DataFrame({
            "time": ["2025-12-31T23:55:00Z", "2026-01-01T00:00:00Z"],
            "open": [1,1], "high": [1,1], "low": [1,1], "close": [1,1],
        }).to_csv(p, index=False)
        try:
            r8.load_market(p)
        except RuntimeError as e:
            assert "protected 2026 row" in str(e)
        else:
            raise AssertionError("2026 row was not rejected")


def test_one_position_at_a_time():
    df = frame(15)
    z = np.array([0, 2.5, 2.5, 2.5, 2.5, 0.2, 2.5, 2.5, 0.2, 0, 0, 0, 0, 0, 0], dtype=float)
    tr = r8.simulate(df, z, 2.0, 0.5, 10)
    assert len(tr) == 2
    assert tr[1]["entry_time"] >= tr[0]["exit_time"]


def main():
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for fn in tests:
        fn()
    print(f"PASS {len(tests)} deterministic R8 preflight tests")


if __name__ == "__main__":
    main()
