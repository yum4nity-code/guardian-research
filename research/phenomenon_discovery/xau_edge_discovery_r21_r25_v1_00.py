#!/usr/bin/env python3
"""Preregistered XAUUSD phenomenon batch R21-R25 v1.00.

Implements only the frozen definitions from R21_R25_XAU_RESEARCH_PLAN_2026_09_14.md.
No entry/SL/TP/PnL optimization. 2026+ is hard-sealed in every mode.
"""
from __future__ import annotations

import argparse, csv, json, math, statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo

DISCOVERY_END=date(2019,6,30); CONFIRMATION_START=date(2019,7,1); CONFIRMATION_END=date(2024,12,31)
PREOOS_START=date(2025,1,1); PREOOS_END=date(2025,12,31); PROTECTED_START=date(2026,1,1)
NEW_YORK_TZ=ZoneInfo('America/New_York')
COMEX_OPEN_MIN=8*60+20; OPENING_RANGE_END_MIN=8*60+35; OPENING_BREAKOUT_SEARCH_END_MIN=10*60
POST_BARS=(1,2,4,8,16); POST_MINUTES=(15,30,60,120); R22_LOOKBACK=48; R22_TRAILING_DAYS=20

@dataclass(frozen=True)
class Bar:
    epoch:int; dt:datetime; timeframe:str; open:float; high:float; low:float; close:float
    @property
    def utc_day(self)->str: return self.dt.date().isoformat()
    @property
    def utc_minute(self)->int: return self.dt.hour*60+self.dt.minute
    def local_day(self,tz:ZoneInfo)->str: return self.dt.astimezone(tz).date().isoformat()
    def local_minute(self,tz:ZoneInfo)->int:
        x=self.dt.astimezone(tz); return x.hour*60+x.minute

def _finite(x:float)->bool: return math.isfinite(float(x))

def _stage_accepts(d:date,stage:str)->bool:
    if d>=PROTECTED_START: raise RuntimeError(f'PROTECTED 2026 row encountered: {d.isoformat()}')
    if stage=='discovery': return d<=DISCOVERY_END
    if stage=='confirmation': return CONFIRMATION_START<=d<=CONFIRMATION_END
    if stage=='preoos': raise RuntimeError('pre-OOS 2025 is locked in R21-R25 v1.00; requires a later explicit authorization/version')
    raise ValueError(f'unsupported stage: {stage}')

def load_bars(path:Path,stage:str)->list[Bar]:
    out=[]; prev=None
    with path.open('r',newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f); need={'timeframe','server_epoch','open','high','low','close'}; missing=need-set(r.fieldnames or [])
        if missing: raise RuntimeError(f'missing columns: {sorted(missing)}')
        for row in r:
            epoch=int(row['server_epoch'])
            if prev is not None and epoch<=prev: raise RuntimeError(f'non-increasing timestamp: {epoch} <= {prev}')
            prev=epoch; dt=datetime.fromtimestamp(epoch,tz=timezone.utc); accepted=_stage_accepts(dt.date(),stage)
            if not accepted: continue
            tf=row['timeframe'].strip().upper()
            if tf!='M5': raise RuntimeError(f'R21-R25 v1.00 requires M5, got {tf}')
            o,h,l,c=map(float,(row['open'],row['high'],row['low'],row['close']))
            if not all(_finite(x) and x>0 for x in (o,h,l,c)): raise RuntimeError(f'invalid OHLC at {dt.isoformat()}')
            if h<max(o,c) or l>min(o,c) or h<l: raise RuntimeError(f'invalid OHLC geometry at {dt.isoformat()}')
            out.append(Bar(epoch,dt,tf,o,h,l,c))
    if not out: raise RuntimeError(f'no usable rows for stage={stage}')
    return out

def forward_return(bars:Sequence[Bar],i:int,h:int)->float|None:
    j=i+h
    if j>=len(bars) or bars[j].epoch-bars[i].epoch!=300*h: return None
    return bars[j].close/bars[i].close-1.0

def signed_stats(values:Iterable[float])->dict:
    xs=[float(x) for x in values if _finite(float(x))]
    if not xs: return {'n':0,'mean':None,'median':None,'t':None,'positive_fraction':None}
    n=len(xs); mean=statistics.fmean(xs); sd=statistics.stdev(xs) if n>1 else 0.0
    return {'n':n,'mean':mean,'median':statistics.median(xs),'t':mean/(sd/math.sqrt(n)) if n>1 and sd>0 else None,'positive_fraction':sum(x>0 for x in xs)/n}

