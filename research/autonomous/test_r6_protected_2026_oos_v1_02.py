#!/usr/bin/env python3
from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import pandas as pd

import r6_protected_2026_oos_v1_01 as oos


def test_preregistration_amendment_is_transport_only():
    here = Path(__file__).parent
    v1 = json.loads((here / "r6_oos_2026_preregistration_v1.json").read_text(encoding="utf-8"))
    v2 = json.loads((here / "r6_oos_2026_preregistration_v2.json").read_text(encoding="utf-8"))
    assert v2["authorized_by_human"] is True
    assert v2["retuning_allowed"] is False
    assert v2["scientific_evaluation_before_amendment"] is False
    assert v2["frozen_survivor_count"] == 12
    assert v2["candidate_pass_criteria"] == v1["candidate_pass_criteria"]
    assert v2["oos_window"]["start"] == "2026-01-01T00:00:00Z"
    assert v2["oos_window"]["split"] == "2026-05-01T00:00:00Z"
    assert v2["oos_window"]["end_exclusive"] == "2026-09-01T00:00:00Z"
    assert v2["inputs"]["news_mask_expected_sha256"] == "8d3eb7dda83376a4bbfd759233465ca6fcd996ef94cc07030369e1d606d2e558"


def test_executor_semantics_are_frozen():
    src = inspect.getsource(oos)
    assert "r5.load_market" not in src
    assert "select_input(" not in src
    assert "r6.evaluate_year(rule, source, raw, 2026)" in src
    assert "source = apply_news_mask(raw_m5, intervals)" in src
    assert 'SPLIT = pd.Timestamp("2026-05-01T00:00:00Z")' in src
    assert '"retuning_performed": False' in src
    assert '"protected_2026_opened": True' in src
    lowered = src.lower()
    for forbidden in ("grid_search", "best_params", "optimize("):
        assert forbidden not in lowered


def test_manifest_validation_is_exact():
    prereg = {
        "inputs": {
            "required_server": "FundedNext-Server 2",
            "required_terminal_data_path": r"D:\MT5_FundedNext",
        }
    }
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "m5_manifest.txt"
        p.write_text(
            "\n".join(
                [
                    "symbol=XAUUSD",
                    "period=M5",
                    "from=2026.01.01 00:00:00",
                    "to_exclusive=2026.09.01 00:00:00",
                    "server=FundedNext-Server 2",
                    r"terminal_data_path=D:\MT5_FundedNext",
                ]
            ),
            encoding="utf-8",
        )
        got = oos.validate_manifest(p, "M5", prereg)
        assert got["period"] == "M5"
        bad = p.read_text(encoding="utf-8").replace("period=M5", "period=M1")
        p.write_text(bad, encoding="utf-8")
        try:
            oos.validate_manifest(p, "M5", prereg)
        except RuntimeError:
            pass
        else:
            raise AssertionError("wrong timeframe manifest did not fail closed")


def test_news_mask_semantics():
    times = pd.to_datetime(
        ["2026-01-02T10:00:00Z", "2026-01-02T10:05:00Z", "2026-01-02T10:10:00Z"],
        utc=True,
    )
    df = pd.DataFrame(
        {
            "time": times,
            "open": [1.0, 1.0, 1.0],
            "high": [1.1, 1.1, 1.1],
            "low": [0.9, 0.9, 0.9],
            "close": [1.0, 1.0, 1.0],
        }
    )
    middle = int(times[1].timestamp())
    old_min = 30000
    # apply_news_mask has a production minimum-length guard; make a sufficiently
    # large synthetic frame while preserving one uniquely masked timestamp.
    repeats = 10001
    big = pd.concat([df] * repeats, ignore_index=True)
    big["time"] = pd.date_range("2026-01-02T00:00:00Z", periods=len(big), freq="5min")
    target = int(big.iloc[100]["time"].timestamp())
    out = oos.apply_news_mask(big, [(target, target)])
    assert len(out) == len(big) - 1
    assert target not in set((out.time.astype("int64") // 1_000_000_000).astype(int).tolist())


def test_candidate_fingerprint_deterministic():
    rules = [
        {
            "candidate_id": "A",
            "lookback_bars": 12,
            "buffer_atr": 0.1,
            "horizon_bars": 24,
            "session": "ALL",
            "session_start": None,
            "session_end": None,
            "direction_name": "LONG",
            "direction": 1,
        }
    ]
    assert oos.candidate_fingerprint(rules) == oos.candidate_fingerprint(rules)
    assert len(oos.candidate_fingerprint(rules)) == 64


def main() -> int:
    tests = [
        test_preregistration_amendment_is_transport_only,
        test_executor_semantics_are_frozen,
        test_manifest_validation_is_exact,
        test_news_mask_semantics,
        test_candidate_fingerprint_deterministic,
    ]
    for test in tests:
        test()
    print(json.dumps({"status": "PASS", "tests": len(tests), "market_data_accessed": False, "scientific_r6_oos_evaluated": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
