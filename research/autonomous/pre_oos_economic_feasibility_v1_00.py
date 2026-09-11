"""Frozen PRE-OOS feasibility screen. No discovery, broker connection or OOS chain.

Market readers consume verified bytes only. All executable input paths are literal
and hash-pinned. See protocol v2 for limits of this reference-price simulation.
"""
from __future__ import annotations
import argparse
import builtins
import ctypes
from ctypes import wintypes
import hashlib
import io
import json
import math
import os
from pathlib import Path
import stat
import sys
import threading
import time
from datetime import datetime, timezone
import numpy as np
import numpy.ma  # Eager dependency load before the file-access fence.
import numpy.rec
import pandas as pd
from pre_oos_r4_features_v1_00 import features, apply_rule

KERNEL = None
if os.name == 'nt':
    import msvcrt
    KERNEL = ctypes.WinDLL('kernel32',use_last_error=True)
    KERNEL.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    KERNEL.CreateFileW.restype=wintypes.HANDLE
    KERNEL.GetFinalPathNameByHandleW.argtypes=[wintypes.HANDLE,wintypes.LPWSTR,wintypes.DWORD,wintypes.DWORD]
    KERNEL.CloseHandle.argtypes=[wintypes.HANDLE]

VERSION = 'pre_oos_economic_feasibility_v1_00'
BASE = Path(__file__).resolve().parents[2]
SPEC = BASE/'research/protocols/pre_oos_economic_feasibility_screen_v2'
BOUNDARY = int(pd.Timestamp('2026-01-01', tz='UTC').timestamp())
START = int(pd.Timestamp('2024-01-01', tz='UTC').timestamp())
SIGNATURE_FIELDS = ('dataset','feature','operator','quantile','cutpoint','horizon_bars','direction','hour_start','hour_width')
PERIODS = {'2024':('2024-01-01','2025-01-01'), '2025':('2025-01-01','2026-01-01'),
           '2025_H1':('2025-01-01','2025-07-01'), '2025_H2':('2025-07-01','2026-01-01')}
PROFILES = {'E1':(0.000007,0.0002,0.0001), 'STRESS':(0.000014,0.0005,0.0002)}
MARKETS = {
 r'D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_ib_v1\xauusd_m1_2024_2025_raw.csv':'f98a395961b27ca9dcb34cffa4ef8dd93720adb70292abf7bc96108667232445',
 r'D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_ib_v1\xauusd_m1_2024_2025_news_clean.csv':'b116c61d0be7d73c455f4a4f897efdf0bf77a2b88594ed4b93ebee0d707570ee',
 r'D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_ib_v1\xauusd_m5_2024_2025_raw.csv':'ba54c9b29755eac4284cb872805148736be529e954533c028e7f826bb444ce66',
 r'D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_ib_v1\xauusd_m5_2024_2025_news_clean.csv':'972ecaf6c3cadf7136363f396d7a29e7a6246646b575fad5c3e677036004b503',
}
SOURCE = r'D:\MT5_Backtests\Research\Autonomous\strategy_factory_r4_conditional_edge\strategy_factory_result.json'
SOURCE_HASH = '7cb29f3251fa0c1f0d37f719286ba4e51a2446aa0d04d0a7cc3bc53e663b3a48'
FROZEN = r'D:\MT5_Backtests\Research\Autonomous\strategy_factory_r4_consolidated_r2\frozen_candidates.json'
FROZEN_HASH = '37bb6f2d52ef12e7a17a2fd38d94f53ebd94843c3f47500ef36b4c7c76c57e9b'


class BlockedData(RuntimeError):
    pass


def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def signature(rule):
    return {key:rule[key] for key in SIGNATURE_FIELDS}


def pathkey(path):
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def no_links(path):
    """Metadata only. Reject reparse points in every ancestor before file open."""
    p=Path(path)
    for part in (p,*p.parents):
        st=part.lstat()
        if stat.S_ISLNK(st.st_mode) or getattr(st,'st_file_attributes',0)&0x400:
            raise BlockedData(f'reparse/symlink forbidden: {part}')
    if not stat.S_ISREG(p.stat().st_mode):
        raise BlockedData('not a regular input file')


