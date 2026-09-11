#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import strategy_factory_causal_next_open_v1_00 as r5

PROTECTED = pd.Timestamp('2026-01-01', tz='UTC')
EXPECTED = {
    'xauusd_m1_2024_2025_raw.csv': {
        'rows': 710300,
        'sha256': 'f98a395961b27ca9dcb34cffa4ef8dd93720adb70292abf7bc96108667232445',
        'tf_seconds': 60,
    },
    'xauusd_m1_2024_2025_news_clean.csv': {
        'rows': 703387,
        'sha256': 'b116c61d0be7d73c455f4a4f897efdf0bf77a2b88594ed4b93ebee0d707570ee',
        'tf_seconds': 60,
    },
    'xauusd_m5_2024_2025_raw.csv': {
        'rows': 142549,
        'sha256': 'ba54c9b29755eac4284cb872805148736be529e954533c028e7f826bb444ce66',
        'tf_seconds': 300,
    },
    'xauusd_m5_2024_2025_news_clean.csv': {
        'rows': 140664,
        'sha256': '972ecaf6c3cadf7136363f396d7a29e7a6246646b575fad5c3e677036004b503',
        'tf_seconds': 300,
    },
}
EXPECTED_R5_SHA256 = '81dd16fabf001025c4dc144035d538fa46fab2fc768ba237610e027af1c7d34e'
EDGE_DRIFT_LIMIT = 0.005
SELECTED_MISMATCH_LIMIT = 0.01


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    tmp.replace(path)


def heartbeat(path: Path | None, done: int, total: int, stage: str, extra=None) -> None:
    if path is None:
        return
    obj = {
        'completed': int(done),
        'total': int(total),
        'stage': stage,
        'updated_at_utc': datetime.now(timezone.utc).isoformat(),
    }
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


def source_row_return(df: pd.DataFrame, atr: pd.Series, horizon: int, direction: int) -> np.ndarray:
    ent = df.open.shift(-1)
    ex = df.open.shift(-(horizon + 1))
    ret = np.array(((ex - ent) / atr * direction).to_numpy(dtype=float), dtype=float, copy=True)
    signal_year = df.time.dt.year.to_numpy()
    entry_year = df.time.shift(-1).dt.year.to_numpy()
    exit_year = df.time.shift(-(horizon + 1)).dt.year.to_numpy()
    valid = (
        np.isfinite(ret)
        & (signal_year == entry_year)
        & (entry_year == exit_year)
        & np.isin(signal_year, [2024, 2025])
    )
    ret[~valid] = np.nan
    return ret


def raw_m1_reference_return(
    source_df: pd.DataFrame,
    source_atr: pd.Series,
    raw_m1_df: pd.DataFrame,
    horizon: int,
    direction: int,
    tf_seconds: int,
) -> np.ndarray:
    """Replay a frozen source rule with first-available raw-M1 execution references.

    Entry is the first raw-M1 open at/after source-bar close. Exit preserves the
    frozen holding-bar target timestamp (source row t+h+1) and resolves that
    timestamp to the first raw-M1 open at/after it.
    """
    n = len(source_df)
    out = np.full(n, np.nan, dtype=float)
    if n == 0 or len(raw_m1_df) == 0:
        return out

    raw_ns = raw_m1_df.time.astype('int64').to_numpy()
    raw_open = raw_m1_df.open.to_numpy(dtype=float)
    source_ns = source_df.time.astype('int64').to_numpy()
    nat = np.iinfo(np.int64).min

    entry_target = source_ns + int(tf_seconds * 1_000_000_000)
    exit_ts = source_df.time.shift(-(horizon + 1))
    exit_ns = exit_ts.astype('int64').to_numpy()

    entry_idx = np.searchsorted(raw_ns, entry_target, side='left')
    safe_exit_target = np.where(exit_ns == nat, raw_ns[-1] + 1, exit_ns)
    exit_idx = np.searchsorted(raw_ns, safe_exit_target, side='left')

    good = (
        (exit_ns != nat)
        & (entry_idx < len(raw_ns))
        & (exit_idx < len(raw_ns))
        & np.isfinite(source_atr.to_numpy(dtype=float))
    )
    if not np.any(good):
        return out

    rows = np.flatnonzero(good)
    ent_i = entry_idx[rows]
    ex_i = exit_idx[rows]
    sig_year = source_df.time.dt.year.to_numpy()[rows]
    ent_year = pd.to_datetime(raw_ns[ent_i], utc=True).year.to_numpy()
    ex_year = pd.to_datetime(raw_ns[ex_i], utc=True).year.to_numpy()
    same_year = (sig_year == ent_year) & (ent_year == ex_year) & np.isin(sig_year, [2024, 2025])
    rows = rows[same_year]
    if len(rows) == 0:
        return out

    ent_i = entry_idx[rows]
    ex_i = exit_idx[rows]
    atrv = source_atr.to_numpy(dtype=float)[rows]
    out[rows] = direction * (raw_open[ex_i] - raw_open[ent_i]) / atrv
    return out


