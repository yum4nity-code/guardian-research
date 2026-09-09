#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    tmp.replace(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', required=True)
    ap.add_argument('--metaeditor', required=True)
    ap.add_argument('--target-source', required=True)
    ap.add_argument('--target-ex5', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    src = Path(args.source)
    meta = Path(args.metaeditor)
    dst = Path(args.target_source)
    ex5 = Path(args.target_ex5)
    out = Path(args.output)

    result = {
        'schema': 1,
        'phase': 'I-F-2026-CALENDAR-EXPORTER-PREP',
        'generated_at_utc': now(),
        'scientific_hypothesis_changed': False,
        'protected_market_content_opened': False,
        'protected_news_content_opened': False,
        'status': 'FAIL',
    }

    if not src.exists():
        result['reason'] = f'source missing: {src}'
        atomic_json(out, result)
        print(json.dumps(result, separators=(',', ':')))
        return 2
    if not meta.exists():
        result['reason'] = f'MetaEditor missing: {meta}'
        atomic_json(out, result)
        print(json.dumps(result, separators=(',', ':')))
        return 3

    text = src.read_text(encoding='utf-8', errors='strict')
    original_sha = sha256(src)

    replacements = [
        (r"input datetime InpFrom\s*=\s*D'2024\.01\.01 00:00:00';", "input datetime InpFrom = D'2026.01.01 00:00:00';"),
        (r"input datetime InpTo\s*=\s*D'2026\.01\.01 00:00:00';", "input datetime InpTo   = D'2026.09.01 00:00:00';"),
        (r'input string\s+InpCurrencies\s*=\s*"[^"]*";', 'input string   InpCurrencies = "USD";'),
        (r'input string\s+InpOutputCsv\s*=\s*"[^"]*";', 'input string   InpOutputCsv = "Guardian\\\\phase_if\\\\mt5_high_impact_calendar_2026_jan_aug.csv";'),
        (r'input string\s+InpManifestTxt\s*=\s*"[^"]*";', 'input string   InpManifestTxt = "Guardian\\\\phase_if\\\\mt5_calendar_terminal_manifest_2026_jan_aug.txt";'),
        (r"InpTo>D'2026\.01\.01 00:00:00'", "InpTo>D'2026.09.01 00:00:00'"),
        (r'Guardian Phase I-A: export 2024-2025 high-impact MT5 economic calendar in trade-server time\.',
         'Guardian Phase I-F: export preregistered Jan-Aug 2026 high-impact USD MT5 economic calendar in trade-server time.'),
        (r'I-A REFUSED: invalid date range or protected 2026 would be opened\.',
         'I-F REFUSED: invalid date range outside preregistered Jan-Aug 2026 window.'),
    ]

    changed = text
    counts = []
    for pattern, repl in replacements:
        changed, n = re.subn(pattern, repl, changed, count=1)
        counts.append({'pattern': pattern, 'count': n})

    required_counts = counts[:6]
    if any(x['count'] != 1 for x in required_counts):
        result['reason'] = 'deterministic source adaptation did not match every required frozen declaration/guard exactly once'
        result['replacement_counts'] = counts
        result['source_sha256'] = original_sha
        atomic_json(out, result)
        print(json.dumps(result, separators=(',', ':')))
        return 4

    # Fail closed if legacy protected-data guard or old output names remain.
    forbidden = [
        "InpTo>D'2026.01.01 00:00:00'",
        'mt5_high_impact_calendar_2024_2025.csv',
        'mt5_calendar_terminal_manifest.txt',
    ]
    leftovers = [x for x in forbidden if x in changed]
    if leftovers:
        result['reason'] = 'legacy 2024/2025 exporter tokens remain after adaptation'
        result['leftovers'] = leftovers
        atomic_json(out, result)
        print(json.dumps(result, separators=(',', ':')))
        return 5

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(changed, encoding='utf-8')

    # Compilation only. Do not launch terminal/script and do not read calendar contents in this job.
    cp = subprocess.run(
        [str(meta), f'/compile:{dst}', f'/log:{dst.with_suffix(".compile.log")}'],
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )

    compile_log = dst.with_suffix('.compile.log')
    log_tail = ''
    if compile_log.exists():
        log_tail = '\n'.join(compile_log.read_text(encoding='utf-16', errors='replace').splitlines()[-40:])

    result.update({
        'source_path': str(src),
        'source_sha256': original_sha,
        'target_source_path': str(dst),
        'target_source_sha256': sha256(dst),
        'target_ex5_path': str(ex5),
        'metaeditor_path': str(meta),
        'compile_exit_code': cp.returncode,
        'compile_stdout_tail': '\n'.join(cp.stdout.splitlines()[-20:]),
        'compile_stderr_tail': '\n'.join(cp.stderr.splitlines()[-20:]),
        'compile_log_tail': log_tail,
        'replacement_counts': counts,
        'frozen_window': {'start': '2026.01.01 00:00:00', 'end_exclusive': '2026.09.01 00:00:00'},
        'currencies': ['USD'],
    })

    if cp.returncode != 0 or not ex5.exists():
        result['reason'] = 'MetaEditor compilation failed or EX5 not produced'
        atomic_json(out, result)
        print(json.dumps(result, separators=(',', ':')))
        return 6

    result['target_ex5_sha256'] = sha256(ex5)
    result['status'] = 'PASS'
    result['reason'] = 'separate Phase I-F exporter prepared and compiled; no 2026 market/news content inspected'
    atomic_json(out, result)
    print(json.dumps(result, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
