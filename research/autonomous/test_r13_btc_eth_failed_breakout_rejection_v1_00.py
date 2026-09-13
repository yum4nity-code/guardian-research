#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, tempfile
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent
SRC=HERE/'r13_btc_eth_failed_breakout_rejection_v1_00.py'
spec=importlib.util.spec_from_file_location('r13',SRC); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def assert_(x,msg):
 if not x: raise AssertionError(msg)

def synthetic(start='2024-01-01',hours=260):
 t=pd.date_range(start,periods=hours,freq='1h',tz='UTC')
 d=pd.DataFrame({'time':t,'open':100.0,'high':101.0,'low':99.0,'close':100.0})
 return d

def main():
 R=m.rules(); assert_(len(R)==72,'rule count'); ids=[m.cid(r) for r in R]; assert_(len(set(ids))==72,'candidate IDs unique'); assert_(ids==[m.cid(r) for r in R],'candidate IDs stable')
 assert_(m.COSTS=={'E1':.001,'STRESS':.002},'costs changed')
 assert_(m.PROTECTED==pd.Timestamp('2026-01-01',tz='UTC'),'protected boundary changed')
 assert_(m.DISC0==pd.Timestamp('2018-01-01',tz='UTC') and m.DISC1==pd.Timestamp('2023-01-01',tz='UTC') and m.CONF1==pd.Timestamp('2025-01-01',tz='UTC'),'chronology changed')

 # Upper sweep + close back inside prior channel => short, entered next H1 open.
 d=synthetic(); i=200; d.loc[i,'high']=101.20; d.loc[i,'close']=100.70; d.loc[i+1,'open']=100.0; d.loc[i+4,'open']=99.0
 r={'asset':'BTCUSDT','channel_hours':24,'penetration_frac':0.05,'reentry_frac':0.10,'hold_hours':3}
 ts=m.simulate(d,r); hit=[x for x in ts if x['decision_time']==d.time.iloc[i]]; assert_(len(hit)==1,'upper rejection missing'); x=hit[0]; assert_(x['direction']==-1,'upper direction'); assert_(x['entry_time']==d.time.iloc[i]+pd.Timedelta(hours=1),'entry timing'); assert_(x['exit_time']==d.time.iloc[i]+pd.Timedelta(hours=4),'exit timing'); assert_(x['gross']>0,'short pnl direction')

 # Prior channel must exclude decision bar: changing only decision-bar high creates the sweep against unchanged prior high.
 assert_(abs(x['channel_high']-101.0)<1e-12,'decision bar leaked into prior channel')

 # Lower sweep + close back inside => long.
 d2=synthetic(); d2.loc[i,'low']=98.80; d2.loc[i,'close']=99.30; d2.loc[i+1,'open']=100.0; d2.loc[i+4,'open']=101.0
 ts2=m.simulate(d2,r); hit2=[x for x in ts2 if x['decision_time']==d2.time.iloc[i]]; assert_(len(hit2)==1 and hit2[0]['direction']==1,'lower rejection missing/symmetry broken')

 # Both sides swept and closed sufficiently inside both boundaries is ambiguous and must be rejected.
 d3=synthetic(); d3.loc[i,'high']=101.20; d3.loc[i,'low']=98.80; d3.loc[i,'close']=100.0
 ts3=m.simulate(d3,r); assert_(not any(x['decision_time']==d3.time.iloc[i] for x in ts3),'ambiguous two-sided bar accepted')

 # Missing required hour must fail closed.
 d4=d.drop(index=i+1).reset_index(drop=True); ts4=m.simulate(d4,r); assert_(not any(x['decision_time']==d.time.iloc[i] for x in ts4),'missing-hour signal accepted')

 # Cross-year exit must be purged.
 dy=synthetic('2024-12-21',260); j=258-4; dy.loc[j,'high']=101.20; dy.loc[j,'close']=100.70
 ry={'asset':'BTCUSDT','channel_hours':24,'penetration_frac':0.05,'reentry_frac':0.10,'hold_hours':12}
 tsy=m.simulate(dy,ry); assert_(not any(x['decision_time']==dy.time.iloc[j] for x in tsy),'cross-year exit accepted')

 # Static source-level contracts: exact hashes and explicit 2026 rejection exist in implementation.
 s=SRC.read_text(encoding='utf-8');
 for h in m.EXPECTED.values(): assert_(h in s,'expected input hash missing from source')
 assert_("if (z.time>=PROTECTED).any(): raise RuntimeError('protected 2026 row present')" in s,'protected row guard missing')
 assert_("if '2026' in p.name: raise RuntimeError('protected filename forbidden')" in s,'protected filename guard missing')
 print(json.dumps({'status':'PASS','tests':'R13 deterministic methodology/code preflight','definitions':len(R)}))
 return 0

if __name__=='__main__': raise SystemExit(main())
