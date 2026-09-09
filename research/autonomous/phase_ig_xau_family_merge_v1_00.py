#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd


def atomic_json(path, obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8'); tmp.replace(path)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--policy',required=True); ap.add_argument('--output-dir',required=True); ap.add_argument('--publisher'); args=ap.parse_args()
    policy=json.loads(Path(args.policy).read_text(encoding='utf-8')); root=Path(args.root); out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True)
    rows=[]; family_counts={}
    for fam in policy['families']:
        p=root/fam/f'{fam}_survivors.csv'
        if not p.exists(): raise RuntimeError(f'missing survivor file for {fam}: {p}')
        df=pd.read_csv(p)
        family_counts[fam]=int(len(df))
        if len(df): rows.append(df)
    all_df=pd.concat(rows,ignore_index=True) if rows else pd.DataFrame()
    reps=[]
    if len(all_df):
        all_df['abs_confirmation_effect']=all_df['confirmation_effect'].abs()
        all_df=all_df.sort_values(['family','outcome','horizon_bars','direction','confirmation_q','abs_confirmation_effect','confirmation_n_state'],ascending=[True,True,True,True,True,False,False])
        reps=all_df.groupby(['family','outcome','horizon_bars','direction'],as_index=False,sort=False).head(1).copy()
        reps=reps.sort_values(['confirmation_q','abs_confirmation_effect','confirmation_n_state'],ascending=[True,False,False]).reset_index(drop=True)
    all_path=out/'phase_ig_all_survivors.csv'; rep_path=out/'phase_ig_independent_representatives.csv'; sum_path=out/'phase_ig_summary.json'
    all_df.to_csv(all_path,index=False); reps.to_csv(rep_path,index=False)
    summary={'schema':1,'phase':'I-G','status':'PASS','protected_2026_untouched':True,'family_survivors':family_counts,'all_survivors':int(len(all_df)),'independent_representatives':int(len(reps)),'generated_at_utc':datetime.now(timezone.utc).isoformat(),'next_rule':'Representatives are phenomenon candidates only; next step is frozen robustness/confirmation, not PnL or OOS.'}
    atomic_json(sum_path,summary)
    if args.publisher:
        cmd=[sys.executable,args.publisher,'--phase','phase-ig-xau-simple-independent-families','--status','PASS','--summary',f"Phase I-G merged: all_survivors={len(all_df)} independent_representatives={len(reps)}; 2026 untouched."]
        for p in [sum_path,all_path,rep_path,args.policy]:
            if Path(p).exists(): cmd += ['--artifact',str(p)]
        rc=subprocess.run(cmd,text=True,capture_output=True).returncode
        if rc!=0: raise RuntimeError(f'publisher exit {rc}')
if __name__=='__main__': main()
