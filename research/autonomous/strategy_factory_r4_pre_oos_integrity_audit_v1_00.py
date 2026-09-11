#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, random, subprocess
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

PROTECTED = pd.Timestamp('2026-01-01', tz='UTC')


def atomic_json(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def hb(path, done, total, stage, extra=None):
    if not path: return
    x = {'completed': int(done), 'total': int(total), 'stage': stage, 'updated_at_utc': datetime.now(timezone.utc).isoformat()}
    if extra: x.update(extra)
    atomic_json(path, x)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def norm(s): return ''.join(c for c in str(s).lower().strip() if c.isalnum() or c == '_')

def find_col(cols, names):
    m = {norm(c): c for c in cols}
    for n in names:
        if n in m: return m[n]
    return None


def detect(path):
    h = pd.read_csv(path, nrows=3); c = list(h.columns)
    m = {'open': find_col(c, ['open','o']), 'high': find_col(c, ['high','h']), 'low': find_col(c, ['low','l']), 'close': find_col(c, ['close','c']),
         'time': find_col(c, ['server_time','time','datetime','timestamp','date']), 'epoch': find_col(c, ['server_epoch','epoch','unix','unix_time']),
         'volume': find_col(c, ['tick_volume','tickvolume','volume','vol'])}
    if not (all(m[k] for k in ['open','high','low','close']) and (m['time'] or m['epoch'])):
        raise RuntimeError(f'unsupported OHLC schema: {path}')
    return m


def load_market(path, max_rows):
    m = detect(path); df = pd.read_csv(path)
    if len(df) > max_rows: df = df.iloc[-max_rows:].copy()
    if m['epoch']:
        x = pd.to_numeric(df[m['epoch']], errors='coerce'); med = float(x.dropna().median()) if x.notna().any() else 0
        t = pd.to_datetime(x, unit='ms' if med > 1e11 else 's', utc=True, errors='coerce')
    else:
        t = pd.to_datetime(df[m['time']].astype(str), utc=True, errors='coerce', format='mixed')
    z = pd.DataFrame({'time': t, 'open': pd.to_numeric(df[m['open']], errors='coerce'), 'high': pd.to_numeric(df[m['high']], errors='coerce'),
                      'low': pd.to_numeric(df[m['low']], errors='coerce'), 'close': pd.to_numeric(df[m['close']], errors='coerce')})
    if m['volume']: z['volume'] = pd.to_numeric(df[m['volume']], errors='coerce')
    z = z.dropna(subset=['time','open','high','low','close']).sort_values('time').drop_duplicates('time')
    if (z.time >= PROTECTED).any(): z = z[z.time < PROTECTED]
    return z.reset_index(drop=True)


def rsi(c, n):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1/n, adjust=False, min_periods=n).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    rs = up / dn.replace(0, np.nan); return 100 - 100 / (1 + rs)


