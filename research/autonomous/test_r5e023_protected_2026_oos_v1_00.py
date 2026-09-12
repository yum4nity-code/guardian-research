#!/usr/bin/env python3
from __future__ import annotations

import inspect
import json
from pathlib import Path

import r5e023_protected_2026_oos_v1_00 as oos


def main() -> int:
    here = Path(__file__).parent
    prereg = json.loads((here / 'r5e023_protected_2026_oos_preregistration_v1.json').read_text(encoding='utf-8'))
    assert prereg['authorized_by_human'] is True
    assert prereg['retuning_allowed'] is False
    assert prereg['live_deployment_allowed'] is False
    assert prereg['candidate_id'] == 'R5E-023'
    assert prereg['upstream_evidence']['published_artifact_sha256'] == 'b22f72442088fea55f049c358c5adfc8316fe77bed60af20774629c05d7f125a'
    assert prereg['upstream_evidence']['historical_fail_reasons'] == ['TRADE_COUNT_2024_LT_100', 'TRADE_COUNT_2025_LT_100']
    assert prereg['frozen_candidate'] == {
        'dataset_semantics': 'xauusd_m5_news_clean',
        'feature': 'sma5',
        'operator': 'lt',
        'quantile': 0.05,
        'cutpoint': -1.1144146539095026,
        'horizon_bars': 48,
        'direction': 1,
        'hour_start': 1,
        'hour_width': 2,
        'execution': 'signal_after_close_entry_next_open_exit_open_after_h_bars'
    }
    assert prereg['cost_profiles']['E1'] == {'commission_rate': 0.000007, 'spread': 0.0002, 'slippage_per_side': 0.0001}
    assert prereg['cost_profiles']['STRESS'] == {'commission_rate': 0.000014, 'spread': 0.0005, 'slippage_per_side': 0.0002}
    assert prereg['oos_window']['start'] == '2026-01-01T00:00:00Z'
    assert prereg['oos_window']['split'] == '2026-05-01T00:00:00Z'
    assert prereg['oos_window']['end_exclusive'] == '2026-09-01T00:00:00Z'
    gates = prereg['candidate_pass_criteria']
    assert gates == {
        'minimum_full_oos_trades': 30,
        'minimum_each_temporal_half_trades': 12,
        'full_e1_net_gt': 0,
        'full_stress_net_gt': 0,
        'half1_e1_net_gt': 0,
        'half2_e1_net_gt': 0,
        'half1_stress_net_gt': 0,
        'half2_stress_net_gt': 0,
        'full_e1_profit_factor_gt': 1.0,
        'full_e1_net_after_best_positive_trade_removed_gt': 0,
        'day_block_bootstrap_e1_p05_gt': 0,
        'bootstrap_resamples': 10000
    }
    src = inspect.getsource(oos)
    assert "r5.apply_rule(source, feats, apply_rule)" in src
    assert "replay_2026(source, raw_m1, signals" in src
    assert "transport.apply_news_mask(raw_m5, intervals)" in src
    assert "exit_source_index = i + horizon + 1" in src
    assert "entry_idx = int(np.searchsorted(raw_ns, available_ns, side='left'))" in src
    assert "retuning_performed': False" in src
    assert "live_deployment_authorized': False" in src
    lowered = src.lower()
    for forbidden in ('grid_search', 'best_params', 'optimize(', 'retune', 'parameter_search'):
        assert forbidden not in lowered or forbidden == 'retune' and 'no 2026 retuning is allowed' in lowered
    print(json.dumps({'status': 'PASS', 'candidate_id': 'R5E-023', 'market_data_accessed': False, 'scientific_oos_evaluated': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
