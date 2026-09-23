from pathlib import Path
import argparse, hashlib, json, math
import numpy as np
import pandas as pd
from scipy.stats import t as student_t
import gef_m5_motion_topology_m04_replication as repl

ENGINE_VERSION="M5-MOTION-TOPOLOGY-M04-LOCKED-OOS-1.0"
START_YEAR=2011
END_YEAR=2025
OOS_START=pd.Timestamp("2023-01-01")
OOS_END=pd.Timestamp("2026-01-01")
FORBIDDEN_DATE=pd.Timestamp("2026-01-01")
MIN_EPISODES=100
MIN_DAYS=60
P_MAX=0.05
TARGETS=["EURUSD","AUDUSD"]
IDS={"EURUSD":"M04_EURUSD_UDXUSD_RELN1_L15","AUDUSD":"M04_AUDUSD_UDXUSD_RELN1_L15"}

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for ch in iter(lambda:f.read(1024*1024),b""): h.update(ch)
    return h.hexdigest()

def latest_reference(root):
    base=root/"Research"/"Autonomous"/"guardian_m5_motion_topology_m04_prelocked_reference"
    runs=[p for p in sorted(base.glob("GEFM5LREF-*")) if (p/"RUN_RECEIPT.json").exists() and (p/"M04_PRE2023_REFERENCE.parquet").exists()]
    if not runs: raise RuntimeError("No frozen pre-2023 reference. Run Freeze-M04Pre2023Reference.ps1 first.")
    run=runs[-1]
    rc=json.loads((run/"RUN_RECEIPT.json").read_text())
    if not rc.get("validation_aggregate_parity_pass"): raise RuntimeError("Pre-2023 reference parity failed")
    if rc.get("2023_2025_accessed"): raise RuntimeError("Reference claims locked OOS access")
    if sha256(run/"M04_PRE2023_REFERENCE.parquet")!=rc["reference_sha256"]:
        raise RuntimeError("Pre-2023 reference hash mismatch")
    return run,rc

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
    if bars.index.max()>=FORBIDDEN_DATE: raise RuntimeError("2026+ escaped locked OOS loader")
    return bars

def cluster_test(y,clusters):
    y=np.asarray(y,dtype=float);clusters=np.asarray(clusters,dtype=object)
    good=np.isfinite(y)&pd.notna(clusters);y=y[good];clusters=clusters[good]
    n=len(y)
    if n<2:return dict(n=n,days=0,mean=np.nan,median=np.nan,positive_frac=np.nan,se=np.nan,t=np.nan,p_one=np.nan)
    codes,_=pd.factorize(clusters,sort=False);u=np.unique(codes);g=len(u)
    mean=float(np.mean(y));median=float(np.median(y));pos=float(np.mean(y>0))
    if g<2:return dict(n=n,days=g,mean=mean,median=median,positive_frac=pos,se=np.nan,t=np.nan,p_one=np.nan)
    resid=y-mean;meat=sum(float(np.sum(resid[codes==c]))**2 for c in u)
    v=(g/(g-1.0))*meat/(n*n)
    se=math.sqrt(v) if np.isfinite(v) and v>0 else np.nan
    tv=mean/se if np.isfinite(se) and se>0 else np.nan
    p=float(student_t.sf(tv,df=max(g-1,1))) if np.isfinite(tv) and mean>0 else 1.0
    return dict(n=n,days=g,mean=mean,median=median,positive_frac=pos,se=se,t=float(tv) if np.isfinite(tv) else np.nan,p_one=p)

