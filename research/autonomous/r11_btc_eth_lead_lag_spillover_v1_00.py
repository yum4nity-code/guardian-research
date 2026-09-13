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
ASSETS=['BTCUSDT','ETHUSDT']; LOOKBACKS=[1,3,6]; ZTHRESH=[1.5,2.0,2.5]; HOLDS=[1,3,6,12]
VOL_WINDOW=168; LAG_RATIO=0.5; COSTS={'E1':.001,'STRESS':.002}
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
 if p.name not in EXPECTED or sha(p)!=EXPECTED[p.name]: raise RuntimeError(f'input hash mismatch: {p.name}')
 d=pd.read_csv(p); req={'time','open','high','low','close'}
 if not req.issubset(d.columns): raise RuntimeError('missing OHLC')
 z=pd.DataFrame({'time':pd.to_datetime(d.time,utc=True,errors='coerce',format='mixed'),'open':pd.to_numeric(d.open,errors='coerce'),'high':pd.to_numeric(d.high,errors='coerce'),'low':pd.to_numeric(d.low,errors='coerce'),'close':pd.to_numeric(d.close,errors='coerce')}).dropna().sort_values('time').reset_index(drop=True)
 if z.time.duplicated().any(): raise RuntimeError('duplicate timestamps')
 if (z.time>=PROTECTED).any(): raise RuntimeError('protected 2026 row present')
 return z
def h1(d):
 g=d.set_index('time').resample('1h',label='left',closed='left'); y=g.agg({'open':'first','high':'max','low':'min','close':'last'}); c=g.close.count()
 return y.loc[c.eq(12)].dropna().reset_index()
def synchronize(btc,eth):
 b=btc.rename(columns={c:f'BTCUSDT_{c}' for c in ['open','high','low','close']}); e=eth.rename(columns={c:f'ETHUSDT_{c}' for c in ['open','high','low','close']})
 d=b.merge(e,on='time',how='inner',validate='one_to_one').sort_values('time').reset_index(drop=True); hourly=d.time.diff().eq(pd.Timedelta(hours=1))
 for a in ASSETS:
  lr=np.log(d[f'{a}_close']).diff().where(hourly); d[f'{a}_logret1']=lr; d[f'{a}_sigma_prior']=lr.rolling(VOL_WINDOW,min_periods=VOL_WINDOW).std(ddof=1).shift(1)
 return d
def rules():
 return [{'leader':a,'follower':('ETHUSDT' if a=='BTCUSDT' else 'BTCUSDT'),'lookback_hours':l,'leader_z_threshold':z,'hold_hours':h,'lag_ratio':LAG_RATIO,'vol_window_hours':VOL_WINDOW} for a in ASSETS for l in LOOKBACKS for z in ZTHRESH for h in HOLDS]
def cid(r): return 'R11-'+hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:12].upper()
def signal_at(d,i,r):
 if i<r['lookback_hours']: return None
 t=d.time.iloc[i]; j=i-r['lookback_hours']
 if d.time.iloc[j] != t-pd.Timedelta(hours=r['lookback_hours']): return None
 seg=d.time.iloc[j:i+1]
 if len(seg)!=(r['lookback_hours']+1) or seg.diff().dropna().ne(pd.Timedelta(hours=1)).any(): return None
 L=r['leader']; F=r['follower']; sig_l=float(d[f'{L}_sigma_prior'].iloc[i]); sig_f=float(d[f'{F}_sigma_prior'].iloc[i])
 if not np.isfinite(sig_l) or not np.isfinite(sig_f) or sig_l<=0 or sig_f<=0: return None
 lb=r['lookback_hours']; lret=float(np.log(d[f'{L}_close'].iloc[i]/d[f'{L}_close'].iloc[j])); fret=float(np.log(d[f'{F}_close'].iloc[i]/d[f'{F}_close'].iloc[j]))
 lz=lret/(sig_l*math.sqrt(lb)); fz=fret/(sig_f*math.sqrt(lb))
 if abs(lz)<r['leader_z_threshold'] or abs(fz)>r['lag_ratio']*abs(lz): return None
 return {'leader_z':float(lz),'follower_z':float(fz),'direction':1 if lz>0 else -1}
