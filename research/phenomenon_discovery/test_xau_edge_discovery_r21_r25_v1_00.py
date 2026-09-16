#!/usr/bin/env python3
"""Synthetic cold-review test suite for R21-R25 v1.00.

These tests validate implementation mechanics only. They are not the required
independent cold audit and do not authorize real-data execution.
"""
from __future__ import annotations

import csv, tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import xau_edge_discovery_r21_r25_v1_00 as m

def B(dt, o, h, l, c):
    return m.Bar(int(dt.timestamp()), dt, 'M5', o, h, l, c)

def test_stage_boundaries():
    assert m._stage_accepts(date(2019,6,30),'discovery')
    assert not m._stage_accepts(date(2019,7,1),'discovery')
    assert m._stage_accepts(date(2019,7,1),'confirmation')
    assert m._stage_accepts(date(2024,12,31),'confirmation')
    assert not m._stage_accepts(date(2025,1,1),'confirmation')
    try: m._stage_accepts(date(2025,1,1),'preoos')
    except RuntimeError as e: assert 'pre-OOS 2025 is locked' in str(e)
    else: raise AssertionError('2025 pre-OOS was not locked')
    try: m._stage_accepts(date(2026,1,1),'preoos')
    except RuntimeError as e: assert 'PROTECTED 2026' in str(e)
    else: raise AssertionError('2026 was not rejected')

def test_loader_rejects_2026_even_if_stage_would_filter():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'x.csv'
        with p.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=['timeframe','server_epoch','open','high','low','close']); w.writeheader()
            dt=datetime(2026,1,2,tzinfo=timezone.utc)
            w.writerow({'timeframe':'M5','server_epoch':int(dt.timestamp()),'open':100,'high':101,'low':99,'close':100})
        try: m.load_bars(p,'discovery')
        except RuntimeError as e: assert 'PROTECTED 2026' in str(e)
        else: raise AssertionError('2026 input did not hard fail')

def test_forward_return_requires_contiguity():
    a=B(datetime(2019,1,1,tzinfo=timezone.utc),100,101,99,100)
    b=B(datetime(2019,1,1,0,10,tzinfo=timezone.utc),100,102,99,101)
    assert m.forward_return([a,b],0,1) is None

def test_r21_uses_0820_ny_close_anchor():
    start=datetime(2019,1,15,13,20,tzinfo=timezone.utc)
    bars=[]
    prices=[100,101,102,104,105]
    for k,p in enumerate(prices):
        dt=start+timedelta(minutes=5*k); bars.append(B(dt,p,p+.2,p-.2,p))
    ev=m.r21_comex_unconditional_drift(bars)
    assert len(ev)==1
    assert abs(ev[0]['post_15m']-(104/100-1))<1e-15

def test_r22_prior48_excludes_current_return():
    start=datetime(2019,1,2,tzinfo=timezone.utc); bars=[]; p=100.0
    for i in range(50):
        if i==49: p*=1.10
        elif i>0: p*=1.0001 if i%2 else 0.9999
        dt=start+timedelta(minutes=5*i); bars.append(B(dt,p,p+.01,p-.01,p))
    st=m._rolling_stdev48(bars)
    assert st[49] is not None and st[49] < 0.001

def test_r22_nearest_rank_quantiles():
    xs=list(range(1,101))
    assert m._quantile_nearest_rank(xs,.10)==10
    assert m._quantile_nearest_rank(xs,.20)==20

def test_r22_sampling_is_independent_by_compression_state():
    bars=[]
    for d in range(1,21):
        dt=datetime(2019,1,d,12,0,tzinfo=timezone.utc)
        bars.append(B(dt,100,101,99,100))
    bars.append(B(datetime(2019,1,21,12,0,tzinfo=timezone.utc),100,101,99,100))
    bars.append(B(datetime(2019,1,21,12,5,tzinfo=timezone.utc),100,101,99,100))
    original_st=m._rolling_stdev48; original_base=m._same_clock_abs_baselines
    try:
        m._rolling_stdev48=lambda _: [float(i) for i in range(1,21)]+[3.5,1.0]
        m._same_clock_abs_baselines=lambda _: {}
        ev=m.r22_volatility_compression(bars)
    finally:
        m._rolling_stdev48=original_st; m._same_clock_abs_baselines=original_base
    cur=[e for e in ev if e['day_utc']=='2019-01-21']
    assert [(e['compression_state'], e['epoch']) for e in cur] == [('bottom20', bars[20].epoch), ('bottom10', bars[21].epoch)]

