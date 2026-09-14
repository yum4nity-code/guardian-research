#!/usr/bin/env python3
"""Build canonical XAUUSD BID M5 from the immutable R15 Dukascopy M1 master index.

Scientific invariants:
- source is the R15 PASS master payload index only;
- every .bi5 payload is SHA256-verified before decoding;
- Dukascopy candle records are 24-byte big-endian: seconds, open, close, low, high, volume;
- XAUUSD raw price integers use scale 1000;
- only exact UTC-aligned 5-minute buckets containing 5 contiguous M1 bars are emitted;
- no interpolation / forward fill / synthetic bars;
- any 2026+ source date hard-fails;
- source caches are read-only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import lzma
import math
import os
import struct
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

PRICE_SCALE = 1000.0
PROTECTED_START = date(2026, 1, 1)
REC = struct.Struct(">IIIIIf")  # sec, open, close, low, high, volume


@dataclass(frozen=True)
class M1:
    epoch: int
    open: float
    high: float
    low: float
    close: float


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_index(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    required = {"date", "path", "sha256", "bytes"}
    if not rows:
        raise RuntimeError("empty R15 payload index")
    missing = required - set(rows[0])
    if missing:
        raise RuntimeError(f"payload index missing columns: {sorted(missing)}")
    previous: date | None = None
    for row in rows:
        d = date.fromisoformat(row["date"])
        if d >= PROTECTED_START:
            raise RuntimeError(f"PROTECTED 2026 source encountered: {d}")
        if previous is not None and d <= previous:
            raise RuntimeError(f"non-increasing payload index date: {d} <= {previous}")
        previous = d
    return rows


def decode_day(day: date, payload: Path, expected_sha: str, expected_bytes: int) -> list[M1]:
    if day >= PROTECTED_START:
        raise RuntimeError(f"PROTECTED 2026 payload requested: {day}")
    if not payload.is_file():
        raise RuntimeError(f"payload missing: {payload}")
    if payload.stat().st_size != expected_bytes:
        raise RuntimeError(f"payload byte-size mismatch: {payload}")
    actual_sha = sha256(payload)
    if actual_sha.lower() != expected_sha.lower():
        raise RuntimeError(f"payload SHA256 mismatch: {payload}")

    raw = lzma.decompress(payload.read_bytes())
    if len(raw) % REC.size:
        raise RuntimeError(f"decoded payload not divisible by 24 bytes: {payload}")

    base = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    out: list[M1] = []
    previous_epoch: int | None = None
    for off in range(0, len(raw), REC.size):
        sec, op_raw, cl_raw, lo_raw, hi_raw, vol = REC.unpack_from(raw, off)
        if not 0 <= sec < 86400:
            raise RuntimeError(f"invalid seconds-of-day {sec}: {payload}")
        if sec % 60 != 0:
            raise RuntimeError(f"non-M1-aligned candle at second {sec}: {payload}")
        if min(op_raw, cl_raw, lo_raw, hi_raw) <= 0:
            raise RuntimeError(f"non-positive raw OHLC: {payload}")
        if not math.isfinite(float(vol)):
            raise RuntimeError(f"non-finite volume: {payload}")

        o = op_raw / PRICE_SCALE
        c = cl_raw / PRICE_SCALE
        lo = lo_raw / PRICE_SCALE
        hi = hi_raw / PRICE_SCALE
        if hi < max(o, c) or lo > min(o, c) or hi < lo:
            raise RuntimeError(f"invalid OHLC geometry at {day} + {sec}s")

        epoch = int((base + timedelta(seconds=int(sec))).timestamp())
        if previous_epoch is not None and epoch <= previous_epoch:
            raise RuntimeError(f"non-increasing M1 timestamp in {payload}")
        previous_epoch = epoch
        out.append(M1(epoch, o, hi, lo, c))
    return out


def aggregate_m5(m1: list[M1]) -> tuple[list[tuple[int, float, float, float, float]], int]:
    by_epoch = {b.epoch: b for b in m1}
    emitted: list[tuple[int, float, float, float, float]] = []
    dropped = 0

    if not m1:
        return emitted, dropped

    first = m1[0].epoch - (m1[0].epoch % 300)
    last = m1[-1].epoch - (m1[-1].epoch % 300)
    start = first
    while start <= last:
        xs = [by_epoch.get(start + 60 * k) for k in range(5)]
        present = [x for x in xs if x is not None]
        if len(present) == 5:
            emitted.append((
                start,
                xs[0].open,  # type: ignore[union-attr]
                max(x.high for x in present),
                min(x.low for x in present),
                xs[-1].close,  # type: ignore[union-attr]
            ))
        elif present:
            dropped += 1
        start += 300
    return emitted, dropped


def atomic_replace(tmp: Path, final: Path) -> None:
    final.parent.mkdir(parents=True, exist_ok=True)
    os.replace(tmp, final)


def build(index_csv: Path, output_csv: Path) -> dict:
    rows = parse_index(index_csv)
    tmp = output_csv.with_suffix(output_csv.suffix + ".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)

    total_m1 = total_m5 = dropped_partial = 0
    previous_m5_epoch: int | None = None

    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "timeframe", "server_time", "server_epoch", "open", "high", "low", "close"])
        for n, row in enumerate(rows, 1):
            day = date.fromisoformat(row["date"])
            payload = Path(row["path"])
            m1 = decode_day(day, payload, row["sha256"], int(row["bytes"]))
            m5, dropped = aggregate_m5(m1)
            total_m1 += len(m1)
            dropped_partial += dropped
            for epoch, o, h, lo, c in m5:
                if previous_m5_epoch is not None and epoch <= previous_m5_epoch:
                    raise RuntimeError(f"non-increasing global M5 timestamp: {epoch}")
                previous_m5_epoch = epoch
                dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
                if dt.date() >= PROTECTED_START:
                    raise RuntimeError(f"PROTECTED 2026 M5 emitted: {dt.isoformat()}")
                w.writerow([
                    "XAUUSD", "M5", dt.isoformat(), epoch,
                    f"{o:.3f}", f"{h:.3f}", f"{lo:.3f}", f"{c:.3f}",
                ])
                total_m5 += 1
            if n % 250 == 0:
                print(f"progress days={n}/{len(rows)} m5={total_m5}", flush=True)

    atomic_replace(tmp, output_csv)
    return {
        "status": "PASS",
        "source_days": len(rows),
        "decoded_m1": total_m1,
        "emitted_m5": total_m5,
        "dropped_partial_m5_buckets": dropped_partial,
        "price_scale": PRICE_SCALE,
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
