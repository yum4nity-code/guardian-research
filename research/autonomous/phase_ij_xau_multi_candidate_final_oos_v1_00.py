#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

START=int(datetime(2026,1,1,tzinfo=timezone.utc).timestamp()); END=int(datetime(2026,9,1,tzinfo=timezone.utc).timestamp())

def atomic(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); s=json.dumps(o,indent=2,sort_keys=True)+'\n'; t=p.with_suffix(p.suffix+'.tmp')
    for _ in range(20):
        try: t.write_text(s,encoding='utf-8'); os.replace(t,p); return
        except PermissionError: time.sleep(.1)
    p.write_text(s,encoding='utf-8')
def hb(p,c,t,s):
    if p: atomic(p,{"completed":c,"total":t,"stage":s,"updated_at_utc":datetime.now(timezone.utc).isoformat()})
def sha(p):
    h=hashlib.sha256();
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def mod(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def manifest(p):
    d={}
    for ln in Path(p).read_text(encoding='utf-8',errors='ignore').splitlines():
        if '=' in ln:
            k,v=ln.split('=',1); d[k.strip()]=v.strip()
    return d
def mask_clean(df,p):
    m=pd.read_csv(p); ints=sorted((int(a),int(b)) for a,b in zip(m.mask_start_server_epoch,m.mask_end_server_epoch)); keep=[]; j=0
    for t in df.server_epoch.astype('int64'):
        while j<len(ints) and ints[j][1]<t: j+=1
        keep.append(not(j<len(ints) and ints[j][0]<=t<=ints[j][1]))
    return df[np.array(keep,dtype=bool)].reset_index(drop=True)
def holm_pass(ps,alpha=.05):
    order=sorted(range(len(ps)),key=lambda i: ps[i]); passed=[False]*len(ps)
    for rank,i in enumerate(order):
        thr=alpha/(len(ps)-rank)
        if ps[i] <= thr: passed[i]=True
        else: break
    return passed
def publish(pub,status,summary,arts,cwd):
    if not pub:return
    cmd=[sys.executable,str(pub),'--phase','phase-ij-xau-multi-final-oos','--status',status,'--summary',summary]
    for p in arts:
        if Path(p).exists(): cmd += ['--artifact',str(p)]
    cp=subprocess.run(cmd,cwd=str(cwd),text=True,capture_output=True,check=False)
    if cp.returncode: raise RuntimeError(cp.stderr.strip() or cp.stdout.strip())
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--csv',required=True); ap.add_argument('--manifest',required=True); ap.add_argument('--news-mask',required=True); ap.add_argument('--policy',required=True); ap.add_argument('--ic-engine',required=True); ap.add_argument('--ie-engine',required=True); ap.add_argument('--output-dir',required=True); ap.add_argument('--progress-file'); ap.add_argument('--publisher'); ap.add_argument('--deploy',required=True); a=ap.parse_args()
    pol=json.loads(Path(a.policy).read_text(encoding='utf-8')); gate=pol['gate']; prog=Path(a.progress_file) if a.progress_file else None
    if pol.get('status')!='PREREGISTERED_SEALED' or pol.get('phase')!='I-J' or len(pol.get('candidates',[]))!=7: raise RuntimeError('invalid sealed policy')
    md=manifest(a.manifest)
    if md.get('symbol')!='XAUUSD' or md.get('period')!='M5' or md.get('from')!='2026.01.01 00:00:00' or md.get('to_exclusive')!='2026.09.01 00:00:00' or md.get('server')!='FundedNext-Server 2': raise RuntimeError('invalid snapshot provenance')
    hb(prog,5,100,'load_snapshot'); df=pd.read_csv(a.csv)
    req={'server_time','server_epoch','open','high','low','close','tick_volume','spread','real_volume'}
    if not req.issubset(df.columns): raise RuntimeError('snapshot columns invalid')
    for k in ['server_epoch','open','high','low','close','tick_volume','spread','real_volume']: df[k]=pd.to_numeric(df[k],errors='raise')
    df=df[(df.server_epoch>=START)&(df.server_epoch<END)].sort_values('server_epoch').drop_duplicates('server_epoch')
    if len(df)<30000: raise RuntimeError('too few M5 rows')
    hb(prog,20,100,'apply_news_mask'); clean=mask_clean(df,a.news_mask)
    ic=mod(a.ic_engine,'ic'); ie=mod(a.ie_engine,'ie')
    horizons=sorted(set(int(c['horizon_bars']) for c in pol['candidates']))
    hb(prog,35,100,'features_labels'); d=ic.add_labels(ic.build_features(clean.copy()),horizons); dt=pd.to_datetime(d.server_time,format='%Y.%m.%d %H:%M:%S')
    raw=[]
    for idx,c in enumerate(pol['candidates']):
        vals=d[f"fwd_ret_atr_h{int(c['horizon_bars'])}"].to_numpy(float); feat=d[c['feature']].to_numpy(float); hours=d['server_hour'].isin(c['server_hours']).to_numpy()
        state=((feat>float(c['cutpoint'])) if c['operator']=='>' else (feat<=float(c['cutpoint']))) & hours
        full=ic.continuous_test(vals,state)
        if full is None: raise RuntimeError(f"test unavailable {c['id']}")
        halves={}
        for name,pm in [('JAN_APR',(dt<pd.Timestamp('2026-05-01')).to_numpy()),('MAY_AUG',((dt>=pd.Timestamp('2026-05-01'))&(dt<pd.Timestamp('2026-09-01'))).to_numpy())]:
            r=ic.continuous_test(vals[pm],state[pm])
            if r is None: raise RuntimeError(f"half unavailable {c['id']} {name}")
            halves[name]=r
        lo,hi,nboot=ie.block_bootstrap_ci(vals,state,int(gate['moving_block_bootstrap']['block_length_bars']),int(gate['moving_block_bootstrap']['replicates']),0.05,int(c['direction']),int(gate['moving_block_bootstrap']['seed'])+idx)
        raw.append({'candidate':c,'full':full,'halves':halves,'bootstrap':{'ci_low':lo,'ci_high':hi,'valid_reps':nboot}})
        hb(prog,40+int(40*(idx+1)/len(pol['candidates'])),100,'candidate_tests')
    hp=holm_pass([float(r['full']['p']) for r in raw],float(gate['normal_p_max']))
    passed=[]
    for r,hpass in zip(raw,hp):
        c=r['candidate']; sign=int(c['direction']); full=float(r['full']['effect']); h1=float(r['halves']['JAN_APR']['effect']); h2=float(r['halves']['MAY_AUG']['effect']); lo=float(r['bootstrap']['ci_low']); hi=float(r['bootstrap']['ci_high'])
        g={
          'full_n': int(r['full']['n_state'])>=int(gate['minimum_state_n_full_window']),
          'full_effect': sign*full>=float(gate['minimum_absolute_full_effect_atr']),
          'jan_apr_n': int(r['halves']['JAN_APR']['n_state'])>=int(gate['minimum_state_n_each_half']),
          'may_aug_n': int(r['halves']['MAY_AUG']['n_state'])>=int(gate['minimum_state_n_each_half']),
          'jan_apr_effect': sign*h1>=float(gate['minimum_absolute_half_effect_atr']),
          'may_aug_effect': sign*h2>=float(gate['minimum_absolute_half_effect_atr']),
          'normal_p': float(r['full']['p'])<=float(gate['normal_p_max']),
          'holm_pass': bool(hpass),
          'bootstrap_ci': (lo>0 if sign>0 else hi<0)
        }
        r['gates']=g; r['status']='PASS' if all(g.values()) else 'FAIL'; passed.append(r['status']=='PASS')
    hb(prog,90,100,'write_results'); out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    result={'schema':1,'phase':'I-J','generated_at_utc':datetime.now(timezone.utc).isoformat(),'status':'PASS' if any(passed) else 'FAIL','candidate_results':raw,'passed_candidate_ids':[r['candidate']['id'] for r in raw if r['status']=='PASS'],'failed_candidate_ids':[r['candidate']['id'] for r in raw if r['status']=='FAIL'],'snapshot_provenance':{'csv_sha256':sha(a.csv),'manifest_sha256':sha(a.manifest),'news_mask_sha256':sha(a.news_mask),'m5_rows_raw':len(df),'m5_rows_news_clean':len(clean),'outcomes_after_2026_09_01_decoded':False},'no_retuning_performed':True,'decision':'advance_passed_candidates_to_execution_translation' if any(passed) else 'close_all_seven_candidates'}
    rp=out/'phase_ij_multi_final_oos_result.json'; atomic(rp,result); hb(prog,100,100,'complete')
    summary=f"Phase I-J seven-candidate protected OOS -> {result['status']}; passed={len(result['passed_candidate_ids'])}/7"
    publish(a.publisher,result['status'],summary,[rp,a.policy,a.news_mask,a.manifest],a.deploy)
    return 0 if any(passed) else 10
if __name__=='__main__': raise SystemExit(main())
