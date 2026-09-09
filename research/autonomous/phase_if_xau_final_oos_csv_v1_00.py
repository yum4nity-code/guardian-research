#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,importlib.util,json,math,os,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
START=int(datetime(2026,1,1,tzinfo=timezone.utc).timestamp()); END=int(datetime(2026,9,1,tzinfo=timezone.utc).timestamp())
def atomic(p,o):
 p.parent.mkdir(parents=True,exist_ok=True); s=json.dumps(o,indent=2,sort_keys=True)+'\n'; t=p.with_suffix(p.suffix+'.tmp')
 for _ in range(20):
  try:t.write_text(s,encoding='utf-8'); os.replace(t,p); return
  except PermissionError: time.sleep(.1)
 p.write_text(s,encoding='utf-8')
def hb(p,c,t,stage):
 if p: atomic(p,{'completed':c,'total':t,'stage':stage,'updated_at_utc':datetime.now(timezone.utc).isoformat()})
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
def aggregate(df):
 df=df.sort_values('server_epoch').copy(); df['bucket']=(df.server_epoch.astype('int64')//300)*300
 g=df.groupby('bucket',sort=True)
 z=pd.DataFrame({'server_epoch':g.server_epoch.first(),'open':g.open.first(),'high':g.high.max(),'low':g.low.min(),'close':g.close.last(),'tick_volume':g.tick_volume.sum(),'spread':g.spread.last(),'real_volume':g.real_volume.sum()}).reset_index(drop=True)
 z['server_time']=pd.to_datetime(z.server_epoch,unit='s',utc=True).dt.strftime('%Y.%m.%d %H:%M:%S'); return z
def mask_clean(df,p):
 m=pd.read_csv(p); ints=sorted((int(a),int(b)) for a,b in zip(m.mask_start_server_epoch,m.mask_end_server_epoch)); keep=[]; j=0
 for t in df.server_epoch.astype('int64'):
  while j<len(ints) and ints[j][1]<t:j+=1
  keep.append(not(j<len(ints) and ints[j][0]<=t<=ints[j][1]))
 return df[np.array(keep,dtype=bool)].reset_index(drop=True)
def publish(pub,status,summary,arts,cwd):
 if not pub:return
 cmd=[sys.executable,str(pub),'--phase','phase-if-xau-final-oos','--status',status,'--summary',summary]
 for p in arts:
  if Path(p).exists(): cmd+=['--artifact',str(p)]
 cp=subprocess.run(cmd,cwd=str(cwd),text=True,capture_output=True,check=False)
 if cp.returncode: raise RuntimeError(cp.stderr.strip() or cp.stdout.strip())
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--csv',required=True); ap.add_argument('--manifest',required=True); ap.add_argument('--news-mask',required=True); ap.add_argument('--policy',required=True); ap.add_argument('--ic-engine',required=True); ap.add_argument('--ie-engine',required=True); ap.add_argument('--output-dir',required=True); ap.add_argument('--progress-file'); ap.add_argument('--publisher'); ap.add_argument('--deploy',required=True); a=ap.parse_args()
 csvp=Path(a.csv); manp=Path(a.manifest); prog=Path(a.progress_file) if a.progress_file else None
 if not csvp.exists() or not manp.exists(): raise RuntimeError('MT5 XAU snapshot missing')
 policy=json.loads(Path(a.policy).read_text()); c=policy['candidate']; gate=policy['single_candidate_final_gate']
 if policy.get('status')!='PREREGISTERED_SEALED' or policy.get('phase')!='I-F': raise RuntimeError('invalid sealed policy')
 if c['state']!='bar_range_atr:Q5:H4' or float(c['frozen_q5_lower_cutpoint'])!=1.2604033158741452 or c['server_hours']!=[16,17,18,19] or int(c['horizon_bars'])!=12: raise RuntimeError('candidate drift')
 md=manifest(manp)
 if md.get('symbol')!='XAUUSD' or md.get('period')!='M1' or md.get('from')!='2026.01.01 00:00:00' or md.get('to_exclusive')!='2026.09.01 00:00:00': raise RuntimeError(f'invalid snapshot manifest: {md}')
 if md.get('terminal_data_path','').lower()!=r'd:\mt5_fundednext'.lower() or md.get('server')!='FundedNext-Server 2': raise RuntimeError(f'wrong terminal/server provenance: {md}')
 hb(prog,10,100,'read_mt5_snapshot'); df=pd.read_csv(csvp)
 req={'server_time','server_epoch','open','high','low','close','tick_volume','spread','real_volume'}
 if not req.issubset(df.columns): raise RuntimeError('snapshot columns invalid')
 for k in ['server_epoch','open','high','low','close','tick_volume','spread','real_volume']: df[k]=pd.to_numeric(df[k],errors='raise')
 df=df[(df.server_epoch>=START)&(df.server_epoch<END)].sort_values('server_epoch').drop_duplicates('server_epoch')
 if len(df)<150000: raise RuntimeError(f'too few M1 rows: {len(df)}')
 if int(df.server_epoch.min())<START or int(df.server_epoch.max())>=END: raise RuntimeError('snapshot window breach')
 hb(prog,30,100,'aggregate_m5'); m5=aggregate(df); clean=mask_clean(m5,a.news_mask)
 if len(clean)<30000: raise RuntimeError(f'too few news-clean M5 rows: {len(clean)}')
 ic=mod(Path(a.ic_engine),'phase_ic'); ie=mod(Path(a.ie_engine),'phase_ie'); hb(prog,50,100,'features_labels'); d=ic.add_labels(ic.build_features(clean.copy()),[12])
 vals=d['fwd_ret_atr_h12'].to_numpy(float); state=(d['bar_range_atr'].to_numpy(float)>float(c['frozen_q5_lower_cutpoint'])) & d['server_hour'].isin(c['server_hours']).to_numpy(); full=ic.continuous_test(vals,state)
 if full is None: raise RuntimeError('full-window test unavailable')
 dt=pd.to_datetime(d.server_time,format='%Y.%m.%d %H:%M:%S'); sub={}
 for name,pm in [('JAN_APR',(dt<pd.Timestamp('2026-05-01')).to_numpy()),('MAY_AUG',((dt>=pd.Timestamp('2026-05-01'))&(dt<pd.Timestamp('2026-09-01'))).to_numpy())]:
  r=ic.continuous_test(vals[pm],state[pm]);
  if r is None: raise RuntimeError(f'{name} unavailable')
  sub[name]=r
 hb(prog,70,100,'bootstrap'); lo,hi,nboot=ie.block_bootstrap_ci(vals,state,int(gate['moving_block_bootstrap']['block_length_bars']),int(gate['moving_block_bootstrap']['replicates']),0.05,1,int(gate['moving_block_bootstrap']['seed']))
 gates={'full_n':int(full['n_state'])>=int(gate['minimum_state_n_full_window']),'full_effect':float(full['effect'])<=-0.06,'jan_apr_n':int(sub['JAN_APR']['n_state'])>=200,'jan_apr_effect':float(sub['JAN_APR']['effect'])<=-0.06,'may_aug_n':int(sub['MAY_AUG']['n_state'])>=200,'may_aug_effect':float(sub['MAY_AUG']['effect'])<=-0.06,'bootstrap_upper_below_zero':float(hi)<0,'normal_p':float(full['p'])<=0.05}
 status='PASS' if all(gates.values()) else 'FAIL'; out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True); result={'schema':1,'phase':'I-F','status':status,'generated_at_utc':datetime.now(timezone.utc).isoformat(),'candidate':c,'snapshot_provenance':{'csv':str(csvp),'csv_sha256':sha(csvp),'manifest':str(manp),'manifest_sha256':sha(manp),'manifest_fields':md,'m1_rows':len(df),'m5_rows_raw':len(m5),'m5_rows_news_clean':len(clean),'outcomes_after_2026_09_01_decoded':False},'news_mask_sha256':sha(a.news_mask),'full':full,'subperiods':sub,'bootstrap':{'ci_low':lo,'ci_high':hi,'valid_reps':nboot,'replicates':5000,'block_length_bars':24,'seed':20260909},'gates':gates,'all_gates_pass':all(gates.values()),'no_retuning_performed':True,'decision':'promote_to_execution_translation' if status=='PASS' else 'close_xau_directional_candidate_family'}
 rp=out/'phase_if_final_oos_result.json'; atomic(rp,result); hb(prog,100,100,'complete'); publish(Path(a.publisher) if a.publisher else None,status,f"Phase I-F frozen XAU final OOS via MT5 snapshot -> {status}; effect={full['effect']:.6f} ATR n={full['n_state']} CI=[{lo:.6f},{hi:.6f}]",[rp,a.policy,a.news_mask,manp],Path(a.deploy)); return 0 if status=='PASS' else 10
if __name__=='__main__': raise SystemExit(main())