def cluster_stats(events:Sequence[dict],metric:str)->dict:
    xs=[(str(e['cluster_day']),float(e[metric])) for e in events if e.get('cluster_day') is not None and isinstance(e.get(metric),(int,float)) and _finite(e[metric])]
    if not xs: return {'n':0,'clusters':0,'mean':None,'cluster_se':None,'cluster_t':None}
    vals=[v for _,v in xs]; mean=statistics.fmean(vals); by=defaultdict(list)
    for d,v in xs: by[d].append(v)
    g=len(by); n=len(vals)
    if g<2 or n<2: return {'n':n,'clusters':g,'mean':mean,'cluster_se':None,'cluster_t':None}
    scores=[sum(v-mean for v in vs) for vs in by.values()]; meat=sum(s*s for s in scores)
    correction=(g/(g-1))*((n-1)/n); se=math.sqrt(max(correction*meat/(n*n),0.0))
    return {'n':n,'clusters':g,'mean':mean,'cluster_se':se,'cluster_t':mean/se if se>0 else None}

def yearly_stability(events:Sequence[dict],metric:str)->dict:
    by=defaultdict(list)
    for e in events:
        v=e.get(metric)
        if isinstance(v,(int,float)) and _finite(v): by[int(e['year'])].append(float(v))
    years={str(y):signed_stats(v) for y,v in sorted(by.items())}; pos=sum((s['mean'] or 0)>0 for s in years.values()); neg=sum((s['mean'] or 0)<0 for s in years.values()); nz=pos+neg
    return {'years':years,'positive_years':pos,'negative_years':neg,'sign_consistency':max(pos,neg)/nz if nz else None}

def _index_by_ny_day(bars):
    d=defaultdict(list)
    for i,b in enumerate(bars): d[b.local_day(NEW_YORK_TZ)].append(i)
    return d

def _find_ny_anchor(bars,idxs,minute): return next((i for i in idxs if bars[i].local_minute(NEW_YORK_TZ)==minute),None)

