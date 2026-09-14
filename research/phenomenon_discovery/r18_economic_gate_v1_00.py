#!/usr/bin/env python3
"""R18 economic gate v1.00.

Purpose
-------
Translate the already-confirmed R18 XAUUSD M5 volatility-shock mean-reversion
phenomenon into a deliberately minimal tradability test WITHOUT opening 2025
or 2026.

Frozen phenomenon definition
----------------------------
- XAUUSD M5 only.
- Shock return: current close / previous close - 1.
- Volatility estimate: sample stdev of the previous 48 contiguous M5 returns.
- Event threshold: abs(shock_return) / trailing_stdev >= 2.0.
- Trade direction: opposite the shock sign.
- Entry: next M5 bar OPEN (first causally executable price after shock close).
- Exits: close after 1, 2, 4, 8, 16 M5 bars from the shock bar, i.e. the
  same frozen horizons used by R18. An exit is accepted only if the complete
  timestamp chain is contiguous.
- No stop, target, trailing, sizing, or parameter search.

Economic-cost doctrine
----------------------
The script reports exact break-even all-in round-trip cost in basis points.
It also evaluates preregistered all-in cost scenarios 0.0, 0.5, 1.0, 2.0,
and 4.0 bps. These are scenarios, not fitted parameters.

Primary economic gate
---------------------
The candidate passes only if BOTH frozen primary horizons (1b and 2b), in
BOTH discovery and independent confirmation samples, have positive net mean
at 1.0 bp all-in round-trip cost in the non-overlap execution mode.

The 1.0 bp hurdle is a fixed robustness hurdle; it is not estimated from the
sample. Gross results and all other cost scenarios remain descriptive.

Protection
----------
Rows dated 2025-01-01 or later are rejected BEFORE any calculation. This gate
therefore cannot inspect pre-OOS 2025 or protected 2026 data.
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
from typing import Iterable

DISCOVERY_END = date(2019, 6, 30)
CONFIRMATION_START = date(2019, 7, 1)
CONFIRMATION_END = date(2024, 12, 31)
PREOOS_START = date(2025, 1, 1)
PROTECTED_START = date(2026, 1, 1)
LOOKBACK = 48
SHOCK_THRESHOLD = 2.0
HORIZONS = (1, 2, 4, 8, 16)
PRIMARY_HORIZONS = (1, 2)
COST_BPS = (0.0, 0.5, 1.0, 2.0, 4.0)
PRIMARY_COST_BPS = 1.0
SECONDS = 300


@dataclass(frozen=True)
class Bar:
    epoch: int
    dt: datetime
    open: float
    high: float
    low: float
    close: float


def _finite(x: float) -> bool:
    return math.isfinite(x)


def load_pre2025_m5(path: Path) -> list[Bar]:
    bars: list[Bar] = []
    prev_epoch: int | None = None
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        need = {"timeframe", "server_epoch", "open", "high", "low", "close"}
        missing = need - set(r.fieldnames or [])
        if missing:
            raise RuntimeError(f"missing columns: {sorted(missing)}")
        for row in r:
            epoch = int(row["server_epoch"])
            if prev_epoch is not None and epoch <= prev_epoch:
                raise RuntimeError(f"non-increasing timestamp: {epoch} <= {prev_epoch}")
            prev_epoch = epoch
            dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
            if dt.date() >= PREOOS_START:
                # Fail closed rather than silently filtering unseen 2025/2026 rows.
                break
            tf = row["timeframe"].strip().upper()
            if tf != "M5":
                raise RuntimeError(f"R18 economic gate requires M5, got {tf}")
            o, h, l, c = map(float, (row["open"], row["high"], row["low"], row["close"]))
            if not all(_finite(x) and x > 0 for x in (o, h, l, c)):
                raise RuntimeError(f"invalid OHLC at {dt.isoformat()}")
            if h < max(o, c) or l > min(o, c) or h < l:
                raise RuntimeError(f"invalid OHLC geometry at {dt.isoformat()}")
            bars.append(Bar(epoch, dt, o, h, l, c))
    if not bars:
        raise RuntimeError("no pre-2025 M5 rows")
    if bars[-1].dt.date() > CONFIRMATION_END:
        raise RuntimeError("unexpected post-confirmation row loaded")
    return bars


def _sample(b: Bar) -> str | None:
    d = b.dt.date()
    if d <= DISCOVERY_END:
        return "discovery"
    if CONFIRMATION_START <= d <= CONFIRMATION_END:
        return "confirmation"
    return None


def _returns(bars: list[Bar]) -> list[float | None]:
    out: list[float | None] = [None]
    for i in range(1, len(bars)):
        if bars[i].epoch - bars[i-1].epoch != SECONDS:
            out.append(None)
        else:
            out.append(bars[i].close / bars[i-1].close - 1.0)
    return out


def detect_events(bars: list[Bar]) -> list[dict]:
    rs = _returns(bars)
    events: list[dict] = []
    for i in range(LOOKBACK, len(bars)):
        sample = _sample(bars[i])
        if sample is None:
            continue
        r = rs[i]
        hist = rs[i-LOOKBACK:i]
        if r is None or any(x is None for x in hist):
            continue
        sd = statistics.stdev(float(x) for x in hist if x is not None)
        if sd <= 0:
            continue
        score = abs(r) / sd
        if score < SHOCK_THRESHOLD:
            continue
        direction = 1 if r > 0 else -1
        entry_idx = i + 1
        if entry_idx >= len(bars) or bars[entry_idx].epoch - bars[i].epoch != SECONDS:
            continue
        event = {
            "shock_idx": i,
            "entry_idx": entry_idx,
            "epoch": bars[i].epoch,
            "sample": sample,
            "year": bars[i].dt.year,
            "direction": direction,
            "shock_score": score,
            "entry": bars[entry_idx].open,
        }
        valid_any = False
        for h in HORIZONS:
            exit_idx = i + h
            key = f"gross_{h}b"
            if exit_idx < entry_idx or exit_idx >= len(bars):
                event[key] = None
                continue
            # Require exact contiguous path from shock through exit.
            if bars[exit_idx].epoch - bars[i].epoch != h * SECONDS:
                event[key] = None
                continue
            exit_px = bars[exit_idx].close
            # contrarian trade: -direction * simple return from executable entry
            event[key] = -direction * (exit_px / bars[entry_idx].open - 1.0)
            valid_any = True
        if valid_any:
            events.append(event)
    return events


def select_nonoverlap(events: list[dict], horizon: int) -> list[dict]:
    selected: list[dict] = []
    busy_until_idx = -1
    for e in events:
        if e.get(f"gross_{horizon}b") is None:
            continue
        if e["entry_idx"] <= busy_until_idx:
            continue
        selected.append(e)
        busy_until_idx = e["shock_idx"] + horizon
    return selected


def _stats(values: Iterable[float]) -> dict:
    xs = [float(x) for x in values if _finite(float(x))]
    if not xs:
        return {"n": 0, "mean": None, "median": None, "win_rate": None,
                "profit_factor": None, "t": None, "sum": None}
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x < 0]
    n = len(xs)
    mean = statistics.fmean(xs)
    sd = statistics.stdev(xs) if n > 1 else 0.0
    gross_profit = sum(wins)
    gross_loss = -sum(losses)
    return {
        "n": n,
        "mean": mean,
        "median": statistics.median(xs),
        "win_rate": len(wins) / n,
        "profit_factor": (gross_profit / gross_loss) if gross_loss > 0 else None,
        "t": mean / (sd / math.sqrt(n)) if n > 1 and sd > 0 else None,
        "sum": sum(xs),
    }


def _max_drawdown_simple(returns: list[float]) -> float:
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        equity *= 1.0 + r
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, 1.0 - equity / peak)
    return max_dd


def summarize(events: list[dict], horizon: int, cost_bps: float) -> dict:
    cost = cost_bps / 10000.0
    gross = [float(e[f"gross_{horizon}b"]) for e in events if e.get(f"gross_{horizon}b") is not None]
    net = [x - cost for x in gross]
    by_year: dict[int, list[float]] = defaultdict(list)
    for e in events:
        v = e.get(f"gross_{horizon}b")
        if v is not None:
            by_year[int(e["year"])].append(float(v) - cost)
    ys = {str(y): _stats(v) for y, v in sorted(by_year.items())}
    return {
        "gross": _stats(gross),
        "net": _stats(net),
        "max_drawdown_compounded_net": _max_drawdown_simple(net),
        "positive_years_net": sum(1 for s in ys.values() if (s["mean"] or 0) > 0),
        "negative_years_net": sum(1 for s in ys.values() if (s["mean"] or 0) < 0),
        "years": ys,
    }


def run(path: Path) -> dict:
    bars = load_pre2025_m5(path)
    events = detect_events(bars)
    out = {
        "schema": 1,
        "study": "R18 economic gate v1.00",
        "source": str(path),
        "shock_threshold": SHOCK_THRESHOLD,
        "lookback_returns": LOOKBACK,
        "entry": "next_M5_open_after_shock_close",
        "horizons_bars": list(HORIZONS),
        "cost_scenarios_bps_all_in_round_trip": list(COST_BPS),
        "primary_cost_bps": PRIMARY_COST_BPS,
        "primary_horizons_bars": list(PRIMARY_HORIZONS),
        "pre_oos_2025_opened": False,
        "protected_2026_opened": False,
        "samples": {},
    }
    for sample in ("discovery", "confirmation"):
        se = [e for e in events if e["sample"] == sample]
        sample_out = {"event_count": len(se), "all_events": {}, "nonoverlap": {}}
        for h in HORIZONS:
            ne = select_nonoverlap(se, h)
            sample_out["all_events"][str(h)] = {
                str(cost): summarize(se, h, cost) for cost in COST_BPS
            }
            sample_out["nonoverlap"][str(h)] = {
                "selected_events": len(ne),
                "costs": {str(cost): summarize(ne, h, cost) for cost in COST_BPS},
            }
        out["samples"][sample] = sample_out

    checks = []
    for sample in ("discovery", "confirmation"):
        for h in PRIMARY_HORIZONS:
            s = out["samples"][sample]["nonoverlap"][str(h)]["costs"][str(PRIMARY_COST_BPS)]["net"]
            checks.append({
                "sample": sample,
                "horizon_bars": h,
                "net_mean": s["mean"],
                "pass": s["mean"] is not None and s["mean"] > 0,
            })
    out["primary_gate_checks"] = checks
    out["economic_gate_pass"] = all(c["pass"] for c in checks)

    # Break-even cost = gross mean * 10,000 bps for non-overlap execution.
    out["break_even_bps_nonoverlap"] = {}
    for sample in ("discovery", "confirmation"):
        out["break_even_bps_nonoverlap"][sample] = {}
        for h in HORIZONS:
            ne = select_nonoverlap([e for e in events if e["sample"] == sample], h)
            g = summarize(ne, h, 0.0)["gross"]["mean"]
            out["break_even_bps_nonoverlap"][sample][str(h)] = g * 10000.0 if g is not None else None
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    result = run(Path(args.input))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(out)

    print("R18 ECONOMIC GATE v1.00")
    print("2025 opened: false | 2026 opened: false")
    for sample in ("discovery", "confirmation"):
        print(f"\n===== {sample.upper()} =====")
        print(f"events={result['samples'][sample]['event_count']}")
        for h in HORIZONS:
            be = result["break_even_bps_nonoverlap"][sample][str(h)]
            block = result["samples"][sample]["nonoverlap"][str(h)]
            s0 = block["costs"]["0.0"]["gross"]
            s1 = block["costs"]["1.0"]["net"]
            print(
                f"{h:2d}b nonoverlap n={block['selected_events']:6d} "
                f"gross_mean={s0['mean']:+.8g} break_even={be:+.4f}bp "
                f"net@1bp={s1['mean']:+.8g} PF@1bp={s1['profit_factor']}"
            )
    print("\nPRIMARY GATE")
    for c in result["primary_gate_checks"]:
        print(f"{c['sample']:12s} {c['horizon_bars']}b net@1bp={c['net_mean']:+.8g} pass={c['pass']}")
    print(f"ECONOMIC_GATE_PASS={result['economic_gate_pass']}")
    print(f"output={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
