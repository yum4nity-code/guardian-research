#!/usr/bin/env python3
"""Deterministic no-market-data preflight for R5 economic robustness."""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

import r5_pre_oos_economic_robustness_v1_00 as m


def frame(start: str, periods: int, freq: str) -> pd.DataFrame:
    t = pd.date_range(start, periods=periods, freq=freq, tz='UTC')
    x = np.arange(periods, dtype=float) + 2000.0
    return pd.DataFrame({'time': t, 'open': x, 'high': x + 1, 'low': x - 1, 'close': x + 0.25, 'volume': 100.0})


def test_cost_accounting() -> None:
    for d in (-1, 1):
        for profile in m.PROFILES:
            x = m.cost(2000.0, 2002.0, d, profile)
            expected = d * (x['exit_model'] - x['entry_model']) - x['commission']
            assert math.isclose(x['net'], expected, rel_tol=1e-12, abs_tol=1e-12)
            assert x['spread'] >= 0 and x['slippage'] >= 0 and x['commission'] >= 0


def test_first_available_and_overlap() -> None:
    src = frame('2025-01-02 00:00:00', 12, '5min')
    raw = frame('2025-01-02 00:00:00', 70, '1min')
    signals = np.zeros(len(src), dtype=bool)
    signals[[0, 1, 2, 5]] = True
    ledger, counts = m.replay(src, raw, signals, horizon=2, direction=1, tf_seconds=300)
    assert ledger
    first = ledger[0]
    assert first['entry_time'] == pd.Timestamp('2025-01-02 00:05:00', tz='UTC').isoformat()
    assert first['exit_time'] == pd.Timestamp('2025-01-02 00:15:00', tz='UTC').isoformat()
    assert counts['ignored_overlap_signals'] >= 2
    for a, b in zip(ledger, ledger[1:]):
        assert pd.Timestamp(a['exit_time']) <= pd.Timestamp(b['entry_time'])


def test_year_boundary_purge() -> None:
    src = frame('2024-12-31 23:40:00', 10, '5min')
    raw = frame('2024-12-31 23:40:00', 50, '1min')
    signals = np.zeros(len(src), dtype=bool)
    signals[2] = True  # signal 23:50; h=3 exit-source open lies in 2025
    ledger, counts = m.replay(src, raw, signals, horizon=3, direction=1, tf_seconds=300)
    assert len(ledger) == 0
    assert counts['excluded_year_boundary_signals'] == 1


def test_gate_exactness() -> None:
    positive = {'trades': 100, 'net': 1.0, 'ex_best_positive_net': 0.5}
    metrics = {p: {q: dict(positive) for q in m.PROFILES} for p in m.PERIODS}
    metrics['2025_H1']['E1']['trades'] = 40
    metrics['2025_H2']['E1']['trades'] = 40
    status, reasons = m.decide(metrics)
    assert status == 'PASS' and not reasons
    metrics['2025_H2']['E1']['net'] = 0.0
    status, reasons = m.decide(metrics)
    assert status == 'FAIL' and 'E1_NET_NONPOSITIVE_2025_H2' in reasons


def main() -> int:
    test_cost_accounting()
    test_first_available_and_overlap()
    test_year_boundary_purge()
    test_gate_exactness()
    print('PASS: deterministic R5 economic robustness preflight')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
