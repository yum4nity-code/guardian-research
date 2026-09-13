#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, math, tempfile
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
TARGET=HERE/'r11_btc_eth_lead_lag_spillover_v1_00.py'
spec=importlib.util.spec_from_file_location('r11',TARGET); r11=importlib.util.module_from_spec(spec); spec.loader.exec_module(r11)

def base_sync(n=260,start='2024-01-01 00:00:00+00:00'):
 t=pd.date_range(start,periods=n,freq='1h',tz='UTC'); x=np.arange(n,dtype=float)
 btc=100*np.exp(.0002*x+.002*np.sin(x/7)); eth=50*np.exp(.00015*x+.0015*np.cos(x/9))
 def one(c): return pd.DataFrame({'time':t,'open':c,'high':c*1.001,'low':c*.999,'close':c})
 return r11.synchronize(one(btc),one(eth))

def manual_signal_frame(start='2024-01-01 00:00:00+00:00',n=40):
 t=pd.date_range(start,periods=n,freq='1h',tz='UTC'); d=pd.DataFrame({'time':t})
 for a,base in [('BTCUSDT',100.0),('ETHUSDT',50.0)]:
  d[f'{a}_open']=base; d[f'{a}_high']=base; d[f'{a}_low']=base; d[f'{a}_close']=base; d[f'{a}_sigma_prior']=1.0; d[f'{a}_logret1']=0.0
 return d