def features(df):
    prev = df.close.shift(1); tr = pd.concat([(df.high-df.low).abs(), (df.high-prev).abs(), (df.low-prev).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean().replace(0, np.nan)
    f = pd.DataFrame(index=df.index)
    for k in [1,3,6,12,24,48]: f[f'ret{k}'] = (df.close-df.close.shift(k))/atr
    f['range']=(df.high-df.low)/atr; f['body']=(df.close-df.open)/atr
    f['uwick']=(df.high-np.maximum(df.open,df.close))/atr; f['lwick']=(np.minimum(df.open,df.close)-df.low)/atr
    f['rsi7']=rsi(df.close,7); f['rsi14']=rsi(df.close,14)
    for n in [5,10,20,50,100]: f[f'sma{n}']=(df.close-df.close.rolling(n,min_periods=n).mean())/atr
    f['atr_regime']=atr/tr.rolling(50,min_periods=50).mean().replace(0,np.nan)
    f['hour']=df.time.dt.hour.astype(float); f['dow']=df.time.dt.dayofweek.astype(float)
    if 'volume' in df:
        vm=df.volume.rolling(48,min_periods=48).mean(); vs=df.volume.rolling(48,min_periods=48).std().replace(0,np.nan); f['volz']=(df.volume-vm)/vs
    return f, atr


def base_mask(df, r):
    m = np.ones(len(df), dtype=bool)
    if r.get('hour_start') is not None:
        hh=df.time.dt.hour.to_numpy(); st=int(r['hour_start']); w=int(r['hour_width'])
        m &= np.array([((int(v)-st)%24) < w for v in hh])
    return m


def selected_mask(df, ft, r):
    x=ft[r['feature']].to_numpy(float); cut=float(r['cutpoint'])
    cond=(x>cut) if r['operator']=='gt' else (x<cut)
    return base_mask(df,r) & cond


def forward_return_same_year(df, atr, h, direction):
    future = df.close.shift(-h)
    ret = ((future-df.close)/atr).to_numpy(float) * int(direction)
    current_year = df.time.dt.year.to_numpy()
    target_year = df.time.shift(-h).dt.year.to_numpy()
    ret[current_year != target_year] = np.nan
    return ret


def edge_stats(sel, base, ret, mask, min_sel=20, min_base=100):
    v = mask & base & np.isfinite(ret)
    a=ret[v & sel]; b=ret[v & (~sel)]
    if len(a)<min_sel or len(b)<min_base: return None
    return {'n_selected':int(len(a)), 'n_baseline':int(len(b)), 'selected_mean_atr':float(np.mean(a)),
            'baseline_mean_atr':float(np.mean(b)), 'edge_atr':float(np.mean(a)-np.mean(b))}


def daily_block_bootstrap(df, sel, base, ret, year, reps, seed):
    mask=(df.time.dt.year.to_numpy()==year) & base & np.isfinite(ret)
    days=df.time.dt.floor('D').to_numpy(); unique=np.unique(days[mask]); blocks=[]
    for d in unique:
        ix=mask & (days==d); a=ret[ix & sel]; b=ret[ix & (~sel)]
        if len(a)+len(b): blocks.append((a,b))
    if len(blocks)<30: return None
    rng=random.Random(seed); vals=[]
    for _ in range(reps):
        aa=[]; bb=[]
        for _j in range(len(blocks)):
            a,b=blocks[rng.randrange(len(blocks))]
            if len(a): aa.append(a)
            if len(b): bb.append(b)
        if not aa or not bb: continue
        A=np.concatenate(aa); B=np.concatenate(bb)
        if len(A)>=20 and len(B)>=100: vals.append(float(np.mean(A)-np.mean(B)))
    if len(vals)<max(200, reps//2): return None
    ar=np.array(vals,float)
    return {'reps_valid':int(len(ar)), 'edge_p05':float(np.quantile(ar,0.05)), 'edge_median':float(np.median(ar)), 'edge_p95':float(np.quantile(ar,0.95))}


def publish(publisher, phase, status, summary, artifacts):
    if not publisher: return
    cmd=['python',publisher,'--phase',phase,'--status',status,'--summary',summary]
    for a in artifacts: cmd += ['--artifact',str(a)]
    subprocess.run(cmd, check=True)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--frozen-json', required=True); ap.add_argument('--policy', required=True); ap.add_argument('--output-dir', required=True)
    ap.add_argument('--progress-file'); ap.add_argument('--publisher'); ap.add_argument('--max-rows', type=int, default=900000)
    args=ap.parse_args(); out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True); progress=Path(args.progress_file) if args.progress_file else None
    policy=json.loads(Path(args.policy).read_text(encoding='utf-8')); frozen_path=Path(args.frozen_json)
    if sha256_file(frozen_path) != policy['expected_frozen_json_sha256']: raise RuntimeError('frozen candidate JSON SHA256 mismatch')
    frozen=json.loads(frozen_path.read_text(encoding='utf-8')); candidates=frozen['candidates']
    if len(candidates) != int(policy['expected_candidate_count']): raise RuntimeError('frozen candidate count mismatch')
    sigs=set(); datasets={}; results=[]; survivors=[]; hb(progress,0,len(candidates),'preflight')
    for i,r in enumerate(candidates):
        sig=(r['dataset'],r['feature'],r['operator'],float(r['cutpoint']),int(r['horizon_bars']),int(r['direction']),r.get('hour_start'),r.get('hour_width'))
        if sig in sigs: raise RuntimeError('duplicate frozen candidate signature')
        sigs.add(sig); p=r['dataset']
        if p not in datasets:
            df=load_market(p,args.max_rows)
            if (df.time>=PROTECTED).any(): raise RuntimeError('protected 2026 row survived loader')
            ft,atr=features(df); datasets[p]=(df,ft,atr)
        df,ft,atr=datasets[p]; sel=selected_mask(df,ft,r); base=base_mask(df,r); h=int(r['horizon_bars']); ret=forward_return_same_year(df,atr,h,int(r['direction'])); y=df.time.dt.year.to_numpy(); mo=df.time.dt.month.to_numpy()
        y24=edge_stats(sel,base,ret,y==2024,min_sel=20,min_base=100); y25=edge_stats(sel,base,ret,y==2025,min_sel=40,min_base=200)
        quarters=[]; quarters_ok=True
        for q,(lo,hi) in enumerate(((1,3),(4,6),(7,9),(10,12)),1):
            qs=edge_stats(sel,base,ret,(y==2025)&(mo>=lo)&(mo<=hi),min_sel=int(policy['quarter_min_selected']),min_base=int(policy['quarter_min_baseline']))
            quarters.append({'quarter':q,'stats':qs})
            if qs is None or qs['edge_atr']<=0: quarters_ok=False
        bs=daily_block_bootstrap(df,sel,base,ret,2025,int(policy['bootstrap_reps']),int(policy['bootstrap_seed'])+i)
        pass_gate=bool(y24 and y25 and y24['edge_atr']>0 and y25['edge_atr']>0 and quarters_ok and bs and bs['edge_p05']>0)
        rr={'candidate_index':i,'signature':list(sig),'purged_2024':y24,'purged_2025':y25,'y2025_quarters':quarters,'daily_block_bootstrap_2025':bs,'pass':pass_gate}
        results.append(rr)
        if pass_gate: survivors.append({'candidate_index':i,'candidate':r,'audit':rr})
        hb(progress,i+1,len(candidates),'audit',{'survivors_so_far':len(survivors)})
    report={'schema':1,'generated_at_utc':datetime.now(timezone.utc).isoformat(),'purpose':'reject-only pre-OOS integrity/robustness audit of frozen R4 candidates',
            'protected_2026_untouched':True,'frozen_json_sha256':sha256_file(frozen_path),'candidate_count':len(candidates),'survivor_count':len(survivors),
            'rules_not_retuned':True,'strict_same_calendar_year_forward_outcomes':True,'results':results}
    rp=out/'pre_oos_integrity_audit.json'; atomic_json(rp,report); sp=out/'pre_oos_audit_survivors.json'
    atomic_json(sp,{'schema':1,'source_frozen_json_sha256':sha256_file(frozen_path),'survivor_count':len(survivors),'survivors':survivors})
    status='PASS' if survivors else 'FAIL'; summary=f'{len(survivors)}/{len(candidates)} frozen R4 candidates survive reject-only purged-year, 2025 quarter-sign and daily-block-bootstrap audit; no retuning; 2026 untouched.'
    hb(progress,len(candidates),len(candidates),'complete',{'survivors':len(survivors),'status':status})
    publish(args.publisher,'strategy-factory-r4-pre-oos-integrity-audit',status,summary,[rp,sp,Path(args.policy)])
    print(json.dumps({'status':status,'survivors':len(survivors),'candidates':len(candidates),'protected_2026_untouched':True})); return 0

if __name__=='__main__': raise SystemExit(main())
