#!/usr/bin/env python3
"""Frozen paired management scorer for D032-M2 / operational wrapper D041."""
from __future__ import annotations
import argparse, json, math, random, sys
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import experiment, runner, tester

class PairedScoreError(RuntimeError): pass
SCORING_MODE='D032_M2_PAIRED_MONTH_BLOCK_BOOTSTRAP'
BOOTSTRAP_RESAMPLES=20000
BOOTSTRAP_SEED=3202048

def _f(row:dict[str,str], field:str)->float:
    try: v=float(row[field])
    except (KeyError,ValueError) as e: raise PairedScoreError(f'invalid {field}: {row.get(field)!r}') from e
    if not math.isfinite(v): raise PairedScoreError(f'non-finite {field}')
    return v

def _month(row:dict[str,str])->str:
    x=row.get('signal_time','')
    if len(x)<7: raise PairedScoreError(f'invalid signal_time {x!r}')
    return x[:7]

def percentile(xs:list[float], q:float)->float:
    if not xs: raise PairedScoreError('empty percentile sample')
    ys=sorted(xs); pos=(len(ys)-1)*q; lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    if lo==hi:return ys[lo]
    return ys[lo]+(ys[hi]-ys[lo])*(pos-lo)

def month_block_bootstrap(rows:list[dict[str,str]], n:int=BOOTSTRAP_RESAMPLES, seed:int=BOOTSTRAP_SEED)->dict[str,float]:
    blocks:dict[str,list[float]]=defaultdict(list)
    for r in rows: blocks[_month(r)].append(_f(r,'paired_delta_r'))
    months=sorted(blocks)
    if not months: raise PairedScoreError('no month blocks')
    rng=random.Random(seed); means=[]
    for _ in range(n):
        vals=[]
        for _j in range(len(months)): vals.extend(blocks[rng.choice(months)])
        means.append(sum(vals)/len(vals))
    return {'blocks':len(months),'resamples':n,'seed':seed,'lower_95':percentile(means,.025),'median':percentile(means,.5),'upper_95':percentile(means,.975)}

def evaluate(rows_by_symbol:dict[str,list[dict[str,str]]], gates:dict[str,Any])->dict[str,Any]:
    eligible=[]
    per={}
    exits=Counter()
    for sym,rows in rows_by_symbol.items():
        es=[]
        for r in rows:
            if r.get('epoch')!='POST2024' or r.get('eligible')!='1': continue
            for f in ('reference_net_r','candidate_net_r','paired_delta_r','candidate_stress_net_r'): _f(r,f)
            es.append(r); exits[r.get('exit_reason','')]+=1
        eligible.extend(es)
        ds=[_f(r,'paired_delta_r') for r in es]; cs=[_f(r,'candidate_net_r') for r in es]
        per[sym]={'n':len(es),'paired_mean_delta_r':sum(ds)/len(ds) if ds else 0.0,'paired_total_delta_r':sum(ds),'candidate_mean_net_r':sum(cs)/len(cs) if cs else 0.0}
    n=len(eligible)
    deltas=[_f(r,'paired_delta_r') for r in eligible]; cand=[_f(r,'candidate_net_r') for r in eligible]; stress=[_f(r,'candidate_stress_net_r') for r in eligible]; refs=[_f(r,'reference_net_r') for r in eligible]
    boot=month_block_bootstrap(eligible) if eligible else {'blocks':0,'resamples':BOOTSTRAP_RESAMPLES,'seed':BOOTSTRAP_SEED,'lower_95':float('-inf'),'median':0.0,'upper_95':0.0}
    positive_syms=[s for s,x in per.items() if x['paired_mean_delta_r']>0]
    pos_totals=[x['paired_total_delta_r'] for x in per.values() if x['paired_total_delta_r']>0]
    pos_sum=sum(pos_totals); max_share=max(pos_totals)/pos_sum if pos_sum>0 else 0.0
    metrics={'aggregate_n':n,'reference_mean_net_r':sum(refs)/n if n else 0.0,'candidate_mean_net_r':sum(cand)/n if n else 0.0,'candidate_mean_stress_r':sum(stress)/n if n else 0.0,'paired_mean_delta_r':sum(deltas)/n if n else 0.0,'paired_total_delta_r':sum(deltas),'positive_delta_symbols':positive_syms,'positive_delta_symbols_n':len(positive_syms),'max_positive_symbol_contribution_share':max_share,'per_symbol':per,'month_block_bootstrap':boot,'exit_reason_counts':dict(exits)}
    gate_results={
      'aggregate_n_min': n>=int(gates['aggregate_n_min']),
      'paired_mean_delta_strictly_positive': metrics['paired_mean_delta_r']>0,
      'month_block_bootstrap_lower_95_strictly_positive': boot['lower_95']>0,
      'positive_delta_symbols_min': len(positive_syms)>=int(gates['positive_delta_symbols_min']),
      'max_positive_symbol_contribution_share': max_share<=float(gates['max_positive_symbol_contribution_share']),
      'candidate_mean_net_r_min': metrics['candidate_mean_net_r']>float(gates['candidate_mean_net_r_min']),
    }
    if not gate_results['aggregate_n_min']: verdict='INCONCLUSIVE_COUNT'
    elif all(gate_results.values()): verdict='MANAGEMENT_VALIDATED'
    else: verdict='REJECT_MANAGEMENT'
    return {'metrics':metrics,'gates':gate_results,'all_gates_pass':all(gate_results.values()),'verdict':verdict}

