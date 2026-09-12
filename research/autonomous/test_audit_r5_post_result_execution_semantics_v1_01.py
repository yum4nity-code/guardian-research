#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
import pandas as pd

import audit_r5_post_result_execution_semantics_v1_01 as audit


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
    assert abs(ret[0] - 5.0) < 1e-12


def test_timestamp_resolution_independence():
    raw = frame(
        pd.date_range('2025-01-02 10:00:00+00:00', periods=21, freq='1min'),
        np.arange(21, dtype=float) + 100.0,
    )
    src = raw.iloc[[0, 5, 10, 15, 20]].reset_index(drop=True)
    atr = pd.Series(np.ones(len(src)))
    expected = audit.raw_m1_reference_return(src, atr, raw, horizon=1, direction=1, tf_seconds=300)
    raw_us = raw.copy(); src_us = src.copy()
    raw_us['time'] = pd.Series(raw_us['time'].array.as_unit('us'))
    src_us['time'] = pd.Series(src_us['time'].array.as_unit('us'))
    actual = audit.raw_m1_reference_return(src_us, atr, raw_us, horizon=1, direction=1, tf_seconds=300)
    assert np.allclose(expected, actual, equal_nan=True)


def test_news_clean_next_row_drift_is_detected():
    raw = frame(
        pd.date_range('2025-01-02 10:00:00+00:00', periods=6, freq='1min'),
        [100, 101, 102, 103, 104, 105],
    )
    clean = raw.iloc[[0, 2, 3, 4, 5]].reset_index(drop=True)
    atr = pd.Series(np.ones(len(clean)))
    src = audit.source_row_return(clean, atr, horizon=1, direction=1)
    replay = audit.raw_m1_reference_return(clean, atr, raw, horizon=1, direction=1, tf_seconds=60)
    selected = np.ones(len(clean), dtype=bool)
    n, den, share = audit.mismatch_share(selected, src, replay)
    assert n >= 1 and den >= 1 and share > 0
    assert abs(src[0] - 1.0) < 1e-12
    assert abs(replay[0] - 2.0) < 1e-12


def test_calendar_boundary_is_purged():
    raw = frame(
        ['2025-12-31 23:58:00+00:00', '2025-12-31 23:59:00+00:00', '2026-01-01 00:00:00+00:00'],
        [100, 101, 102],
    )
    atr = pd.Series(np.ones(len(raw)))
    ret = audit.raw_m1_reference_return(raw.copy(), atr, raw, horizon=1, direction=1, tf_seconds=60)
    assert np.isnan(ret[0]) and np.isnan(ret[1])


def test_materiality_constants_are_unchanged():
    assert audit.EDGE_DRIFT_LIMIT == 0.005
    assert audit.SELECTED_MISMATCH_LIMIT == 0.01
    assert audit.EXPECTED_R5_SHA256 == '81dd16fabf001025c4dc144035d538fa46fab2fc768ba237610e027af1c7d34e'


def main():
    tests = [
        test_raw_m1_aligned_m5_reference_matches_expected,
        test_timestamp_resolution_independence,
        test_news_clean_next_row_drift_is_detected,
        test_calendar_boundary_is_purged,
        test_materiality_constants_are_unchanged,
    ]
    for test in tests:
        test()
    print({'status': 'PASS', 'tests': len(tests), 'market_data_access': False, 'scientific_protocol_changed': False})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
