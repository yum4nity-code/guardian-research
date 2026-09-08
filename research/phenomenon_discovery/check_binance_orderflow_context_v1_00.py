#!/usr/bin/env python3
"""Integrity gate for Phase F-A Binance order-flow context."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_ROWS = 210528
STEP_MS = 300000
CUTOFF_2026_MS = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)

REQUIRED_NUMERIC = [
    "spot_taker_imbalance",
    "perp_taker_imbalance",
    "taker_imbalance_diff",
    "perp_spot_basis_bps",
    "log_quote_volume_ratio",
    "log_trade_count_ratio",
]


def inspect(path: Path) -> dict:
    rows = 0
    first = last = prev = None
    dup = gaps = future = avail_viol = 0
    missing = {k: 0 for k in REQUIRED_NUMERIC}
    seen: set[int] = set()
    with path.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows += 1
            ts = int(r["timestamp_ms"])
            available = int(r["feature_available_at_ms"])
            first = ts if first is None else first
            last = ts
            if ts in seen:
                dup += 1
            seen.add(ts)
            if prev is not None and ts - prev != STEP_MS:
                gaps += 1
            prev = ts
            if ts >= CUTOFF_2026_MS:
                future += 1
            if available != ts + STEP_MS:
                avail_viol += 1
            for k in REQUIRED_NUMERIC:
                if r.get(k, "") == "":
                    missing[k] += 1
                else:
                    float(r[k])
    return {
        "file": str(path),
        "rows": rows,
        "first_timestamp_ms": first,
        "last_timestamp_ms": last,
        "duplicate_timestamps": dup,
        "non_5m_gap_count": gaps,
        "opened_2026_rows": future,
        "feature_availability_violations": avail_viol,
        "missing_required_numeric": missing,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\binance_orderflow_v1")
    args = ap.parse_args()
    root = Path(args.input_dir)
    report = {"schema": 1, "phase": "F-A", "status": "PASS", "protected_2026_untouched": True, "symbols": {}}
    failures: list[str] = []
    for symbol in ("BTCUSDT", "ETHUSDT"):
        files = sorted(root.glob(f"{symbol}_binance_spot_um_5m_orderflow_*.csv"))
        if len(files) != 1:
            failures.append(f"{symbol}: expected exactly one orderflow file, found {len(files)}")
            continue
        rec = inspect(files[0])
        report["symbols"][symbol] = rec
        if rec["rows"] != EXPECTED_ROWS:
            failures.append(f"{symbol}: rows={rec['rows']} expected={EXPECTED_ROWS}")
        if rec["duplicate_timestamps"]:
            failures.append(f"{symbol}: duplicate timestamps={rec['duplicate_timestamps']}")
        if rec["non_5m_gap_count"]:
            failures.append(f"{symbol}: non-5m gaps={rec['non_5m_gap_count']}")
        if rec["opened_2026_rows"]:
            failures.append(f"{symbol}: opened 2026 rows={rec['opened_2026_rows']}")
        if rec["feature_availability_violations"]:
            failures.append(f"{symbol}: feature availability violations={rec['feature_availability_violations']}")
        for k, v in rec["missing_required_numeric"].items():
            if v:
                failures.append(f"{symbol}: missing {k} rows={v}")
    if failures:
        report["status"] = "FAIL"
        report["failures"] = failures
    out = root / "binance_orderflow_integrity_v1.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Integrity report: {out}")
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
