#!/usr/bin/env python3
"""Preregistered XAUUSD phenomenon batch R16-R20.

Stdlib-only event extraction and descriptive statistics.
The module intentionally does not optimize trading P&L.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo

PROTECTED_YEAR = 2026
PRE_OOS_YEAR = 2025
ALLOWED_TIMEFRAMES = {"M1": 60, "M5": 300}
POST_HORIZONS_M5 = (1, 2, 4, 8, 16)
SHOCK_THRESHOLDS = (2.0, 2.5, 3.0)
ROUND_STEPS = (10.0, 25.0, 50.0, 100.0)

# Session definitions are local-market clocks and DST-aware.
# They can be changed only by versioning/preregistration, not after seeing results.
LONDON_TZ = ZoneInfo("Europe/London")
NEW_YORK_TZ = ZoneInfo("America/New_York")
ASIA_START_MINUTE_LONDON = 0
ASIA_END_MINUTE_LONDON = 7 * 60
LONDON_START_MINUTE = 8 * 60
LONDON_END_MINUTE = 12 * 60
NY_START_MINUTE = 8 * 60 + 20
NY_END_MINUTE = 12 * 60
COMEX_OPEN_MINUTE_NY = 8 * 60 + 20


@dataclass(frozen=True)
class Bar:
    epoch: int
    dt: datetime
    timeframe: str
    open: float
    high: float
    low: float
    close: float

    @property
    def day(self) -> str:
        return self.dt.date().isoformat()

    def local_minute(self, tz: ZoneInfo) -> int:
        local = self.dt.astimezone(tz)
        return local.hour * 60 + local.minute

    def local_day(self, tz: ZoneInfo) -> str:
        return self.dt.astimezone(tz).date().isoformat()


def _finite(x: float) -> bool:
    return math.isfinite(x)


def _parse_dt(server_time: str, epoch: int) -> datetime:
    # Epoch is canonical because the existing XAU export records it and the
    # integrity gate checks strict monotonicity.
    return datetime.fromtimestamp(epoch, tz=timezone.utc)


def load_bars(path: Path, *, stage: str) -> list[Bar]:
    if stage not in {"discovery", "confirmation", "preoos"}:
        raise ValueError(f"unsupported stage: {stage}")
    bars: list[Bar] = []
    previous_epoch: int | None = None
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"timeframe", "server_time", "server_epoch", "open", "high", "low", "close"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise RuntimeError(f"missing columns: {sorted(missing)}")
        for r in reader:
            epoch = int(r["server_epoch"])
            if previous_epoch is not None and epoch <= previous_epoch:
                raise RuntimeError(f"non-increasing timestamp: {epoch} <= {previous_epoch}")
            previous_epoch = epoch
            dt = _parse_dt(r["server_time"], epoch)
            year = dt.year
            if year >= PROTECTED_YEAR:
                raise RuntimeError(f"PROTECTED {PROTECTED_YEAR} row encountered at {dt.isoformat()}")
            if stage != "preoos" and year >= PRE_OOS_YEAR:
                continue
            if stage == "preoos" and year != PRE_OOS_YEAR:
                continue
            tf = r["timeframe"].strip().upper()
            if tf not in ALLOWED_TIMEFRAMES:
                raise RuntimeError(f"unsupported timeframe {tf}")
            o, h, l, c = map(float, (r["open"], r["high"], r["low"], r["close"]))
            if not all(_finite(x) and x > 0 for x in (o, h, l, c)):
                raise RuntimeError(f"invalid OHLC at {dt.isoformat()}")
            if h < max(o, c) or l > min(o, c) or h < l:
                raise RuntimeError(f"invalid OHLC geometry at {dt.isoformat()}")
            bars.append(Bar(epoch, dt, tf, o, h, l, c))
    if not bars:
        raise RuntimeError(f"no usable rows for stage={stage}")
    return bars


def forward_return(bars: Sequence[Bar], i: int, horizon: int) -> float | None:
    j = i + horizon
    if j >= len(bars):
        return None
    step = ALLOWED_TIMEFRAMES[bars[i].timeframe]
    if bars[j].epoch - bars[i].epoch != step * horizon:
        return None
    return bars[j].close / bars[i].close - 1.0


def signed_stats(values: Iterable[float]) -> dict:
    xs = [float(x) for x in values if _finite(float(x))]
    n = len(xs)
    if not n:
        return {"n": 0, "mean": None, "median": None, "t": None, "positive_fraction": None}
    mean = statistics.fmean(xs)
    med = statistics.median(xs)
    pos = sum(x > 0 for x in xs) / n
    if n >= 2:
        sd = statistics.stdev(xs)
        t = mean / (sd / math.sqrt(n)) if sd > 0 else None
    else:
        t = None
    return {"n": n, "mean": mean, "median": med, "t": t, "positive_fraction": pos}


def yearly_stability(events: Sequence[dict], metric: str) -> dict:
    by_year: dict[int, list[float]] = defaultdict(list)
    for e in events:
        v = e.get(metric)
        if isinstance(v, (int, float)) and _finite(float(v)):
            by_year[int(e["year"])].append(float(v))
    years = {str(y): signed_stats(xs) for y, xs in sorted(by_year.items())}
    signs = [1 if s["mean"] and s["mean"] > 0 else -1 if s["mean"] and s["mean"] < 0 else 0
             for s in years.values()]
    nonzero = [s for s in signs if s]
    return {
        "years": years,
        "positive_years": sum(s > 0 for s in nonzero),
        "negative_years": sum(s < 0 for s in nonzero),
        "sign_consistency": (max(sum(s > 0 for s in nonzero), sum(s < 0 for s in nonzero)) / len(nonzero))
        if nonzero else None,
    }


def _same_day_indices(bars: Sequence[Bar]) -> dict[str, list[int]]:
    out: dict[str, list[int]] = defaultdict(list)
    for i, b in enumerate(bars):
        out[b.day].append(i)
    return out


def r16_asian_london(bars: Sequence[Bar], reentry_bars: int = 3) -> list[dict]:
    events: list[dict] = []
    by_london_day: dict[str, list[int]] = defaultdict(list)
    for i, b in enumerate(bars):
        by_london_day[b.local_day(LONDON_TZ)].append(i)
    for day, idxs in by_london_day.items():
        asia = [i for i in idxs if ASIA_START_MINUTE_LONDON <= bars[i].local_minute(LONDON_TZ) < ASIA_END_MINUTE_LONDON]
        london = [i for i in idxs if LONDON_START_MINUTE <= bars[i].local_minute(LONDON_TZ) < LONDON_END_MINUTE]
        if not asia or not london:
            continue
        hi = max(bars[i].high for i in asia)
        lo = min(bars[i].low for i in asia)
        if hi <= lo:
            continue
        for i in london:
            b = bars[i]
            direction = 1 if b.close > hi else -1 if b.close < lo else 0
            if not direction:
                continue
            reentered = False
            for k in range(1, reentry_bars + 1):
                j = i + k
                if j >= len(bars) or bars[j].local_day(LONDON_TZ) != day:
                    break
                if lo <= bars[j].close <= hi:
                    reentered = True
                    break
            event = {
                "research": "R16",
                "epoch": b.epoch, "year": b.dt.year, "day_london": day,
                "direction": direction, "asian_high": hi, "asian_low": lo,
                "asian_range": hi - lo, "break_close": b.close,
                "break_displacement_range": ((b.close - hi) if direction > 0 else (lo - b.close)) / (hi - lo),
                "reentered_within_bars": reentered,
            }
            for h in POST_HORIZONS_M5:
                r = forward_return(bars, i, h)
                event[f"fwd_{h}b"] = r
                event[f"continuation_{h}b"] = (direction * r) if r is not None else None
                event[f"reversal_{h}b"] = (-direction * r) if (r is not None and reentered) else None
            events.append(event)
            break
    return events


def r17_comex_open(bars: Sequence[Bar]) -> list[dict]:
    by_ny_day: dict[str, list[int]] = defaultdict(list)
    for i, b in enumerate(bars):
        by_ny_day[b.local_day(NEW_YORK_TZ)].append(i)
    step = ALLOWED_TIMEFRAMES[bars[0].timeframe]
    events: list[dict] = []
    for day, idxs in by_ny_day.items():
        target = next((i for i in idxs if bars[i].local_minute(NEW_YORK_TZ) == COMEX_OPEN_MINUTE_NY), None)
        if target is None:
            continue
        b = bars[target]
        event = {"research": "R17", "epoch": b.epoch, "year": b.dt.year, "day_new_york": day}
        for minutes in (5, 15, 30):
            n = minutes * 60 // step
            j = target - n
            event[f"pre_{minutes}m"] = (b.open / bars[j].open - 1.0) if j >= 0 and bars[target].epoch - bars[j].epoch == n * step else None
        for minutes in (15, 30, 60, 120):
            n = minutes * 60 // step
            r = forward_return(bars, target, n)
            event[f"post_{minutes}m"] = r
            pre = event.get("pre_15m")
            event[f"continuation_{minutes}m"] = (math.copysign(1.0, pre) * r) if r is not None and pre not in (None, 0.0) else None
        events.append(event)
    return events


def _returns(bars: Sequence[Bar]) -> list[float | None]:
    out: list[float | None] = [None]
    for i in range(1, len(bars)):
        step = ALLOWED_TIMEFRAMES[bars[i].timeframe]
        if bars[i].epoch - bars[i - 1].epoch == step:
            out.append(bars[i].close / bars[i - 1].close - 1.0)
        else:
            out.append(None)
    return out


def r18_volatility_shock(bars: Sequence[Bar], lookback: int = 48) -> list[dict]:
    rets = _returns(bars)
    events: list[dict] = []
    for i in range(lookback, len(bars)):
        r = rets[i]
        hist = rets[i - lookback:i]
        if r is None or any(x is None for x in hist):
            continue
        hist_f = [float(x) for x in hist if x is not None]
        sd = statistics.stdev(hist_f)
        if sd <= 0:
            continue
        score = abs(r) / sd
        crossed = [t for t in SHOCK_THRESHOLDS if score >= t]
        if not crossed:
            continue
        direction = 1 if r > 0 else -1
        e = {
            "research": "R18", "epoch": bars[i].epoch, "year": bars[i].dt.year,
            "day": bars[i].day, "bar_return": r, "shock_score": score,
            "max_preregistered_threshold": max(crossed), "direction": direction,
        }
        for h in POST_HORIZONS_M5:
            fr = forward_return(bars, i, h)
            e[f"fwd_{h}b"] = fr
            e[f"continuation_{h}b"] = direction * fr if fr is not None else None
            e[f"reversal_{h}b"] = -direction * fr if fr is not None else None
        events.append(e)
    return events


def _daily_levels(bars: Sequence[Bar]) -> dict[str, tuple[float, float]]:
    days = _same_day_indices(bars)
    ordered = sorted(days)
    out: dict[str, tuple[float, float]] = {}
    for previous, current in zip(ordered, ordered[1:]):
        idxs = days[previous]
        out[current] = (max(bars[i].high for i in idxs), min(bars[i].low for i in idxs))
    return out


def _rolling_true_range(bars: Sequence[Bar], i: int, n: int = 14) -> float | None:
    if i < n:
        return None
    trs: list[float] = []
    for j in range(i - n + 1, i + 1):
        prev = bars[j - 1].close if j > 0 else bars[j].open
        trs.append(max(bars[j].high - bars[j].low, abs(bars[j].high - prev), abs(bars[j].low - prev)))
    return statistics.fmean(trs)


def r19_previous_day_levels(bars: Sequence[Bar], proximity_atr: float = 0.20) -> list[dict]:
    levels = _daily_levels(bars)
    events: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for i, b in enumerate(bars):
        session = "London" if LONDON_START_MINUTE <= b.local_minute(LONDON_TZ) < LONDON_END_MINUTE else "NY" if NY_START_MINUTE <= b.local_minute(NEW_YORK_TZ) < NY_END_MINUTE else None
        if not session or b.day not in levels:
            continue
        atr = _rolling_true_range(bars, i)
        if not atr or atr <= 0:
            continue
        pdh, pdl = levels[b.day]
        for label, level in (("PDH", pdh), ("PDL", pdl)):
            distance = abs(b.close - level)
            if distance > proximity_atr * atr and not (b.low <= level <= b.high):
                continue
            key = (b.day, session, label)
            if key in seen:
                continue
            seen.add(key)
            side = 1 if label == "PDH" else -1
            crossed = b.close > level if side > 0 else b.close < level
            e = {
                "research": "R19", "epoch": b.epoch, "year": b.dt.year, "day": b.day,
                "session": session, "level_type": label, "level": level,
                "close": b.close, "distance": b.close - level,
                "distance_atr": (b.close - level) / atr, "closed_beyond": crossed,
            }
            for h in POST_HORIZONS_M5:
                fr = forward_return(bars, i, h)
                e[f"fwd_{h}b"] = fr
                e[f"breakout_{h}b"] = side * fr if fr is not None else None
                e[f"rejection_{h}b"] = -side * fr if fr is not None else None
            events.append(e)
    return events


def _nearest_round(price: float, step: float) -> float:
    return round(price / step) * step


def r20_round_numbers(bars: Sequence[Bar], proximity_fraction: float = 0.10) -> list[dict]:
    events: list[dict] = []
    seen: set[tuple[str, str, float, float]] = set()
    for i, b in enumerate(bars):
        session = "London" if LONDON_START_MINUTE <= b.local_minute(LONDON_TZ) < LONDON_END_MINUTE else "NY" if NY_START_MINUTE <= b.local_minute(NEW_YORK_TZ) < NY_END_MINUTE else None
        if not session:
            continue
        for step in ROUND_STEPS:
            level = _nearest_round(b.close, step)
            if abs(b.close - level) > step * proximity_fraction and not (b.low <= level <= b.high):
                continue
            key = (b.day, session, step, level)
            if key in seen:
                continue
            seen.add(key)
            prev_close = bars[i - 1].close if i > 0 else b.open
            approach_side = 1 if prev_close < level else -1 if prev_close > level else 0
            crossed = (prev_close < level <= b.close) or (prev_close > level >= b.close)
            e = {
                "research": "R20", "epoch": b.epoch, "year": b.dt.year, "day": b.day,
                "session": session, "step": step, "level": level, "close": b.close,
                "signed_distance": b.close - level, "approach_side": approach_side,
                "touched": b.low <= level <= b.high, "crossed_on_close": crossed,
            }
            for h in POST_HORIZONS_M5:
                fr = forward_return(bars, i, h)
                e[f"fwd_{h}b"] = fr
                if approach_side:
                    e[f"continuation_{h}b"] = approach_side * fr if fr is not None else None
                    e[f"rejection_{h}b"] = -approach_side * fr if fr is not None else None
                else:
                    e[f"continuation_{h}b"] = None
                    e[f"rejection_{h}b"] = None
            events.append(e)
    return events


def summarize(name: str, events: Sequence[dict]) -> dict:
    metrics = sorted({k for e in events for k in e if k.startswith(("continuation_", "reversal_", "breakout_", "rejection_", "post_", "fwd_"))})
    return {
        "research": name,
        "event_count": len(events),
        "metrics": {m: signed_stats(e[m] for e in events if isinstance(e.get(m), (int, float))) for m in metrics},
        "year_stability": {m: yearly_stability(events, m) for m in metrics},
    }


def run(path: Path, stage: str, selected: Sequence[str]) -> dict:
    bars = load_bars(path, stage=stage)
    if len({b.timeframe for b in bars}) != 1:
        raise RuntimeError("input must contain exactly one timeframe")
    if bars[0].timeframe != "M5":
        raise RuntimeError("R16-R20 v1.00 is frozen for M5 input")
    funcs = {
        "R16": r16_asian_london,
        "R17": r17_comex_open,
        "R18": r18_volatility_shock,
        "R19": r19_previous_day_levels,
        "R20": r20_round_numbers,
    }
    results = {}
    for name in selected:
        events = funcs[name](bars)
        results[name] = {"summary": summarize(name, events), "events": events}
    return {
        "schema": 1,
        "batch": "R16-R20",
        "version": "1.00",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "source": str(path),
        "rows": len(bars),
        "first_epoch": bars[0].epoch,
        "last_epoch": bars[-1].epoch,
        "protected_2026_opened": False,
        "pre_oos_2025_opened": stage == "preoos",
        "doctrine": "phenomenon-first; no P&L optimization; 2026 hard-sealed",
        "results": results,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Existing XAUUSD M5 research CSV")
    ap.add_argument("--output", required=True)
    ap.add_argument("--stage", choices=("discovery", "confirmation", "preoos"), default="discovery")
    ap.add_argument("--research", nargs="+", choices=("R16", "R17", "R18", "R19", "R20"),
                    default=["R16", "R17", "R18", "R19", "R20"])
    args = ap.parse_args()
    payload = run(Path(args.input), args.stage, args.research)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "results"}, indent=2, sort_keys=True))
    for name, item in payload["results"].items():
        print(f"{name}: events={item['summary']['event_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
