#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math
from pathlib import Path
import numpy as np
import pandas as pd

TARGETS=[0.5,1.0,1.25,1.5,2.0,2.5,3.0,4.0,5.0]
COL={0.5:'hit05_utc',1.0:'hit1_utc',1.25:'hit125_utc',1.5:'hit15_utc',2.0:'hit2_utc',2.5:'hit25_utc',3.0:'hit3_utc',4.0:'hit4_utc',5.0:'hit5_utc'}

def read(p): return pd.read_csv(p,sep=';')

def minpos(x):
    vals=[]
    for v in x:
        try:
            i=int(float(v))
            if i>0: vals.append(i)
        except Exception: pass
    return min(vals) if vals else 0

def anyyes(x): return 'YES' if pd.Series(x).astype(str).str.upper().eq('YES').any() else 'NO'

def event_level(trades,outcomes):
    keys=['session_id','event_id','symbol','strategy','side']
    if 'leg' in outcomes.columns and 'leg' in trades.columns: keys.append('leg')
    agg={'mfe_r':'max','mae_r':'max'}
    for c in list(COL.values())+['stop_utc','be_after1_utc','be_after125_utc','rsi50_utc','rsi70_utc']:
        if c in outcomes.columns: agg[c]=minpos
    for c in ['ambiguous_stop_target_m1','ambiguous_be1_m1','ambiguous_be125_m1']:
        if c in outcomes.columns: agg[c]=anyyes
    out=outcomes.groupby(keys,as_index=False).agg(agg)
    keep=[c for c in ['session_id','event_id','entry_utc','symbol','strategy','variant','side','leg','entry','sl','risk_price','signal_tf','context'] if c in trades.columns]
    jt=trades[keep].drop_duplicates(['session_id','event_id'])
    merge_keys=[c for c in keys if c in jt.columns]
    out=jt.merge(out,on=merge_keys,how='left')
    out['entry_dt']=pd.to_datetime(out['entry_utc'],format='%Y.%m.%d %H:%M:%S',errors='coerce')
    out['year']=out['entry_dt'].dt.year
    return out

def wilson(p,n,z=1.96):
    if n<=0:return (np.nan,np.nan)
    den=1+z*z/n;center=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return center-half,center+half

def fixed(sub,r):
    h=pd.to_numeric(sub.get(COL[r],0),errors='coerce').fillna(0).astype('int64')
    st=pd.to_numeric(sub.get('stop_utc',0),errors='coerce').fillna(0).astype('int64')
    amb=sub.get('ambiguous_stop_target_m1',pd.Series('NO',index=sub.index)).astype(str).str.upper().eq('YES')
    w=(h>0)&((st==0)|(h<st));l=(st>0)&((h==0)|(st<h));valid=(w|l)&~amb
    n=int(valid.sum());wins=int((w&valid).sum())
    if not n:return {'n_total':len(sub),'n_resolved':0,'wins':0,'p':None,'ev':None,'lo95':None,'hi95':None}
    p=wins/n;lo,hi=wilson(p,n)
    return {'n_total':len(sub),'n_resolved':n,'wins':wins,'p':p,'ev':(r+1)*p-1,'lo95':(r+1)*lo-1,'hi95':(r+1)*hi-1}

