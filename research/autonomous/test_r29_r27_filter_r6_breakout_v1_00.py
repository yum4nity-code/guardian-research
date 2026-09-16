#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

import r29_r27_filter_r6_breakout_v1_00 as m


def make_m5(start: str, days: int = 25, bars_per_day: int = 60) -> pd.DataFrame:
    rows = []
    t0 = pd.Timestamp(start, tz="UTC")
    price = 100.0
    for d in range(days):
        day0 = t0 + pd.Timedelta(days=d)
        for i in range(bars_per_day):
            t = day0 + pd.Timedelta(minutes=5 * i)
            # deterministic, changing daily scale to create percentile structure
            step = (0.0001 + d * 0.000002) * (1 if i % 2 == 0 else -1)
            price *= 1.0 + step
            rows.append(
                {
                    "time": t,
                    "open": price,
                    "high": price * 1.0001,
                    "low": price * 0.9999,
                    "close": price,
                }
            )
    return pd.DataFrame(rows)


def test_frozen_candidate_definitions():
    assert m.CANDIDATES["R6B-347"] == {
        "candidate_id": "R6B-347",
        "lookback_bars": 96,
        "buffer_atr": 0.10,
        "horizon_bars": 96,
        "session": "UTC00_08",
        "session_start": 0,
        "session_end": 8,
        "direction": 1,
        "direction_name": "LONG",
        "role": "PRIMARY",
    }
    assert m.CANDIDATES["R6B-307"]["lookback_bars"] == 96
    assert m.CANDIDATES["R6B-307"]["buffer_atr"] == 0.0
    assert m.CANDIDATES["R6B-307"]["horizon_bars"] == 48
    assert m.CANDIDATES["R6B-307"]["session_start"] == 0
    assert m.CANDIDATES["R6B-307"]["session_end"] == 8
    assert m.CANDIDATES["R6B-307"]["direction"] == 1


def test_active_state_excludes_current_bar_return():
    df = make_m5("2024-01-01", days=25, bars_per_day=60)
    state1 = m.active_bottom10_state(df)

    # Modify only current bar close at a late index. Since stdev48 at i uses
    # returns i-48:i, the state at i must remain unchanged.
    i = len(df) - 10
    assert state1[i] is not None
    df2 = df.copy()
    df2.loc[i, "close"] *= 1.50
    state2 = m.active_bottom10_state(df2)
    assert state2[i] == state1[i]


def test_gap_makes_state_unavailable_until_48_contiguous_returns_rebuild():
    df = make_m5("2024-01-01", days=25, bars_per_day=60)
    # Remove one bar late enough that prior-day history exists.
    cut = len(df) - 100
    df = df.drop(index=cut).reset_index(drop=True)
    state = m.active_bottom10_state(df)

    # Bar immediately after the gap cannot have a valid contiguous 48-return window.
    gap_next = cut
    assert state[gap_next] is None
    # 49+ bars later the rolling window can recover.
    assert any(x is not None for x in state[gap_next + 49 :])


def fake_trade(idx: int, state: str, net_e1: float, net_stress: float, day: str) -> dict:
    return {
        "signal_index": idx,
        "signal_time": f"{day}T01:00:00+00:00",
        "entry_time": f"{day}T01:05:00+00:00",
        "exit_time": f"{day}T02:00:00+00:00",
        "entry_open": 100.0,
        "exit_open": 101.0,
        "direction": 1,
        "r29_state": state,
        "r29_stdev48": 0.1 if state != "STATE_UNAVAILABLE" else None,
        "r29_q10": 0.2 if state != "STATE_UNAVAILABLE" else None,
        "r29_trailing_distribution_n": 100 if state != "STATE_UNAVAILABLE" else None,
        "profiles": {
            "E1": {
                "gross": net_e1,
                "spread": 0.0,
                "slippage": 0.0,
                "commission": 0.0,
                "net": net_e1,
                "entry_model": 100.0,
                "exit_model": 101.0,
            },
            "STRESS": {
                "gross": net_stress,
                "spread": 0.0,
                "slippage": 0.0,
                "commission": 0.0,
                "net": net_stress,
                "entry_model": 100.0,
                "exit_model": 101.0,
            },
        },
    }


def test_interaction_difference_ignores_unavailable():
    trades = [
        fake_trade(0, "ACTIVE_BOTTOM10", -2.0, -3.0, "2024-01-01"),
        fake_trade(1, "NOT_BOTTOM10", 2.0, 1.0, "2024-01-02"),
        fake_trade(2, "STATE_UNAVAILABLE", 1000.0, 1000.0, "2024-01-03"),
    ]
    assert m.interaction_difference(trades, "E1") == -4.0
    assert m.interaction_difference(trades, "STRESS") == -4.0


