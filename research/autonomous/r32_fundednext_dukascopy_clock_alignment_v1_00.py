#!/usr/bin/env python3
"""R32: FundedNext vs Dukascopy M5 clock alignment by return correlation."""
from __future__ import annotations
import argparse, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

import strategy_factory_causal_next_open_v1_00 as r5

FN_SHA="ba54c9b29755eac4284cb872805148736be529e954533c028e7f826bb444ce66"
R15_INDEX_SHA="d77fb76e5b5ee0600a488c331084e70972a8800a33ae59a957c1044dc39ef566"
SHIFTS=list(range(-4,5))


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


def load_fn(path:Path)->pd.DataFrame:
    if sha256(path)!=FN_SHA: raise RuntimeError("FundedNext raw M5 SHA mismatch")
    meta=r5.detect(path)
    if not meta: raise RuntimeError("cannot detect FundedNext M5")
    df=r5.load_market(path,meta,2_000_000)
    if not set(int(x) for x in df.time.dt.year.unique()).issubset({2024,2025}):
        raise RuntimeError("FundedNext M5 contains unexpected years")
    return df[["time","close"]].copy()


def load_duk(manifest:dict,year:int)->pd.DataFrame:
    rec=manifest["yearly"][str(year)]
    p=Path(rec["m5_path"])
    if sha256(p)!=rec["m5_sha256"]: raise RuntimeError(f"Dukascopy {year} M5 SHA mismatch")
    z=pd.read_csv(p,usecols=["server_epoch","close"])
    if len(z)!=int(rec["m5_rows"]): raise RuntimeError(f"Dukascopy {year} row mismatch")
    t=pd.to_datetime(pd.to_numeric(z.server_epoch,errors="raise").astype("int64"),unit="s",utc=True)
    out=pd.DataFrame({"time":t,"close":pd.to_numeric(z.close,errors="raise")})
    if (out.time.dt.year!=year).any(): raise RuntimeError(f"Dukascopy {year} year mismatch")
    return out


def contiguous_returns(df:pd.DataFrame)->pd.DataFrame:
    x=df.sort_values("time").drop_duplicates("time").reset_index(drop=True)
    dt=x.time.diff().dt.total_seconds()
    ret=x.close.pct_change()
    ok=dt.eq(300) & np.isfinite(ret)
    return pd.DataFrame({"time":x.loc[ok,"time"].to_numpy(),"ret":ret.loc[ok].to_numpy(float)})


def score_month(fnret:pd.DataFrame,dukret:pd.DataFrame,month:str)->dict:
    a=pd.Timestamp(month+"-01",tz="UTC")
    b=a+pd.offsets.MonthBegin(1)
    d=dukret[(dukret.time>=a)&(dukret.time<b)].copy()
    rows=[]
    for sh in SHIFTS:
        f=fnret.copy()
        f["aligned_time"]=f.time+pd.Timedelta(hours=sh)
        f=f[(f.aligned_time>=a)&(f.aligned_time<b)][["aligned_time","ret"]].rename(columns={"ret":"fn_ret"})
        m=f.merge(d.rename(columns={"time":"aligned_time","ret":"duk_ret"}),on="aligned_time",how="inner")
        n=len(m)
        corr=float(m.fn_ret.corr(m.duk_ret)) if n>=500 and m.fn_ret.std()>0 and m.duk_ret.std()>0 else None
        rows.append({"shift_hours":sh,"matched":n,"return_correlation":corr})
    valid=[r for r in rows if r["return_correlation"] is not None]
    if not valid: raise RuntimeError(f"no valid shift for {month}")
    valid=sorted(valid,key=lambda r:r["return_correlation"],reverse=True)
    best=valid[0]; runner=valid[1] if len(valid)>1 else None
    return {
        "month":month,
        "best_shift_hours":best["shift_hours"],
        "implied_server_utc_offset_hours":-best["shift_hours"],
        "best_correlation":best["return_correlation"],
        "best_matched":best["matched"],
        "runner_up_shift_hours":runner["shift_hours"] if runner else None,
        "runner_up_correlation":runner["return_correlation"] if runner else None,
        "correlation_gap":best["return_correlation"]-runner["return_correlation"] if runner else None,
        "all_shifts":rows,
    }


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--phase-ib-root",required=True,type=Path)
    ap.add_argument("--r30-manifest",required=True,type=Path)
    ap.add_argument("--output-dir",required=True,type=Path)
    args=ap.parse_args()

    out=args.output_dir; out.mkdir(parents=True,exist_ok=True)
    rp=out/"r32_fundednext_dukascopy_clock_alignment.json"
    if rp.exists(): raise RuntimeError("existing R32 result; refusing overwrite")

    manifest=json.loads(args.r30_manifest.read_text(encoding="utf-8"))
    if manifest.get("status")!="PASS" or manifest.get("source_index_sha256")!=R15_INDEX_SHA:
        raise RuntimeError("R30 manifest provenance mismatch")
    if manifest.get("protected_2026_opened") is not False:
        raise RuntimeError("R30 manifest touched 2026")

    fn=load_fn(args.phase_ib_root/"xauusd_m5_2024_2025_raw.csv")
    duk=pd.concat([load_duk(manifest,2024),load_duk(manifest,2025)],ignore_index=True)
    fnret=contiguous_returns(fn)
    dukret=contiguous_returns(duk)

    months=[f"{y}-{m:02d}" for y in (2024,2025) for m in range(1,13)]
    results=[score_month(fnret,dukret,m) for m in months]

    counts={}
    for r in results:
        k=str(r["best_shift_hours"]); counts[k]=counts.get(k,0)+1
    weighted_corr=float(np.average([r["best_correlation"] for r in results],weights=[r["best_matched"] for r in results]))

    payload={
        "schema":1,"research":"R32","generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "protected_2026_opened":False,"strategy_pnl_computed":False,
        "definition":"aligned_fundednext_time = fundednext_timestamp + shift_hours",
        "shift_grid_hours":SHIFTS,
        "months":results,
        "best_shift_month_counts":counts,
        "matched_weighted_mean_best_correlation":weighted_corr,
    }
    atomic_json(rp,payload)
    print(json.dumps({
        "status":"PASS",
        "best_shift_month_counts":counts,
        "weighted_mean_best_corr":weighted_corr,
        "months":[{"month":r["month"],"shift":r["best_shift_hours"],"offset":r["implied_server_utc_offset_hours"],"corr":r["best_correlation"],"gap":r["correlation_gap"]} for r in results],
        "protected_2026_opened":False
    },sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
