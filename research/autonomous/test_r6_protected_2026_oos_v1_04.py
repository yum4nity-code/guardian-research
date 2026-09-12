#!/usr/bin/env python3
from __future__ import annotations

import inspect
import json
from pathlib import Path

import numpy as np
import pandas as pd

import r6_protected_2026_oos_v1_03 as oos


def test_repair_addendum_is_mechanical_only():
    here = Path(__file__).parent
    v2 = json.loads((here / "r6_oos_2026_preregistration_v2.json").read_text(encoding="utf-8"))
    v3 = json.loads((here / "r6_oos_2026_execution_repair_addendum_v3.json").read_text(encoding="utf-8"))
    assert v3["authorized_by_human"] is True
    assert v3["repair_only"] is True
    assert v3["r4_scientific_result_valid"] is False
    assert v3["r4_outcome_trades_evaluated"] == 0
    assert v3["r4_signal_counts_exposed"] is True
    assert v3["retuning_allowed"] is False
    assert v3["candidate_changes_allowed"] is False
    assert v3["gate_changes_allowed"] is False
    assert v3["window_changes_allowed"] is False
    assert v3["frozen_candidate_count"] == v2["frozen_survivor_count"] == 12
    assert v3["frozen_window"]["start"] == v2["oos_window"]["start"]
    assert v3["frozen_window"]["split"] == v2["oos_window"]["split"]
    assert v3["frozen_window"]["end_exclusive"] == v2["oos_window"]["end_exclusive"]


def test_authorized_replay_has_no_pre_oos_year_guard():
    src = inspect.getsource(oos.authorized_replay)
    assert "signal_year not in (2024, 2025)" not in src
    assert "PROTECTED.value" not in src
    assert "END_NS" in src
    assert "excluded_oos_boundary_signals" in src
    assert oos.base.r6.evaluate_year is oos.evaluate_year_authorized


def test_synthetic_2026_signal_executes():
    source_times = pd.date_range("2026-01-02T00:00:00Z", periods=12, freq="5min")
    source = pd.DataFrame(
        {
            "time": source_times,
            "open": np.linspace(100.0, 101.1, len(source_times)),
            "high": np.linspace(100.2, 101.3, len(source_times)),
            "low": np.linspace(99.8, 100.9, len(source_times)),
            "close": np.linspace(100.1, 101.2, len(source_times)),
        }
    )
    raw_times = pd.date_range("2026-01-02T00:00:00Z", periods=61, freq="1min")
    raw = pd.DataFrame(
        {
            "time": raw_times,
            "open": np.linspace(100.0, 101.0, len(raw_times)),
            "high": np.linspace(100.1, 101.1, len(raw_times)),
            "low": np.linspace(99.9, 100.9, len(raw_times)),
            "close": np.linspace(100.0, 101.0, len(raw_times)),
        }
    )
    signals = np.zeros(len(source), dtype=bool)
    signals[1] = True
    ledger, counts = oos.authorized_replay(source, raw, signals, horizon=2, direction=1, tf_seconds=300)
    assert counts["signals_total"] == 1
    assert counts["executable_trades"] == 1
    assert counts["excluded_oos_boundary_signals"] == 0
    assert len(ledger) == 1
    assert pd.Timestamp(ledger[0]["entry_time"]).year == 2026
    assert pd.Timestamp(ledger[0]["exit_time"]).year == 2026


def test_true_window_boundary_is_rejected():
    source_times = pd.date_range("2026-08-31T23:00:00Z", periods=12, freq="5min")
    source = pd.DataFrame(
        {
            "time": source_times,
            "open": [100.0] * 12,
            "high": [101.0] * 12,
            "low": [99.0] * 12,
            "close": [100.0] * 12,
        }
    )
    raw_times = pd.date_range("2026-08-31T23:00:00Z", periods=60, freq="1min")
    raw = pd.DataFrame(
        {
            "time": raw_times,
            "open": [100.0] * 60,
            "high": [101.0] * 60,
            "low": [99.0] * 60,
            "close": [100.0] * 60,
        }
    )
    signals = np.zeros(len(source), dtype=bool)
    signals[10] = True
    ledger, counts = oos.authorized_replay(source, raw, signals, horizon=2, direction=1, tf_seconds=300)
    assert len(ledger) == 0
    assert counts["excluded_oos_boundary_signals"] == 1


def test_scientific_contract_still_delegates_to_frozen_r6_logic():
    src = inspect.getsource(oos.evaluate_year_authorized)
    assert "r6.atr14(source)" in src
    assert "r6.breakout_signal(" in src
    assert 'rule["lookback_bars"]' in src
    assert 'rule["buffer_atr"]' in src
    assert 'rule["horizon_bars"]' in src
    assert 'rule["direction"]' in src
    lowered = inspect.getsource(oos).lower()
    for forbidden in ("grid_search", "best_params", "optimize(", "retune"):
        assert forbidden not in lowered.replace("no candidate parameter", "")


def main() -> int:
    tests = [
        test_repair_addendum_is_mechanical_only,
        test_authorized_replay_has_no_pre_oos_year_guard,
        test_synthetic_2026_signal_executes,
        test_true_window_boundary_is_rejected,
        test_scientific_contract_still_delegates_to_frozen_r6_logic,
    ]
    for test in tests:
        test()
    print(json.dumps({
        "status": "PASS",
        "tests": len(tests),
        "market_data_accessed": False,
        "scientific_r6_oos_evaluated": False,
        "repair": "replace_pre_oos_2024_2025_guard_with_authorized_jan_aug_2026_window_guard"
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
