#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, os, subprocess
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

PROTECTED=pd.Timestamp('2026-01-01',tz='UTC')
DISC0=pd.Timestamp('2018-01-01',tz='UTC'); DISC1=pd.Timestamp('2023-01-01',tz='UTC')
CONF1=pd.Timestamp('2025-01-01',tz='UTC'); PRE1=PROTECTED
ASSETS=['BTCUSDT','ETHUSDT']; CHANNELS=[24,72,168]; PEN=[0.0,0.05]; REENTRY=[0.0,0.10]; HOLDS=[3,6,12]
COSTS={'E1':.001,'STRESS':.002}
EXPECTED={'BTCUSDT_spot_5m_2017_2025.csv':'75d0d48dcfa7e649192d1eb2c96e89a591aa49bcfac11d394a1f84113264f6e8','ETHUSDT_spot_5m_2017_2025.csv':'21b170675eae6bd2e3d442391e2acb9392abdff443f517b5cb0ee1946a12aa13'}

def atomic_json(p,o):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(o,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8'); os.replace(t,p)
def hb(p,d,t,s,e=None):
 if not p:return
 x={'completed':int(d),'total':int(t),'stage':s,'updated_at_utc':datetime.now(timezone.utc).isoformat()}; x.update(e or {}); atomic_json(p,x)
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def load(p):
 p=Path(p)
 if '2026' in p.name: raise RuntimeError('protected filename forbidden')
 if p.name not in EXPECTED: raise RuntimeError(f'unexpected input file: {p.name}')
 if sha(p)!=EXPECTED[p.name]: raise RuntimeError(f'input hash mismatch: {p.name}')
 d=pd.read_csv(p); req={'time','open','high','low','close'}
 if not req.issubset(d.columns): raise RuntimeError('missing OHLC')
 z=pd.DataFrame({'time':pd.to_datetime(d.time,utc=True,errors='coerce',format='mixed'),'open':pd.to_numeric(d.open,errors='coerce'),'high':pd.to_numeric(d.high,errors='coerce'),'low':pd.to_numeric(d.low,errors='coerce'),'close':pd.to_numeric(d.close,errors='coerce')}).dropna().sort_values('time').reset_index(drop=True)
 if z.time.duplicated().any(): raise RuntimeError('duplicate timestamps')
 if (z.time>=PROTECTED).any(): raise RuntimeError('protected 2026 row present')
 return z
def h1(d):
 g=d.set_index('time').resample('1h',label='left',closed='left'); y=g.agg({'open':'first','high':'max','low':'min','close':'last'}); c=g.close.count(); return y.loc[c.eq(12)].dropna().reset_index()
def rules(): return [{'asset':a,'channel_hours':c,'penetration_frac':p,'reentry_frac':r,'hold_hours':h} for a in ASSETS for c in CHANNELS for p in PEN for r in REENTRY for h in HOLDS]
def cid(r): return 'R13-'+hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:12].upper()
def simulate(d,r):
 idx={t:i for i,t in enumerate(d.time)}; out=[]; next_free=None; ch=r['channel_hours']; hold=r['hold_hours']; pen=r['penetration_frac']; re=r['reentry_frac']
 for i in range(ch,len(d)):
  t=d.time.iloc[i]
  if next_free is not None and t<next_free: continue
  hist_start=t-pd.Timedelta(hours=ch); hs=idx.get(hist_start)
  et=t+pd.Timedelta(hours=1); xt=et+pd.Timedelta(hours=hold); ei=idx.get(et); xi=idx.get(xt)
  if hs is None or ei is None or xi is None or xi<=ei: continue
  path=d.time.iloc[hs:xi+1]
  if path.empty or path.iloc[0]!=hist_start or path.iloc[-1]!=xt or path.diff().dropna().ne(pd.Timedelta(hours=1)).any(): continue
  prior=d.iloc[i-ch:i]
  if len(prior)!=ch: continue
  hi=float(prior.high.max()); lo=float(prior.low.min()); rng=hi-lo
  if not np.isfinite(rng) or rng<=0: continue
  dh=float(d.high.iloc[i]); dl=float(d.low.iloc[i]); dc=float(d.close.iloc[i])
  upper=(dh>hi+pen*rng) and (dc<=hi-re*rng)
  lower=(dl<lo-pen*rng) and (dc>=lo+re*rng)
  if upper==lower: continue
  direction=-1 if upper else 1
  if t.year!=xt.year: continue
  gross=direction*float(d.open.iloc[xi]/d.open.iloc[ei]-1.0)
  out.append({'decision_time':t,'entry_time':et,'exit_time':xt,'direction':direction,'channel_high':hi,'channel_low':lo,'channel_range':rng,'gross':gross,'E1':gross-COSTS['E1'],'STRESS':gross-COSTS['STRESS']})
  next_free=xt
 return out
