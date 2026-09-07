#!/usr/bin/env python3
"""One-command operational workflow for preregistered D032-M2 management validation.

D041 uses a paired candidate-vs-reference scorer whose schema is intentionally
not the generic entry-strategy score/rich schema. Therefore this workflow must
never pass D041 paired analytics to publisher.publish_bundle(). Score and paired
analytics are published as immutable result events; the final specialized event
is the archive receipt. No MT5 rerun is warranted for a post-score transport or
archive failure.
"""
from __future__ import annotations
import argparse, json, sys
from typing import Any
import campaign, paired_management_score, result_transport

def run(identifier:str, stage:str)->dict[str,Any]:
    if stage=='smoke':
        return campaign.run_campaign([identifier], 'smoke', finalize_development=False)
    if stage!='development':
        raise ValueError('D041 workflow supports smoke and development (scientific POST2024 validation) only')

    base=campaign.run_campaign([identifier], 'development', finalize_development=False)
    exps=base.get('experiments',[])
    if not exps or exps[0].get('status')=='EXPERIMENT_ENGINEERING_FAILURE':
        return {'status':'D041_ENGINEERING_FAILURE','campaign':base}

    batch_path=exps[0]['batch']['batch_path']
    decision=paired_management_score.score(identifier,'development',batch_path)
    score_transport=result_transport.safe_publish_event(identifier,'development','score',decision)

    analytics_event={
        'schema_version':1,
        'status':'PAIRED_ANALYTICS_COMPLETE',
        'experiment_id':decision['experiment_id'],
        'stage':'development',
        'scientific_role':decision['scientific_role'],
        'verdict':decision['verdict'],
        'metrics':decision['metrics'],
        'gates':decision['gates'],
        'analytics_path':decision['analytics_path'],
        'rich_score_path':decision['analytics_path'],
        'autosync_used':False,
    }
    rich_transport=result_transport.safe_publish_event(identifier,'development','rich-score',analytics_event)

    final={
        'schema_version':1,
        'status':'D041_MANAGEMENT_VALIDATION_COMPLETE',
        'experiment_id':decision['experiment_id'],
        'stage':'development',
        'scientific_role':decision['scientific_role'],
        'verdict':decision['verdict'],
        'all_gates_pass':decision['all_gates_pass'],
        'metrics':decision['metrics'],
        'gates':decision['gates'],
        'verdict_path':decision['verdict_path'],
        'analytics_path':decision['analytics_path'],
        'batch_path':decision['batch_path'],
        'score_transport':score_transport,
        'rich_transport':rich_transport,
        'generic_publisher_used':False,
        'generic_publisher_reason':'D041 paired-management schema is intentionally incompatible with generic entry-strategy bundle schema',
        'base_campaign':base,
        'autosync_used':False,
    }
    final['github_transport']=result_transport.safe_publish_event(identifier,'development','management-finalize',final)
    return final

def main()->int:
    ap=argparse.ArgumentParser(description='Run exact D032-M2 management validation through D041 wrapper')
    ap.add_argument('experiment',nargs='?',default='D041')
    ap.add_argument('--stage',choices=('smoke','development'),default='smoke')
    a=ap.parse_args()
    try:r=run(a.experiment,a.stage)
    except Exception as e:
        print(f'ERROR: {e}',file=sys.stderr)
        return 1
    print(json.dumps(r,indent=2,ensure_ascii=False,allow_nan=False))
    return 0
if __name__=='__main__': raise SystemExit(main())
