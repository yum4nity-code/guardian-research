#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import strategy_factory_causal_next_open_v1_00 as r5
import r5_pre_oos_economic_robustness_v1_00 as econ
import r6_protected_2026_oos_v1_02 as transport
import r6_xau_low_turnover_breakout_v1_00 as r6stats

START = pd.Timestamp('2026-01-01T00:00:00Z')
SPLIT = pd.Timestamp('2026-05-01T00:00:00Z')
END = pd.Timestamp('2026-09-01T00:00:00Z')
JAN7 = pd.Timestamp('2026-01-07T00:00:00Z')
AUG25 = pd.Timestamp('2026-08-25T00:00:00Z')


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def atomic_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def heartbeat(path: Path | None, done: int, total: int, stage: str, extra=None) -> None:
    if path is None:
        return
    obj = {'completed': int(done), 'total': int(total), 'stage': stage, 'updated_at_utc': datetime.now(timezone.utc).isoformat()}
    if extra:
        obj.update(extra)
    atomic_json(path, obj)


def publish(publisher: str | None, status: str, summary: str, artifacts) -> None:
    if not publisher:
        return
    cmd = ['python', publisher, '--phase', 'r5e023-protected-2026-oos', '--status', status, '--summary', summary]
    for artifact in artifacts:
        cmd += ['--artifact', str(artifact)]
    subprocess.run(cmd, check=True)


def period(trades, start: pd.Timestamp, end: pd.Timestamp):
    return [t for t in trades if start <= pd.Timestamp(t['entry_time']) and pd.Timestamp(t['exit_time']) < end]