def trim_best_mean(vals,pct):
    vals=np.asarray(vals,dtype=float);vals=vals[np.isfinite(vals)]
    if not len(vals): return np.nan
    k=int(math.ceil(len(vals)*pct))
    if k>=len(vals): return np.nan
    return float(np.mean(np.sort(vals)[::-1][k:]))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root);repo=root/"guardian-research"
    specp=repo/"research"/"campaigns"/"GUARDIAN_M5_M04_LOCKED_OOS_SPEC_2026_09_23.json"
    spec=json.loads(specp.read_text())
    if spec.get("status")!="FROZEN_BEFORE_2023_2025_OUTCOMES": raise RuntimeError("Locked OOS spec not frozen")
    if len(spec.get("frozen_candidates",[]))!=2: raise RuntimeError("Expected exactly two locked OOS candidates")

    ref_run,ref_receipt=latest_reference(root)
    ref=pd.read_parquet(ref_run/"M04_PRE2023_REFERENCE.parquet");ref.index=pd.to_datetime(ref.index)

    print("[M5-LOCKED] 1/8 | load 2011-2025 only; 2026 forbidden",flush=True)
    bars={};trad={};ret5={};target={}
    for s in ["UDXUSD","EURUSD","AUDUSD"]:
        b=load_market_m5(root,s)
        bars[s]=b;trad[s]=repl.observed_tradability(b["close"])
        ret5[s]=b["close"].pct_change(fill_method=None).astype("float32")
        if s!="UDXUSD": target[s]=repl.endpoint_target(b,trad[s],15)
    idx=bars["UDXUSD"].index

    corr={};zmap={}
    for s in TARGETS:
        cb=repl.corr_break(ret5["UDXUSD"],ret5[s])
        corr[s]=cb;zmap[s]=repl.causal_z(cb)

    parity=[]
    pre=(idx<OOS_START)
    for s in TARGETS:
        for kind,cur in [("corr_break",corr[s]),("corr_break_z",zmap[s])]:
            col=f"{s}__{kind}"
            rr=pd.to_numeric(ref[col],errors="coerce").reindex(idx)
            m=pre&rr.notna().to_numpy()&cur.notna().to_numpy()
            if not np.any(m): raise RuntimeError(f"No pre-2023 parity overlap {s} {kind}")
            diff=float(np.max(np.abs(rr.to_numpy(dtype=float)[m]-cur.to_numpy(dtype=float)[m])))
            ok=bool(diff<=5e-7)
            parity.append({"target":s,"object":kind,"max_abs_diff":diff,"pass":ok})
            if not ok: raise RuntimeError(f"Pre-2023 parity failed {s} {kind}: {diff}")
    print("[M5-LOCKED] 2/8 | pre-2023 parity PASS",flush=True)

    rows=[];annual=[];loo=[];placebo=[]
    oos=(idx>=OOS_START)&(idx<OOS_END)
    for s in TARGETS:
        y=target[s]
        raw=repl.m04_event(zmap[s])&y.notna()&pd.Series(oos,index=idx)
        ep=repl.cooldown_first(idx,raw.to_numpy(),repl.COOLDOWN_MIN)
        yy=y.to_numpy(dtype=float)[ep];tt=idx[ep]
        fit=cluster_test(yy,tt.normalize().strftime("%Y-%m-%d").to_numpy(dtype=object))
        passed=bool(fit["n"]>=MIN_EPISODES and fit["days"]>=MIN_DAYS and fit["mean"]>0 and fit["p_one"]<=P_MAX)
        trim1=trim_best_mean(yy,0.01);trim2=trim_best_mean(yy,0.02)
        rows.append({
          "id":IDS[s],"target":s,"peer":"UDXUSD","relation":-1,
          "lookback_min":15,"horizon_min":15,
          "episodes":fit["n"],"days":fit["days"],"mean_endpoint":fit["mean"],"median_endpoint":fit["median"],
          "positive_frac":fit["positive_frac"],"se":fit["se"],"t":fit["t"],"p_one":fit["p_one"],
          "trim_best_1pct_mean":trim1,"trim_best_2pct_mean":trim2,"locked_oos_pass":passed
        })
        for year in [2023,2024,2025]:
            vals=yy[tt.year==year]
            annual.append({"id":IDS[s],"year":year,"episodes":int(len(vals)),
                           "mean_endpoint":float(np.mean(vals)) if len(vals) else np.nan,
                           "median_endpoint":float(np.median(vals)) if len(vals) else np.nan,
                           "positive_frac":float(np.mean(vals>0)) if len(vals) else np.nan})
        for year in [2023,2024,2025]:
            vals=yy[tt.year!=year]
            loo.append({"id":IDS[s],"left_out_year":year,"mean_endpoint":float(np.mean(vals)) if len(vals) else np.nan})
        for shift_min in [-60,60]:
            shifted=tt+pd.Timedelta(minutes=shift_min)
            vals=y.reindex(shifted).to_numpy(dtype=float);vals=vals[np.isfinite(vals)]
            placebo.append({"id":IDS[s],"shift_min":shift_min,"episodes":int(len(vals)),
                            "mean_endpoint":float(np.mean(vals)) if len(vals) else np.nan,
                            "median_endpoint":float(np.median(vals)) if len(vals) else np.nan,
                            "positive_frac":float(np.mean(vals>0)) if len(vals) else np.nan})

    R=pd.DataFrame(rows);A=pd.DataFrame(annual);L=pd.DataFrame(loo);P=pd.DataFrame(placebo)

    base=root/"Research"/"Autonomous"/"guardian_m5_motion_topology_m04_locked_oos"
    base.mkdir(parents=True,exist_ok=True)
    rid="GEFM5OOS-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    out=base/rid;out.mkdir(parents=True,exist_ok=False)
    pd.DataFrame(parity).to_csv(out/"PRE2023_PARITY.csv",index=False)
    R.to_csv(out/"LOCKED_OOS_RESULTS.csv",index=False)
    A.to_csv(out/"LOCKED_OOS_YEARLY.csv",index=False)
    L.to_csv(out/"LOCKED_OOS_LEAVE_ONE_YEAR_OUT.csv",index=False)
    P.to_csv(out/"LOCKED_OOS_PLACEBO_SHIFTS.csv",index=False)

    receipt={
      "run_id":rid,"status":"COMPLETE_M04_LOCKED_OOS_2023_2025",
      "engine_version":ENGINE_VERSION,
      "parent_validation_run":spec["parent_validation_run"],
      "pre2023_reference_run":ref_receipt["run_id"],
      "pre2023_reference_sha256":ref_receipt["reference_sha256"],
      "frozen_candidates_tested":2,
      "locked_oos_survivors":int(R["locked_oos_pass"].sum()),
      "survivors":R.loc[R["locked_oos_pass"],"id"].tolist(),
      "pre2023_parity_pass":bool(all(x["pass"] for x in parity)),
      "2026_accessed":False,
      "next":"STOP. HUMAN REVIEW BEFORE ANY EXECUTION DESIGN, SHADOW DEPLOYMENT OR 2026 ACCESS."
    }
    write_json(out/"RUN_RECEIPT.json",receipt)
    write_json(out/"RUNTIME_PROVENANCE.json",{
      "engine_version":ENGINE_VERSION,"spec_sha256":sha256(specp),
      "raw_years":list(range(2011,2026)),"locked_oos_window":"2023-2025",
      "forbidden_from":"2026-01-01","hard_gates":{"min_episodes":MIN_EPISODES,"min_days":MIN_DAYS,"mean_positive":True,"p_one_max":P_MAX}
    })

    print("[M5-LOCKED] 3/8 | two frozen candidates scored",flush=True)
    print("[M5-LOCKED] 4/8 | yearly diagnostics complete",flush=True)
    print("[M5-LOCKED] 5/8 | leave-one-year-out diagnostics complete",flush=True)
    print("[M5-LOCKED] 6/8 | placebo diagnostics complete",flush=True)
    print("[M5-LOCKED] 7/8 | 2026 remains unopened",flush=True)
    print("[M5-LOCKED] 8/8 | DONE",flush=True)
    print("\n=== M04 LOCKED OOS RECEIPT ===")
    print(json.dumps(receipt,indent=2))
    print("\n=== PRE-2023 PARITY ===")
    print(pd.DataFrame(parity).to_string(index=False))
    print("\n=== LOCKED OOS RESULTS ===")
    print(R.to_string(index=False))
    print("\n=== YEARLY ===")
    print(A.to_string(index=False))
    print("\n=== LEAVE-ONE-YEAR-OUT ===")
    print(L.to_string(index=False))
    print("\n=== PLACEBO SHIFTS ===")
    print(P.to_string(index=False))
    print("\nRUN:",out)

if __name__=="__main__":
    main()
