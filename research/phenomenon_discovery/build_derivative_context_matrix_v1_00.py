#!/usr/bin/env python3
"""Build causal derivative-context matrices for Phase E-A.

Joins validated Phase A feature rows to exact 5m mark/index/premium bars and uses
only the most recent already-settled funding record as of feature_available_at_ms.
No future funding value is used.
"""
from __future__ import annotations

import argparse
import csv
import json
from bisect import bisect_right
from pathlib import Path

INTERVAL_MS = 5 * 60 * 1000


def fnum(x: str | None):
    if x is None or x == "":
        return None
    return float(x)


def load_context(path: Path) -> dict[int, dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return {int(r["timestamp_ms"]): r for r in csv.DictReader(f)}


def load_funding(path: Path) -> tuple[list[int], list[float]]:
    ts, vals = [], []
    with path.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ts.append(int(r["funding_timestamp_ms"]))
            vals.append(float(r["funding_rate"]))
    return ts, vals


def asof_funding(ts: int, times: list[int], vals: list[float]):
    j = bisect_right(times, ts) - 1
    if j < 0:
        return None, None, None
    prev = vals[j - 1] if j > 0 else None
    return times[j], vals[j], prev


def lag(rows: list[dict], idx: int, field: str, bars: int):
    j = idx - bars
    if j < 0:
        return None
    if rows[idx]["timestamp_ms"] - rows[j]["timestamp_ms"] != bars * INTERVAL_MS:
        return None
    return rows[j].get(field)


def pct_change(cur, old):
    if cur is None or old is None or old == 0:
        return None
    return (cur / old - 1.0) * 100.0


def delta(cur, old):
    if cur is None or old is None:
        return None
    return cur - old


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1")
    ap.add_argument("--context-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\derivative_context_v1")
    ap.add_argument("--output-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\derivative_matrix_v1")
    args = ap.parse_args()

    feat_dir = Path(args.features_dir)
    ctx_dir = Path(args.context_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": 1, "symbols": {}}

    for symbol in ("BTCUSDT", "ETHUSDT"):
        feat_files = sorted(feat_dir.glob(f"{symbol}_bybit_5m_oi_price_*_features_v1.csv"))
        ctx_files = sorted(ctx_dir.glob(f"{symbol}_bybit_derivative_5m_*.csv"))
        fund_files = sorted(ctx_dir.glob(f"{symbol}_bybit_funding_*.csv"))
        if len(feat_files) != 1 or len(ctx_files) != 1 or len(fund_files) != 1:
            raise RuntimeError(f"{symbol}: expected exactly one feature/context/funding file")

        context = load_context(ctx_files[0])
        fund_ts, fund_vals = load_funding(fund_files[0])
        with feat_files[0].open("r", newline="", encoding="utf-8") as f:
            features = list(csv.DictReader(f))

        base_rows = []
        missing_context = 0
        missing_funding = 0
        for r in features:
            ts = int(r["timestamp_ms"])
            c = context.get(ts)
            if c is None:
                missing_context += 1
                continue
            available = int(r.get("feature_available_at_ms") or (ts + INTERVAL_MS))
            settled_ts, settled_rate, prev_rate = asof_funding(available, fund_ts, fund_vals)
            if settled_rate is None:
                missing_funding += 1
            row = dict(r)
            row.update({
                "mark_close": c["mark_close"],
                "index_close": c["index_close"],
                "premium_index_close": c["premium_index_close"],
                "mark_index_bps": c["mark_index_bps"],
                "funding_last_settled_ts_ms": "" if settled_ts is None else str(settled_ts),
                "funding_last_settled_rate": "" if settled_rate is None else repr(settled_rate),
                "funding_prev_settled_rate": "" if prev_rate is None else repr(prev_rate),
                "funding_delta_settlement": "" if settled_rate is None or prev_rate is None else repr(settled_rate - prev_rate),
                "minutes_since_funding_settlement": "" if settled_ts is None else repr((available - settled_ts) / 60000.0),
            })
            base_rows.append(row)

        for i, r in enumerate(base_rows):
            cur_mib = fnum(r.get("mark_index_bps"))
            cur_prem = fnum(r.get("premium_index_close"))
            for bars, tag in ((1, "5m"), (3, "15m"), (12, "1h")):
                old_mib = fnum(lag(base_rows, i, "mark_index_bps", bars))
                old_prem = fnum(lag(base_rows, i, "premium_index_close", bars))
                d1 = delta(cur_mib, old_mib)
                d2 = delta(cur_prem, old_prem)
                r[f"mark_index_bps_change_{tag}"] = "" if d1 is None else repr(d1)
                r[f"premium_index_change_{tag}"] = "" if d2 is None else repr(d2)

        out_path = out_dir / f"{symbol}_derivative_context_features_v1.csv"
        if not base_rows:
            raise RuntimeError(f"{symbol}: no joined rows")
        fields = list(base_rows[0].keys())
        with out_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(base_rows)

        manifest["symbols"][symbol] = {
            "rows": len(base_rows),
            "missing_context_rows_skipped": missing_context,
            "rows_without_asof_funding": missing_funding,
            "output_file": str(out_path),
        }
        print(f"{symbol}: rows={len(base_rows)} missing_context={missing_context} missing_funding={missing_funding}")

    mpath = out_dir / "derivative_matrix_manifest_v1.json"
    mpath.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Manifest: {mpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