def replay_2026(source: pd.DataFrame, raw_m1: pd.DataFrame, signals: np.ndarray, horizon: int, direction: int, tf_seconds: int):
    source_ns = source.time.array.as_unit('ns').asi8
    raw_ns = raw_m1.time.array.as_unit('ns').asi8
    raw_open = raw_m1.open.to_numpy(dtype=float)
    signals = np.asarray(signals, dtype=bool)
    ledger = []
    state = None
    counts = {'signals_total': int(signals.sum()), 'ignored_overlap_signals': 0, 'excluded_oos_boundary_signals': 0, 'missing_reference_trades': 0, 'executable_trades': 0}
    n = len(source)

    def close_state(s):
        exit_idx = int(np.searchsorted(raw_ns, s['exit_available_ns'], side='left'))
        if s['entry_idx'] >= len(raw_ns) or exit_idx >= len(raw_ns):
            counts['missing_reference_trades'] += 1
            return
        entry_ns = int(raw_ns[s['entry_idx']]); exit_ns = int(raw_ns[exit_idx])
        if not (int(START.value) <= entry_ns < int(END.value) and int(START.value) <= exit_ns < int(END.value)):
            counts['excluded_oos_boundary_signals'] += 1
            return
        oe = float(raw_open[s['entry_idx']]); ox = float(raw_open[exit_idx])
        ledger.append({
            'signal_index': s['signal_index'],
            'signal_time': pd.Timestamp(s['signal_ns'], tz='UTC').isoformat(),
            'entry_time': pd.Timestamp(entry_ns, tz='UTC').isoformat(),
            'exit_time': pd.Timestamp(exit_ns, tz='UTC').isoformat(),
            'entry_open': oe, 'exit_open': ox, 'direction': int(direction),
            'profiles': {p: econ.cost(oe, ox, direction, p) for p in econ.PROFILES},
        })

    for i in range(n):
        available_ns = int(source_ns[i] + tf_seconds * 1_000_000_000)
        if state is not None and available_ns >= state['exit_available_ns']:
            close_state(state)
            state = None
        if not signals[i]:
            continue
        if state is not None:
            counts['ignored_overlap_signals'] += 1
            continue
        exit_source_index = i + horizon + 1
        if exit_source_index >= n:
            counts['excluded_oos_boundary_signals'] += 1
            continue
        if available_ns < int(START.value) or available_ns >= int(END.value) or int(source_ns[exit_source_index]) >= int(END.value):
            counts['excluded_oos_boundary_signals'] += 1
            continue
        entry_idx = int(np.searchsorted(raw_ns, available_ns, side='left'))
        if entry_idx >= len(raw_ns):
            counts['missing_reference_trades'] += 1
            continue
        state = {'signal_index': int(i), 'signal_ns': int(source_ns[i]), 'entry_idx': entry_idx, 'exit_available_ns': int(source_ns[exit_source_index])}

    if state is not None:
        close_state(state)
    counts['executable_trades'] = len(ledger)
    return ledger, counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--preregistration', required=True)
    ap.add_argument('--root', required=True)
    ap.add_argument('--output-dir', required=True)
    ap.add_argument('--progress-file')
    ap.add_argument('--publisher')
    args = ap.parse_args()

    prereg_path = Path(args.preregistration)
    prereg = load_json(prereg_path)
    if prereg.get('authorized_by_human') is not True or prereg.get('retuning_allowed') is not False or prereg.get('live_deployment_allowed') is not False:
        raise RuntimeError('authorization/freeze contract invalid')
    if prereg.get('candidate_id') != 'R5E-023':
        raise RuntimeError('unexpected candidate')

    rule = dict(prereg['frozen_candidate'])
    expected_rule = {
        'dataset_semantics': 'xauusd_m5_news_clean', 'feature': 'sma5', 'operator': 'lt', 'quantile': 0.05,
        'cutpoint': -1.1144146539095026, 'horizon_bars': 48, 'direction': 1,
        'hour_start': 1, 'hour_width': 2, 'execution': 'signal_after_close_entry_next_open_exit_open_after_h_bars'
    }
    if rule != expected_rule:
        raise RuntimeError('R5E-023 frozen definition mismatch')
    if prereg['upstream_evidence'].get('published_artifact_sha256') != 'b22f72442088fea55f049c358c5adfc8316fe77bed60af20774629c05d7f125a':
        raise RuntimeError('upstream evidence hash mismatch')
    if prereg['upstream_evidence'].get('historical_fail_reasons') != ['TRADE_COUNT_2024_LT_100', 'TRADE_COUNT_2025_LT_100']:
        raise RuntimeError('candidate was not frozen as count-only historical failure')

    root = Path(args.root)
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    progress = Path(args.progress_file) if args.progress_file else None
    inputs = prereg['inputs']
    expand = lambda v: Path(v.replace('{ROOT}', str(root))) if '{ROOT}' in v else Path(v)
    m5_path = expand(inputs['m5_csv']); m1_path = expand(inputs['m1_csv'])
    m5_manifest_path = expand(inputs['m5_manifest']); m1_manifest_path = expand(inputs['m1_manifest']); mask_path = expand(inputs['news_mask'])

    heartbeat(progress, 0, 1, 'validate_frozen_inputs')
    m5_manifest = transport.base.validate_manifest(m5_manifest_path, 'M5', prereg)
    m1_manifest = transport.base.validate_manifest(m1_manifest_path, 'M1', prereg)
    raw_m5 = transport.base.load_snapshot(m5_path, 'M5')
    raw_m1 = transport.base.load_snapshot(m1_path, 'M1')
    intervals, mask_sha = transport.base.read_news_mask(mask_path, inputs['news_mask_expected_sha256'])
    source = transport.apply_news_mask(raw_m5, intervals)

    overlap_start = max(source.time.min(), raw_m1.time.min()); overlap_end = min(source.time.max(), raw_m1.time.max())
    overlap_days = float((overlap_end - overlap_start).total_seconds() / 86400.0)
    if overlap_days < float(prereg['oos_window']['minimum_overlap_days']) or overlap_start > JAN7 or overlap_end < AUG25:
        raise RuntimeError(f'insufficient frozen Jan-Aug overlap: {overlap_start} .. {overlap_end} ({overlap_days:.2f}d)')
    source = source[(source.time >= overlap_start) & (source.time <= overlap_end)].reset_index(drop=True)
    raw_m1 = raw_m1[(raw_m1.time >= overlap_start) & (raw_m1.time <= overlap_end)].reset_index(drop=True)

    feats, _ = r5.features(source)
    apply_rule = dict(rule)
    apply_rule['dataset'] = str(m5_path)
    signals = r5.apply_rule(source, feats, apply_rule)
    ledger, accounting = replay_2026(source, raw_m1, signals, int(rule['horizon_bars']), int(rule['direction']), 300)

    full = {p: econ.stats(ledger, p) for p in econ.PROFILES}
    h1_trades = period(ledger, START, SPLIT); h2_trades = period(ledger, SPLIT, END)
    h1 = {p: econ.stats(h1_trades, p) for p in econ.PROFILES}; h2 = {p: econ.stats(h2_trades, p) for p in econ.PROFILES}
    boot = r6stats.day_block_bootstrap(ledger, 'E1', 'R5E-023', b=int(prereg['candidate_pass_criteria']['bootstrap_resamples']))
    gates = prereg['candidate_pass_criteria']
    pf = full['E1']['PF'] if full['E1']['PF'] is not None else (float('inf') if full['E1']['net'] > 0 else 0.0)
    checks = {
        'minimum_full_oos_trades': full['E1']['trades'] >= int(gates['minimum_full_oos_trades']),
        'minimum_half1_trades': h1['E1']['trades'] >= int(gates['minimum_each_temporal_half_trades']),
        'minimum_half2_trades': h2['E1']['trades'] >= int(gates['minimum_each_temporal_half_trades']),
        'full_e1_net': full['E1']['net'] > float(gates['full_e1_net_gt']),
        'full_stress_net': full['STRESS']['net'] > float(gates['full_stress_net_gt']),
        'half1_e1_net': h1['E1']['net'] > float(gates['half1_e1_net_gt']),
        'half2_e1_net': h2['E1']['net'] > float(gates['half2_e1_net_gt']),
        'half1_stress_net': h1['STRESS']['net'] > float(gates['half1_stress_net_gt']),
        'half2_stress_net': h2['STRESS']['net'] > float(gates['half2_stress_net_gt']),
        'full_e1_pf': float(pf) > float(gates['full_e1_profit_factor_gt']),
        'full_e1_ex_best': full['E1']['ex_best_positive_net'] > float(gates['full_e1_net_after_best_positive_trade_removed_gt']),
        'bootstrap_p05': boot.get('p05') is not None and float(boot['p05']) > float(gates['day_block_bootstrap_e1_p05_gt'])
    }
    status = 'PASS' if all(checks.values()) else 'FAIL'
    report = {
        'schema': 1, 'phase': 'r5e023-protected-2026-oos', 'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'status': status, 'candidate_id': 'R5E-023', 'protected_2026_opened': True, 'retuning_performed': False,
        'live_deployment_authorized': False, 'frozen_candidate': rule,
        'coverage': {'start_utc': overlap_start.isoformat(), 'end_utc': overlap_end.isoformat(), 'days': overlap_days},
        'signal_accounting': accounting, 'oos_full': full, 'oos_half1_jan_apr': h1, 'oos_half2_may_aug': h2,
        'bootstrap_2026_e1': boot, 'gate_checks': checks,
        'input_manifest': {
            'm5': {'path': str(m5_path), 'sha256': transport.base.sha256_file(m5_path), 'manifest': m5_manifest},
            'm1': {'path': str(m1_path), 'sha256': transport.base.sha256_file(m1_path), 'manifest': m1_manifest},
            'news_mask': {'path': str(mask_path), 'sha256': mask_sha, 'intervals': len(intervals)}
        },
        'interpretation': 'PASS is protected-OOS evidence for frozen R5E-023 only, not live authorization. FAIL closes this exact candidate for promotion; no 2026 retuning is allowed.'
    }
    report_path = out / 'r5e023_protected_2026_oos_result.json'
    atomic_json(report_path, report)
    heartbeat(progress, 1, 1, 'complete', {'status': status, 'trades': full['E1']['trades']})
    publish(args.publisher, status, f"R5E-023 protected Jan-Aug 2026 OOS {status}: {full['E1']['trades']} trades; no retuning; no live deployment.", [report_path, prereg_path])
    print(json.dumps({'status': status, 'candidate_id': 'R5E-023', 'trades': full['E1']['trades'], 'protected_2026_opened': True}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
