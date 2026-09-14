#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

PROTECTED_YEAR = 2026

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def atomic_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--output-manifest", required=True)
    args = ap.parse_args()

    cache = Path(args.cache_dir)
    if not cache.exists():
        raise SystemExit(f"cache directory missing: {cache}")

    files = sorted(cache.rglob("*.bi5"))
    if not files:
        raise SystemExit("no cached .bi5 payloads found")

    rows = []
    years = set()
    total_bytes = 0

    for p in files:
        rel = p.relative_to(cache).as_posix()
        parts = rel.split("/")
        try:
            year = int(parts[0])
        except Exception as e:
            raise RuntimeError(f"unrecognized cache layout: {rel}") from e
        if year >= PROTECTED_YEAR:
            raise RuntimeError(f"protected 2026+ payload present: {rel}")
        years.add(year)
        size = p.stat().st_size
        total_bytes += size
        rows.append({
            "relative_path": rel,
            "bytes": size,
            "sha256": sha256(p),
        })

    manifest = {
        "schema": 1,
        "status": "PASS",
        "dataset": "XAUUSD Dukascopy BID M1 master cache",
        "source_format": "Dukascopy BID_candles_min_1.bi5",
        "cache_dir": str(cache.resolve()),
        "payload_count": len(rows),
        "total_bytes": total_bytes,
        "years_present": sorted(years),
        "protected_2026_opened": False,
        "immutability_rule": "source payloads are read-only; derived datasets must be written separately",
        "reuse_rule": "reuse cache before remote download; derive higher timeframes locally from M1 when appropriate",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "payloads": rows,
    }

    out = Path(args.output_manifest)
    atomic_json(out, manifest)
    print(json.dumps({
        "status": "PASS",
        "payload_count": len(rows),
        "years_present": sorted(years),
        "total_bytes": total_bytes,
        "manifest": str(out),
        "protected_2026_opened": False,
    }))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