def simulate(d,r):
 idx={t:i for i,t in enumerate(d.time)}; out=[]; next_free=None; hold=r['hold_hours']
 for i in range(len(d)):
  t=d.time.iloc[i]; et=t+pd.Timedelta(hours=1)
  if next_free is not None and et<next_free: continue
  s=signal_at(d,i,r)
  if s is None: continue
  xt=et+pd.Timedelta(hours=hold); ei=idx.get(et); xi=idx.get(xt)
  if ei is None or xi is None or xi<=ei: continue
  path=d.time.iloc[i:xi+1]
  if len(path)!=(hold+2) or path.diff().dropna().ne(pd.Timedelta(hours=1)).any(): continue
  if t.year!=xt.year: continue
  F=r['follower']; gross=s['direction']*float(d[f'{F}_open'].iloc[xi]/d[f'{F}_open'].iloc[ei]-1.0)
  out.append({'decision_bar_time':t,'entry_time':et,'exit_time':xt,'direction':s['direction'],'leader_z':s['leader_z'],'follower_z':s['follower_z'],'gross':gross,'E1':gross-COSTS['E1'],'STRESS':gross-COSTS['STRESS']})
  next_free=xt
 return out
def sub(ts,a,b): return [x for x in ts if a<=x['decision_bar_time']<b]
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
 c=['python',pub,'--phase','r11-btc-eth-lead-lag-spillover','--status',status,'--summary',summary]
 for a in arts:c+=['--artifact',str(a)]
 subprocess.run(c,check=True)

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--data-dir',required=True); ap.add_argument('--output-dir',required=True); ap.add_argument('--progress-file'); ap.add_argument('--publisher'); A=ap.parse_args()
 out=Path(A.output_dir); out.mkdir(parents=True,exist_ok=True); prog=Path(A.progress_file) if A.progress_file else None
 paths={a:Path(A.data_dir)/f'{a}_spot_5m_2017_2025.csv' for a in ASSETS}; hashes={}; hb(prog,0,72,'load')
 raw={}
 for a,p in paths.items(): raw[a]=h1(load(p)); hashes[p.name]=sha(p)
 data=synchronize(raw['BTCUSDT'],raw['ETHUSDT']); R=rules()
 if len(R)!=72 or len({cid(r) for r in R})!=72: raise RuntimeError('rule count/identity mismatch')
 disc=[]
 for n,r in enumerate(R,1):
  ts=simulate(data,r); d=sub(ts,DISC0,DISC1); m=met(d); pos=0; yearly={}
  for y in range(2018,2023):
   ym=met(sub(d,pd.Timestamp(f'{y}-01-01',tz='UTC'),pd.Timestamp(f'{y+1}-01-01',tz='UTC'))); yearly[str(y)]=ym
   if ym['E1']['net_sum'] is not None and ym['E1']['net_sum']>0: pos+=1
  if m['n']>=80 and m['E1']['mean']>0 and m['STRESS']['mean']>0 and pos>=4 and m['E1']['p']<.01: disc.append({'candidate_id':cid(r),'rule':r,'discovery':m,'discovery_yearly':yearly,'positive_discovery_years':pos})
  hb(prog,n,72,'discovery_2018_2022',{'discovery_candidates':len(disc)})
 ids=sorted(x['candidate_id'] for x in disc); dh=hashlib.sha256('|'.join(ids).encode()).hexdigest(); hb(prog,72,72,'discovery_frozen_before_confirmation',{'count':len(ids),'sha256':dh})
 temp=[]; ps=[]
 for c in disc:
  ts=simulate(data,c['rule']); x=sub(ts,DISC1,CONF1); m=met(x); y23=met(sub(x,pd.Timestamp('2023-01-01',tz='UTC'),pd.Timestamp('2024-01-01',tz='UTC'))); y24=met(sub(x,pd.Timestamp('2024-01-01',tz='UTC'),CONF1)); temp.append((c,m,y23,y24)); ps.append(m['E1']['p'] if m['n'] else 1.0)
 qs=bh(ps); conf=[]
 for i,(c,m,y23,y24) in enumerate(temp):
  if m['n']>=30 and m['E1']['mean']>0 and m['STRESS']['mean']>0 and y23['E1']['net_sum'] is not None and y23['E1']['net_sum']>0 and y24['E1']['net_sum'] is not None and y24['E1']['net_sum']>0 and qs[i]<=.05:
   z=dict(c); z.update({'confirmation':m,'confirmation_2023':y23,'confirmation_2024':y24,'confirmation_bh_q':qs[i]}); conf.append(z)
 ids2=sorted(x['candidate_id'] for x in conf); ch=hashlib.sha256('|'.join(ids2).encode()).hexdigest(); hb(prog,72,72,'confirmation_frozen_before_2025',{'count':len(ids2),'sha256':ch})
 surv=[]
 for c in conf:
  ts=simulate(data,c['rule']); y=sub(ts,CONF1,PRE1); m=met(y); h1m=met(sub(y,CONF1,pd.Timestamp('2025-07-01',tz='UTC'))); h2m=met(sub(y,pd.Timestamp('2025-07-01',tz='UTC'),PRE1)); stress=sorted([x['STRESS'] for x in y]); exbest=sum(stress[:-1]) if len(stress)>1 else -1; posvals=[v for v in stress if v>0]; conc=(max(posvals)/sum(posvals)) if posvals and sum(posvals)>0 else 1.0
  if m['n']>=15 and m['E1']['mean']>0 and m['STRESS']['mean']>0 and h1m['E1']['net_sum'] is not None and h1m['E1']['net_sum']>0 and h2m['E1']['net_sum'] is not None and h2m['E1']['net_sum']>0 and exbest>0 and conc<=.35:
   z=dict(c); z.update({'preoos_2025':m,'preoos_h1':h1m,'preoos_h2':h2m,'stress_ex_best_net_sum':float(exbest),'stress_best_positive_concentration':float(conc)}); surv.append(z)
 result={'schema':1,'method':'btc_eth_lead_lag_shock_spillover','generated_at_utc':datetime.now(timezone.utc).isoformat(),'preregistration':'research/autonomous/R11_BTC_ETH_LEAD_LAG_SPILLOVER_PREREGISTRATION_2026_09_13.md','protected_2026_opened':False,'definitions_tested':72,'vol_window_hours':VOL_WINDOW,'lag_ratio':LAG_RATIO,'input_sha256':hashes,'synchronized_h1_rows':len(data),'discovery_candidate_count':len(disc),'discovery_frozen_ids_sha256':dh,'confirmation_candidate_count':len(conf),'confirmation_frozen_ids_sha256':ch,'survivor_count':len(surv),'survivors':surv}
 rp=out/'r11_btc_eth_lead_lag_spillover_result.json'; cp=out/'r11_btc_eth_lead_lag_spillover_survivors.csv'; atomic_json(rp,result); pd.json_normalize(surv).to_csv(cp,index=False)
 hb(prog,72,72,'complete',{'survivors':len(surv)}); status='PASS' if surv else 'FAIL'; summary=f'R11 BTC/ETH lead-lag spillover {status}: {len(surv)} pre-OOS survivors after frozen 2018-22 discovery, 2023-24 confirmation and 2025 gate; 2026 untouched.'; publish(A.publisher,status,summary,[rp,cp]); print(json.dumps({'status':status,'survivors':len(surv),'protected_2026_opened':False})); return 0
if __name__=='__main__': raise SystemExit(main())