def r21_comex_unconditional_drift(bars):
    out=[]
    for ny_day,idxs in sorted(_index_by_ny_day(bars).items()):
        i=_find_ny_anchor(bars,idxs,COMEX_OPEN_MIN)
        if i is None: continue
        e={'research':'R21','epoch':bars[i].epoch,'year':bars[i].dt.year,'cluster_day':ny_day,'day_new_york':ny_day}
        for m in POST_MINUTES: e[f'post_{m}m']=forward_return(bars,i,m//5)
        out.append(e)
    return out

def _returns(bars):
    out=[None]
    for i in range(1,len(bars)): out.append(bars[i].close/bars[i-1].close-1 if bars[i].epoch-bars[i-1].epoch==300 else None)
    return out

def _rolling_stdev48(bars):
    rs=_returns(bars); out=[None]*len(bars)
    for i in range(R22_LOOKBACK,len(bars)):
        hist=rs[i-R22_LOOKBACK:i]
        if len(hist)!=R22_LOOKBACK or any(x is None for x in hist): continue
        sd=statistics.stdev(float(x) for x in hist)
        if sd>0: out[i]=sd
    return out

def _quantile_nearest_rank(xs,q):
    ys=sorted(float(x) for x in xs); rank=max(1,math.ceil(q*len(ys))); return ys[rank-1]

def _same_clock_abs_baselines(bars):
    buckets=defaultdict(list)
    for i,b in enumerate(bars):
        for h in POST_BARS:
            r=forward_return(bars,i,h)
            if r is not None: buckets[(b.utc_minute,h)].append(abs(r))
    return {k:statistics.fmean(v) for k,v in buckets.items() if v}

def r22_volatility_compression(bars):
    st=_rolling_stdev48(bars); baselines=_same_clock_abs_baselines(bars); hbd=defaultdict(list); ordered=[]; seen=set()
    for i,b in enumerate(bars):
        if st[i] is None: continue
        hbd[b.utc_day].append(float(st[i]))
        if b.utc_day not in seen: seen.add(b.utc_day); ordered.append(b.utc_day)
    prior={}
    for pos,d in enumerate(ordered):
        vals=[]
        for pd in ordered[max(0,pos-R22_TRAILING_DAYS):pos]: vals.extend(hbd[pd])
        prior[d]=vals
    out=[]; sampled=set()
    for i,b in enumerate(bars):
        sd=st[i]; hist=prior.get(b.utc_day,[])
        if sd is None or not hist: continue
        q10=_quantile_nearest_rank(hist,.10); q20=_quantile_nearest_rank(hist,.20)
        states=[]
        if sd<=q10: states.append('bottom10')
        if sd<=q20: states.append('bottom20')
        for state in states:
            key=(b.utc_day,b.dt.hour,state)
            if key in sampled: continue
            sampled.add(key)
            e={'research':'R22','compression_state':state,'epoch':b.epoch,'year':b.dt.year,'cluster_day':b.utc_day,'day_utc':b.utc_day,'utc_hour':b.dt.hour,'stdev48':sd,'q10':q10,'q20':q20,'trailing_distribution_n':len(hist)}
            for h in POST_BARS:
                r=forward_return(bars,i,h); ar=abs(r) if r is not None else None; base=baselines.get((b.utc_minute,h))
                e[f'abs_fwd_{h}b']=ar; e[f'baseline_abs_{h}b']=base; e[f'excess_abs_{h}b']=ar-base if ar is not None and base is not None else None
            out.append(e)
    return out

def r23_overnight_to_ny(bars):
    by_epoch={b.epoch:i for i,b in enumerate(bars)}; out=[]
    for ny_day,idxs in sorted(_index_by_ny_day(bars).items()):
        i=_find_ny_anchor(bars,idxs,COMEX_OPEN_MIN)
        if i is None: continue
        a=bars[i]; midnight=int(datetime(a.dt.year,a.dt.month,a.dt.day,tzinfo=timezone.utc).timestamp()); j=by_epoch.get(midnight)
        if j is None or bars[j].dt.date()!=a.dt.date(): continue
        pre=a.close/bars[j].close-1
        if pre==0: continue
        direction=1 if pre>0 else -1
        e={'research':'R23','epoch':a.epoch,'year':a.dt.year,'cluster_day':ny_day,'day_new_york':ny_day,'pre_ny_return':pre,'direction':direction,'utc_midnight_epoch':bars[j].epoch}
        for m in POST_MINUTES:
            r=forward_return(bars,i,m//5); e[f'post_{m}m']=r; e[f'continuation_{m}m']=direction*r if r is not None else None; e[f'reversal_{m}m']=-direction*r if r is not None else None
        out.append(e)
    return out

def r24_comex_opening_range_breakout(bars):
    out=[]
    for ny_day,idxs in sorted(_index_by_ny_day(bars).items()):
        ris=[i for i in idxs if COMEX_OPEN_MIN<=bars[i].local_minute(NEW_YORK_TZ)<OPENING_RANGE_END_MIN]
        if [bars[i].local_minute(NEW_YORK_TZ) for i in ris] != [COMEX_OPEN_MIN,COMEX_OPEN_MIN+5,COMEX_OPEN_MIN+10]: continue
        hi=max(bars[i].high for i in ris); lo=min(bars[i].low for i in ris); bi=None; direction=0
        for i in idxs:
            m=bars[i].local_minute(NEW_YORK_TZ)
            if m<OPENING_RANGE_END_MIN or m>OPENING_BREAKOUT_SEARCH_END_MIN: continue
            if bars[i].close>hi: bi,direction=i,1; break
            if bars[i].close<lo: bi,direction=i,-1; break
        if bi is None: continue
        b=bars[bi]; e={'research':'R24','epoch':b.epoch,'year':b.dt.year,'cluster_day':ny_day,'day_new_york':ny_day,'direction':direction,'opening_range_high':hi,'opening_range_low':lo,'breakout_close':b.close}
        for h in POST_BARS:
            r=forward_return(bars,bi,h); e[f'continuation_{h}b']=direction*r if r is not None else None; e[f'reversal_{h}b']=-direction*r if r is not None else None
        out.append(e)
    return out

def _utc_day_indices(bars):
    d=defaultdict(list)
    for i,b in enumerate(bars): d[b.utc_day].append(i)
    return sorted(d),d

def r25_ny_gap_previous_close(bars):
    days,by=_utc_day_indices(bars); prevmap={cur:prev for prev,cur in zip(days,days[1:])}; out=[]
    for ny_day,idxs in sorted(_index_by_ny_day(bars).items()):
        i=_find_ny_anchor(bars,idxs,COMEX_OPEN_MIN)
        if i is None: continue
        a=bars[i]; prevday=prevmap.get(a.utc_day)
        if prevday is None: continue
        pidx=by[prevday][-1]; pc=bars[pidx].close; gap=a.close/pc-1
        if gap==0: continue
        direction=1 if gap>0 else -1
        e={'research':'R25','epoch':a.epoch,'year':a.dt.year,'cluster_day':ny_day,'day_new_york':ny_day,'previous_utc_day':prevday,'previous_close_epoch':bars[pidx].epoch,'previous_close':pc,'anchor_close':a.close,'gap_return':gap,'gap_direction':direction}
        for m in POST_MINUTES:
            h=m//5; r=forward_return(bars,i,h); e[f'toward_{m}m']=-direction*r if r is not None else None; e[f'away_{m}m']=direction*r if r is not None else None; j=i+h
            if r is None or j>=len(bars): e[f'filled_by_{m}m']=None
            else:
                path=bars[i+1:j+1]; e[f'filled_by_{m}m']=any(x.low<=pc for x in path) if direction>0 else any(x.high>=pc for x in path)
        out.append(e)
    return out

def _metric_summary(events, prefixes):
    metrics=sorted({k for e in events for k in e if k.startswith(prefixes)})
    return {m:{'naive':signed_stats(e[m] for e in events if isinstance(e.get(m),(int,float))),'clustered':cluster_stats(events,m),'year_stability':yearly_stability(events,m)} for m in metrics}

def summarize(name,events):
    prefixes=('post_','excess_abs_','continuation_','reversal_','toward_','away_')
    out={'research':name,'event_count':len(events),'day_count':len({e['cluster_day'] for e in events})}
    if name=='R22':
        out['states']={}
        for state in ('bottom10','bottom20'):
            xs=[e for e in events if e.get('compression_state')==state]
            out['states'][state]={'event_count':len(xs),'day_count':len({e['cluster_day'] for e in xs}),'metrics':_metric_summary(xs,prefixes)}
    else:
        out['metrics']=_metric_summary(events,prefixes)
    return out

def run(path:Path,stage:str,selected:Sequence[str])->dict:
    bars=load_bars(path,stage); funcs={'R21':r21_comex_unconditional_drift,'R22':r22_volatility_compression,'R23':r23_overnight_to_ny,'R24':r24_comex_opening_range_breakout,'R25':r25_ny_gap_previous_close}; results={}
    for name in selected:
        ev=funcs[name](bars); results[name]={'summary':summarize(name,ev),'events':ev}
    return {'schema':1,'batch':'R21-R25','version':'1.00','generated_at_utc':datetime.now(timezone.utc).isoformat(),'stage':stage,'source':str(path),'rows':len(bars),'first_epoch':bars[0].epoch,'last_epoch':bars[-1].epoch,'stage_boundaries':{'discovery_end':'2019-06-30','confirmation_start':'2019-07-01','confirmation_end':'2024-12-31','preoos':'2025','protected':'2026+'},'protected_2026_opened':False,'pre_oos_2025_opened':stage=='preoos','doctrine':'phenomenon-first; preregistered definitions only; no P&L optimization; 2026 hard-sealed','results':results}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--input',required=True); ap.add_argument('--output',required=True); ap.add_argument('--stage',choices=('discovery','confirmation'),default='discovery'); ap.add_argument('--research',nargs='+',choices=('R21','R22','R23','R24','R25'),default=['R21','R22','R23','R24','R25']); a=ap.parse_args()
    payload=run(Path(a.input),a.stage,a.research); out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2,sort_keys=True)+'
',encoding='utf-8')
    print(json.dumps({k:v for k,v in payload.items() if k!='results'},indent=2,sort_keys=True))
    for name,item in payload['results'].items(): print(f"{name}: events={item['summary']['event_count']} days={item['summary']['day_count']}")
    return 0

if __name__=='__main__': raise SystemExit(main())
