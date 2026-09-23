from pathlib import Path
import argparse, hashlib, json, math
import numpy as np
import pandas as pd
import gef_m5_motion_topology_m04_replication as repl

START_YEAR=2011
END_YEAR=2022
VALID_START=pd.Timestamp("2018-01-01")
VALID_END=pd.Timestamp("2023-01-01")
FORBIDDEN_DATE=pd.Timestamp("2023-01-01")
TARGETS=["EURUSD","AUDUSD"]

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for ch in iter(lambda:f.read(1024*1024),b""): h.update(ch)
    return h.hexdigest()

def load_market_m5(root,sym):
    parts=[];true_ohlc=True
    for y in range(START_YEAR,END_YEAR+1):
        p=root/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
        if not p.exists(): raise RuntimeError(f"Missing {p}")
        d=pd.read_parquet(p)
        d,dc,op,hi,lo,close=repl.detect_cols(d)
        if any(x is None for x in [op,hi,lo]): true_ohlc=False
        utc=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(hours=5)
        q=pd.DataFrame({"utc":utc,"close":pd.to_numeric(d[close],errors="coerce")})
        if true_ohlc and all(x is not None for x in [op,hi,lo]):
            q["open"]=pd.to_numeric(d[op],errors="coerce")
            q["high"]=pd.to_numeric(d[hi],errors="coerce")
            q["low"]=pd.to_numeric(d[lo],errors="coerce")
        q=q.dropna(subset=["utc","close"])
        q=q[q["utc"].dt.year==y].sort_values("utc").drop_duplicates("utc",keep="last")
        parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last").set_index("utc")
    if true_ohlc and {"open","high","low","close"}.issubset(q.columns):
        bars=pd.DataFrame({
          "open":q["open"].resample("5min",label="right",closed="left").first(),
          "high":q["high"].resample("5min",label="right",closed="left").max(),
          "low":q["low"].resample("5min",label="right",closed="left").min(),
          "close":q["close"].resample("5min",label="right",closed="left").last(),
        })
    else:
        c=q["close"]
        bars=pd.DataFrame({
          "open":c.resample("5min",label="right",closed="left").first(),
          "high":c.resample("5min",label="right",closed="left").max(),
          "low":c.resample("5min",label="right",closed="left").min(),
          "close":c.resample("5min",label="right",closed="left").last(),
        })
    grid=pd.date_range(f"{START_YEAR}-01-01 00:00",f"{END_YEAR}-12-31 23:55",freq="5min")
    bars=bars.reindex(grid);bars.index.name="decision_time_utc"
    if bars.index.max()>=FORBIDDEN_DATE: raise RuntimeError("2023+ escaped reference builder")
    return bars

def latest_validation(root):
    base=root/"Research"/"Autonomous"/"guardian_m5_motion_topology_m04_validation"
    runs=[p for p in sorted(base.glob("GEFM5V-*")) if (p/"RUN_RECEIPT.json").exists() and (p/"VALIDATION_RESULTS.csv").exists()]
    if not runs: raise RuntimeError("No validation run")
    return runs[-1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root)
    vr=latest_validation(root)
    rc=json.loads((vr/"RUN_RECEIPT.json").read_text())
    if rc.get("run_id")!="GEFM5V-20260923-055623": raise RuntimeError("Unexpected validation parent")
    if rc.get("2023_2025_accessed"): raise RuntimeError("Validation claims 2023-2025 access")
    published=pd.read_csv(vr/"VALIDATION_RESULTS.csv")
    published=published[published["id"].isin(["M04_EURUSD_UDXUSD_RELN1_L15","M04_AUDUSD_UDXUSD_RELN1_L15"])].copy()

    bars={};trad={};ret5={}
    for s in ["UDXUSD","EURUSD","AUDUSD"]:
        b=load_market_m5(root,s)
        bars[s]=b;trad[s]=repl.observed_tradability(b["close"])
        ret5[s]=b["close"].pct_change(fill_method=None).astype("float32")
    idx=bars["UDXUSD"].index

    ref=pd.DataFrame(index=idx)
    checks=[]
    for s in TARGETS:
        cb=repl.corr_break(ret5["UDXUSD"],ret5[s])
        z=repl.causal_z(cb)
        ref[f"{s}__corr_break"]=cb.astype("float32")
        ref[f"{s}__corr_break_z"]=z.astype("float32")
        y=repl.endpoint_target(bars[s],trad[s],15)
        raw=repl.m04_event(z)&y.notna()&pd.Series((idx>=VALID_START)&(idx<VALID_END),index=idx)
        ep=repl.cooldown_first(idx,raw.to_numpy(),repl.COOLDOWN_MIN)
        yy=y.to_numpy(dtype=float)[ep];tt=idx[ep]
        fit=repl.cluster_test(yy,tt.normalize().strftime("%Y-%m-%d").to_numpy(dtype=object))
        pid="M04_EURUSD_UDXUSD_RELN1_L15" if s=="EURUSD" else "M04_AUDUSD_UDXUSD_RELN1_L15"
        row=published[published["id"]==pid].iloc[0]
        passed=(int(row["episodes"])==fit["n"] and int(row["days"])==fit["days"]
                and abs(float(row["mean_endpoint"])-fit["mean"])<=1e-12
                and abs(float(row["p_one"])-fit["p_one"])<=1e-12)
        checks.append({"id":pid,"pass":bool(passed),
                       "mean_abs_diff":abs(float(row["mean_endpoint"])-fit["mean"]),
                       "p_abs_diff":abs(float(row["p_one"])-fit["p_one"])})
        if not passed: raise RuntimeError(f"Validation aggregate parity failed for {pid}")

    base=root/"Research"/"Autonomous"/"guardian_m5_motion_topology_m04_prelocked_reference"
    base.mkdir(parents=True,exist_ok=True)
    rid="GEFM5LREF-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    out=base/rid;out.mkdir(parents=True,exist_ok=False)
    rp=out/"M04_PRE2023_REFERENCE.parquet";ref.to_parquet(rp)
    pd.DataFrame(checks).to_csv(out/"VALIDATION_AGGREGATE_PARITY.csv",index=False)
    receipt={
      "run_id":rid,"status":"FROZEN_M04_PRE2023_REFERENCE",
      "parent_validation_run":rc["run_id"],"rows":len(ref),"columns":list(ref.columns),
      "reference_sha256":sha256(rp),"validation_aggregate_parity_pass":True,
      "2023_2025_accessed":False,"2026_accessed":False
    }
    write_json(out/"RUN_RECEIPT.json",receipt)
    print("\n=== M04 PRE-2023 REFERENCE RECEIPT ===")
    print(json.dumps(receipt,indent=2))
    print("\n=== VALIDATION AGGREGATE PARITY ===")
    print(pd.DataFrame(checks).to_string(index=False))
    print("\nRUN:",out)

if __name__=="__main__":
    main()