def latest_batch(config:dict[str,Any], expid:str, stage:str)->Path:
    base=runner._expand_path(config['workspace_dir'])/'batches'/expid/stage
    for p in sorted(base.glob('*/batch.json'),reverse=True) if base.exists() else []:
        try: data=json.loads(p.read_text(encoding='utf-8'))
        except Exception: continue
        if data.get('status')=='BATCH_PASS_INTEGRITY': return p
    raise PairedScoreError(f'no integrity-passed batch for {expid} {stage}')

def score(identifier:str, stage:str='development', batch_path:str|None=None)->dict[str,Any]:
    _,mpath,manifest=runner.load_context(identifier)
    if manifest.get('cost_model',{}).get('scoring_mode')!=SCORING_MODE: raise PairedScoreError('manifest scoring_mode mismatch')
    if stage!='development': raise PairedScoreError('D032-M2 formal management validation is mapped to runner development stage only')
    config=runner.load_config(); p=Path(batch_path).resolve() if batch_path else latest_batch(config,manifest['experiment_id'],stage)
    batch=json.loads(p.read_text(encoding='utf-8'))
    if batch.get('status')!='BATCH_PASS_INTEGRITY': raise PairedScoreError('batch not integrity-passed')
    expected=manifest['stages'][stage]['symbols']; tests=batch.get('tests',[])
    if [x.get('symbol') for x in tests]!=expected: raise PairedScoreError('batch symbol order/content mismatch')
    rows_by={}
    for item in tests:
        sym=item['symbol']; tp=Path(item['trades']['path']); sp=Path(item['stats']['path'])
        if runner.sha256_file(tp)!=item['trades']['sha256'] or runner.sha256_file(sp)!=item['stats']['sha256']: raise PairedScoreError(f'evidence SHA mismatch {sym}')
        rows_by[sym]=tester.read_semicolon_csv(tp)
    result=evaluate(rows_by,manifest['stages'][stage]['gates'])
    created=datetime.now(timezone.utc); out=runner._expand_path(config['workspace_dir'])/'scores'/manifest['experiment_id']/stage/created.strftime('%Y%m%dT%H%M%SZ'); out.mkdir(parents=True,exist_ok=False)
    payload={'schema_version':1,'created_at_utc':created.isoformat(),'experiment_id':manifest['experiment_id'],'scientific_preregistration':manifest['preregistration']['path'],'scientific_role':'D032_M2_MANAGEMENT_VALIDATION_POST2024','runner_stage':stage,'manifest_path':str(mpath.relative_to(runner.ROOT)),'manifest_source_sha256':manifest['source']['source_sha256'],'batch_path':str(p),**result,'confirmation_opened':False,'autosync_used':False}
    vp=out/'verdict.json'; ap=out/'paired_analytics.json'; runner.write_receipt(vp,payload); runner.write_receipt(ap,{'schema_version':1,'created_at_utc':created.isoformat(),'experiment_id':manifest['experiment_id'],'status':'PAIRED_ANALYTICS_COMPLETE','scientific_role':payload['scientific_role'],'metrics':result['metrics'],'gates':result['gates'],'verdict':result['verdict'],'autosync_used':False})
    return {'verdict_path':str(vp),'analytics_path':str(ap),**payload}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('experiment'); ap.add_argument('--stage',default='development'); ap.add_argument('--batch'); a=ap.parse_args()
    try:r=score(a.experiment,a.stage,a.batch)
    except Exception as e: print(f'ERROR: {e}',file=sys.stderr); return 1
    print(json.dumps(r,indent=2,ensure_ascii=False,allow_nan=False));return 0
if __name__=='__main__': raise SystemExit(main())