def main():
 R=r11.rules(); assert len(R)==72; assert len({r11.cid(x) for x in R})==72
 assert r11.EXPECTED['BTCUSDT_spot_5m_2017_2025.csv']=='75d0d48dcfa7e649192d1eb2c96e89a591aa49bcfac11d394a1f84113264f6e8'
 assert r11.EXPECTED['ETHUSDT_spot_5m_2017_2025.csv']=='21b170675eae6bd2e3d442391e2acb9392abdff443f517b5cb0ee1946a12aa13'
 assert r11.COSTS=={'E1':.001,'STRESS':.002} and r11.LAG_RATIO==.5 and r11.VOL_WINDOW==168

 # Current completed return must not alter its own volatility denominator.
 d1=base_sync(); i=220; s1=float(d1.BTCUSDT_sigma_prior.iloc[i])
 d2=base_sync(); d2.loc[i,'BTCUSDT_close']*=1.50
 btc=d2[['time','BTCUSDT_open','BTCUSDT_high','BTCUSDT_low','BTCUSDT_close']].rename(columns=lambda c:c.replace('BTCUSDT_',''))
 eth=d2[['time','ETHUSDT_open','ETHUSDT_high','ETHUSDT_low','ETHUSDT_close']].rename(columns=lambda c:c.replace('ETHUSDT_',''))
 d2b=r11.synchronize(btc,eth); s2=float(d2b.BTCUSDT_sigma_prior.iloc[i]); assert math.isclose(s1,s2,rel_tol=0,abs_tol=1e-15)

 # A synchronized-hour gap must poison the 168-hour prior-volatility window instead of being treated as a one-hour return.
 g=base_sync(n=380); btc=g[['time','BTCUSDT_open','BTCUSDT_high','BTCUSDT_low','BTCUSDT_close']].rename(columns=lambda c:c.replace('BTCUSDT_','')); eth=g[['time','ETHUSDT_open','ETHUSDT_high','ETHUSDT_low','ETHUSDT_close']].rename(columns=lambda c:c.replace('ETHUSDT_',''))
 btc=btc.drop(index=190).reset_index(drop=True); gg=r11.synchronize(btc,eth); gap_i=int(np.where(gg.time.diff().eq(pd.Timedelta(hours=2)))[0][0]); assert pd.isna(gg.BTCUSDT_logret1.iloc[gap_i]); assert pd.isna(gg.BTCUSDT_sigma_prior.iloc[gap_i+10])

 # Frozen lag-ratio gate and direction transfer.
 d=manual_signal_frame(); i=10; d.loc[i-1,'BTCUSDT_close']=100; d.loc[i,'BTCUSDT_close']=100*math.exp(2.0); d.loc[i-1,'ETHUSDT_close']=50; d.loc[i,'ETHUSDT_close']=50*math.exp(.5)
 rule={'leader':'BTCUSDT','follower':'ETHUSDT','lookback_hours':1,'leader_z_threshold':1.5,'hold_hours':3,'lag_ratio':.5,'vol_window_hours':168}
 s=r11.signal_at(d,i,rule); assert s is not None and s['direction']==1 and math.isclose(s['leader_z'],2.0,abs_tol=1e-12)
 d.loc[i,'ETHUSDT_close']=50*math.exp(1.2); assert r11.signal_at(d,i,rule) is None

 # Missing synchronized H1 inside lookback fails closed.
 dm=manual_signal_frame(n=12).drop(index=8).reset_index(drop=True); dm.loc[8,'BTCUSDT_close']=100*math.exp(2.0)
 rule3=dict(rule); rule3['lookback_hours']=3; assert r11.signal_at(dm,8,rule3) is None

 # Next-H1-open entry, fixed exit, costs and one-position semantics.
 d=manual_signal_frame(n=30); d.loc[:,['BTCUSDT_sigma_prior','ETHUSDT_sigma_prior']]=.01
 for k in [5,6,7,8,9,10]:
  d.loc[k-1,'BTCUSDT_close']=100; d.loc[k,'BTCUSDT_close']=103; d.loc[k,'ETHUSDT_close']=50
 d['ETHUSDT_open']=np.linspace(50,53,len(d)); rulex=dict(rule); rulex['hold_hours']=3
 ts=r11.simulate(d,rulex); assert ts
 q=ts[0]; assert q['entry_time']==q['decision_bar_time']+pd.Timedelta(hours=1); assert q['exit_time']==q['entry_time']+pd.Timedelta(hours=3)
 assert math.isclose(q['E1'],q['gross']-.001,abs_tol=1e-15); assert math.isclose(q['STRESS'],q['gross']-.002,abs_tol=1e-15)
 for a,b in zip(ts,ts[1:]): assert b['entry_time']>=a['exit_time']

 # Calendar-year crossing trade is rejected.
 y=manual_signal_frame(start='2024-12-31 18:00:00+00:00',n=10); y.loc[:,['BTCUSDT_sigma_prior','ETHUSDT_sigma_prior']]=.01
 y.loc[4,'BTCUSDT_close']=100; y.loc[5,'BTCUSDT_close']=103; y.loc[5,'ETHUSDT_close']=50
 ry=dict(rule); ry['hold_hours']=3; ty=r11.simulate(y,ry); assert not any(x['decision_bar_time'].year!=x['exit_time'].year for x in ty)

 # H1 builder rejects an incomplete 5-minute hour.
 tt=pd.date_range('2024-01-01',periods=24,freq='5min',tz='UTC'); raw=pd.DataFrame({'time':tt,'open':1.,'high':1.,'low':1.,'close':1.}); raw=raw.drop(index=3).reset_index(drop=True); hh=r11.h1(raw); assert pd.Timestamp('2024-01-01 00:00:00+00:00') not in set(hh.time)

 # Protected filename is rejected before any read.
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'BTCUSDT_2026.csv'; p.write_text('time,open,high,low,close\n',encoding='utf-8')
  try: r11.load(p); raise AssertionError('protected filename was not rejected')
  except RuntimeError as e: assert 'protected filename forbidden' in str(e)

 print('PASS R11 deterministic preflight: 72 rules, prior-only normalization, synchronized-gap fail-closed behavior, lag gate, timing/overlap, costs, year purge, hashes and 2026 boundary verified.')
 return 0

if __name__=='__main__': raise SystemExit(main())
