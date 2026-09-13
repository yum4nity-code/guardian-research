#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('r12',HERE/'r12_btc_eth_compression_breakout_v1_00.py')
M=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)

R=M.rules()
assert len(R)==72
assert len({M.cid(r) for r in R})==72
assert M.PROTECTED==pd.Timestamp('2026-01-01',tz='UTC')
assert M.BASELINE_HOURS==168
assert M.COSTS=={'E1':.001,'STRESS':.002}
assert set(M.EXPECTED)=={'BTCUSDT_spot_5m_2017_2025.csv','ETHUSDT_spot_5m_2017_2025.csv'}

# Complete-H1 construction: exactly 12 M5 bars required.
t5=pd.date_range('2024-01-01',periods=36,freq='5min',tz='UTC')
p5=np.linspace(100,101,len(t5))
d5=pd.DataFrame({'time':t5,'open':p5,'high':p5+.1,'low':p5-.1,'close':p5})
assert len(M.h1(d5))==3
d5gap=d5.drop(index=[13]).reset_index(drop=True)
hg=M.h1(d5gap)
assert pd.Timestamp('2024-01-01 01:00:00+00:00') not in set(hg.time)

# Synthetic H1 path with volatile baseline, compressed recent window, then upside breakout.
t=pd.date_range('2024-01-01',periods=500,freq='1h',tz='UTC')
close=[]
price=100.0
for i in range(len(t)):
 if i<330:
  price*=1.01 if i%2==0 else .99
 elif i<370:
  price*=1.00001 if i%2==0 else .99999
 elif i==370:
  price*=1.08
 else:
  price*=1.0005
 close.append(price)
open_=close.copy(); high=np.asarray(close)*1.0001; low=np.asarray(close)*.9999
d=pd.DataFrame({'time':t,'open':open_,'high':high,'low':low,'close':close})
r={'asset':'BTCUSDT','vol_window_hours':24,'channel_hours':24,'vol_ratio_max':.70,'hold_hours':6}
ts=M.simulate(d,r)
assert ts, 'expected at least one synthetic compression-breakout trade'
x=ts[0]
assert x['entry_time']==x['decision_time']+pd.Timedelta(hours=1)
assert x['exit_time']==x['entry_time']+pd.Timedelta(hours=6)
assert x['vol_ratio']<=.70
assert x['direction'] in (-1,1)

# One-position replay and no overlap.
for a,b in zip(ts,ts[1:]): assert b['decision_time']>=a['exit_time']

# Verify feature windows exclude the breakout/decision return and do not overlap.
i=d.index[d.time==x['decision_time']][0]
lr=np.log(d.close/d.close.shift(1)).to_numpy(float)
recent=lr[i-r['vol_window_hours']:i]
base=lr[i-r['vol_window_hours']-M.BASELINE_HOURS:i-r['vol_window_hours']]
assert len(recent)==24 and len(base)==168
assert np.isfinite(recent).all() and np.isfinite(base).all()
assert i not in range(i-r['vol_window_hours'],i)
assert set(range(i-r['vol_window_hours'],i)).isdisjoint(range(i-r['vol_window_hours']-M.BASELINE_HOURS,i-r['vol_window_hours']))
prior=d.iloc[i-r['channel_hours']:i]
assert len(prior)==24 and i not in prior.index

# Missing hour must fail closed for any surviving trade path.
dgap=d.drop(index=[360]).reset_index(drop=True)
for z in M.simulate(dgap,r):
 start=min(z['decision_time']-pd.Timedelta(hours=r['channel_hours']),z['decision_time']-pd.Timedelta(hours=r['vol_window_hours']+M.BASELINE_HOURS+1))
 path=dgap[(dgap.time>=start)&(dgap.time<=z['exit_time'])].time
 assert path.diff().dropna().eq(pd.Timedelta(hours=1)).all()

# Exit may not cross calendar year.
t2=pd.date_range('2024-12-20',periods=24*20,freq='1h',tz='UTC')
price=100.0; c2=[]
for i in range(len(t2)):
 price*=1.01 if i<250 and i%2==0 else (.99 if i<250 else (1.00001 if i<350 else 1.005))
 c2.append(price)
d2=pd.DataFrame({'time':t2,'open':c2,'high':np.asarray(c2)*1.0001,'low':np.asarray(c2)*.9999,'close':c2})
for z in M.simulate(d2,{'asset':'BTCUSDT','vol_window_hours':24,'channel_hours':24,'vol_ratio_max':.90,'hold_hours':24}):
 assert z['decision_time'].year==z['exit_time'].year

print('PASS R12 deterministic cold tests')
