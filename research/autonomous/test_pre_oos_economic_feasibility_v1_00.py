import ast
import copy
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
import pre_oos_economic_feasibility_v1_00 as v

# Keep synthetic temporary files inside the explicitly writable workspace.
TEST_TEMP = v.BASE/'research'/'feasibility_test_tmp'
TEST_TEMP.mkdir(exist_ok=True)
tempfile.tempdir = str(TEST_TEMP)


def bars(times,opens=None):
    t=pd.to_datetime(times,utc=True)
    p=np.array(opens if opens is not None else [100.]*len(t),float)
    return pd.DataFrame({'time':t,'open':p,'high':p+1,'low':p-1,'close':p,'volume':np.ones(len(t))})


def regular(n=8,freq='min',start='2025-01-02 10:00'):
    return bars(pd.date_range(start,periods=n,freq=freq,tz='UTC'))


def rule(i=0):
    return {'dataset':next(iter(v.MARKETS)),'feature':'ret1','operator':'gt','quantile':.8,'cutpoint':i/100.,'horizon_bars':1,'direction':1,'hour_start':None,'hour_width':None}


class FeasibilityTests(unittest.TestCase):
    def test_unmanifested_before_open(self):
        with patch.object(v,'no_links') as metadata, patch('builtins.open') as opened:
            with self.assertRaises(v.BlockedData):
                v.verified_bytes('NEVER_OPEN_2026.csv',v.MARKETS,[])
            metadata.assert_not_called(); opened.assert_not_called()

    def test_reparse_input_rejected_before_native_reader(self):
        from types import SimpleNamespace
        with patch.object(Path,'lstat',return_value=SimpleNamespace(st_mode=0o100644,st_file_attributes=0x400)):
            with self.assertRaises(v.BlockedData):
                v.verified_bytes(next(iter(v.MARKETS)),v.MARKETS,[])

    def test_registration_cannot_inject_a_market_path(self):
        import argparse
        bad={'files':{'synthetic_protected_2026.csv':'0'*64}}
        args=argparse.Namespace(output_dir=r'D:\MT5_Backtests\Research\Autonomous\pre_oos_economic_feasibility_unit_not_created',progress_file=r'D:\MT5_Backtests\Research\Autonomous\progress\PRE-OOS-ECONOMIC-FEASIBILITY-UNIT-NOT-CREATED.json',smoke=True,commit_sha='synthetic')
        with patch.object(Path,'read_text',return_value=json.dumps(bad)),patch.object(v,'verified_bytes') as reader:
            with self.assertRaisesRegex(v.BlockedData,'support manifest'): v.run(args)
            reader.assert_not_called()

    def test_protected_fence_no_real_file(self):
        f=v.AccessFence(v.MARKETS,Path.cwd()/'out',Path.cwd()/'progress.json')
        for name in ['unmanifested.csv','synthetic_2026.csv']:
            with self.assertRaises(v.BlockedData): f('open',(name,'r',os.O_RDONLY))

    def test_scans_network_subprocess_dynamic_dll_denied(self):
        f=v.AccessFence({},Path.cwd()/'out',Path.cwd()/'progress.json')
        for event in ('os.scandir','os.listdir','socket.connect','subprocess.Popen','ctypes.dlopen'):
            with self.assertRaises(v.BlockedData): f(event,('synthetic',))

    def test_hash_mismatch_before_use(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'synthetic.txt'; p.write_bytes(b'synthetic')
            with self.assertRaises(v.BlockedData): v.verified_bytes(p,{str(p):'0'*64},[])

    def test_verified_windows_reader(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'synthetic.txt'; p.write_bytes(b'synthetic')
            self.assertEqual(v.verified_bytes(p,{str(p):v.sha(b'synthetic')},[]),b'synthetic')

    def test_m1_timing(self):
        r=regular(); rows,_=v.replay(r,r,[True]+[False]*7,1,1,60)
        self.assertEqual(rows[0]['entry'],v.epochs(r)[1]); self.assertEqual(rows[0]['exit'],v.epochs(r)[2])

    def test_m5_timing(self):
        r=regular(25); s=regular(4,'5min')
        rows,_=v.replay(s,r,[True,False,False,False],1,1,300)
        self.assertEqual(rows[0]['entry'],v.epochs(r)[5]); self.assertEqual(rows[0]['exit'],v.epochs(r)[10])

    def test_next_available_after_gap(self):
        r=regular().drop(index=1).reset_index(drop=True); s=regular()
        rows,_=v.replay(s,r,[True]+[False]*7,3,1,60)
        self.assertEqual(rows[0]['entry'],v.epochs(s)[2])

    def test_raw_horizon(self):
        r=regular(); rows,_=v.replay(r,r,[True]+[False]*7,3,1,60)
        self.assertEqual(rows[0]['exit']-rows[0]['entry'],180)

    def test_clean_horizon_counter(self):
        r=regular(12); s=r.iloc[[0,1,5,7,8,9,10]].reset_index(drop=True)
        rows,_=v.replay(s,r,[True]+[False]*6,3,1,60)
        self.assertEqual(rows[0]['entry'],v.epochs(r)[1]); self.assertEqual(rows[0]['exit'],v.epochs(r)[8])

    def test_future_clean_support_does_not_select_entry(self):
        r=regular(20); a=r.iloc[[0,1,2,3,4,5]].reset_index(drop=True); b=r.iloc[[0,1,2,8,9,10]].reset_index(drop=True)
        x,_=v.replay(a,r,[True]+[False]*5,3,1,60); y,_=v.replay(b,r,[True]+[False]*5,3,1,60)
        self.assertEqual(x[0]['entry'],y[0]['entry']); self.assertNotEqual(x[0]['exit'],y[0]['exit'])

    def test_news_mask_only_temporal_intersection(self):
        self.assertTrue(v.news_intersection(1000,60,1000)); self.assertTrue(v.news_intersection(700,60,1000))
        self.assertFalse(v.news_intersection(640,60,1000)); self.assertFalse(v.news_intersection(1301,60,1000))

    def test_clean_preserves_values(self):
        r=regular(); c=r.iloc[[0,3,5]].copy(); v.clean_subset(r,c)
        c.loc[3,'close']+=1
        with self.assertRaises(v.BlockedData): v.clean_subset(r,c)

    def test_end_2025_boundary_without_lookups(self):
        r=regular(5,start='2025-12-31 23:55')
        with patch.object(v,'verified_bytes') as reader:
            rows,c=v.replay(r,r,[False,False,True,True,True],3,1,60)
            self.assertEqual(rows,[]); self.assertEqual(c['excluded_boundary_trades'],2)
            self.assertEqual(c['ignored_overlap_signals'],1); reader.assert_not_called()

    def test_no_midnight_filter(self):
        r=regular(10,start='2025-01-02 23:57')
        rows,_=v.replay(r,r,[True]+[False]*9,6,1,60)
        self.assertGreater(rows[0]['exposure']['overnight_trade_seconds'],0)

    def test_weekend_exposure(self):
        a=int(pd.Timestamp('2025-01-03 23:00',tz='UTC').timestamp()); b=a+3*86400
        self.assertEqual(v.exposure_parts(a,b)['weekend_seconds'],172800)

    def test_overlap(self):
        r=regular(10); rows,c=v.replay(r,r,[True]*10,3,1,60)
        self.assertEqual(c['ignored_overlap_signals'],7); self.assertEqual(len(rows),2)
        self.assertEqual(rows[1]['entry'],rows[0]['exit'])

    def test_contradictory_direction_rejected(self):
        rows=[rule(i) for i in range(500)]; rows[3]['direction']=0
        with self.assertRaises(v.BlockedData): v.ingest({'survivor_count':500,'survivors':rows},v.MARKETS)

    def test_long_pnl(self):
        c=v.cost(100,110,1,'E1'); self.assertEqual(c['gross'],10)
        self.assertAlmostEqual(c['net'],c['exit_model']-c['entry_model']-c['commission'])

    def test_short_pnl(self):
        c=v.cost(110,100,-1,'E1'); self.assertEqual(c['gross'],10)
        self.assertAlmostEqual(c['net'],c['entry_model']-c['exit_model']-c['commission'])

    def test_full_spread_not_doubled(self):
        self.assertAlmostEqual(v.cost(100,100,1,'E1')['spread'],.02)
        self.assertAlmostEqual(v.cost(100,100,1,'STRESS')['spread'],.05)

    def test_commission_each_side(self):
        for profile,c in [('E1',.000007),('STRESS',.000014)]:
            r=v.cost(100,120,-1,profile)
            self.assertAlmostEqual(r['commission'],c*(r['entry_model']+r['exit_model']))

    def test_slippage_each_side(self):
        self.assertAlmostEqual(v.cost(100,120,1,'E1')['slippage'],.0001*220)

    def test_h1_h2_crossing_retained_annual(self):
        r=regular(8,start='2025-06-30 23:57'); rows,_=v.replay(r,r,[True]+[False]*7,3,1,60)
        self.assertEqual(rows[0]['periods'],['2025'])

    def test_year_crossing_not_forced_close(self):
        r=regular(8,start='2024-12-31 23:57'); rows,_=v.replay(r,r,[True]+[False]*7,3,1,60)
        self.assertEqual(rows[0]['periods'],[]); self.assertEqual(rows[0]['exit']-rows[0]['entry'],180)

    def test_best_trade_removal_drawdown_pf(self):
        r=regular(10); rows,_=v.replay(r,r,[True]*10,1,1,60)
        rows=rows[:3]
        for rec,net in zip(rows,[5.,-2.,1.]):
            rec['profiles']['E1']['net']=net; rec['profiles']['E1']['worst_observed_mark']=min(-1.,net)
        s=v.stats(rows,'E1'); self.assertEqual(s['ex_best_positive_net'],-1.)
        self.assertEqual(s['max_drawdown_realized'],2.); self.assertEqual(s['PF'],3.)

    def test_pf_no_losses(self):
        self.assertIsNone(v.stats([],'E1')['PF'])

    def test_deterministic_rerun(self):
        r=regular(30)
        self.assertEqual(v.canonical(v.replay(r,r,[True]*30,3,-1,60)),v.canonical(v.replay(r,r,[True]*30,3,-1,60)))

    def test_atomic_permission_retry(self):
        with tempfile.TemporaryDirectory() as td, patch.object(v.os,'replace',side_effect=[PermissionError(),PermissionError(),None]) as replace, patch.object(v.time,'sleep') as sleep:
            v.atomic_json(Path(td)/'x.json',{'x':1}); self.assertEqual(replace.call_count,3)
            self.assertEqual([c.args[0] for c in sleep.call_args_list],[.05,.10])

    def test_atomic_exhaustion_explicit(self):
        with tempfile.TemporaryDirectory() as td, patch.object(v.os,'replace',side_effect=PermissionError()), patch.object(v.time,'sleep'):
            with self.assertRaises(RuntimeError) as exc: v.atomic_json(Path(td)/'x.json',{})
            self.assertIsInstance(exc.exception.__cause__,PermissionError)

    def test_atomic_other_exception_not_masked(self):
        with tempfile.TemporaryDirectory() as td, patch.object(v.os,'replace',side_effect=ValueError('distinct')) as replace:
            with self.assertRaisesRegex(ValueError,'distinct'): v.atomic_json(Path(td)/'x.json',{})
            self.assertEqual(replace.call_count,1)

    def test_malformed_dataset(self):
        with self.assertRaises(v.BlockedData): v.parse_market(b'foo,bar\n1,2\n','M1')

    def test_nonfinite_dataset(self):
        data=b'symbol,timeframe,server_time,server_epoch,open,high,low,close,tick_volume\nXAUUSD,M1,2025.01.01 00:00:00,1735689600,NaN,1,1,1,1\n'
        with self.assertRaises(v.BlockedData): v.parse_market(data,'M1')

    def test_500_and_32_annotations_only(self):
        rows=[rule(i) for i in range(500)]
        out=v.ingest({'survivor_count':500,'survivors':rows},v.MARKETS,{'candidates':rows[:32]})
        self.assertEqual(len(out),500); self.assertEqual(sum(r['annotation_32'] for r in out),32)

    def test_duplicate_candidate_rejected(self):
        with self.assertRaises(v.BlockedData): v.ingest({'survivor_count':500,'survivors':[rule()]*500},v.MARKETS)

    def test_features_exact_original_ast(self):
        original=ast.parse((v.BASE/'research/autonomous/strategy_factory_conditional_edge_v1_00.py').read_text())
        pure=ast.parse((v.BASE/'research/autonomous/pre_oos_r4_features_v1_00.py').read_text())
        a={x.name:ast.dump(x) for x in original.body if isinstance(x,ast.FunctionDef)}
        b={x.name:ast.dump(x) for x in pure.body if isinstance(x,ast.FunctionDef)}
        for key in b: self.assertEqual(a[key],b[key])

    def test_anti_lookahead_features_and_signals(self):
        r=regular(200); r['close']+=np.sin(np.arange(200)/3.)*.5
        altered=r.copy(); altered.loc[150:,['open','high','low','close']]*=2
        a,_=v.features(r); b,_=v.features(altered)
        pd.testing.assert_frame_equal(a.iloc[:150],b.iloc[:150])
        np.testing.assert_array_equal(v.apply_rule(r,a,rule())[:150],v.apply_rule(altered,b,rule())[:150])

    def test_exact_frozen_gate_rules(self):
        m={p:{k:{'trades':100,'net':1.,'ex_best_positive_net':.5} for k in v.PROFILES} for p in v.PERIODS}
        m['2025_H1']['STRESS']['net']=-1
        self.assertEqual(v.decide(m)[0],'PASS')
        m['2025_H1']['E1']['trades']=39
        self.assertIn('TRADE_COUNT_2025_H1_LT_40',v.decide(m)[1])

    def test_fundednext_no_profile(self):
        self.assertEqual(set(v.PROFILES),{'E1','STRESS'})

    def test_heartbeat_output(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'progress.json'
            with v.Heartbeat(p,500) as hb: hb.update(completed=1,candidate='R4P-0001',phase='synthetic')
            obj=json.loads(p.read_text()); self.assertEqual(obj['completed'],1); self.assertIn('updated_at_utc',obj)

    def test_installed_fence_real_python_and_pandas_readers(self):
        code="""
import sys
import pre_oos_economic_feasibility_v1_00 as v
f=v.AccessFence({},v.BASE/'synthetic_output',v.BASE/'synthetic_progress.json')
sys.addaudithook(f)
for reader in (open,v.pd.read_csv,v.np.load):
    try: reader('synthetic_protected_2026.csv')
    except v.BlockedData: pass
    else: raise AssertionError('unmanifested read was not denied')
data=b'symbol,timeframe,server_time,server_epoch,open,high,low,close,tick_volume\\nXAUUSD,M1,2025.01.01 00:00:00,1735689600,1,1,1,1,1\\n'
df=v.parse_market(data,'M1')
v.features(df)
assert len(f.denied)==3
print('FENCE_PASS')
"""
        cp=subprocess.run([sys.executable,'-B','-c',code],cwd=Path(v.__file__).parent,capture_output=True,text=True)
        self.assertEqual(cp.returncode,0,cp.stderr); self.assertIn('FENCE_PASS',cp.stdout)


if __name__=='__main__': unittest.main(verbosity=2)
