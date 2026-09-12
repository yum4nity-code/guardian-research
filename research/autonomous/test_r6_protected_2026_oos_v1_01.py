#!/usr/bin/env python3
from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import r6_protected_2026_oos_v1_00 as oos


def test_preregistration_contract():
    p = Path(__file__).with_name("r6_oos_2026_preregistration_v1.json")
    x = json.loads(p.read_text(encoding="utf-8"))
    assert x["authorized_by_human"] is True
    assert x["retuning_allowed"] is False
    assert x["frozen_survivor_count"] == 12
    assert x["oos_window"]["start"] == "2026-01-01T00:00:00Z"
    assert x["oos_window"]["end_exclusive"] == "2027-01-01T00:00:00Z"
    assert x["input_selection"]["ambiguity_policy"] == "fail_closed_if_not_exactly_one_file_per_timeframe"
    g = x["candidate_pass_criteria"]
    assert g["minimum_full_oos_trades"] == 18
    assert g["minimum_each_temporal_half_trades"] == 6
    assert g["bh_fdr_q_lte"] == 0.05


def test_executor_is_frozen():
    src = inspect.getsource(oos)
    required = [
        'if len(survivors) != 12',
        'expected exactly 12 frozen R6 survivors',
        'retuning_allowed',
        'r6.evaluate_year(rule, source, raw, 2026)',
        'r6.bh_qvalues(pvals)',
        'retuning_performed": False',
        'protected_2026_opened": True',
    ]
    for token in required:
        assert token in src, token
    forbidden = ["optimize", "grid_search", "best_params"]
    lowered = src.lower()
    for token in forbidden:
        assert token not in lowered, token


def test_candidate_fingerprint_deterministic():
    rules = [
        {"candidate_id":"A","lookback_bars":12,"buffer_atr":0.1,"horizon_bars":24,"session":"ALL","session_start":None,"session_end":None,"direction_name":"LONG","direction":1},
        {"candidate_id":"B","lookback_bars":24,"buffer_atr":0.2,"horizon_bars":48,"session":"UTC08_16","session_start":8,"session_end":16,"direction_name":"SHORT","direction":-1},
    ]
    a = oos.candidate_fingerprint(rules)
    b = oos.candidate_fingerprint(rules)
    assert a == b and len(a) == 64


def test_input_selection_fail_closed_without_market_reads():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        m5 = root / "xauusd_m5_2026.csv"
        m1 = root / "xauusd_m1_2026.csv"
        m5.write_text("sentinel", encoding="utf-8")
        m1.write_text("sentinel", encoding="utf-8")
        assert oos.select_input(root, "m5") == m5
        assert oos.select_input(root, "m1") == m1

        duplicate = root / "copy_xauusd_m5_2026.csv"
        duplicate.write_text("sentinel", encoding="utf-8")
        try:
            oos.select_input(root, "m5")
        except RuntimeError as exc:
            assert "expected exactly one XAUUSD 2026 m5 CSV" in str(exc)
        else:
            raise AssertionError("duplicate M5 input did not fail closed")

        duplicate.unlink()
        m1.unlink()
        try:
            oos.select_input(root, "m1")
        except RuntimeError as exc:
            assert "expected exactly one XAUUSD 2026 m1 CSV" in str(exc)
        else:
            raise AssertionError("missing M1 input did not fail closed")


def main():
    tests = [
        test_preregistration_contract,
        test_executor_is_frozen,
        test_candidate_fingerprint_deterministic,
        test_input_selection_fail_closed_without_market_reads,
    ]
    for t in tests:
        t()
    print(json.dumps({"status":"PASS","tests":len(tests),"market_data_accessed":False,"protected_2026_opened":False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
