#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-path', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--symbol-root', default='XAUUSD')
    args = ap.parse_args()

    root = Path(args.data_path)
    if not root.exists():
        raise RuntimeError(f'data path missing: {root}')

    symbol = args.symbol_root.lower()
    candidates = []
    for p in root.rglob('*'):
        if not p.is_file():
            continue
        name = p.name.lower()
        full = str(p).lower()
        if symbol not in full:
            continue
        if p.suffix.lower() not in {'.hcc', '.hc', '.hst', '.dat', '.raw'}:
            continue
        st = p.stat()
        candidates.append({
            'path': str(p),
            'suffix': p.suffix.lower(),
            'size_bytes': int(st.st_size),
            'mtime_utc': datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
        })

    candidates.sort(key=lambda x: (x['suffix'], x['path']))
    year_markers = {str(y): [] for y in (2024, 2025)}
    for c in candidates:
        low = c['path'].lower()
        for y in year_markers:
            if y in low:
                year_markers[y].append(c['path'])

    out = {
        'schema': 1,
        'status': 'PASS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'data_path': str(root),
        'symbol_root': args.symbol_root,
        'candidate_file_count': len(candidates),
        'candidate_total_bytes': sum(c['size_bytes'] for c in candidates),
        'year_markers': year_markers,
        'files': candidates,
        'protected_2026_untouched': True,
        'note': 'Read-only filesystem inventory only; no market data rows were opened or parsed, including 2026.'
    }
    op = Path(args.output)
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