def test_r23_overnight_direction_and_post_sign():
    bars=[]
    day=datetime(2019,1,15,tzinfo=timezone.utc)
    bars.append(B(day,100,100.2,99.8,100))
    start=datetime(2019,1,15,13,20,tzinfo=timezone.utc)
    vals=[110,111,112,113,114,115,116,117,118,119,120,121,122]
    for k,p in enumerate(vals):
        dt=start+timedelta(minutes=5*k); bars.append(B(dt,p,p+.2,p-.2,p))
    ev=m.r23_overnight_to_ny(bars)
    assert len(ev)==1 and ev[0]['direction']==1
    assert abs(ev[0]['pre_ny_return']-.10)<1e-15
    assert ev[0]['continuation_30m']>0 and ev[0]['reversal_30m']<0

def test_r24_opening_range_and_first_breakout():
    start=datetime(2019,1,15,13,20,tzinfo=timezone.utc)
    bars=[]
    rows=[(100,101,99,100.5),(100.5,102,100,101),(101,101.5,99.5,100.8),(100.8,101.8,100,101.5),(101.5,103,101,102.5),(102.5,104,102,103.5),(103.5,105,103,104.5),(104.5,106,104,105.5),(105.5,107,105,106.5)]
    for k,(o,h,l,c) in enumerate(rows):
        dt=start+timedelta(minutes=5*k); bars.append(B(dt,o,h,l,c))
    ev=m.r24_comex_opening_range_breakout(bars)
    assert len(ev)==1 and ev[0]['direction']==1
    assert ev[0]['epoch']==bars[4].epoch
    assert abs(ev[0]['continuation_2b']-(104.5/102.5-1))<1e-15

def test_r25_previous_data_day_gap_fill_and_direction():
    bars=[]
    prev=datetime(2019,1,14,23,55,tzinfo=timezone.utc)
    bars.append(B(prev,99.5,100.2,99.4,100))
    start=datetime(2019,1,15,13,20,tzinfo=timezone.utc)
    vals=[(105,105.2,104.8,105),(104,104.2,103.8,104),(102,102.2,101.8,102),(100,100.2,99.8,100),(99,99.2,98.8,99),(98,98.2,97.8,98),(97,97.2,96.8,97)]
    for k,(o,h,l,c) in enumerate(vals):
        dt=start+timedelta(minutes=5*k); bars.append(B(dt,o,h,l,c))
    ev=m.r25_ny_gap_previous_close(bars)
    assert len(ev)==1 and ev[0]['gap_direction']==1
    assert ev[0]['toward_15m']>0 and ev[0]['away_15m']<0
    assert ev[0]['filled_by_15m'] is True

def test_cluster_stats_uses_day_clusters():
    events=[{'cluster_day':'a','x':1.0},{'cluster_day':'a','x':2.0},{'cluster_day':'b','x':-1.0},{'cluster_day':'b','x':0.0}]
    s=m.cluster_stats(events,'x')
    assert s['n']==4 and s['clusters']==2 and abs(s['mean']-.5)<1e-15

def main():
    test_stage_boundaries(); test_loader_rejects_2026_even_if_stage_would_filter(); test_forward_return_requires_contiguity()
    test_r21_uses_0820_ny_close_anchor(); test_r22_prior48_excludes_current_return(); test_r22_nearest_rank_quantiles(); test_r22_sampling_is_independent_by_compression_state()
    test_r23_overnight_direction_and_post_sign(); test_r24_opening_range_and_first_breakout(); test_r25_previous_data_day_gap_fill_and_direction(); test_cluster_stats_uses_day_clusters()
    print('PASS: R21-R25 synthetic implementation tests')

if __name__=='__main__': main()
