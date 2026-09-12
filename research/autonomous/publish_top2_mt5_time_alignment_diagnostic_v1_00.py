#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess
from pathlib import Path


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',required=True)
    ap.add_argument('--publisher',required=True)
    args=ap.parse_args()
    p=Path(args.input)
    if not p.exists():
        raise RuntimeError(f'missing diagnostic artifact: {p}')
    x=json.loads(p.read_text(encoding='utf-8'))
    if x.get('schema') != 1 or x.get('phase') != 'top2-mt5-time-alignment-diagnostic':
        raise RuntimeError('unexpected diagnostic schema/phase')
    if x.get('protected_2026_opened') is not False:
        raise RuntimeError('protected 2026 status is not explicitly false')
    expected={'R6B-347','R6B-307'}
    if set(x.get('candidates',{})) != expected:
        raise RuntimeError('candidate set mismatch')
    summaries=[]
    for cid in sorted(expected):
        for year in ('2024','2025'):
            y=x['candidates'][cid]['years'][year]
            rows=y.get('shift_match_table',[])
            if not rows:
                raise RuntimeError(f'no shift table for {cid} {year}')
            best=max(rows,key=lambda r:(int(r.get('exact_pair_matches',0)),int(r.get('exact_entry_matches',0))))
            summaries.append(f"{cid} {year}: best_shift={best['shift_hours']}h pair={best['exact_pair_matches']}/{best['canonical_trades']} entry={best['exact_entry_matches']}/{best['canonical_trades']}")
    summary='; '.join(summaries) + '; infrastructure timestamp-alignment diagnosis only; frozen R6 hypotheses unchanged; 2026 unopened.'
    cmd=['python',args.publisher,'--phase','top2-mt5-time-alignment-diagnostic','--status','PASS','--summary',summary,'--artifact',str(p)]
    subprocess.run(cmd,check=True)
    print(json.dumps({'status':'PASS','published_phase':'top2-mt5-time-alignment-diagnostic','protected_2026_opened':False,'summary':summary}))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
