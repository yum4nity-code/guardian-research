#!/usr/bin/env python3
from __future__ import annotations
import math
import numpy as np
import pandas as pd
import strategy_factory_causal_next_open_v1_00 as f


def frame(times,opens,closes=None):
    if closes is None: closes=opens
    return pd.DataFrame({'time':pd.to_datetime(times,utc=True),'open':opens,'high':np.maximum(opens,closes),'low':np.minimum(opens,closes),'close':closes})


def main():
    # Signal at t=0 must not capture close[0]->open[1]. For h=1 it captures open[1]->open[2].
    df=frame(['2024-01-01 00:00','2024-01-01 00:05','2024-01-01 00:10','2024-01-01 00:15'],[100.,110.,130.,160.],[105.,120.,140.,170.])
    atr=pd.Series([10.,10.,10.,10.])
    r=f.causal_return(df,atr,1,1)
    assert math.isclose(r[0],2.0,abs_tol=1e-12),r[0]  # (130-110)/10
    assert math.isclose(r[1],3.0,abs_tol=1e-12),r[1]  # (160-130)/10
    assert np.isnan(r[2]) and np.isnan(r[3])

    # Direction must invert exactly.
    rs=f.causal_return(df,atr,1,-1)
    assert math.isclose(rs[0],-2.0,abs_tol=1e-12)

    # Year boundary purge: signal, entry and exit must all remain in the same year.
    ydf=frame(['2024-12-31 23:50','2024-12-31 23:55','2025-01-01 00:00','2025-01-01 00:05'],[100.,101.,102.,103.])
    yr=f.causal_return(ydf,pd.Series([1.,1.,1.,1.]),1,1)
    assert np.isnan(yr[0]),yr  # exit lands in 2025
    assert np.isnan(yr[1]),yr  # entry lands in 2025 while signal is 2024

    # Tail rule uses only current/past feature values and serialized session parameters.
    rule={'feature':'x','operator':'gt','cutpoint':1.5,'hour_start':0,'hour_width':24}
    ft=pd.DataFrame({'x':[1.,2.,3.,4.]})
    mask=f.apply_rule(df,ft,rule)
    assert mask.tolist()==[False,True,True,True]

    # BH q-values monotone in sorted p order and bounded.
    q=f.bh_qvalues(np.array([0.001,0.01,0.2,1.0]))
    assert np.all((q>=0)&(q<=1))
    order=np.argsort(np.array([0.001,0.01,0.2,1.0]))
    assert np.all(np.diff(q[order])>=-1e-15)

    print('{"status":"PASS","tests":5,"protected_market_data_access":false}')
    return 0

if __name__=='__main__': raise SystemExit(main())
