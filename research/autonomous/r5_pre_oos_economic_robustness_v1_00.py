#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import strategy_factory_causal_next_open_v1_00 as r5

PROTECTED = pd.Timestamp('2026-01-01', tz='UTC')
EXPECTED_R5_SHA256 = '81dd16fabf001025c4dc144035d538fa46fab2fc768ba237610e027af1c7d34e'
EXPECTED_AUDIT_SHA256 = 'ee3847d5a2c5c81b7cfb51290fa96d170c8e7fd4ac976d0bfca3cc03908fd628'
EXPECTED = {
    'xauusd_m1_2024_2025_raw.csv': ('f98a395961b27ca9dcb34cffa4ef8dd93720adb70292abf7bc96108667232445', 710300, 60),
    'xauusd_m1_2024_2025_news_clean.csv': ('b116c61d0be7d73c455f4a4f897efdf0bf77a2b88594ed4b93ebee0d707570ee', 703387, 60),
    'xauusd_m5_2024_2025_raw.csv': ('ba54c9b29755eac4284cb872805148736be529e954533c028e7f826bb444ce66', 142549, 300),
    'xauusd_m5_2024_2025_news_clean.csv': ('972ecaf6c3cadf7136363f396d7a29e7a6246646b575fad5c3e677036004b503', 140664, 300),
}
PROFILES = {
    'E1': (0.000007, 0.0002, 0.0001),
    'STRESS': (0.000014, 0.0005, 0.0002),
}
PERIODS = {
    '2024': (pd.Timestamp('2024-01-01', tz='UTC'), pd.Timestamp('2025-01-01', tz='UTC')),
    '2025': (pd.Timestamp('2025-01-01', tz='UTC'), pd.Timestamp('2026-01-01', tz='UTC')),
    '2025_H1': (pd.Timestamp('2025-01-01', tz='UTC'), pd.Timestamp('2025-07-01', tz='UTC')),
    '2025_H2': (pd.Timestamp('2025-07-01', tz='UTC'), pd.Timestamp('2026-01-01', tz='UTC')),
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


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


def publish(publisher: str | None, phase: str, status: str, summary: str, artifacts: list[Path]) -> None:
    if not publisher:
        return
    cmd = ['python', publisher, '--phase', phase, '--status', status, '--summary', summary]
    for artifact in artifacts:
        cmd += ['--artifact', str(artifact)]
    subprocess.run(cmd, check=True)


def cost(entry_open: float, exit_open: float, direction: int, profile: str) -> dict:
    commission_rate, spread, slippage = PROFILES[profile]
    friction = spread / 2.0 + slippage
    entry_model = entry_open * (1.0 + direction * friction)
    exit_model = exit_open * (1.0 - direction * friction)
    gross = direction * (exit_open - entry_open)
    spread_cost = spread / 2.0 * (entry_open + exit_open)
    slippage_cost = slippage * (entry_open + exit_open)
    commission = commission_rate * (entry_model + exit_model)
    net = gross - spread_cost - slippage_cost - commission
    return {
        'gross': float(gross), 'spread': float(spread_cost), 'slippage': float(slippage_cost),
        'commission': float(commission), 'net': float(net),
        'entry_model': float(entry_model), 'exit_model': float(exit_model),
    }


def replay(source: pd.DataFrame, raw_m1: pd.DataFrame, signals: np.ndarray, horizon: int, direction: int, tf_seconds: int) -> tuple[list[dict], dict]:
    """Chronological one-position replay using first raw-M1 references.

    Evaluation-boundary trades whose frozen source horizon crosses a calendar year
    are excluded before entry. This mirrors the R5 cross-year purge and prevents
    2024/2025 contamination; it is not a trading filter to be optimized.
    """
    source_ns = source.time.array.as_unit('ns').asi8
    raw_ns = raw_m1.time.array.as_unit('ns').asi8
    raw_open = raw_m1.open.to_numpy(dtype=float)
    signals = np.asarray(signals, dtype=bool)
    ledger: list[dict] = []
    state = None
    counts = {
        'signals_total': int(signals.sum()),
        'ignored_overlap_signals': 0,
        'excluded_year_boundary_signals': 0,
        'missing_reference_trades': 0,
        'executable_trades': 0,
    }
    n = len(source)

    for i in range(n):
        available_ns = int(source_ns[i] + tf_seconds * 1_000_000_000)

        if state is not None and available_ns >= state['exit_available_ns']:
            exit_idx = int(np.searchsorted(raw_ns, state['exit_available_ns'], side='left'))
            if state['entry_idx'] >= len(raw_ns) or exit_idx >= len(raw_ns):
                counts['missing_reference_trades'] += 1
            else:
                entry_ns = int(raw_ns[state['entry_idx']]); exit_ns = int(raw_ns[exit_idx])
                entry_year = pd.Timestamp(entry_ns, tz='UTC').year
                exit_year = pd.Timestamp(exit_ns, tz='UTC').year
                if entry_year == state['signal_year'] == exit_year and exit_ns < int(PROTECTED.value):
                    oe = float(raw_open[state['entry_idx']]); ox = float(raw_open[exit_idx])
                    ledger.append({
                        'signal_index': state['signal_index'],
                        'signal_time': pd.Timestamp(state['signal_ns'], tz='UTC').isoformat(),
                        'entry_time': pd.Timestamp(entry_ns, tz='UTC').isoformat(),
                        'exit_time': pd.Timestamp(exit_ns, tz='UTC').isoformat(),
                        'entry_open': oe, 'exit_open': ox, 'direction': int(direction),
                        'profiles': {p: cost(oe, ox, direction, p) for p in PROFILES},
                    })
                else:
                    counts['excluded_year_boundary_signals'] += 1
            state = None

        if not signals[i]:
            continue
        if state is not None:
            counts['ignored_overlap_signals'] += 1
            continue

        exit_source_index = i + horizon + 1
        if exit_source_index >= n:
            counts['excluded_year_boundary_signals'] += 1
            continue
        signal_year = int(source.time.iloc[i].year)
        if signal_year not in (2024, 2025) or int(source.time.iloc[exit_source_index].year) != signal_year:
            counts['excluded_year_boundary_signals'] += 1
            continue
        if available_ns >= int(PROTECTED.value):
            counts['excluded_year_boundary_signals'] += 1
            continue
        entry_idx = int(np.searchsorted(raw_ns, available_ns, side='left'))
        if entry_idx >= len(raw_ns):
            counts['missing_reference_trades'] += 1
            continue
        exit_available_ns = int(source_ns[exit_source_index])
        state = {
            'signal_index': int(i), 'signal_ns': int(source_ns[i]), 'signal_year': signal_year,
            'entry_idx': entry_idx, 'exit_available_ns': exit_available_ns,
        }

    if state is not None:
        exit_idx = int(np.searchsorted(raw_ns, state['exit_available_ns'], side='left'))
        if state['entry_idx'] < len(raw_ns) and exit_idx < len(raw_ns):
            entry_ns = int(raw_ns[state['entry_idx']]); exit_ns = int(raw_ns[exit_idx])
            if pd.Timestamp(entry_ns, tz='UTC').year == state['signal_year'] == pd.Timestamp(exit_ns, tz='UTC').year and exit_ns < int(PROTECTED.value):
                oe = float(raw_open[state['entry_idx']]); ox = float(raw_open[exit_idx])
                ledger.append({
                    'signal_index': state['signal_index'], 'signal_time': pd.Timestamp(state['signal_ns'], tz='UTC').isoformat(),
                    'entry_time': pd.Timestamp(entry_ns, tz='UTC').isoformat(), 'exit_time': pd.Timestamp(exit_ns, tz='UTC').isoformat(),
                    'entry_open': oe, 'exit_open': ox, 'direction': int(direction),
                    'profiles': {p: cost(oe, ox, direction, p) for p in PROFILES},
                })
            else:
                counts['excluded_year_boundary_signals'] += 1
        else:
            counts['missing_reference_trades'] += 1

    counts['executable_trades'] = len(ledger)
    return ledger, counts


def in_period(trade: dict, period: str) -> bool:
    start, end = PERIODS[period]
    e = pd.Timestamp(trade['entry_time'])
    x = pd.Timestamp(trade['exit_time'])
    return e >= start and x < end


def stats(trades: list[dict], profile: str) -> dict:
    vals = [t['profiles'][profile] for t in trades]
    nets = [v['net'] for v in vals]
    sums = {k: float(math.fsum(v[k] for v in vals)) for k in ('gross', 'spread', 'slippage', 'commission', 'net')}
    best = max(nets, default=0.0)
    losses = -math.fsum(x for x in nets if x < 0)
    wins = math.fsum(x for x in nets if x > 0)
    equity = peak = max_dd = 0.0
    for x in nets:
        equity += x
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return {
        **sums,
        'trades': len(nets),
        'expectancy': sums['net'] / len(nets) if nets else None,
        'expectancy_bps': float(np.mean([v['net'] / t['entry_open'] * 10000 for v, t in zip(vals, trades)])) if nets else None,
        'PF': wins / losses if losses else None,
        'win_rate': sum(x > 0 for x in nets) / len(nets) if nets else None,
        'max_drawdown_realized': float(max_dd),
        'best_trade': float(best) if nets else None,
        'worst_trade': float(min(nets)) if nets else None,
        'ex_best_positive_net': float(sums['net'] - max(0.0, best)),
    }


def decide(metrics: dict) -> tuple[str, list[str]]:
    reasons = []
    for p, minimum in [('2024', 100), ('2025', 100), ('2025_H1', 40), ('2025_H2', 40)]:
        if metrics[p]['E1']['trades'] < minimum:
            reasons.append(f'TRADE_COUNT_{p}_LT_{minimum}')
    for p in PERIODS:
        if metrics[p]['E1']['net'] <= 0:
            reasons.append('E1_NET_NONPOSITIVE_' + p)
    for p in ('2024', '2025'):
        if metrics[p]['STRESS']['net'] <= 0:
            reasons.append('STRESS_NET_NONPOSITIVE_' + p)
    if metrics['2025']['STRESS']['ex_best_positive_net'] <= 0:
        reasons.append('STRESS_2025_EX_BEST_NONPOSITIVE')
    return ('PASS' if not reasons else 'FAIL'), reasons


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--r5-result', required=True)
    ap.add_argument('--audit-result', required=True)
    ap.add_argument('--phase-ib-root', required=True)
    ap.add_argument('--output-dir', required=True)
    ap.add_argument('--progress-file')
    ap.add_argument('--publisher')
    args = ap.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    progress = Path(args.progress_file) if args.progress_file else None
    result_path = Path(args.r5_result)
    audit_path = Path(args.audit_result)
    root = Path(args.phase_ib_root)

    heartbeat(progress, 0, 96, 'provenance')
    if sha256_file(result_path) != EXPECTED_R5_SHA256:
        raise RuntimeError('R5 result hash mismatch')
    if sha256_file(audit_path) != EXPECTED_AUDIT_SHA256:
        raise RuntimeError('R5 cold-audit hash mismatch')
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    if audit.get('status') != 'PASS_INTERPRETABLE' or audit.get('material_semantic_change_count') != 0 or audit.get('protected_2026_opened') is not False:
        raise RuntimeError('upstream cold audit is not the frozen clean PASS')

    frozen = json.loads(result_path.read_text(encoding='utf-8'))
    survivors = frozen.get('survivors', [])
    if frozen.get('survivor_count') != 96 or len(survivors) != 96:
        raise RuntimeError('expected exactly 96 frozen R5 survivors')

    frames = {}
    for name, (digest, rows, _) in EXPECTED.items():
        path = root / name
        if not path.is_file() or sha256_file(path) != digest:
            raise RuntimeError('canonical input missing/hash mismatch: ' + name)
        mapping = r5.detect(path)
        if mapping is None:
            raise RuntimeError('cannot detect canonical input: ' + name)
        df = r5.load_market(path, mapping, max_rows=2_000_000)
        if len(df) != rows or (len(df) and df.time.max() >= PROTECTED):
            raise RuntimeError('canonical row/protected-boundary mismatch: ' + name)
        frames[name] = df

    raw_m1 = frames['xauusd_m1_2024_2025_raw.csv']
    feature_cache = {name: r5.features(df)[0] for name, df in frames.items()}
    results = []
    seen = set()

    for idx, rule in enumerate(survivors, 1):
        dataset_name = Path(str(rule.get('dataset', '')).replace('\\', '/')).name
        if dataset_name not in EXPECTED:
            raise RuntimeError('survivor references unmanifested dataset: ' + dataset_name)
        signature = (dataset_name, rule.get('feature'), rule.get('operator'), rule.get('quantile'), rule.get('cutpoint'), rule.get('horizon_bars'), rule.get('direction'), rule.get('hour_start'), rule.get('hour_width'))
        if signature in seen:
            raise RuntimeError('duplicate frozen survivor signature')
        seen.add(signature)
        if rule.get('execution') != 'signal_after_close_entry_next_open_exit_open_after_h_bars':
            raise RuntimeError('unexpected R5 execution annotation')

        source = frames[dataset_name]
        signals = r5.apply_rule(source, feature_cache[dataset_name], rule)
        tf_seconds = EXPECTED[dataset_name][2]
        ledger, counts = replay(source, raw_m1, signals, int(rule['horizon_bars']), int(rule['direction']), tf_seconds)
        metrics = {p: {profile: stats([t for t in ledger if in_period(t, p)], profile) for profile in PROFILES} for p in PERIODS}
        status, reasons = decide(metrics)
        results.append({
            'candidate_id': f'R5E-{idx:03d}',
            'dataset': dataset_name,
            'feature': rule['feature'], 'operator': rule['operator'], 'quantile': rule['quantile'], 'cutpoint': rule['cutpoint'],
            'horizon_bars': rule['horizon_bars'], 'direction': rule['direction'], 'hour_start': rule['hour_start'], 'hour_width': rule['hour_width'],
            'status': status, 'fail_reasons': reasons, 'signal_accounting': counts, 'metrics': metrics,
        })
        heartbeat(progress, idx, 96, 'economic_replay', {'candidate': idx, 'provisional_passes': sum(x['status'] == 'PASS' for x in results)})

    passes = [r for r in results if r['status'] == 'PASS']
    phase_status = 'PASS' if passes else 'FAIL'
    summary = {
        'schema': 1,
        'phase': 'r5-pre-oos-economic-robustness',
        'status': phase_status,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'r5_result_sha256': EXPECTED_R5_SHA256,
        'cold_audit_sha256': EXPECTED_AUDIT_SHA256,
        'frozen_survivor_count': 96,
        'pass_count': len(passes),
        'fail_count': 96 - len(passes),
        'cost_profiles': {k: {'commission_rate': v[0], 'spread': v[1], 'slippage_per_side': v[2]} for k, v in PROFILES.items()},
        'protected_2026_opened': False,
        'interpretation': 'Reject-only 2024/2025 economic feasibility. PASS is not an EA and does not authorize protected 2026.',
        'results': results,
    }
    json_path = out / 'r5_pre_oos_economic_robustness.json'
    csv_path = out / 'r5_pre_oos_economic_robustness.csv'
    atomic_json(json_path, summary)
    flat = []
    for r in results:
        row = {k: v for k, v in r.items() if k not in ('metrics', 'signal_accounting', 'fail_reasons')}
        row['fail_reasons'] = ';'.join(r['fail_reasons'])
        row.update({'signals_total': r['signal_accounting']['signals_total'], 'ignored_overlap_signals': r['signal_accounting']['ignored_overlap_signals'], 'executable_trades': r['signal_accounting']['executable_trades']})
        for period in PERIODS:
            for profile in PROFILES:
                m = r['metrics'][period][profile]
                for field in ('trades', 'gross', 'net', 'expectancy', 'expectancy_bps', 'PF', 'win_rate', 'max_drawdown_realized', 'ex_best_positive_net'):
                    row[f'{period}_{profile}_{field}'] = m[field]
        flat.append(row)
    pd.DataFrame(flat).to_csv(csv_path, index=False)
    heartbeat(progress, 96, 96, 'complete', {'passes': len(passes), 'status': phase_status})
    text = f'R5 pre-OOS economic robustness {phase_status}: {len(passes)}/96 frozen survivors pass inherited E1/STRESS reject-only gates; 2026 unopened.'
    publish(args.publisher, 'r5-pre-oos-economic-robustness', phase_status, text, [json_path, csv_path])
    print(json.dumps({'status': phase_status, 'passes': len(passes), 'total': 96, 'protected_2026_opened': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
