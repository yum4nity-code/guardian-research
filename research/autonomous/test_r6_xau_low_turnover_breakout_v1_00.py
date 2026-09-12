#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import r6_xau_low_turnover_breakout_v1_00 as r6
import r5_pre_oos_economic_robustness_v1_00 as econ


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_grid():
    g = r6.definition_grid()
    check(len(g) == 384, 'grid must contain exactly 384 preregistered candidates')
    check(len({x['candidate_id'] for x in g}) == 384, 'candidate ids must be unique')
    sigs = {(x['lookback_bars'], x['buffer_atr'], x['horizon_bars'], x['session'], x['direction']) for x in g}
    check(len(sigs) == 384, 'candidate definitions must be unique')


def test_prior_bar_only_breakout():
    n = 20
    t = pd.date_range('2024-01-01', periods=n, freq='5min', tz='UTC')
    df = pd.DataFrame({'time': t, 'open': 100.0, 'high': 100.0, 'low': 99.0, 'close': 100.0})
    df.loc[n-1, 'high'] = 200.0
    df.loc[n-1, 'close'] = 101.0
    atr = pd.Series(np.ones(n))
    sig = r6.breakout_signal(df, atr, 12, 0.0, 1, None, None)
    check(bool(sig[-1]), 'current bar high leaked into rolling breakout reference')


def test_sessions():
    t = pd.date_range('2024-01-01', periods=24, freq='1h', tz='UTC')
    df = pd.DataFrame({'time': t})
    check(int(r6.session_mask(df, 0, 8).sum()) == 8, '00-08 mask')
    check(int(r6.session_mask(df, 8, 16).sum()) == 8, '08-16 mask')
    check(int(r6.session_mask(df, 16, 24).sum()) == 8, '16-24 mask')
    check(int(r6.session_mask(df, None, None).sum()) == 24, 'ALL mask')


def test_inherited_cost_formula():
    x = econ.cost(2400.0, 2410.0, 1, 'E1')
    spread = 0.0002 / 2.0 * (2400.0 + 2410.0)
    slip = 0.0001 * (2400.0 + 2410.0)
    entry_model = 2400.0 * (1.0 + (0.0002/2.0 + 0.0001))
    exit_model = 2410.0 * (1.0 - (0.0002/2.0 + 0.0001))
    comm = 0.000007 * (entry_model + exit_model)
    expected = 10.0 - spread - slip - comm
    check(abs(x['net'] - expected) < 1e-12, 'inherited E1 cost identity changed')


def test_cross_year_replay_purge():
    st = pd.to_datetime(['2024-12-31T23:50:00Z','2024-12-31T23:55:00Z','2025-01-01T00:00:00Z','2025-01-01T00:05:00Z'])
    src = pd.DataFrame({'time': st, 'open':[1.,1.,1.,1.], 'high':[1.,1.,1.,1.], 'low':[1.,1.,1.,1.], 'close':[1.,1.,1.,1.]})
    rt = pd.date_range('2024-12-31T23:50:00Z', periods=21, freq='1min')
    raw = pd.DataFrame({'time': rt, 'open': np.ones(len(rt)), 'high':np.ones(len(rt)), 'low':np.ones(len(rt)), 'close':np.ones(len(rt))})
    sig = np.array([True, False, False, False])
    ledger, counts = econ.replay(src, raw, sig, 1, 1, 300)
    check(len(ledger) == 0, 'cross-year trade must be purged')
    check(counts['excluded_year_boundary_signals'] >= 1, 'cross-year purge must be recorded')


def test_bh_and_bootstrap_determinism():
    q = r6.bh_qvalues([0.001, 0.02, 0.9])
    check(q[0] <= q[1] < q[2], 'BH ordering invalid')
    trades=[]
    for i in range(20):
        day = pd.Timestamp('2025-01-01', tz='UTC') + pd.Timedelta(days=i)
        trades.append({'entry_time': day.isoformat(), 'profiles': {'E1': {'net': 1.0 + (i%3)*0.1}}})
    a=r6.day_block_bootstrap(trades,'E1','R6B-001',200); b=r6.day_block_bootstrap(trades,'E1','R6B-001',200)
    check(a == b, 'bootstrap must be deterministic by candidate id')
    check(a['p05'] > 0, 'positive synthetic series should have positive bootstrap floor')


def test_year_isolation_and_source_contract():
    t = pd.to_datetime(['2024-12-31T23:55:00Z','2025-01-01T00:00:00Z'])
    df = pd.DataFrame({'time':t,'open':[1.,1.],'high':[1.,1.],'low':[1.,1.],'close':[1.,1.]})
    check(len(r6.year_slice(df,2024)) == 1 and len(r6.year_slice(df,2025)) == 1, 'year slicing failed')
    source = Path(r6.__file__).read_text(encoding='utf-8')
    a = source.index("'discovery_2024_only'")
    b = source.index("'discovery_frozen_before_2025'")
    c = source.index("'confirmation_2025_only'")
    check(a < b < c, 'code order must freeze complete 2024 discovery before 2025 confirmation')
    check('source24=year_slice(source_all,2024)' in source and 'source25=year_slice(source_all,2025)' in source, 'separate year dataframes required')
    check("'protected_2026_opened':False" in source, 'protected-2026 result assertion missing')


def main():
    tests=[test_grid,test_prior_bar_only_breakout,test_sessions,test_inherited_cost_formula,test_cross_year_replay_purge,test_bh_and_bootstrap_determinism,test_year_isolation_and_source_contract]
    for t in tests:t()
    print({'status':'PASS','tests':len(tests),'market_data_accessed':False,'protected_2026_opened':False})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
