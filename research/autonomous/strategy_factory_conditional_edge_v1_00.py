#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, os, random, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

PROTECTED = pd.Timestamp('2026-01-01', tz='UTC')
TAIL_Q = [.05,.10,.20,.30]
HORIZONS = [1,3,6,12,24,48]


def atomic_json(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    for attempt,delay in enumerate((0.05,0.10,0.20,0.40,0.80,1.00)):
        try: os.replace(tmp,path); return
        except PermissionError:
            if attempt==5: raise
            time.sleep(delay)


def hb(path,done,total,stage,extra=None):
    if not path:return
    x={'completed':int(done),'total':int(total),'stage':stage,'updated_at_utc':datetime.now(timezone.utc).isoformat()}
    if extra:x.update(extra)
    atomic_json(path,x)


def norm(s): return ''.join(c for c in str(s).lower().strip() if c.isalnum() or c=='_')
def find_col(cols,names):
    m={norm(c):c for c in cols}
    for n in names:
        if n in m:return m[n]
    return None

def detect(path):
    try:h=pd.read_csv(path,nrows=3)
    except Exception:return None
    c=list(h.columns)
    m={'open':find_col(c,['open','o']),'high':find_col(c,['high','h']),'low':find_col(c,['low','l']),'close':find_col(c,['close','c']),
       'time':find_col(c,['server_time','time','datetime','timestamp','date']),'epoch':find_col(c,['server_epoch','epoch','unix','unix_time']),
       'volume':find_col(c,['tick_volume','tickvolume','volume','vol'])}
    return m if all(m[k] for k in ['open','high','low','close']) and (m['time'] or m['epoch']) else None

def inventory(roots,max_files):
    out=[]; seen=set()
    for root in roots:
        p=Path(root)
        if not p.exists():continue
        for f in p.rglob('*.csv'):
            if len(out)>=max_files:return out
            try: rp=str(f.resolve()).lower(); size=f.stat().st_size
            except OSError:continue
            if rp in seen or size<10000 or size>2_000_000_000:continue
            seen.add(rp); m=detect(f)
            if m:out.append((f,m,size))
    return out

def load_market(path,m,max_rows):
    df=pd.read_csv(path)
    if len(df)>max_rows:df=df.iloc[-max_rows:].copy()
    if m['epoch']:
        x=pd.to_numeric(df[m['epoch']],errors='coerce'); med=float(x.dropna().median()) if x.notna().any() else 0
        t=pd.to_datetime(x,unit='ms' if med>1e11 else 's',utc=True,errors='coerce')
    else:t=pd.to_datetime(df[m['time']].astype(str),utc=True,errors='coerce',format='mixed')
    z=pd.DataFrame({'time':t,'open':pd.to_numeric(df[m['open']],errors='coerce'),'high':pd.to_numeric(df[m['high']],errors='coerce'),'low':pd.to_numeric(df[m['low']],errors='coerce'),'close':pd.to_numeric(df[m['close']],errors='coerce')})
    if m['volume']:z['volume']=pd.to_numeric(df[m['volume']],errors='coerce')
    z=z.dropna(subset=['time','open','high','low','close']).sort_values('time').drop_duplicates('time')
    return z[z.time<PROTECTED].reset_index(drop=True)

def rsi(c,n):
    d=c.diff(); up=d.clip(lower=0).ewm(alpha=1/n,adjust=False,min_periods=n).mean(); dn=(-d.clip(upper=0)).ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    rs=up/dn.replace(0,np.nan); return 100-100/(1+rs)
def features(df):
    prev=df.close.shift(1); tr=pd.concat([(df.high-df.low).abs(),(df.high-prev).abs(),(df.low-prev).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean().replace(0,np.nan)
    f=pd.DataFrame(index=df.index)
    for k in [1,3,6,12,24,48]:f[f'ret{k}']=(df.close-df.close.shift(k))/atr
    f['range']=(df.high-df.low)/atr; f['body']=(df.close-df.open)/atr
    f['uwick']=(df.high-np.maximum(df.open,df.close))/atr; f['lwick']=(np.minimum(df.open,df.close)-df.low)/atr
    f['rsi7']=rsi(df.close,7); f['rsi14']=rsi(df.close,14)
    for n in [5,10,20,50,100]:f[f'sma{n}']=(df.close-df.close.rolling(n,min_periods=n).mean())/atr
    f['atr_regime']=atr/tr.rolling(50,min_periods=50).mean().replace(0,np.nan)
    f['hour']=df.time.dt.hour.astype(float); f['dow']=df.time.dt.dayofweek.astype(float)
    if 'volume' in df:
        vm=df.volume.rolling(48,min_periods=48).mean(); vs=df.volume.rolling(48,min_periods=48).std().replace(0,np.nan); f['volz']=(df.volume-vm)/vs
    return f,atr

def base_mask(df,rule):
    m=np.ones(len(df),dtype=bool)
    if rule['hour_start'] is not None:
        hh=df.time.dt.hour.to_numpy(); st=rule['hour_start']; w=rule['hour_width']
        m &= np.array([((int(v)-st)%24)<w for v in hh])
    return m

def apply_rule(df,ft,rule,cut_override=None):
    x=ft[rule['feature']].to_numpy(float); cut=rule['cutpoint'] if cut_override is None else cut_override
    cond=(x>cut) if rule['operator']=='gt' else (x<cut)
    return base_mask(df,rule) & cond

def welch_edge(selected,base,ret,min_n=100):
    valid=base & np.isfinite(ret)
    a=ret[selected & valid]; b=ret[(~selected) & valid]
    if len(a)<min_n or len(b)<min_n:return None
    ma=float(np.mean(a)); mb=float(np.mean(b)); va=float(np.var(a,ddof=1)); vb=float(np.var(b,ddof=1)); edge=ma-mb
    se=math.sqrt(va/len(a)+vb/len(b)); z=edge/se if se>0 else 0.0; p=math.erfc(abs(z)/math.sqrt(2))
    return {'n_selected':int(len(a)),'n_baseline':int(len(b)),'selected_mean_atr':ma,'baseline_mean_atr':mb,'edge_atr':edge,'p_fast':p}
def hac_edge(selected,base,ret,max_lag,min_n=100):
    valid=base & np.isfinite(ret); g=selected[valid].astype(float); y=ret[valid]
    n=len(y); ns=int(g.sum()); nb=n-ns
    if ns<min_n or nb<min_n:return None
    pg=float(g.mean()); edge=float(y[g==1].mean()-y[g==0].mean())
    z=y*(g/pg-(1.0-g)/(1.0-pg)); z=z-z.mean(); n=len(z)
    gamma0=float(np.dot(z,z)/n); lrv=gamma0
    L=min(int(max_lag),n-1)
    for lag in range(1,L+1):
        cov=float(np.dot(z[lag:],z[:-lag])/n); w=1.0-lag/(L+1.0); lrv += 2.0*w*cov
    se=math.sqrt(max(lrv,1e-18)/n); stat=edge/se if se>0 else 0.0; p=math.erfc(abs(stat)/math.sqrt(2))
    return {'n_selected':ns,'n_baseline':nb,'edge_atr':edge,'hac_lag':L,'hac_se':se,'hac_z':stat,'p_hac':p}
def bh_qvalues(pvals):
    n=len(pvals); order=np.argsort(pvals); q=np.ones(n); prev=1.0
    for k in range(n-1,-1,-1):
        idx=order[k]; rank=k+1; val=min(prev,float(pvals[idx])*n/rank); q[idx]=val; prev=val
    return q
def publish(publisher,phase,status,summary,artifacts):
    if not publisher:return
    cmd=['python',publisher,'--phase',phase,'--status',status,'--summary',summary]
    for a in artifacts:cmd += ['--artifact',str(a)]
    subprocess.run(cmd,check=True)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--roots',nargs='+',required=True); ap.add_argument('--output-dir',required=True); ap.add_argument('--progress-file'); ap.add_argument('--trials',type=int,default=250000); ap.add_argument('--max-files',type=int,default=120); ap.add_argument('--max-rows',type=int,default=900000); ap.add_argument('--seed',type=int,default=260912); ap.add_argument('--publisher')
    args=ap.parse_args(); out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True); progress=Path(args.progress_file) if args.progress_file else None; rng=random.Random(args.seed)
    files=inventory(args.roots,args.max_files); hb(progress,0,args.trials,'inventory',{'datasets':len(files)}); atomic_json(out/'dataset_inventory.json',[{'path':str(f),'size_bytes':s} for f,_,s in files])
    markets=[]
    for f,m,_ in files:
        try:
            df=load_market(f,m,args.max_rows)
            if (df.time.dt.year==2024).sum()<1000 or (df.time.dt.year==2025).sum()<1000:continue
            ft,atr=features(df); markets.append({'path':str(f),'df':df,'ft':ft,'atr':atr})
        except Exception:continue
    if not markets:raise RuntimeError('no eligible 2024+2025 dataset')
    discovery=[]; seen=set()
    for i in range(args.trials):
        mi=rng.randrange(len(markets)); M=markets[mi]; df=M['df']; ft=M['ft']; atr=M['atr']; feature=rng.choice(list(ft.columns)); op=rng.choice(['gt','lt']); tail=rng.choice(TAIL_Q); q=(1.0-tail) if op=='gt' else tail; h=rng.choice(HORIZONS); direction=rng.choice([-1,1]); hour_start=None; hour_width=None
        if rng.random()<0.35:hour_start=rng.randrange(24); hour_width=rng.choice([2,4,6,8])
        sig=(mi,feature,op,q,h,direction,hour_start,hour_width)
        if sig in seen:continue
        seen.add(sig); x=ft[feature].to_numpy(float); y=df.time.dt.year.to_numpy(); x24=x[(y==2024)&np.isfinite(x)]
        if len(x24)<1000:continue
        cut=float(np.quantile(x24,q)); rule={'market_index':mi,'dataset':M['path'],'feature':feature,'operator':op,'quantile':q,'cutpoint':cut,'horizon_bars':h,'direction':direction,'hour_start':hour_start,'hour_width':hour_width}
        sel=apply_rule(df,ft,rule); base=base_mask(df,rule); ret=((df.close.shift(-h)-df.close)/atr).to_numpy(float)*direction; s24=welch_edge(sel&(y==2024),base&(y==2024),ret,100)
        if s24 and s24['edge_atr']>0.03 and s24['p_fast']<0.01:rule['y2024']=s24; discovery.append(rule)
        if (i+1)%1000==0:hb(progress,i+1,args.trials,'discovery_2024_conditional_edge',{'datasets':len(markets),'discovery_candidates':len(discovery)})
    confirms=[]; pvals=[]; totalc=len(discovery)
    for j,r in enumerate(discovery):
        M=markets[r['market_index']]; df=M['df']; ft=M['ft']; atr=M['atr']; y=df.time.dt.year.to_numpy(); mo=df.time.dt.month.to_numpy(); h=r['horizon_bars']; sel=apply_rule(df,ft,r); base=base_mask(df,r); ret=((df.close.shift(-h)-df.close)/atr).to_numpy(float)*r['direction']
        s25=welch_edge(sel&(y==2025),base&(y==2025),ret,100); h1=welch_edge(sel&(y==2025)&(mo<=6),base&(y==2025)&(mo<=6),ret,40); h2=welch_edge(sel&(y==2025)&(mo>=7),base&(y==2025)&(mo>=7),ret,40)
        hac=None
        if s25 and h1 and h2 and s25['edge_atr']>0.02 and s25['p_fast']<0.01 and h1['edge_atr']>0 and h2['edge_atr']>0:
            hac=hac_edge(sel&(y==2025),base&(y==2025),ret,max_lag=max(48,2*h),min_n=100)
        p=1.0 if hac is None else hac['p_hac']; pvals.append(p); rr=dict(r); rr['y2025_fast']=s25; rr['y2025_h1_fast']=h1; rr['y2025_h2_fast']=h2; rr['y2025_hac']=hac; confirms.append(rr)
        if (j+1)%250==0:hb(progress,j+1,max(1,totalc),'confirmation_2025_conditional_edge',{'discovery_candidates':totalc})
    qvals=bh_qvalues(np.array(pvals,float)) if pvals else np.array([]); survivors=[]
    for idx,r in enumerate(confirms):
        r['confirmation_bh_q']=float(qvals[idx]) if len(qvals) else 1.0; s=r['y2025_hac']; h1=r['y2025_h1_fast']; h2=r['y2025_h2_fast']
        if not (s and h1 and h2 and r['confirmation_bh_q']<=0.05 and s['edge_atr']>0.02 and h1['edge_atr']>0 and h2['edge_atr']>0):continue
        qi=[.05,.10,.20,.30,.70,.80,.90,.95].index(r['quantile']); allq=[.05,.10,.20,.30,.70,.80,.90,.95]; neigh=[k for k in [qi-1,qi+1] if 0<=k<len(allq) and ((r['operator']=='lt' and allq[k]<=.30) or (r['operator']=='gt' and allq[k]>=.70))]; robust=False; nstats=[]
        M=markets[r['market_index']]; df=M['df']; ft=M['ft']; atr=M['atr']; y=df.time.dt.year.to_numpy(); x=ft[r['feature']].to_numpy(float); x24=x[(y==2024)&np.isfinite(x)]; ret=((df.close.shift(-r['horizon_bars'])-df.close)/atr).to_numpy(float)*r['direction']; base=base_mask(df,r)
        for k in neigh:
            nq=allq[k]; nc=float(np.quantile(x24,nq)); nm=apply_rule(df,ft,r,cut_override=nc); ns=welch_edge(nm&(y==2025),base&(y==2025),ret,80); nstats.append({'quantile':nq,'cutpoint':nc,'y2025_edge':ns})
            if ns and ns['edge_atr']>0.01:robust=True
        r['neighbor_stress']=nstats
        if robust:r.pop('market_index',None); survivors.append(r)
    survivors.sort(key=lambda r:(r['confirmation_bh_q'],-min(r['y2024']['edge_atr'],r['y2025_hac']['edge_atr'],r['y2025_h1_fast']['edge_atr'],r['y2025_h2_fast']['edge_atr']))); survivors=survivors[:500]
    result={'schema':3,'method':'conditional_edge_random_rule_factory','generated_at_utc':datetime.now(timezone.utc).isoformat(),'protected_2026_untouched':True,'thresholds_fit_on_2024_only':True,'confirmation_year':2025,'effect_definition':'directional forward return conditional mean minus same-session complement mean','tail_rules_only':True,'serial_dependence_control':'Newey-West/Bartlett HAC on confirmation influence series; lag=max(48,2*horizon)','multiple_testing':'Benjamini-Hochberg FDR 5% across all 2024 discovery candidates with non-HAC-screened candidates assigned p=1','trials':args.trials,'datasets_scanned':len(files),'datasets_eligible':len(markets),'unique_rules_tested':len(seen),'discovery_candidate_count':len(discovery),'survivor_count':len(survivors),'survivors':survivors}
    rp=out/'strategy_factory_result.json'; atomic_json(rp,result); cp=out/'strategy_factory_survivors.csv'; pd.json_normalize(survivors).to_csv(cp,index=False) if survivors else pd.DataFrame().to_csv(cp,index=False); hb(progress,args.trials,args.trials,'complete',{'datasets':len(markets),'discovery_candidates':len(discovery),'survivors':len(survivors)})
    status='PASS' if survivors else 'FAIL'; summary=f'{len(survivors)} conditional-edge survivors after 2024 discovery and untouched 2025 HAC/BH confirmation; tail-only rules; 2026 untouched.'; publish(args.publisher,'strategy-factory-r4-conditional-edge',status,summary,[rp,cp,out/'dataset_inventory.json']); print(json.dumps({'status':status,'discovery_candidates':len(discovery),'survivors':len(survivors),'protected_2026_untouched':True})); return 0
if __name__=='__main__':raise SystemExit(main())
