#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, math, os, random, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import strategy_factory_causal_next_open_v1_00 as r5
import r5_pre_oos_economic_robustness_v1_00 as econ

PROTECTED = pd.Timestamp('2026-01-01', tz='UTC')
EXPECTED = {
    'xauusd_m5_2024_2025_news_clean.csv': '972ecaf6c3cadf7136363f396d7a29e7a6246646b575fad5c3e677036004b503',
    'xauusd_m1_2024_2025_raw.csv': 'f98a395961b27ca9dcb34cffa4ef8dd93720adb70292abf7bc96108667232445',
}
LOOKBACKS = [12, 24, 48, 96]
BUFFERS = [0.0, 0.10, 0.20]
HORIZONS = [12, 24, 48, 96]
SESSIONS = [('ALL', None, None), ('UTC00_08', 0, 8), ('UTC08_16', 8, 16), ('UTC16_24', 16, 24)]
DIRECTIONS = [('LONG', 1), ('SHORT', -1)]
BOOTSTRAPS = 2000


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
    for attempt, delay in enumerate((.05, .1, .2, .4, .8, 1.0)):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(delay)


def heartbeat(path: Path | None, done: int, total: int, stage: str, extra=None) -> None:
    if path is None:
        return
    x = {'completed': int(done), 'total': int(total), 'stage': stage, 'updated_at_utc': datetime.now(timezone.utc).isoformat()}
    if extra:
        x.update(extra)
    atomic_json(path, x)


def load_exact(path: Path) -> pd.DataFrame:
    if path.name not in EXPECTED:
        raise RuntimeError(f'unapproved input: {path.name}')
    got = sha256_file(path)
    if got != EXPECTED[path.name]:
        raise RuntimeError(f'hash mismatch {path.name}: {got}')
    mapping = r5.detect(path)
    if not mapping:
        raise RuntimeError(f'unreadable OHLC input: {path}')
    df = r5.load_market(path, mapping, 2_000_000)
    if (df.time >= PROTECTED).any():
        raise RuntimeError(f'protected row present: {path}')
    years = set(df.time.dt.year.unique().tolist())
    if not years.issubset({2024, 2025}):
        raise RuntimeError(f'unapproved calendar years in {path}: {sorted(years)}')
    return df


