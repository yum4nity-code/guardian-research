#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

BASE_URL = "https://data.binance.vision/data/spot/monthly/klines"
COLS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades", "taker_buy_base",
    "taker_buy_quote", "ignore",
]
PROTECTED_START = pd.Timestamp("2026-01-01", tz="UTC")


def atomic_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    delays = (0.05, 0.10, 0.20, 0.40, 0.80, 1.00)
    for attempt, delay in enumerate(delays):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == len(delays) - 1:
                raise
            time.sleep(delay)


def heartbeat(path: Path | None, completed: int, total: int, stage: str, extra: dict | None = None) -> None:
    if path is None:
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


def months(start: str, end: str) -> list[str]:
    a = pd.Period(start, freq="M")
    b = pd.Period(end, freq="M")
    if b < a:
        raise ValueError("end month before start month")
    return [str(x) for x in pd.period_range(a, b, freq="M")]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, target: Path, retries: int = 4) -> None:
    if target.exists() and target.stat().st_size > 0:
        if zipfile.is_zipfile(target):
            return
        target.unlink()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "guardian-research/1.0"})
    last: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=45) as resp, tmp.open("wb") as out:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
            if tmp.stat().st_size <= 0:
                raise RuntimeError(f"empty download: {url}")
            os.replace(tmp, target)
            return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            if tmp.exists():
                tmp.unlink()
            if attempt + 1 < retries:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"download failed after {retries} attempts: {url}: {last}")


def infer_time(values: pd.Series) -> pd.Series:
    x = pd.to_numeric(values, errors="coerce")
    finite = x.dropna()
    if finite.empty:
        return pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns, UTC]")
    med = float(finite.median())
    if med > 1e14:
        unit = "us"
    elif med > 1e11:
        unit = "ms"
    else:
        unit = "s"
    return pd.to_datetime(x, unit=unit, utc=True, errors="coerce")


def read_month(zip_path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path, "r") as zf:
        members = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if len(members) != 1:
            raise RuntimeError(f"expected one CSV in {zip_path}, found {len(members)}")
        with zf.open(members[0], "r") as raw:
            df = pd.read_csv(raw, header=None, names=COLS, dtype=str)
    # Some archives may contain a header row; numeric coercion drops it safely.
    t = infer_time(df["open_time"])
    out = pd.DataFrame({
        "time": t,
        "open": pd.to_numeric(df["open"], errors="coerce"),
        "high": pd.to_numeric(df["high"], errors="coerce"),
        "low": pd.to_numeric(df["low"], errors="coerce"),
        "close": pd.to_numeric(df["close"], errors="coerce"),
        "volume": pd.to_numeric(df["volume"], errors="coerce"),
        "quote_volume": pd.to_numeric(df["quote_volume"], errors="coerce"),
        "trades": pd.to_numeric(df["trades"], errors="coerce"),
        "taker_buy_base": pd.to_numeric(df["taker_buy_base"], errors="coerce"),
        "taker_buy_quote": pd.to_numeric(df["taker_buy_quote"], errors="coerce"),
    })
    out = out.dropna(subset=["time", "open", "high", "low", "close"])
    out = out.sort_values("time").drop_duplicates("time")
    if (out["time"] >= PROTECTED_START).any():
        raise RuntimeError(f"protected 2026 row present in {zip_path}")
    return out


