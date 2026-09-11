#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
import pandas as pd

import audit_r5_post_result_execution_semantics_v1_00 as audit


def frame(times, opens):
    t = pd.to_datetime(times, utc=True)
    o = np.asarray(opens, dtype=float)
    return pd.DataFrame({'time': t, 'open': o, 'high': o + 0.2, 'low': o - 0.2, 'close': o + 0.1})


def test_raw_m1_aligned_m5_reference_matches_expected():
    raw = frame(
        pd.date_range('2025-01-02 10:00:00+00:00', periods=21, freq='1min'),
        np.arange(21, dtype=float) + 100.0,
    )
    src = raw.iloc[[0, 5, 10, 15, 20]].reset_index(drop=True)
    atr = pd.Series(np.ones(len(src)))
    ret = audit.raw_m1_reference_return(src, atr, raw, horizon=1, direction=1, tf_seconds=300)
    # signal 10:00 closes at 10:05 => entry 105; frozen exit target t+2 = 10:10 => 110
    assert abs(ret[0] - 5.0) < 1e-12


def test_news_clean_next_row_drift_is_detected():
    raw = frame(
        pd.date_range('2025-01-02 10:00:00+00:00', periods=6, freq='1min'),
        [100, 101, 102, 103, 104, 105],
    )
    # 10:01 is removed from the clean source. Frozen source-row entry for 10:00 is 10:02,
    # while first executable raw-M1 entry after the 10:00 bar closes is 10:01.
    clean = raw.iloc[[0, 2, 3, 4, 5]].reset_index(drop=True)
    atr = pd.Series(np.ones(len(clean)))
    src = audit.source_row_return(clean, atr, horizon=1, direction=1)
    replay = audit.raw_m1_reference_return(clean, atr, raw, horizon=1, direction=1, tf_seconds=60)
    selected = np.ones(len(clean), dtype=bool)
    n, den, share = audit.mismatch_share(selected, src, replay)
    assert n >= 1
    assert den >= 1
    assert share > 0
    assert abs(src[0] - 1.0) < 1e-12  # clean 10:02 -> clean 10:03
    assert abs(replay[0] - 2.0) < 1e-12  # raw 10:01 -> target 10:03


def test_calendar_boundary_is_purged():
    raw = frame(
        ['2025-12-31 23:58:00+00:00', '2025-12-31 23:59:00+00:00', '2026-01-01 00:00:00+00:00'],
        [100, 101, 102],
    )
    src = raw.copy()
    atr = pd.Series(np.ones(len(src)))
    ret = audit.raw_m1_reference_return(src, atr, raw, horizon=1, direction=1, tf_seconds=60)
    assert np.isnan(ret[0])
    assert np.isnan(ret[1])


def test_materiality_constants_are_reject_only():
    assert audit.EDGE_DRIFT_LIMIT == 0.005
    assert audit.SELECTED_MISMATCH_LIMIT == 0.01
    assert audit.EXPECTED_R5_SHA256 == '81dd16fabf001025c4dc144035d538fa46fab2fc768ba237610e027af1c7d34e'


def main():
    tests = [
        test_raw_m1_aligned_m5_reference_matches_expected,
        test_news_clean_next_row_drift_is_detected,
        test_calendar_boundary_is_purged,
        test_materiality_constants_are_reject_only,
    ]
    for t in tests:
        t()
    print({'status': 'PASS', 'tests': len(tests), 'market_data_access': False})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