def test_day_block_bootstrap_is_deterministic():
    trades = []
    for i in range(20):
        state = "ACTIVE_BOTTOM10" if i % 4 == 0 else "NOT_BOTTOM10"
        net = -2.0 if state == "ACTIVE_BOTTOM10" else 1.0
        trades.append(
            fake_trade(i, state, net, net - 0.5, f"2024-01-{i+1:02d}")
        )
    a = m.day_block_bootstrap_difference(trades, "E1", "R6B-347")
    b = m.day_block_bootstrap_difference(trades, "E1", "R6B-347")
    assert a == b
    assert a["valid_resamples"] >= 4750
    assert a["observed_difference"] < 0
    assert a["p975"] < 0


def make_candidate_result(
    diff24=-2.0,
    diff25=-2.0,
    pooled_e1=-2.0,
    pooled_stress=-1.0,
    active=20,
    availability=1.0,
    upper=-0.1,
):
    def block(diff, profile="E1"):
        return {
            "total_trades": 50,
            "state_available_trades": int(50 * availability),
            "state_unavailable_trades": 50 - int(50 * availability),
            "state_availability_fraction": availability,
            "active_bottom10_trades": active // 2,
            "active_bottom10_fraction_of_available": 0.2,
            "interaction_difference": diff,
            "active_bottom10": {"expectancy": -1.0},
            "not_bottom10": {"expectancy": 1.0},
            "all_original": {"expectancy": 0.5},
            "hypothetical_veto_retained": {"expectancy": 1.0},
        }
    return {
        "years": {
            "2024": {"E1": block(diff24), "STRESS": block(-1.0, "STRESS")},
            "2025": {"E1": block(diff25), "STRESS": block(-1.0, "STRESS")},
        },
        "pooled": {
            "E1": {**block(pooled_e1), "active_bottom10_trades": active},
            "STRESS": {**block(pooled_stress, "STRESS"), "active_bottom10_trades": active},
        },
        "bootstrap_pooled_e1": {
            "resamples": 5000,
            "valid_resamples": 5000,
            "observed_difference": pooled_e1,
            "p025": -3.0,
            "p975": upper,
            "reason": None,
        },
    }


def test_filter_lead_gate_requires_every_condition():
    results = {
        "R6B-347": make_candidate_result(),
        "R6B-307": make_candidate_result(),
    }
    assert m.filter_lead_gate(results)["status"] == "FILTER_LEAD"

    bad = {
        "R6B-347": make_candidate_result(diff25=0.1),
        "R6B-307": make_candidate_result(),
    }
    assert m.filter_lead_gate(bad)["status"] == "NO_FILTER_LEAD"

    bad2 = {
        "R6B-347": make_candidate_result(upper=0.01),
        "R6B-307": make_candidate_result(),
    }
    assert m.filter_lead_gate(bad2)["status"] == "NO_FILTER_LEAD"

    bad3 = {
        "R6B-347": make_candidate_result(),
        "R6B-307": make_candidate_result(active=10),
    }
    assert m.filter_lead_gate(bad3)["status"] == "NO_FILTER_LEAD"


def test_classify_ledger_uses_original_signal_index():
    state = [
        None,
        {"active_bottom10": True, "stdev48": 0.1, "q10": 0.2, "trailing_distribution_n": 10},
        {"active_bottom10": False, "stdev48": 0.3, "q10": 0.2, "trailing_distribution_n": 10},
    ]
    ledger = [
        {"signal_index": 1, "profiles": {}},
        {"signal_index": 2, "profiles": {}},
        {"signal_index": 0, "profiles": {}},
    ]
    out = m.classify_ledger(ledger, state)
    assert [x["r29_state"] for x in out] == [
        "ACTIVE_BOTTOM10",
        "NOT_BOTTOM10",
        "STATE_UNAVAILABLE",
    ]


def main():
    test_frozen_candidate_definitions()
    test_active_state_excludes_current_bar_return()
    test_gap_makes_state_unavailable_until_48_contiguous_returns_rebuild()
    test_interaction_difference_ignores_unavailable()
    test_day_block_bootstrap_is_deterministic()
    test_filter_lead_gate_requires_every_condition()
    test_classify_ledger_uses_original_signal_index()
    print("PASS: R29 R27-filter × R6 interaction tests")


if __name__ == "__main__":
    main()
