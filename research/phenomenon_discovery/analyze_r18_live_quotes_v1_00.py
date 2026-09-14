#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from bisect import bisect_left
from dataclasses import dataclass
from pathlib import Path

LOOKBACK = 48
THRESHOLD = 2.0
HORIZONS = (1, 2, 4, 8, 16)
M5 = 300
COMMISSION_RT_BPS = 0.14

@dataclass(frozen=True)
class Bar:
    epoch: int
    open: float
    high: float
    low: float
    close: float

@dataclass(frozen=True)
class Tick:
    time_msc: int
    bid: float
    ask: float

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) * 0.5

    @property
    def spread_bps(self) -> float:
        m = self.mid
        return (self.ask - self.bid) / m * 10000.0 if m > 0 else float("nan")


def load_bars(path: Path) -> list[Bar]:
    out=[]
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f)
        need={"bar_epoch","open","high","low","close"}
        miss=need-set(r.fieldnames or [])
        if miss: raise RuntimeError(f"missing bar columns: {sorted(miss)}")
        prev=None
        for row in r:
            e=int(row["bar_epoch"])
            if prev is not None and e<=prev: raise RuntimeError("non-increasing bar epochs")
            prev=e
            o,h,l,c=map(float,(row["open"],row["high"],row["low"],row["close"]))
            if not all(math.isfinite(x) and x>0 for x in (o,h,l,c)): raise RuntimeError(f"invalid OHLC at {e}")
            if h<max(o,c) or l>min(o,c) or h<l: raise RuntimeError(f"invalid OHLC geometry at {e}")
            out.append(Bar(e,o,h,l,c))
    return out


def load_ticks(path: Path) -> list[Tick]:
    out=[]
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f)
        need={"time_msc","bid","ask"}
        miss=need-set(r.fieldnames or [])
        if miss: raise RuntimeError(f"missing tick columns: {sorted(miss)}")
        prev=None
        for row in r:
            t=int(row["time_msc"]); bid=float(row["bid"]); ask=float(row["ask"])
            if prev is not None and t<prev: raise RuntimeError("decreasing tick timestamps")
            prev=t
            if bid<=0 or ask<=0 or ask<bid: continue
            out.append(Tick(t,bid,ask))
    return out


def first_tick_at_or_after(ticks:list[Tick], times:list[int], epoch_seconds:int) -> Tick|None:
    target=epoch_seconds*1000
    i=bisect_left(times,target)
    return ticks[i] if i<len(ticks) else None


def sample_sd(xs:list[float]) -> float:
    return statistics.stdev(xs)


def detect_events(bars:list[Bar]) -> list[dict]:
    events=[]
    for i in range(LOOKBACK+1,len(bars)):
        # Require exact continuity across shock and all 48 historical returns.
        ok=True
        for k in range(i-(LOOKBACK+1)+1,i+1):
            if bars[k].epoch-bars[k-1].epoch!=M5:
                ok=False; break
        if not ok: continue
        shock=bars[i].close/bars[i-1].close-1.0
        hist=[]
        for k in range(i-1,i-LOOKBACK-1,-1):
            hist.append(bars[k].close/bars[k-1].close-1.0)
        sd=sample_sd(hist)
        if sd<=0: continue
        score=abs(shock)/sd
        if score<THRESHOLD: continue
        events.append({"bar_index":i,"shock_epoch":bars[i].epoch,"shock_return":shock,"shock_score":score,"direction":1 if shock>0 else -1})
    return events


def signed_mid_return(is_long:bool, entry_mid:float, exit_mid:float)->float:
    return exit_mid/entry_mid-1.0 if is_long else 1.0-exit_mid/entry_mid


def signed_exec_return(is_long:bool, entry_exec:float, exit_exec:float)->float:
    return exit_exec/entry_exec-1.0 if is_long else 1.0-exit_exec/entry_exec


