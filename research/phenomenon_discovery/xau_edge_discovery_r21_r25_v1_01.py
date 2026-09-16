#!/usr/bin/env python3
"""Preregistered XAUUSD phenomenon batch R21-R25 v1.01 — discovery only.

Implements the frozen definitions from R21_R25_XAU_RESEARCH_PLAN_2026_09_14.md.
This version can open discovery data only (<= 2019-06-30). Confirmation, 2025
pre-OOS, and 2026+ are deliberately inaccessible.
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

DISCOVERY_START = date(2004, 11, 8)
DISCOVERY_END = date(2019, 6, 30)
PROTECTED_START = date(2026, 1, 1)
NEW_YORK_TZ = ZoneInfo("America/New_York")
COMEX_OPEN_MIN = 8 * 60 + 20
OPENING_RANGE_END_MIN = 8 * 60 + 35
OPENING_BREAKOUT_LAST_OPEN_MIN = 9 * 60 + 55  # closes at 10:00 NY
POST_BARS = (1, 2, 4, 8, 16)
POST_MINUTES = (15, 30, 60, 120)
R22_LOOKBACK = 48
R22_TRAILING_DAYS = 20


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
    def utc_day(self) -> str:
        return self.dt.date().isoformat()

    @property
    def utc_minute(self) -> int:
        return self.dt.hour * 60 + self.dt.minute

    def local_day(self, tz: ZoneInfo) -> str:
        return self.dt.astimezone(tz).date().isoformat()

    def local_minute(self, tz: ZoneInfo) -> int:
        x = self.dt.astimezone(tz)
        return x.hour * 60 + x.minute


def _finite(x: float) -> bool:
    return math.isfinite(float(x))


def _discovery_date_allowed(d: date) -> bool:
    if d >= PROTECTED_START:
        raise RuntimeError(f"PROTECTED 2026 row encountered: {d.isoformat()}")
    if d > DISCOVERY_END:
        raise RuntimeError(
            f"R21-R25 v1.01 is discovery-only; out-of-discovery row encountered: {d.isoformat()}"
        )
    if d < DISCOVERY_START:
        return False
    return True


def load_bars(path: Path) -> list[Bar]:
    out: list[Bar] = []
    prev: int | None = None
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        need = {"timeframe", "server_epoch", "open", "high", "low", "close"}
        missing = need - set(r.fieldnames or [])
        if missing:
            raise RuntimeError(f"missing columns: {sorted(missing)}")
        for row in r:
            epoch = int(row["server_epoch"])
            if prev is not None and epoch <= prev:
                raise RuntimeError(f"non-increasing timestamp: {epoch} <= {prev}")
            prev = epoch
            dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
            if not _discovery_date_allowed(dt.date()):
                continue
            tf = row["timeframe"].strip().upper()
            if tf != "M5":
                raise RuntimeError(f"R21-R25 v1.01 requires M5, got {tf}")
            o, h, l, c = map(float, (row["open"], row["high"], row["low"], row["close"]))
            if not all(_finite(x) and x > 0 for x in (o, h, l, c)):
                raise RuntimeError(f"invalid OHLC at {dt.isoformat()}")
            if h < max(o, c) or l > min(o, c) or h < l:
                raise RuntimeError(f"invalid OHLC geometry at {dt.isoformat()}")
            out.append(Bar(epoch, dt, tf, o, h, l, c))
    if not out:
        raise RuntimeError("no usable discovery rows")
    return out


def _contiguous(bars: Sequence[Bar], i: int, j: int) -> bool:
    if i < 0 or j >= len(bars) or j < i:
        return False
    return all(bars[k].epoch - bars[k - 1].epoch == 300 for k in range(i + 1, j + 1))


def forward_return(bars: Sequence[Bar], i: int, horizon: int) -> float | None:
    j = i + horizon
    if j >= len(bars) or not _contiguous(bars, i, j):
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


def cluster_stats(events: Sequence[dict], metric: str) -> dict:
    """One-way day-clustered intercept-only CR1 SE.

    With k=1 (intercept only), the standard finite-sample CR1 factor reduces to
    G/(G-1); the extra (N-1)/(N-k) term equals one and must not be applied again.
    """
    xs = [
        (str(e["cluster_day"]), float(e[metric]))
        for e in events
        if e.get("cluster_day") is not None
        and isinstance(e.get(metric), (int, float))
        and _finite(e[metric])
    ]
    if not xs:
        return {"n": 0, "clusters": 0, "mean": None, "cluster_se": None, "cluster_t": None, "method": "CR1_day"}
    vals = [v for _, v in xs]
    mean = statistics.fmean(vals)
    by: dict[str, list[float]] = defaultdict(list)
    for d, v in xs:
        by[d].append(v)
    g = len(by)
    n = len(vals)
    if g < 2 or n < 2:
        return {"n": n, "clusters": g, "mean": mean, "cluster_se": None, "cluster_t": None, "method": "CR1_day"}
    scores = [sum(v - mean for v in vs) for vs in by.values()]
    meat = sum(s * s for s in scores)
    se = math.sqrt(max((g / (g - 1)) * meat / (n * n), 0.0))
    return {
        "n": n,
        "clusters": g,
        "mean": mean,
        "cluster_se": se,
        "cluster_t": mean / se if se > 0 else None,
        "method": "CR1_day",
    }


def yearly_stability(events: Sequence[dict], metric: str) -> dict:
    by: dict[int, list[float]] = defaultdict(list)
    for e in events:
        v = e.get(metric)
        if isinstance(v, (int, float)) and _finite(v):
            by[int(e["year"])].append(float(v))
    years = {str(y): signed_stats(v) for y, v in sorted(by.items())}
    pos = sum((s["mean"] or 0) > 0 for s in years.values())
    neg = sum((s["mean"] or 0) < 0 for s in years.values())
    nz = pos + neg
    return {
        "years": years,
        "positive_years": pos,
        "negative_years": neg,
        "sign_consistency": max(pos, neg) / nz if nz else None,
    }


def _index_by_ny_day(bars: Sequence[Bar]) -> dict[str, list[int]]:
    d: dict[str, list[int]] = defaultdict(list)
    for i, b in enumerate(bars):
        d[b.local_day(NEW_YORK_TZ)].append(i)
    return d


def _find_ny_anchor(bars: Sequence[Bar], idxs: Sequence[int], minute: int) -> int | None:
    return next((i for i in idxs if bars[i].local_minute(NEW_YORK_TZ) == minute), None)


def r21_comex_unconditional_drift(bars: Sequence[Bar]) -> list[dict]:
    out: list[dict] = []
    for ny_day, idxs in sorted(_index_by_ny_day(bars).items()):
        i = _find_ny_anchor(bars, idxs, COMEX_OPEN_MIN)
        if i is None:
            continue
        e = {"research": "R21", "epoch": bars[i].epoch, "year": bars[i].dt.year, "cluster_day": ny_day, "day_new_york": ny_day}
        for minutes in POST_MINUTES:
            e[f"post_{minutes}m"] = forward_return(bars, i, minutes // 5)
        out.append(e)
    return out


def _returns(bars: Sequence[Bar]) -> list[float | None]:
    out: list[float | None] = [None]
    for i in range(1, len(bars)):
        out.append(bars[i].close / bars[i - 1].close - 1 if bars[i].epoch - bars[i - 1].epoch == 300 else None)
    return out


def _rolling_stdev48(bars: Sequence[Bar]) -> list[float | None]:
    rs = _returns(bars)
    out: list[float | None] = [None] * len(bars)
    for i in range(R22_LOOKBACK, len(bars)):
        hist = rs[i - R22_LOOKBACK : i]
        if len(hist) != R22_LOOKBACK or any(x is None for x in hist):
            continue
        sd = statistics.stdev(float(x) for x in hist if x is not None)
        if sd >= 0:
            out[i] = sd
    return out


def _quantile_nearest_rank(xs: Sequence[float], q: float) -> float:
    ys = sorted(float(x) for x in xs)
    rank = max(1, math.ceil(q * len(ys)))
    return ys[rank - 1]


def _baseline_observations(bars: Sequence[Bar], horizon: int) -> list[tuple[str, int, float]]:
    out: list[tuple[str, int, float]] = []
    for i, b in enumerate(bars):
        r = forward_return(bars, i, horizon)
        if r is not None:
            out.append((b.utc_day, b.utc_minute, abs(r)))
    return out


def _baseline_means(bars: Sequence[Bar]) -> dict[tuple[int, int], float]:
    buckets: dict[tuple[int, int], list[float]] = defaultdict(list)
    for h in POST_BARS:
        for _, clock, y in _baseline_observations(bars, h):
            buckets[(clock, h)].append(y)
    return {k: statistics.fmean(v) for k, v in buckets.items() if v}


def r22_volatility_compression(bars: Sequence[Bar]) -> list[dict]:
    st = _rolling_stdev48(bars)
    baselines = _baseline_means(bars)
    hbd: dict[str, list[float]] = defaultdict(list)
    ordered: list[str] = []
    seen: set[str] = set()
    for i, b in enumerate(bars):
        if st[i] is None:
            continue
        hbd[b.utc_day].append(float(st[i]))
        if b.utc_day not in seen:
            seen.add(b.utc_day)
            ordered.append(b.utc_day)
    prior: dict[str, list[float]] = {}
    for pos, d in enumerate(ordered):
        vals: list[float] = []
        for pd in ordered[max(0, pos - R22_TRAILING_DAYS) : pos]:
            vals.extend(hbd[pd])
        prior[d] = vals

    out: list[dict] = []
    sampled: set[tuple[str, int, str]] = set()
    for i, b in enumerate(bars):
        sd = st[i]
        hist = prior.get(b.utc_day, [])
        if sd is None or not hist:
            continue
        q10 = _quantile_nearest_rank(hist, 0.10)
        q20 = _quantile_nearest_rank(hist, 0.20)
        states: list[str] = []
        if sd <= q10:
            states.append("bottom10")
        if sd <= q20:
            states.append("bottom20")
        for state in states:
            key = (b.utc_day, b.dt.hour, state)
            if key in sampled:
                continue
            sampled.add(key)
            e = {
                "research": "R22",
                "compression_state": state,
                "epoch": b.epoch,
                "year": b.dt.year,
                "cluster_day": b.utc_day,
                "day_utc": b.utc_day,
                "utc_hour": b.dt.hour,
                "utc_minute": b.utc_minute,
                "stdev48": sd,
                "q10": q10,
                "q20": q20,
                "trailing_distribution_n": len(hist),
            }
            for h in POST_BARS:
                r = forward_return(bars, i, h)
                ar = abs(r) if r is not None else None
                base = baselines.get((b.utc_minute, h))
                e[f"abs_fwd_{h}b"] = ar
                e[f"baseline_abs_{h}b"] = base
                e[f"excess_abs_{h}b"] = ar - base if ar is not None and base is not None else None
            out.append(e)
    return out


def r22_complete_estimator_day_jackknife(
    bars: Sequence[Bar], events: Sequence[dict], state: str, horizon: int
) -> dict:
    """Day-cluster delete-one jackknife of the complete R22 estimator.

    Recomputes both the compressed-event mean and the shared same-clock baseline
    after deleting each UTC day, so baseline estimation uncertainty is included.
    """
    metric = f"abs_fwd_{horizon}b"
    ev = [
        e
        for e in events
        if e.get("compression_state") == state
        and isinstance(e.get(metric), (int, float))
        and isinstance(e.get("utc_minute"), int)
    ]
    if not ev:
        return {"n": 0, "clusters": 0, "mean": None, "cluster_se": None, "cluster_t": None, "method": "delete_one_day_complete_estimator"}

    base_obs = _baseline_observations(bars, horizon)
    total_base_count: dict[int, int] = defaultdict(int)
    total_base_sum: dict[int, float] = defaultdict(float)
    day_base_count: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    day_base_sum: dict[str, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for day, clock, y in base_obs:
        total_base_count[clock] += 1
        total_base_sum[clock] += y
        day_base_count[day][clock] += 1
        day_base_sum[day][clock] += y

    event_count_clock: dict[int, int] = defaultdict(int)
    day_event_count_clock: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    day_event_n: dict[str, int] = defaultdict(int)
    day_event_sum: dict[str, float] = defaultdict(float)
    event_sum = 0.0
    for e in ev:
        day = str(e["cluster_day"])
        clock = int(e["utc_minute"])
        y = float(e[metric])
        event_count_clock[clock] += 1
        day_event_count_clock[day][clock] += 1
        day_event_n[day] += 1
        day_event_sum[day] += y
        event_sum += y

    n = len(ev)

    def estimate(
        n_event: int,
        sum_event: float,
        counts_event_clock: dict[int, int],
        removed_day: str | None = None,
    ) -> float | None:
        if n_event <= 0:
            return None
        weighted_base = 0.0
        for clock, ec in counts_event_clock.items():
            if ec <= 0:
                continue
            bc = total_base_count[clock]
            bs = total_base_sum[clock]
            if removed_day is not None:
                bc -= day_base_count[removed_day].get(clock, 0)
                bs -= day_base_sum[removed_day].get(clock, 0.0)
            if bc <= 0:
                return None
            weighted_base += ec * (bs / bc)
        return sum_event / n_event - weighted_base / n_event

    full = estimate(n, event_sum, dict(event_count_clock), None)
    if full is None:
        return {"n": n, "clusters": 0, "mean": None, "cluster_se": None, "cluster_t": None, "method": "delete_one_day_complete_estimator"}

    days = sorted({day for day, _, _ in base_obs} | set(day_event_n))
    loo: list[float] = []
    for day in days:
        n2 = n - day_event_n.get(day, 0)
        sum2 = event_sum - day_event_sum.get(day, 0.0)
        counts2 = dict(event_count_clock)
        for clock, c in day_event_count_clock.get(day, {}).items():
            counts2[clock] = counts2.get(clock, 0) - c
        est = estimate(n2, sum2, counts2, day)
        if est is not None:
            loo.append(est)
    g = len(loo)
    if g < 2:
        return {"n": n, "clusters": g, "mean": full, "cluster_se": None, "cluster_t": None, "method": "delete_one_day_complete_estimator"}
    mean_loo = statistics.fmean(loo)
    var = ((g - 1) / g) * sum((x - mean_loo) ** 2 for x in loo)
    se = math.sqrt(max(var, 0.0))
    return {
        "n": n,
        "clusters": g,
        "mean": full,
        "cluster_se": se,
        "cluster_t": full / se if se > 0 else None,
        "method": "delete_one_day_complete_estimator",
    }


def r23_overnight_to_ny(bars: Sequence[Bar]) -> list[dict]:
    by_epoch = {b.epoch: i for i, b in enumerate(bars)}
    out: list[dict] = []
    for ny_day, idxs in sorted(_index_by_ny_day(bars).items()):
        i = _find_ny_anchor(bars, idxs, COMEX_OPEN_MIN)
        if i is None:
            continue
        a = bars[i]
        midnight = int(datetime(a.dt.year, a.dt.month, a.dt.day, tzinfo=timezone.utc).timestamp())
        j = by_epoch.get(midnight)
        if j is None or bars[j].dt.date() != a.dt.date():
            continue
        pre = a.close / bars[j].close - 1
        if pre == 0:
            continue
        direction = 1 if pre > 0 else -1
        e = {
            "research": "R23",
            "epoch": a.epoch,
            "year": a.dt.year,
            "cluster_day": ny_day,
            "day_new_york": ny_day,
            "pre_ny_return": pre,
            "direction": direction,
            "utc_midnight_epoch": bars[j].epoch,
        }
        for minutes in POST_MINUTES:
            r = forward_return(bars, i, minutes // 5)
            e[f"post_{minutes}m"] = r
            e[f"continuation_{minutes}m"] = direction * r if r is not None else None
            e[f"reversal_{minutes}m"] = -direction * r if r is not None else None
        out.append(e)
    return out


def r24_comex_opening_range_breakout(bars: Sequence[Bar]) -> list[dict]:
    out: list[dict] = []
    for ny_day, idxs in sorted(_index_by_ny_day(bars).items()):
        minute_to_i = {bars[i].local_minute(NEW_YORK_TZ): i for i in idxs}
        range_minutes = [COMEX_OPEN_MIN, COMEX_OPEN_MIN + 5, COMEX_OPEN_MIN + 10]
        if any(mn not in minute_to_i for mn in range_minutes):
            continue
        ris = [minute_to_i[mn] for mn in range_minutes]
        hi = max(bars[i].high for i in ris)
        lo = min(bars[i].low for i in ris)
        bi: int | None = None
        direction = 0
        valid = True
        for minute in range(OPENING_RANGE_END_MIN, OPENING_BREAKOUT_LAST_OPEN_MIN + 1, 5):
            i = minute_to_i.get(minute)
            if i is None:
                valid = False
                break
            if bars[i].close > hi:
                bi, direction = i, 1
                break
            if bars[i].close < lo:
                bi, direction = i, -1
                break
        if not valid or bi is None:
            continue
        b = bars[bi]
        e = {
            "research": "R24",
            "epoch": b.epoch,
            "year": b.dt.year,
            "cluster_day": ny_day,
            "day_new_york": ny_day,
            "direction": direction,
            "opening_range_high": hi,
            "opening_range_low": lo,
            "breakout_close": b.close,
        }
        for h in POST_BARS:
            r = forward_return(bars, bi, h)
            e[f"continuation_{h}b"] = direction * r if r is not None else None
            e[f"reversal_{h}b"] = -direction * r if r is not None else None
        out.append(e)
    return out


def _utc_day_indices(bars: Sequence[Bar]) -> tuple[list[str], dict[str, list[int]]]:
    d: dict[str, list[int]] = defaultdict(list)
    for i, b in enumerate(bars):
        d[b.utc_day].append(i)
    return sorted(d), d


def r25_ny_gap_previous_close(bars: Sequence[Bar]) -> list[dict]:
    days, by = _utc_day_indices(bars)
    prevmap = {cur: prev for prev, cur in zip(days, days[1:])}
    out: list[dict] = []
    for ny_day, idxs in sorted(_index_by_ny_day(bars).items()):
        i = _find_ny_anchor(bars, idxs, COMEX_OPEN_MIN)
        if i is None:
            continue
        a = bars[i]
        prevday = prevmap.get(a.utc_day)
        if prevday is None:
            continue
        pidx = by[prevday][-1]
        pc = bars[pidx].close
        gap = a.close / pc - 1
        if gap == 0:
            continue
        direction = 1 if gap > 0 else -1
        e = {
            "research": "R25",
            "epoch": a.epoch,
            "year": a.dt.year,
            "cluster_day": ny_day,
            "day_new_york": ny_day,
            "previous_utc_day": prevday,
            "previous_close_epoch": bars[pidx].epoch,
            "previous_close": pc,
            "anchor_close": a.close,
            "gap_return": gap,
            "gap_direction": direction,
        }
        for minutes in POST_MINUTES:
            h = minutes // 5
            r = forward_return(bars, i, h)
            e[f"toward_{minutes}m"] = -direction * r if r is not None else None
            e[f"away_{minutes}m"] = direction * r if r is not None else None
            j = i + h
            if r is None or j >= len(bars):
                e[f"filled_by_{minutes}m"] = None
            else:
                path = bars[i + 1 : j + 1]
                e[f"filled_by_{minutes}m"] = (
                    any(x.low <= pc for x in path) if direction > 0 else any(x.high >= pc for x in path)
                )
        out.append(e)
    return out


def _metric_summary(events: Sequence[dict], prefixes: tuple[str, ...]) -> dict:
    metrics = sorted({k for e in events for k in e if k.startswith(prefixes)})
    return {
        metric: {
            "naive": signed_stats(e[metric] for e in events if isinstance(e.get(metric), (int, float))),
            "clustered": cluster_stats(events, metric),
            "year_stability": yearly_stability(events, metric),
        }
        for metric in metrics
    }


def _r25_fill_summary(events: Sequence[dict]) -> dict:
    out: dict[str, dict] = {}
    for minutes in POST_MINUTES:
        key = f"filled_by_{minutes}m"
        vals = [bool(e[key]) for e in events if isinstance(e.get(key), bool)]
        out[key] = {
            "n_valid": len(vals),
            "filled": sum(vals),
            "fill_probability": (sum(vals) / len(vals)) if vals else None,
        }
    return out


def summarize(name: str, events: Sequence[dict], bars: Sequence[Bar]) -> dict:
    prefixes = ("post_", "excess_abs_", "continuation_", "reversal_", "toward_", "away_")
    out: dict = {
        "research": name,
        "event_count": len(events),
        "day_count": len({e["cluster_day"] for e in events}),
    }
    if name == "R22":
        out["states"] = {}
        for state in ("bottom10", "bottom20"):
            xs = [e for e in events if e.get("compression_state") == state]
            metrics = _metric_summary(xs, prefixes)
            for h in POST_BARS:
                key = f"excess_abs_{h}b"
                if key in metrics:
                    metrics[key]["clustered"] = r22_complete_estimator_day_jackknife(bars, events, state, h)
            out["states"][state] = {
                "event_count": len(xs),
                "day_count": len({e["cluster_day"] for e in xs}),
                "metrics": metrics,
            }
    else:
        out["metrics"] = _metric_summary(events, prefixes)
        if name == "R25":
            out["fill_probability_descriptive"] = _r25_fill_summary(events)
    return out


def run(path: Path, selected: Sequence[str]) -> dict:
    bars = load_bars(path)
    funcs = {
        "R21": r21_comex_unconditional_drift,
        "R22": r22_volatility_compression,
        "R23": r23_overnight_to_ny,
        "R24": r24_comex_opening_range_breakout,
        "R25": r25_ny_gap_previous_close,
    }
    results: dict = {}
    for name in selected:
        ev = funcs[name](bars)
        results[name] = {"summary": summarize(name, ev, bars), "events": ev}
    return {
        "schema": 1,
        "batch": "R21-R25",
        "version": "1.01",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "discovery",
        "source": str(path),
        "rows": len(bars),
        "first_epoch": bars[0].epoch,
        "last_epoch": bars[-1].epoch,
        "stage_boundaries": {
            "discovery_start": DISCOVERY_START.isoformat(),
            "discovery_end": DISCOVERY_END.isoformat(),
            "confirmation": "LOCKED_IN_V1_01",
            "preoos_2025": "LOCKED_IN_V1_01",
            "protected_2026_plus": "HARD_FAIL",
        },
        "protected_2026_opened": False,
        "pre_oos_2025_opened": False,
        "confirmation_opened": False,
        "doctrine": "phenomenon-first; preregistered definitions only; discovery only; no P&L optimization",
        "results": results,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument(
        "--research",
        nargs="+",
        choices=("R21", "R22", "R23", "R24", "R25"),
        default=["R21", "R22", "R23", "R24", "R25"],
    )
    a = ap.parse_args()
    payload = run(Path(a.input), a.research)
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "results"}, indent=2, sort_keys=True))
    for name, item in payload["results"].items():
        print(f"{name}: events={item['summary']['event_count']} days={item['summary']['day_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
