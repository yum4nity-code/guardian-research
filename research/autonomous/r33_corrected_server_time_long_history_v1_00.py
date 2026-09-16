#!/usr/bin/env python3
"""R33: corrected FundedNext-server-time Dukascopy long history for R6B."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import r5_pre_oos_economic_robustness_v1_00 as econ
import r6_xau_low_turnover_breakout_v1_00 as r6
import top2_xau_long_history_backtest_v1_00 as top2

INITIAL_CAPITAL=10000.0
R15_INDEX_SHA="d77fb76e5b5ee0600a488c331084e70972a8800a33ae59a957c1044dc39ef566"
R31_SHA="46120b2f3fe648058c2560ead475d2471279fa7ef1ea08d4ff8594a1c52ef368"
NY=ZoneInfo("America/New_York")

CANDIDATES={
    "R6B-347":{"candidate_id":"R6B-347","lookback_bars":96,"buffer_atr":0.1,"horizon_bars":96,"session_start":0,"session_end":8,"direction":1,"direction_name":"LONG"},
    "R6B-307":{"candidate_id":"R6B-307","lookback_bars":96,"buffer_atr":0.0,"horizon_bars":48,"session_start":0,"session_end":8,"direction":1,"direction_name":"LONG"},
}


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()


def atomic_json(path:Path,obj)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    os.replace(tmp,path)


def heartbeat(path:Path|None,done:int,total:int,stage:str,extra=None)->None:
    if path is None:return
    obj={"completed":int(done),"total":int(total),"stage":stage,
         "updated_at_utc":datetime.now(timezone.utc).isoformat(),
         "protected_2026_opened":False}
    if extra:obj.update(extra)
    atomic_json(path,obj)


_DST_CACHE={}


def dst_bounds_utc(year:int):
    """Return [first DST UTC hour, first post-DST UTC hour) for New York."""
    if year in _DST_CACHE:return _DST_CACHE[year]
    start=datetime(year,1,1,tzinfo=timezone.utc)
    end=datetime(year+1,1,1,tzinfo=timezone.utc)
    prev=False
    dst_start=None
    dst_end=None
    t=start
    while t<end:
        cur=bool(t.astimezone(NY).dst())
        if cur and not prev and dst_start is None:
            dst_start=t
        if prev and not cur and dst_start is not None:
            dst_end=t
            break
        prev=cur
        t+=timedelta(hours=1)
    if dst_start is None or dst_end is None:
        raise RuntimeError(f"cannot determine New York DST bounds for {year}")
    _DST_CACHE[year]=(dst_start,dst_end)
    return _DST_CACHE[year]


def server_offset_hours_for_utc(dt:pd.Timestamp)->int:
    py=dt.to_pydatetime()
    return 3 if bool(py.astimezone(NY).dst()) else 2


def to_server_coordinate(df:pd.DataFrame)->pd.DataFrame:
    x=df.copy()
    ns=x.time.array.as_unit("ns").asi8.copy()
    years=x.time.dt.year.to_numpy(int)
    offsets=np.full(len(x),2,dtype=np.int64)
    for year in np.unique(years):
        a,b=dst_bounds_utc(int(year))
        a_ns=int(pd.Timestamp(a).value); b_ns=int(pd.Timestamp(b).value)
        mask=(years==year)&(ns>=a_ns)&(ns<b_ns)
        offsets[mask]=3
    x["time"]=pd.to_datetime(ns+offsets*3600*1_000_000_000,unit="ns",utc=True)
    return x


def load_year(manifest:dict,year:int,tf:str)->pd.DataFrame:
    rec=manifest["yearly"][str(year)]
    key=tf.lower()
    p=Path(rec[f"{key}_path"])
    if sha256(p)!=rec[f"{key}_sha256"]:
        raise RuntimeError(f"{tf} {year} hash mismatch")
    z=pd.read_csv(p,usecols=["server_epoch","open","high","low","close"])
    if len(z)!=int(rec[f"{key}_rows"]):
        raise RuntimeError(f"{tf} {year} row mismatch")
    t=pd.to_datetime(pd.to_numeric(z.server_epoch,errors="raise").astype("int64"),unit="s",utc=True)
    out=pd.DataFrame({
        "time":t,
        "open":pd.to_numeric(z.open,errors="raise"),
        "high":pd.to_numeric(z.high,errors="raise"),
        "low":pd.to_numeric(z.low,errors="raise"),
        "close":pd.to_numeric(z.close,errors="raise"),
    })
    if (out.time.dt.year!=year).any():raise RuntimeError(f"{tf} year mismatch {year}")
    if (out.time>=pd.Timestamp("2026-01-01",tz="UTC")).any():raise RuntimeError("protected 2026 row")
    return to_server_coordinate(out)


def capital(trades,profile,initial=INITIAL_CAPITAL):
    eq=float(initial); peak=eq; dd=0.0
    for t in sorted(trades,key=lambda x:x["entry_time"]):
        r=float(t["profiles"][profile]["net"])/float(t["entry_open"])
        if not math.isfinite(r) or r<=-1:raise RuntimeError(f"invalid trade return {r}")
        eq*=1+r
        peak=max(peak,eq)
        dd=max(dd,(peak-eq)/peak)
    return {"initial_capital":initial,"ending_capital":eq,"return_pct":(eq/initial-1)*100,
            "max_drawdown_trade_close_pct":dd*100,"trades":len(trades)}


def cagr(initial,final,start,end):
    years=(end-start).total_seconds()/(365.2425*86400.0)
    if initial<=0 or final<=0 or years<=0:return None
    return ((final/initial)**(1/years)-1)*100


def signal(rule,source):
    atr=r6.atr14(source)
    return r6.breakout_signal(source,atr,rule["lookback_bars"],rule["buffer_atr"],rule["direction"],rule["session_start"],rule["session_end"])


def select_server_year(parts:list[pd.DataFrame],year:int)->pd.DataFrame:
    x=pd.concat(parts,ignore_index=True).sort_values("time").drop_duplicates("time").reset_index(drop=True)
    a=pd.Timestamp(f"{year}-01-01",tz="UTC"); b=pd.Timestamp(f"{year+1}-01-01",tz="UTC")
    return x[(x.time>=a)&(x.time<b)].reset_index(drop=True)


def compare_overlap(metrics,cap,r31,cid,year,profile):
    ref=r31["candidates"][cid]["RAW"][str(year)]
    rm=ref["metrics"][profile]; rc=ref["capital"][profile]
    return {
        "dukascopy_corrected":{"trades":metrics["trades"],"net":metrics["net"],"expectancy_bps":metrics["expectancy_bps"],"PF":metrics["PF"],"ending_capital":cap["ending_capital"]},
        "fundednext_raw":{"trades":rm["trades"],"net":rm["net"],"expectancy_bps":rm["expectancy_bps"],"PF":rm["PF"],"ending_capital":rc["ending"]},
        "delta_duk_minus_fn":{
            "trades":int(metrics["trades"])-int(rm["trades"]),
            "net":float(metrics["net"])-float(rm["net"]),
            "expectancy_bps":float(metrics["expectancy_bps"])-float(rm["expectancy_bps"]),
            "PF":(float(metrics["PF"])-float(rm["PF"])) if metrics["PF"] is not None and rm["PF"] is not None else None,
            "ending_capital":float(cap["ending_capital"])-float(rc["ending"]),
        }
    }


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--r30-manifest",required=True,type=Path)
    ap.add_argument("--r31-result",required=True,type=Path)
    ap.add_argument("--output-dir",required=True,type=Path)
    ap.add_argument("--progress-file",type=Path)
    args=ap.parse_args()

    out=args.output_dir; out.mkdir(parents=True,exist_ok=True)
    rp=out/"r33_corrected_server_time_long_history_result.json"
    yp=out/"r33_corrected_server_time_yearly.csv"
    if rp.exists():raise RuntimeError("existing R33 result; refusing overwrite")

    manifest=json.loads(args.r30_manifest.read_text(encoding="utf-8"))
    if manifest.get("status")!="PASS" or manifest.get("source_index_sha256")!=R15_INDEX_SHA or manifest.get("protected_2026_opened") is not False:
        raise RuntimeError("R30 manifest provenance mismatch")
    if sha256(args.r31_result)!=R31_SHA:raise RuntimeError("R31 result SHA mismatch")
    r31=json.loads(args.r31_result.read_text(encoding="utf-8"))

    years=sorted(int(y) for y in manifest["yearly"])
    if years[0]!=2004 or years[-1]!=2025:raise RuntimeError("unexpected year span")

    ledgers={cid:[] for cid in CANDIDATES}
    yearly={cid:{} for cid in CANDIDATES}
    rows=[]
    cache_m1={}; cache_m5={}
    step=0; total=len(years)*2
    first_time=None; last_time=None

    for year in years:
        need=[y for y in (year-1,year) if str(y) in manifest["yearly"]]
        for y in need:
            if y not in cache_m1:cache_m1[y]=load_year(manifest,y,"M1")
            if y not in cache_m5:cache_m5[y]=load_year(manifest,y,"M5")
        source=select_server_year([cache_m5[y] for y in need],year)
        raw=select_server_year([cache_m1[y] for y in need],year)
        if source.empty or raw.empty:raise RuntimeError(f"empty synthetic server year {year}")
        if first_time is None:first_time=raw.time.iloc[0]
        last_time=raw.time.iloc[-1]
        a=pd.Timestamp(f"{year}-01-01",tz="UTC"); b=pd.Timestamp(f"{year+1}-01-01",tz="UTC")

        for cid,rule in CANDIDATES.items():
            sig=signal(rule,source)
            ledger,accounting=top2.replay_window(source,raw,sig,rule["horizon_bars"],rule["direction"],a,b)
            ledgers[cid].extend(ledger)
            yearly[cid][str(year)]={"partial_year":year==2004,"accounting":accounting,
                                    "E1":econ.stats(ledger,"E1"),"STRESS":econ.stats(ledger,"STRESS")}
            for p in ("E1","STRESS"):
                rows.append({"candidate_id":cid,"year":year,"profile":p,**yearly[cid][str(year)][p]})
            step+=1
            heartbeat(args.progress_file,step,total,"replay_corrected_server_year",{"year":year,"candidate_id":cid,"trades":len(ledger)})

        for old in list(cache_m1):
            if old<year-1:
                cache_m1.pop(old,None); cache_m5.pop(old,None)

    result={
        "schema":1,"research":"R33","generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "clock_model":"FundedNext synthetic server coordinate: UTC+3 when America/New_York DST active, else UTC+2",
        "r15_source_index_sha256":R15_INDEX_SHA,"r31_result_sha256":R31_SHA,
        "protected_2026_opened":False,"retuning_performed":False,
        "market_start_server_coordinate":pd.Timestamp(first_time).isoformat(),
        "market_end_server_coordinate":pd.Timestamp(last_time).isoformat(),
        "initial_capital":INITIAL_CAPITAL,"candidates":{}
    }
    overlap={}
    for cid,rule in CANDIDATES.items():
        trades=sorted(ledgers[cid],key=lambda x:x["entry_time"])
        rec={"definition":rule,"yearly":yearly[cid],"full":{},"overlap_vs_fundednext_raw":{}}
        for p in ("E1","STRESS"):
            met=econ.stats(trades,p); cp=capital(trades,p)
            cp["cagr_pct"]=cagr(INITIAL_CAPITAL,cp["ending_capital"],pd.Timestamp(first_time),pd.Timestamp(last_time))
            annual=[]; eq=INITIAL_CAPITAL; pos=0
            for y in years:
                ytr=[t for t in trades if pd.Timestamp(t["entry_time"]).year==y]
                start_eq=eq; peak=eq; ydd=0.0
                for t in ytr:
                    rr=float(t["profiles"][p]["net"])/float(t["entry_open"])
                    eq*=1+rr; peak=max(peak,eq); ydd=max(ydd,(peak-eq)/peak)
                yret=(eq/start_eq-1)*100
                if y>=2005 and yret>0:pos+=1
                annual.append({"year":y,"partial_year":y==2004,"start_equity":start_eq,"end_equity":eq,
                               "return_pct":yret,"max_drawdown_trade_close_pct":ydd*100,"trades":len(ytr)})
            cp["annual_capital"]=annual; cp["positive_full_years_2005_2025"]=pos; cp["full_year_count_2005_2025"]=21
            rec["full"][p]={"trade_metrics":met,"capital":cp}
            for y in (2024,2025):
                ym=yearly[cid][str(y)][p]
                ytr=[t for t in trades if pd.Timestamp(t["entry_time"]).year==y]
                ycap=capital(ytr,p)
                rec["overlap_vs_fundednext_raw"].setdefault(str(y),{})[p]=compare_overlap(ym,ycap,r31,cid,y,p)
        result["candidates"][cid]=rec

    atomic_json(rp,result)
    pd.DataFrame(rows).to_csv(yp,index=False)
    heartbeat(args.progress_file,total,total,"complete",{"protected_2026_opened":False})

    summary={}
    for cid in CANDIDATES:
        summary[cid]={}
        for p in ("E1","STRESS"):
            cp=result["candidates"][cid]["full"][p]["capital"]
            summary[cid][p]={"ending_capital":cp["ending_capital"],"return_pct":cp["return_pct"],"cagr_pct":cp["cagr_pct"],
                             "max_dd_pct":cp["max_drawdown_trade_close_pct"],"trades":cp["trades"],
                             "positive_full_years":cp["positive_full_years_2005_2025"]}
        summary[cid]["overlap_2024_E1"]=result["candidates"][cid]["overlap_vs_fundednext_raw"]["2024"]["E1"]
        summary[cid]["overlap_2025_E1"]=result["candidates"][cid]["overlap_vs_fundednext_raw"]["2025"]["E1"]
    print(json.dumps({"status":"PASS","summary":summary,"protected_2026_opened":False},sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
