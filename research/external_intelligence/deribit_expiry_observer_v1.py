#!/usr/bin/env python3
"""Deribit BTC 0DTE expiry open-interest observer — Guardian Banger Lab V1.

READ-ONLY. No authentication. No trading. Standard library only.

Run once daily near 07:00 UTC (recommended 06:55-07:05):
    python deribit_expiry_observer_v1.py --outdir D:\\MT5_Backtests\\external\\deribit_expiry

It stores one canonical daily snapshot and computes a point-in-time expanding
90th percentile using PRIOR days only. Warm-up is 30 prior observations.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://www.deribit.com/api/v2/public"
ATM_BAND = 0.025
WARMUP_DAYS = 30


def api(method: str, **params: Any) -> Any:
    url = f"{BASE}/{method}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "GuardianResearch-DeribitExpiryObserver/1.0"})
    with urlopen(req, timeout=20) as r:
        payload = json.loads(r.read().decode("utf-8"))
    if "error" in payload:
        raise RuntimeError(f"Deribit {method}: {payload['error']}")
    return payload["result"]


def qtile(values: list[float], q: float) -> float:
    if not values:
        return math.nan
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo = int(math.floor(pos)); hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    w = pos - lo
    return xs[lo] * (1 - w) + xs[hi] * w


@dataclass
class Snapshot:
    date_utc: str
    captured_at_utc: str
    expiry_utc: str
    index_price: float
    atm_band_pct: float
    option_count_0dte: int
    atm_option_count: int
    total_0dte_oi: float
    atm_oi: float
    prior_days_n: int
    prior_p90_atm_oi: float | None
    signal_state: str


def build_snapshot(now: datetime, index_price: float, instruments: list[dict], summaries: list[dict], prior_oi: list[float]) -> Snapshot:
    active = [x for x in instruments if x.get("kind") == "option" and x.get("is_active", True)]
    expiries = sorted({int(x["expiration_timestamp"]) for x in active if int(x["expiration_timestamp"]) > int(now.timestamp() * 1000)})
    if not expiries:
        raise RuntimeError("No future BTC option expiry returned by Deribit")
    exp_ms = expiries[0]
    exp_dt = datetime.fromtimestamp(exp_ms / 1000, tz=timezone.utc)
    if exp_dt.date() != now.date():
        raise RuntimeError(f"Nearest BTC option expiry is not today: {exp_dt.isoformat()}")

    exp_names = {x["instrument_name"] for x in active if int(x["expiration_timestamp"]) == exp_ms}
    meta = {x["instrument_name"]: x for x in active if x["instrument_name"] in exp_names}
    smap = {x["instrument_name"]: x for x in summaries if x.get("instrument_name") in exp_names}

    atm_names = set()
    for name, x in meta.items():
        strike = float(x.get("strike", 0.0) or 0.0)
        if index_price > 0 and abs(strike / index_price - 1.0) <= ATM_BAND + 1e-12:
            atm_names.add(name)

    total_oi = sum(float(smap[n].get("open_interest", 0.0) or 0.0) for n in exp_names if n in smap)
    atm_oi = sum(float(smap[n].get("open_interest", 0.0) or 0.0) for n in atm_names if n in smap)

    p90 = qtile(prior_oi, 0.90) if len(prior_oi) >= WARMUP_DAYS else math.nan
    if len(prior_oi) < WARMUP_DAYS:
        state = "WARMUP"
        p90_out = None
    else:
        state = "HIGH_OI" if atm_oi >= p90 else "NORMAL_OI"
        p90_out = round(p90, 10)

    return Snapshot(
        date_utc=now.date().isoformat(),
        captured_at_utc=now.isoformat(),
        expiry_utc=exp_dt.isoformat(),
        index_price=round(index_price, 10),
        atm_band_pct=ATM_BAND * 100,
        option_count_0dte=len(exp_names),
        atm_option_count=len(atm_names),
        total_0dte_oi=round(total_oi, 10),
        atm_oi=round(atm_oi, 10),
        prior_days_n=len(prior_oi),
        prior_p90_atm_oi=p90_out,
        signal_state=state,
    )


def read_daily(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", newline="", encoding="utf-8") as f:
        return {row["date_utc"]: row for row in csv.DictReader(f)}


def write_daily(path: Path, rows: dict[str, dict[str, Any]]) -> None:
    fields = list(asdict(Snapshot("","","",0,0,0,0,0,0,0,None,"")).keys())
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for d in sorted(rows):
            w.writerow(rows[d])
    tmp.replace(path)


def self_test() -> None:
    now = datetime(2026, 9, 6, 7, 0, tzinfo=timezone.utc)
    exp_ms = int(datetime(2026, 9, 6, 8, 0, tzinfo=timezone.utc).timestamp() * 1000)
    instruments = [
        {"kind":"option","is_active":True,"expiration_timestamp":exp_ms,"instrument_name":"A","strike":100000},
        {"kind":"option","is_active":True,"expiration_timestamp":exp_ms,"instrument_name":"B","strike":102500},
        {"kind":"option","is_active":True,"expiration_timestamp":exp_ms,"instrument_name":"C","strike":110000},
    ]
    summaries = [
        {"instrument_name":"A","open_interest":10},
        {"instrument_name":"B","open_interest":20},
        {"instrument_name":"C","open_interest":100},
    ]
    prior = [float(i) for i in range(1, 31)]
    s = build_snapshot(now, 100000.0, instruments, summaries, prior)
    assert s.atm_option_count == 2, s
    assert s.atm_oi == 30.0, s
    assert s.signal_state == "HIGH_OI", s
    assert qtile([1,2,3,4,5], .5) == 3
    print("SELF_TEST_PASS", json.dumps(asdict(s), indent=2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test(); return 0

    now = datetime.now(timezone.utc)
    out = Path(args.outdir); out.mkdir(parents=True, exist_ok=True)
    daily_path = out / "DERIBIT_BTC_0DTE_DAILY.csv"
    rows = read_daily(daily_path)
    prior_oi = []
    for d, row in rows.items():
        if d < now.date().isoformat():
            try:
                prior_oi.append(float(row["atm_oi"]))
            except Exception:
                pass

    idx = api("get_index_price", index_name="btc_usd")
    instruments = api("get_instruments", currency="BTC", kind="option", expired="false")
    summaries = api("get_book_summary_by_currency", currency="BTC", kind="option")
    snap = build_snapshot(now, float(idx["index_price"]), instruments, summaries, prior_oi)
    row = asdict(snap)
    rows[snap.date_utc] = row
    write_daily(daily_path, rows)

    clock_min = now.hour * 60 + now.minute
    clock_ok = (6 * 60 + 55) <= clock_min <= (7 * 60 + 5)
    signal = dict(row)
    signal["clock_window_ok"] = clock_ok
    signal["research_eligible"] = bool(clock_ok and snap.signal_state in {"HIGH_OI", "NORMAL_OI"})
    signal_path = out / "DERIBIT_BTC_0DTE_SIGNAL.json"
    signal_path.write_text(json.dumps(signal, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(signal, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
