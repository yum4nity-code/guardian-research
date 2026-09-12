#!/usr/bin/env python3
from __future__ import annotations

import math
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import r7_long_history_causal_factory_v1_00 as r7


def frame(start: str, periods: int, freq: str = "15min") -> pd.DataFrame:
    t = pd.date_range(start, periods=periods, freq=freq, tz="UTC")
    x = np.arange(periods, dtype=float) + 100.0
    return pd.DataFrame({"time": t, "open": x, "high": x + 1, "low": x - 1, "close": x + 0.5, "volume": np.ones(periods)})


def main() -> int:
    # Resampling is left-labelled/left-closed and uses only bars inside each completed bucket.
    raw = frame("2020-01-01", 12, "5min")
    m15 = r7.resample(raw, "M15")
    assert len(m15) == 4
    assert math.isclose(m15.iloc[0]["open"], raw.iloc[0]["open"])
    assert math.isclose(m15.iloc[0]["close"], raw.iloc[2]["close"])

    # An incomplete source bucket must be dropped instead of synthesizing a candle.
    raw_gap = raw.drop(index=[1]).reset_index(drop=True)
    m15_gap = r7.resample(raw_gap, "M15")
    assert pd.Timestamp("2020-01-01T00:00:00Z") not in set(m15_gap["time"])

    # Discovery cutpoint cannot be changed by huge values added only in 2023+.
    t = pd.Series(pd.to_datetime(["2018-01-01", "2019-01-01", "2020-01-01", "2021-01-01", "2022-01-01"] * 300 + ["2023-01-01"] * 300, utc=True))
    f = pd.Series(list(np.linspace(0, 1, 1500)) + [1e9] * 300)
    cut = r7.fit_cutpoint(f, t, 0.90)
    expected = float(np.quantile(np.linspace(0, 1, 1500), 0.90))
    assert abs(cut - expected) < 1e-12

    # Session mask wraps correctly across midnight.
    df = pd.DataFrame({"time": pd.to_datetime(["2020-01-01 22:00", "2020-01-01 23:00", "2020-01-02 00:00", "2020-01-02 01:00", "2020-01-02 02:00"], utc=True)})
    sm = r7.session_mask(df, 22, 4)
    assert sm.tolist() == [True, True, True, True, False]

    # Long-history causal return must work outside the old 2024/2025 guard.
    cdf = frame("2020-01-01", 10, "15min")
    atr = pd.Series(np.ones(len(cdf)))
    cr = r7.causal_return(cdf, atr, 1, 1, "M15")
    assert np.isfinite(cr[0])

    # Missing-bar paths fail closed rather than treating a later bar as the next bar.
    gap = cdf.drop(index=[2]).reset_index(drop=True)
    gatr = pd.Series(np.ones(len(gap)))
    gr = r7.causal_return(gap, gatr, 1, 1, "M15")
    assert np.isnan(gr[0])

    # Holding paths crossing a year boundary fail closed.
    ydf = frame("2020-12-31 23:30", 6, "15min")
    yatr = pd.Series(np.ones(len(ydf)))
    yr = r7.causal_return(ydf, yatr, 2, 1, "M15")
    assert np.isnan(yr[0])

    # Rule IDs are deterministic and insensitive to dict insertion order.
    a = {"dataset":"BTC","timeframe":"M15","feature":"rsi14","operator":"lt","quantile":.1,"horizon_bars":6,"direction":1,"hour_start":None,"hour_width":None}
    b = dict(reversed(list(a.items())))
    assert r7.stable_rule_id(a) == r7.stable_rule_id(b)

    # Protected data is rejected at input.
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "BTCUSDT_spot_5m_2017_2025.csv"
        x = pd.DataFrame({
            "time": ["2017-08-20T00:00:00Z", "2025-12-31T23:55:00Z", "2026-01-01T00:00:00Z"],
            "open": [1,1,1], "high": [1,1,1], "low": [1,1,1], "close": [1,1,1]
        })
        x.to_csv(p, index=False)
        try:
            r7.load_exact(p)
            raise AssertionError("protected row was not rejected")
        except RuntimeError as exc:
            assert "protected 2026 row" in str(exc)

    print('{"status":"PASS","tests":9,"protected_market_data_access":false}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
