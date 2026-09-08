#!/usr/bin/env python3
"""Phenomenon Discovery Lab v1.00 — causal 5m feature matrix builder.

Input: aligned Bybit 5m kline + open-interest CSV produced by
`download_bybit_oi_price_v1_00.py`.

Output: one research matrix per symbol. Predictors use CLOSED bars only.
`feature_available_at_ms` is the 5m bar close. `future_*` columns are offline
labels only and must never be fed back as predictors.

Missing 5m intervals are never bridged: indicators reset after a gap and lag /
future labels are left blank when their required window is not contiguous.
This is deliberately not a trading strategy and contains no BUY/SELL rule.
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

FIVE_MIN_MS = 300_000


def f(x: str) -> float:
    return float(x)


def pct(a: float, b: float) -> float | None:
    return None if b == 0 else (a / b - 1.0) * 100.0


def contiguous_segments(ts: list[int]) -> list[tuple[int, int]]:
    if not ts:
        return []
    out: list[tuple[int, int]] = []
    start = 0
    for i in range(1, len(ts)):
        if ts[i] - ts[i - 1] != FIVE_MIN_MS:
            out.append((start, i))
            start = i
    out.append((start, len(ts)))
    return out


def is_contiguous(ts: list[int], start: int, end: int) -> bool:
    """True when inclusive indexes start..end are exact consecutive 5m bars."""
    if start < 0 or end >= len(ts) or end < start:
        return False
    return ts[end] - ts[start] == (end - start) * FIVE_MIN_MS


def rsi_segment(closes: list[float], period: int = 14) -> list[float | None]:
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

    def value(g: float, loss: float) -> float:
        if loss == 0 and g == 0:
            return 50.0
        if loss == 0:
            return 100.0
        return 100.0 - 100.0 / (1.0 + g / loss)

    out[period] = value(avg_gain, avg_loss)
    for i in range(period + 1, len(closes)):
        avg_gain = ((period - 1) * avg_gain + gains[i]) / period
        avg_loss = ((period - 1) * avg_loss + losses[i]) / period
        out[i] = value(avg_gain, avg_loss)
    return out


def atr_segment(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[float | None]:
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


def segmented_indicators(
    ts: list[int], highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> tuple[list[float | None], list[float | None]]:
    atr: list[float | None] = [None] * len(ts)
    rsi: list[float | None] = [None] * len(ts)
    for start, end in contiguous_segments(ts):
        seg_a = atr_segment(highs[start:end], lows[start:end], closes[start:end], period)
        seg_r = rsi_segment(closes[start:end], period)
        atr[start:end] = seg_a
        rsi[start:end] = seg_r
    return atr, rsi


def lag_pct(values: list[float], ts: list[int], i: int, bars: int) -> float | None:
    if i < bars or not is_contiguous(ts, i - bars, i):
        return None
    return pct(values[i], values[i - bars])


def fmt(x: float | None) -> str:
    return "" if x is None or not math.isfinite(x) else f"{x:.10f}"


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
    atr, rsi = segmented_indicators(ts, h, l, c, 14)

    fields = [
        "timestamp_ms", "timestamp_utc", "feature_available_at_ms", "symbol",
        "open", "high", "low", "close", "volume", "open_interest",
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

            atr_prev = atr[i - 1] if i >= 1 and is_contiguous(ts, i - 1, i) else None
            atr_3 = atr[i - 3] if i >= 3 and is_contiguous(ts, i - 3, i) else None
            oi5 = lag_pct(oi, ts, i, 1)
            oi15 = lag_pct(oi, ts, i, 3)
            prev_oi5 = lag_pct(oi, ts, i - 1, 1) if i >= 2 else None
            prev_oi15 = lag_pct(oi, ts, i - 3, 3) if i >= 6 else None

            def future_ret(bars: int) -> float | None:
                if i + bars >= len(c) or not is_contiguous(ts, i, i + bars):
                    return None
                return pct(c[i + bars], c[i])

            def excursions(bars: int) -> tuple[float | None, float | None]:
                if i + bars >= len(c) or not is_contiguous(ts, i, i + bars):
                    return None, None
                mx = max(h[i + 1:i + bars + 1])
                mn = min(l[i + 1:i + bars + 1])
                return (mx - c[i]) / a, (mn - c[i]) / a

            def first_touch(horizon: int) -> tuple[str, int | None]:
                if i + horizon >= len(c) or not is_contiguous(ts, i, i + horizon):
                    return "", None
                up = c[i] + a
                dn = c[i] - a
                for j in range(i + 1, i + horizon + 1):
                    hit_up = h[j] >= up
                    hit_dn = l[j] <= dn
                    if hit_up and hit_dn:
                        return "AMBIGUOUS_SAME_BAR", j - i
                    if hit_up:
                        return "UP", j - i
                    if hit_dn:
                        return "DOWN", j - i
                return "NONE", None

            mfe6, mae6 = excursions(6)
            mfe12, mae12 = excursions(12)
            touch, touchbars = first_touch(12)
            w.writerow({
                "timestamp_ms": ts[i],
                "timestamp_utc": r["timestamp_utc"],
                "feature_available_at_ms": ts[i] + FIVE_MIN_MS,
                "symbol": r["symbol"],
                "open": o[i], "high": h[i], "low": l[i], "close": c[i], "volume": v[i], "open_interest": oi[i],
                "rsi14": fmt(rsi[i]), "atr14": fmt(a),
                "atr_slope_1bar_abs": fmt(None if atr_prev is None else a - atr_prev),
                "atr_slope_1bar_pct": fmt(None if atr_prev in (None, 0) else pct(a, atr_prev)),
                "atr_slope_3bar_pct": fmt(None if atr_3 in (None, 0) else pct(a, atr_3)),
                "price_change_5m_pct": fmt(lag_pct(c, ts, i, 1)),
                "price_change_15m_pct": fmt(lag_pct(c, ts, i, 3)),
                "price_change_1h_pct": fmt(lag_pct(c, ts, i, 12)),
                "oi_change_5m_pct": fmt(oi5),
                "oi_change_15m_pct": fmt(oi15),
                "oi_change_1h_pct": fmt(lag_pct(oi, ts, i, 12)),
                "oi_accel_5m_pctpt": fmt(None if oi5 is None or prev_oi5 is None else oi5 - prev_oi5),
                "oi_accel_15m_pctpt": fmt(None if oi15 is None or prev_oi15 is None else oi15 - prev_oi15),
                "range_atr": fmt((h[i] - l[i]) / a),
                "body_atr": fmt((c[i] - o[i]) / a),
                "future_return_5m_pct": fmt(future_ret(1)),
                "future_return_15m_pct": fmt(future_ret(3)),
                "future_return_30m_pct": fmt(future_ret(6)),
                "future_return_1h_pct": fmt(future_ret(12)),
                "future_mfe_30m_atr": fmt(mfe6),
                "future_mae_30m_atr": fmt(mae6),
                "future_mfe_1h_atr": fmt(mfe12),
                "future_mae_1h_atr": fmt(mae12),
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