def sub(ts,a,b): return [x for x in ts if a<=x['decision_time']<b]
def pval(v):
 a=np.asarray(v,float)
 if len(a)<2:return 1.0
 sd=float(a.std(ddof=1)); mu=float(a.mean())
 if sd<=0:return 0.0 if mu else 1.0
 return float(math.erfc(abs(mu/(sd/math.sqrt(len(a))))/math.sqrt(2)))
def met(ts):
 o={'n':len(ts)}
 for k in ('gross','E1','STRESS'):
  a=np.asarray([x[k] for x in ts],float); o[k]={'mean':float(a.mean()) if len(a) else None,'net_sum':float(a.sum()) if len(a) else None,'p':pval(a) if len(a) else 1.0}
 return o
def bh(ps):
 n=len(ps)
 if not n:return []
 order=np.argsort(ps); q=np.ones(n); prev=1.0
 for j in range(n-1,-1,-1):
  i=int(order[j]); prev=min(prev,float(ps[i])*n/(j+1)); q[i]=prev
 return q.tolist()
def publish(pub,status,summary,arts):
 if not pub:return
 c=['python',pub,'--phase','r13-btc-eth-failed-breakout-rejection','--status',status,'--summary',summary]
 for a in arts:c+=['--artifact',str(a)]
 subprocess.run(c,check=True)

def discovery_gate(m,q,pos_gross_years):
 return m['n']>=75 and m['gross']['mean'] is not None and m['gross']['mean']>0 and pos_gross_years>=3 and q<=.05

def confirmation_gate(m,y23,y24,q):
 return (
  m['n']>=25 and
  m['gross']['mean'] is not None and m['gross']['mean']>0 and
  y23['gross']['net_sum'] is not None and y23['gross']['net_sum']>0 and
  y24['gross']['net_sum'] is not None and y24['gross']['net_sum']>0 and
  q<=.05
 )

