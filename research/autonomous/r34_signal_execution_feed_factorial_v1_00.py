#!/usr/bin/env python3
"""R34: frozen 2x2 signal-feed/execution-feed diagnostic for R6B-347."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import r5_pre_oos_economic_robustness_v1_00 as econ
import r6_xau_low_turnover_breakout_v1_00 as r6
import r31_r6b_raw_vs_news_clean_v1_00 as r31
import r33_corrected_server_time_long_history_v1_00 as r33
import strategy_factory_causal_next_open_v1_00 as r5
import top2_xau_long_history_backtest_v1_00 as top2

YEARS=(2024,2025)
PROTECTED=pd.Timestamp("2026-01-01T00:00:00Z")
R15_INDEX_SHA=r33.R15_INDEX_SHA
R30_MANIFEST_SHA="7e4c7139f66cff7c20bd9c75de0a824bf7a38672baa1d58882717df1526c5d8d"
RULE={"candidate_id":"R6B-347","lookback_bars":96,"buffer_atr":0.1,"horizon_bars":96,
      "session_start":0,"session_end":8,"direction":1,"direction_name":"LONG"}
CELLS=(
    ("FN_SIGNAL__FN_EXECUTION","FN","FN"),
    ("FN_SIGNAL__DUKA_EXECUTION","FN","DUKA"),
    ("DUKA_SIGNAL__FN_EXECUTION","DUKA","FN"),
    ("DUKA_SIGNAL__DUKA_EXECUTION","DUKA","DUKA"),
)


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()


def atomic_json(path:Path,obj)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    os.replace(tmp,path)


def assert_frozen_rule()->None:
    expected={"candidate_id":"R6B-347","lookback_bars":96,"buffer_atr":0.1,"horizon_bars":96,
              "session_start":0,"session_end":8,"direction":1,"direction_name":"LONG"}
    if RULE!=expected:raise RuntimeError("R6B-347 frozen definition changed")
    upstream=r33.CANDIDATES["R6B-347"]
    for key,value in expected.items():
        if key in upstream and upstream[key]!=value:
            raise RuntimeError(f"R6B-347 differs from R33: {key}")


def validate_years(df:pd.DataFrame,label:str, *, coordinate_shifted:bool=False)->None:
    if df.empty:raise RuntimeError(f"empty dataset: {label}")
    years=set(int(v) for v in df.time.dt.year.unique())
    if not years.issubset(set(YEARS)):
        raise RuntimeError(f"unexpected years in {label}: {sorted(years)}")
    if not coordinate_shifted and (df.time>=PROTECTED).any():
        raise RuntimeError(f"protected 2026 row in {label}")


def load_fn(path:Path,expected_sha:str)->pd.DataFrame:
    if sha256(path)!=expected_sha:raise RuntimeError(f"FundedNext hash mismatch: {path.name}")
    meta=r5.detect(path)
    if not meta:raise RuntimeError(f"cannot detect FundedNext file: {path}")
    df=r5.load_market(path,meta,2_000_000)
    validate_years(df,path.name)
    return df[["time","open","high","low","close"]].copy()


def load_duka_utc_year(manifest:dict,year:int,tf:str)->pd.DataFrame:
    rec=manifest["yearly"][str(year)];key=tf.lower();path=Path(rec[f"{key}_path"])
    if sha256(path)!=rec[f"{key}_sha256"]:raise RuntimeError(f"Dukascopy {tf} {year} hash mismatch")
    raw=pd.read_csv(path,usecols=["server_epoch","open","high","low","close"])
    if len(raw)!=int(rec[f"{key}_rows"]):raise RuntimeError(f"Dukascopy {tf} {year} row mismatch")
    utc=pd.to_datetime(pd.to_numeric(raw.server_epoch,errors="raise").astype("int64"),unit="s",utc=True)
    if (utc>=PROTECTED).any() or (utc.dt.year!=year).any():raise RuntimeError(f"Dukascopy {tf} protected/unexpected year")
    df=pd.DataFrame({"time":utc,"open":pd.to_numeric(raw.open,errors="raise"),
                     "high":pd.to_numeric(raw.high,errors="raise"),"low":pd.to_numeric(raw.low,errors="raise"),
                     "close":pd.to_numeric(raw.close,errors="raise")})
    return df


def select_server_year(parts:list[pd.DataFrame],year:int)->pd.DataFrame:
    shifted=r33.to_server_coordinate(pd.concat(parts,ignore_index=True).sort_values("time").drop_duplicates("time").reset_index(drop=True))
    a=pd.Timestamp(f"{year}-01-01T00:00:00Z"); b=pd.Timestamp(f"{year+1}-01-01T00:00:00Z")
    shifted=shifted[(shifted.time>=a)&(shifted.time<b)].reset_index(drop=True)
    validate_years(shifted,f"Dukascopy synthetic {year}",coordinate_shifted=True)
    return shifted


def load_duka_server_year(manifest:dict,year:int,tf:str)->pd.DataFrame:
    needed=[value for value in (year-1,year) if str(value) in manifest["yearly"]]
    if year-1 not in needed:raise RuntimeError(f"Dukascopy prior UTC year missing for server year {year}")
    return select_server_year([load_duka_utc_year(manifest,value,tf) for value in needed],year)


def signal_diagnostics(source:pd.DataFrame)->pd.DataFrame:
    atr=r6.atr14(source)
    prior=source.high.shift(1).rolling(RULE["lookback_bars"],min_periods=RULE["lookback_bars"]).max()
    threshold=prior+RULE["buffer_atr"]*atr
    mask=r6.breakout_signal(source,atr,RULE["lookback_bars"],RULE["buffer_atr"],RULE["direction"],RULE["session_start"],RULE["session_end"])
    out=pd.DataFrame({"time":source.time,"close":source.close,"high":source.high,"atr":atr,
                      "prior_96_high":prior,"threshold":threshold})
    return out.loc[mask].reset_index(drop=True)


def _stage_pairs(fn:pd.DataFrame,duka:pd.DataFrame,fn_free:set[int],duka_free:set[int],limit_minutes:int,stage:str):
    limit_ns=limit_minutes*60*1_000_000_000
    candidates=[]
    ft=fn.time.array.as_unit("ns").asi8; dt=duka.time.array.as_unit("ns").asi8
    for i in sorted(fn_free):
        lo=int(np.searchsorted(dt,ft[i]-limit_ns,"left")); hi=int(np.searchsorted(dt,ft[i]+limit_ns,"right"))
        for j in range(lo,hi):
            if j in duka_free:candidates.append((abs(int(dt[j]-ft[i])),int(ft[i]),int(dt[j]),i,j))
    pairs=[]
    for delta,_,__,i,j in sorted(candidates):
        if i in fn_free and j in duka_free:
            fn_free.remove(i); duka_free.remove(j); pairs.append((i,j,stage,delta/60_000_000_000.0))
    return pairs


def match_signals(fn:pd.DataFrame,duka:pd.DataFrame):
    fn=fn.sort_values("time").reset_index(drop=True); duka=duka.sort_values("time").reset_index(drop=True)
    fi=set(range(len(fn))); di=set(range(len(duka))); pairs=[]
    pairs+=_stage_pairs(fn,duka,fi,di,0,"EXACT")
    exact=len(pairs)
    pairs+=_stage_pairs(fn,duka,fi,di,5,"WITHIN_5M")
    within5=len(pairs)
    pairs+=_stage_pairs(fn,duka,fi,di,10,"WITHIN_10M")
    rows=[]
    fields=("close","high","atr","prior_96_high","threshold")
    for i,j,stage,delta_minutes in sorted(pairs,key=lambda z:(fn.time.iloc[z[0]],duka.time.iloc[z[1]])):
        row={"match_stage":stage,"fn_time":fn.time.iloc[i].isoformat(),"duka_time":duka.time.iloc[j].isoformat(),
             "absolute_time_delta_minutes":delta_minutes}
        for field in fields:
            fv=float(fn.loc[i,field]); dv=float(duka.loc[j,field])
            row[f"fn_{field}"]=fv; row[f"duka_{field}"]=dv; row[f"delta_duka_minus_fn_{field}"]=dv-fv
        rows.append(row)
    matched=pd.DataFrame(rows)
    summary={"fn_signals":len(fn),"duka_signals":len(duka),"exact_timestamp":exact,
             "within_5_minutes_cumulative":within5,"within_10_minutes_cumulative":len(pairs),
             "fn_only_after_10_minutes":len(fi),"duka_only_after_10_minutes":len(di),"differences":{}}
    for field in fields:
        vals=matched.get(f"delta_duka_minus_fn_{field}",pd.Series(dtype=float))
        summary["differences"][field]={"matched":int(len(vals)),"mean_signed_duka_minus_fn":float(vals.mean()) if len(vals) else None,
                                       "mean_absolute":float(vals.abs().mean()) if len(vals) else None,
                                       "median_absolute":float(vals.abs().median()) if len(vals) else None}
    return matched,summary,sorted(fi),sorted(di)


def capital(trades,profile,initial=10000.0):
    eq=float(initial);peak=eq;dd=0.0
    for trade in sorted(trades,key=lambda x:x["entry_time"]):
        ret=float(trade["profiles"][profile]["net"])/float(trade["entry_open"])
        if not math.isfinite(ret) or ret<=-1:raise RuntimeError("invalid trade return")
        eq*=1+ret;peak=max(peak,eq);dd=max(dd,(peak-eq)/peak)
    return {"initial":initial,"ending":eq,"return_pct":100*(eq/initial-1),"max_dd_pct":100*dd,"trades":len(trades)}


def run_cell(signal_source:pd.DataFrame,execution_m1:pd.DataFrame,year:int):
    a=pd.Timestamp(f"{year}-01-01T00:00:00Z");b=pd.Timestamp(f"{year+1}-01-01T00:00:00Z")
    sig=signal_diagnostics(signal_source)
    signal_times=set(sig.time.array.as_unit("ns").asi8.tolist())
    mask=np.asarray([int(v) in signal_times for v in signal_source.time.array.as_unit("ns").asi8],dtype=bool)
    ledger,accounting=top2.replay_window(signal_source,execution_m1,mask,RULE["horizon_bars"],RULE["direction"],a,b)
    return ledger,{"accounting":accounting,"metrics":{p:econ.stats(ledger,p) for p in econ.PROFILES},
                   "capital":{p:capital(ledger,p) for p in econ.PROFILES}}


def _metric(matrix,year,cell,metric):
    rec=matrix[cell][str(year)]
    if metric=="trades":return float(rec["accounting"]["executable_trades"])
    value=rec["metrics"]["E1"][metric]
    if metric=="PF":
        if value is None:return 1.0
        value=max(0.0,float(value));return value/(1.0+value)
    return float(value)


def classify(matrix):
    signal_contrasts=[];execution_contrasts=[];detail=[]
    for year in YEARS:
        for metric in ("trades","net","expectancy_bps","PF"):
            vals={cell:_metric(matrix,year,cell,metric) for cell,_,__ in CELLS}
            sf=[];ef=[]
            for execution in ("FN","DUKA"):
                a=vals[f"FN_SIGNAL__{execution}_EXECUTION"];b=vals[f"DUKA_SIGNAL__{execution}_EXECUTION"]
                sf.append(abs(b-a)/max(abs(a),abs(b),1e-12))
            for signal in ("FN","DUKA"):
                a=vals[f"{signal}_SIGNAL__FN_EXECUTION"];b=vals[f"{signal}_SIGNAL__DUKA_EXECUTION"]
                ef.append(abs(b-a)/max(abs(a),abs(b),1e-12))
            ss=float(np.mean(sf));es=float(np.mean(ef));signal_contrasts.append(ss);execution_contrasts.append(es)
            detail.append({"year":year,"metric":metric,"signal_effect":ss,"execution_effect":es})
    signal_score=float(np.median(signal_contrasts));execution_score=float(np.median(execution_contrasts))
    if signal_score==0 and execution_score==0:label="MIXED"
    elif signal_score>=2*execution_score:label="SIGNAL_FEED_DOMINANT"
    elif execution_score>=2*signal_score:label="EXECUTION_FEED_DOMINANT"
    else:label="MIXED"
    return {"classification":label,"signal_score":signal_score,"execution_score":execution_score,"detail":detail}


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--phase-ib-root",required=True,type=Path)
    ap.add_argument("--r30-manifest",required=True,type=Path)
    ap.add_argument("--output-dir",required=True,type=Path)
    args=ap.parse_args();assert_frozen_rule()
    out=args.output_dir
    if out.exists():raise RuntimeError("existing R34 output directory; refusing overwrite")
    staging=out.parent/f".{out.name}.staging-{os.getpid()}"
    if staging.exists():raise RuntimeError("existing R34 staging directory; refusing overwrite")
    if sha256(args.r30_manifest)!=R30_MANIFEST_SHA:raise RuntimeError("R30 manifest SHA mismatch")
    manifest=json.loads(args.r30_manifest.read_text(encoding="utf-8"))
    if manifest.get("status")!="PASS" or manifest.get("source_index_sha256")!=R15_INDEX_SHA or manifest.get("protected_2026_opened") is not False:
        raise RuntimeError("R30 manifest provenance mismatch")
    if not set(manifest.get("yearly",{})).issuperset({"2024","2025"}):raise RuntimeError("R30 years missing")
    fn_m5_all=load_fn(args.phase_ib_root/"xauusd_m5_2024_2025_raw.csv",r31.EXPECTED["xauusd_m5_2024_2025_raw.csv"])
    fn_m1_all=load_fn(args.phase_ib_root/"xauusd_m1_2024_2025_raw.csv",r31.EXPECTED["xauusd_m1_2024_2025_raw.csv"])
    data={"FN":{"M5":{},"M1":{}},"DUKA":{"M5":{},"M1":{}}}
    for year in YEARS:
        for tf,frame in (("M5",fn_m5_all),("M1",fn_m1_all)):
            data["FN"][tf][year]=frame[frame.time.dt.year==year].reset_index(drop=True)
        data["DUKA"]["M5"][year]=load_duka_server_year(manifest,year,"M5")
        data["DUKA"]["M1"][year]=load_duka_server_year(manifest,year,"M1")
    matrix={cell:{} for cell,_,__ in CELLS};ledgers={cell:[] for cell,_,__ in CELLS};similarity={};pair_parts=[]
    signal_parts={"FN":[],"DUKA":[]}
    for year in YEARS:
        diag={feed:signal_diagnostics(data[feed]["M5"][year]) for feed in ("FN","DUKA")}
        for feed in diag:
            part=diag[feed].copy();part.insert(0,"year",year);signal_parts[feed].append(part)
        pairs,summary,fn_only,duka_only=match_signals(diag["FN"],diag["DUKA"]);pairs.insert(0,"year",year)
        unmatched=[]
        for feed,indexes in (("FN",fn_only),("DUKA",duka_only)):
            for index in indexes:
                src=diag[feed].iloc[index]
                row={"year":year,"match_stage":f"{feed}_ONLY","fn_time":None,"duka_time":None,"absolute_time_delta_minutes":None}
                row[f"{feed.lower()}_time"]=src.time.isoformat()
                for field in ("close","high","atr","prior_96_high","threshold"):row[f"{feed.lower()}_{field}"]=float(src[field])
                unmatched.append(row)
        pair_parts.append(pd.concat([pairs,pd.DataFrame(unmatched)],ignore_index=True,sort=False));similarity[str(year)]=summary
        for cell,signal_feed,execution_feed in CELLS:
            ledger,rec=run_cell(data[signal_feed]["M5"][year],data[execution_feed]["M1"][year],year)
            matrix[cell][str(year)]=rec
            for trade in ledger:ledgers[cell].append({"year":year,"cell":cell,**trade})
    if set(matrix)!=set(c for c,_,__ in CELLS) or any(set(v)!={"2024","2025"} for v in matrix.values()):raise RuntimeError("incomplete matrix")
    input_provenance={"r30_manifest":{"path":str(args.r30_manifest),"sha256":R30_MANIFEST_SHA},
                      "fundednext_m5":{"path":str(args.phase_ib_root/"xauusd_m5_2024_2025_raw.csv"),"sha256":r31.EXPECTED["xauusd_m5_2024_2025_raw.csv"]},
                      "fundednext_m1":{"path":str(args.phase_ib_root/"xauusd_m1_2024_2025_raw.csv"),"sha256":r31.EXPECTED["xauusd_m1_2024_2025_raw.csv"]},
                      "dukascopy_yearly":{str(y):{tf.lower():manifest["yearly"][str(y)][f"{tf.lower()}_sha256"] for tf in ("M1","M5")} for y in (2023,2024,2025)}}
    result={"schema":1,"research":"R34","generated_at_utc":datetime.now(timezone.utc).isoformat(),"candidate":RULE,
            "years":list(YEARS),"protected_2026_opened":False,"retuning_performed":False,
            "clock_model":"R33 UTC+3 New York DST, otherwise UTC+2","input_provenance":input_provenance,"matrix":matrix,"signal_similarity":similarity,
            "factorial_classification":classify(matrix)}
    try:
        staging.mkdir(parents=True)
        atomic_json(staging/"r34_signal_execution_feed_factorial_result.json",result)
        rows=[]
        for cell,_,__ in CELLS:
            for year in YEARS:
                rec=matrix[cell][str(year)]
                for profile in econ.PROFILES:rows.append({"cell":cell,"year":year,"profile":profile,**rec["accounting"],**rec["metrics"][profile],**{f"capital_{k}":v for k,v in rec["capital"][profile].items()}})
            pd.DataFrame(ledgers[cell]).to_csv(staging/f"r34_ledger_{cell.lower()}.csv",index=False)
        pd.DataFrame(rows).to_csv(staging/"r34_matrix_yearly.csv",index=False)
        pd.concat(pair_parts,ignore_index=True).to_csv(staging/"r34_signal_pairs.csv",index=False)
        for feed in ("FN","DUKA"):pd.concat(signal_parts[feed],ignore_index=True).to_csv(staging/f"r34_{feed.lower()}_signals.csv",index=False)
        os.replace(staging,out)
    except Exception:
        if staging.exists():shutil.rmtree(staging)
        raise
    print(json.dumps({"status":"COMPLETE","classification":result["factorial_classification"]["classification"],"protected_2026_opened":False},sort_keys=True))
    return 0


if __name__=="__main__":raise SystemExit(main())
