#!/usr/bin/env python3
"""Phenomenon Discovery Lab v1.00 — historical Bybit OI + 5m price bootstrap.

Research only. Public read-only endpoints. No API key. No trading endpoint.

Downloads, for BTCUSDT and ETHUSDT by default:
- Bybit USDT perpetual 5-minute klines
- Bybit historical open interest at 5-minute granularity

Writes one CSV per symbol plus a manifest. Data are aligned on the 5-minute
bar start timestamp. The downloader is intentionally separate from the live
sniffer: historical exchange data are discovery input; the existing sniffer
remains a later forward/availability-gated validation source.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = "https://api.bybit.com"
FIVE_MIN_MS = 5 * 60 * 1000
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT"]


def utc_ms(text: str) -> int:
    dt = datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def iso_ms(ts: int) -> str:
    return datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat()


def http_json(path: str, params: dict[str, Any], retries: int = 6) -> dict[str, Any]:
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "guardian-phenomenon-discovery/1.00"})
            with urllib.request.urlopen(req, timeout=20) as r:
                payload = json.loads(r.read().decode("utf-8"))
            if int(payload.get("retCode", -1)) != 0:
                raise RuntimeError(f"Bybit retCode={payload.get('retCode')} retMsg={payload.get('retMsg')}")
            return payload
        except Exception as exc:  # noqa: BLE001
            err = exc
            time.sleep(min(8.0, 0.8 * (2 ** attempt)))
    raise RuntimeError(f"Bybit request failed after {retries} attempts: {url}: {err}")


def fetch_klines(symbol: str, start_ms: int, end_ms: int) -> dict[int, dict[str, float]]:
    out: dict[int, dict[str, float]] = {}
    # Kline endpoint returns reverse chronological data. Walk backwards by end.
    cursor_end = end_ms - 1
    pages = 0
    while cursor_end >= start_ms:
        payload = http_json(
            "/v5/market/kline",
            {
                "category": "linear",
                "symbol": symbol,
                "interval": "5",
                "start": start_ms,
                "end": cursor_end,
                "limit": 1000,
            },
        )
        rows = (payload.get("result") or {}).get("list") or []
        if not rows:
            break
        oldest = None
        for row in rows:
            ts = int(row[0])
            if ts < start_ms or ts >= end_ms:
                continue
            out[ts] = {
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
                "turnover": float(row[6]),
            }
            oldest = ts if oldest is None else min(oldest, ts)
        pages += 1
        if oldest is None or oldest <= start_ms:
            break
        cursor_end = oldest - 1
        if pages % 25 == 0:
            print(f"[{symbol}] klines pages={pages} rows={len(out)} oldest={iso_ms(oldest)}")
        time.sleep(0.03)
    return out


def fetch_open_interest(symbol: str, start_ms: int, end_ms: int) -> dict[int, float]:
    out: dict[int, float] = {}
    # Use cursor pagination exactly as documented by Bybit.
    cursor: str | None = None
    pages = 0
    while True:
        params: dict[str, Any] = {
            "category": "linear",
            "symbol": symbol,
            "intervalTime": "5min",
            "startTime": start_ms,
            "endTime": end_ms - 1,
            "limit": 200,
        }
        if cursor:
            params["cursor"] = cursor
        payload = http_json("/v5/market/open-interest", params)
        result = payload.get("result") or {}
        rows = result.get("list") or []
        for row in rows:
            ts = int(row["timestamp"])
            if start_ms <= ts < end_ms:
                out[ts] = float(row["openInterest"])
        pages += 1
        cursor = result.get("nextPageCursor") or None
        if pages % 50 == 0:
            print(f"[{symbol}] OI pages={pages} rows={len(out)}")
        if not cursor or not rows:
            break
        time.sleep(0.03)
    return out


def pct_change(cur: float | None, prev: float | None) -> float | None:
    if cur is None or prev is None or prev == 0:
        return None
    return (cur / prev - 1.0) * 100.0


def write_symbol_csv(path: Path, symbol: str, klines: dict[int, dict[str, float]], oi: dict[int, float]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamps = sorted(set(klines).intersection(oi))
    fields = [
        "timestamp_ms", "timestamp_utc", "symbol",
        "open", "high", "low", "close", "volume", "turnover", "open_interest",
        "oi_change_5m_pct", "price_change_5m_pct",
    ]
    prev_oi = None
    prev_close = None
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for ts in timestamps:
            k = klines[ts]
            cur_oi = oi[ts]
            w.writerow({
                "timestamp_ms": ts,
                "timestamp_utc": iso_ms(ts),
                "symbol": symbol,
                **k,
                "open_interest": cur_oi,
                "oi_change_5m_pct": "" if prev_oi is None else f"{pct_change(cur_oi, prev_oi):.10f}",
                "price_change_5m_pct": "" if prev_close is None else f"{pct_change(k['close'], prev_close):.10f}",
            })
            prev_oi = cur_oi
            prev_close = k["close"]
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "symbol": symbol,
        "kline_rows": len(klines),
        "oi_rows": len(oi),
        "aligned_rows": len(timestamps),
        "coverage_pct_vs_klines": (100.0 * len(timestamps) / len(klines)) if klines else 0.0,
        "first_timestamp_utc": iso_ms(timestamps[0]) if timestamps else None,
        "last_timestamp_utc": iso_ms(timestamps[-1]) if timestamps else None,
        "csv": str(path),
        "sha256": sha,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2024-01-01", help="UTC YYYY-MM-DD")
    ap.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"), help="UTC YYYY-MM-DD, exclusive")
    ap.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS)
    ap.add_argument("--output-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\historical_v1")
    args = ap.parse_args()

    start_ms = utc_ms(args.start)
    end_ms = utc_ms(args.end)
    if end_ms <= start_ms:
        raise SystemExit("--end must be after --start")

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "version": "1.00",
        "source": "Bybit V5 public market API",
        "category": "linear",
        "interval": "5m",
        "start_utc": iso_ms(start_ms),
        "end_utc_exclusive": iso_ms(end_ms),
        "symbols": [],
        "notes": [
            "Historical exchange data are for discovery, not forward validation.",
            "Existing live sniffer remains the availability-gated forward source.",
            "No interpolation or forward fill is performed when OI is missing.",
        ],
    }

    for symbol in [s.upper() for s in args.symbols]:
        print(f"\n=== {symbol}: downloading 5m klines ===")
        klines = fetch_klines(symbol, start_ms, end_ms)
        print(f"[{symbol}] klines={len(klines)}")
        print(f"=== {symbol}: downloading 5m open interest ===")
        oi = fetch_open_interest(symbol, start_ms, end_ms)
        print(f"[{symbol}] OI={len(oi)}")
        csv_path = outdir / f"{symbol}_bybit_5m_oi_price_{args.start}_{args.end}.csv"
        info = write_symbol_csv(csv_path, symbol, klines, oi)
        manifest["symbols"].append(info)
        print(f"[{symbol}] aligned={info['aligned_rows']} coverage={info['coverage_pct_vs_klines']:.2f}% -> {csv_path}")

    manifest_path = outdir / f"manifest_{args.start}_{args.end}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nManifest: {manifest_path}")

    bad = [x for x in manifest["symbols"] if x["aligned_rows"] < 1000]
    if bad:
        print("WARNING: one or more symbols have <1000 aligned rows; inspect coverage before analysis.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
