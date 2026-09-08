#!/usr/bin/env python3
"""Build Binance spot + USD-M futures 5m order-flow context for Phase F-A.

Downloads monthly public Binance archives for BTCUSDT/ETHUSDT, 2024-2025 only.
Uses closed 5m bars and derives taker-buy imbalance, volume/trade-count ratios,
and spot-perp basis. No 2026 data and no rule search.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://data.binance.vision/data"
STEP_MS = 300000
START_MS = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
END_MS = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
EXPECTED_ROWS = 210528


def normalize_ts(raw: str) -> int:
    v = int(raw)
    if v >= 100_000_000_000_000:  # Binance spot switched to microseconds in 2025.
        v //= 1000
    return v


def download_verified(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    checksum_url = url + ".CHECKSUM"
    with urllib.request.urlopen(checksum_url, timeout=60) as r:
        checksum_text = r.read().decode("utf-8").strip()
    expected = checksum_text.split()[0].lower()
    if path.exists():
        actual = hashlib.sha256(path.read_bytes()).hexdigest().lower()
        if actual == expected:
            return
    with urllib.request.urlopen(url, timeout=120) as r:
        data = r.read()
    actual = hashlib.sha256(data).hexdigest().lower()
    if actual != expected:
        raise RuntimeError(f"checksum mismatch for {url}: {actual} != {expected}")
    path.write_bytes(data)


def monthly_urls(market: str, symbol: str):
    prefix = "spot" if market == "spot" else "futures/um"
    for year in (2024, 2025):
        for month in range(1, 13):
            name = f"{symbol}-5m-{year}-{month:02d}.zip"
            yield f"{BASE}/{prefix}/monthly/klines/{symbol}/5m/{name}", name


def parse_zip(path: Path) -> dict[int, dict[str, float]]:
    out: dict[int, dict[str, float]] = {}
    with zipfile.ZipFile(path, "r") as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise RuntimeError(f"expected one CSV in {path}, found {len(names)}")
        raw = zf.read(names[0]).decode("utf-8")
    reader = csv.reader(io.StringIO(raw))
    for row in reader:
        if not row or not row[0] or not row[0][0].isdigit():
            continue
        if len(row) < 11:
            raise RuntimeError(f"unexpected kline width in {path}: {len(row)}")
        ts = normalize_ts(row[0])
        if not (START_MS <= ts < END_MS):
            continue
        close = float(row[4])
        quote_vol = float(row[7])
        trades = float(row[8])
        taker_buy_quote = float(row[10])
        imbalance = 0.0 if quote_vol <= 0 else (2.0 * taker_buy_quote / quote_vol - 1.0)
        out[ts] = {
            "close": close,
            "quote_volume": quote_vol,
            "trade_count": trades,
            "taker_buy_quote": taker_buy_quote,
            "taker_imbalance": imbalance,
        }
    return out


def load_market(raw_dir: Path, market: str, symbol: str) -> dict[int, dict[str, float]]:
    rows: dict[int, dict[str, float]] = {}
    for url, name in monthly_urls(market, symbol):
        path = raw_dir / market / symbol / name
        download_verified(url, path)
        part = parse_zip(path)
        overlap = set(rows).intersection(part)
        if overlap:
            raise RuntimeError(f"duplicate timestamps across archives for {market} {symbol}: {len(overlap)}")
        rows.update(part)
        print(f"{market} {symbol}: {name} cumulative_rows={len(rows)}")
    return rows


def lag_value(rows: list[dict], i: int, field: str, bars: int):
    j = i - bars
    if j < 0:
        return None
    if rows[i]["timestamp_ms"] - rows[j]["timestamp_ms"] != bars * STEP_MS:
        return None
    return rows[j].get(field)


def add_changes(rows: list[dict]) -> None:
    fields = [
        "spot_taker_imbalance",
        "perp_taker_imbalance",
        "taker_imbalance_diff",
        "perp_spot_basis_bps",
        "log_quote_volume_ratio",
        "log_trade_count_ratio",
    ]
    for i, row in enumerate(rows):
        for bars, tag in ((3, "15m"), (12, "1h")):
            for field in fields:
                old = lag_value(rows, i, field, bars)
                cur = row.get(field)
                row[f"{field}_change_{tag}"] = "" if old is None or cur is None else repr(cur - old)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\binance_orderflow_v1")
    args = ap.parse_args()
    out_dir = Path(args.output_dir)
    raw_dir = out_dir / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema": 1,
        "phase": "F-A",
        "start": "2024-01-01",
        "end_exclusive": "2026-01-01",
        "protected_2026_untouched": True,
        "symbols": {},
    }

    for symbol in ("BTCUSDT", "ETHUSDT"):
        spot = load_market(raw_dir, "spot", symbol)
        perp = load_market(raw_dir, "um", symbol)
        if len(spot) != EXPECTED_ROWS or len(perp) != EXPECTED_ROWS:
            raise RuntimeError(f"{symbol}: expected {EXPECTED_ROWS} spot/perp rows, got spot={len(spot)} perp={len(perp)}")
        timestamps = list(range(START_MS, END_MS, STEP_MS))
        rows = []
        for ts in timestamps:
            s = spot.get(ts)
            p = perp.get(ts)
            if s is None or p is None:
                raise RuntimeError(f"{symbol}: missing aligned row at {ts}")
            basis = (p["close"] / s["close"] - 1.0) * 10000.0 if s["close"] else 0.0
            qratio = math.log((p["quote_volume"] + 1e-12) / (s["quote_volume"] + 1e-12))
            tratio = math.log((p["trade_count"] + 1.0) / (s["trade_count"] + 1.0))
            rows.append({
                "timestamp_ms": ts,
                "timestamp_utc": datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat(),
                "feature_available_at_ms": ts + STEP_MS,
                "spot_close": repr(s["close"]),
                "spot_quote_volume": repr(s["quote_volume"]),
                "spot_trade_count": repr(s["trade_count"]),
                "spot_taker_buy_quote": repr(s["taker_buy_quote"]),
                "spot_taker_imbalance": s["taker_imbalance"],
                "perp_close": repr(p["close"]),
                "perp_quote_volume": repr(p["quote_volume"]),
                "perp_trade_count": repr(p["trade_count"]),
                "perp_taker_buy_quote": repr(p["taker_buy_quote"]),
                "perp_taker_imbalance": p["taker_imbalance"],
                "taker_imbalance_diff": p["taker_imbalance"] - s["taker_imbalance"],
                "perp_spot_basis_bps": basis,
                "log_quote_volume_ratio": qratio,
                "log_trade_count_ratio": tratio,
            })
        add_changes(rows)
        path = out_dir / f"{symbol}_binance_spot_um_5m_orderflow_2024-01-01_2026-01-01.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        manifest["symbols"][symbol] = {
            "spot_rows": len(spot),
            "perp_rows": len(perp),
            "aligned_rows": len(rows),
            "output_file": str(path),
        }
        print(f"{symbol}: aligned_rows={len(rows)} output={path}")

    mpath = out_dir / "binance_orderflow_manifest_v1.json"
    mpath.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Manifest: {mpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
