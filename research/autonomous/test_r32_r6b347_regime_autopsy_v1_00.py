#!/usr/bin/env python3
from __future__ import annotations
import pandas as pd
import r32_r6b347_regime_autopsy_v1_00 as m

def trade(net): return {"entry_time":"2020-01-01T00:00:00+00:00","entry_open":100.0,"profiles":{"E1":{"net":net},"STRESS":{"net":net}}}
def main():
    assert m.RULE["candidate_id"]=="R6B-347" and m.RULE["lookback_bars"]==96 and m.RULE["buffer_atr"]==0.1 and m.RULE["horizon_bars"]==96
    assert m.FEATURES==["ret20","ret60","ret252","vol20","vol60","eff20","dist_high252","atr_pct","breakout_margin_atr"]
    assert m.QUANTILES==[0.2,0.3,0.4,0.5,0.6,0.7,0.8]
    x=m.cap([trade(10.0),{**trade(-5.0),"entry_time":"2020-01-02T00:00:00+00:00"}],"E1",10000.0); assert abs(x["ending"]-10450.0)<1e-9
    n=m.BPD*253+10; t=pd.date_range("2020-01-01",periods=n,freq="5min",tz="UTC"); c=pd.Series([100+i*.001 for i in range(n)])
    df=pd.DataFrame({"time":t,"open":c,"high":c+.1,"low":c-.1,"close":c}); a=m.attach_features(df.copy()); i=n-5; df2=df.copy(); df2.loc[i+1:,['open','high','low','close']]*=10; b=m.attach_features(df2)
    assert float(a.loc[i,'ret20'])==float(b.loc[i,'ret20']) and float(a.loc[i,'ret252'])==float(b.loc[i,'ret252'])
    print("PASS: R32 causal regime autopsy tests")
if __name__=='__main__': main()
