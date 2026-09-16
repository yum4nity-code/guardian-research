#!/usr/bin/env python3
"""Build the physically sealed R21-R25 discovery M5 slice from R15 master index.

This v1.02 builder has no confirmation/pre-OOS mode and no arbitrary date arguments.
It may open payloads only from 2004-11-08 through 2019-06-30 inclusive.
Index metadata after that date may be scanned for integrity, but market payload bytes
outside the discovery window are never opened.
"""
from __future__ import annotations

import argparse
import csv
import os
from datetime import date, datetime, timezone
from pathlib import Path

DISCOVERY_START = date(2004, 11, 8)
DISCOVERY_END = date(2019, 6, 30)
PROTECTED_START = date(2026, 1, 1)


def parse_discovery_rows(index_csv: Path) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    previous: date | None = None
    with index_csv.open("r", newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        required = {"date", "path", "sha256", "bytes"}
        missing = required - set(r.fieldnames or [])
        if missing:
            raise RuntimeError(f"payload index missing columns: {sorted(missing)}")
        for row in r:
            d = date.fromisoformat(row["date"])
            if d >= PROTECTED_START:
                raise RuntimeError(f"PROTECTED 2026 index row encountered: {d}")
            if previous is not None and d <= previous:
                raise RuntimeError(f"non-increasing payload index date: {d} <= {previous}")
            previous = d
            if DISCOVERY_START <= d <= DISCOVERY_END:
                selected.append(row)
    if not selected:
        raise RuntimeError("no payload rows in frozen R21-R25 discovery window")
    return selected


def _assert_discovery_payload_date(d: date) -> None:
    if not DISCOVERY_START <= d <= DISCOVERY_END:
        raise RuntimeError(f"refusing to open non-discovery payload: {d}")


def _canonical_builder_api():
    from build_xau_m5_from_r15_master_v1_00 import decode_day, aggregate_m5, sha256
    return decode_day, aggregate_m5, sha256


def build(index_csv: Path, output_csv: Path, progress_callback=None) -> dict:
    decode_day, aggregate_m5, sha256 = _canonical_builder_api()
    rows = parse_discovery_rows(index_csv)
    tmp = output_csv.with_suffix(output_csv.suffix + ".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    total_m1 = total_m5 = dropped = 0
    prev_epoch: int | None = None
    opened_dates: list[str] = []

    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "timeframe", "server_time", "server_epoch", "open", "high", "low", "close"])
        for row_number, row in enumerate(rows, 1):
            d = date.fromisoformat(row["date"])
            _assert_discovery_payload_date(d)
            payload = Path(row["path"])
            # Payload bytes are first touched only after the hard discovery-date gate above.
            m1 = decode_day(d, payload, row["sha256"], int(row["bytes"]))
            opened_dates.append(d.isoformat())
            m5, drop = aggregate_m5(m1)
            total_m1 += len(m1)
            dropped += drop
            for epoch, o, h, l, c in m5:
                dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
                if not DISCOVERY_START <= dt.date() <= DISCOVERY_END:
                    raise RuntimeError(f"out-of-discovery M5 emitted: {dt.isoformat()}")
                if prev_epoch is not None and epoch <= prev_epoch:
                    raise RuntimeError(f"non-increasing M5 epoch: {epoch}")
                prev_epoch = epoch
                total_m5 += 1
                w.writerow([
                    "XAUUSD", "M5", dt.isoformat(), epoch,
                    f"{o:.3f}", f"{h:.3f}", f"{l:.3f}", f"{c:.3f}",
                ])
            if progress_callback is not None and (
                row_number == 1 or row_number == len(rows) or row_number % 10 == 0
            ):
                progress_callback({
                    "completed": row_number,
                    "total": len(rows),
                    "last_opened_payload_date": d.isoformat(),
                    "decoded_m1": total_m1,
                    "emitted_m5": total_m5,
                    "dropped_partial_m5_buckets": dropped,
                })

    os.replace(tmp, output_csv)
    return {
        "status": "PASS",
        "stage": "discovery",
        "stage_start": DISCOVERY_START.isoformat(),
        "stage_end_inclusive": DISCOVERY_END.isoformat(),
        "source_days": len(rows),
        "first_opened_payload_date": opened_dates[0],
        "last_opened_payload_date": opened_dates[-1],
        "decoded_m1": total_m1,
        "emitted_m5": total_m5,
        "dropped_partial_m5_buckets": dropped,
        "confirmation_opened": False,
        "pre_oos_2025_opened": False,
        "protected_2026_opened": False,
        "output": str(output_csv.resolve()),
        "output_sha256": sha256(output_csv),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    a = ap.parse_args()
    result = build(a.index, a.output)
    import json
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