def verified_bytes(path, allowed, accesses):
    """Membership BEFORE metadata/open; lock file against writes/replacement on Windows.

    Hash and parsing use the very same bytes. Final handle path is checked before
    reading, covering replacement of an ancestor after the metadata checks.
    """
    key=pathkey(path)
    permitted={pathkey(k):v for k,v in allowed.items()}
    if key not in permitted:
        accesses.append({'path':key,'status':'DENIED_BEFORE_OPEN'})
        raise BlockedData('input not manifested')
    no_links(path)
    if os.name=='nt':
        kernel=KERNEL
        h=kernel.CreateFileW(str(Path(path).absolute()),0x80000000,1,None,3,0x08000000,None)
        if h==ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            buf=ctypes.create_unicode_buffer(32768)
            n=kernel.GetFinalPathNameByHandleW(h,buf,len(buf),0)
            if not n or n>=len(buf):
                raise BlockedData('cannot verify final handle path')
            final=buf.value
            if final.startswith('\\\\?\\'):
                final=final[4:]
            if pathkey(final)!=key:
                raise BlockedData('handle identity/path changed before read')
            fd=msvcrt.open_osfhandle(h,os.O_RDONLY|os.O_BINARY)
            h=None
            with os.fdopen(fd,'rb') as f:
                data=f.read()
        finally:
            if h is not None:
                kernel.CloseHandle(h)
    else:
        with open(path,'rb') as f:
            data=f.read()
    actual=sha(data)
    if actual!=permitted[key]:
        accesses.append({'path':key,'status':'HASH_MISMATCH','sha256':actual})
        raise BlockedData('input hash mismatch before parsing/use')
    accesses.append({'path':key,'status':'VERIFIED','sha256':actual,'bytes':len(data)})
    return data


class AccessFence:
    """Defense-in-depth Python audit fence, not an OS sandbox claim.

    Native market IO is limited to verified_bytes above; pandas sees BytesIO.
    Existing trusted native libraries are imported before installation. No plugin,
    arbitrary source import or dynamic shared library is allowed afterwards.
    """
    def __init__(self, inputs, output, progress):
        self.reads={pathkey(p) for p in inputs}
        self.output=pathkey(output)+os.sep
        self.progress={pathkey(progress),pathkey(str(progress)+'.tmp')}
        self.denied=[]
    def writable(self,p):
        k=pathkey(p)
        return k.startswith(self.output) or k in self.progress
    def __call__(self,event,args):
        denied=False
        if event=='open':
            p,mode,flags=args
            if isinstance(p,int):
                return  # fd from the fixed native verified reader, no CLI fd input
            write=bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            denied=not (self.writable(p) if write else pathkey(p) in self.reads)
        elif event in ('os.listdir','os.scandir','os.system','subprocess.Popen','ctypes.dlopen') or event.startswith('socket.'):
            denied=True
        elif event in ('os.rename','os.remove','os.rmdir'):
            denied=not all(self.writable(p) for p in args[:2] if isinstance(p,(str,bytes)))
        if denied:
            self.denied.append({'event':event,'path':str(args[0]) if args else ''})
            raise BlockedData('access fence denied '+event)


