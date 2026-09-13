#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import os
import struct
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

START = date(2004, 11, 8)
END_EXCLUSIVE = date(2026, 1, 1)
NY = ZoneInfo("America/New_York")
NEEDED = {"11:30", "12:00", "15:30", "16:00"}
BASE = "https://datafeed.dukascopy.com/datafeed/XAUUSD"
FILE_NAME = "BID_candles_min_1.bi5"

def atomic_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def progress(path: Path | None, completed: int, total: int, stage: str, extra=None) -> None:
    if not path:
        return
    obj = {
        "completed": int(completed),
        "total": int(total),
        "stage": stage,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        obj.update(extra)
    atomic_json(path, obj)

def day_url(d: date) -> str:
    if d >= END_EXCLUSIVE:
        raise RuntimeError("protected 2026 request forbidden")
    return f"{BASE}/{d.year:04d}/{d.month - 1:02d}/{d.day:02d}/{FILE_NAME}"

def decode_day(d: date, payload: bytes) -> list[dict]:
    if not payload:
        return []
    try:
        raw = lzma.decompress(payload)
    except lzma.LZMAError as e:
        raise RuntimeError(f"{d}: LZMA decode failed") from e
    if len(raw) % 24 != 0:
        raise RuntimeError(f"{d}: malformed candle payload length={len(raw)}")
    out = []
    base = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    for off in range(0, len(raw), 24):
        sec, open_raw = struct.unpack_from(">II", raw, off)
        if not (0 <= sec < 86400):
            raise RuntimeError(f"{d}: invalid second-of-day {sec}")
        if open_raw <= 0:
            raise RuntimeError(f"{d}: nonpositive open")
        ts = base + timedelta(seconds=int(sec))
        local = ts.astimezone(NY)
        hm = local.strftime("%H:%M")
        if hm in NEEDED:
            out.append({
                "date_ny": local.date().isoformat(),
                "hm": hm,
                "timestamp_utc": ts.isoformat(),
                "open_raw": int(open_raw),
            })
    return out

def fetch_payload(d: date, retries: int = 5, timeout: int = 30) -> tuple[str, bytes | None]:
    url = day_url(d)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "guardian-research-r15/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                payload = r.read()
                if not payload:
                    return "missing", None
                return "ok", payload
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "missing", None
            last = e
        except Exception as e:
            last = e
        time.sleep(min(8.0, 0.75 * (2 ** attempt)))
    raise RuntimeError(f"{d}: download failed after {retries} attempts: {last}")

def weekdays(start: date, end_exclusive: date):
    d = start
    while d < end_exclusive:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)

def fetch_one(d: date) -> dict:
    status, payload = fetch_payload(d)
    if status == "missing":
        return {"date": d.isoformat(), "status": "missing", "rows": []}
    rows = decode_day(d, payload or b"")
    return {
        "date": d.isoformat(),
        "status": "ok",
        "payload_sha256": hashlib.sha256(payload or b"").hexdigest(),
        "rows": rows,
    }

def synthetic_record(sec: int, open_raw: int) -> bytes:
    return struct.pack(">IIIIIf", sec, open_raw, open_raw, open_raw, open_raw, 1.0)

