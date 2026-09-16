#!/usr/bin/env python3
from __future__ import annotations

import pandas as pd

import r31_r6b347_regime_autopsy_v1_00 as m


def test_rule_frozen():
    assert m.RULE == {
        "candidate_id":"R6B-347",
        "lookback_bars":96,
        "buffer_atr":0.1,
        "horizon_bars":96,
        "session_start":0,
        "session_end":8,
        "direction":1,
    }


def test_capital_math():
    ts=[]
    for i,net in enumerate((10.0,-5.0)):
        ts.append({
            "entry_time":f"2020-01-0{i+1}T00:00:00+00:00",
            "entry_open":100.0,
            "profiles":{"E1":{"net":net},"STRESS":{"net":net}},
        })
    out=m.cap(ts,"E1",10000.0)
    assert abs(out["ending"]-10450.0)<1e-9
    assert abs(out["return_pct"]-4.5)<1e-9


def test_features_do_not_use_future_close_for_trailing_returns():
    n=m.BPD*253+10
    t=pd.date_range("2020-01-01",periods=n,freq="5min",tz="UTC")
    close=pd.Series([100.0+i*0.001 for i in range(n)])
    df=pd.DataFrame({
        "time":t,
        "open":close,
        "high":close+0.1,
        "low":close-0.1,
        "close":close,
    })
    a=m.attach_features(df.copy())
    i=n-5
    before=float(a.loc[i,"ret20"])
    df2=df.copy()
    df2.loc[i+1:,"close"]*=10.0
    df2.loc[i+1:,"open"]*=10.0
    df2.loc[i+1:,"high"]*=10.0
    df2.loc[i+1:,"low"]*=10.0
    b=m.attach_features(df2)
    assert float(b.loc[i,"ret20"])==before
    assert float(b.loc[i,"ret60"])==float(a.loc[i,"ret60"])
    assert float(b.loc[i,"ret252"])==float(a.loc[i,"ret252"])


def test_feature_library_fixed():
    assert m.FEATURES == [
        "ret20","ret60","ret252","vol20","vol60",
        "eff20","dist_high252","atr_pct","breakout_margin_atr"
    ]
    assert m.QUANTILES == [0.2,0.3,0.4,0.5,0.6,0.7,0.8]


def main():
    test_rule_frozen()
    test_capital_math()
    test_features_do_not_use_future_close_for_trailing_returns()
    test_feature_library_fixed()
    print("PASS: R31 causal regime autopsy tests")

if __name__=="__main__": main()
