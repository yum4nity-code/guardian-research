#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, random
from pathlib import Path
import numpy as np
import pandas as pd
from strategy_factory_conditional_edge_v1_00 import (
    HORIZONS, atomic_json, hb, inventory, load_market, features,
    welch_edge, hac_edge, bh_qvalues, publish
)

TAIL_Q=(0.05,0.10,0.20,0.30)
OPS=('lt','gt')
EXCLUDE_FEATURES={'hour','dow'}


def cond(x,op,cut):
    return (x<cut) if op=='lt' else (x>cut)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--roots',nargs='+',required=True)
    ap.add_argument('--output-dir',required=True)
    ap.add_argument('--progress-file')
    ap.add_argument('--trials',type=int,default=120000)
    ap.add_argument('--max-files',type=int,default=120)
    ap.add_argument('--max-rows',type=int,default=900000)
    ap.add_argument('--seed',type=int,default=260913)
    ap.add_argument('--publisher')
    args=ap.parse_args()
    out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True)
    progress=Path(args.progress_file) if args.progress_file else None
    rng=random.Random(args.seed)

    files=inventory(args.roots,args.max_files)
    atomic_json(out/'dataset_inventory.json',[{'path':str(f),'size_bytes':s} for f,_,s in files])
    markets=[]
    for f,m,_ in files:
        try:
            df=load_market(f,m,args.max_rows)
            if (df.time.dt.year==2024).sum()<1000 or (df.time.dt.year==2025).sum()<1000: continue
            ft,atr=features(df)
            markets.append({'path':str(f),'df':df,'ft':ft,'atr':atr})
        except Exception:
            continue
    if not markets: raise RuntimeError('no eligible pre-2026 dataset')

    discovery=[]; seen=set()
    for i in range(args.trials):
        mi=rng.randrange(len(markets)); M=markets[mi]; df=M['df']; ft=M['ft']; atr=M['atr']
        feats=[c for c in ft.columns if c not in EXCLUDE_FEATURES]
        f1,f2=rng.sample(feats,2); o1=rng.choice(OPS); o2=rng.choice(OPS)
        t1=rng.choice(TAIL_Q); t2=rng.choice(TAIL_Q)
        q1=t1 if o1=='lt' else 1-t1; q2=t2 if o2=='lt' else 1-t2
        h=rng.choice(HORIZONS); direction=rng.choice((-1,1))
        sig=(mi,f1,o1,q1,f2,o2,q2,h,direction)
        if sig in seen: continue
        seen.add(sig)
        year=df.time.dt.year.to_numpy()
        x1=ft[f1].to_numpy(float); x2=ft[f2].to_numpy(float)
        finite=np.isfinite(x1)&np.isfinite(x2)
        a=x1[(year==2024)&finite]; b=x2[(year==2024)&finite]
        if len(a)<1000 or len(b)<1000: continue
        c1=float(np.quantile(a,q1)); c2=float(np.quantile(b,q2))
        selected=finite&cond(x1,o1,c1)&cond(x2,o2,c2)
        target_year=df.time.shift(-h).dt.year.to_numpy()
        ret=((df.close.shift(-h)-df.close)/atr).to_numpy(float)*direction
        ret[target_year!=year]=np.nan
        s24=welch_edge(selected&(year==2024),finite&(year==2024),ret,100)
        if s24 and s24['edge_atr']>0.04 and s24['p_fast']<0.005:
            discovery.append({'market_index':mi,'dataset':M['path'],'feature1':f1,'operator1':o1,'quantile1':q1,'cutpoint1':c1,
                              'feature2':f2,'operator2':o2,'quantile2':q2,'cutpoint2':c2,'horizon_bars':h,'direction':direction,'y2024':s24})
        if (i+1)%1000==0: hb(progress,i+1,args.trials,'discovery_2024_interactions',{'datasets':len(markets),'discovery_candidates':len(discovery)})

    confirms=[]; pvals=[]
    for j,r in enumerate(discovery):
        M=markets[r['market_index']]; df=M['df']; ft=M['ft']; atr=M['atr']; year=df.time.dt.year.to_numpy(); month=df.time.dt.month.to_numpy(); h=r['horizon_bars']
        x1=ft[r['feature1']].to_numpy(float); x2=ft[r['feature2']].to_numpy(float); finite=np.isfinite(x1)&np.isfinite(x2)
        selected=finite&cond(x1,r['operator1'],r['cutpoint1'])&cond(x2,r['operator2'],r['cutpoint2'])
        target_year=df.time.shift(-h).dt.year.to_numpy(); ret=((df.close.shift(-h)-df.close)/atr).to_numpy(float)*r['direction']; ret[target_year!=year]=np.nan
        s25=welch_edge(selected&(year==2025),finite&(year==2025),ret,100)
        hac=hac_edge(selected&(year==2025),finite&(year==2025),ret,max_lag=max(48,2*h),min_n=100) if s25 else None
        quarters=[]
        for q in range(4):
            lo=1+3*q; hi=lo+2; pm=(year==2025)&(month>=lo)&(month<=hi)
            quarters.append(welch_edge(selected&pm,finite&pm,ret,30))
        rr=dict(r); rr['y2025_hac']=hac; rr['y2025_quarters']=quarters
        confirms.append(rr); pvals.append(1.0 if hac is None else hac['p_hac'])
        if (j+1)%250==0: hb(progress,j+1,max(1,len(discovery)),'confirmation_2025_interactions',{'discovery_candidates':len(discovery)})

    qv=bh_qvalues(np.asarray(pvals,float)) if pvals else np.asarray([])
    survivors=[]
    for i,r in enumerate(confirms):
        r['confirmation_bh_q']=float(qv[i]) if len(qv) else 1.0
        hac=r['y2025_hac']; qs=r['y2025_quarters']
        if not hac or r['confirmation_bh_q']>0.05 or hac['edge_atr']<=0.02: continue
        if any(x is None or x['edge_atr']<=0 for x in qs): continue
        r.pop('market_index',None); survivors.append(r)
    survivors.sort(key=lambda r:(r['confirmation_bh_q'],-min(r['y2024']['edge_atr'],r['y2025_hac']['edge_atr'])))
    survivors=survivors[:300]
    result={'schema':1,'method':'two_state_interaction_conditional_edge','generated_at_utc':pd.Timestamp.now(tz='UTC').isoformat(),
            'protected_2026_untouched':True,'thresholds_fit_on_2024_only':True,'cross_year_forward_returns_purged':True,
            'confirmation_year':2025,'multiple_testing':'BH-FDR 5% across all 2024 discoveries','trials':args.trials,
            'unique_rules_tested':len(seen),'datasets_scanned':len(files),'datasets_eligible':len(markets),
            'discovery_candidate_count':len(discovery),'survivor_count':len(survivors),'survivors':survivors}
    rp=out/'interaction_factory_result.json'; atomic_json(rp,result)
    cp=out/'interaction_factory_survivors.csv'; pd.json_normalize(survivors).to_csv(cp,index=False)
    hb(progress,args.trials,args.trials,'complete',{'discovery_candidates':len(discovery),'survivors':len(survivors)})
    status='PASS' if survivors else 'FAIL'
    if args.publisher:
        publish(args.publisher,'strategy-factory-xau-interaction-edge',status,
                f'{len(survivors)} two-state interaction survivors after 2024 discovery and untouched 2025 HAC/BH/quarter confirmation; 2026 untouched.',
                [rp,cp,out/'dataset_inventory.json'])
    print(json.dumps({'status':status,'trials':args.trials,'survivors':len(survivors),'protected_2026_untouched':True}))
    return 0

if __name__=='__main__': raise SystemExit(main())
