#!/usr/bin/env python3
"""Frozen scorer for D037 Williams-inspired previous-day-range volatility breakout V0."""
from __future__ import annotations
import argparse,csv,json,statistics
from pathlib import Path

EXPECTED={"BTCUSD","ETHUSD","EURUSD","GBPUSD","USDJPY","XAUUSD"}
PF_INF=1_000_000_000.0


def ns(s:str)->str:
    u=s.upper()
    for x in EXPECTED:
        if x in u:return x
    return u


def pf(v):
    gp=sum(x for x in v if x>0);gl=-sum(x for x in v if x<0)
    if gl==0:return PF_INF if gp>0 else None
    return gp/gl


def st(v):
    if not v:return {"n":0}
    return {"n":len(v),"sum":sum(v),"mean":statistics.fmean(v),"median":statistics.median(v),
            "win_rate":sum(x>0 for x in v)/len(v),"pf":pf(v),"min":min(v),"max":max(v)}


def streak(v):
    best=cur=0
    for x in v:
        cur=cur+1 if x<0 else 0
        best=max(best,cur)
    return best


def load_trades(paths):
    out=[]
    req={'run_stage','symbol','side','entry_time','exit_time','net_r','net_r_commission_x1_5','exit_reason',
         'entry','initial_stop','exit','risk_money_1lot_usd'}
    for p0 in paths:
        p=Path(p0)
        with p.open('r',encoding='utf-8-sig',newline='') as f:
            r=csv.DictReader(f,delimiter=';')
            if not r.fieldnames or not req.issubset(r.fieldnames):
                raise ValueError(f'{p}: incomplete D037 TRADES header')
            for z in r:
                if not z.get('symbol'):continue
                for k in ('entry','initial_stop','exit','risk_money_1lot_usd','net_r','net_r_commission_x1_5'):
                    x=float(z[k])
                    if not (x==x):raise ValueError(f'{p}: non-finite {k}')
                    if k in ('entry','initial_stop','exit','risk_money_1lot_usd') and x<=0:
                        raise ValueError(f'{p}: non-positive {k}={x}')
                z['_s']=ns(z['symbol'])
                z['_n']=float(z['net_r'])
                z['_x']=float(z['net_r_commission_x1_5'])
                z['_y']=z['entry_time'][:4]
                out.append(z)
    return out


def load_stats(paths,stage):
    out={}
    req={'status','run_stage','symbol','trades_opened','trades_closed','csv_trade_rows','invalid_price','invalid_risk',
         'risk_calc_failures','pnl_calc_failures'}
    for p0 in paths:
        p=Path(p0)
        with p.open('r',encoding='utf-8-sig',newline='') as f:
            r=csv.DictReader(f,delimiter=';')
            if not r.fieldnames or not req.issubset(r.fieldnames):
                raise ValueError(f'{p}: incomplete D037 STATS header')
            rows=[z for z in r if z.get('status')]
        if not rows:raise ValueError(f'{p}: no STATS rows')
        z=rows[-1];s=ns(z['symbol'])
        if s in out:raise ValueError(f'duplicate STATS for {s}')
        if z['run_stage']!=stage:raise ValueError(f'{p}: stage mismatch')
        opened=int(z['trades_opened']);closed=int(z['trades_closed']);csvrows=int(z['csv_trade_rows'])
        integrity={
            'final_status_ok':z['status']=='FINAL',
            'opened_eq_closed_eq_rows':opened==closed==csvrows,
            'invalid_price_zero':int(z['invalid_price'])==0,
            'invalid_risk_zero':int(z['invalid_risk'])==0,
            'risk_calc_failures_zero':int(z['risk_calc_failures'])==0,
            'pnl_calc_failures_zero':int(z['pnl_calc_failures'])==0,
        }
        out[s]={'file':str(p),'status':z['status'],'opened':opened,'closed':closed,'rows':csvrows,
                'ambiguous_days':int(z.get('ambiguous_days') or 0),'risk_fallbacks':int(z.get('risk_fallbacks') or 0),
                'pnl_fallbacks':int(z.get('pnl_fallbacks') or 0),'integrity':integrity,'integrity_ok':all(integrity.values())}
    return out


