#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd


def atomic_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    tmp.replace(path)


def heartbeat(path: Path | None, completed: int, total: int, stage: str):
    if path:
        atomic_json(path, {
            'completed': int(completed),
            'total': int(total),
            'stage': stage,
            'updated_at_utc': datetime.now(timezone.utc).isoformat(),
        })


def publish(publisher: str | None, status: str, summary: str, artifacts: list[Path]):
    if not publisher:
        return 0
    cmd = [sys.executable, publisher, '--phase', 'phase-ii-xau-directional-consolidation', '--status', status, '--summary', summary]
    for p in artifacts:
        if p.exists():
            cmd += ['--artifact', str(p)]
    return subprocess.run(cmd, text=True, capture_output=True).returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ih-csv', required=True)
    ap.add_argument('--policy', required=True)
    ap.add_argument('--output-dir', required=True)
    ap.add_argument('--progress-file')
    ap.add_argument('--publisher')
    args = ap.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    hb = Path(args.progress_file) if args.progress_file else None
    policy = json.loads(Path(args.policy).read_text(encoding='utf-8'))
    if policy.get('protected_2026_forbidden') is not True:
        raise RuntimeError('policy must explicitly forbid protected 2026')

    heartbeat(hb, 0, 100, 'load')
    df = pd.read_csv(args.ih_csv)
    required = {'family','feature','quintile','hour_block','horizon_bars','outcome','confirmation_n_state','confirmation_effect','confirmation_q','direction','robustness_pass'}
    missing = required - set(df.columns)
    if missing:
        raise RuntimeError(f'missing columns: {sorted(missing)}')

    elig = df[(df['robustness_pass'] == True) & (df['outcome'] == policy['eligible_outcome'])].copy()
    heartbeat(hb, 35, 100, 'eligible_directionals')
    if len(elig):
        elig['confirmation_q_sort'] = pd.to_numeric(elig['confirmation_q'], errors='coerce').fillna(math.inf)
        elig['abs_confirmation_effect'] = pd.to_numeric(elig['confirmation_effect'], errors='coerce').abs()
        elig['confirmation_n_state'] = pd.to_numeric(elig['confirmation_n_state'], errors='coerce').fillna(0)
        elig['horizon_bars'] = pd.to_numeric(elig['horizon_bars'], errors='coerce').fillna(10**9)
        elig['state_key'] = elig.apply(lambda r: f"{r['feature']}|Q{int(r['quintile'])}|H{r['hour_block']}|h{int(r['horizon_bars'])}", axis=1)
        elig = elig.sort_values(
            ['family','direction','confirmation_q_sort','abs_confirmation_effect','confirmation_n_state','horizon_bars','state_key'],
            ascending=[True,True,True,False,False,True,True],
            kind='mergesort'
        )
        reps = elig.groupby(['family','direction'], as_index=False, sort=True).head(1).copy()
    else:
        reps = elig.copy()

    heartbeat(hb, 70, 100, 'write')
    all_path = out / 'phase_ii_all_robust_directionals.csv'
    rep_path = out / 'phase_ii_independent_directional_representatives.csv'
    summary_path = out / 'phase_ii_summary.json'
    elig.drop(columns=['confirmation_q_sort'], errors='ignore').to_csv(all_path, index=False)
    reps.drop(columns=['confirmation_q_sort'], errors='ignore').to_csv(rep_path, index=False)

    families = sorted(reps['family'].astype(str).unique().tolist()) if len(reps) else []
    summary = {
        'schema': 1,
        'phase': 'I-I',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'protected_2026_untouched': True,
        'robust_directional_survivors': int(len(elig)),
        'independent_representatives': int(len(reps)),
        'families_represented': families,
        'status': 'PASS' if len(reps) else 'FAIL',
        'next_rule': 'If representatives exist, scientific supervisor may preregister protected final OOS only after explicit owner approval under current supervisor instruction. No strategy/PnL claim yet.'
    }
    atomic_json(summary_path, summary)
    heartbeat(hb, 100, 100, 'complete')
    status = summary['status']
    text = f"Phase I-I directional consolidation: robust_directionals={len(elig)} independent_representatives={len(reps)}; 2026 untouched."
    rc = publish(args.publisher, status, text, [summary_path, all_path, rep_path, Path(args.policy)])
    if rc != 0:
        raise RuntimeError(f'publisher exit {rc}')
    return 0 if status == 'PASS' else 10


if __name__ == '__main__':
    raise SystemExit(main())
