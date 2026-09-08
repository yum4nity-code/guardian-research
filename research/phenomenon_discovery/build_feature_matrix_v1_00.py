#!/usr/bin/env python3
"""Phenomenon Discovery Lab v1.00 — causal 5m feature matrix builder.

Input: aligned Bybit 5m kline + open-interest CSV produced by
`download_bybit_oi_price_v1_00.py`.

Output: one research matrix per symbol. Features use current/previous CLOSED
bars only. Future columns are labels for offline discovery and must never be
fed back as features.

This is deliberately not a trading strategy and contains no BUY/SELL rule.
"""
from __future__ import annotations

import argparse
import csv
import math
from collections import deque
from pathlib import Path
from typing import Iterable


def f(x: str) -> float:
    return float(x)


def pct(a: float, b: float) -> float | None:
    return None if b == 0 else (a / b - 1.0) * 100.0


def wilder_rsi(closes: list[float], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains = [0.0] * len(closes)
    losses = [0.0] * len(closes)
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains[i] = max(d, 0.0)
        losses[i] = max(-d, 0.0)
    avg_gain = sum(gains[1:period + 1]) / period
    avg_loss = sum(losses[1:period + 1]) / period
    out[period] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    for i in range(period + 1, len(closes)):
        avg_gain = ((period - 1) * avg_gain + gains[i]) / period
        avg_loss = ((period - 1) * avg_loss + losses[i]) / period
        out[i] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return out


def wilder_atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return out
    tr = [0.0] * len(closes)
    tr[0] = highs[0] - lows[0]
    for i in range(1, len(closes)):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
    atr = sum(tr[1:period + 1]) / period
    out[period] = atr
    for i in range(period + 1, len(closes)):
        atr = ((period - 1) * atr + tr[i]) / period
        out[i] = atr
    return out


def lag_pct(values: list[float], i: int, bars: int) -> float | None:
    return None if i < bars else pct(values[i], values[i - bars])


def fmt(x: float | None) -> str:
    return "" if x is None or not math.isfinite(x) else f"{x:.10f}"


def first_touch(highs: list[float], lows: list[float], entry: float, atr: float, i: int, horizon: int) -> tuple[str, int | None]:
    up = entry + atr
    dn = entry - atr
    for j in range(i + 1, min(len(highs), i + horizon + 1)):
        hit_up = highs[j] >= up
        hit_dn = lows[j] <= dn
        if hit_up and hit_dn:
            return "AMBIGUOUS_SAME_BAR", j - i
        if hit_up:
            return "UP", j - i
        if hit_dn:
            return "DOWN", j - i
    return "NONE", None


def load(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as fobj:
        return list(csv.DictReader(fobj))


def build(path: Path, output: Path) -> None:
    rows = load(path)
    if len(rows) < 200:
        raise RuntimeError(f"Too few rows: {len(rows)}")
    ts = [int(r["timestamp_ms"]) for r in rows]
    o = [f(r["open"]) for r in rows]
    h = [f(r["high"]) for r in rows]
    l = [f(r["low"]) for r in rows]
    c = [f(r["close"]) for r in rows]
    v = [f(r["volume"]) for r in rows]
    oi = [f(r["open_interest"]) for r in rows]
    atr = wilder_atr(h, l, c, 14)
    rsi = wilder_rsi(c, 14)

    fields = [
        "timestamp_ms", "timestamp_utc", "symbol", "open", "high", "low", "close", "volume", "open_interest",
        "rsi14", "atr14",
        "atr_slope_1bar_abs", "atr_slope_1bar_pct", "atr_slope_3bar_pct",
        "price_change_5m_pct", "price_change_15m_pct", "price_change_1h_pct",
        "oi_change_5m_pct", "oi_change_15m_pct", "oi_change_1h_pct",
        "oi_accel_5m_pctpt", "oi_accel_15m_pctpt",
        "range_atr", "body_atr",
        "future_return_5m_pct", "future_return_15m_pct", "future_return_30m_pct", "future_return_1h_pct",
        "future_mfe_30m_atr", "future_mae_30m_atr", "future_mfe_1h_atr", "future_mae_1h_atr",
        "future_first_touch_1atr_1h", "future_first_touch_bars_1atr_1h",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as fo:
        w = csv.DictWriter(fo, fieldnames=fields)
        w.writeheader()
        for i, r in enumerate(rows):
            a = atr[i]
            if a is None or a <= 0:
                continue
            atr_prev = atr[i - 1] if i >= 1 else None
            atr_3 = atr[i - 3] if i >= 3 else None
            oi5 = lag_pct(oi, i, 1)
            oi15 = lag_pct(oi, i, 3)
            prev_oi5 = lag_pct(oi, i - 1, 1) if i >= 2 else None
            prev_oi15 = lag_pct(oi, i - 3, 3) if i >= 6 else None

            def future_ret(bars: int) -> float | None:
                return pct(c[i + bars], c[i]) if i + bars < len(c) else None

            def excursions(bars: int) -> tuple[float | None, float | None]:
                end = min(len(c), i + bars + 1)
                if end <= i + 1:
                    return None, None
                mx = max(h[i + 1:end])
                mn = min(l[i + 1:end])
                return (mx - c[i]) / a, (mn - c[i]) / a

            mfe6, mae6 = excursions(6)
            mfe12, mae12 = excursions(12)
            touch, touchbars = first_touch(h, l, c[i], a, i, 12)
            w.writerow({
                "timestamp_ms": ts[i], "timestamp_utc": r["timestamp_utc"], "symbol": r["symbol"],
                "open": o[i], "high": h[i], "low": l[i], "close": c[i], "volume": v[i], "open_interest": oi[i],
                "rsi14": fmt(rsi[i]), "atr14": fmt(a),
                "atr_slope_1bar_abs": fmt(None if atr_prev is None else a - atr_prev),
                "atr_slope_1bar_pct": fmt(None if atr_prev in (None, 0) else pct(a, atr_prev)),
                "atr_slope_3bar_pct": fmt(None if atr_3 in (None, 0) else pct(a, atr_3)),
                "price_change_5m_pct": fmt(lag_pct(c, i, 1)),
                "price_change_15m_pct": fmt(lag_pct(c, i, 3)),
                "price_change_1h_pct": fmt(lag_pct(c, i, 12)),
                "oi_change_5m_pct": fmt(oi5), "oi_change_15m_pct": fmt(oi15), "oi_change_1h_pct": fmt(lag_pct(oi, i, 12)),
                "oi_accel_5m_pctpt": fmt(None if oi5 is None or prev_oi5 is None else oi5 - prev_oi5),
                "oi_accel_15m_pctpt": fmt(None if oi15 is None or prev_oi15 is None else oi15 - prev_oi15),
                "range_atr": fmt((h[i] - l[i]) / a), "body_atr": fmt((c[i] - o[i]) / a),
                "future_return_5m_pct": fmt(future_ret(1)), "future_return_15m_pct": fmt(future_ret(3)),
                "future_return_30m_pct": fmt(future_ret(6)), "future_return_1h_pct": fmt(future_ret(12)),
                "future_mfe_30m_atr": fmt(mfe6), "future_mae_30m_atr": fmt(mae6),
                "future_mfe_1h_atr": fmt(mfe12), "future_mae_1h_atr": fmt(mae12),
                "future_first_touch_1atr_1h": touch,
                "future_first_touch_bars_1atr_1h": "" if touchbars is None else touchbars,
            })
    print(f"Built {output}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\historical_v1")
    ap.add_argument("--output-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1")
    args = ap.parse_args()
    inp = Path(args.input_dir)
    out = Path(args.output_dir)
    files = sorted(inp.glob("*_bybit_5m_oi_price_*.csv"))
    if not files:
        raise SystemExit(f"No downloader CSV found in {inp}")
    for p in files:
        build(p, out / (p.stem + "_features_v1.csv"))
    print("Feature matrix complete. Future_* columns are labels only; never use them as predictors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
