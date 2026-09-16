#!/usr/bin/env python3
"""R30 build v1.01: canonical Dukascopy XAUUSD yearly M1/M5 slices, 2004-2025.

Reads only the pinned R15 master payload index. Every BI5 payload is verified
before decode through the reviewed R15 builder helpers. Outputs per-year raw
M1 and exact complete-bucket M5 CSVs plus SHA256 manifest.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

PHENOMENON_DIR = Path(__file__).resolve().parents[1] / "phenomenon_discovery"
if str(PHENOMENON_DIR) not in sys.path:
    sys.path.insert(0, str(PHENOMENON_DIR))

import build_xau_m5_from_r15_master_v1_00 as base

PINNED_INDEX_SHA256 = "d77fb76e5b5ee0600a488c331084e70972a8800a33ae59a957c1044dc39ef566"
PROTECTED_START = date(2026, 1, 1)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def heartbeat(path: Path | None, completed: int, total: int, stage: str, extra=None) -> None:
    if path is None:
        return
    payload = {
        "completed": int(completed),
        "total": int(total),
        "stage": stage,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "protected_2026_opened": False,
    }
    if extra:
        payload.update(extra)
    atomic_json(path, payload)


def open_year_files(out: Path, year: int):
    m1 = out / f"xauusd_m1_{year}.csv"
    m5 = out / f"xauusd_m5_{year}.csv"
    for p in (m1, m5):
        if p.exists():
            raise RuntimeError(f"R30 yearly output already exists: {p}")
    f1 = m1.open("w", newline="", encoding="utf-8")
    f5 = m5.open("w", newline="", encoding="utf-8")
    w1 = csv.writer(f1)
    w5 = csv.writer(f5)
    header = ["symbol","timeframe","server_time","server_epoch","open","high","low","close"]
    w1.writerow(header)
    w5.writerow(header)
    return m1, m5, f1, f5, w1, w5


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--progress-file", type=Path)
    args = ap.parse_args()

    index = args.index
    out = args.output_dir
    manifest_path = args.manifest
    progress = args.progress_file

    if manifest_path.exists():
        raise RuntimeError("existing R30 build manifest detected; refusing overwrite")
    out.mkdir(parents=True, exist_ok=True)
    # A missing final manifest means a prior build did not complete. Clean only
    # R30's dedicated yearly CSV surface so a failed partial run can restart.
    for stale in list(out.glob("xauusd_m1_*.csv")) + list(out.glob("xauusd_m5_*.csv")):
        if stale.is_file() and not stale.is_symlink():
            stale.unlink()
    if sha256(index) != PINNED_INDEX_SHA256:
        raise RuntimeError("R30 pinned R15 index SHA256 mismatch")

    rows = base.parse_index(index)
    if not rows:
        raise RuntimeError("empty pinned R15 index")
    if date.fromisoformat(rows[-1]["date"]) >= PROTECTED_START:
        raise RuntimeError("protected 2026+ index row encountered")

    total = len(rows)
    heartbeat(progress, 0, total, "decode_yearly")

    current_year = None
    handles = None
    yearly = {}
    total_m1 = total_m5 = dropped_partial = 0
    previous_global_m1 = None
    previous_global_m5 = None

    def close_current():
        nonlocal handles
        if handles is not None:
            _, _, f1, f5, _, _ = handles
            f1.close(); f5.close()
            handles = None

    try:
        for n, row in enumerate(rows, 1):
            d = date.fromisoformat(row["date"])
            if d >= PROTECTED_START:
                raise RuntimeError(f"protected 2026 payload requested: {d}")

            if current_year != d.year:
                close_current()
                current_year = d.year
                handles = open_year_files(out, current_year)
                m1_path, m5_path, _, _, _, _ = handles
                yearly[str(current_year)] = {
                    "m1_path": str(m1_path.resolve()),
                    "m5_path": str(m5_path.resolve()),
                    "m1_rows": 0,
                    "m5_rows": 0,
                    "source_days": 0,
                    "first_date": d.isoformat(),
                    "last_date": d.isoformat(),
                }

            m1_path, m5_path, f1, f5, w1, w5 = handles
            decoded = base.decode_day(
                d,
                Path(row["path"]),
                row["sha256"],
                int(row["bytes"]),
            )
            m5, dropped = base.aggregate_m5(decoded)
            dropped_partial += dropped
            rec = yearly[str(current_year)]
            rec["source_days"] += 1
            rec["last_date"] = d.isoformat()

            for b in decoded:
                if previous_global_m1 is not None and b.epoch <= previous_global_m1:
                    raise RuntimeError("non-increasing global M1 timestamp")
                previous_global_m1 = b.epoch
                dt = datetime.fromtimestamp(b.epoch, tz=timezone.utc)
                w1.writerow([
                    "XAUUSD","M1",dt.isoformat(),b.epoch,
                    f"{b.open:.3f}",f"{b.high:.3f}",f"{b.low:.3f}",f"{b.close:.3f}"
                ])
                rec["m1_rows"] += 1
                total_m1 += 1

            for epoch, o, h, lo, c in m5:
                if previous_global_m5 is not None and epoch <= previous_global_m5:
                    raise RuntimeError("non-increasing global M5 timestamp")
                previous_global_m5 = epoch
                dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
                w5.writerow([
                    "XAUUSD","M5",dt.isoformat(),epoch,
                    f"{o:.3f}",f"{h:.3f}",f"{lo:.3f}",f"{c:.3f}"
                ])
                rec["m5_rows"] += 1
                total_m5 += 1

            if n % 25 == 0 or n == total:
                heartbeat(
                    progress,n,total,"decode_yearly",
                    {
                        "year":current_year,
                        "decoded_m1":total_m1,
                        "emitted_m5":total_m5,
                        "last_date":d.isoformat(),
                    }
                )
                print(f"progress days={n}/{total} year={current_year} m1={total_m1} m5={total_m5}", flush=True)
    finally:
        close_current()

    heartbeat(progress,total,total,"hash_outputs")
    for y, rec in yearly.items():
        rec["m1_sha256"] = sha256(Path(rec["m1_path"]))
        rec["m5_sha256"] = sha256(Path(rec["m5_path"]))

    manifest = {
        "schema":1,
        "research":"R30",
        "stage":"dukascopy_yearly_build",
        "status":"PASS",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_index":str(index.resolve()),
        "source_index_sha256":PINNED_INDEX_SHA256,
        "source_days":total,
        "decoded_m1":total_m1,
        "emitted_m5":total_m5,
        "dropped_partial_m5_buckets":dropped_partial,
        "first_source_date":rows[0]["date"],
        "last_source_date":rows[-1]["date"],
        "protected_2026_opened":False,
        "yearly":yearly,
    }
    atomic_json(manifest_path, manifest)
    heartbeat(progress,total,total,"complete",{"manifest":str(manifest_path),"protected_2026_opened":False})
    print(json.dumps({
        "status":"PASS",
        "years":len(yearly),
        "source_days":total,
        "decoded_m1":total_m1,
        "emitted_m5":total_m5,
        "protected_2026_opened":False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