def self_test() -> None:
    d = date(2025, 6, 2)
    raw = b"".join([
        synthetic_record(15 * 3600 + 30 * 60, 3330000),
        synthetic_record(16 * 3600, 3340000),
        synthetic_record(19 * 3600 + 30 * 60, 3350000),
        synthetic_record(20 * 3600, 3360000),
    ])
    payload = lzma.compress(raw)
    rows = decode_day(d, payload)
    got = {(x["hm"], x["open_raw"]) for x in rows}
    exp = {("11:30", 3330000), ("12:00", 3340000), ("15:30", 3350000), ("16:00", 3360000)}
    if got != exp:
        raise RuntimeError(f"DST/clock self-test failed: {got} != {exp}")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--progress-file")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--probe-only", action="store_true")
    args = ap.parse_args()

    self_test()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prog = Path(args.progress_file) if args.progress_file else None

    if args.probe_only:
        probes = [date(2005, 6, 1), date(2010, 6, 1), date(2019, 5, 1), date(2025, 6, 2)]
        report = []
        for d in probes:
            r = fetch_one(d)
            report.append({
                "date": d.isoformat(),
                "status": r["status"],
                "retained_boundaries": len(r["rows"]),
                "hms": [x["hm"] for x in r["rows"]],
            })
        if not all(x["status"] == "ok" and x["retained_boundaries"] >= 4 for x in report):
            raise RuntimeError(f"probe failed: {report}")
        print(json.dumps({"status": "PASS", "probe": report, "protected_2026_opened": False}))
        return 0

    days = list(weekdays(START, END_EXCLUSIVE))
    total = len(days)
    progress(prog, 0, total, "download_dukascopy_m1_boundaries")

    by_date: dict[str, dict[str, dict]] = {}
    missing_dates = []
    provenance = []
    completed = 0

    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 6))) as ex:
        futs = {ex.submit(fetch_one, d): d for d in days}
        for fut in as_completed(futs):
            d = futs[fut]
            r = fut.result()
            if r["status"] == "missing":
                missing_dates.append(d.isoformat())
            else:
                provenance.append({"date": r["date"], "payload_sha256": r["payload_sha256"]})
                for row in r["rows"]:
                    by_date.setdefault(row["date_ny"], {})[row["hm"]] = row
            completed += 1
            if completed % 25 == 0 or completed == total:
                progress(prog, completed, total, "download_dukascopy_m1_boundaries", {"last_date": d.isoformat()})

    rows_out = []
    for date_ny in sorted(by_date):
        rec = by_date[date_ny]
        if not NEEDED.issubset(rec):
            continue
        if date_ny >= "2026-01-01":
            raise RuntimeError("protected 2026 boundary row created")
        rows_out.append({
            "date_ny": date_ny,
            "ts_1130_utc": rec["11:30"]["timestamp_utc"],
            "p_1130_raw": rec["11:30"]["open_raw"],
            "ts_1200_utc": rec["12:00"]["timestamp_utc"],
            "p_1200_raw": rec["12:00"]["open_raw"],
            "ts_1530_utc": rec["15:30"]["timestamp_utc"],
            "p_1530_raw": rec["15:30"]["open_raw"],
            "ts_1600_utc": rec["16:00"]["timestamp_utc"],
            "p_1600_raw": rec["16:00"]["open_raw"],
        })

    df = pd.DataFrame(rows_out)
    if df.empty:
        raise RuntimeError("no eligible R15 boundary days downloaded")
    if pd.to_datetime(df["date_ny"]).max() >= pd.Timestamp("2026-01-01"):
        raise RuntimeError("protected 2026 found in compact dataset")

    csv_path = out_dir / "r15_dukascopy_xauusd_m1_boundaries_2004_2025.csv"
    df.to_csv(csv_path, index=False)

    prov_path = out_dir / "r15_dukascopy_daily_payload_provenance.csv"
    pd.DataFrame(sorted(provenance, key=lambda x: x["date"])).to_csv(prov_path, index=False)

    manifest = {
        "schema": 1,
        "phase": "r15-dukascopy-xauusd-boundary-export",
        "status": "PASS",
        "source": "Dukascopy XAUUSD BID M1 public historical feed",
        "url_pattern": f"{BASE}/YYYY/MM0/DD/{FILE_NAME}",
        "window": {"start": START.isoformat(), "end_exclusive": END_EXCLUSIVE.isoformat()},
        "requested_weekdays": total,
        "eligible_boundary_days": int(len(df)),
        "missing_or_holiday_weekdays": int(len(missing_dates)),
        "boundary_csv": str(csv_path),
        "boundary_csv_sha256": sha256(csv_path),
        "payload_provenance_csv": str(prov_path),
        "payload_provenance_csv_sha256": sha256(prov_path),
        "protected_2026_opened": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = out_dir / "r15_dukascopy_market_manifest.json"
    atomic_json(manifest_path, manifest)
    progress(prog, total, total, "complete", {"status": "PASS", "eligible_boundary_days": int(len(df)), "protected_2026_opened": False})
    print(json.dumps({
        "status": "PASS",
        "eligible_boundary_days": int(len(df)),
        "missing_or_holiday_weekdays": int(len(missing_dates)),
        "boundary_csv": str(csv_path),
        "manifest": str(manifest_path),
        "protected_2026_opened": False,
    }))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
