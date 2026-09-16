#!/usr/bin/env python3
from __future__ import annotations

import copy
import numpy as np
import pandas as pd

import r34_signal_execution_feed_factorial_v1_00 as m


def bars(start="2023-12-31T16:00:00Z",periods=210,freq="5min",price_shift=0.0):
    time=pd.date_range(start,periods=periods,freq=freq)
    base=100+np.arange(periods)*0.01+price_shift
    high=base+0.05
    # Force two separated breakouts in the frozen session.
    high[100]=base[100]+2.0;high[205]=base[205]+2.0
    close=base.copy();close[100]=high[100]+0.5;close[205]=high[205]+0.5
    return pd.DataFrame({"time":time,"open":base,"high":high,"low":base-0.05,"close":close})


def m1(start="2024-01-01T00:00:00Z",periods=1800,price_shift=0.0):
    time=pd.date_range(start,periods=periods,freq="1min")
    base=100+np.arange(periods)*0.001+price_shift
    return pd.DataFrame({"time":time,"open":base,"high":base+0.01,"low":base-0.01,"close":base})


def test_frozen_contract():
    m.assert_frozen_rule();assert m.YEARS==(2024,2025);assert len(m.CELLS)==4
    assert m.RULE=={"candidate_id":"R6B-347","lookback_bars":96,"buffer_atr":0.1,"horizon_bars":96,"session_start":0,"session_end":8,"direction":1,"direction_name":"LONG"}


def test_signal_diagnostics_formula():
    source=bars();diag=m.signal_diagnostics(source)
    assert list(diag.columns)==["time","close","high","atr","prior_96_high","threshold"]
    assert len(diag)>=1
    row=diag.iloc[0];assert abs(row.threshold-(row.prior_96_high+0.1*row.atr))<1e-12


def test_matching_stages_and_differences():
    cols={"close":[100,101,102,103],"high":[101,102,103,104],"atr":[1,1,1,1],"prior_96_high":[99,100,101,102],"threshold":[99.1,100.1,101.1,102.1]}
    fn=pd.DataFrame({"time":pd.to_datetime(["2024-01-01T00:00Z","2024-01-01T01:00Z","2024-01-01T02:00Z","2024-01-01T03:00Z"]),**cols})
    dc=copy.deepcopy(cols);dc["close"]=[101,102,103,104]
    du=pd.DataFrame({"time":pd.to_datetime(["2024-01-01T00:00Z","2024-01-01T01:05Z","2024-01-01T02:10Z","2024-01-01T04:00Z"]),**dc})
    pairs,s,fi,di=m.match_signals(fn,du)
    assert s["exact_timestamp"]==1;assert s["within_5_minutes_cumulative"]==2;assert s["within_10_minutes_cumulative"]==3
    assert s["fn_only_after_10_minutes"]==1 and s["duka_only_after_10_minutes"]==1
    assert set(pairs.match_stage)=={"EXACT","WITHIN_5M","WITHIN_10M"}
    assert (pairs.delta_duka_minus_fn_close==1).all();assert len(fi)==len(di)==1


def test_matrix_axis_isolation():
    signal=bars();execution_a=m1();execution_b=m1(price_shift=10.0)
    led_a,rec_a=m.run_cell(signal,execution_a,2024);led_b,rec_b=m.run_cell(signal,execution_b,2024)
    assert rec_a["accounting"]["signals_total"]==rec_b["accounting"]["signals_total"]
    assert rec_a["accounting"]["executable_trades"]==rec_b["accounting"]["executable_trades"]
    assert led_a and led_b and led_a[0]["entry_open"]!=led_b[0]["entry_open"]


def test_server_year_includes_prior_utc_tail():
    prior=pd.DataFrame({"time":pd.to_datetime(["2023-12-31T22:00:00Z"]),"open":[1.0],"high":[1.0],"low":[1.0],"close":[1.0]})
    current=pd.DataFrame({"time":pd.to_datetime(["2024-01-01T00:00:00Z"]),"open":[2.0],"high":[2.0],"low":[2.0],"close":[2.0]})
    selected=m.select_server_year([prior,current],2024)
    assert selected.time.iloc[0]==pd.Timestamp("2024-01-01T00:00:00Z")
    assert selected.open.iloc[0]==1.0


def fake_rec(trades,net,pf,exp):
    return {"accounting":{"executable_trades":trades},"metrics":{"E1":{"trades":trades,"net":net,"PF":pf,"expectancy_bps":exp}}}


def matrix_for(signal_effect,execution_effect):
    out={c:{} for c,_,__ in m.CELLS}
    for year in m.YEARS:
        for cell,sig,exe in m.CELLS:
            value=100+(signal_effect if sig=="DUKA" else 0)+(execution_effect if exe=="DUKA" else 0)
            out[cell][str(year)]=fake_rec(value,value,float(value),float(value))
    return out


def test_classification():
    assert m.classify(matrix_for(80,5))["classification"]=="SIGNAL_FEED_DOMINANT"
    assert m.classify(matrix_for(5,80))["classification"]=="EXECUTION_FEED_DOMINANT"
    assert m.classify(matrix_for(20,20))["classification"]=="MIXED"
    no_loss=matrix_for(20,20)
    for cell in no_loss:
        for year in ("2024","2025"):no_loss[cell][year]["metrics"]["E1"]["PF"]=None
    assert m.classify(no_loss)["classification"]=="MIXED"


def test_2026_guard():
    bad=pd.DataFrame({"time":pd.to_datetime(["2026-01-01T00:00:00Z"]),"open":[1.0],"high":[1.0],"low":[1.0],"close":[1.0]})
    try:m.validate_years(bad,"bad")
    except RuntimeError as exc:assert "unexpected years" in str(exc) or "protected 2026" in str(exc)
    else:raise AssertionError("2026 was not rejected")


def main():
    test_frozen_contract();test_signal_diagnostics_formula();test_matching_stages_and_differences()
    test_matrix_axis_isolation();test_server_year_includes_prior_utc_tail();test_classification();test_2026_guard()
    print("PASS: R34 signal/execution factorial synthetic tests")


if __name__=="__main__":main()