def atomic_json(path,obj):
    path=Path(path)
    tmp=Path(str(path)+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    delays=(.05,.10,.20,.20,.20)
    for i in range(6):
        try:
            os.replace(tmp,path)
            return
        except PermissionError as exc:
            if i==5:
                raise RuntimeError('atomic JSON replace exhausted six PermissionError attempts: '+str(path)) from exc
            time.sleep(delays[i])


class Heartbeat:
    def __init__(self,path,total):
        self.path=path
        self.lock=threading.Lock()
        self.stop=threading.Event()
        self.error=None
        self.state={'completed':0,'total':total,'candidate':None,'phase':'initializing','provisional_survivors':0}
        self.started=time.monotonic()
        self.thread=threading.Thread(target=self.loop,daemon=True)
    def write(self):
        with self.lock:
            atomic_json(self.path,{**self.state,'updated_at_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-self.started})
    def loop(self):
        try:
            while not self.stop.wait(5):
                self.write()
        except Exception as exc:
            self.error=exc
    def update(self,**kw):
        if self.error:
            raise RuntimeError('background heartbeat failed') from self.error
        with self.lock:
            self.state.update(kw)
        self.write()
    def __enter__(self):
        self.write(); self.thread.start(); return self
    def __exit__(self,*args):
        self.stop.set(); self.thread.join(timeout=10)
        if self.thread.is_alive():
            raise RuntimeError('heartbeat writer did not stop')
        if self.error:
            raise RuntimeError('heartbeat writer failed') from self.error


def parse_market(data,tf):
    df=pd.read_csv(io.BytesIO(data))
    required=['symbol','timeframe','server_time','server_epoch','open','high','low','close','tick_volume']
    if not all(c in df for c in required) or len(df)==0:
        raise BlockedData('missing columns/empty dataset')
    if not df.symbol.eq('XAUUSD').all() or not df.timeframe.eq(tf).all():
        raise BlockedData('symbol/timeframe mismatch')
    nums=df[['server_epoch','open','high','low','close','tick_volume']].apply(pd.to_numeric,errors='raise')
    if not np.isfinite(nums.to_numpy(float)).all():
        raise BlockedData('nonfinite market value')
    ts=nums.server_epoch.to_numpy(float)
    if np.any(ts!=np.floor(ts)) or np.any(np.diff(ts)<=0) or ts[0]<START or ts[-1]>=BOUNDARY:
        raise BlockedData('timestamps not unique/increasing/admitted')
    if np.any(ts % (60 if tf=='M1' else 300)):
        raise BlockedData('unaligned bar timestamp')
    parsed=pd.to_datetime(df.server_time,format='%Y.%m.%d %H:%M:%S',utc=True,errors='raise')
    t=pd.to_datetime(nums.server_epoch,unit='s',utc=True)
    if not parsed.eq(t).all():
        raise BlockedData('time/epoch mismatch')
    z=pd.DataFrame({'time':t,**{c:nums[c] for c in ('open','high','low','close')},'volume':nums.tick_volume})
    if (z[['open','high','low','close']]<=0).any().any() or (z.volume<0).any() or (z.high<z[['open','close','low']].max(axis=1)).any() or (z.low>z[['open','close','high']].min(axis=1)).any():
        raise BlockedData('invalid OHLC/volume')
    return z


def clean_subset(raw,clean):
    a=raw.set_index('time'); b=clean.set_index('time')
    if not b.index.isin(a.index).all() or not np.array_equal(a.loc[b.index].to_numpy(),b.to_numpy()):
        raise BlockedData('clean bars differ from raw apart from causal mask removal')


def news_intersection(bar_start,seconds,event_epoch):
    """Frozen mask interval overlap [bar_start,close) vs [event-5m,event+5m]."""
    return bar_start<=event_epoch+300 and bar_start+seconds>event_epoch-300


def ingest(source,allowed,frozen=None):
    rows=source['survivors']
    if source['survivor_count']!=500 or len(rows)!=500:
        raise BlockedData('expected exactly 500 R4 survivors')
    annotations=set()
    if frozen is not None:
        if len(frozen['candidates'])!=32:
            raise BlockedData('expected 32 annotations')
        annotations={sha(canonical(signature(r))) for r in frozen['candidates']}
    out=[]; seen=set()
    for i,r in enumerate(rows):
        s=signature(r); digest=sha(canonical(s))
        if digest in seen or r['dataset'] not in allowed:
            raise BlockedData('duplicate signature or unmanifested candidate dataset')
        if r['direction'] not in (-1,1) or r['operator'] not in ('gt','lt') or r['horizon_bars'] not in (1,3,6,12,24,48) or not math.isfinite(r['cutpoint']):
            raise BlockedData('malformed frozen rule')
        if r['hour_start'] is not None and (r['hour_start'] not in range(24) or r['hour_width'] not in (2,4,6,8)):
            raise BlockedData('malformed session gate')
        seen.add(digest)
        out.append({'id':f'R4P-{i+1:04d}','signature_sha256':digest,'rule':s,'dataset_kind':'news-clean' if 'news_clean' in r['dataset'] else 'raw','timeframe':'M1' if '_m1_' in r['dataset'] else 'M5','annotation_32':digest in annotations})
    if not annotations<=seen:
        raise BlockedData('annotation not in 500')
    return out


def epochs(df):
    return df.time.array.as_unit('s').asi8


def cost(oe,ox,d,profile):
    c,s,l=PROFILES[profile]
    f=s/2+l; pe=oe*(1+d*f); px=ox*(1-d*f)
    gross=d*(ox-oe); spread=s/2*(oe+ox); slip=l*(oe+ox); comm=c*(pe+px)
    return {'gross':float(gross),'spread':float(spread),'slippage':float(slip),'commission':float(comm),'net':float(gross-spread-slip-comm),'entry_model':float(pe),'exit_model':float(px)}


def period_members(entry,exit):
    return [p for p,(a,b) in PERIODS.items() if entry>=pd.Timestamp(a,tz='UTC').timestamp() and exit<pd.Timestamp(b,tz='UTC').timestamp()]


def exposure_parts(entry,exit):
    total=exit-entry
    overnight=float(total) if entry//86400!=exit//86400 else 0.
    weekend=0
    at=entry
    while at<exit:
        end=min(exit,(at//86400+1)*86400)
        if (at//86400+3)%7>=5:  # Unix epoch Thursday
            weekend+=end-at
        at=end
    return {'seconds':int(total),'overnight_trade_seconds':overnight,'weekend_seconds':int(weekend)}


def replay(df,raw,signals,h,d,tf,admit=None,tick=None):
    """Chronological source-close counter; never inspect a future source row.

    Raw reference lookup is the owner's first-available rule. Pending raw events
    remain pending until their timestamp occurs. A source close decrements the
    horizon exactly once. Exits precede new signals at an equal timestamp.
    """
    st=epochs(df); rt=epochs(raw); opens=raw.open.to_numpy(float)
    signals=np.asarray(signals,dtype=bool)
    admitted=signals if admit is None else signals & admit
    ledger=[]; state=None
    counts={'signals_total':int(signals.sum()),'ignored_overlap_signals':0,'excluded_boundary_trades':0,'missing_reference_trades':0,'BLOCKED_DATA_occurrences':0,'smoke_not_admitted':int(signals.sum()-admitted.sum())}

    def finish(pos):
        ei=pos['ei']; xi=pos['xi']; entry=int(rt[ei]); exit=int(rt[xi])
        if exit<entry:
            raise BlockedData('horizon resolved before entry')
        oe=float(opens[ei]); ox=float(opens[xi])
        # Held bar ranges exclude the exit minute and include the entry minute.
        adverse=raw.low.iloc[ei:xi].to_numpy(float) if d==1 else raw.high.iloc[ei:xi].to_numpy(float)
        rec={'signal_index':pos['i'],'signal':pos['signal'],'available':pos['available'],'entry':entry,'exit_available':pos['exit_available'],'exit':exit,'entry_reference':oe,'exit_reference':ox,'direction':int(d),'horizon_bars':int(h),'periods':period_members(entry,exit),'exposure':exposure_parts(entry,exit),'profiles':{}}
        rec['observed_minutes']=xi-ei
        rec['unobserved_holding_seconds']=max(0,exit-entry-60*(xi-ei))
        for p in PROFILES:
            vals=cost(oe,ox,d,p)
            # Worst observed mark relative to trade entry, including entry/exit.
            worst=float(np.min(adverse)) if d==1 and len(adverse) else (float(np.max(adverse)) if len(adverse) else oe)
            vals['worst_observed_mark']=min(cost(oe,oe,d,p)['net'],cost(oe,worst,d,p)['net'],vals['net'])
            rec['profiles'][p]=vals
        ledger.append(rec)

    for i,bar_time in enumerate(st):
        if tick and i%20000==0:
            tick(source_bars_processed=i)
        a=int(bar_time+tf)
        if state is not None:
            # Process a previously scheduled raw exit only when time reaches it.
            if state['xi'] is not None and state['xi']<len(rt) and rt[state['xi']]<=a:
                finish(state); state=None
            elif state['remaining']>0:
                state['remaining']-=1
                if state['remaining']==0:
                    state['exit_available']=a
                    state['xi']=int(np.searchsorted(rt,a)) if a<BOUNDARY else len(rt)
                    if state['ei']<len(rt) and state['xi']<len(rt) and rt[state['xi']]<=a:
                        finish(state); state=None
        if not admitted[i]:
            continue
        if a>=BOUNDARY:
            counts['excluded_boundary_trades']+=1; continue
        if state is not None:
            counts['ignored_overlap_signals']+=1; continue
        # No future source timestamp is inspected here, including near the end.
        state={'i':int(i),'signal':int(bar_time),'available':a,'remaining':h,'ei':int(np.searchsorted(rt,a)),'xi':None,'exit_available':None}
    if state is not None:
        if state['xi'] is not None and state['xi']<len(rt) and state['ei']<len(rt):
            finish(state)  # admissible raw exit after the final source close
        else:
            counts['excluded_boundary_trades']+=1
            if state['ei']==len(rt) or state['xi']==len(rt):
                counts['missing_reference_trades']+=1
    counts['executable_trades']=len(ledger)
    return ledger,counts


def stats(trades,profile):
    vals=[r['profiles'][profile] for r in trades]
    nets=[v['net'] for v in vals]
    sums={k:float(math.fsum(v[k] for v in vals)) for k in ('gross','spread','slippage','commission','net')}
    wins=math.fsum(x for x in nets if x>0); losses=-math.fsum(x for x in nets if x<0)
    equity=peak=dd=observed_dd=0.
    for v in vals:
        observed_dd=max(observed_dd,peak-(equity+v['worst_observed_mark']))
        equity+=v['net']; peak=max(peak,equity); dd=max(dd,peak-equity)
    best=max(nets,default=0.); worst=min(nets,default=0.)
    return {**sums,'trades':len(nets),'expectancy':sums['net']/len(nets) if nets else None,'expectancy_bps':float(np.mean([v['net']/r['entry_reference']*10000 for v,r in zip(vals,trades)])) if nets else None,
            'PF':wins/losses if losses else None,'PF_flag':None if losses else 'NO_LOSSES','win_rate':sum(x>0 for x in nets)/len(nets) if nets else None,'max_drawdown_realized':dd,'max_drawdown_observed_adverse_marks':observed_dd,'best_trade':best if nets else None,'worst_trade':worst if nets else None,'ex_best_positive_net':sums['net']-max(0.,best),
            'exposure_seconds':sum(r['exposure']['seconds'] for r in trades),'overnight_trade_seconds':sum(r['exposure']['overnight_trade_seconds'] for r in trades),'weekend_seconds':sum(r['exposure']['weekend_seconds'] for r in trades),'unobserved_holding_seconds':sum(r['unobserved_holding_seconds'] for r in trades)}


def decide(metrics):
    reasons=[]
    for p,n in [('2024',100),('2025',100),('2025_H1',40),('2025_H2',40)]:
        if metrics[p]['E1']['trades']<n:
            reasons.append(f'TRADE_COUNT_{p}_LT_{n}')
    for p in PERIODS:
        if metrics[p]['E1']['net']<=0:
            reasons.append('E1_NET_NONPOSITIVE_'+p)
    for p in ('2024','2025'):
        if metrics[p]['STRESS']['net']<=0:
            reasons.append('STRESS_NET_NONPOSITIVE_'+p)
    if metrics['2025']['STRESS']['ex_best_positive_net']<=0:
        reasons.append('STRESS_2025_EX_BEST_NONPOSITIVE')
    return ('FAIL' if reasons else 'PASS'),reasons


def summarize(candidate,ledger,counts):
    metrics={p:{profile:stats([r for r in ledger if p in r['periods']],profile) for profile in PROFILES} for p in PERIODS}
    status,reasons=decide(metrics)
    excluded={p:sum(1 for r in ledger if p not in r['periods'] and r['entry']<pd.Timestamp(PERIODS[p][1],tz='UTC').timestamp() and r['exit']>=pd.Timestamp(PERIODS[p][0],tz='UTC').timestamp()) for p in PERIODS}
    return {**candidate,**counts,'status':status,'fail_reasons':reasons,'excluded_subperiod_boundary_trades':excluded,'metrics':metrics,'all_history_descriptive':{p:stats(ledger,p) for p in PROFILES},'FUNDENDNEXT_PROFILE':{'status':'UNRESOLVED / DISABLED','results':None}}


def validate_ledger(ledger,counts):
    if counts['signals_total']!=counts['ignored_overlap_signals']+counts['excluded_boundary_trades']+counts['smoke_not_admitted']+len(ledger):
        raise RuntimeError('signal accounting mismatch')
    previous_exit=-1
    for r in ledger:
        if not START<=r['signal']<r['available']<=r['entry']<=r['exit']<BOUNDARY or r['entry']<previous_exit or r['exit']<r['exit_available']:
            raise RuntimeError('ledger causal/overlap/boundary invariant')
        previous_exit=r['exit']
        for p,x in r['profiles'].items():
            expected=cost(r['entry_reference'],r['exit_reference'],r['direction'],p)
            for k,val in expected.items():
                if not math.isclose(x[k],val,rel_tol=1e-12,abs_tol=1e-12):
                    raise RuntimeError('ledger cost mismatch')
            if not math.isclose(x['net'],r['direction']*(x['exit_model']-x['entry_model'])-x['commission'],rel_tol=1e-10,abs_tol=1e-9):
                raise RuntimeError('independent modeled price accounting mismatch')


def smoke_admission(df):
    dates=df.time.dt.floor('D')
    allowed=[]
    for a,b in [('2024-01-01','2024-07-01'),('2024-07-01','2025-01-01'),('2025-01-01','2025-07-01'),('2025-07-01','2026-01-01')]:
        unique=dates[(dates>=pd.Timestamp(a,tz='UTC'))&(dates<pd.Timestamp(b,tz='UTC'))&(dates.dt.dayofweek<5)].drop_duplicates()
        allowed.extend(unique.iloc[:5].tolist())
    return dates.isin(allowed).to_numpy()


def run(args):
    out=Path(args.output_dir).absolute(); progress=Path(args.progress_file).absolute()
    runroot=Path(r'D:\MT5_Backtests\Research\Autonomous')
    if out.parent!=runroot or not out.name.startswith('pre_oos_economic_feasibility_') or progress.parent!=runroot/'progress' or not progress.name.startswith('PRE-OOS-ECONOMIC-FEASIBILITY-'):
        raise RuntimeError('output/progress outside dedicated feasibility namespace')
    for parent in (out.parent,progress.parent):
        for p in (parent,*parent.parents):
            if p.exists() and (p.is_symlink() or getattr(p.lstat(),'st_file_attributes',0)&0x400):
                raise BlockedData('output ancestor is a reparse point')
    if out.exists():
        raise RuntimeError('immutable output directory already exists; no duplicate run')
    if progress.exists():
        raise RuntimeError('progress file already exists; no duplicate run')
    # Bootstrap files are fixed code/support, never arbitrary CLI input.
    # PRE_REGISTRATION hashes are checked before any market file is opened.
    reg=json.loads((SPEC/'PRE_REGISTRATION.json').read_text(encoding='utf-8'))
    expected_support={
        'research/autonomous/pre_oos_economic_feasibility_v1_00.py',
        'research/autonomous/pre_oos_r4_features_v1_00.py',
        *('research/protocols/pre_oos_economic_feasibility_screen_v2/'+name for name in ('PROTOCOL.md','POLICY.json','DATA_MANIFEST.json','FTMO_VERIFICATION.json','OWNER_DECISIONS.md')),
    }
    if set(reg['files'])!=expected_support:
        raise BlockedData('support manifest contains unexpected/missing path; rejected before open')
    support={str(BASE/rel):digest for rel,digest in reg['files'].items()}
    accesses=[]
    for p in support:
        verified_bytes(p,support,accesses)
    manifest=json.loads(verified_bytes(SPEC/'DATA_MANIFEST.json',support,accesses))
    if {r['path']:r['sha256'] for r in manifest['files']}!=MARKETS:
        raise BlockedData('manifest differs from four compiled pinned inputs')
    if set(PROFILES)!= {'E1','STRESS'}:
        raise RuntimeError('profile invariant')
    allowed={**MARKETS,SOURCE:SOURCE_HASH,FROZEN:FROZEN_HASH,**support}
    # Preload Windows file APIs before the fence disallows dynamic libraries.
    # ctypes caches are not sufficient: verified_bytes uses this fixed DLL only.
    out.mkdir(parents=True); progress.parent.mkdir(parents=True,exist_ok=True)
    fence=AccessFence(allowed,out,progress)
    sys.addaudithook(fence)
    try:
        with Heartbeat(progress,8 if args.smoke else 500) as hb:
            source=json.loads(verified_bytes(SOURCE,allowed,accesses))
            frozen=json.loads(verified_bytes(FROZEN,allowed,accesses))
            candidates=ingest(source,MARKETS,frozen)
            selected=candidates
            if args.smoke:
                selected=[]
                for p in MARKETS:
                    selected.extend([c for c in candidates if c['rule']['dataset']==p][:2])
            frames={}
            for r in manifest['files']:
                hb.update(phase='verified_loading',dataset=r['path'])
                df=parse_market(verified_bytes(r['path'],allowed,accesses),r['timeframe'])
                if len(df)!=r['rows']:
                    raise BlockedData('certified row count mismatch')
                frames[r['path']]=df
            paths=list(MARKETS)
            clean_subset(frames[paths[0]],frames[paths[1]])
            clean_subset(frames[paths[2]],frames[paths[3]])
            raw=frames[paths[0]]; ft={}
            for p,df in frames.items():
                hb.update(phase='features',dataset=p)
                ft[p]=features(df)[0]
            results=[]
            for n,c in enumerate(selected):
                hb.update(phase='simulation',candidate=c['id'],completed=n)
                r=c['rule']; df=frames[r['dataset']]
                signals=apply_rule(df,ft[r['dataset']],r)
                tf=60 if '_m1_' in r['dataset'] else 300
                ledger,counts=replay(df,raw,signals,r['horizon_bars'],r['direction'],tf,smoke_admission(df) if args.smoke else None,lambda **kw: hb.update(**kw))
                validate_ledger(ledger,counts)
                result=summarize(c,ledger,counts)
                # The smoke never performs candidate selection or exposes ranks.
                if args.smoke:
                    result['status']='SMOKE_NOT_FOR_SELECTION'; result['fail_reasons']=[]
                atomic_json(out/(c['id']+'.json'),{'summary':result,'trades':ledger})
                results.append(result)
                hb.update(completed=n+1,provisional_survivors=sum(x['status']=='PASS' for x in results))
            status='SMOKE_PASS' if args.smoke else ('PASS' if any(c['status']=='PASS' for c in results) else 'FAIL')
            result={'validator':VERSION,'cost_profile_version':'v2','profile_labels':{'E1':'FTMO COMMISSION + E1 SIMULATED EXECUTION','STRESS':'CONSERVATIVE STRESS'},'status':status,'source_candidates_ingested':len(candidates),'candidates_evaluated':len(results),'results':results,'provenance':{'registration':reg,'commit_sha':args.commit_sha,'input_accesses':accesses,'denied_accesses':fence.denied,'python':sys.version,'numpy':np.__version__,'pandas':pd.__version__},'interpretation':'specified-cost feasibility only; no verified fills/profitability/OOS; financing unmodeled and exposures reported'}
            atomic_json(out/'feasibility_result.json',result)
            hb.update(phase='complete',scientific_status=status)
            print(json.dumps({'status':status,'candidates':len(results),'source_candidates':500}))
            return 0 if status in ('PASS','SMOKE_PASS') else 1
    except Exception as exc:
        atomic_json(out/'failure.json',{'status':'BLOCKED_DATA' if isinstance(exc,BlockedData) else 'ERROR','exception_type':type(exc).__name__,'message':str(exc),'input_accesses':accesses,'denied_accesses':fence.denied})
        raise


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output-dir',required=True); ap.add_argument('--progress-file',required=True)
    ap.add_argument('--commit-sha',required=True); ap.add_argument('--smoke',action='store_true')
    return run(ap.parse_args())


if __name__=='__main__':
    raise SystemExit(main())
