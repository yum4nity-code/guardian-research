#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path


def atomic_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def family(feature: str) -> str:
    if feature.startswith('ret'):
        return 'returns'
    if feature in {'range', 'body', 'uwick', 'lwick'}:
        return 'candle_structure'
    if feature.startswith('rsi'):
        return 'rsi'
    if feature.startswith('sma'):
        return 'trend_distance'
    if feature == 'atr_regime':
        return 'volatility_regime'
    if feature in {'hour', 'dow'}:
        return 'calendar'
    if feature == 'volz':
        return 'volume_activity'
    return feature


def edge(rule, key: str) -> float:
    block = rule.get(key) or {}
    return float(block.get('edge_atr', float('-inf')))


def robustness_score(rule) -> tuple:
    # Used only after every input rule has already passed the frozen R4 confirmation gate.
    # The protected 2026 period is not read here. Final-OOS remains mandatory.
    vals = [edge(rule, 'y2024'), edge(rule, 'y2025_hac'), edge(rule, 'y2025_h1_fast'), edge(rule, 'y2025_h2_fast')]
    worst = min(vals)
    q = float(rule.get('confirmation_bh_q', 1.0))
    n25 = int((rule.get('y2025_hac') or {}).get('n_selected', 0))
    # Prefer robust worst-slice edge, then lower q, then larger confirmation sample.
    return (worst, -q, n25)


def structural_key(rule) -> tuple:
    # Variants differing only in exact feature parameter/horizon/quantile remain within a mechanism bucket.
    return (
        str(rule.get('dataset', '')),
        family(str(rule.get('feature', ''))),
        str(rule.get('operator', '')),
        int(rule.get('direction', 0)),
        'session' if rule.get('hour_start') is not None else 'all_hours',
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--policy', required=True)
    ap.add_argument('--output-dir', required=True)
    ap.add_argument('--progress-file')
    args = ap.parse_args()

    inp = Path(args.input)
    policy_path = Path(args.policy)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    policy = json.loads(policy_path.read_text(encoding='utf-8'))
    src = json.loads(inp.read_text(encoding='utf-8'))

    if src.get('method') != 'conditional_edge_random_rule_factory':
        raise RuntimeError('unexpected source method')
    if src.get('protected_2026_untouched') is not True:
        raise RuntimeError('source does not prove protected 2026 untouched')
    if src.get('thresholds_fit_on_2024_only') is not True:
        raise RuntimeError('source thresholds were not fit on 2024 only')

    survivors = list(src.get('survivors') or [])
    if not survivors:
        raise RuntimeError('no R4 survivors to consolidate')

    buckets = {}
    for r in survivors:
        buckets.setdefault(structural_key(r), []).append(r)

    reps = []
    for key, rules in sorted(buckets.items(), key=lambda kv: repr(kv[0])):
        rules.sort(key=robustness_score, reverse=True)
        chosen = dict(rules[0])
        chosen['mechanism_family'] = family(str(chosen.get('feature', '')))
        chosen['structural_bucket_size'] = len(rules)
        chosen['structural_bucket_key'] = list(key)
        reps.append(chosen)

    # Diversity cap: limit concentration in any one dataset+direction while ranking only among already-confirmed rules.
    max_total = int(policy['max_frozen_candidates'])
    max_per_dataset_direction = int(policy['max_per_dataset_direction'])
    reps.sort(key=robustness_score, reverse=True)
    frozen, counts = [], {}
    for r in reps:
        k = (str(r.get('dataset', '')), int(r.get('direction', 0)))
        if counts.get(k, 0) >= max_per_dataset_direction:
            continue
        frozen.append(r)
        counts[k] = counts.get(k, 0) + 1
        if len(frozen) >= max_total:
            break

    if not frozen:
        raise RuntimeError('consolidation produced no frozen candidates')

    frozen_path = out / 'frozen_candidates.json'
    result = {
        'schema': 1,
        'method': 'r4_structural_consolidation',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_result_sha256': sha256_file(inp),
        'policy_sha256': sha256_file(policy_path),
        'source_survivor_count': len(survivors),
        'structural_bucket_count': len(buckets),
        'frozen_candidate_count': len(frozen),
        'protected_2026_untouched': True,
        'selection_note': 'Representatives selected only from already R4-confirmed rules; 2026 remains sealed. Protected final OOS is still mandatory and requires separate preregistration/authorization.',
        'candidates': frozen,
    }
    atomic_json(frozen_path, result)

    csv_path = out / 'frozen_candidates.csv'
    rows = []
    for i, r in enumerate(frozen, 1):
        rows.append({
            'candidate_id': f'R4F-{i:03d}',
            'dataset': r.get('dataset'),
            'mechanism_family': r.get('mechanism_family'),
            'feature': r.get('feature'),
            'operator': r.get('operator'),
            'quantile': r.get('quantile'),
            'cutpoint': r.get('cutpoint'),
            'horizon_bars': r.get('horizon_bars'),
            'direction': r.get('direction'),
            'hour_start': r.get('hour_start'),
            'hour_width': r.get('hour_width'),
            'bh_q': r.get('confirmation_bh_q'),
            'edge_2024': edge(r, 'y2024'),
            'edge_2025': edge(r, 'y2025_hac'),
            'edge_2025_h1': edge(r, 'y2025_h1_fast'),
            'edge_2025_h2': edge(r, 'y2025_h2_fast'),
            'bucket_size': r.get('structural_bucket_size'),
        })
    with csv_path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    summary = {
        'status': 'PASS',
        'source_survivors': len(survivors),
        'structural_buckets': len(buckets),
        'frozen_candidates': len(frozen),
        'protected_2026_untouched': True,
        'frozen_candidates_sha256': sha256_file(frozen_path),
        'csv_sha256': sha256_file(csv_path),
    }
    atomic_json(out / 'consolidation_summary.json', summary)
    if args.progress_file:
        atomic_json(Path(args.progress_file), {'completed': len(survivors), 'total': len(survivors), 'stage': 'complete', **summary, 'updated_at_utc': datetime.now(timezone.utc).isoformat()})
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
