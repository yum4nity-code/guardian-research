#!/usr/bin/env python3
from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import pandas as pd

import r6_protected_2026_oos_v1_02 as oos


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
    base_src = inspect.getsource(oos.base)
    wrapper_src = inspect.getsource(oos)
    assert "r5.load_market" not in base_src
    assert "select_input(" not in base_src
    assert "r6.evaluate_year(rule, source, raw, 2026)" in base_src
    assert "source = apply_news_mask(raw_m5, intervals)" in base_src
    assert 'SPLIT = pd.Timestamp("2026-05-01T00:00:00Z")' in base_src
    assert '"retuning_performed": False' in base_src
    assert '"protected_2026_opened": True' in base_src
    assert "base.apply_news_mask = apply_news_mask" in wrapper_src
    assert "Timestamp(v).value // 1_000_000_000" in wrapper_src
    lowered = (base_src + wrapper_src).lower()
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
        got = oos.base.validate_manifest(p, "M5", prereg)
        assert got["period"] == "M5"
        p.write_text(p.read_text(encoding="utf-8").replace("period=M5", "period=M1"), encoding="utf-8")
        try:
            oos.base.validate_manifest(p, "M5", prereg)
        except RuntimeError:
            pass
        else:
            raise AssertionError("wrong timeframe manifest did not fail closed")


def test_news_mask_semantics_resolution_safe():
    n = 30003
    times = pd.date_range("2026-01-02T00:00:00Z", periods=n, freq="5min")
    big = pd.DataFrame(
        {
            "time": times,
            "open": [1.0] * n,
            "high": [1.1] * n,
            "low": [0.9] * n,
            "close": [1.0] * n,
        }
    )
    target_ts = pd.Timestamp(big.iloc[100]["time"])
    target = int(target_ts.value // 1_000_000_000)
    out = oos.apply_news_mask(big, [(target, target)])
    assert len(out) == len(big) - 1
    got = set(oos.epoch_seconds(out.time).tolist())
    assert target not in got

    # Explicitly exercise different datetime storage resolutions when supported.
    naive = pd.Series(pd.date_range("2026-01-02", periods=3, freq="5min", tz="UTC"))
    expected = [int(pd.Timestamp(v).value // 1_000_000_000) for v in naive]
    assert oos.epoch_seconds(naive).tolist() == expected


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
    assert oos.base.candidate_fingerprint(rules) == oos.base.candidate_fingerprint(rules)
    assert len(oos.base.candidate_fingerprint(rules)) == 64


def main() -> int:
    tests = [
        test_preregistration_amendment_is_transport_only,
        test_executor_semantics_are_frozen,
        test_manifest_validation_is_exact,
        test_news_mask_semantics_resolution_safe,
        test_candidate_fingerprint_deterministic,
    ]
    for test in tests:
        test()
    print(json.dumps({"status": "PASS", "tests": len(tests), "market_data_accessed": False, "scientific_r6_oos_evaluated": False, "repair": "datetime_epoch_resolution_only"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
