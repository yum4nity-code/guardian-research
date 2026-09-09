#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, math, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd


def atomic_json(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8'); tmp.replace(path)
def load_module(path):
    spec=importlib.util.spec_from_file_location('ic',path); mod=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(mod); return mod
def ctest(values,mask):
    finite=np.isfinite(values); a=values[mask & finite]; b=values[(~mask)&finite]
    if len(a)<2 or len(b)<2:return None
    return {'n_state':len(a),'n_comp':len(b),'effect':float(np.mean(a)-np.mean(b))}
def btest(values,mask):
    finite=np.isfinite(values); a=values[mask & finite]; b=values[(~mask)&finite]
    if len(a)<2 or len(b)<2:return None
    return {'n_state':len(a),'n_comp':len(b),'effect':float(np.mean(a)-np.mean(b))}
def test(df,col,mask,outcome):
    return ctest(df[col].to_numpy(float),mask) if outcome=='mean_fwd_ret_atr' else btest(df[col].to_numpy(float),mask)
def sign(x): return 1 if x>0 else (-1 if x<0 else 0)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--ib-dir',required=True); ap.add_argument('--ig-representatives',required=True); ap.add_argument('--policy',required=True); ap.add_argument('--ic-engine',required=True); ap.add_argument('--output-dir',required=True); ap.add_argument('--publisher'); args=ap.parse_args()
    pol=json.loads(Path(args.policy).read_text(encoding='utf-8'))
    if pol.get('protected_2026_forbidden') is not True: raise RuntimeError('policy must forbid 2026')
    reps=pd.read_csv(args.ig_representatives); out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True)
    ib=Path(args.ib_dir); df=pd.read_csv(ib/'xauusd_m5_2024_2025_news_clean.csv')
    if not df.server_time.astype(str).str.startswith(('2024.','2025.')).all(): raise RuntimeError('out-of-window row present')
    ic=load_module(args.ic_engine); df=df.sort_values('server_epoch').reset_index(drop=True); df['year']=df.server_time.str[:4].astype(int); dt=pd.to_datetime(df.server_time,format='%Y.%m.%d %H:%M:%S'); df['month']=dt.dt.month; df=ic.build_features(df); df=ic.add_labels(df,[3,6,12,24]); d24=df[df.year==2024].copy(); d25=df[df.year==2025].copy()
    gates=pol['gates']; rows=[]
    for _,r in reps.iterrows():
        f=str(r['feature']); cuts=ic.fit_cutpoints(d24[f]); q25=ic.assign_q(d25[f],cuts); mask=q25==(int(r['quintile'])-1)
        hb=r.get('hour_block');
        if pd.notna(hb): mask &= d25.hour_block.to_numpy()==int(hb)
        h=int(r['horizon_bars']); outcome=str(r['outcome']); col={'mean_fwd_ret_atr':f'fwd_ret_atr_h{h}','move_ge_1atr':f'move_ge_1atr_h{h}','up_first_1atr':f'up_first_1atr_h{h}'}[outcome]
        full=test(d25,col,mask,outcome)
        if not full: continue
        s=sign(full['effect']); half_details={}; halves_ok=0
        for name,months in [('H1',{1,2,3,4,5,6}),('H2',{7,8,9,10,11,12})]:
            hm=mask & d25.month.isin(months).to_numpy(); rr=test(d25,col,hm,outcome); ok=bool(rr and rr['n_state']>=gates['minimum_halfyear_n'] and sign(rr['effect'])==s and abs(rr['effect'])>=gates['minimum_effect_retention_fraction_vs_full_2025']*abs(full['effect'])); halves_ok+=int(ok); half_details[name]={'ok':ok,'n_state':rr['n_state'] if rr else 0,'effect':rr['effect'] if rr else None}
        month_details={}; months_ok=0
        for m in range(1,13):
            mm=mask & (d25.month.to_numpy()==m); rr=test(d25,col,mm,outcome); ok=bool(rr and rr['n_state']>=gates['minimum_month_n'] and sign(rr['effect'])==s); months_ok+=int(ok); month_details[str(m)]={'ok':ok,'n_state':rr['n_state'] if rr else 0,'effect':rr['effect'] if rr else None}
        passed=bool(full['n_state']>=gates['minimum_confirmation_n'] and halves_ok>=gates['halves_same_sign_required'] and months_ok>=gates['months_same_sign_required'])
        row=dict(r); row.update({'robustness_full_n':full['n_state'],'robustness_full_effect':full['effect'],'halves_same_sign':halves_ok,'months_same_sign':months_ok,'half_details':json.dumps(half_details,sort_keys=True),'month_details':json.dumps(month_details,sort_keys=True),'robustness_pass':passed}); rows.append(row)
    res=pd.DataFrame(rows); pass_df=res[res.robustness_pass==True].copy() if len(res) else pd.DataFrame()
    all_path=out/'phase_ih_all_candidates.csv'; pass_path=out/'phase_ih_robust_survivors.csv'; sum_path=out/'phase_ih_summary.json'; res.to_csv(all_path,index=False); pass_df.to_csv(pass_path,index=False)
    summary={'schema':1,'phase':'I-H','status':'PASS','protected_2026_untouched':True,'tested':int(len(res)),'robust_survivors':int(len(pass_df)),'generated_at_utc':datetime.now(timezone.utc).isoformat(),'next_rule':'Robust survivors remain phenomenon candidates; no strategy/PnL claim until later frozen validation.'}; atomic_json(sum_path,summary)
    if args.publisher:
        cmd=[sys.executable,args.publisher,'--phase','phase-ih-xau-simple-robustness','--status','PASS','--summary',f"Phase I-H robustness: tested={len(res)} robust_survivors={len(pass_df)}; 2026 untouched."]
        for p in [sum_path,all_path,pass_path,args.policy]:
            if Path(p).exists(): cmd += ['--artifact',str(p)]
        rc=subprocess.run(cmd,text=True,capture_output=True).returncode
        if rc!=0: raise RuntimeError(f'publisher exit {rc}')
if __name__=='__main__': main()