def edge_bundle(df: pd.DataFrame, selected: np.ndarray, base: np.ndarray, ret: np.ndarray, horizon: int):
    year = df.time.dt.year.to_numpy()
    month = df.time.dt.month.to_numpy()
    y24 = r5.welch_edge(selected & (year == 2024), base & (year == 2024), ret, 100)
    y25 = r5.welch_edge(selected & (year == 2025), base & (year == 2025), ret, 100)
    quarters = []
    for a, b in ((1, 3), (4, 6), (7, 9), (10, 12)):
        quarters.append(
            r5.welch_edge(
                selected & (year == 2025) & (month >= a) & (month <= b),
                base & (year == 2025) & (month >= a) & (month <= b),
                ret,
                30,
            )
        )
    hac = None
    if y25 is not None:
        hac = r5.hac_edge(
            selected & (year == 2025),
            base & (year == 2025),
            ret,
            max_lag=max(48, 2 * int(horizon)),
            min_n=100,
        )
    return {'y2024': y24, 'y2025': y25, 'quarters_2025': quarters, 'hac_2025': hac}


def numerical_gate(bundle) -> bool:
    y24 = bundle['y2024']
    y25 = bundle['y2025']
    qs = bundle['quarters_2025']
    hac = bundle['hac_2025']
    return bool(
        y24
        and y25
        and hac
        and all(qs)
        and y24['edge_atr'] > 0.02
        and y24['p_fast'] < 0.01
        and y25['edge_atr'] > 0.015
        and all(q['edge_atr'] > 0 for q in qs)
        and hac['p_hac'] < 0.05
    )


