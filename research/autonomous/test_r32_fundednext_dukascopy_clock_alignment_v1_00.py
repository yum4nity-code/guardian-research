#!/usr/bin/env python3
from __future__ import annotations
import pandas as pd
import r32_fundednext_dukascopy_clock_alignment_v1_00 as m

def test_contiguous_returns():
    df=pd.DataFrame({
        "time":pd.to_datetime(["2024-01-01T00:00:00Z","2024-01-01T00:05:00Z","2024-01-01T00:15:00Z"]),
        "close":[100.0,101.0,102.0],
    })
    r=m.contiguous_returns(df)
    assert len(r)==1
    assert r.iloc[0]["time"]==pd.Timestamp("2024-01-01T00:05:00Z")

def test_shift_grid():
    assert m.SHIFTS==list(range(-4,5))

def test_sign_convention():
    # If broker/server stamp is UTC+2, shifting by -2h aligns to UTC.
    t=pd.Timestamp("2024-01-01T10:00:00Z")
    assert t+pd.Timedelta(hours=-2)==pd.Timestamp("2024-01-01T08:00:00Z")

def main():
    test_contiguous_returns()
    test_shift_grid()
    test_sign_convention()
    print("PASS: R32 clock-alignment tests")

if __name__=="__main__":
    main()
