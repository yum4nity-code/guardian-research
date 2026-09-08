#!/usr/bin/env python3
"""Integrity and causality gate for Phase E-A derivative context."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_CONTEXT_ROWS = 210528
EXPECTED_MATRIX_ROWS = 210514
STEP_MS = 300000
CUTOFF_2026_MS = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)


def inspect_context(path: Path) -> dict:
    rows = 0
    first = last = prev = None
    dup = gaps = 0
    missing_mark = missing_index = missing_premium = 0
    seen: set[int] = set()
    with path.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows += 1
            ts = int(r["timestamp_ms"])
            first = ts if first is None else first
            last = ts
            if ts in seen:
                dup += 1
            seen.add(ts)
            if prev is not None and ts - prev != STEP_MS:
                gaps += 1
            prev = ts
            missing_mark += int(not r.get("mark_close"))
            missing_index += int(not r.get("index_close"))
            missing_premium += int(not r.get("premium_index_close"))
    return {
        "file": str(path),
        "rows": rows,
        "first_timestamp_ms": first,
        "last_timestamp_ms": last,
        "duplicate_timestamps": dup,
        "non_5m_gap_count": gaps,
        "missing_mark": missing_mark,
        "missing_index": missing_index,
        "missing_premium": missing_premium,
    }


def inspect_matrix(path: Path) -> dict:
    rows = 0
    first = last = prev = None
    dup = gaps = 0
    missing_mark = missing_index = missing_premium = missing_funding = 0
    future_funding_violations = 0
    feature_availability_violations = 0
    seen: set[int] = set()
    with path.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows += 1
            ts = int(r["timestamp_ms"])
            available = int(r.get("feature_available_at_ms") or (ts + STEP_MS))
            first = ts if first is None else first
            last = ts
            if ts in seen:
                dup += 1
            seen.add(ts)
            if prev is not None and ts - prev != STEP_MS:
                gaps += 1
            prev = ts
            missing_mark += int(not r.get("mark_close"))
            missing_index += int(not r.get("index_close"))
            missing_premium += int(not r.get("premium_index_close"))
            if not r.get("funding_last_settled_rate"):
                missing_funding += 1
            if r.get("funding_last_settled_ts_ms"):
                settled = int(r["funding_last_settled_ts_ms"])
                if settled > available:
                    future_funding_violations += 1
            if available < ts + STEP_MS:
                feature_availability_violations += 1
    return {
        "file": str(path),
        "rows": rows,
        "first_timestamp_ms": first,
        "last_timestamp_ms": last,
        "duplicate_timestamps": dup,
        "non_5m_gap_count": gaps,
        "missing_mark": missing_mark,
        "missing_index": missing_index,
        "missing_premium": missing_premium,
        "missing_asof_funding": missing_funding,
        "future_funding_violations": future_funding_violations,
        "feature_availability_violations": feature_availability_violations,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--context-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\derivative_context_v1")
    ap.add_argument("--matrix-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\derivative_matrix_v1")
    args = ap.parse_args()

    context_dir = Path(args.context_dir)
    matrix_dir = Path(args.matrix_dir)
    report = {"schema": 1, "status": "PASS", "protected_2026_untouched": True, "symbols": {}}
    failures: list[str] = []

    for symbol in ("BTCUSDT", "ETHUSDT"):
        context_files = sorted(context_dir.glob(f"{symbol}_bybit_derivative_5m_*.csv"))
        matrix_files = sorted(matrix_dir.glob(f"{symbol}_derivative_context_features_v1.csv"))
        if len(context_files) != 1:
            failures.append(f"{symbol}: expected exactly one derivative context file, found {len(context_files)}")
            continue
        if len(matrix_files) != 1:
            failures.append(f"{symbol}: expected exactly one derivative matrix file, found {len(matrix_files)}")
            continue

        c = inspect_context(context_files[0])
        m = inspect_matrix(matrix_files[0])
        report["symbols"][symbol] = {"context": c, "matrix": m}

        if c["rows"] != EXPECTED_CONTEXT_ROWS:
            failures.append(f"{symbol}: context rows {c['rows']} != {EXPECTED_CONTEXT_ROWS}")
        if m["rows"] != EXPECTED_MATRIX_ROWS:
            failures.append(f"{symbol}: matrix rows {m['rows']} != {EXPECTED_MATRIX_ROWS}")
        for name, rec in (("context", c), ("matrix", m)):
            if rec["duplicate_timestamps"] != 0:
                failures.append(f"{symbol}: {name} duplicate timestamps")
            if rec["non_5m_gap_count"] != 0:
                failures.append(f"{symbol}: {name} non-5m gaps")
            if rec["missing_mark"] != 0 or rec["missing_index"] != 0 or rec["missing_premium"] != 0:
                failures.append(f"{symbol}: {name} missing mark/index/premium")
            if rec["last_timestamp_ms"] is not None and rec["last_timestamp_ms"] >= CUTOFF_2026_MS:
                failures.append(f"{symbol}: {name} opened 2026 data")
        if m["missing_asof_funding"] != 0:
            failures.append(f"{symbol}: missing causal as-of funding rows={m['missing_asof_funding']}")
        if m["future_funding_violations"] != 0:
            failures.append(f"{symbol}: future funding violations={m['future_funding_violations']}")
        if m["feature_availability_violations"] != 0:
            failures.append(f"{symbol}: feature availability violations={m['feature_availability_violations']}")

    if failures:
        report["status"] = "FAIL"
        report["failures"] = failures

    matrix_dir.mkdir(parents=True, exist_ok=True)
    out = matrix_dir / "derivative_context_integrity_v1.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Integrity report: {out}")
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
