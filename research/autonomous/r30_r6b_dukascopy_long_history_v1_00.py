#!/usr/bin/env python3
"""R30 long-history capital characterization for R6B-347 / R6B-307.

Source: canonical pinned Dukascopy XAUUSD BID yearly M1/M5 exports built by R30.
Rules are frozen R6 definitions. Each calendar year is replayed independently,
matching the original R6 year-isolation style. Capital is then compounded
chronologically across yearly ledgers at 1x notional exposure:
    equity *= 1 + (net_pnl_per_1_xau / entry_price)
No sizing optimization or leverage search.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import r5_pre_oos_economic_robustness_v1_00 as econ
import r6_xau_low_turnover_breakout_v1_00 as r6
import top2_xau_long_history_backtest_v1_00 as top2

INITIAL_CAPITAL = 10000.0
PINNED_INDEX_SHA256 = "d77fb76e5b5ee0600a488c331084e70972a8800a33ae59a957c1044dc39ef566"

CANDIDATES = {
    "R6B-347": {
        "candidate_id":"R6B-347",
        "lookback_bars":96,
        "buffer_atr":0.1,
        "horizon_bars":96,
        "session":"UTC00_08",
        "session_start":0,
        "session_end":8,
        "direction":1,
        "direction_name":"LONG",
    },
    "R6B-307": {
        "candidate_id":"R6B-307",
        "lookback_bars":96,
        "buffer_atr":0.0,
        "horizon_bars":48,
        "session":"UTC00_08",
        "session_start":0,
        "session_end":8,
        "direction":1,
        "direction_name":"LONG",
    },
}


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path,obj:dict) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    os.replace(tmp,path)


def heartbeat(path: Path|None,completed:int,total:int,stage:str,extra=None)->None:
    if path is None:return
    obj={"completed":int(completed),"total":int(total),"stage":stage,
         "updated_at_utc":datetime.now(timezone.utc).isoformat(),
         "protected_2026_opened":False}
    if extra:obj.update(extra)
    atomic_json(path,obj)


def load_year(path: Path, expected_sha: str, expected_rows: int, year: int, tf: str) -> pd.DataFrame:
    if sha256(path)!=expected_sha:
        raise RuntimeError(f"R30 {tf} {year} SHA256 mismatch")
    z=pd.read_csv(path)
    req={"server_epoch","open","high","low","close"}
    if not req.issubset(z.columns):
        raise RuntimeError(f"R30 {tf} {year} missing columns")
    if len(z)!=int(expected_rows):
        raise RuntimeError(f"R30 {tf} {year} row-count mismatch")
    t=pd.to_datetime(pd.to_numeric(z.server_epoch,errors="raise").astype("int64"),unit="s",utc=True)
    out=pd.DataFrame({
        "time":t,
        "open":pd.to_numeric(z.open,errors="raise"),
        "high":pd.to_numeric(z.high,errors="raise"),
        "low":pd.to_numeric(z.low,errors="raise"),
        "close":pd.to_numeric(z.close,errors="raise"),
    })
    if out.empty or not out.time.is_monotonic_increasing or out.time.duplicated().any():
        raise RuntimeError(f"R30 {tf} {year} invalid time sequence")
    if (out.time.dt.year!=year).any():
        raise RuntimeError(f"R30 {tf} {year} contains other calendar years")
    if (out.time>=pd.Timestamp("2026-01-01",tz="UTC")).any():
        raise RuntimeError("protected 2026+ row encountered")
    return out


def signal(rule:dict,source:pd.DataFrame)->np.ndarray:
    atr=r6.atr14(source)
    return r6.breakout_signal(
        source,atr,
        int(rule["lookback_bars"]),
        float(rule["buffer_atr"]),
        int(rule["direction"]),
        int(rule["session_start"]),
        int(rule["session_end"]),
    )


def capital_path(trades:list[dict],profile:str,initial:float=INITIAL_CAPITAL)->dict:
    equity=float(initial)
    peak=equity
    max_dd=0.0
    curve=[{"time":None,"equity":equity}]
    returns=[]
    for t in sorted(trades,key=lambda x:x["entry_time"]):
        entry=float(t["entry_open"])
        net=float(t["profiles"][profile]["net"])
        r=net/entry
        if not math.isfinite(r) or r<=-1:
            raise RuntimeError(f"invalid 1x trade return {r}")
        equity*=1.0+r
        returns.append(r)
        peak=max(peak,equity)
        max_dd=max(max_dd,(peak-equity)/peak)
        curve.append({"time":t["exit_time"],"equity":equity})
    return {
        "initial_capital":float(initial),
        "ending_capital":float(equity),
        "return_pct":float((equity/initial-1.0)*100.0),
        "max_drawdown_trade_close_pct":float(max_dd*100.0),
        "trades":len(trades),
        "mean_trade_return_pct":float(np.mean(returns)*100.0) if returns else None,
        "median_trade_return_pct":float(np.median(returns)*100.0) if returns else None,
        "curve":curve,
    }


def cagr(initial:float,final:float,start:pd.Timestamp,end:pd.Timestamp)->float|None:
    if initial<=0 or final<=0 or end<=start:return None
    years=(end-start).total_seconds()/(365.2425*86400.0)
    if years<=0:return None
    return float(((final/initial)**(1.0/years)-1.0)*100.0)


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",required=True,type=Path)
    ap.add_argument("--output-dir",required=True,type=Path)
    ap.add_argument("--progress-file",type=Path)
    args=ap.parse_args()

    manifest=json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("status")!="PASS" or manifest.get("research")!="R30":
        raise RuntimeError("R30 build manifest not PASS")
    if manifest.get("source_index_sha256")!=PINNED_INDEX_SHA256:
        raise RuntimeError("R30 manifest source-index pin mismatch")
    if manifest.get("protected_2026_opened") is not False:
        raise RuntimeError("R30 build touched protected 2026")

    out=args.output_dir
    out.mkdir(parents=True,exist_ok=True)
    result_path=out/"r30_r6b_dukascopy_long_history_result.json"
    yearly_path=out/"r30_r6b_dukascopy_yearly.csv"
    capital_path_csv=out/"r30_r6b_dukascopy_capital_curve.csv"
    if result_path.exists():
        raise RuntimeError("existing R30 result detected; refusing overwrite")

    years=sorted(int(y) for y in manifest["yearly"])
    if years[0]!=2004 or years[-1]!=2025:
        raise RuntimeError(f"unexpected R30 year span: {years[0]}..{years[-1]}")

    heartbeat(args.progress_file,0,len(years)*2,"start")
    ledgers={cid:[] for cid in CANDIDATES}
    yearly_rows=[]
    annual_by_candidate={cid:{} for cid in CANDIDATES}

    step=0
    first_market_time=None
    last_market_time=None

    for year in years:
        rec=manifest["yearly"][str(year)]
        m5=load_year(Path(rec["m5_path"]),rec["m5_sha256"],rec["m5_rows"],year,"M5")
        m1=load_year(Path(rec["m1_path"]),rec["m1_sha256"],rec["m1_rows"],year,"M1")
        if first_market_time is None:first_market_time=m1.time.iloc[0]
        last_market_time=m1.time.iloc[-1]
        start=pd.Timestamp(f"{year}-01-01",tz="UTC")
        end=pd.Timestamp(f"{year+1}-01-01",tz="UTC")

        for cid,rule in CANDIDATES.items():
            sig=signal(rule,m5)
            ledger,accounting=top2.replay_window(
                m5,m1,sig,int(rule["horizon_bars"]),int(rule["direction"]),start,end
            )
            ledgers[cid].extend(ledger)
            annual_by_candidate[cid][str(year)]={
                "partial_year":bool(year==2004),
                "source_m1_rows":len(m1),
                "source_m5_rows":len(m5),
                "signal_accounting":accounting,
                "E1":econ.stats(ledger,"E1"),
                "STRESS":econ.stats(ledger,"STRESS"),
            }
            for profile in ("E1","STRESS"):
                m=annual_by_candidate[cid][str(year)][profile]
                yearly_rows.append({
                    "candidate_id":cid,"year":year,"partial_year":year==2004,
                    "profile":profile,**m
                })
            step+=1
            heartbeat(args.progress_file,step,len(years)*2,"replay_year",
                      {"year":year,"candidate_id":cid,"trades":len(ledger)})

    result={
        "schema":1,
        "research":"R30",
        "stage":"dukascopy_long_history_capital_characterization",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "source":"R15 pinned Dukascopy XAUUSD BID raw M1/M5",
        "source_index_sha256":PINNED_INDEX_SHA256,
        "market_start":pd.Timestamp(first_market_time).isoformat(),
        "market_end":pd.Timestamp(last_market_time).isoformat(),
        "years":years,
        "initial_capital":INITIAL_CAPITAL,
        "capital_model":"1x notional, compounded trade-by-trade using net/entry_open",
        "year_isolation":True,
        "news_filter":"NONE on Dukascopy long history",
        "protected_2026_opened":False,
        "retuning_performed":False,
        "candidates":{},
    }
    curve_rows=[]

    for cid,rule in CANDIDATES.items():
        trades=sorted(ledgers[cid],key=lambda x:x["entry_time"])
        rec={"definition":rule,"yearly":annual_by_candidate[cid],"full":{}}
        for profile in ("E1","STRESS"):
            metrics=econ.stats(trades,profile)
            cp=capital_path(trades,profile,INITIAL_CAPITAL)
            cp["cagr_pct"]=cagr(
                INITIAL_CAPITAL,cp["ending_capital"],
                pd.Timestamp(first_market_time),pd.Timestamp(last_market_time)
            )
            annual_equity=[]
            equity=INITIAL_CAPITAL
            peak=equity
            full_year_positive=0
            for year in years:
                ytr=[t for t in trades if pd.Timestamp(t["entry_time"]).year==year]
                start_eq=equity
                local_peak=equity
                local_maxdd=0.0
                for t in ytr:
                    r=float(t["profiles"][profile]["net"])/float(t["entry_open"])
                    equity*=1+r
                    peak=max(peak,equity)
                    local_peak=max(local_peak,equity)
                    local_maxdd=max(local_maxdd,(local_peak-equity)/local_peak)
                    curve_rows.append({
                        "candidate_id":cid,"profile":profile,
                        "time":t["exit_time"],"equity":equity,
                        "year":year
                    })
                yret=(equity/start_eq-1)*100 if start_eq else None
                if year>=2005 and yret is not None and yret>0:full_year_positive+=1
                annual_equity.append({
                    "year":year,
                    "partial_year":year==2004,
                    "start_equity":start_eq,
                    "end_equity":equity,
                    "return_pct":yret,
                    "max_drawdown_trade_close_pct":local_maxdd*100,
                    "trades":len(ytr),
                })
            cp["annual_capital"]=annual_equity
            cp["positive_full_years_2005_2025"]=full_year_positive
            cp["full_year_count_2005_2025"]=21
            rec["full"][profile]={"trade_metrics":metrics,"capital":cp}
        result["candidates"][cid]=rec

    atomic_json(result_path,result)
    pd.DataFrame(yearly_rows).to_csv(yearly_path,index=False)
    pd.DataFrame(curve_rows).to_csv(capital_path_csv,index=False)
    heartbeat(args.progress_file,len(years)*2,len(years)*2,"complete",
              {"result":str(result_path),"protected_2026_opened":False})

    summary={}
    for cid in CANDIDATES:
        summary[cid]={}
        for p in ("E1","STRESS"):
            cp=result["candidates"][cid]["full"][p]["capital"]
            summary[cid][p]={
                "ending_capital":cp["ending_capital"],
                "return_pct":cp["return_pct"],
                "cagr_pct":cp["cagr_pct"],
                "max_dd_pct":cp["max_drawdown_trade_close_pct"],
                "trades":cp["trades"],
                "positive_full_years":cp["positive_full_years_2005_2025"],
            }
    print(json.dumps({"status":"PASS","summary":summary,"protected_2026_opened":False},sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
