#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import inspect
import math
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ENGINE = HERE / "r14_bitcoin_hourly_negative_shock_replication_v1_00.py"

spec = importlib.util.spec_from_file_location("r14", ENGINE)
m = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)

def ok(cond, msg):
    if not cond:
        raise AssertionError(msg)

def make_h1(n=40, start="2022-01-01T00:00:00Z", base=100.0):
    t = pd.date_range(start, periods=n, freq="1h", tz="UTC")
    close = np.full(n, base, dtype=float)
    open_ = np.full(n, base, dtype=float)
    return pd.DataFrame({"time":t, "open":open_, "high":open_, "low":open_, "close":close})

def test_rule_grid():
    r = m.rules()
    ok(len(r) == 48, "must preserve 48 published negative-shock cells")
    ok(len({m.cid(x) for x in r}) == 48, "candidate IDs must be unique")
    ok(m.FILTERS == [0.005,0.010,0.015,0.025,0.035,0.050], "filter grid changed")
    ok(m.HOLDS == [1,2,3,4,5,6,12,24], "hold grid changed")

def test_strict_negative_shock_and_event_return():
    d = make_h1(10)
    d.loc[1, "close"] = 100.0
    d.loc[2, "close"] = 100.0 * math.exp(-0.010)
    d.loc[3, "close"] = d.loc[2, "close"] * math.exp(0.02)
    exact_ret = abs(math.log(float(d.loc[2, "close"]) / float(d.loc[1, "close"])))
    ev = m.paper_event_returns(d, exact_ret, 1, pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2022-01-02", tz="UTC"))
    ok(len(ev) == 0, "strict threshold equality must not trigger")
    d.loc[2, "close"] = 100.0 * math.exp(-0.0101)
    d.loc[3, "close"] = d.loc[2, "close"] * math.exp(0.02)
    ev = m.paper_event_returns(d, 0.010, 1, pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2022-01-02", tz="UTC"))
    ok(len(ev) == 1, f"expected one event, got {len(ev)}")
    ok(abs(ev[0]["acr"] - 0.02) < 1e-12, "paper-style ACR formula wrong")

def test_overlap_allowed_in_replication():
    d = make_h1(12)
    d.loc[1, "close"] = 100.0
    d.loc[2, "close"] = 98.0
    d.loc[3, "close"] = 96.0
    d.loc[4:, "close"] = 97.0
    ev = m.paper_event_returns(d, 0.005, 3, pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2022-01-02", tz="UTC"))
    times = [x["decision_time"] for x in ev]
    ok(d.loc[2, "time"] in times and d.loc[3, "time"] in times, "replication must allow overlapping event-study observations")

def test_stage_boundary_fail_closed():
    d = make_h1(8)
    d.loc[4, "close"] = 90.0
    end = d.loc[6, "time"]
    ev = m.paper_event_returns(d, 0.005, 3, d.loc[0, "time"], end)
    ok(len(ev) == 0, "event whose exit crosses stage end must be rejected")

def test_executable_next_open_and_one_position():
    d = make_h1(20)
    d["open"] = np.arange(100.0, 120.0)
    d["close"] = 100.0
    d.loc[1, "close"] = 100.0
    d.loc[2, "close"] = 98.0
    d.loc[3, "close"] = 96.0
    trades = m.executable_trades(d, 0.005, 3, d.loc[0, "time"], d.loc[15, "time"])
    ok(len(trades) >= 1, "expected executable trade")
    first = trades[0]
    ok(first["entry_time"] == d.loc[3, "time"], "entry must be next H1 open after completed shock bar")
    ok(first["exit_time"] == d.loc[6, "time"], "exit must be hold-hours after entry")
    expected = d.loc[6, "open"] / d.loc[3, "open"] - 1.0
    ok(abs(first["gross"] - expected) < 1e-12, "executable gross return wrong")
    ok(abs(first["E1"] - (expected - 0.001)) < 1e-12, "E1 cost wrong")
    ok(abs(first["STRESS"] - (expected - 0.002)) < 1e-12, "STRESS cost wrong")
    ok(all(t["entry_time"] >= first["exit_time"] for t in trades[1:]), "overlap not blocked")

def test_complete_h1_only():
    t = pd.date_range("2022-01-01", periods=24, freq="5min", tz="UTC")
    m5 = pd.DataFrame({"time":t, "open":1.0, "high":1.0, "low":1.0, "close":1.0})
    m5 = m5.drop(index=15).reset_index(drop=True)
    h = m.to_h1(m5)
    ok(len(h) == 1, "incomplete H1 hour must be rejected")

def test_protected_filename_guard_precedes_hash():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "BTCUSDT_spot_5m_2026.csv"
        p.write_text("time,open,high,low,close\n", encoding="utf-8")
        try:
            m.load_m5(p)
        except RuntimeError as e:
            ok("protected filename forbidden" in str(e), "wrong 2026 filename guard")
        else:
            raise AssertionError("2026 filename was not rejected")

def test_stage_separation_source():
    paper_src = inspect.getsource(m.paper_event_returns)
    exec_src = inspect.getsource(m.executable_trades)
    ok("E1" not in paper_src and "STRESS" not in paper_src, "cost gate leaked into paper replication")
    ok("E1" in exec_src and "STRESS" in exec_src, "economic costs missing from executable stage")
    ok(m.REPL1 == pd.Timestamp("2021-07-01", tz="UTC"), "replication boundary changed")
    ok(m.CONF1 == pd.Timestamp("2025-01-01", tz="UTC"), "confirmation boundary changed")
    ok(m.PRE1 == pd.Timestamp("2026-01-01", tz="UTC"), "pre-OOS boundary changed")

def test_bh():
    q = m.bh([0.001, 0.01, 0.2])
    ok(len(q) == 3, "BH output size wrong")
    ok(all(0 <= x <= 1 for x in q), "BH q outside [0,1]")

def main():
    tests = [test_rule_grid, test_strict_negative_shock_and_event_return, test_overlap_allowed_in_replication, test_stage_boundary_fail_closed, test_executable_next_open_and_one_position, test_complete_h1_only, test_protected_filename_guard_precedes_hash, test_stage_separation_source, test_bh]
    for fn in tests:
        fn()
    print('{"status":"PASS","tests":"R14 deterministic methodology/code preflight","definitions":48}')

if __name__ == "__main__":
    main()
