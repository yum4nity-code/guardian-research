#!/usr/bin/env python3
from __future__ import annotations
import pandas as pd
import r33_corrected_server_time_long_history_v1_00 as m

def test_frozen_defs():
    assert m.CANDIDATES["R6B-347"]["lookback_bars"]==96
    assert m.CANDIDATES["R6B-347"]["buffer_atr"]==0.1
    assert m.CANDIDATES["R6B-347"]["horizon_bars"]==96
    assert m.CANDIDATES["R6B-307"]["lookback_bars"]==96
    assert m.CANDIDATES["R6B-307"]["buffer_atr"]==0.0
    assert m.CANDIDATES["R6B-307"]["horizon_bars"]==48

def test_dst_2024():
    assert m.server_offset_hours_for_utc(pd.Timestamp("2024-02-15T12:00:00Z"))==2
    assert m.server_offset_hours_for_utc(pd.Timestamp("2024-03-15T12:00:00Z"))==3
    assert m.server_offset_hours_for_utc(pd.Timestamp("2024-10-15T12:00:00Z"))==3
    assert m.server_offset_hours_for_utc(pd.Timestamp("2024-11-15T12:00:00Z"))==2

def test_dst_pre_2007_rule():
    assert m.server_offset_hours_for_utc(pd.Timestamp("2006-03-15T12:00:00Z"))==2
    assert m.server_offset_hours_for_utc(pd.Timestamp("2006-04-15T12:00:00Z"))==3
    assert m.server_offset_hours_for_utc(pd.Timestamp("2006-11-01T12:00:00Z"))==2

def test_server_coordinate_shift():
    df=pd.DataFrame({
        "time":pd.to_datetime(["2024-02-15T12:00:00Z","2024-07-15T12:00:00Z"]),
        "open":[1,1],"high":[1,1],"low":[1,1],"close":[1,1],
    })
    x=m.to_server_coordinate(df)
    assert x.time.iloc[0]==pd.Timestamp("2024-02-15T14:00:00Z")
    assert x.time.iloc[1]==pd.Timestamp("2024-07-15T15:00:00Z")

def test_capital():
    trades=[
        {"entry_time":"2024-01-01T00:00:00+00:00","entry_open":100.0,"profiles":{"E1":{"net":10.0},"STRESS":{"net":10.0}}},
        {"entry_time":"2024-01-02T00:00:00+00:00","entry_open":100.0,"profiles":{"E1":{"net":-5.0},"STRESS":{"net":-5.0}}},
    ]
    x=m.capital(trades,"E1",10000.0)
    assert abs(x["ending_capital"]-10450.0)<1e-9

def main():
    test_frozen_defs()
    test_dst_2024()
    test_dst_pre_2007_rule()
    test_server_coordinate_shift()
    test_capital()
    print("PASS: R33 corrected server-time long-history tests")

if __name__=="__main__":
    main()
