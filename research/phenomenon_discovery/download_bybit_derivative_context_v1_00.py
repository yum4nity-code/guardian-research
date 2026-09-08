#!/usr/bin/env python3
"""Download causal Bybit derivative context for Phenomenon Discovery Phase E-A.

Discovery window defaults to 2024-01-01 through 2026-01-01 exclusive.
2026 is not downloaded. Public read-only Bybit V5 endpoints only.

Downloads 5m mark/index/premium-index klines and settled funding history for
BTCUSDT/ETHUSDT. Funding includes a short pre-window seed so the last funding
known at the first 2024 bar can be reconstructed causally.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = "https://api.bybit.com"
INTERVAL_MS = 5 * 60 * 1000


def ms(text: str) -> int:
    return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp() * 1000)


def iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()


def get(path: str, params: dict[str, object], tries: int = 6) -> dict:
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GuardianResearch/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                obj = json.loads(r.read().decode("utf-8"))
            if obj.get("retCode") != 0:
                raise RuntimeError(f"Bybit retCode={obj.get('retCode')} retMsg={obj.get('retMsg')}")
            return obj
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt + 1 >= tries:
                break
            time.sleep(min(8.0, 0.75 * (2 ** attempt)))
    raise RuntimeError(f"GET failed: {url}: {last}")


def download_kline(path: str, symbol: str, start_ms: int, end_ms: int) -> dict[int, float]:
    rows: dict[int, float] = {}
    cursor_end = end_ms - 1
    pages = 0
    while cursor_end >= start_ms:
        obj = get(path, {
            "category": "linear",
            "symbol": symbol,
            "interval": "5",
            "start": start_ms,
            "end": cursor_end,
            "limit": 1000,
        })
        data = obj.get("result", {}).get("list", [])
        if not data:
            break
        pages += 1
        oldest = None
        for item in data:
            ts = int(item[0])
            if start_ms <= ts < end_ms:
                rows[ts] = float(item[4])
            oldest = ts if oldest is None else min(oldest, ts)
        if pages % 25 == 0:
            print(f"[{symbol}] {path} pages={pages} rows={len(rows)} oldest={iso(oldest)}")
        if oldest is None or oldest <= start_ms:
            break
        cursor_end = oldest - 1
        time.sleep(0.02)
    return rows


def download_funding(symbol: str, start_ms: int, end_ms: int) -> list[tuple[int, float]]:
    # Bybit funding history supports startTime/endTime and max 200 records.
    # Walk backwards using endTime; seed starts before discovery window.
    rows: dict[int, float] = {}
    cursor_end = end_ms - 1
    pages = 0
    while cursor_end >= start_ms:
        obj = get("/v5/market/funding/history", {
            "category": "linear",
            "symbol": symbol,
            "endTime": cursor_end,
            "limit": 200,
        })
        data = obj.get("result", {}).get("list", [])
        if not data:
            break
        pages += 1
        oldest = None
        for item in data:
            ts = int(item["fundingRateTimestamp"])
            if start_ms <= ts < end_ms:
                rows[ts] = float(item["fundingRate"])
            oldest = ts if oldest is None else min(oldest, ts)
        if pages % 10 == 0:
            print(f"[{symbol}] funding pages={pages} rows={len(rows)} oldest={iso(oldest)}")
        if oldest is None or oldest <= start_ms:
            break
        cursor_end = oldest - 1
        time.sleep(0.02)
    return sorted(rows.items())


def write_context(path: Path, mark: dict[int, float], index: dict[int, float], premium: dict[int, float], start_ms: int, end_ms: int) -> dict:
    timestamps = list(range(start_ms, end_ms, INTERVAL_MS))
    path.parent.mkdir(parents=True, exist_ok=True)
    missing = {"mark": 0, "index": 0, "premium": 0}
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp_ms", "timestamp_utc", "mark_close", "index_close", "premium_index_close", "mark_index_bps"])
        for ts in timestamps:
            m = mark.get(ts)
            i = index.get(ts)
            p = premium.get(ts)
            if m is None:
                missing["mark"] += 1
            if i is None:
                missing["index"] += 1
            if p is None:
                missing["premium"] += 1
            mib = "" if m is None or i is None or i == 0 else (m / i - 1.0) * 10000.0
            w.writerow([ts, iso(ts), "" if m is None else repr(m), "" if i is None else repr(i), "" if p is None else repr(p), "" if mib == "" else repr(mib)])
    return {"rows": len(timestamps), "missing": missing}


def write_funding(path: Path, rows: list[tuple[int, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["funding_timestamp_ms", "funding_timestamp_utc", "funding_rate"])
        for ts, rate in rows:
            w.writerow([ts, iso(ts), repr(rate)])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default="2026-01-01")
    ap.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"])
    ap.add_argument("--output-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\derivative_context_v1")
    args = ap.parse_args()

    start_ms = ms(args.start)
    end_ms = ms(args.end)
    if end_ms > ms("2026-01-01"):
        raise RuntimeError("Phase E-A guard: do not download 2026 or later.")
    funding_seed_ms = start_ms - int(timedelta(days=2).total_seconds() * 1000)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": 1, "start": args.start, "end_exclusive": args.end, "symbols": {}, "funding_seed_start_utc": iso(funding_seed_ms)}

    for symbol in args.symbols:
        print(f"\n=== {symbol}: mark price 5m ===")
        mark = download_kline("/v5/market/mark-price-kline", symbol, start_ms, end_ms)
        print(f"[{symbol}] mark={len(mark)}")
        print(f"=== {symbol}: index price 5m ===")
        index = download_kline("/v5/market/index-price-kline", symbol, start_ms, end_ms)
        print(f"[{symbol}] index={len(index)}")
        print(f"=== {symbol}: premium index 5m ===")
        premium = download_kline("/v5/market/premium-index-price-kline", symbol, start_ms, end_ms)
        print(f"[{symbol}] premium={len(premium)}")
        print(f"=== {symbol}: settled funding history ===")
        funding = download_funding(symbol, funding_seed_ms, end_ms)
        print(f"[{symbol}] funding={len(funding)}")

        context_path = out / f"{symbol}_bybit_derivative_5m_{args.start}_{args.end}.csv"
        funding_path = out / f"{symbol}_bybit_funding_{args.start}_{args.end}.csv"
        stats = write_context(context_path, mark, index, premium, start_ms, end_ms)
        write_funding(funding_path, funding)
        manifest["symbols"][symbol] = {
            **stats,
            "mark_rows_downloaded": len(mark),
            "index_rows_downloaded": len(index),
            "premium_rows_downloaded": len(premium),
            "funding_rows_downloaded_including_seed": len(funding),
            "context_file": str(context_path),
            "funding_file": str(funding_path),
        }

    manifest_path = out / f"manifest_derivative_{args.start}_{args.end}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
