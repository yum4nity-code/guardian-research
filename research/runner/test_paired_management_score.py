#!/usr/bin/env python3
from __future__ import annotations
import unittest
import paired_management_score as p

GATES={
    'aggregate_n_min':40,
    'paired_mean_delta_strictly_positive':True,
    'month_block_bootstrap_lower_95_strictly_positive':True,
    'positive_delta_symbols_min':2,
    'max_positive_symbol_contribution_share':0.60,
    'candidate_mean_net_r_min':0.20,
}

def row(month:str, delta:float=0.10, candidate:float=0.50):
    reference=candidate-delta
    return {
        'epoch':'POST2024','eligible':'1','signal_time':month+'-15 12:00:00',
        'reference_net_r':str(reference),'candidate_net_r':str(candidate),
        'paired_delta_r':str(delta),'candidate_stress_net_r':str(candidate-0.03),
        'exit_reason':'TIMEOUT_48H',
    }

class PairedManagementScoreTests(unittest.TestCase):
    def test_frozen_gate_pass(self):
        data={s:[row(f'2024-{(i%6)+1:02d}') for i in range(15)] for s in ('BTCUSD','ETHUSD','DOGUSD')}
        result=p.evaluate(data,GATES)
        self.assertEqual('MANAGEMENT_VALIDATED',result['verdict'])
        self.assertTrue(result['all_gates_pass'])
        self.assertGreater(result['metrics']['month_block_bootstrap']['lower_95'],0)

    def test_count_failure_is_inconclusive(self):
        data={s:[row('2024-01') for _ in range(5)] for s in ('BTCUSD','ETHUSD','DOGUSD')}
        result=p.evaluate(data,GATES)
        self.assertEqual('INCONCLUSIVE_COUNT',result['verdict'])
        self.assertFalse(result['gates']['aggregate_n_min'])

    def test_negative_delta_rejects(self):
        data={s:[row(f'2024-{(i%6)+1:02d}',delta=-0.05,candidate=0.40) for i in range(15)] for s in ('BTCUSD','ETHUSD','DOGUSD')}
        result=p.evaluate(data,GATES)
        self.assertEqual('REJECT_MANAGEMENT',result['verdict'])
        self.assertFalse(result['gates']['paired_mean_delta_strictly_positive'])

if __name__=='__main__': unittest.main()
