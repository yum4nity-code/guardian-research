#!/usr/bin/env python3
from __future__ import annotations

import inspect
import json
from pathlib import Path

import numpy as np
import pandas as pd

import top2_xau_long_history_backtest_v1_00 as bt
import top2_xau_long_history_market_export_v1_00 as exp


def test_frozen_selection_and_window():
    here = Path(__file__).parent
    p = json.loads((here / "top2_xau_long_history_preregistration_v1.json").read_text(encoding="utf-8"))
    assert p["window"]["start"] == "2017-01-01T00:00:00Z"
    assert p["window"]["end_exclusive"] == "2026-08-01T00:00:00Z"
    assert p["execution"]["parameter_retuning"] is False
    assert p["execution"]["sizing_optimization"] is False
    got = {x["candidate_id"]: x for x in p["candidates"]}
    assert set(got) == {"R6B-347", "R6B-307"}
    assert got["R6B-347"]["lookback_bars"] == 96
    assert got["R6B-347"]["buffer_atr"] == 0.1
    assert got["R6B-347"]["horizon_bars"] == 96
    assert got["R6B-307"]["lookback_bars"] == 96
    assert got["R6B-307"]["buffer_atr"] == 0.0
    assert got["R6B-307"]["horizon_bars"] == 48
    assert got["R6B-347"]["session_start"] == got["R6B-307"]["session_start"] == 0
    assert got["R6B-347"]["session_end"] == got["R6B-307"]["session_end"] == 8
    assert got["R6B-347"]["direction"] == got["R6B-307"]["direction"] == 1


def test_no_retuning_or_live_action_in_code():
    src = inspect.getsource(bt)
    esrc = inspect.getsource(exp)
    lower = (src + esrc).lower()
    for forbidden in ("grid_search", "best_params", "optimize(", "order_send(", "trade_action_deal"):
        assert forbidden not in lower
    assert "copy_rates_range" in esrc
    assert "reconcile(exp_2425, can_2425" in esrc
    assert "reconcile(exp_2026, can_2026" in esrc
    assert '"HYBRID_CANONICAL"' in src
    assert "compare_known(yearly, published_by_id[cid], cid)" in src
    assert '"live_deployment_authorized": False' in src


def test_replay_accepts_old_history_and_fails_closed_at_window_end():
    start = pd.Timestamp("2018-01-01T00:00:00Z")
    end = pd.Timestamp("2018-01-02T00:00:00Z")
    times = pd.date_range(start, periods=288, freq="5min")
    source = pd.DataFrame({
        "time": times,
        "open": np.arange(len(times), dtype=float) + 1000,
        "high": np.arange(len(times), dtype=float) + 1001,
        "low": np.arange(len(times), dtype=float) + 999,
        "close": np.arange(len(times), dtype=float) + 1000.5,
    })
    rtimes = pd.date_range(start, periods=1440, freq="1min")
    raw = pd.DataFrame({
        "time": rtimes,
        "open": np.arange(len(rtimes), dtype=float) / 100 + 1000,
        "high": 0.0,
        "low": 0.0,
        "close": 0.0,
    })
    signals = np.zeros(len(source), dtype=bool)
    signals[20] = True
    signals[-2] = True
    ledger, accounting = bt.replay_window(source, raw, signals, 12, 1, start, end)
    assert len(ledger) == 1
    assert accounting["executable_trades"] == 1
    assert accounting["excluded_boundary_signals"] >= 1


def test_mask_bar_overlap_semantics():
    times = pd.to_datetime(["2020-01-01T00:00:00Z", "2020-01-01T00:05:00Z", "2020-01-01T00:10:00Z"], utc=True)
    source = pd.DataFrame({"time": times, "open": [1,1,1], "high": [1,1,1], "low": [1,1,1], "close": [1,1,1]})
    target = int(pd.Timestamp("2020-01-01T00:05:00Z").timestamp())
    out = bt.apply_mask(source, [(target + 60, target + 120)])
    assert len(out) == 2
    assert pd.Timestamp("2020-01-01T00:05:00Z") not in set(out.time)


def main() -> int:
    tests = [
        test_frozen_selection_and_window,
        test_no_retuning_or_live_action_in_code,
        test_replay_accepts_old_history_and_fails_closed_at_window_end,
        test_mask_bar_overlap_semantics,
    ]
    for t in tests:
        t()
    print(json.dumps({"status": "PASS", "tests": len(tests), "market_data_accessed": False, "live_action": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
