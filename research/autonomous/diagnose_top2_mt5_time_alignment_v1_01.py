#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import r6_xau_low_turnover_breakout_v1_00 as r6

CANDIDATES = ("R6B-347", "R6B-307")
YEARS = (2024, 2025)
PHASE = "top2-mt5-time-alignment-diagnostic-r2"


def atomic_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_mt5(path: Path):
    z = pd.read_csv(path, sep=";")
    req = {"candidate_id", "entry_time", "exit_time"}
    if not req.issubset(z.columns):
        raise RuntimeError(f"bad MT5 trade csv: {path}")
    z["entry_time"] = pd.to_datetime(z["entry_time"], format="%Y.%m.%d %H:%M:%S", utc=True)
    z["exit_time"] = pd.to_datetime(z["exit_time"], format="%Y.%m.%d %H:%M:%S", utc=True)
    return z.sort_values(["entry_time", "exit_time"]).reset_index(drop=True)


def canonical_for(rule, source_all, raw_all, year):
    src = r6.year_slice(source_all, year)
    raw = r6.year_slice(raw_all, year)
    ledger, _, _ = r6.evaluate_year(rule, src, raw, year)
    return pd.DataFrame(
        {
            "entry_time": [pd.Timestamp(t["entry_time"]).tz_convert("UTC") for t in ledger],
            "exit_time": [pd.Timestamp(t["exit_time"]).tz_convert("UTC") for t in ledger],
        }
    ).sort_values(["entry_time", "exit_time"]).reset_index(drop=True)


def timestamp_ns(value) -> int:
    """Normalize any pandas datetime resolution to integer nanoseconds safely."""
    return int(pd.Timestamp(value).value)


def series_ns(series: pd.Series) -> np.ndarray:
    # Do not use Series.astype('int64'): pandas may preserve microsecond storage
    # resolution, while Timestamp.value is always nanoseconds. Mixing those units
    # created the invalid generation-65 ~-473k-hour offsets.
    return np.fromiter((timestamp_ns(v) for v in series), dtype=np.int64, count=len(series))


def nearest_offsets_hours(canon: pd.Series, mt5: pd.Series):
    if canon.empty or mt5.empty:
        return []
    m = series_ns(mt5)
    out = []
    for ts in canon:
        x = timestamp_ns(ts)
        j = int(np.abs(m - x).argmin())
        out.append(round((int(m[j]) - x) / 3_600_000_000_000, 6))
    return out


def summarize_offsets(vals):
    if not vals:
        return {"count": 0, "mode_hours": None, "mode_count": 0, "top_offsets_hours": []}
    rounded = [round(v, 3) for v in vals]
    c = Counter(rounded)
    top = c.most_common(10)
    return {
        "count": len(vals),
        "mode_hours": top[0][0],
        "mode_count": top[0][1],
        "top_offsets_hours": [{"hours": k, "count": v} for k, v in top],
    }


def exact_after_shift(canon: pd.DataFrame, mt5: pd.DataFrame, hours: float):
    d = pd.to_timedelta(hours, unit="h")
    c = {(a + d, b + d) for a, b in zip(canon.entry_time, canon.exit_time)}
    m = set(zip(mt5.entry_time, mt5.exit_time))
    e = {a + d for a in canon.entry_time}
    me = set(mt5.entry_time)
    return {
        "shift_hours": hours,
        "exact_entry_matches": len(e & me),
        "exact_pair_matches": len(c & m),
        "canonical_trades": len(canon),
        "mt5_trades": len(mt5),
    }


def timestamp_inventory(canon: pd.DataFrame, mt5: pd.DataFrame):
    def one(frame):
        if frame.empty:
            return {"count": 0, "entry_dtype": str(frame.entry_time.dtype), "first_entry": None, "last_entry": None}
        return {
            "count": int(len(frame)),
            "entry_dtype": str(frame.entry_time.dtype),
            "first_entry": pd.Timestamp(frame.entry_time.iloc[0]).isoformat(),
            "last_entry": pd.Timestamp(frame.entry_time.iloc[-1]).isoformat(),
            "first_entry_ns": timestamp_ns(frame.entry_time.iloc[0]),
            "last_entry_ns": timestamp_ns(frame.entry_time.iloc[-1]),
        }

    return {"canonical": one(canon), "mt5": one(mt5)}


def publish(publisher: str | None, result_path: Path):
    if not publisher:
        return
    result = json.loads(result_path.read_text(encoding="utf-8"))
    parts = []
    for cid in CANDIDATES:
        for year in YEARS:
            rec = result["candidates"][cid]["years"][str(year)]
            best = max(rec["shift_match_table"], key=lambda x: (x["exact_pair_matches"], x["exact_entry_matches"]))
            parts.append(
                f"{cid} {year}: nearest_mode={rec['nearest_entry_offset_summary']['mode_hours']}h; "
                f"best_shift={best['shift_hours']}h pair={best['exact_pair_matches']}/{best['canonical_trades']} "
                f"entry={best['exact_entry_matches']}/{best['canonical_trades']}"
            )
    summary = "Resolution-safe MT5/canonical timestamp diagnostic; " + "; ".join(parts) + "; 2026 unopened."
    subprocess.run(
        ["python", publisher, "--phase", PHASE, "--status", "PASS", "--summary", summary, "--artifact", str(result_path)],
        check=True,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase-ib-root", required=True)
    ap.add_argument("--mt5-dir", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--publisher")
    args = ap.parse_args()

    ib = Path(args.phase_ib_root)
    mt5dir = Path(args.mt5_dir)
    out = Path(args.output)
    source_all = r6.load_exact(ib / "xauusd_m5_2024_2025_news_clean.csv")
    raw_all = r6.load_exact(ib / "xauusd_m1_2024_2025_raw.csv")
    rules = {x["candidate_id"]: x for x in r6.definition_grid()}

    result = {
        "schema": 2,
        "phase": PHASE,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "protected_2026_opened": False,
        "canonical_inputs": r6.EXPECTED,
        "purpose": "Infrastructure timestamp diagnosis only; frozen R6 rules are unchanged.",
        "repair": "Normalize every compared timestamp through pandas.Timestamp.value nanoseconds; never mix Series integer storage resolutions.",
        "candidates": {},
    }

    for cid in CANDIDATES:
        z = load_mt5(mt5dir / f"{cid}_TRADES.csv")
        rec = {"years": {}}
        for year in YEARS:
            c = canonical_for(rules[cid], source_all, raw_all, year)
            m = z[z.entry_time.dt.year == year].reset_index(drop=True)
            offsets = nearest_offsets_hours(c.entry_time, m.entry_time)
            sm = summarize_offsets(offsets)
            mode = sm["mode_hours"]
            shifts = []
            candidate_shifts = {-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0}
            if mode is not None:
                candidate_shifts.add(float(mode))
            for h in sorted(candidate_shifts):
                shifts.append(exact_after_shift(c, m, h))
            rec["years"][str(year)] = {
                "timestamp_inventory": timestamp_inventory(c, m),
                "nearest_entry_offset_summary": sm,
                "shift_match_table": shifts,
            }
        result["candidates"][cid] = rec

    atomic_json(out, result)
    publish(args.publisher, out)
    print(json.dumps({"status": "PASS", "protected_2026_opened": False, "output": str(out), "phase": PHASE}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
