#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import r7_pre_oos_economic_robustness_v1_00 as econ


def synthetic_market() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    t = pd.date_range("2025-01-01", periods=20, freq="15min", tz="UTC")
    o = np.arange(100.0, 120.0)
    df = pd.DataFrame({"time": t, "open": o, "high": o + 1, "low": o - 1, "close": o + 0.5})
    ft = pd.DataFrame({"ret1": np.ones(len(df))}, index=df.index)
    atr = pd.Series(np.ones(len(df)), index=df.index)
    return df, ft, atr


def test_nonoverlap_and_costs() -> None:
    df, ft, atr = synthetic_market()
    rule = {
        "candidate_id": "TEST",
        "dataset": "TEST.csv",
        "timeframe": "M15",
        "feature": "ret1",
        "operator": "gt",
        "quantile": 0.7,
        "cutpoint": 0.0,
        "horizon_bars": 3,
        "direction": 1,
        "hour_start": None,
        "hour_width": None,
        "execution": "signal_after_bar_close_entry_next_open_exit_open_after_h_bars",
    }
    trades, accounting = econ.extract_nonoverlap_trades(df, ft, atr, rule)
    assert len(trades) > 0
    assert accounting["ignored_overlap"] > 0
    assert (trades.entry_time.iloc[1:].reset_index(drop=True) >= trades.exit_time.iloc[:-1].reset_index(drop=True)).all()
    expected_gross = trades.iloc[0].exit / trades.iloc[0].entry - 1.0
    assert abs(trades.iloc[0].gross_return - expected_gross) < 1e-12
    assert abs(trades.iloc[0].net_E1 - (expected_gross - 0.0010)) < 1e-12
    assert abs(trades.iloc[0].net_STRESS - (expected_gross - 0.0020)) < 1e-12


def test_year_boundary_fails_closed() -> None:
    t = pd.date_range("2025-12-31 22:00", periods=12, freq="15min", tz="UTC")
    o = np.arange(100.0, 112.0)
    df = pd.DataFrame({"time": t, "open": o, "high": o + 1, "low": o - 1, "close": o + 0.5})
    ft = pd.DataFrame({"ret1": np.ones(len(df))}, index=df.index)
    atr = pd.Series(np.ones(len(df)), index=df.index)
    rule = {
        "candidate_id": "BOUNDARY",
        "dataset": "TEST.csv",
        "timeframe": "M15",
        "feature": "ret1",
        "operator": "gt",
        "quantile": 0.7,
        "cutpoint": 0.0,
        "horizon_bars": 4,
        "direction": 1,
        "hour_start": None,
        "hour_width": None,
        "execution": "signal_after_bar_close_entry_next_open_exit_open_after_h_bars",
    }
    try:
        econ.extract_nonoverlap_trades(df, ft, atr, rule)
    except RuntimeError as exc:
        assert "protected" in str(exc).lower()
    else:
        raise AssertionError("protected 2026 path should fail closed")


def test_drawdown_includes_zero_origin() -> None:
    s = pd.Series([-0.10, 0.02, 0.01])
    assert econ.max_drawdown(s) <= -0.10 + 1e-12


def test_atomic_json_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.json"
        econ.atomic_json(p, {"ok": True})
        assert json.loads(p.read_text(encoding="utf-8")) == {"ok": True}


def main() -> int:
    test_nonoverlap_and_costs()
    test_year_boundary_fails_closed()
    test_drawdown_includes_zero_origin()
    test_atomic_json_roundtrip()
    print("PASS: R7 pre-OOS economic robustness deterministic regression tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