def atr14(df: pd.DataFrame) -> pd.Series:
    prev = df.close.shift(1)
    tr = pd.concat([(df.high-df.low).abs(), (df.high-prev).abs(), (df.low-prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()


def session_mask(df: pd.DataFrame, start: int | None, end: int | None) -> np.ndarray:
    if start is None:
        return np.ones(len(df), dtype=bool)
    h = df.time.dt.hour.to_numpy()
    return (h >= start) & (h < end)


def breakout_signal(df: pd.DataFrame, atr: pd.Series, lookback: int, buffer_atr: float, direction: int, start: int | None, end: int | None) -> np.ndarray:
    # shift(1) is mandatory: the breakout reference cannot contain bar t.
    prior_hi = df.high.shift(1).rolling(lookback, min_periods=lookback).max().to_numpy(float)
    prior_lo = df.low.shift(1).rolling(lookback, min_periods=lookback).min().to_numpy(float)
    a = atr.to_numpy(float)
    c = df.close.to_numpy(float)
    if direction == 1:
        sig = c > (prior_hi + buffer_atr * a)
    else:
        sig = c < (prior_lo - buffer_atr * a)
    return np.asarray(sig & np.isfinite(a) & session_mask(df, start, end), dtype=bool)


def trades_in_period(trades: list[dict], start: str, end: str) -> list[dict]:
    a = pd.Timestamp(start, tz='UTC'); b = pd.Timestamp(end, tz='UTC')
    return [t for t in trades if pd.Timestamp(t['entry_time']) >= a and pd.Timestamp(t['exit_time']) < b]


def pf(metric: dict) -> float:
    x = metric.get('PF')
    return float(x) if x is not None and math.isfinite(float(x)) else float('inf') if metric.get('net', 0) > 0 else 0.0


def bh_qvalues(pvals: list[float]) -> list[float]:
    n = len(pvals)
    if n == 0:
        return []
    order = np.argsort(np.asarray(pvals, float)); q = np.ones(n); prev = 1.0
    for k in range(n-1, -1, -1):
        idx = int(order[k]); rank = k + 1
        val = min(prev, float(pvals[idx]) * n / rank)
        q[idx] = val; prev = val
    return q.tolist()


def candidate_seed(candidate_id: str) -> int:
    return int(hashlib.sha256(candidate_id.encode('utf-8')).hexdigest()[:16], 16) & 0xFFFFFFFF


def day_block_bootstrap(trades: list[dict], profile: str, candidate_id: str, b: int = BOOTSTRAPS) -> dict:
    by_day: dict[str, list[float]] = {}
    for t in trades:
        day = pd.Timestamp(t['entry_time']).strftime('%Y-%m-%d')
        by_day.setdefault(day, []).append(float(t['profiles'][profile]['net']))
    days = sorted(by_day)
    if not days:
        return {'days': 0, 'resamples': b, 'p_one_sided': 1.0, 'mean': None, 'p05': None}
    blocks = [by_day[d] for d in days]
    observed = float(np.mean([x for block in blocks for x in block]))
    rng = random.Random(candidate_seed(candidate_id)); means = []
    for _ in range(b):
        vals = []
        for _j in range(len(blocks)):
            vals.extend(blocks[rng.randrange(len(blocks))])
        means.append(float(np.mean(vals)) if vals else 0.0)
    p = (1 + sum(x <= 0.0 for x in means)) / (b + 1)
    return {'days': len(days), 'resamples': b, 'p_one_sided': float(p), 'mean': observed, 'p05': float(np.quantile(means, .05))}


def publish(publisher: str | None, status: str, summary: str, artifacts: list[Path]) -> None:
    if not publisher:
        return
    cmd = ['python', publisher, '--phase', 'r6-xau-low-turnover-breakout', '--status', status, '--summary', summary]
    for a in artifacts:
        cmd += ['--artifact', str(a)]
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--phase-ib-root', required=True)
    ap.add_argument('--output-dir', required=True)
    ap.add_argument('--progress-file')
    ap.add_argument('--publisher')
    args = ap.parse_args()
    root = Path(args.phase_ib_root); out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    progress = Path(args.progress_file) if args.progress_file else None
    source_path = root / 'xauusd_m5_2024_2025_news_clean.csv'; raw_path = root / 'xauusd_m1_2024_2025_raw.csv'
    heartbeat(progress, 0, 384, 'load_and_verify')
    source = load_exact(source_path); raw = load_exact(raw_path); atr = atr14(source)
    candidates = []; idx = 0
    for L in LOOKBACKS:
        for buf in BUFFERS:
            for h in HORIZONS:
                for sname, st, en in SESSIONS:
                    for dname, direction in DIRECTIONS:
                        idx += 1; cid = f'R6B-{idx:03d}'
                        sig = breakout_signal(source, atr, L, buf, direction, st, en)
                        ledger, accounting = econ.replay(source, raw, sig, h, direction, 300)
                        t24 = trades_in_period(ledger, '2024-01-01', '2025-01-01')
                        m24 = {p: econ.stats(t24, p) for p in econ.PROFILES}
                        discovery_pass = (
                            m24['E1']['trades'] >= 30 and m24['E1']['net'] > 0 and m24['STRESS']['net'] > 0
                            and m24['E1']['ex_best_positive_net'] > 0 and pf(m24['E1']) > 1.0
                        )
                        rec = {'candidate_id': cid, 'lookback_bars': L, 'buffer_atr': buf, 'horizon_bars': h,
                               'session': sname, 'session_start': st, 'session_end': en, 'direction_name': dname,
                               'direction': direction, 'signal_accounting': accounting, 'y2024': m24,
                               'discovery_pass': bool(discovery_pass)}
                        if discovery_pass:
                            # 2025 is touched only after the 2024 gate for this frozen candidate definition.
                            t25 = trades_in_period(ledger, '2025-01-01', '2026-01-01')
                            h1 = trades_in_period(ledger, '2025-01-01', '2025-07-01')
                            h2 = trades_in_period(ledger, '2025-07-01', '2026-01-01')
                            rec['y2025'] = {p: econ.stats(t25, p) for p in econ.PROFILES}
                            rec['y2025_h1'] = {p: econ.stats(h1, p) for p in econ.PROFILES}
                            rec['y2025_h2'] = {p: econ.stats(h2, p) for p in econ.PROFILES}
                            rec['bootstrap_2025_e1'] = day_block_bootstrap(t25, 'E1', cid)
                        candidates.append(rec)
                        if idx % 16 == 0:
                            heartbeat(progress, idx, 384, 'grid_2024_then_2025_confirmation', {'discovery_passes': sum(x['discovery_pass'] for x in candidates)})
    discovery = [x for x in candidates if x['discovery_pass']]
    pvals = [x['bootstrap_2025_e1']['p_one_sided'] for x in discovery]
    qvals = bh_qvalues(pvals)
    survivors = []
    for r, q in zip(discovery, qvals):
        r['confirmation_bh_q'] = float(q)
        y = r['y2025']; a = r['y2025_h1']; b = r['y2025_h2']; boot = r['bootstrap_2025_e1']
        ok = (
            y['E1']['trades'] >= 30 and a['E1']['trades'] >= 12 and b['E1']['trades'] >= 12
            and y['E1']['net'] > 0 and a['E1']['net'] > 0 and b['E1']['net'] > 0
            and y['STRESS']['net'] > 0 and a['STRESS']['net'] > 0 and b['STRESS']['net'] > 0
            and y['E1']['ex_best_positive_net'] > 0 and pf(y['E1']) > 1.0
            and q <= .05 and boot['p05'] is not None and boot['p05'] > 0
        )
        r['confirmation_pass'] = bool(ok)
        if ok:
            survivors.append(r)
    result = {
        'schema': 1, 'phase': 'r6-xau-low-turnover-breakout', 'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'protected_2026_opened': False, 'scientific_family': 'structured_rolling_range_breakout_with_costs',
        'source_hashes': {k: EXPECTED[k] for k in EXPECTED}, 'grid_size': 384,
        'discovery_pass_count': len(discovery), 'survivor_count': len(survivors), 'survivors': survivors,
        'all_candidates': candidates,
        'interpretation': 'PASS is pre-OOS evidence only; it is not an EA and does not authorize protected 2026.'
    }
    result_path = out / 'r6_xau_low_turnover_breakout_result.json'; atomic_json(result_path, result)
    rows = []
    for r in candidates:
        rows.append({'candidate_id': r['candidate_id'], 'lookback_bars': r['lookback_bars'], 'buffer_atr': r['buffer_atr'],
                     'horizon_bars': r['horizon_bars'], 'session': r['session'], 'direction': r['direction_name'],
                     'discovery_pass': r['discovery_pass'], 'confirmation_pass': r.get('confirmation_pass', False),
                     'y2024_e1_net': r['y2024']['E1']['net'], 'y2024_stress_net': r['y2024']['STRESS']['net'],
                     'y2025_e1_net': r.get('y2025', {}).get('E1', {}).get('net'), 'y2025_stress_net': r.get('y2025', {}).get('STRESS', {}).get('net'),
                     'bh_q': r.get('confirmation_bh_q')})
    csv_path = out / 'r6_xau_low_turnover_breakout_candidates.csv'; pd.DataFrame(rows).to_csv(csv_path, index=False)
    heartbeat(progress, 384, 384, 'complete', {'discovery_passes': len(discovery), 'survivors': len(survivors)})
    status = 'PASS' if survivors else 'FAIL'
    summary = f'R6 structured low-turnover breakout {status}: {len(survivors)}/{len(discovery)} 2024 discovery candidates survive untouched 2025 economic confirmation; 2026 unopened.'
    publish(args.publisher, status, summary, [result_path, csv_path])
    print(json.dumps({'status': status, 'discovery_passes': len(discovery), 'survivors': len(survivors), 'protected_2026_opened': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