def main():
    a=argparse.ArgumentParser()
    a.add_argument('--input',action='append',required=True)
    a.add_argument('--stats',action='append',required=True)
    a.add_argument('--stage',required=True,choices=['SMOKE_MAR2025','DEV_2024_2025','CONFIRM_2026_H1'])
    a.add_argument('--out')
    q=a.parse_args()

    rows=load_trades(q.input)
    stats=load_stats(q.stats,q.stage)
    if any(r['run_stage']!=q.stage for r in rows):raise ValueError('TRADES stage mismatch')

    sy=sorted({r['_s'] for r in rows})
    v=[r['_n'] for r in rows];vx=[r['_x'] for r in rows]
    ps={s:st([r['_n'] for r in rows if r['_s']==s]) for s in sy}
    py={y:st([r['_n'] for r in rows if r['_y']==y]) for y in sorted({r['_y'] for r in rows})}
    side={s:st([r['_n'] for r in rows if r['side']==s]) for s in ('LONG','SHORT')}
    ex={}
    for e in sorted({r['exit_reason'] for r in rows}):
        w=[r['_n'] for r in rows if r['exit_reason']==e]
        ex[e]={**st(w),'share':len(w)/len(rows) if rows else 0.0}

    pos={s:max(0.0,ps[s].get('sum',0.0)) for s in sy}
    pt=sum(pos.values())
    conc=max(pos.values())/pt if pt>0 and pos else None
    agg=st(v);stress=st(vx)
    integrity_all=(set(stats)==EXPECTED and all(stats[s]['integrity_ok'] for s in EXPECTED))

    result={'strategy':'D037_WILLIAMS_PREVDAY_RANGE_VOLATILITY_BREAKOUT_V0','scorer_version':'1.00','stage':q.stage,
            'files':q.input,'stats_files':q.stats,'symbols_present':sy,'expected_symbols':sorted(EXPECTED),
            'aggregate':agg,'stress_1p5_commission':stress,'per_symbol':ps,'per_year':py,'per_side':side,
            'exit_reason':ex,'positive_symbol_concentration':conc,'max_losing_streak':streak(v),
            'integrity':stats,'integrity_all_six_ok':integrity_all,'pf_infinite_sentinel':PF_INF}

    gates={}
    if q.stage=='DEV_2024_2025':
        gates={
            'aggregate_n_ge_800':agg.get('n',0)>=800,
            'each_symbol_n_ge_80':set(ps)==EXPECTED and all(ps[s].get('n',0)>=80 for s in EXPECTED),
            'mean_net_r_ge_0p05':agg.get('mean',-999)>=0.05,
            'net_pf_ge_1p10':(agg.get('pf') or 0)>=1.10,
            'positive_symbols_ge_4':sum(ps[s].get('sum',0)>0 for s in ps)>=4,
            '2024_and_2025_positive':all(py.get(y,{}).get('sum',0)>0 for y in ('2024','2025')),
            'stress_1p5_total_positive':stress.get('sum',0)>0,
            'positive_symbol_concentration_le_0p60':conc is not None and conc<=0.60,
            'zero_integrity_events_all_six':integrity_all,
        }
        result['verdict']='CONTINUE_TO_UNTOUCHED_2026H1' if all(gates.values()) else 'REJECT_V0'
    elif q.stage=='CONFIRM_2026_H1':
        gates={
            'aggregate_n_ge_180':agg.get('n',0)>=180,
            'mean_net_r_positive':agg.get('mean',-999)>0,
            'net_pf_ge_1p08':(agg.get('pf') or 0)>=1.08,
            'positive_symbols_ge_3':sum(ps[s].get('sum',0)>0 for s in ps)>=3,
            'stress_1p5_total_positive':stress.get('sum',0)>0,
            'zero_integrity_events_all_six':integrity_all,
        }
        result['verdict']='CONFIRM' if all(gates.values()) else 'UNCONFIRMED'
    else:
        result['verdict']='SMOKE_ONLY_NO_ALPHA_SCORE'
    result['gates']=gates
    text=json.dumps(result,indent=2,allow_nan=False)
    if q.out:Path(q.out).write_text(text,encoding='utf-8')
    print(text)

if __name__=='__main__':main()
