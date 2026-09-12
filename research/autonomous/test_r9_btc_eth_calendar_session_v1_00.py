#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, tempfile
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('r9',HERE/'r9_btc_eth_calendar_session_v1_00.py'); r9=importlib.util.module_from_spec(spec); spec.loader.exec_module(r9)

def check(ok,msg):
 if not ok: raise AssertionError(msg)

def synth_5m(start,periods,base=100.0,step=0.01):
 t=pd.date_range(start,periods=periods,freq='5min',tz='UTC'); o=[base+i*step for i in range(periods)]
 return pd.DataFrame({'time':t,'open':o,'high':[x+.05 for x in o],'low':[x-.05 for x in o],'close':[x+.01 for x in o]})

def main():
 check(len(r9.rules())==672,'frozen candidate count')
 d=synth_5m('2024-01-01',36); h=r9.h1(d); check(len(h)==3,'complete H1 resampling')
 # Monday 00:00 UTC, 1h hold, exact contiguous bars; long wins, short loses.
 x=pd.DataFrame({'time':pd.date_range('2024-01-01',periods=4,freq='1h',tz='UTC'),'open':[100,101,102,103],'high':[101,102,103,104],'low':[99,100,101,102],'close':[100.5,101.5,102.5,103.5]})
 rl={'asset':'BTCUSDT','weekday':0,'hour':0,'hold_hours':1,'direction':1}; rs=dict(rl); rs['direction']=-1
 tl=r9.simulate(x,rl); ts=r9.simulate(x,rs); check(len(tl)==1 and tl[0]['gross']>0,'long pnl/timing'); check(len(ts)==1 and ts[0]['gross']<0,'short pnl sign'); check(abs(tl[0]['E1']-(tl[0]['gross']-.001))<1e-12,'E1 cost'); check(abs(tl[0]['STRESS']-(tl[0]['gross']-.002))<1e-12,'stress cost')
 gap=x.drop(index=1).reset_index(drop=True); check(len(r9.simulate(gap,rl))==0,'missing-hour fail closed')
 y=pd.DataFrame({'time':pd.to_datetime(['2024-12-31T23:00Z','2025-01-01T00:00Z']),'open':[100,101],'high':[101,102],'low':[99,100],'close':[100,101]}); rr={'asset':'BTCUSDT','weekday':1,'hour':23,'hold_hours':1,'direction':1}; check(len(r9.simulate(y,rr))==0,'year-boundary purge')
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'BTCUSDT_spot_5m_2017_2025.csv'; z=synth_5m('2025-12-31 23:00',13); z.to_csv(p,index=False)
  try: r9.load(p); raise AssertionError('protected row was accepted')
  except RuntimeError as e: check('protected' in str(e).lower(),'protected rejection reason')
 print('PASS R9 deterministic preflight: 672 rules, UTC trigger/execution semantics, costs, gaps, year purge, protected-2026 rejection')
 return 0
if __name__=='__main__': raise SystemExit(main())
