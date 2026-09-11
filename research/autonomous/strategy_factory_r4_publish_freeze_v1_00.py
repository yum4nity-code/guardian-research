#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha256(obj) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def atomic_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    tmp.replace(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--policy', required=True)
    ap.add_argument('--output-dir', required=True)
    ap.add_argument('--progress-file')
    ap.add_argument('--consolidator', required=True)
    ap.add_argument('--publisher', required=True)
    args = ap.parse_args()

    inp = Path(args.input)
    policy = Path(args.policy)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Infrastructure/provenance repair only: rerun the already-frozen deterministic
    # R4 consolidation on the same pre-2026 source and unchanged policy.
    cmd = [
        sys.executable, args.consolidator,
        '--input', str(inp),
        '--policy', str(policy),
        '--output-dir', str(out),
    ]
    if args.progress_file:
        cmd += ['--progress-file', args.progress_file]
    subprocess.run(cmd, check=True)

    frozen_path = out / 'frozen_candidates.json'
    csv_path = out / 'frozen_candidates.csv'
    summary_path = out / 'consolidation_summary.json'
    frozen = json.loads(frozen_path.read_text(encoding='utf-8'))
    summary = json.loads(summary_path.read_text(encoding='utf-8'))

    if frozen.get('protected_2026_untouched') is not True:
        raise RuntimeError('freeze artifact does not prove protected 2026 untouched')
    if int(frozen.get('frozen_candidate_count', 0)) != len(frozen.get('candidates') or []):
        raise RuntimeError('candidate count mismatch')
    if int(frozen.get('frozen_candidate_count', 0)) != 32:
        raise RuntimeError('unexpected frozen candidate count; refusing to publish')

    candidate_set_sha = canonical_sha256(frozen['candidates'])
    manifest = {
        'schema': 1,
        'phase': 'strategy-factory-r4-consolidated-freeze',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'purpose': 'Publish and cryptographically identify the already-frozen R4 shortlist before any protected OOS request. No scientific selection is changed in this repair.',
        'source_result_sha256': frozen['source_result_sha256'],
        'policy_sha256': frozen['policy_sha256'],
        'frozen_candidate_count': frozen['frozen_candidate_count'],
        'candidate_set_sha256_canonical': candidate_set_sha,
        'frozen_json_sha256': sha256_file(frozen_path),
        'frozen_csv_sha256': sha256_file(csv_path),
        'protected_2026_untouched': True,
        'protected_2026_authorized': False,
        'next_gate': 'Separate committed protected-OOS preregistration plus explicit owner approval required before any 2026 data access.',
    }
    manifest_path = out / 'freeze_publication_manifest.json'
    atomic_json(manifest_path, manifest)

    publish_summary = (
        f"Published frozen R4 shortlist: {manifest['frozen_candidate_count']} candidates; "
        f"canonical candidate-set SHA256 {candidate_set_sha}; protected 2026 untouched and unauthorized."
    )
    subprocess.run([
        sys.executable, args.publisher,
        '--phase', 'strategy-factory-r4-consolidated-freeze',
        '--status', 'PASS',
        '--summary', publish_summary,
        '--artifact', str(manifest_path),
        '--artifact', str(frozen_path),
        '--artifact', str(csv_path),
        '--artifact', str(summary_path),
    ], check=True)

    print(json.dumps({
        'status': 'PASS',
        'frozen_candidates': manifest['frozen_candidate_count'],
        'candidate_set_sha256_canonical': candidate_set_sha,
        'protected_2026_untouched': True,
        'protected_2026_authorized': False,
    }, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
