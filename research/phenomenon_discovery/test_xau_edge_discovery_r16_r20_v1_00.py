#!/usr/bin/env python3
"""Cold-audit smoke tests for R16-R20 v1.00. No external framework required."""
from __future__ import annotations

import csv
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import xau_edge_discovery_r16_r20_v1_00 as batch


def write_csv(path: Path, start: datetime, bars: int) -> None:
    fields = ["symbol", "timeframe", "server_time", "server_epoch", "open", "high", "low", "close"]
    price = 2000.0
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for i in range(bars):
            dt = start + timedelta(minutes=5*i); epoch = int(dt.timestamp())
            move = .6 if i % 7 else -1.0; o = price; c = price + move
            w.writerow({"symbol":"XAUUSD","timeframe":"M5","server_time":dt.strftime("%Y.%m.%d %H:%M"),
                        "server_epoch":epoch,"open":o,"high":max(o,c)+.2,"low":min(o,c)-.2,"close":c})
            price = c


def test_frozen_stage_boundaries() -> None:
    assert batch._stage_accepts(date(2019, 6, 30), "discovery")
    assert not batch._stage_accepts(date(2019, 7, 1), "discovery")
    assert batch._stage_accepts(date(2019, 7, 1), "confirmation")
    assert batch._stage_accepts(date(2024, 12, 31), "confirmation")
    assert not batch._stage_accepts(date(2025, 1, 1), "confirmation")
    assert batch._stage_accepts(date(2025, 1, 1), "preoos")
    assert batch._stage_accepts(date(2025, 12, 31), "preoos")


def test_protected_2026_rejected(tmp: Path) -> None:
    p = tmp / "protected.csv"; write_csv(p, datetime(2026,1,2,tzinfo=timezone.utc), 10)
    try: batch.load_bars(p, "preoos")
    except RuntimeError as e: assert "PROTECTED 2026" in str(e)
    else: raise AssertionError("2026 was not rejected")


def test_forward_gap_rejected() -> None:
    B=batch.Bar
    a=B(0,datetime(2024,1,1,tzinfo=timezone.utc),"M5",100,101,99,100)
    b=B(600,datetime(2024,1,1,0,10,tzinfo=timezone.utc),"M5",100,102,99,101)
    assert batch.forward_return([a,b],0,1) is None


def test_dst_local_clock() -> None:
    B=batch.Bar
    winter=B(int(datetime(2024,1,15,8,tzinfo=timezone.utc).timestamp()),datetime(2024,1,15,8,tzinfo=timezone.utc),"M5",1,1,1,1)
    summer=B(int(datetime(2024,7,15,7,tzinfo=timezone.utc).timestamp()),datetime(2024,7,15,7,tzinfo=timezone.utc),"M5",1,1,1,1)
    assert winter.local_minute(batch.LONDON_TZ)==8*60
    assert summer.local_minute(batch.LONDON_TZ)==8*60


def test_round_math() -> None:
    assert batch._nearest_round(2037,10)==2040
    assert batch._nearest_round(2037,25)==2025
    assert batch._nearest_round(2037,50)==2050
    assert batch._nearest_round(2037,100)==2000


def test_r16_reversal_anchored_after_reentry() -> None:
    B=batch.Bar; start=datetime(2024,1,15,0,0,tzinfo=timezone.utc); bars=[]
    # Asian range 100..101 from 00:00 to 06:55 London.
    for n in range(84):
        dt=start+timedelta(minutes=5*n); bars.append(B(int(dt.timestamp()),dt,"M5",100.4,101,100,100.5))
    # Fill 07:00..07:55 inside range.
    for n in range(84,96):
        dt=start+timedelta(minutes=5*n); bars.append(B(int(dt.timestamp()),dt,"M5",100.5,100.8,100.2,100.5))
    # 08:00 breakout close, 08:05 continuation, 08:10 confirmed re-entry.
    vals=[(101.1,101.4,101.0,101.2),(101.2,101.6,101.1,101.5),(101.5,101.6,100.7,100.8),
          (100.8,100.9,100.4,100.5),(100.5,100.6,100.1,100.2)]
    for k,(o,h,l,c) in enumerate(vals):
        dt=start+timedelta(hours=8,minutes=5*k); bars.append(B(int(dt.timestamp()),dt,"M5",o,h,l,c))
    ev=batch.r16_asian_london(bars)
    assert len(ev)==1 and ev[0]["bars_to_reentry"]==2
    assert ev[0]["reentry_epoch"]==bars[98].epoch
    # 1-bar reversal is measured from 08:10 -> 08:15, not 08:00 -> 08:05.
    expected=-(bars[99].close/bars[98].close-1.0)
    assert abs(ev[0]["reversal_1b"]-expected)<1e-15


def main() -> int:
    with tempfile.TemporaryDirectory() as d: test_protected_2026_rejected(Path(d))
    test_frozen_stage_boundaries(); test_forward_gap_rejected(); test_dst_local_clock(); test_round_math()
    test_r16_reversal_anchored_after_reentry()
    print("PASS: R16-R20 cold-audit smoke tests")
    return 0


if __name__ == "__main__": raise SystemExit(main())
