#!/usr/bin/env python3
"""Preregistered XAUUSD phenomenon batch R16-R20 v1.00.

Phenomenon-first event study. No entry/SL/TP/PnL optimisation.
2026 is hard-sealed in every mode.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo

DISCOVERY_END = date(2019, 6, 30)
CONFIRMATION_START = date(2019, 7, 1)
CONFIRMATION_END = date(2024, 12, 31)
PREOOS_START = date(2025, 1, 1)
PREOOS_END = date(2025, 12, 31)
PROTECTED_START = date(2026, 1, 1)
ALLOWED_TIMEFRAMES = {"M5": 300}
POST_HORIZONS = (1, 2, 4, 8, 16)
SHOCK_THRESHOLDS = (2.0, 2.5, 3.0)
ROUND_STEPS = (10.0, 25.0, 50.0, 100.0)
LONDON_TZ = ZoneInfo("Europe/London")
NEW_YORK_TZ = ZoneInfo("America/New_York")
ASIA_START = 0
ASIA_END = 7 * 60
LONDON_START = 8 * 60
LONDON_END = 12 * 60
NY_START = 8 * 60 + 20
NY_END = 12 * 60
COMEX_OPEN = 8 * 60 + 20


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
        x = self.dt.astimezone(tz)
        return x.hour * 60 + x.minute

    def local_day(self, tz: ZoneInfo) -> str:
        return self.dt.astimezone(tz).date().isoformat()


def _finite(x: float) -> bool:
    return math.isfinite(x)


def _stage_accepts(d: date, stage: str) -> bool:
    if d >= PROTECTED_START:
        raise RuntimeError(f"PROTECTED 2026 row encountered: {d.isoformat()}")
    if stage == "discovery":
        return d <= DISCOVERY_END
    if stage == "confirmation":
        return CONFIRMATION_START <= d <= CONFIRMATION_END
    if stage == "preoos":
        return PREOOS_START <= d <= PREOOS_END
    raise ValueError(f"unsupported stage: {stage}")


def load_bars(path: Path, stage: str) -> list[Bar]:
    bars: list[Bar] = []
    previous_epoch: int | None = None
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        need = {"timeframe", "server_epoch", "open", "high", "low", "close"}
        missing = need - set(reader.fieldnames or [])
        if missing:
            raise RuntimeError(f"missing columns: {sorted(missing)}")
        for row in reader:
            epoch = int(row["server_epoch"])
            if previous_epoch is not None and epoch <= previous_epoch:
                raise RuntimeError(f"non-increasing timestamp: {epoch} <= {previous_epoch}")
            previous_epoch = epoch
            dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
            accepted = _stage_accepts(dt.date(), stage)  # protection checked before filtering
            if not accepted:
                continue
            tf = row["timeframe"].strip().upper()
            if tf != "M5":
                raise RuntimeError(f"R16-R20 v1.00 requires M5, got {tf}")
            o, h, l, c = map(float, (row["open"], row["high"], row["low"], row["close"]))
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
    if bars[j].epoch - bars[i].epoch != 300 * horizon:
        return None
    return bars[j].close / bars[i].close - 1.0


def signed_stats(values: Iterable[float]) -> dict:
    xs = [float(x) for x in values if _finite(float(x))]
    if not xs:
        return {"n": 0, "mean": None, "median": None, "t": None, "positive_fraction": None}
    n = len(xs)
    mean = statistics.fmean(xs)
    sd = statistics.stdev(xs) if n > 1 else 0.0
    return {
        "n": n,
        "mean": mean,
        "median": statistics.median(xs),
        "t": mean / (sd / math.sqrt(n)) if n > 1 and sd > 0 else None,
        "positive_fraction": sum(x > 0 for x in xs) / n,
    }


def yearly_stability(events: Sequence[dict], metric: str) -> dict:
    by_year: dict[int, list[float]] = defaultdict(list)
    for e in events:
        v = e.get(metric)
        if isinstance(v, (int, float)) and _finite(float(v)):
            by_year[int(e["year"])].append(float(v))
    years = {str(y): signed_stats(v) for y, v in sorted(by_year.items())}
    pos = sum((s["mean"] or 0) > 0 for s in years.values())
    neg = sum((s["mean"] or 0) < 0 for s in years.values())
    nz = pos + neg
    return {"years": years, "positive_years": pos, "negative_years": neg,
            "sign_consistency": max(pos, neg) / nz if nz else None}


def r16_asian_london(bars: Sequence[Bar], reentry_bars: int = 3) -> list[dict]:
    by_day: dict[str, list[int]] = defaultdict(list)
    for i, b in enumerate(bars):
        by_day[b.local_day(LONDON_TZ)].append(i)
    events: list[dict] = []
    for day, idxs in by_day.items():
        asia = [i for i in idxs if ASIA_START <= bars[i].local_minute(LONDON_TZ) < ASIA_END]
        london = [i for i in idxs if LONDON_START <= bars[i].local_minute(LONDON_TZ) < LONDON_END]
        if not asia or not london:
            continue
        hi, lo = max(bars[i].high for i in asia), min(bars[i].low for i in asia)
        if hi <= lo:
            continue
        for i in london:
            b = bars[i]
            direction = 1 if b.close > hi else -1 if b.close < lo else 0
            if not direction:
                continue
            reentry_idx: int | None = None
            for k in range(1, reentry_bars + 1):
                j = i + k
                if j >= len(bars) or bars[j].local_day(LONDON_TZ) != day:
                    break
                if lo <= bars[j].close <= hi:
                    reentry_idx = j
                    break
            e = {"research": "R16", "epoch": b.epoch, "year": b.dt.year,
                 "day_london": day, "direction": direction, "asian_high": hi,
                 "asian_low": lo, "asian_range": hi - lo, "break_close": b.close,
                 "break_displacement_range": ((b.close-hi) if direction > 0 else (lo-b.close))/(hi-lo),
                 "reentered_within_bars": reentry_idx is not None,
                 "reentry_epoch": bars[reentry_idx].epoch if reentry_idx is not None else None,
                 "bars_to_reentry": reentry_idx-i if reentry_idx is not None else None}
            for h in POST_HORIZONS:
                r = forward_return(bars, i, h)
                e[f"continuation_{h}b"] = direction * r if r is not None else None
                rr = forward_return(bars, reentry_idx, h) if reentry_idx is not None else None
                e[f"reversal_{h}b"] = -direction * rr if rr is not None else None
            events.append(e)
            break
    return events


def r17_comex_open(bars: Sequence[Bar]) -> list[dict]:
    by_day: dict[str, list[int]] = defaultdict(list)
    for i, b in enumerate(bars):
        by_day[b.local_day(NEW_YORK_TZ)].append(i)
    events: list[dict] = []
    for day, idxs in by_day.items():
        i = next((x for x in idxs if bars[x].local_minute(NEW_YORK_TZ) == COMEX_OPEN), None)
        if i is None:
            continue
        e = {"research": "R17", "epoch": bars[i].epoch, "year": bars[i].dt.year, "day_new_york": day}
        for mins in (5, 15, 30):
            n = mins // 5
            j = i - n
            e[f"pre_{mins}m"] = bars[i].open / bars[j].open - 1 if j >= 0 and bars[i].epoch-bars[j].epoch == n*300 else None
        for mins in (15, 30, 60, 120):
            r = forward_return(bars, i, mins//5)
            pre = e.get("pre_15m")
            e[f"post_{mins}m"] = r
            e[f"continuation_{mins}m"] = math.copysign(1.0, pre)*r if r is not None and pre not in (None, 0.0) else None
            e[f"reversal_{mins}m"] = -math.copysign(1.0, pre)*r if r is not None and pre not in (None, 0.0) else None
        events.append(e)
    return events


def _returns(bars: Sequence[Bar]) -> list[float | None]:
    out: list[float | None] = [None]
    for i in range(1, len(bars)):
        out.append(bars[i].close/bars[i-1].close-1 if bars[i].epoch-bars[i-1].epoch == 300 else None)
    return out


def r18_volatility_shock(bars: Sequence[Bar], lookback: int = 48) -> list[dict]:
    rs = _returns(bars); events: list[dict] = []
    for i in range(lookback, len(bars)):
        r, hist = rs[i], rs[i-lookback:i]
        if r is None or any(x is None for x in hist):
            continue
        sd = statistics.stdev(float(x) for x in hist if x is not None)
        if sd <= 0 or abs(r)/sd < SHOCK_THRESHOLDS[0]:
            continue
        score = abs(r)/sd; direction = 1 if r > 0 else -1
        e = {"research":"R18","epoch":bars[i].epoch,"year":bars[i].dt.year,"day":bars[i].day,
             "bar_return":r,"shock_score":score,
             "max_preregistered_threshold":max(t for t in SHOCK_THRESHOLDS if score >= t),"direction":direction}
        for h in POST_HORIZONS:
            fr = forward_return(bars, i, h)
            e[f"continuation_{h}b"] = direction*fr if fr is not None else None
            e[f"reversal_{h}b"] = -direction*fr if fr is not None else None
        events.append(e)
    return events


def _daily_levels(bars: Sequence[Bar]) -> dict[str, tuple[float,float]]:
    days: dict[str,list[int]] = defaultdict(list)
    for i,b in enumerate(bars): days[b.day].append(i)
    ordered = sorted(days); out: dict[str,tuple[float,float]] = {}
    for prev, cur in zip(ordered, ordered[1:]):
        idx = days[prev]; out[cur] = (max(bars[i].high for i in idx), min(bars[i].low for i in idx))
    return out


def _atr(bars: Sequence[Bar], i: int, n: int = 14) -> float | None:
    if i < n: return None
    tr=[]
    for j in range(i-n+1, i+1):
        prev=bars[j-1].close
        tr.append(max(bars[j].high-bars[j].low, abs(bars[j].high-prev), abs(bars[j].low-prev)))
    return statistics.fmean(tr)


def _session(b: Bar) -> str | None:
    if LONDON_START <= b.local_minute(LONDON_TZ) < LONDON_END: return "London"
    if NY_START <= b.local_minute(NEW_YORK_TZ) < NY_END: return "NY"
    return None


def r19_previous_day_levels(bars: Sequence[Bar], proximity_atr: float = .20) -> list[dict]:
    levels=_daily_levels(bars); seen=set(); events=[]
    for i,b in enumerate(bars):
        session=_session(b)
        if not session or b.day not in levels: continue
        atr=_atr(bars,i)
        if not atr: continue
        for label,level,side in (("PDH",levels[b.day][0],1),("PDL",levels[b.day][1],-1)):
            if abs(b.close-level)>proximity_atr*atr and not b.low<=level<=b.high: continue
            key=(b.day,session,label)
            if key in seen: continue
            seen.add(key)
            e={"research":"R19","epoch":b.epoch,"year":b.dt.year,"day":b.day,"session":session,
               "level_type":label,"level":level,"close":b.close,"distance":b.close-level,
               "distance_atr":(b.close-level)/atr,"closed_beyond": b.close>level if side>0 else b.close<level}
            for h in POST_HORIZONS:
                fr=forward_return(bars,i,h)
                e[f"breakout_{h}b"]=side*fr if fr is not None else None
                e[f"rejection_{h}b"]=-side*fr if fr is not None else None
            events.append(e)
    return events


def _nearest_round(price: float, step: float) -> float:
    return round(price/step)*step


def r20_round_numbers(bars: Sequence[Bar], proximity_fraction: float = .10) -> list[dict]:
    seen=set(); events=[]
    for i,b in enumerate(bars):
        session=_session(b)
        if not session: continue
        for step in ROUND_STEPS:
            level=_nearest_round(b.close,step)
            if abs(b.close-level)>step*proximity_fraction and not b.low<=level<=b.high: continue
            key=(b.day,session,step,level)
            if key in seen: continue
            seen.add(key)
            prev=bars[i-1].close if i else b.open
            approach=1 if prev<level else -1 if prev>level else 0
            e={"research":"R20","epoch":b.epoch,"year":b.dt.year,"day":b.day,"session":session,
               "step":step,"level":level,"close":b.close,"signed_distance":b.close-level,
               "approach_side":approach,"touched":b.low<=level<=b.high,
               "crossed_on_close":(prev<level<=b.close) or (prev>level>=b.close)}
            for h in POST_HORIZONS:
                fr=forward_return(bars,i,h)
                e[f"continuation_{h}b"]=approach*fr if fr is not None and approach else None
                e[f"rejection_{h}b"]=-approach*fr if fr is not None and approach else None
            events.append(e)
    return events


def summarize(name: str, events: Sequence[dict]) -> dict:
    prefixes=("continuation_","reversal_","breakout_","rejection_","post_")
    metrics=sorted({k for e in events for k in e if k.startswith(prefixes)})
    return {"research":name,"event_count":len(events),
            "metrics":{m:signed_stats(e[m] for e in events if isinstance(e.get(m),(int,float))) for m in metrics},
            "year_stability":{m:yearly_stability(events,m) for m in metrics}}


def run(path: Path, stage: str, selected: Sequence[str]) -> dict:
    bars=load_bars(path,stage)
    funcs={"R16":r16_asian_london,"R17":r17_comex_open,"R18":r18_volatility_shock,
           "R19":r19_previous_day_levels,"R20":r20_round_numbers}
    results={}
    for name in selected:
        ev=funcs[name](bars); results[name]={"summary":summarize(name,ev),"events":ev}
    return {"schema":1,"batch":"R16-R20","version":"1.00","generated_at_utc":datetime.now(timezone.utc).isoformat(),
            "stage":stage,"source":str(path),"rows":len(bars),"first_epoch":bars[0].epoch,"last_epoch":bars[-1].epoch,
            "stage_boundaries":{"discovery_end":"2019-06-30","confirmation_start":"2019-07-01","confirmation_end":"2024-12-31","preoos":"2025","protected":"2026+"},
            "protected_2026_opened":False,"pre_oos_2025_opened":stage=="preoos",
            "doctrine":"phenomenon-first; independent stages; no P&L optimization; 2026 hard-sealed","results":results}


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--stage",choices=("discovery","confirmation","preoos"),default="discovery")
    ap.add_argument("--research",nargs="+",choices=("R16","R17","R18","R19","R20"),default=["R16","R17","R18","R19","R20"])
    a=ap.parse_args(); payload=run(Path(a.input),a.stage,a.research)
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in payload.items() if k!="results"},indent=2,sort_keys=True))
    for name,item in payload["results"].items(): print(f"{name}: events={item['summary']['event_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
