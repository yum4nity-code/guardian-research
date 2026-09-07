#!/usr/bin/env python3
from __future__ import annotations
import unittest
import management_benchmark_v2 as v2

def row(*,gross=0.5,net=0.4,commission=0.1,mae=0.4,r2=False,r3=False,r5=False,min2='',min3='',mae2=0.2,mae3=0.2,mae5=0.2,amb=False,exit_reason='EOD'):
    return {
        'symbol':'TEST','gross_r':str(gross),'commission_r':str(commission),'net_r':str(net),'net_r_commission_x1_5':str(gross-1.5*commission),
        'path_ambiguous':'1' if amb else '0','mae_r':str(mae),'exit_reason':exit_reason,
        'reached_2r':'1' if r2 else '0','mae_before_2r':str(mae2),'min_r_after_first_2r_before_exit':str(min2),
        'reached_3r':'1' if r3 else '0','mae_before_3r':str(mae3),'min_r_after_first_3r_before_exit':str(min3),
        'reached_5r':'1' if r5 else '0','mae_before_5r':str(mae5),
    }

class ManagementBenchmarkV2Tests(unittest.TestCase):
    def rule(self,name): return next(x for x in v2.RULES if x['name']==name)

    def test_lock1_after_2r_triggers_floor(self):
        gross,reason=v2.apply_rule(row(gross=-0.3,net=-0.4,r2=True,min2=0.7),self.rule('LOCK1_AFTER_2R'))
        self.assertEqual(1.0,gross); self.assertEqual('LATE_FLOOR_THRESHOLD_PROXY',reason)

    def test_lock1_after_2r_keeps_original_without_retrace(self):
        gross,reason=v2.apply_rule(row(gross=2.6,net=2.5,r2=True,min2=1.4),self.rule('LOCK1_AFTER_2R'))
        self.assertEqual(2.6,gross); self.assertEqual('ORIGINAL_EXIT_NO_FLOOR_RETRACE',reason)

    def test_partial_25_at_3r(self):
        gross,reason=v2.apply_rule(row(gross=5.0,net=4.9,r3=True,min3=2.5),self.rule('P25_AT_3R_REST_ORIGINAL'))
        self.assertAlmostEqual(4.5,gross); self.assertEqual('LATE_PARTIAL_PLUS_ORIGINAL_REMAINDER',reason)

    def test_partial_floor_after_3r(self):
        gross,reason=v2.apply_rule(row(gross=0.4,net=0.3,r3=True,min3=1.2),self.rule('P25_AT_3R_LOCK2_REST'))
        self.assertAlmostEqual(2.25,gross); self.assertEqual('LATE_PARTIAL_PLUS_FLOOR_PROXY',reason)

    def test_tp5_respects_mae_before_milestone(self):
        gross,reason=v2.apply_rule(row(gross=6.0,net=5.9,r5=True,mae5=1.1),self.rule('SL1_TP5'))
        self.assertEqual(-1.0,gross); self.assertEqual('SL_BEFORE_LATE_TP_THRESHOLD_PROXY',reason)

    def test_ambiguous_rows_are_excluded(self):
        gross,reason=v2.apply_rule(row(amb=True,r3=True,min3=-0.2),self.rule('BE_AFTER_3R'))
        self.assertIsNone(gross); self.assertEqual('EXCLUDED_PATH_AMBIGUOUS',reason)

    def test_cross_family_prefers_more_improved_families(self):
        matrix=[]; pooled={str(r['name']):[] for r in v2.RULES}
        for dataset,delta_a,delta_b in [('D038',0.01,0.5),('D039',0.01,-0.1),('D040',0.01,-0.1),('D045',-0.001,-0.1)]:
            for name,delta in [('BE_AFTER_3R',delta_a),('LOCK1_AFTER_2R',delta_b)]:
                matrix.append({'dataset':dataset,'rule':name,'mean_net_delta_vs_baseline':delta})
                pooled[name].append(delta)
        ranked=v2.cross_family(matrix,pooled)
        self.assertEqual('BE_AFTER_3R',ranked[0]['rule'])
        self.assertEqual(3,ranked[0]['families_improved'])

if __name__=='__main__': unittest.main()
