#!/usr/bin/env python3
"""Integrity/coverage check for Phenomenon Discovery Phase A datasets."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

FIVE_MIN_MS = 300_000


def inspect(path: Path) -> dict:
    with path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    ts = [int(r["timestamp_ms"]) for r in rows]
    gaps = Counter()
    duplicates = len(ts) - len(set(ts))
    for a, b in zip(ts, ts[1:]):
        d = b - a
        if d != FIVE_MIN_MS:
            gaps[d] += 1
    blank_oi = sum(1 for r in rows if not r.get("open_interest"))
    blank_atr = sum(1 for r in rows if "atr14" in r and not r.get("atr14"))
    return {
        "file": str(path),
        "rows": len(rows),
        "first_timestamp_utc": rows[0].get("timestamp_utc") if rows else None,
        "last_timestamp_utc": rows[-1].get("timestamp_utc") if rows else None,
        "duplicate_timestamps": duplicates,
        "non_5m_gap_count": sum(gaps.values()),
        "largest_gap_ms": max(gaps, default=FIVE_MIN_MS),
        "blank_open_interest": blank_oi,
        "blank_atr14": blank_atr,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--historical-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\historical_v1")
    ap.add_argument("--features-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1")
    args = ap.parse_args()
    files = sorted(Path(args.historical_dir).glob("*.csv")) + sorted(Path(args.features_dir).glob("*.csv"))
    if not files:
        raise SystemExit("No CSV datasets found")
    report = [inspect(p) for p in files]
    out = Path(args.features_dir) / "dataset_integrity_v1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"Integrity report: {out}")
    hard_fail = any(x["rows"] < 10_000 or x["duplicate_timestamps"] > 0 or x["blank_open_interest"] > 0 for x in report)
    return 2 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
