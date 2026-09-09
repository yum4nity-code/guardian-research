#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, math, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd


def atomic_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    tmp.replace(path)

def heartbeat(path: Path | None, completed: int, total: int, stage: str):
    if path:
        atomic_json(path, {'completed': int(completed), 'total': int(total), 'stage': stage, 'updated_at_utc': datetime.now(timezone.utc).isoformat()})

def load_module(path: str):
    spec = importlib.util.spec_from_file_location('phase_ic_engine', path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod

def bh_adjust(rows, pkey='p', qkey='q'):
    vals = sorted([(i, float(r[pkey])) for i, r in enumerate(rows) if r.get(pkey) is not None and math.isfinite(float(r[pkey]))], key=lambda x: x[1])
    m = len(vals); prev = 1.0
    for rank in range(m, 0, -1):
        idx, p = vals[rank-1]
        q = min(prev, p*m/rank, 1.0)
        rows[idx][qkey] = q; prev = q
    for r in rows: r.setdefault(qkey, None)

def ctest(values, mask):
    finite = np.isfinite(values); a = values[mask & finite]; b = values[(~mask) & finite]
    if len(a) < 2 or len(b) < 2: return None
    ma, mb = float(np.mean(a)), float(np.mean(b)); va, vb = float(np.var(a, ddof=1)), float(np.var(b, ddof=1))
    se = math.sqrt(va/len(a) + vb/len(b)); z = (ma-mb)/se if se > 0 else 0.0
    return {'n_state': len(a), 'n_comp': len(b), 'effect': ma-mb, 'state_mean': ma, 'comp_mean': mb, 'p': math.erfc(abs(z)/math.sqrt(2.0))}

def btest(values, mask):
    finite = np.isfinite(values); a = values[mask & finite]; b = values[(~mask) & finite]
    if len(a) < 2 or len(b) < 2: return None
    pa, pb = float(np.mean(a)), float(np.mean(b)); pooled = (float(np.sum(a))+float(np.sum(b)))/(len(a)+len(b))
    se = math.sqrt(max(0.0, pooled*(1-pooled)*(1/len(a)+1/len(b)))); z = (pa-pb)/se if se > 0 else 0.0
    return {'n_state': len(a), 'n_comp': len(b), 'effect': pa-pb, 'state_mean': pa, 'comp_mean': pb, 'p': math.erfc(abs(z)/math.sqrt(2.0))}

def test(df, col, mask, outcome):
    vals = df[col].to_numpy(float)
    return ctest(vals, mask) if outcome == 'mean_fwd_ret_atr' else btest(vals, mask)

def publish(publisher, phase, status, summary, artifacts):
    if not publisher: return 0
    cmd = [sys.executable, publisher, '--phase', phase, '--status', status, '--summary', summary]
    for a in artifacts:
        if Path(a).exists(): cmd += ['--artifact', str(a)]
    return subprocess.run(cmd, text=True, capture_output=True).returncode

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ib-dir', required=True); ap.add_argument('--policy', required=True); ap.add_argument('--ic-engine', required=True)
    ap.add_argument('--family', required=True); ap.add_argument('--output-dir', required=True); ap.add_argument('--progress-file')
    ap.add_argument('--publisher'); args = ap.parse_args()
    policy = json.loads(Path(args.policy).read_text(encoding='utf-8'))
    if policy.get('protected_2026_forbidden') is not True: raise RuntimeError('policy must forbid protected 2026')
    if args.family not in policy['families']: raise RuntimeError(f'unknown family {args.family}')
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True); hb = Path(args.progress_file) if args.progress_file else None
    ib = Path(args.ib_dir); integ = json.loads((ib/'phase_ib_integrity.json').read_text(encoding='utf-8')); summ = json.loads((ib/'phase_ib_summary.json').read_text(encoding='utf-8'))
    if integ.get('status') != 'PASS' or summ.get('protected_2026_untouched') is not True: raise RuntimeError('Phase I-B clean provenance required')
    data = ib/'xauusd_m5_2024_2025_news_clean.csv'; heartbeat(hb, 0, 100, 'load_2024_2025')
    df = pd.read_csv(data)
    if not df.server_time.astype(str).str.startswith(('2024.','2025.')).all(): raise RuntimeError('out-of-window row present')
    ic = load_module(args.ic_engine)
    df = df.sort_values('server_epoch').reset_index(drop=True); df['year'] = df.server_time.str[:4].astype(int); df['quarter'] = pd.to_datetime(df.server_time, format='%Y.%m.%d %H:%M:%S').dt.quarter
    df = ic.build_features(df); df = ic.add_labels(df, policy['horizons_bars']); d24 = df[df.year==2024].copy(); d25 = df[df.year==2025].copy(); heartbeat(hb, 20, 100, 'features_labels')
    features = policy['families'][args.family]; raw = []; tests_total = len(features)*5*7*len(policy['horizons_bars'])*3; done = 0
    for f in features:
        cuts = ic.fit_cutpoints(d24[f])
        if cuts is None: continue
        q24 = ic.assign_q(d24[f], cuts); q25 = ic.assign_q(d25[f], cuts)
        for q in range(5):
            for hblock in [None,0,1,2,3,4,5]:
                m24 = q24 == q; m25 = q25 == q
                if hblock is not None:
                    m24 = m24 & (d24.hour_block.to_numpy()==hblock); m25 = m25 & (d25.hour_block.to_numpy()==hblock)
                for h in policy['horizons_bars']:
                    for outcome in policy['outcomes']:
                        col = {'mean_fwd_ret_atr':f'fwd_ret_atr_h{h}','move_ge_1atr':f'move_ge_1atr_h{h}','up_first_1atr':f'up_first_1atr_h{h}'}[outcome]
                        r24 = test(d24, col, m24, outcome); done += 1
                        if r24 and r24['n_state'] >= policy['min_state_n_discovery'] and abs(r24['effect']) >= policy['minimum_absolute_effect'][outcome]:
                            raw.append({'family':args.family,'feature':f,'quintile':q+1,'hour_block':hblock,'horizon_bars':h,'outcome':outcome,**r24,'_m25':m25,'_col':col})
                        if done % 100 == 0: heartbeat(hb, 20 + int(40*done/max(1,tests_total)), 100, 'discovery')
    groups = {}
    for r in raw: groups.setdefault((r['outcome'], r['horizon_bars']), []).append(r)
    shortlist = []
    for grp in groups.values():
        bh_adjust(grp)
        shortlist.extend([r for r in grp if r['q'] is not None and r['q'] <= policy['discovery_bh_q']])
    heartbeat(hb, 65, 100, 'confirmation')
    confirmed = []
    for r in shortlist:
        r25 = test(d25, r['_col'], r['_m25'], r['outcome'])
        if not r25 or r25['n_state'] < policy['min_state_n_confirmation']: continue
        sign = 1 if r['effect'] > 0 else -1; sign25 = 1 if r25['effect'] > 0 else (-1 if r25['effect'] < 0 else 0)
        if sign25 != sign or abs(r25['effect']) < policy['confirmation_effect_retention_fraction']*abs(r['effect']): continue
        x = {k:v for k,v in r.items() if not k.startswith('_')}; x.update({'confirmation_n_state':r25['n_state'],'confirmation_n_comp':r25['n_comp'],'confirmation_effect':r25['effect'],'confirmation_p':r25['p'],'direction':sign})
        confirmed.append(x)
    cgroups = {}
    for r in confirmed: cgroups.setdefault((r['outcome'],r['horizon_bars']),[]).append(r)
    for grp in cgroups.values():
        temp=[{'p':r['confirmation_p'],'ref':r} for r in grp]; bh_adjust(temp)
        for t in temp: t['ref']['confirmation_q']=t['q']
    survivors=[]
    for r in confirmed:
        if r.get('confirmation_q') is None or r['confirmation_q'] > policy['confirmation_bh_q']: continue
        f=r['feature']; cuts=ic.fit_cutpoints(d24[f]); q25=ic.assign_q(d25[f],cuts); base=(q25==(r['quintile']-1));
        if r['hour_block'] is not None: base &= d25.hour_block.to_numpy()==r['hour_block']
        same=0; qdetails={}
        col={'mean_fwd_ret_atr':f"fwd_ret_atr_h{r['horizon_bars']}",'move_ge_1atr':f"move_ge_1atr_h{r['horizon_bars']}",'up_first_1atr':f"up_first_1atr_h{r['horizon_bars']}"}[r['outcome']]
        for quarter in (1,2,3,4):
            qm=base & (d25.quarter.to_numpy()==quarter); rr=test(d25,col,qm,r['outcome'])
            ok=bool(rr and rr['n_state']>=policy['min_state_n_quarter'] and ((rr['effect']>0)-(rr['effect']<0))==r['direction'])
            same += int(ok); qdetails[str(quarter)]={'ok':ok,'n_state': rr['n_state'] if rr else 0,'effect': rr['effect'] if rr else None}
        if same >= policy['quarters_same_sign_required']:
            r['quarters_same_sign']=same; r['quarter_details']=json.dumps(qdetails,sort_keys=True); survivors.append(r)
    survivors.sort(key=lambda r:(r['confirmation_q'], -abs(r['confirmation_effect']), -r['confirmation_n_state']))
    raw_path=out/f'{args.family}_shortlist.csv'; surv_path=out/f'{args.family}_survivors.csv'; sum_path=out/f'{args.family}_summary.json'
    pd.DataFrame([{k:v for k,v in r.items() if not k.startswith('_')} for r in shortlist]).to_csv(raw_path,index=False)
    pd.DataFrame(survivors).to_csv(surv_path,index=False)
    summary={'schema':1,'phase':'I-G','family':args.family,'protected_2026_untouched':True,'features':features,'discovery_shortlist':len(shortlist),'confirmed_before_quarter_gate':len(confirmed),'survivors':len(survivors),'generated_at_utc':datetime.now(timezone.utc).isoformat(),'status':'PASS'}
    atomic_json(sum_path,summary); heartbeat(hb,100,100,'complete')
    phase=f'phase-ig-xau-{args.family.replace("_","-")}'
    rc=publish(args.publisher,phase,'PASS',f"Phase I-G {args.family}: shortlist={len(shortlist)} confirmed={len(confirmed)} survivors={len(survivors)}; 2026 untouched.",[sum_path,raw_path,surv_path,args.policy])
    if rc != 0: raise RuntimeError(f'publisher exit {rc}')

if __name__ == '__main__': main()
