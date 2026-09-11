"""Pure R4 feature/signal definitions copied without inventory/loading/main."""
import numpy as np
import pandas as pd

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