def be_manager(sub,trigger,target):
    ht=pd.to_numeric(sub.get(COL[target],0),errors='coerce').fillna(0).astype('int64')
    hs=pd.to_numeric(sub.get(COL[trigger],0),errors='coerce').fillna(0).astype('int64')
    st=pd.to_numeric(sub.get('stop_utc',0),errors='coerce').fillna(0).astype('int64')
    bec='be_after1_utc' if trigger==1.0 else 'be_after125_utc'
    be=pd.to_numeric(sub.get(bec,0),errors='coerce').fillna(0).astype('int64')
    amb0=sub.get('ambiguous_stop_target_m1',pd.Series('NO',index=sub.index)).astype(str).str.upper().eq('YES')
    ambb=sub.get('ambiguous_be1_m1' if trigger==1.0 else 'ambiguous_be125_m1',pd.Series('NO',index=sub.index)).astype(str).str.upper().eq('YES')
    loss=(st>0)&((hs==0)|(st<hs))
    trig=(hs>0)&((st==0)|(hs<st))
    win=trig&(ht>0)&((be==0)|(ht<be))
    bez=trig&(be>0)&((ht==0)|(be<ht))
    tie=(trig&(ht>0)&(be>0)&(ht==be))|((hs>0)&(st>0)&(hs==st))
    valid=(loss|win|bez)&~amb0&~ambb&~tie
    pay=pd.Series(np.nan,index=sub.index)
    pay.loc[loss]=-1.0;pay.loc[bez]=0.0;pay.loc[win]=target
    vals=pay[valid].dropna()
    return {'n_total':len(sub),'n_resolved':int(len(vals)),'coverage':float(len(vals)/len(sub)) if len(sub) else None,'ev':float(vals.mean()) if len(vals) else None,'loss':int((loss&valid).sum()),'be':int((bez&valid).sum()),'target':int((win&valid).sum())}

def momentum_partial(sub,target=3.0):
    # Research comparator only, not exact native trail: BE armed at 1.25R; 25% banked at 2R; 75% aims at target.
    h125=pd.to_numeric(sub.get('hit125_utc',0),errors='coerce').fillna(0).astype('int64')
    h2=pd.to_numeric(sub.get('hit2_utc',0),errors='coerce').fillna(0).astype('int64')
    ht=pd.to_numeric(sub.get(COL[target],0),errors='coerce').fillna(0).astype('int64')
    st=pd.to_numeric(sub.get('stop_utc',0),errors='coerce').fillna(0).astype('int64')
    be=pd.to_numeric(sub.get('be_after125_utc',0),errors='coerce').fillna(0).astype('int64')
    amb=sub.get('ambiguous_stop_target_m1',pd.Series('NO',index=sub.index)).astype(str).str.upper().eq('YES')|sub.get('ambiguous_be125_m1',pd.Series('NO',index=sub.index)).astype(str).str.upper().eq('YES')
    loss=(st>0)&((h125==0)|(st<h125))
    armed=(h125>0)&((st==0)|(h125<st))
    be_before2=armed&(be>0)&((h2==0)|(be<h2))
    reached2=armed&(h2>0)&((be==0)|(h2<be))
    target_after2=reached2&(ht>0)&((be==0)|(ht<be))
    be_after2=reached2&(be>0)&((ht==0)|(be<ht))
    valid=(loss|be_before2|target_after2|be_after2)&~amb
    pay=pd.Series(np.nan,index=sub.index)
    pay.loc[loss]=-1.0;pay.loc[be_before2]=0.0;pay.loc[be_after2]=0.25*2.0;pay.loc[target_after2]=0.25*2.0+0.75*target
    vals=pay[valid].dropna()
    return {'n_total':len(sub),'n_resolved':int(len(vals)),'coverage':float(len(vals)/len(sub)) if len(sub) else None,'ev':float(vals.mean()) if len(vals) else None}

def level_rate(sub,col):
    if col not in sub.columns:return None
    t=pd.to_numeric(sub[col],errors='coerce').fillna(0).astype('int64');st=pd.to_numeric(sub.get('stop_utc',0),errors='coerce').fillna(0).astype('int64')
    valid=(t>0)&((st==0)|(t<st))
    return {'n':len(sub),'count':int(valid.sum()),'rate':float(valid.mean()) if len(sub) else None}