def stats(xs:list[float])->dict:
    if not xs: return {"n":0,"mean":None,"median":None,"p10":None,"p50":None,"p90":None}
    ys=sorted(xs)
    def q(p:float):
        if len(ys)==1:return ys[0]
        x=(len(ys)-1)*p; lo=int(math.floor(x)); hi=int(math.ceil(x));
        return ys[lo] if lo==hi else ys[lo]+(ys[hi]-ys[lo])*(x-lo)
    return {"n":len(xs),"mean":statistics.fmean(xs),"median":statistics.median(xs),"p10":q(.1),"p50":q(.5),"p90":q(.9)}


def run(bars_path:Path,ticks_path:Path)->dict:
    bars=load_bars(bars_path); ticks=load_ticks(ticks_path); times=[t.time_msc for t in ticks]
    events=detect_events(bars)
    rows=[]
    for e in events:
        i=e["bar_index"]
        entry_boundary=bars[i].epoch+M5
        entry_tick=first_tick_at_or_after(ticks,times,entry_boundary)
        if entry_tick is None: continue
        is_long=e["direction"]<0
        entry_exec=entry_tick.ask if is_long else entry_tick.bid
        for h in HORIZONS:
            exit_boundary=entry_boundary+h*M5
            exit_tick=first_tick_at_or_after(ticks,times,exit_boundary)
            if exit_tick is None: continue
            entry_mid=entry_tick.mid; exit_mid=exit_tick.mid
            exit_exec=exit_tick.bid if is_long else exit_tick.ask
            mid_r=signed_mid_return(is_long,entry_mid,exit_mid)
            exec_r=signed_exec_return(is_long,entry_exec,exit_exec)
            quote_friction=(mid_r-exec_r)*10000.0
            allin=quote_friction+COMMISSION_RT_BPS
            rows.append({
                "shock_epoch":e["shock_epoch"],"shock_score":e["shock_score"],"shock_return":e["shock_return"],
                "direction":"LONG" if is_long else "SHORT","horizon":h,
                "entry_time_msc":entry_tick.time_msc,"exit_time_msc":exit_tick.time_msc,
                "entry_spread_bps":entry_tick.spread_bps,"exit_spread_bps":exit_tick.spread_bps,
                "mid_return_bps":mid_r*10000.0,"exec_return_bps":exec_r*10000.0,
                "quote_friction_bps":quote_friction,"commission_rt_bps":COMMISSION_RT_BPS,
                "all_in_cost_bps":allin,
            })
    summary={}
    for h in HORIZONS:
        hr=[x for x in rows if x["horizon"]==h]
        summary[str(h)]={
            "events":len(hr),
            "entry_spread_bps":stats([x["entry_spread_bps"] for x in hr]),
            "exit_spread_bps":stats([x["exit_spread_bps"] for x in hr]),
            "quote_friction_bps":stats([x["quote_friction_bps"] for x in hr]),
            "all_in_cost_bps_including_0_14bp_commission":stats([x["all_in_cost_bps"] for x in hr]),
        }
    return {"schema":1,"study":"R18 live FTMO quote-cost analysis v1.00","lookback":LOOKBACK,"threshold":THRESHOLD,
            "horizons":list(HORIZONS),"commission_rt_bps":COMMISSION_RT_BPS,"event_count":len(events),"rows":rows,"summary":summary}


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--bars",required=True)
    ap.add_argument("--ticks",required=True)
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    result=run(Path(a.bars),Path(a.ticks))
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    tmp=out.with_suffix(out.suffix+".tmp")
    tmp.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"); tmp.replace(out)
    print(f"R18 events={result['event_count']}")
    for h in HORIZONS:
        s=result['summary'][str(h)]['all_in_cost_bps_including_0_14bp_commission']
        print(f"{h:2d}b n={s['n']:5d} all_in mean={s['mean']} bp median={s['median']} bp p90={s['p90']} bp")
    print(f"output={out}")
    return 0

if __name__=="__main__": raise SystemExit(main())
