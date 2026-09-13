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
ASSETS=['BTCUSDT','ETHUSDT']; VOL_WINDOWS=[24,72]; CHANNELS=[24,72]; RATIOS=[.50,.70,.90]; HOLDS=[6,12,24]
BASELINE_HOURS=168
COSTS={'E1':.001,'STRESS':.002}
EXPECTED={'BTCUSDT_spot_5m_2017_2025.csv':'75d0d48dcfa7e649192d1eb2c96e89a591aa49bcfac11d394a1f84113264f6e8','ETHUSDT_spot_5m_2017_2025.csv':'21b170675eae6bd2e3d442391e2acb9392abdff443f517b5cb0ee1946a12aa13'}

# Prospectively corrected after R8-R11 methodology audit. Final standards are not lowered:
# phenomenon discovery -> independent confirmation -> economic robustness -> 2025 pre-OOS.

def atomic_json(p,o):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(o,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8'); os.replace(t,p)
def hb(p,d,t,s,e=None):
 if not p:return
 x={'completed':int(d),'total':int(t),'stage':s,'updated_at_utc':datetime.now(timezone.utc).isoformat()}; x.update(e or {}); atomic_json(p,x)
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
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
def rules(): return [{'asset':a,'vol_window_hours':v,'channel_hours':c,'vol_ratio_max':q,'hold_hours':h} for a in ASSETS for v in VOL_WINDOWS for c in CHANNELS for q in RATIOS for h in HOLDS]
def cid(r): return 'R12-'+hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:12].upper()
def simulate(d,r):
 idx={t:i for i,t in enumerate(d.time)}; out=[]; next_free=None
 vw=r['vol_window_hours']; ch=r['channel_hours']; hold=r['hold_hours']; ratio_max=r['vol_ratio_max']
 lr=np.log(d.close/d.close.shift(1)).to_numpy(float); need=max(ch,vw+BASELINE_HOURS+1)
 for i in range(need,len(d)):
  t=d.time.iloc[i]
  if next_free is not None and t<next_free: continue
  hist_start=min(t-pd.Timedelta(hours=ch),t-pd.Timedelta(hours=vw+BASELINE_HOURS+1)); hs=idx.get(hist_start)
  if hs is None: continue
  et=t+pd.Timedelta(hours=1); xt=et+pd.Timedelta(hours=hold); ei=idx.get(et); xi=idx.get(xt)
  if ei is None or xi is None or xi<=ei: continue
  path=d.time.iloc[hs:xi+1]
  if path.empty or path.iloc[0]!=hist_start or path.iloc[-1]!=xt or path.diff().dropna().ne(pd.Timedelta(hours=1)).any(): continue
  recent=lr[i-vw:i]; base=lr[i-vw-BASELINE_HOURS:i-vw]
  if len(recent)!=vw or len(base)!=BASELINE_HOURS or not np.isfinite(recent).all() or not np.isfinite(base).all(): continue
  recent_vol=float(np.std(recent,ddof=1)); baseline_vol=float(np.std(base,ddof=1))
  if baseline_vol<=0 or not np.isfinite(recent_vol) or not np.isfinite(baseline_vol): continue
  vr=recent_vol/baseline_vol
  if vr>ratio_max: continue
  prior=d.iloc[i-ch:i]
  if len(prior)!=ch: continue
  hi=float(prior.high.max()); lo=float(prior.low.min()); close=float(d.close.iloc[i])
  direction=1 if close>hi else (-1 if close<lo else 0)
  if not direction or t.year!=xt.year: continue
  gross=direction*float(d.open.iloc[xi]/d.open.iloc[ei]-1.0)
  out.append({'decision_time':t,'entry_time':et,'exit_time':xt,'direction':direction,'vol_ratio':vr,'channel_high':hi,'channel_low':lo,'gross':gross,'E1':gross-COSTS['E1'],'STRESS':gross-COSTS['STRESS']}); next_free=xt
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
def discovery_gate(m,q,pos_gross_years):
 return m['n']>=75 and m['gross']['mean'] is not None and m['gross']['mean']>0 and pos_gross_years>=3 and q<=.05
def confirmation_gate(m,y23,y24,q):
 return m['n']>=25 and m['gross']['mean'] is not None and m['gross']['mean']>0 and y23['gross']['net_sum'] is not None and y23['gross']['net_sum']>0 and y24['gross']['net_sum'] is not None and y24['gross']['net_sum']>0 and q<=.05
def economic_gate(m):
 return m['E1']['mean'] is not None and m['E1']['mean']>0 and m['STRESS']['mean'] is not None and m['STRESS']['mean']>0
