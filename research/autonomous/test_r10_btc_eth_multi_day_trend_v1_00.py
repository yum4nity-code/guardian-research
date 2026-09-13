#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('r10',HERE/'r10_btc_eth_multi_day_trend_v1_00.py')
M=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)

assert len(M.rules())==72
assert len({M.cid(r) for r in M.rules()})==72
assert M.PROTECTED==pd.Timestamp('2026-01-01',tz='UTC')
assert set(M.COSTS)=={'E1','STRESS'} and M.COSTS['E1']==.001 and M.COSTS['STRESS']==.002

# Synthetic complete H1 path: daily 00:00 decisions, deterministic rising price.
t=pd.date_range('2024-01-01',periods=24*45,freq='1h',tz='UTC')
p=[100.0*(1.0005**i) for i in range(len(t))]
d=pd.DataFrame({'time':t,'open':p,'high':p,'low':p,'close':p})
r={'asset':'BTCUSDT','lookback_hours':24,'threshold':.01,'hold_hours':24}
ts=M.simulate(d,r)
assert ts, 'expected synthetic trend trades'
for x in ts:
 assert x['entry_time']==x['decision_time']+pd.Timedelta(hours=1)
 assert x['exit_time']==x['entry_time']+pd.Timedelta(hours=24)
 assert x['gross']>0
# One-position replay: positions cannot overlap.
for a,b in zip(ts,ts[1:]): assert b['decision_time']>=a['exit_time']

# Missing hour must fail closed for any trade whose required path crosses the gap.
dgap=d.drop(index=[300]).reset_index(drop=True)
for x in M.simulate(dgap,r):
 path=dgap[(dgap.time>=x['decision_time']-pd.Timedelta(hours=24))&(dgap.time<=x['exit_time'])].time
 assert path.diff().dropna().eq(pd.Timedelta(hours=1)).all()

# Boundary exits may not cross calendar year.
t2=pd.date_range('2024-12-20',periods=24*20,freq='1h',tz='UTC'); p2=[100*(1.001**i) for i in range(len(t2))]
d2=pd.DataFrame({'time':t2,'open':p2,'high':p2,'low':p2,'close':p2})
for x in M.simulate(d2,{'asset':'BTCUSDT','lookback_hours':24,'threshold':.01,'hold_hours':168}): assert x['decision_time'].year==x['exit_time'].year

print('PASS R10 deterministic cold tests')
