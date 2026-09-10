#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, os, random
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

PROTECTED = pd.Timestamp('2026-01-01', tz='UTC')

def atomic_json(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8'); os.replace(tmp,path)

def hb(path,done,total,stage,extra=None):
    if not path:return
    x={'completed':int(done),'total':int(total),'stage':stage,'updated_at_utc':datetime.now(timezone.utc).isoformat()}
    if extra:x.update(extra)
    atomic_json(path,x)

def norm(s):return ''.join(c for c in str(s).lower().strip() if c.isalnum() or c=='_')
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
            try:
                rp=str(f.resolve()).lower(); size=f.stat().st_size
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
    z=z[z.time<PROTECTED].reset_index(drop=True)
    return z

def rsi(c,n):
    d=c.diff(); up=d.clip(lower=0).ewm(alpha=1/n,adjust=False,min_periods=n).mean(); dn=(-d.clip(upper=0)).ewm(alpha=1/n,adjust=False,min_periods=n).mean(); rs=up/dn.replace(0,np.nan); return 100-100/(1+rs)

def features(df):
    prev=df.close.shift(1); tr=pd.concat([(df.high-df.low).abs(),(df.high-prev).abs(),(df.low-prev).abs()],axis=1).max(axis=1); atr=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean().replace(0,np.nan)
    f=pd.DataFrame(index=df.index)
    for k in [1,3,6,12,24,48]:f[f'ret{k}']=(df.close-df.close.shift(k))/atr
    f['range']=(df.high-df.low)/atr; f['body']=(df.close-df.open)/atr; f['uwick']=(df.high-np.maximum(df.open,df.close))/atr; f['lwick']=(np.minimum(df.open,df.close)-df.low)/atr
    f['rsi7']=rsi(df.close,7); f['rsi14']=rsi(df.close,14)
    for n in [5,10,20,50,100]:f[f'sma{n}']=(df.close-df.close.rolling(n,min_periods=n).mean())/atr
    f['atr_regime']=atr/tr.rolling(50,min_periods=50).mean().replace(0,np.nan); f['hour']=df.time.dt.hour.astype(float); f['dow']=df.time.dt.dayofweek.astype(float)
    if 'volume' in df:
        vm=df.volume.rolling(48,min_periods=48).mean(); vs=df.volume.rolling(48,min_periods=48).std().replace(0,np.nan); f['volz']= (df.volume-vm)/vs
    return f,atr

def eval_rule(mask,ret,years,min_n):
    out={}
    for y in [2024,2025]:
        a=ret[mask & (years==y) & np.isfinite(ret)]
        if len(a)<min_n:return None
        mu=float(np.mean(a)); sd=float(np.std(a,ddof=1)); se=sd/math.sqrt(len(a)) if len(a)>1 else 1e9; z=mu/se if se>0 else 0; p=math.erfc(abs(z)/math.sqrt(2))
        out[str(y)]={'n':int(len(a)),'mean_atr':mu,'p':p}
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--roots',nargs='+',required=True); ap.add_argument('--output-dir',required=True); ap.add_argument('--progress-file'); ap.add_argument('--trials',type=int,default=250000); ap.add_argument('--max-files',type=int,default=80); ap.add_argument('--max-rows',type=int,default=900000); ap.add_argument('--seed',type=int,default=260910); args=ap.parse_args()
    out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True); progress=Path(args.progress_file) if args.progress_file else None; rng=random.Random(args.seed)
    files=inventory(args.roots,args.max_files); hb(progress,0,max(1,args.trials),'inventory',{'datasets':len(files)})
    inv=[{'path':str(f),'size_bytes':s} for f,_,s in files]; atomic_json(out/'dataset_inventory.json',inv)
    if not files: raise RuntimeError('no OHLC CSV datasets found')
    markets=[]
    for f,m,_ in files:
        try:
            df=load_market(f,m,args.max_rows)
            if (df.time.dt.year==2024).sum()<1000 or (df.time.dt.year==2025).sum()<1000:continue
            ft,atr=features(df); markets.append((f,df,ft,atr))
        except Exception:continue
    if not markets:raise RuntimeError('no dataset has sufficient clean 2024 and 2025 rows')
    survivors=[]; total=args.trials
    horizons=[1,3,6,12,24,48]; ops=['gt','lt']; done=0
    for i in range(total):
        fpath,df,ft,atr=rng.choice(markets); col=rng.choice(list(ft.columns)); op=rng.choice(ops); h=rng.choice(horizons); direction=rng.choice([-1,1]); x=ft[col].to_numpy(float)
        finite=x[np.isfinite(x)]
        if len(finite)<2000:continue
        q=rng.choice([.05,.1,.2,.3,.7,.8,.9,.95]); cut=float(np.quantile(finite,q)); mask=(x>cut) if op=='gt' else (x<cut)
        if rng.random()<0.35:
            hour=rng.randrange(24); width=rng.choice([2,4,6,8]); hh=df.time.dt.hour.to_numpy(); mask &= np.array([((v-hour)%24)<width for v in hh])
        ret=((df.close.shift(-h)-df.close)/atr).to_numpy(float)*direction; years=df.time.dt.year.to_numpy(); ev=eval_rule(mask,ret,years,80)
        if ev:
            a=ev['2024']; b=ev['2025']; same=(a['mean_atr']>0 and b['mean_atr']>0)
            if same and min(a['mean_atr'],b['mean_atr'])>0.03 and max(a['p'],b['p'])<0.10:
                survivors.append({'dataset':str(fpath),'feature':col,'operator':op,'cutpoint':cut,'quantile':q,'horizon_bars':h,'direction':direction,'y2024':a,'y2025':b})
        done=i+1
        if done%1000==0:hb(progress,done,total,'random_search',{'datasets':len(markets),'survivors':len(survivors)})
    survivors.sort(key=lambda r:min(r['y2024']['mean_atr'],r['y2025']['mean_atr']),reverse=True); survivors=survivors[:500]
    atomic_json(out/'strategy_factory_result.json',{'schema':1,'generated_at_utc':datetime.now(timezone.utc).isoformat(),'protected_2026_untouched':True,'datasets_scanned':len(files),'datasets_eligible':len(markets),'trials':total,'survivors':survivors,'survivor_count':len(survivors)})
    hb(progress,total,total,'complete',{'datasets':len(markets),'survivors':len(survivors)})
    print(json.dumps({'status':'PASS','trials':total,'survivors':len(survivors),'protected_2026_untouched':True}))
    return 0

if __name__=='__main__':raise SystemExit(main())