def publish(pub,status,summary,arts):
 if not pub:return
 c=['python',pub,'--phase','r12-btc-eth-compression-breakout','--status',status,'--summary',summary]
 for a in arts:c+=['--artifact',str(a)]
 subprocess.run(c,check=True)

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--data-dir',required=True); ap.add_argument('--output-dir',required=True); ap.add_argument('--progress-file'); ap.add_argument('--publisher'); A=ap.parse_args()
 out=Path(A.output_dir); out.mkdir(parents=True,exist_ok=True); prog=Path(A.progress_file) if A.progress_file else None
 paths={a:Path(A.data_dir)/f'{a}_spot_5m_2017_2025.csv' for a in ASSETS}; data={}; hashes={}; R=rules(); total=len(R)
 if total!=72 or len({cid(r) for r in R})!=72: raise RuntimeError('rule count/identity mismatch')
 hb(prog,0,total,'load')
 for a,p in paths.items(): data[a]=h1(load(p)); hashes[p.name]=sha(p)

 # Discovery computes diagnostics for every definition before selection; costs are diagnostic only here.
 rows=[]; dcache={}; dps=[]
 for n,r in enumerate(R,1):
  ts=simulate(data[r['asset']],r); d=sub(ts,DISC0,DISC1); m=met(d); dcache[cid(r)]=(r,m,ts)
  yearly={}; pos_gross=0
  for y in range(2018,2023):
   ym=met(sub(d,pd.Timestamp(f'{y}-01-01',tz='UTC'),pd.Timestamp(f'{y+1}-01-01',tz='UTC'))); yearly[str(y)]=ym
   if ym['gross']['net_sum'] is not None and ym['gross']['net_sum']>0: pos_gross+=1
  dps.append(m['gross']['p'] if m['n'] else 1.0)
  rows.append({'candidate_id':cid(r),'rule':r,'discovery':m,'discovery_yearly':yearly,'positive_gross_years':pos_gross})
  hb(prog,n,total,'discovery_metrics_2018_2022')
 dqs=bh(dps); disc=[]
 for row,q in zip(rows,dqs):
  row['discovery_bh_q']=q
  row['gate_enough_n']=row['discovery']['n']>=75
  row['gate_gross_positive']=row['discovery']['gross']['mean'] is not None and row['discovery']['gross']['mean']>0
  row['gate_gross_stability']=row['positive_gross_years']>=3
  row['gate_discovery_fdr']=q<=.05
  row['gate_e1_positive_diagnostic']=row['discovery']['E1']['mean'] is not None and row['discovery']['E1']['mean']>0
  row['gate_stress_positive_diagnostic']=row['discovery']['STRESS']['mean'] is not None and row['discovery']['STRESS']['mean']>0
  row['discovery_pass']=discovery_gate(row['discovery'],q,row['positive_gross_years'])
  if row['discovery_pass']: disc.append(row)
 ids=sorted(x['candidate_id'] for x in disc); dh=hashlib.sha256('|'.join(ids).encode()).hexdigest(); hb(prog,total,total,'discovery_frozen_before_confirmation',{'count':len(ids),'sha256':dh})

 # Independent confirmation remains gross/statistical; no cost gate yet.
 conf_temp=[]; cps=[]
 for c in disc:
  ts=dcache[c['candidate_id']][2]; x=sub(ts,DISC1,CONF1); m=met(x); y23=met(sub(x,pd.Timestamp('2023-01-01',tz='UTC'),pd.Timestamp('2024-01-01',tz='UTC'))); y24=met(sub(x,pd.Timestamp('2024-01-01',tz='UTC'),CONF1)); conf_temp.append((c,m,y23,y24)); cps.append(m['gross']['p'] if m['n'] else 1.0)
 cqs=bh(cps); confirmed=[]
 for q,(c,m,y23,y24) in zip(cqs,conf_temp):
  passed=confirmation_gate(m,y23,y24,q); c['confirmation']=m; c['confirmation_2023']=y23; c['confirmation_2024']=y24; c['confirmation_bh_q']=q; c['confirmation_pass']=passed
  if passed: confirmed.append(c)
 ids2=sorted(x['candidate_id'] for x in confirmed); chash=hashlib.sha256('|'.join(ids2).encode()).hexdigest(); hb(prog,total,total,'confirmation_frozen_before_economic',{'count':len(ids2),'sha256':chash})

 # Economic robustness is downstream of independent confirmation.
 econ=[]
 for c in confirmed:
  m=c['confirmation']; c['economic_e1_positive']=m['E1']['mean'] is not None and m['E1']['mean']>0; c['economic_stress_positive']=m['STRESS']['mean'] is not None and m['STRESS']['mean']>0; c['economic_pass']=economic_gate(m)
  if c['economic_pass']: econ.append(c)
 ids3=sorted(x['candidate_id'] for x in econ); ehash=hashlib.sha256('|'.join(ids3).encode()).hexdigest(); hb(prog,total,total,'economic_frozen_before_2025',{'count':len(ids3),'sha256':ehash})

 surv=[]
 for c in econ:
  ts=dcache[c['candidate_id']][2]; y=sub(ts,CONF1,PRE1); m=met(y); h1m=met(sub(y,CONF1,pd.Timestamp('2025-07-01',tz='UTC'))); h2m=met(sub(y,pd.Timestamp('2025-07-01',tz='UTC'),PRE1)); stress=sorted([x['STRESS'] for x in y]); exbest=sum(stress[:-1]) if len(stress)>1 else -1; posvals=[v for v in stress if v>0]; conc=(max(posvals)/sum(posvals)) if posvals and sum(posvals)>0 else 1.0
  if m['n']>=10 and economic_gate(m) and h1m['E1']['net_sum'] is not None and h1m['E1']['net_sum']>0 and h2m['E1']['net_sum'] is not None and h2m['E1']['net_sum']>0 and exbest>0 and conc<=.35:
   z=dict(c); z.update({'preoos_2025':m,'preoos_h1':h1m,'preoos_h2':h2m,'stress_ex_best_net_sum':float(exbest),'stress_best_positive_concentration':float(conc)}); surv.append(z)

 funnel={'tested':total,'enough_n':sum(r['gate_enough_n'] for r in rows),'gross_positive':sum(r['gate_gross_positive'] for r in rows),'gross_stability':sum(r['gate_gross_stability'] for r in rows),'discovery_fdr':sum(r['gate_discovery_fdr'] for r in rows),'discovery_pass':len(disc),'confirmation_pass':len(confirmed),'economic_pass':len(econ),'preoos_survivors':len(surv)}
 diag=[]
 for r in rows:
  diag.append({'candidate_id':r['candidate_id'],**r['rule'],'n':r['discovery']['n'],'gross_mean':r['discovery']['gross']['mean'],'gross_p':r['discovery']['gross']['p'],'discovery_bh_q':r['discovery_bh_q'],'e1_mean':r['discovery']['E1']['mean'],'stress_mean':r['discovery']['STRESS']['mean'],'positive_gross_years':r['positive_gross_years'],'gate_enough_n':r['gate_enough_n'],'gate_gross_positive':r['gate_gross_positive'],'gate_gross_stability':r['gate_gross_stability'],'gate_discovery_fdr':r['gate_discovery_fdr'],'discovery_pass':r['discovery_pass']})
 result={'schema':2,'method':'btc_eth_volatility_compression_channel_breakout','architecture':'phenomenon_then_confirmation_then_economic_then_preoos','generated_at_utc':datetime.now(timezone.utc).isoformat(),'preregistration':'research/autonomous/R12_BTC_ETH_COMPRESSION_BREAKOUT_PREREGISTRATION_2026_09_13_AMENDMENT.md','protected_2026_opened':False,'definitions_tested':total,'input_sha256':hashes,'baseline_hours':BASELINE_HOURS,'funnel':funnel,'discovery_candidate_count':len(disc),'discovery_frozen_ids_sha256':dh,'confirmation_candidate_count':len(confirmed),'confirmation_frozen_ids_sha256':chash,'economic_candidate_count':len(econ),'economic_frozen_ids_sha256':ehash,'survivor_count':len(surv),'survivors':surv}
 rp=out/'r12_btc_eth_compression_breakout_result.json'; cp=out/'r12_btc_eth_compression_breakout_survivors.csv'; dp=out/'r12_btc_eth_compression_breakout_discovery_diagnostics.csv'; atomic_json(rp,result); pd.json_normalize(surv).to_csv(cp,index=False); pd.DataFrame(diag).to_csv(dp,index=False)
 hb(prog,total,total,'complete',{'survivors':len(surv),'funnel':funnel}); status='PASS' if surv else 'FAIL'; summary=f"R12 compression breakout {status}: funnel {funnel}; 2026 untouched."; publish(A.publisher,status,summary,[rp,cp,dp]); print(json.dumps({'status':status,'survivors':len(surv),'funnel':funnel,'protected_2026_opened':False})); return 0
if __name__=='__main__': raise SystemExit(main())
