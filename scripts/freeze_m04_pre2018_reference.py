from pathlib import Path
import argparse, hashlib, json, math
import numpy as np
import pandas as pd
import gef_m5_motion_topology_m04_replication as repl

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for ch in iter(lambda:f.read(1024*1024),b""):
            h.update(ch)
    return h.hexdigest()

def latest_replication(root):
    base=root/"Research"/"Autonomous"/"guardian_m5_motion_topology_m04_replication"
    runs=[p for p in sorted(base.glob("GEFM5R-*")) if (p/"RUN_RECEIPT.json").exists() and (p/"REPLICATION_RESULTS.csv").exists()]
    if not runs: raise RuntimeError("No completed M04 replication run")
    return runs[-1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root)
    rep=latest_replication(root)
    receipt=json.loads((rep/"RUN_RECEIPT.json").read_text())
    if receipt.get("run_id")!="GEFM5R-20260923-053206":
        raise RuntimeError(f"Unexpected parent replication run {receipt.get('run_id')}")
    if receipt.get("2018_plus_accessed"):
        raise RuntimeError("Parent replication claims 2018+ access")
    published=pd.read_csv(rep/"REPLICATION_RESULTS.csv")

    bars={};trad={};ret5={};targets={}
    for s in repl.MARKETS:
        b,_=repl.load_market_m5(root,s)
        if b.index.max()>=pd.Timestamp("2018-01-01"):
            raise RuntimeError("2018+ escaped reference builder")
        bars[s]=b
        trad[s]=repl.observed_tradability(b["close"])
        ret5[s]=b["close"].pct_change(fill_method=None).astype("float32")

    idx=bars["UDXUSD"].index
    ref=pd.DataFrame(index=idx)
    for s in repl.TARGETS:
        cb=repl.corr_break(ret5["UDXUSD"],ret5[s])
        z=repl.causal_z(cb)
        ref[f"{s}__corr_break"]=cb.astype("float32")
        ref[f"{s}__corr_break_z"]=z.astype("float32")

    specp=root/"guardian-research"/"research"/"campaigns"/"GUARDIAN_M5_M04_REPLICATION_SPEC_2026_09_23.json"
    spec=json.loads(specp.read_text())
    recomputed=[]
    for sv in spec["frozen_survivors"]:
        s=sv["target"];L=int(sv["lookback_min"])
        if (s,L) not in targets:
            targets[(s,L)]=repl.endpoint_target(bars[s],trad[s],L)
        y=targets[(s,L)]
        z=ref[f"{s}__corr_break_z"]
        raw=repl.m04_event(z)&y.notna()&pd.Series((idx>=pd.Timestamp("2015-01-01"))&(idx<pd.Timestamp("2018-01-01")),index=idx)
        ep=repl.cooldown_first(idx,raw.to_numpy(),repl.COOLDOWN_MIN)
        yy=y.to_numpy(dtype=float)[ep];tt=idx[ep]
        fit=repl.cluster_test(yy,tt.normalize().strftime("%Y-%m-%d").to_numpy(dtype=object))
        recomputed.append({"id":sv["id"],"episodes":fit["n"],"days":fit["days"],"mean_endpoint":fit["mean"],"p_one":fit["p_one"]})

    rc=pd.DataFrame(recomputed)
    chk=published.merge(rc,on="id",suffixes=("_published","_recomputed"),how="outer",indicator=True)
    if not (chk["_merge"]=="both").all(): raise RuntimeError("Replication result identity mismatch")
    checks=[]
    for r in chk.itertuples():
        passed=(int(r.episodes_published)==int(r.episodes_recomputed) and int(r.days_published)==int(r.days_recomputed)
                and abs(float(r.mean_endpoint_published)-float(r.mean_endpoint_recomputed))<=1e-12
                and abs(float(r.p_one_published)-float(r.p_one_recomputed))<=1e-12)
        checks.append({"id":r.id,"pass":bool(passed),
                       "mean_abs_diff":abs(float(r.mean_endpoint_published)-float(r.mean_endpoint_recomputed)),
                       "p_abs_diff":abs(float(r.p_one_published)-float(r.p_one_recomputed))})
        if not passed: raise RuntimeError(f"Replication aggregate parity failed for {r.id}")

    base=root/"Research"/"Autonomous"/"guardian_m5_motion_topology_m04_prevalidation_reference"
    base.mkdir(parents=True,exist_ok=True)
    rid="GEFM5P-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    out=base/rid;out.mkdir(parents=True,exist_ok=False)
    rp=out/"M04_PRE2018_REFERENCE.parquet"
    ref.to_parquet(rp)
    pd.DataFrame(checks).to_csv(out/"REPLICATION_AGGREGATE_PARITY.csv",index=False)
    receipt_out={
      "run_id":rid,"status":"FROZEN_M04_PRE2018_REFERENCE",
      "parent_replication_run":receipt["run_id"],
      "rows":len(ref),"columns":list(ref.columns),
      "reference_sha256":sha256(rp),
      "replication_aggregate_parity_pass":True,
      "2018_plus_accessed":False,"2023_2025_accessed":False,"2026_accessed":False
    }
    write_json(out/"RUN_RECEIPT.json",receipt_out)
    print("\n=== M04 PRE-2018 REFERENCE RECEIPT ===")
    print(json.dumps(receipt_out,indent=2))
    print("\n=== REPLICATION AGGREGATE PARITY ===")
    print(pd.DataFrame(checks).to_string(index=False))
    print("\nRUN:",out)

if __name__=="__main__":
    main()
