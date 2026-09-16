#!/usr/bin/env python3
"""R31: FundedNext RAW vs NEWS-CLEAN ablation for frozen R6B candidates."""
from __future__ import annotations

import argparse, hashlib, json, math, os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import strategy_factory_causal_next_open_v1_00 as r5
import r5_pre_oos_economic_robustness_v1_00 as econ
import r6_xau_low_turnover_breakout_v1_00 as r6

EXPECTED = {
    "xauusd_m1_2024_2025_raw.csv":"f98a395961b27ca9dcb34cffa4ef8dd93720adb70292abf7bc96108667232445",
    "xauusd_m5_2024_2025_raw.csv":"ba54c9b29755eac4284cb872805148736be529e954533c028e7f826bb444ce66",
    "xauusd_m5_2024_2025_news_clean.csv":"972ecaf6c3cadf7136363f396d7a29e7a6246646b575fad5c3e677036004b503",
}
CANDIDATES = {
    "R6B-347":{"candidate_id":"R6B-347","lookback_bars":96,"buffer_atr":0.1,"horizon_bars":96,"session_start":0,"session_end":8,"direction":1},
    "R6B-307":{"candidate_id":"R6B-307","lookback_bars":96,"buffer_atr":0.0,"horizon_bars":48,"session_start":0,"session_end":8,"direction":1},
}
INITIAL=10000.0


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


def load(path:Path, expected:str)->pd.DataFrame:
    if sha256(path)!=expected:
        raise RuntimeError(f"hash mismatch: {path.name}")
    meta=r5.detect(path)
    if not meta: raise RuntimeError(f"unreadable market file: {path}")
    df=r5.load_market(path,meta,2_000_000)
    years=set(int(x) for x in df.time.dt.year.unique())
    if not years.issubset({2024,2025}):
        raise RuntimeError(f"unexpected years in {path.name}: {years}")
    if (df.time>=pd.Timestamp("2026-01-01",tz="UTC")).any():
        raise RuntimeError("protected 2026 row present")
    return df


def capital(trades,profile,initial=INITIAL):
    eq=float(initial); peak=eq; dd=0.0
    for t in sorted(trades,key=lambda x:x["entry_time"]):
        r=float(t["profiles"][profile]["net"])/float(t["entry_open"])
        if not math.isfinite(r) or r<=-1: raise RuntimeError(f"invalid return {r}")
        eq*=1+r
        peak=max(peak,eq)
        dd=max(dd,(peak-eq)/peak)
    return {"initial":initial,"ending":eq,"return_pct":(eq/initial-1)*100,"max_dd_pct":dd*100,"trades":len(trades)}


def eval_variant(source_all,raw_all,rule):
    out={}; pooled=[]
    for year in (2024,2025):
        source=source_all[source_all.time.dt.year==year].reset_index(drop=True)
        raw=raw_all[raw_all.time.dt.year==year].reset_index(drop=True)
        ledger,accounting,metrics=r6.evaluate_year(rule,source,raw,year)
        pooled.extend(ledger)
        out[str(year)]={"accounting":accounting,"metrics":metrics,"capital":{p:capital(ledger,p) for p in econ.PROFILES}}
    out["pooled"]={"metrics":{p:econ.stats(pooled,p) for p in econ.PROFILES},"capital":{p:capital(pooled,p) for p in econ.PROFILES}}
    return out


def delta(clean,raw):
    out={}
    for scope in ("2024","2025","pooled"):
        out[scope]={}
        for p in econ.PROFILES:
            cm=clean[scope]["metrics"][p]; rm=raw[scope]["metrics"][p]
            cc=clean[scope]["capital"][p]; rc=raw[scope]["capital"][p]
            out[scope][p]={
                "trades_delta":int(cm["trades"])-int(rm["trades"]),
                "net_delta":float(cm["net"])-float(rm["net"]),
                "expectancy_delta":float(cm["expectancy"])-float(rm["expectancy"]) if cm["expectancy"] is not None and rm["expectancy"] is not None else None,
                "pf_delta":float(cm["PF"])-float(rm["PF"]) if cm["PF"] is not None and rm["PF"] is not None else None,
                "ending_capital_delta":float(cc["ending"])-float(rc["ending"]),
                "return_pct_delta":float(cc["return_pct"])-float(rc["return_pct"]),
            }
    return out


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--phase-ib-root",required=True,type=Path)
    ap.add_argument("--output-dir",required=True,type=Path)
    args=ap.parse_args()

    out=args.output_dir; out.mkdir(parents=True,exist_ok=True)
    result_path=out/"r31_r6b_raw_vs_news_clean_result.json"
    if result_path.exists(): raise RuntimeError("existing R31 result; refusing overwrite")

    root=args.phase_ib_root
    raw_m1=load(root/"xauusd_m1_2024_2025_raw.csv",EXPECTED["xauusd_m1_2024_2025_raw.csv"])
    raw_m5=load(root/"xauusd_m5_2024_2025_raw.csv",EXPECTED["xauusd_m5_2024_2025_raw.csv"])
    clean_m5=load(root/"xauusd_m5_2024_2025_news_clean.csv",EXPECTED["xauusd_m5_2024_2025_news_clean.csv"])

    result={
        "schema":1,"research":"R31","generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "protected_2026_opened":False,"retuning_performed":False,
        "inputs":EXPECTED,"candidates":{}
    }
    for cid,rule in CANDIDATES.items():
        raw=eval_variant(raw_m5,raw_m1,rule)
        clean=eval_variant(clean_m5,raw_m1,rule)
        result["candidates"][cid]={"definition":rule,"RAW":raw,"NEWS_CLEAN":clean,"delta_news_clean_minus_raw":delta(clean,raw)}

    atomic_json(result_path,result)
    summary={}
    for cid in CANDIDATES:
        summary[cid]={}
        for p in econ.PROFILES:
            r=result["candidates"][cid]
            summary[cid][p]={
                "raw_2024_net":r["RAW"]["2024"]["metrics"][p]["net"],
                "clean_2024_net":r["NEWS_CLEAN"]["2024"]["metrics"][p]["net"],
                "raw_2025_net":r["RAW"]["2025"]["metrics"][p]["net"],
                "clean_2025_net":r["NEWS_CLEAN"]["2025"]["metrics"][p]["net"],
                "raw_pooled_capital":r["RAW"]["pooled"]["capital"][p]["ending"],
                "clean_pooled_capital":r["NEWS_CLEAN"]["pooled"]["capital"][p]["ending"],
            }
    print(json.dumps({"status":"PASS","summary":summary,"protected_2026_opened":False},sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
