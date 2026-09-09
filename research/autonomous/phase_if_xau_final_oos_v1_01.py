#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,math,os,struct,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd

START=int(datetime(2026,1,1,tzinfo=timezone.utc).timestamp())
END=int(datetime(2026,9,1,tzinfo=timezone.utc).timestamp())
REC=60

def atomic(p,o):
 p.parent.mkdir(parents=True,exist_ok=True)
 payload=json.dumps(o,indent=2,sort_keys=True)+'\n'; t=p.with_suffix(p.suffix+'.tmp'); last=None
 for _ in range(20):
  try:
   t.write_text(payload,encoding='utf-8'); os.replace(t,p); return
  except PermissionError as e:
   last=e; time.sleep(0.1)
 try:
  p.write_text(payload,encoding='utf-8'); return
 except OSError:
  if last: raise last
  raise
def hb(p,c,t,stage):
 if p: atomic(p,{'completed':c,'total':t,'stage':stage,'updated_at_utc':datetime.now(timezone.utc).isoformat()})
def loadmod(path,name):
 s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def sha256(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def decode(data,pos):
 if pos<0 or pos+REC>len(data): return None
 try:
  ts=struct.unpack_from('<q',data,pos)[0]
  if ts<START or ts>=END or ts%60: return None
  o,h,l,c=struct.unpack_from('<dddd',data,pos+8); tv=struct.unpack_from('<q',data,pos+40)[0]; sp=struct.unpack_from('<i',data,pos+48)[0]; rv=struct.unpack_from('<q',data,pos+52)[0]
  if not all(math.isfinite(x) for x in (o,h,l,c)) or not (100<o<100000 and 100<h<100000 and 100<l<100000 and 100<c<100000): return None
  if h<max(o,c) or l>min(o,c) or h<l or tv<0 or sp < -1 or rv<0: return None
  return {'server_time':datetime.fromtimestamp(ts,tz=timezone.utc).strftime('%Y.%m.%d %H:%M:%S'),'server_epoch':ts,'open':o,'high':h,'low':l,'close':c,'tick_volume':int(tv),'spread':int(sp),'real_volume':int(rv)}
 except: return None
def parse_hcc_bounded(p,progress=None):
 data=p.read_bytes()
 if len(data)<512: raise RuntimeError('2026 HCC too small')
 header=struct.unpack_from('<I',data,0)[0]
 if not 128<=header<=8192: raise RuntimeError(f'implausible HCC header {header}')
 out=[]; seen=set(); pos=header; n=len(data); blocks=0
 while pos+REC<=n:
  found=None; end=min(n-REC,pos+250000); i=pos
  while i<=end:
   r=decode(data,i)
   if r is not None:
    r2=decode(data,i+REC)
    if r2 is not None and 0<=r2['server_epoch']-r['server_epoch']<=14*86400: found=i; break
   i+=1
  if found is None: pos=end+1; continue
  blocks+=1; pos=found; prev=None
  while pos+REC<=n:
   r=decode(data,pos)
   if r is None: break
   t=r['server_epoch']
   if prev is not None and (t<prev or t-prev>14*86400): break
   prev=t
   if t not in seen: out.append(r); seen.add(t)
   pos+=REC
  pos+=1
 out.sort(key=lambda x:x['server_epoch'])
 if len(out)<150000: raise RuntimeError(f'too few Jan-Aug 2026 M1 rows recovered: {len(out)}')
 return out,{'path':str(p),'sha256':sha256(p),'size_bytes':len(data),'header_size':header,'blocks_found':blocks,'rows_in_frozen_window':len(out),'decoded_outcomes_after_end_exclusive':False}
def aggregate(m1):
 rows=[]; key=None; bucket=[]
 def flush(k,b):
  if not b:return
  rows.append({'server_time':datetime.fromtimestamp(k,tz=timezone.utc).strftime('%Y.%m.%d %H:%M:%S'),'server_epoch':k,'open':b[0]['open'],'high':max(x['high'] for x in b),'low':min(x['low'] for x in b),'close':b[-1]['close'],'tick_volume':sum(x['tick_volume'] for x in b),'spread':b[-1]['spread'],'real_volume':sum(x['real_volume'] for x in b)})
 for r in m1:
  k=(r['server_epoch']//300)*300
  if key is None:key=k
  if k!=key: flush(key,bucket); bucket=[]; key=k
  bucket.append(r)
 flush(key,bucket)
 if len(rows)<30000: raise RuntimeError(f'too few M5 rows: {len(rows)}')
 return rows
def read_mask(p):
 z=pd.read_csv(p); req={'mask_start_server_epoch','mask_end_server_epoch'}
 if not req.issubset(z.columns): raise RuntimeError('invalid frozen news mask')
 return [(int(a),int(b)) for a,b in zip(z.mask_start_server_epoch,z.mask_end_server_epoch)]
def clean_m5(rows,intervals):
 out=[]; j=0; ints=sorted(intervals)
 for r in rows:
  t=r['server_epoch']
  while j<len(ints) and ints[j][1]<t:j+=1
  if j<len(ints) and ints[j][0]<=t<=ints[j][1]: continue
  out.append(r)
 return out
def publish(pub,status,summary,arts,cwd):
 if not pub:return
 cmd=[sys.executable,str(pub),'--phase','phase-if-xau-final-oos','--status',status,'--summary',summary]
 for p in arts:
  if p.exists():cmd+=['--artifact',str(p)]
 cp=subprocess.run(cmd,cwd=str(cwd),text=True,capture_output=True,check=False)
 if cp.returncode: raise RuntimeError(cp.stderr.strip() or cp.stdout.strip())

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--hcc',required=True); ap.add_argument('--news-mask',required=True); ap.add_argument('--policy',required=True); ap.add_argument('--ic-engine',required=True); ap.add_argument('--ie-engine',required=True); ap.add_argument('--output-dir',required=True); ap.add_argument('--progress-file'); ap.add_argument('--publisher'); ap.add_argument('--deploy',required=True); a=ap.parse_args()
 policy=json.loads(Path(a.policy).read_text(encoding='utf-8')); out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True); prog=Path(a.progress_file) if a.progress_file else None; pub=Path(a.publisher) if a.publisher else None; deploy=Path(a.deploy)
 if policy.get('status')!='PREREGISTERED_SEALED' or policy.get('phase')!='I-F': raise RuntimeError('invalid sealed I-F policy')
 c=policy['candidate']; gate=policy['single_candidate_final_gate']
 if c['state']!='bar_range_atr:Q5:H4' or float(c['frozen_q5_lower_cutpoint'])!=1.2604033158741452 or c['server_hours']!=[16,17,18,19] or int(c['horizon_bars'])!=12: raise RuntimeError('frozen candidate drift')
 maskp=Path(a.news_mask); hcc=Path(a.hcc)
 if not maskp.exists(): raise RuntimeError('frozen news mask missing')
 hb(prog,0,100,'parse_frozen_hcc'); m1,meta=parse_hcc_bounded(hcc,prog); hb(prog,30,100,'aggregate_m5'); m5=aggregate(m1); intervals=read_mask(maskp); clean=clean_m5(m5,intervals)
 df=pd.DataFrame(clean).sort_values('server_epoch').reset_index(drop=True); ic=loadmod(Path(a.ic_engine),'phase_ic'); ie=loadmod(Path(a.ie_engine),'phase_ie'); hb(prog,50,100,'features_labels'); df=ic.build_features(df); df=ic.add_labels(df,[12])
 vals=df['fwd_ret_atr_h12'].to_numpy(float); state=(df['bar_range_atr'].to_numpy(float)>float(c['frozen_q5_lower_cutpoint'])) & df['server_hour'].isin(c['server_hours']).to_numpy()
 full=ic.continuous_test(vals,state)
 if full is None: raise RuntimeError('full-window test unavailable')
 dt=pd.to_datetime(df.server_time,format='%Y.%m.%d %H:%M:%S'); janapr=(dt<pd.Timestamp('2026-05-01')); mayaug=(dt>=pd.Timestamp('2026-05-01')) & (dt<pd.Timestamp('2026-09-01'))
 sub={}
 for name,pm in [('JAN_APR',janapr.to_numpy()),('MAY_AUG',mayaug.to_numpy())]:
  r=ic.continuous_test(vals[pm],state[pm])
  if r is None: raise RuntimeError(f'{name} test unavailable')
  sub[name]=r
 hb(prog,70,100,'bootstrap'); lo,hi,nboot=ie.block_bootstrap_ci(vals,state,int(gate['moving_block_bootstrap']['block_length_bars']),int(gate['moving_block_bootstrap']['replicates']),0.05,1,int(gate['moving_block_bootstrap']['seed']))
 gates={
  'full_n':int(full['n_state'])>=int(gate['minimum_state_n_full_window']),
  'full_effect':float(full['effect'])<=-0.06,
  'jan_apr_n':int(sub['JAN_APR']['n_state'])>=200,
  'jan_apr_effect':float(sub['JAN_APR']['effect'])<=-0.06,
  'may_aug_n':int(sub['MAY_AUG']['n_state'])>=200,
  'may_aug_effect':float(sub['MAY_AUG']['effect'])<=-0.06,
  'bootstrap_upper_below_zero':float(hi)<0.0,
  'normal_p':float(full['p'])<=0.05,
 }
 status='PASS' if all(gates.values()) else 'FAIL'; result={'schema':1,'phase':'I-F','status':status,'generated_at_utc':datetime.now(timezone.utc).isoformat(),'candidate':c,'hcc_provenance':meta,'news_mask':str(maskp),'news_mask_sha256':sha256(maskp),'m1_rows':len(m1),'m5_rows_raw':len(m5),'m5_rows_news_clean':len(clean),'full':full,'subperiods':sub,'bootstrap':{'ci_low':lo,'ci_high':hi,'valid_reps':nboot,'replicates':5000,'block_length_bars':24,'seed':20260909},'gates':gates,'all_gates_pass':all(gates.values()),'no_retuning_performed':True,'outcomes_after_2026_09_01_decoded':False,'decision':'promote_to_execution_translation' if status=='PASS' else 'close_xau_directional_candidate_family'}
 rp=out/'phase_if_final_oos_result.json'; atomic(rp,result); hb(prog,100,100,'complete'); publish(pub,status,f"Phase I-F frozen XAU final OOS -> {status}; effect={full['effect']:.6f} ATR n={full['n_state']} CI=[{lo:.6f},{hi:.6f}]",[rp,Path(a.policy),maskp],deploy); print(json.dumps(result,sort_keys=True)); return 0 if status=='PASS' else 10
if __name__=='__main__': raise SystemExit(main())