def economic_gate(m):
 return (
  m['E1']['mean'] is not None and m['E1']['mean']>0 and
  m['STRESS']['mean'] is not None and m['STRESS']['mean']>0
 )

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--data-dir',required=True)
 ap.add_argument('--output-dir',required=True)
 ap.add_argument('--progress-file')
 ap.add_argument('--publisher')
 A=ap.parse_args()

 out=Path(A.output_dir)
 out.mkdir(parents=True,exist_ok=True)
 prog=Path(A.progress_file) if A.progress_file else None

 paths={a:Path(A.data_dir)/f'{a}_spot_5m_2017_2025.csv' for a in ASSETS}
 data={}
 hashes={}
 R=rules()
 total=len(R)

 if total!=72 or len({cid(r) for r in R})!=72:
  raise RuntimeError('rule count/identity mismatch')

 hb(prog,0,total,'load')

 for a,p in paths.items():
  data[a]=h1(load(p))
  hashes[p.name]=sha(p)

 # ------------------------------------------------------------
 # STAGE 1 — DISCOVERY
 # Gross phenomenon only.
 # E1/STRESS are retained as diagnostics but are NOT selection gates.
 # ------------------------------------------------------------

 rows=[]
 cache={}
 gross_ps=[]

 for n,r in enumerate(R,1):
  ts=simulate(data[r['asset']],r)
  cache[cid(r)]=ts

  d=sub(ts,DISC0,DISC1)
  m=met(d)

  yearly={}
  pos_gross_years=0

  for y in range(2018,2023):
   ym=met(
    sub(
     d,
     pd.Timestamp(f'{y}-01-01',tz='UTC'),
     pd.Timestamp(f'{y+1}-01-01',tz='UTC')
    )
   )
   yearly[str(y)]=ym

   if ym['gross']['net_sum'] is not None and ym['gross']['net_sum']>0:
    pos_gross_years+=1

  gross_ps.append(m['gross']['p'] if m['n'] else 1.0)

  rows.append({
   'candidate_id':cid(r),
   'rule':r,
   'discovery':m,
   'discovery_yearly':yearly,
   'positive_gross_years':pos_gross_years
  })

  hb(prog,n,total,'discovery_metrics_2018_2022')

 dqs=bh(gross_ps)
 disc=[]

 for row,q in zip(rows,dqs):
  row['discovery_bh_q']=q

  row['gate_enough_n']=row['discovery']['n']>=75

  row['gate_gross_positive']=(
   row['discovery']['gross']['mean'] is not None and
   row['discovery']['gross']['mean']>0
  )

  row['gate_gross_stability']=row['positive_gross_years']>=3
  row['gate_discovery_fdr']=q<=.05

  # Diagnostic only — explicitly NOT discovery selection gates.
  row['diagnostic_e1_positive']=(
   row['discovery']['E1']['mean'] is not None and
   row['discovery']['E1']['mean']>0
  )

  row['diagnostic_stress_positive']=(
   row['discovery']['STRESS']['mean'] is not None and
   row['discovery']['STRESS']['mean']>0
  )

  row['discovery_pass']=discovery_gate(
   row['discovery'],
   q,
   row['positive_gross_years']
  )

  if row['discovery_pass']:
   disc.append(row)

 disc_ids=sorted(x['candidate_id'] for x in disc)
 disc_hash=hashlib.sha256('|'.join(disc_ids).encode()).hexdigest()

 hb(
  prog,total,total,
  'discovery_frozen_before_confirmation',
  {'count':len(disc_ids),'sha256':disc_hash}
 )

 # ------------------------------------------------------------
 # STAGE 2 — INDEPENDENT CONFIRMATION
 # Still gross/statistical. No cost rescue or cost selection.
 # ------------------------------------------------------------

 conf_temp=[]
 conf_ps=[]

 for c in disc:
  ts=cache[c['candidate_id']]
  x=sub(ts,DISC1,CONF1)

  m=met(x)

  y23=met(
   sub(
    x,
    pd.Timestamp('2023-01-01',tz='UTC'),
    pd.Timestamp('2024-01-01',tz='UTC')
   )
  )

  y24=met(
   sub(
    x,
    pd.Timestamp('2024-01-01',tz='UTC'),
    CONF1
   )
  )

  conf_temp.append((c,m,y23,y24))
  conf_ps.append(m['gross']['p'] if m['n'] else 1.0)

 conf_qs=bh(conf_ps)
 confirmed=[]

 for q,(c,m,y23,y24) in zip(conf_qs,conf_temp):
  z=dict(c)

  z.update({
   'confirmation':m,
   'confirmation_2023':y23,
   'confirmation_2024':y24,
   'confirmation_bh_q':q,
   'confirmation_pass':confirmation_gate(m,y23,y24,q)
  })

  if z['confirmation_pass']:
   confirmed.append(z)

 conf_ids=sorted(x['candidate_id'] for x in confirmed)
 conf_hash=hashlib.sha256('|'.join(conf_ids).encode()).hexdigest()

 hb(
  prog,total,total,
  'confirmation_frozen_before_economic',
  {'count':len(conf_ids),'sha256':conf_hash}
 )

 # ------------------------------------------------------------
 # STAGE 3 — ECONOMIC ROBUSTNESS
 # Costs enter only here.
 # ------------------------------------------------------------

 econ=[]

 for c in confirmed:
  z=dict(c)
  m=z['confirmation']

  z['economic_e1_positive']=(
   m['E1']['mean'] is not None and m['E1']['mean']>0
  )

  z['economic_stress_positive']=(
   m['STRESS']['mean'] is not None and m['STRESS']['mean']>0
  )

  z['economic_pass']=economic_gate(m)

  if z['economic_pass']:
   econ.append(z)

 econ_ids=sorted(x['candidate_id'] for x in econ)
 econ_hash=hashlib.sha256('|'.join(econ_ids).encode()).hexdigest()

 hb(
  prog,total,total,
  'economic_frozen_before_2025',
  {'count':len(econ_ids),'sha256':econ_hash}
 )

 # ------------------------------------------------------------
 # STAGE 4 — 2025 PRE-OOS
 # Exact frozen candidates. No retuning.
 # ------------------------------------------------------------

 survivors=[]

 for c in econ:
  ts=cache[c['candidate_id']]
  y=sub(ts,CONF1,PRE1)

  m=met(y)

  h1m=met(
   sub(
    y,
    CONF1,
    pd.Timestamp('2025-07-01',tz='UTC')
   )
  )

  h2m=met(
   sub(
    y,
    pd.Timestamp('2025-07-01',tz='UTC'),
    PRE1
   )
  )

  stress=sorted([x['STRESS'] for x in y])

  exbest=sum(stress[:-1]) if len(stress)>1 else -1

  posvals=[v for v in stress if v>0]

  conc=(
   max(posvals)/sum(posvals)
   if posvals and sum(posvals)>0
   else 1.0
  )

  preoos_pass=(
   m['n']>=10 and
   economic_gate(m) and
   h1m['E1']['net_sum'] is not None and
   h1m['E1']['net_sum']>0 and
   h2m['E1']['net_sum'] is not None and
   h2m['E1']['net_sum']>0 and
   exbest>0 and
   conc<=.35
  )

  if preoos_pass:
   z=dict(c)

   z.update({
    'preoos_2025':m,
    'preoos_h1':h1m,
    'preoos_h2':h2m,
    'stress_ex_best_net_sum':float(exbest),
    'stress_best_positive_concentration':float(conc),
    'preoos_pass':True
   })

   survivors.append(z)

 # ------------------------------------------------------------
 # AUDITABLE FUNNEL
 # ------------------------------------------------------------

 funnel={
  'tested':total,
  'enough_n':sum(int(r['gate_enough_n']) for r in rows),
  'gross_positive':sum(int(r['gate_gross_positive']) for r in rows),
  'gross_stability':sum(int(r['gate_gross_stability']) for r in rows),
  'discovery_fdr':sum(int(r['gate_discovery_fdr']) for r in rows),
  'discovery_pass':len(disc),
  'confirmation_pass':len(confirmed),
  'economic_pass':len(econ),
  'preoos_survivors':len(survivors)
 }

 diagnostics=[]

 for r in rows:
  diagnostics.append({
   'candidate_id':r['candidate_id'],
   **r['rule'],
   'n':r['discovery']['n'],
   'gross_mean':r['discovery']['gross']['mean'],
   'gross_p':r['discovery']['gross']['p'],
   'discovery_bh_q':r['discovery_bh_q'],
   'e1_mean':r['discovery']['E1']['mean'],
   'stress_mean':r['discovery']['STRESS']['mean'],
   'positive_gross_years':r['positive_gross_years'],
   'gate_enough_n':r['gate_enough_n'],
   'gate_gross_positive':r['gate_gross_positive'],
   'gate_gross_stability':r['gate_gross_stability'],
   'gate_discovery_fdr':r['gate_discovery_fdr'],
   'discovery_pass':r['discovery_pass']
  })

 result={
  'schema':2,
  'method':'btc_eth_failed_breakout_rejection',
  'architecture':'phenomenon_then_confirmation_then_economic_then_preoos',
  'generated_at_utc':datetime.now(timezone.utc).isoformat(),
  'source_revision':'R13-v1.01',
  'protected_2026_opened':False,
  'definitions_tested':total,
  'input_sha256':hashes,
  'funnel':funnel,
  'discovery_candidate_count':len(disc),
  'discovery_frozen_ids_sha256':disc_hash,
  'confirmation_candidate_count':len(confirmed),
  'confirmation_frozen_ids_sha256':conf_hash,
  'economic_candidate_count':len(econ),
  'economic_frozen_ids_sha256':econ_hash,
  'survivor_count':len(survivors),
  'survivors':survivors
 }

 rp=out/'r13_btc_eth_failed_breakout_rejection_v1_01_result.json'
 cp=out/'r13_btc_eth_failed_breakout_rejection_v1_01_survivors.csv'
 dp=out/'r13_btc_eth_failed_breakout_rejection_v1_01_discovery_diagnostics.csv'

 atomic_json(rp,result)
 pd.json_normalize(survivors).to_csv(cp,index=False)
 pd.DataFrame(diagnostics).to_csv(dp,index=False)

 hb(
  prog,total,total,'complete',
  {
   'tested':funnel['tested'],
   'discovery_candidates':funnel['discovery_pass'],
   'confirmation_candidates':funnel['confirmation_pass'],
   'economic_candidates':funnel['economic_pass'],
   'pre_oos_survivors':funnel['preoos_survivors'],
   'survivors':len(survivors)
  }
 )

 status='PASS' if survivors else 'FAIL'

 summary=(
  f'R13 v1.01 BTC/ETH failed-breakout rejection {status}: '
  f'{len(survivors)} pre-OOS survivors; '
  f'funnel={funnel}; protected 2026 untouched.'
 )

 publish(A.publisher,status,summary,[rp,cp,dp])

 print(json.dumps({
  'status':status,
  'funnel':funnel,
  'survivors':len(survivors),
  'protected_2026_opened':False
 }))

 return 0

if __name__=='__main__':
 raise SystemExit(main())