def mismatch_share(selected: np.ndarray, a: np.ndarray, b: np.ndarray) -> tuple[int, int, float]:
    fa = np.isfinite(a)
    fb = np.isfinite(b)
    evaluable = selected & (fa | fb)
    different = evaluable & ((fa != fb) | (fa & fb & (np.abs(a - b) > 1e-12)))
    den = int(evaluable.sum())
    num = int(different.sum())
    return num, den, (num / den if den else 0.0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--r5-result', required=True)
    ap.add_argument('--phase-ib-root', required=True)
    ap.add_argument('--output-dir', required=True)
    ap.add_argument('--progress-file')
    ap.add_argument('--publisher')
    args = ap.parse_args()

    result_path = Path(args.r5_result)
    root = Path(args.phase_ib_root)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    progress = Path(args.progress_file) if args.progress_file else None

    heartbeat(progress, 0, 1, 'provenance')
    provenance_failures = []
    r5_hash = sha256_file(result_path)
    if r5_hash != EXPECTED_R5_SHA256:
        provenance_failures.append(f'R5 result sha256 mismatch: {r5_hash}')
    frozen = json.loads(result_path.read_text(encoding='utf-8'))
    survivors = frozen.get('survivors', [])
    if int(frozen.get('survivor_count', -1)) != len(survivors):
        provenance_failures.append('R5 survivor_count does not match serialized survivor list')
    if len(survivors) != 96:
        provenance_failures.append(f'expected 96 frozen survivors, found {len(survivors)}')

    files = {}
    provenance_rows = []
    for name, spec in EXPECTED.items():
        path = root / name
        if not path.is_file():
            provenance_failures.append(f'missing canonical file: {name}')
            continue
        digest = sha256_file(path)
        mapping = r5.detect(path)
        if mapping is None:
            provenance_failures.append(f'cannot detect OHLC/time columns: {name}')
            continue
        df = r5.load_market(path, mapping, max_rows=2_000_000)
        rows = len(df)
        if digest != spec['sha256']:
            provenance_failures.append(f'hash mismatch: {name}: {digest}')
        if rows != spec['rows']:
            provenance_failures.append(f'row-count mismatch: {name}: {rows}')
        if len(df) and df.time.max() >= PROTECTED:
            provenance_failures.append(f'protected timestamp encountered: {name}')
        files[name] = df
        provenance_rows.append({'name': name, 'rows': rows, 'sha256': digest, 'max_time': str(df.time.max())})

    serialized_datasets = {Path(s.get('dataset', '')).name.lower() for s in survivors}
    unexpected = sorted(serialized_datasets - set(EXPECTED))
    if unexpected:
        provenance_failures.append(f'unexpected survivor datasets: {unexpected}')

    raw_m1 = files.get('xauusd_m1_2024_2025_raw.csv')
    diagnostics = []
    material = 0
    if provenance_failures or raw_m1 is None:
        status = 'FAIL_PROVENANCE'
    else:
        cache = {}
        total = max(1, len(survivors))
        for idx, rule in enumerate(survivors, 1):
            name = Path(rule['dataset']).name.lower()
            df = files[name]
            if name not in cache:
                ft, atr = r5.features(df)
                cache[name] = (ft, atr)
            ft, atr = cache[name]
            selected = r5.apply_rule(df, ft, rule)
            base = r5.base_mask(df, rule)
            h = int(rule['horizon_bars'])
            direction = int(rule['direction'])
            src_ret = source_row_return(df, atr, h, direction)
            raw_ret = raw_m1_reference_return(df, atr, raw_m1, h, direction, EXPECTED[name]['tf_seconds'])
            src_stats = edge_bundle(df, selected, base, src_ret, h)
            raw_stats = edge_bundle(df, selected, base, raw_ret, h)
            num_diff, den_diff, share_diff = mismatch_share(selected, src_ret, raw_ret)

            src_gate = numerical_gate(src_stats)
            raw_gate = numerical_gate(raw_stats)
            d24 = math.inf if not (src_stats['y2024'] and raw_stats['y2024']) else abs(src_stats['y2024']['edge_atr'] - raw_stats['y2024']['edge_atr'])
            d25 = math.inf if not (src_stats['y2025'] and raw_stats['y2025']) else abs(src_stats['y2025']['edge_atr'] - raw_stats['y2025']['edge_atr'])
            is_material = (not raw_gate) or (not src_gate) or d24 > EDGE_DRIFT_LIMIT or d25 > EDGE_DRIFT_LIMIT or share_diff > SELECTED_MISMATCH_LIMIT
            if is_material:
                material += 1

            diagnostics.append({
                'index': idx - 1,
                'dataset': name,
                'feature': rule['feature'],
                'operator': rule['operator'],
                'quantile': rule['quantile'],
                'horizon_bars': h,
                'direction': direction,
                'hour_start': rule.get('hour_start'),
                'hour_width': rule.get('hour_width'),
                'source_numerical_gate': src_gate,
                'raw_m1_numerical_gate': raw_gate,
                'selected_return_reference_mismatch_n': num_diff,
                'selected_return_reference_evaluable_n': den_diff,
                'selected_return_reference_mismatch_share': share_diff,
                'edge_drift_2024_atr': d24,
                'edge_drift_2025_atr': d25,
                'material_semantic_change': is_material,
                'source_stats': src_stats,
                'raw_m1_stats': raw_stats,
                'original_confirmation_bh_q': rule.get('confirmation_bh_q'),
            })
            if idx % 8 == 0 or idx == len(survivors):
                heartbeat(progress, idx, total, 'survivor_execution_replay', {'material_changes': material})

        status = 'PASS_INTERPRETABLE' if material == 0 else 'FAIL_SEMANTIC_DRIFT'

    summary_obj = {
        'schema': 1,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'status': status,
        'audit_type': 'reject_only_r5_post_result_execution_semantics_and_provenance',
        'r5_result_sha256': r5_hash,
        'expected_r5_result_sha256': EXPECTED_R5_SHA256,
        'frozen_survivor_count': len(survivors),
        'canonical_provenance': provenance_rows,
        'provenance_failures': provenance_failures,
        'material_semantic_change_count': material if not provenance_failures else None,
        'edge_drift_limit_atr': EDGE_DRIFT_LIMIT,
        'selected_reference_mismatch_limit': SELECTED_MISMATCH_LIMIT,
        'protected_2026_opened': False,
        'interpretation': (
            'R5 r2 may proceed only to a separately preregistered economic/reject-only robustness screen; protected 2026 remains sealed.'
            if status == 'PASS_INTERPRETABLE'
            else 'R5 r2 may not be promoted. If semantic drift is material, rerun a newly preregistered full discovery/confirmation family with raw-M1 execution semantics so BH-FDR is recomputed across the full family.'
            if status == 'FAIL_SEMANTIC_DRIFT'
            else 'Stop and repair provenance/infrastructure only; no scientific inference is permitted.'
        ),
    }

    summary_path = out / 'r5_post_result_cold_audit.json'
    diagnostics_path = out / 'r5_post_result_survivor_diagnostics.json'
    csv_path = out / 'r5_post_result_survivor_diagnostics.csv'
    atomic_json(summary_path, summary_obj)
    atomic_json(diagnostics_path, diagnostics)
    if diagnostics:
        flat = []
        for d in diagnostics:
            flat.append({k: v for k, v in d.items() if k not in {'source_stats', 'raw_m1_stats'}})
        pd.DataFrame(flat).to_csv(csv_path, index=False)
    else:
        pd.DataFrame().to_csv(csv_path, index=False)

    heartbeat(progress, 1, 1, 'complete', {'status': status, 'material_changes': material if not provenance_failures else None})
    summary = f'R5 cold audit {status}; frozen survivors={len(survivors)}; material semantic changes={material if not provenance_failures else "NA"}; protected 2026 unopened.'
    publish(args.publisher, 'r5-post-result-cold-audit', 'PASS' if status == 'PASS_INTERPRETABLE' else 'FAIL', summary, [summary_path, diagnostics_path, csv_path])
    print(json.dumps({'status': status, 'survivors': len(survivors), 'material_changes': material if not provenance_failures else None, 'protected_2026_opened': False}))
    return 0 if status == 'PASS_INTERPRETABLE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
