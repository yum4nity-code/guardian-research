#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, os
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import r6_xau_low_turnover_breakout_v1_00 as r6

CANDIDATES=("R6B-347","R6B-307")


def atomic_json(path:Path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    os.replace(tmp,path)


def fmt(ts):
    t=pd.Timestamp(ts)
    if t.tzinfo is not None:
        t=t.tz_convert('UTC').tz_localize(None)
    return t.strftime('%Y.%m.%d %H:%M:%S')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--phase-ib-root',required=True)
    ap.add_argument('--common-dir',required=True)
    ap.add_argument('--output-dir',required=True)
    args=ap.parse_args()
    ib=Path(args.phase_ib_root); common=Path(args.common_dir); out=Path(args.output_dir)
    common.mkdir(parents=True,exist_ok=True); out.mkdir(parents=True,exist_ok=True)

    source_all=r6.load_exact(ib/'xauusd_m5_2024_2025_news_clean.csv')
    raw_all=r6.load_exact(ib/'xauusd_m1_2024_2025_raw.csv')
    rules={x['candidate_id']:x for x in r6.definition_grid()}
    manifest={'schema':1,'generated_at_utc':datetime.now(timezone.utc).isoformat(),'protected_2026_opened':False,'source_hashes':r6.EXPECTED,'candidates':{}}

    for cid in CANDIDATES:
        rule=rules[cid]; rows=[]
        for year in (2024,2025):
            src=r6.year_slice(source_all,year); raw=r6.year_slice(raw_all,year)
            ledger,_,_=r6.evaluate_year(rule,src,raw,year)
            for t in ledger:
                e=pd.Timestamp(t['entry_time']); x=pd.Timestamp(t['exit_time'])
                if e.year not in (2024,2025) or x.year not in (2024,2025):
                    raise RuntimeError(f'forbidden schedule boundary for {cid}: {e} -> {x}')
                rows.append((cid,fmt(e),fmt(x)))
        rows.sort(key=lambda z:(z[1],z[2]))
        target=common/f'{cid}_SCHEDULE.csv'
        with target.open('w',newline='',encoding='ascii') as f:
            w=csv.writer(f,delimiter=';'); w.writerow(['candidate_id','entry_time','exit_time']); w.writerows(rows)
        copy=out/f'{cid}_SCHEDULE.csv'; copy.write_bytes(target.read_bytes())
        manifest['candidates'][cid]={'schedule_rows':len(rows),'schedule_file':str(target),'frozen_rule':{k:rule[k] for k in ('candidate_id','lookback_bars','buffer_atr','horizon_bars','session','session_start','session_end','direction_name','direction')}}

    mp=out/'canonical_replay_schedule_manifest.json'; atomic_json(mp,manifest)
    print(json.dumps({'status':'PASS','protected_2026_opened':False,'candidates':{k:v['schedule_rows'] for k,v in manifest['candidates'].items()}}))
    return 0

if __name__=='__main__': raise SystemExit(main())
