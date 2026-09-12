#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, os, random, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import strategy_factory_causal_next_open_v1_00 as r5
import r5_pre_oos_economic_robustness_v1_00 as econ

PROTECTED=pd.Timestamp('2026-01-01',tz='UTC')
EXPECTED={'xauusd_m5_2024_2025_news_clean.csv':'972ecaf6c3cadf7136363f396d7a29e7a6246646b575fad5c3e677036004b503','xauusd_m1_2024_2025_raw.csv':'f98a395961b27ca9dcb34cffa4ef8dd93720adb70292abf7bc96108667232445'}
LOOKBACKS=[12,24,48,96]; BUFFERS=[0.0,.10,.20]; HORIZONS=[12,24,48,96]
SESSIONS=[('ALL',None,None),('UTC00_08',0,8),('UTC08_16',8,16),('UTC16_24',16,24)]
DIRECTIONS=[('LONG',1),('SHORT',-1)]; BOOTSTRAPS=2000

def sha256_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def atomic_json(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    for i,d in enumerate((.05,.1,.2,.4,.8,1.0)):
        try: os.replace(tmp,path); return
        except PermissionError:
            if i==5: raise
            time.sleep(d)

def heartbeat(path,done,total,stage,extra=None):
    if not path:return
    x={'completed':int(done),'total':int(total),'stage':stage,'updated_at_utc':datetime.now(timezone.utc).isoformat()}
    if extra:x.update(extra)
    atomic_json(path,x)

def load_exact(path):
    path=Path(path)
    if path.name not in EXPECTED: raise RuntimeError(f'unapproved input: {path.name}')
    got=sha256_file(path)
    if got!=EXPECTED[path.name]: raise RuntimeError(f'hash mismatch {path.name}: {got}')
    m=r5.detect(path)
    if not m: raise RuntimeError(f'unreadable OHLC input: {path}')
    df=r5.load_market(path,m,2_000_000)
    if (df.time>=PROTECTED).any(): raise RuntimeError(f'protected row present: {path}')
    if not set(df.time.dt.year.unique()).issubset({2024,2025}): raise RuntimeError('unapproved year')
    return df

def year_slice(df,year): return df[df.time.dt.year==year].reset_index(drop=True).copy()

def atr14(df):
    prev=df.close.shift(1); tr=pd.concat([(df.high-df.low).abs(),(df.high-prev).abs(),(df.low-prev).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()

def session_mask(df,start,end):
    if start is None:return np.ones(len(df),dtype=bool)
    h=df.time.dt.hour.to_numpy(); return (h>=start)&(h<end)

def breakout_signal(df,atr,lookback,buffer_atr,direction,start,end):
    hi=df.high.shift(1).rolling(lookback,min_periods=lookback).max().to_numpy(float)
    lo=df.low.shift(1).rolling(lookback,min_periods=lookback).min().to_numpy(float)
    a=atr.to_numpy(float); c=df.close.to_numpy(float)
    sig=c>(hi+buffer_atr*a) if direction==1 else c<(lo-buffer_atr*a)
    return np.asarray(sig&np.isfinite(a)&session_mask(df,start,end),dtype=bool)

def pf(metric):
    x=metric.get('PF')
    if x is None:return float('inf') if metric.get('net',0)>0 else 0.0
    return float(x)

def bh_qvalues(pvals):
    n=len(pvals)
    if not n:return []
    order=np.argsort(np.asarray(pvals,float)); q=np.ones(n); prev=1.0
    for k in range(n-1,-1,-1):
        idx=int(order[k]); val=min(prev,float(pvals[idx])*n/(k+1)); q[idx]=val; prev=val
    return q.tolist()

def candidate_seed(cid): return int(hashlib.sha256(cid.encode()).hexdigest()[:16],16)&0xffffffff

def day_block_bootstrap(trades,profile,cid,b=BOOTSTRAPS):
    by={}
    for t in trades: by.setdefault(pd.Timestamp(t['entry_time']).strftime('%Y-%m-%d'),[]).append(float(t['profiles'][profile]['net']))
    blocks=[by[d] for d in sorted(by)]
    if not blocks:return {'days':0,'resamples':b,'p_one_sided':1.0,'mean':None,'p05':None}
    obs=float(np.mean([x for z in blocks for x in z])); rng=random.Random(candidate_seed(cid)); means=[]
    for _ in range(b):
        vals=[]
        for __ in range(len(blocks)): vals.extend(blocks[rng.randrange(len(blocks))])
        means.append(float(np.mean(vals)))
    return {'days':len(blocks),'resamples':b,'p_one_sided':float((1+sum(x<=0 for x in means))/(b+1)),'mean':obs,'p05':float(np.quantile(means,.05))}

def period(trades,start,end):
    a=pd.Timestamp(start,tz='UTC'); b=pd.Timestamp(end,tz='UTC')
    return [t for t in trades if a<=pd.Timestamp(t['entry_time']) and pd.Timestamp(t['exit_time'])<b]

def definition_grid():
    out=[]; i=0
    for L in LOOKBACKS:
      for buf in BUFFERS:
       for h in HORIZONS:
        for sname,st,en in SESSIONS:
         for dname,d in DIRECTIONS:
          i+=1; out.append({'candidate_id':f'R6B-{i:03d}','lookback_bars':L,'buffer_atr':buf,'horizon_bars':h,'session':sname,'session_start':st,'session_end':en,'direction_name':dname,'direction':d})
    return out

def evaluate_year(rule,source,raw,year):
    atr=atr14(source); sig=breakout_signal(source,atr,rule['lookback_bars'],rule['buffer_atr'],rule['direction'],rule['session_start'],rule['session_end'])
    ledger,accounting=econ.replay(source,raw,sig,rule['horizon_bars'],rule['direction'],300)
    full=period(ledger,f'{year}-01-01',f'{year+1}-01-01')
    return ledger,accounting,{p:econ.stats(full,p) for p in econ.PROFILES}

def publish(publisher,status,summary,artifacts):
    if not publisher:return
    cmd=['python',publisher,'--phase','r6-xau-low-turnover-breakout','--status',status,'--summary',summary]
    for a in artifacts:cmd+=['--artifact',str(a)]
    subprocess.run(cmd,check=True)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--phase-ib-root',required=True); ap.add_argument('--output-dir',required=True); ap.add_argument('--progress-file'); ap.add_argument('--publisher'); args=ap.parse_args()
    root=Path(args.phase_ib_root); out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True); progress=Path(args.progress_file) if args.progress_file else None
    heartbeat(progress,0,384,'verify_inputs')
    source_all=load_exact(root/'xauusd_m5_2024_2025_news_clean.csv'); raw_all=load_exact(root/'xauusd_m1_2024_2025_raw.csv')
    source24=year_slice(source_all,2024); raw24=year_slice(raw_all,2024); source25=year_slice(source_all,2025); raw25=year_slice(raw_all,2025)
    rules=definition_grid(); discovery=[]; all_candidates=[]
    # Discovery loop is strictly 2024. No 2025 signal/replay/metric is computed here.
    for i,r in enumerate(rules,1):
        ledger,accounting,m=evaluate_year(r,source24,raw24,2024)
        ok=m['E1']['trades']>=30 and m['E1']['net']>0 and m['STRESS']['net']>0 and m['E1']['ex_best_positive_net']>0 and pf(m['E1'])>1.0
        rec=dict(r); rec.update({'signal_accounting_2024':accounting,'y2024':m,'discovery_pass':bool(ok)})
        all_candidates.append(rec)
        if ok: discovery.append(rec)
        if i%16==0:heartbeat(progress,i,384,'discovery_2024_only',{'discovery_passes':len(discovery)})
    # Freeze the entire discovery set before touching confirmation calculations.
    frozen_ids=tuple(r['candidate_id'] for r in discovery)
    heartbeat(progress,384,384,'discovery_frozen_before_2025',{'discovery_passes':len(discovery),'frozen_ids_sha256':hashlib.sha256('|'.join(frozen_ids).encode()).hexdigest()})
    pvals=[]
    for j,r in enumerate(discovery,1):
        ledger,accounting,m=evaluate_year(r,source25,raw25,2025); h1=period(ledger,'2025-01-01','2025-07-01'); h2=period(ledger,'2025-07-01','2026-01-01')
        r['signal_accounting_2025']=accounting; r['y2025']=m; r['y2025_h1']={p:econ.stats(h1,p) for p in econ.PROFILES}; r['y2025_h2']={p:econ.stats(h2,p) for p in econ.PROFILES}; r['bootstrap_2025_e1']=day_block_bootstrap(ledger,'E1',r['candidate_id']); pvals.append(r['bootstrap_2025_e1']['p_one_sided'])
        heartbeat(progress,j,max(1,len(discovery)),'confirmation_2025_only',{'discovery_passes':len(discovery)})
    survivors=[]
    for r,q in zip(discovery,bh_qvalues(pvals)):
        r['confirmation_bh_q']=float(q); y=r['y2025']; a=r['y2025_h1']; b=r['y2025_h2']; boot=r['bootstrap_2025_e1']
        ok=y['E1']['trades']>=30 and a['E1']['trades']>=12 and b['E1']['trades']>=12 and y['E1']['net']>0 and a['E1']['net']>0 and b['E1']['net']>0 and y['STRESS']['net']>0 and a['STRESS']['net']>0 and b['STRESS']['net']>0 and y['E1']['ex_best_positive_net']>0 and pf(y['E1'])>1.0 and q<=.05 and boot['p05'] is not None and boot['p05']>0
        r['confirmation_pass']=bool(ok)
        if ok:survivors.append(r)
    result={'schema':1,'phase':'r6-xau-low-turnover-breakout','generated_at_utc':datetime.now(timezone.utc).isoformat(),'protected_2026_opened':False,'scientific_family':'structured_rolling_range_breakout_with_costs','source_hashes':EXPECTED,'grid_size':384,'discovery_frozen_before_2025':True,'discovery_ids_sha256':hashlib.sha256('|'.join(frozen_ids).encode()).hexdigest(),'discovery_pass_count':len(discovery),'survivor_count':len(survivors),'survivors':survivors,'all_candidates':all_candidates,'interpretation':'PASS is pre-OOS evidence only; not an EA and no authorization for protected 2026.'}
    jp=out/'r6_xau_low_turnover_breakout_result.json'; atomic_json(jp,result)
    rows=[{'candidate_id':r['candidate_id'],'lookback_bars':r['lookback_bars'],'buffer_atr':r['buffer_atr'],'horizon_bars':r['horizon_bars'],'session':r['session'],'direction':r['direction_name'],'discovery_pass':r['discovery_pass'],'confirmation_pass':r.get('confirmation_pass',False),'y2024_e1_net':r['y2024']['E1']['net'],'y2024_stress_net':r['y2024']['STRESS']['net'],'y2025_e1_net':r.get('y2025',{}).get('E1',{}).get('net'),'y2025_stress_net':r.get('y2025',{}).get('STRESS',{}).get('net'),'bh_q':r.get('confirmation_bh_q')} for r in all_candidates]
    cp=out/'r6_xau_low_turnover_breakout_candidates.csv'; pd.DataFrame(rows).to_csv(cp,index=False)
    heartbeat(progress,384,384,'complete',{'discovery_passes':len(discovery),'survivors':len(survivors)})
    status='PASS' if survivors else 'FAIL'; summary=f'R6 low-turnover breakout {status}: {len(survivors)}/{len(discovery)} 2024 discovery candidates survive isolated 2025 economic confirmation; 2026 unopened.'
    publish(args.publisher,status,summary,[jp,cp]); print(json.dumps({'status':status,'discovery_passes':len(discovery),'survivors':len(survivors),'protected_2026_opened':False})); return 0
if __name__=='__main__': raise SystemExit(main())