def group(ev,cols):
    rows=[]
    for key,sub in ev.groupby(cols,dropna=False):
        if not isinstance(key,tuple):key=(key,)
        rec={c:v for c,v in zip(cols,key)};rec['n']=len(sub)
        rec['fixed']={str(r):fixed(sub,r) for r in [0.5,1.0,1.25,1.5,2.0,2.5,3.0]}
        rec['be1_to2']=be_manager(sub,1.0,2.0);rec['be1_to3']=be_manager(sub,1.0,3.0);rec['be125_to2']=be_manager(sub,1.25,2.0);rec['be125_to3']=be_manager(sub,1.25,3.0)
        if sub['strategy'].astype(str).str.contains('D017_MOMENTUM').any():rec['mom_25pct2_be125_to3']=momentum_partial(sub,3.0)
        if 'rsi50_utc' in sub.columns:rec['rsi50_before_stop']=level_rate(sub,'rsi50_utc');rec['rsi70_before_stop']=level_rate(sub,'rsi70_utc')
        rows.append(rec)
    return rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--trades',required=True);ap.add_argument('--outcomes',required=True);ap.add_argument('--events');ap.add_argument('--json-out');ap.add_argument('--md-out');args=ap.parse_args()
    tr=read(args.trades);out=read(args.outcomes);ev=event_level(tr,out)
    res={'schema':'LONG_HISTORY_SIGNAL_PATH_V1','trade_rows':len(tr),'unique_events':len(ev),'sessions':tr.groupby(['session_id','symbol','strategy']).size().reset_index(name='n').to_dict('records'),'overall':group(ev,['symbol','strategy']),'year':group(ev,['symbol','strategy','year'])}
    if 'leg' in ev.columns:res['leg']=group(ev,['symbol','strategy','year','leg'])
    if args.events:
        e=read(args.events);res['event_rows']=len(e);res['transitions']=e.groupby(['session_id','symbol','strategy','transition']).size().reset_index(name='n').to_dict('records') if 'transition' in e else []
    js=json.dumps(res,indent=2,default=str)
    if args.json_out:Path(args.json_out).write_text(js,encoding='utf-8')
    lines=['# Long-history signal path diagnostic','',f'Unique virtual signals: **{len(ev)}**','']
    for rec in res['overall']:
        lines += [f"## {rec['symbol']} — {rec['strategy']}",'','| target | resolved | EV | 95% EV interval |','|---|---:|---:|---:|']
        for r in [0.5,1.0,1.25,1.5,2.0,2.5,3.0]:
            m=rec['fixed'][str(r)];evv='NA' if m['ev'] is None else f"{m['ev']:+.3f}R";ci='NA' if m['lo95'] is None else f"{m['lo95']:+.3f} .. {m['hi95']:+.3f}R";lines.append(f'| +{r:g}R | {m["n_resolved"]} | {evv} | {ci} |')
        for k,label in [('be1_to2','BE@1 -> 2R'),('be1_to3','BE@1 -> 3R'),('be125_to2','BE@1.25 -> 2R'),('be125_to3','BE@1.25 -> 3R')]:
            m=rec[k];lines.append(f"- {label}: EV {m['ev']:+.3f}R on {m['n_resolved']} resolved" if m['ev'] is not None else f'- {label}: NA')
        if 'mom_25pct2_be125_to3' in rec:
            m=rec['mom_25pct2_be125_to3'];lines.append(f"- Momentum comparator 25%@2R + BE@1.25 + rest->3R (not exact trail): {m['ev']:+.3f}R" if m['ev'] is not None else '- Momentum comparator: NA')
        if 'rsi50_before_stop' in rec and rec['rsi50_before_stop']:
            a=rec['rsi50_before_stop'];b=rec['rsi70_before_stop'];lines.append(f"- RSI50 before structural stop: {a['rate']:.1%}; RSI70 before structural stop: {b['rate']:.1%}")
        lines.append('')
    md='\n'.join(lines)
    if args.md_out:Path(args.md_out).write_text(md,encoding='utf-8')
    else:print(md)

if __name__=='__main__':main()
