#!/usr/bin/env python3
"""Score frozen D036 MT5 TRADES CSV outputs without parameter search."""
from __future__ import annotations
import argparse, csv, json, math, statistics
from collections import defaultdict
from pathlib import Path

EXPECTED={"BTCUSD","ETHUSD","EURUSD","GBPUSD","USDJPY","XAUUSD"}

def norm_symbol(s:str)->str:
    for x in EXPECTED:
        if x in s.upper(): return x
    return s.upper()

def pf(vals):
    gp=sum(x for x in vals if x>0); gl=-sum(x for x in vals if x<0)
    if gl==0: return math.inf if gp>0 else None
    return gp/gl

def stats(vals):
    if not vals:return {"n":0}
    return {"n":len(vals),"sum":sum(vals),"mean":statistics.fmean(vals),"median":statistics.median(vals),
            "win_rate":sum(x>0 for x in vals)/len(vals),"pf":pf(vals),"min":min(vals),"max":max(vals)}

def max_losing_streak(vals):
    best=cur=0
    for x in vals:
        cur=cur+1 if x<0 else 0; best=max(best,cur)
    return best

def load(paths):
    rows=[]
    for p0 in paths:
        p=Path(p0)
        with p.open('r',encoding='utf-8-sig',newline='') as f:
            r=csv.DictReader(f,delimiter=';')
            req={'run_stage','symbol','side','entry_time','exit_time','net_r','net_r_commission_x1_5','exit_reason'}
            if not r.fieldnames or not req.issubset(set(r.fieldnames)):
                raise ValueError(f'{p}: D036 TRADES header incomplete')
            for z in r:
                if not z.get('symbol'): continue
                z['_symbol']=norm_symbol(z['symbol'])
                z['_net']=float(z['net_r']); z['_stress']=float(z['net_r_commission_x1_5'])
                z['_year']=z['entry_time'][:4]
                rows.append(z)
    return rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',action='append',required=True)
    ap.add_argument('--stage',required=True,choices=['SMOKE_MAR2025','DEV_2024_2025','CONFIRM_2026_H1'])
    ap.add_argument('--out')
    a=ap.parse_args()
    rows=load(a.input)
    bad=[r for r in rows if r['run_stage']!=a.stage]
    if bad: raise ValueError(f'stage mismatch: expected {a.stage}')
    syms=sorted({r['_symbol'] for r in rows})
    vals=[r['_net'] for r in rows]; stress=[r['_stress'] for r in rows]
    per_symbol={s:stats([r['_net'] for r in rows if r['_symbol']==s]) for s in syms}
    per_year={y:stats([r['_net'] for r in rows if r['_year']==y]) for y in sorted({r['_year'] for r in rows})}
    per_side={s:stats([r['_net'] for r in rows if r['side']==s]) for s in ('LONG','SHORT')}
    exits={}
    for reason in sorted({r['exit_reason'] for r in rows}):
        v=[r['_net'] for r in rows if r['exit_reason']==reason]
        exits[reason]={**stats(v),'share':len(v)/len(rows) if rows else 0.0}
    pos_contrib={s:max(0.0,per_symbol[s].get('sum',0.0)) for s in syms}
    pos_total=sum(pos_contrib.values())
    concentration=(max(pos_contrib.values())/pos_total if pos_total>0 and pos_contrib else None)
    agg=stats(vals); stress_agg=stats(stress)
    result={
        'strategy':'D036_DONCHIAN_TREND_BREAKOUT_H1_V0','stage':a.stage,'files':a.input,
        'symbols_present':syms,'expected_symbols':sorted(EXPECTED),
        'aggregate':agg,'stress_1p5_commission':stress_agg,
        'per_symbol':per_symbol,'per_year':per_year,'per_side':per_side,'exit_reason':exits,
        'positive_symbol_concentration':concentration,'max_losing_streak':max_losing_streak(vals),
    }
    gates={}
    if a.stage=='DEV_2024_2025':
        gates={
            'aggregate_n_ge_180':agg.get('n',0)>=180,
            'each_symbol_n_ge_20':set(per_symbol)==EXPECTED and all(per_symbol[s].get('n',0)>=20 for s in EXPECTED),
            'mean_net_r_ge_0p08':agg.get('mean',-999)>=0.08,
            'net_pf_ge_1p15':(agg.get('pf') or 0)>=1.15,
            'positive_symbols_ge_4':sum(per_symbol[s].get('sum',0)>0 for s in per_symbol)>=4,
            '2024_and_2025_positive':all(per_year.get(y,{}).get('sum',0)>0 for y in ('2024','2025')),
            'stress_1p5_total_positive':stress_agg.get('sum',0)>0,
            'positive_symbol_concentration_le_0p60':concentration is not None and concentration<=0.60,
        }
        result['verdict']='CONTINUE_TO_UNTOUCHED_2026H1' if all(gates.values()) else 'REJECT_V0'
    elif a.stage=='CONFIRM_2026_H1':
        gates={
            'aggregate_n_ge_45':agg.get('n',0)>=45,
            'mean_net_r_positive':agg.get('mean',-999)>0,
            'net_pf_ge_1p10':(agg.get('pf') or 0)>=1.10,
            'positive_symbols_ge_3':sum(per_symbol[s].get('sum',0)>0 for s in per_symbol)>=3,
            'stress_1p5_total_positive':stress_agg.get('sum',0)>0,
        }
        result['verdict']='CONFIRM' if all(gates.values()) else 'UNCONFIRMED'
    else:
        result['verdict']='SMOKE_ONLY_NO_ALPHA_SCORE'
    result['gates']=gates
    text=json.dumps(result,indent=2,allow_nan=False)
    if a.out: Path(a.out).write_text(text,encoding='utf-8')
    print(text)
if __name__=='__main__': main()