def validate_symbol(df: pd.DataFrame, symbol: str) -> dict:
    if df.empty:
        raise RuntimeError(f"{symbol}: no rows")
    df = df.sort_values("time").drop_duplicates("time").reset_index(drop=True)
    if not df["time"].is_monotonic_increasing:
        raise RuntimeError(f"{symbol}: non-monotonic time")
    if (df["time"] >= PROTECTED_START).any():
        raise RuntimeError(f"{symbol}: protected 2026 row present")
    d = df["time"].diff().dropna()
    expected = pd.Timedelta(minutes=5)
    gap_count = int((d != expected).sum())
    duplicate_count = int(df["time"].duplicated().sum())
    first = df["time"].iloc[0]
    last = df["time"].iloc[-1]
    if first > pd.Timestamp("2017-08-31 23:59:59", tz="UTC"):
        raise RuntimeError(f"{symbol}: history starts too late: {first}")
    if last < pd.Timestamp("2025-12-31 23:50:00", tz="UTC"):
        raise RuntimeError(f"{symbol}: history ends too early: {last}")
    return {
        "symbol": symbol,
        "rows": int(len(df)),
        "first_time": first.isoformat(),
        "last_time": last.isoformat(),
        "gap_count_non_5m": gap_count,
        "duplicate_count": duplicate_count,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"])
    ap.add_argument("--interval", default="5m")
    ap.add_argument("--start-month", default="2017-08")
    ap.add_argument("--end-month", default="2025-12")
    ap.add_argument("--progress-file")
    args = ap.parse_args()

    if args.interval != "5m":
        raise ValueError("R7 v1.00 is preregistered for 5m only")
    if sorted(args.symbols) != ["BTCUSDT", "ETHUSDT"]:
        raise ValueError("R7 v1.00 is preregistered for BTCUSDT and ETHUSDT only")
    if args.start_month != "2017-08" or args.end_month != "2025-12":
        raise ValueError("R7 v1.00 data window is frozen at 2017-08 through 2025-12")
    if pd.Period(args.end_month, freq="M") >= pd.Period("2026-01", freq="M"):
        raise ValueError("2026 download is forbidden")

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(out)
    required_free_bytes = 5 * 1024 ** 3
    estimated_upper_bound_bytes = 1 * 1024 ** 3
    if usage.free < required_free_bytes:
        raise RuntimeError(f"insufficient free space on target volume: free={usage.free}, required={required_free_bytes}")
    progress = Path(args.progress_file) if args.progress_file else None
    month_list = months(args.start_month, args.end_month)
    total = len(month_list) * len(args.symbols)
    done = 0
    manifest = {
        "schema": 1,
        "phase": "r7-long-history-data",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Binance Data Vision spot monthly klines",
        "interval": args.interval,
        "start_month": args.start_month,
        "end_month": args.end_month,
        "protected_2026_opened": False,
        "storage": {
            "target": str(out),
            "free_bytes_before": int(usage.free),
            "estimated_upper_bound_bytes": int(estimated_upper_bound_bytes),
            "required_free_bytes": int(required_free_bytes)
        },
        "symbols": {},
    }

    for symbol in args.symbols:
        raw_dir = out / "raw" / symbol
        frames: list[pd.DataFrame] = []
        files = []
        for ym in month_list:
            name = f"{symbol}-{args.interval}-{ym}.zip"
            url = f"{BASE_URL}/{symbol}/{args.interval}/{name}"
            target = raw_dir / name
            heartbeat(progress, done, total, "download", {"symbol": symbol, "month": ym})
            download(url, target)
            sha = sha256_file(target)
            frame = read_month(target)
            if frame.empty:
                raise RuntimeError(f"{symbol} {ym}: empty archive after parse")
            frames.append(frame)
            files.append({"month": ym, "path": str(target), "bytes": target.stat().st_size, "sha256": sha, "rows": int(len(frame))})
            done += 1

        df = pd.concat(frames, ignore_index=True)
        df = df.sort_values("time").drop_duplicates("time").reset_index(drop=True)
        summary = validate_symbol(df, symbol)
        csv_path = out / f"{symbol}_spot_5m_2017_2025.csv"
        df.to_csv(csv_path, index=False, date_format="%Y-%m-%dT%H:%M:%S.%fZ")
        summary["consolidated_path"] = str(csv_path)
        summary["consolidated_bytes"] = csv_path.stat().st_size
        summary["consolidated_sha256"] = sha256_file(csv_path)
        summary["archives"] = files
        manifest["symbols"][symbol] = summary

    manifest["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    manifest_path = out / "r7_long_history_data_manifest.json"
    atomic_json(manifest_path, manifest)
    heartbeat(progress, total, total, "complete", {"manifest": str(manifest_path)})
    print(json.dumps({
        "status": "PASS",
        "symbols": {k: {"rows": v["rows"], "first_time": v["first_time"], "last_time": v["last_time"], "gaps": v["gap_count_non_5m"]} for k, v in manifest["symbols"].items()},
        "manifest": str(manifest_path),
        "protected_2026_opened": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
