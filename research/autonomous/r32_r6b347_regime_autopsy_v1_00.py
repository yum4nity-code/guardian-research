#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, math, os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import r5_pre_oos_economic_robustness_v1_00 as econ
import r6_xau_low_turnover_breakout_v1_00 as r6
import top2_xau_long_history_backtest_v1_00 as top2

RULE={"candidate_id":"R6B-347","lookback_bars":96,"buffer_atr":0.1,"horizon_bars":96,"session_start":0,"session_end":8,"direction":1}
BPD=288
FEATURES=["ret20","ret60","ret252","vol20","vol60","eff20","dist_high252","atr_pct","breakout_margin_atr"]
QUANTILES=[0.2,0.3,0.4,0.5,0.6,0.7,0.8]

def atomic_json(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8'); os.replace(t,p)
def hb(p,d,t,stage,extra=None):
    if not p:return
    o={"completed":d,"total":t,"stage":stage,"updated_at_utc":datetime.now(timezone.utc).isoformat(),"protected_2026_opened":False}
    if extra:o.update(extra)
    atomic_json(p,o)
def sha256(path):
    import hashlib
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def load_year(rec,tf,year):
    p=Path(rec[f"{tf.lower()}_path"])
    if sha256(p)!=rec[f"{tf.lower()}_sha256"]: raise RuntimeError(f'{tf} {year} sha mismatch')
    z=pd.read_csv(p)
    if len(z)!=int(rec[f"{tf.lower()}_rows"]): raise RuntimeError(f'{tf} {year} row mismatch')
    t=pd.to_datetime(pd.to_numeric(z.server_epoch).astype('int64'),unit='s',utc=True)
    out=pd.DataFrame({"time":t,"open":z.open.astype(float),"high":z.high.astype(float),"low":z.low.astype(float),"close":z.close.astype(float)})
    if (out.time.dt.year!=year).any() or (out.time>=pd.Timestamp('2026-01-01',tz='UTC')).any(): raise RuntimeError('year/protection violation')
    return out
def cap(trades,profile='E1',initial=10000.0):
    e=initial; peak=e; dd=0.0
    for t in sorted(trades,key=lambda x:x['entry_time']):
        r=float(t['profiles'][profile]['net'])/float(t['entry_open']); e*=1+r; peak=max(peak,e); dd=max(dd,(peak-e)/peak)
    return {"ending":e,"return_pct":(e/initial-1)*100,"max_dd_pct":dd*100,"trades":len(trades)}
def attach_features(allm5):
    c=allm5.close.astype(float); lr=np.log(c).diff()
    for d in (20,60,252): allm5[f'ret{d}']=c/c.shift(BPD*d)-1
    allm5['vol20']=lr.rolling(BPD*20,min_periods=BPD*20).std(); allm5['vol60']=lr.rolling(BPD*60,min_periods=BPD*60).std()
    abs_sum=lr.abs().rolling(BPD*20,min_periods=BPD*20).sum(); allm5['eff20']=np.log(c/c.shift(BPD*20)).abs()/abs_sum
    allm5['dist_high252']=c/c.shift(1).rolling(BPD*252,min_periods=BPD*252).max()-1
    atr=r6.atr14(allm5); allm5['atr_pct']=atr/c
    hi=allm5.high.shift(1).rolling(96,min_periods=96).max(); allm5['breakout_margin_atr']=(c-hi)/atr
    return allm5
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',required=True,type=Path); ap.add_argument('--output-dir',required=True,type=Path); ap.add_argument('--progress-file',type=Path); a=ap.parse_args()
    man=json.loads(a.manifest.read_text(encoding='utf-8'))
    if man.get('status')!='PASS' or man.get('protected_2026_opened') is not False: raise RuntimeError('invalid R30 manifest')
    out=a.output_dir; out.mkdir(parents=True,exist_ok=True); rp=out/'r32_regime_autopsy.json'
    if rp.exists(): raise RuntimeError('existing R32 result; refusing overwrite')
    years=sorted(int(y) for y in man['yearly'])
    hb(a.progress_file,0,5,'load_m5'); m5parts=[]
    for y in years:
        m=load_year(man['yearly'][str(y)],'M5',y); m5parts.append(m)
    allm5=pd.concat(m5parts,ignore_index=True).sort_values('time').reset_index(drop=True)
    hb(a.progress_file,1,5,'features'); allm5=attach_features(allm5); feat_by_time=allm5.set_index('time')
    trades=[]; annual={}; hb(a.progress_file,2,5,'replay')
    for y in years:
        if y==2004: continue
        rec=man['yearly'][str(y)]; m5=load_year(rec,'M5',y); m1=load_year(rec,'M1',y)
        atr=r6.atr14(m5); sig=r6.breakout_signal(m5,atr,96,0.1,1,0,8)
        led,_=top2.replay_window(m5,m1,sig,96,1,pd.Timestamp(f'{y}-01-01',tz='UTC'),pd.Timestamp(f'{y+1}-01-01',tz='UTC'))
        for t in led:
            st=pd.Timestamp(t['signal_time']); row=feat_by_time.loc[st]
            if isinstance(row,pd.DataFrame): row=row.iloc[0]
            z=dict(t); z['year']=y
            for f in FEATURES:z[f]=None if pd.isna(row[f]) else float(row[f])
            trades.append(z)
        annual[str(y)]={"E1":econ.stats(led,'E1'),"STRESS":econ.stats(led,'STRESS')}
    dev=[t for t in trades if 2005<=t['year']<=2017]; val=[t for t in trades if 2018<=t['year']<=2025]
    hb(a.progress_file,3,5,'scan_univariate'); scans=[]
    for f in FEATURES:
        vals=np.array([t[f] for t in dev if t[f] is not None and math.isfinite(t[f])],float)
        if len(vals)<100: continue
        for q in QUANTILES:
            thr=float(np.quantile(vals,q))
            for op in ('>=','<='):
                def keep(t,f=f,thr=thr,op=op): return t[f] is not None and math.isfinite(t[f]) and ((t[f]>=thr) if op=='>=' else (t[f]<=thr))
                d=[t for t in dev if keep(t)]; v=[t for t in val if keep(t)]
                if len(d)<150 or len(v)<80: continue
                scans.append({"feature":f,"op":op,"quantile":q,"threshold":thr,"dev_E1":cap(d,'E1'),"dev_STRESS":cap(d,'STRESS'),"val_E1":cap(v,'E1'),"val_STRESS":cap(v,'STRESS'),"dev_expectancy_bps":econ.stats(d,'E1')['expectancy_bps'],"val_expectancy_bps":econ.stats(v,'E1')['expectancy_bps']})
    scans.sort(key=lambda x:(x['dev_E1']['ending'],x['dev_STRESS']['ending']),reverse=True); top=scans[:20]
    base={"dev_E1":cap(dev,'E1'),"dev_STRESS":cap(dev,'STRESS'),"val_E1":cap(val,'E1'),"val_STRESS":cap(val,'STRESS')}
    survivors=[x for x in top if x['val_E1']['ending']>10000 and x['val_STRESS']['ending']>10000 and x['val_expectancy_bps']>0]
    result={"schema":1,"research":"R32","generated_at_utc":datetime.now(timezone.utc).isoformat(),"rule":RULE,"development":"2005-2017","validation":"2018-2025","features":FEATURES,"quantiles":QUANTILES,"base":base,"annual":annual,"top20_by_dev":top,"validation_survivors_among_top20":survivors,"protected_2026_opened":False}
    atomic_json(rp,result); pd.DataFrame(scans).to_json(out/'r32_all_filters.json',orient='records',indent=2)
    hb(a.progress_file,5,5,'complete',{"survivors":len(survivors),"protected_2026_opened":False})
    print(json.dumps({"status":"PASS","base":base,"top":top[:5],"survivors":survivors,"protected_2026_opened":False},sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())