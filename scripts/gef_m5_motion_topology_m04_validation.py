from pathlib import Path
import argparse, hashlib, json, math
import numpy as np
import pandas as pd
from scipy.stats import t as student_t
import gef_m5_motion_topology_m04_replication as repl

ENGINE_VERSION="M5-MOTION-TOPOLOGY-M04-VALIDATION-1.1"
VALID_START=pd.Timestamp("2018-01-01")
VALID_END=pd.Timestamp("2023-01-01")
FORBIDDEN_DATE=pd.Timestamp("2023-01-01")
MIN_EPISODES=250
MIN_DAYS=150
P_MAX=0.05

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for ch in iter(lambda:f.read(1024*1024),b""):
            h.update(ch)
    return h.hexdigest()

def latest_reference(root):
    base=root/"Research"/"Autonomous"/"guardian_m5_motion_topology_m04_prevalidation_reference"
    runs=[p for p in sorted(base.glob("GEFM5P-*")) if (p/"RUN_RECEIPT.json").exists() and (p/"M04_PRE2018_REFERENCE.parquet").exists()]
    if not runs: raise RuntimeError("No frozen pre-2018 M04 reference. Run Freeze-M04Pre2018Reference.ps1 first.")
    run=runs[-1]
    rc=json.loads((run/"RUN_RECEIPT.json").read_text())
    if not rc.get("replication_aggregate_parity_pass"): raise RuntimeError("Pre-2018 reference did not pass replication parity")
    if rc.get("2018_plus_accessed"): raise RuntimeError("Reference claims 2018+ access")
    if sha256(run/"M04_PRE2018_REFERENCE.parquet")!=rc["reference_sha256"]:
        raise RuntimeError("Pre-2018 reference hash mismatch")
    return run,rc

def detect_cols(d):
    return repl.detect_cols(d)

def load_market_m5(root,sym,start_year=2011,end_year=2022):
    parts=[];true_ohlc=True
    for y in range(start_year,end_year+1):
        p=root/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
        if not p.exists(): raise RuntimeError(f"Missing {p}")
        d=pd.read_parquet(p)
        d,dc,op,hi,lo,close=detect_cols(d)
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
    grid=pd.date_range(f"{start_year}-01-01 00:00",f"{end_year}-12-31 23:55",freq="5min")
    bars=bars.reindex(grid);bars.index.name="decision_time_utc"
    if bars.index.max()>=FORBIDDEN_DATE: raise RuntimeError("2023+ escaped validation loader")
    return bars

def cluster_test(y,clusters):
    y=np.asarray(y,dtype=float);clusters=np.asarray(clusters,dtype=object)
    good=np.isfinite(y)&pd.notna(clusters);y=y[good];clusters=clusters[good]
    n=len(y)
    if n<2:return dict(n=n,days=0,mean=np.nan,median=np.nan,positive_frac=np.nan,se=np.nan,t=np.nan,p_one=np.nan)
    codes,_=pd.factorize(clusters,sort=False);u=np.unique(codes);g=len(u)
    mean=float(np.mean(y));median=float(np.median(y));pos=float(np.mean(y>0))
    if g<2:return dict(n=n,days=g,mean=mean,median=median,positive_frac=pos,se=np.nan,t=np.nan,p_one=np.nan)
    resid=y-mean
    meat=sum(float(np.sum(resid[codes==c]))**2 for c in u)
    v=(g/(g-1.0))*meat/(n*n)
    se=math.sqrt(v) if np.isfinite(v) and v>0 else np.nan
    tv=mean/se if np.isfinite(se) and se>0 else np.nan
    p=float(student_t.sf(tv,df=max(g-1,1))) if np.isfinite(tv) and mean>0 else 1.0
    return dict(n=n,days=g,mean=mean,median=median,positive_frac=pos,se=se,t=float(tv) if np.isfinite(tv) else np.nan,p_one=p)

def trim_best_mean(vals,pct):
    vals=np.asarray(vals,dtype=float)
    vals=vals[np.isfinite(vals)]
    if not len(vals): return np.nan
    k=int(math.ceil(len(vals)*pct))
    if k>=len(vals): return np.nan
    order=np.sort(vals)[::-1]
    return float(np.mean(order[k:]))

def latest_replication(root):
    base=root/"Research"/"Autonomous"/"guardian_m5_motion_topology_m04_replication"
    runs=[p for p in sorted(base.glob("GEFM5R-*")) if (p/"RUN_RECEIPT.json").exists()]
    if not runs: raise RuntimeError("No replication run")
    return runs[-1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root);repo=root/"guardian-research"
    specp=repo/"research"/"campaigns"/"GUARDIAN_M5_M04_VALIDATION_SPEC_2026_09_23.json"
    spec=json.loads(specp.read_text())
    if spec.get("status")!="FROZEN_BEFORE_2018_2022_OUTCOMES_AMENDED": raise RuntimeError("Validation spec not frozen/amended")
    survivors=spec["frozen_survivors"]
    if len(survivors)!=5: raise RuntimeError("Expected exactly five validation survivors")

    ref_run,ref_receipt=latest_reference(root)
    ref=pd.read_parquet(ref_run/"M04_PRE2018_REFERENCE.parquet")
    ref.index=pd.to_datetime(ref.index)

    base=root/"Research"/"Autonomous"/"guardian_m5_motion_topology_m04_validation"
    base.mkdir(parents=True,exist_ok=True)
    rid="GEFM5V-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    out=base/rid;out.mkdir(parents=True,exist_ok=False)

    print("[M5-VALID] 1/9 | load 2011-2022 only; 2023+ forbidden",flush=True)
    markets=["UDXUSD","EURUSD","GBPUSD","AUDUSD","USDCHF"]
    bars={};trad={};ret5={};targets={}
    for s in markets:
        b=load_market_m5(root,s)
        bars[s]=b
        trad[s]=repl.observed_tradability(b["close"])
        ret5[s]=b["close"].pct_change(fill_method=None).astype("float32")
        if s!="UDXUSD":
            needed=sorted({int(x["lookback_min"]) for x in survivors if x["target"]==s})
            targets[s]={L:repl.endpoint_target(b,trad[s],L) for L in needed}
    idx=bars["UDXUSD"].index
    print("[M5-VALID] 2/9 | causal objects",flush=True)

    corr={};zmap={}
    for s in ["EURUSD","GBPUSD","AUDUSD","USDCHF"]:
        cb=repl.corr_break(ret5["UDXUSD"],ret5[s])
        corr[s]=cb
        zmap[s]=repl.causal_z(cb)

    # Exact pre-2018 parity against frozen reference.
    parity=[]
    pre=(idx<VALID_START)
    for s in ["EURUSD","GBPUSD","AUDUSD","USDCHF"]:
        for kind,cur in [("corr_break",corr[s]),("corr_break_z",zmap[s])]:
            col=f"{s}__{kind}"
            rr=pd.to_numeric(ref[col],errors="coerce").reindex(idx)
            m=pre&rr.notna().to_numpy()&cur.notna().to_numpy()
            if not np.any(m): raise RuntimeError(f"No pre-2018 parity overlap {s} {kind}")
            diff=float(np.max(np.abs(rr.to_numpy(dtype=float)[m]-cur.to_numpy(dtype=float)[m])))
            ok=bool(diff<=5e-7)
            parity.append({"target":s,"object":kind,"max_abs_diff":diff,"pass":ok})
            if not ok: raise RuntimeError(f"Pre-2018 parity failed {s} {kind}: {diff}")
    pd.DataFrame(parity).to_csv(out/"PRE2018_PARITY.csv",index=False)
    print("[M5-VALID] 3/9 | pre-2018 parity PASS",flush=True)

    rows=[];annual=[];loo=[];placebo=[]
    valid_mask=(idx>=VALID_START)&(idx<VALID_END)
    for sv in survivors:
        s=sv["target"];L=int(sv["lookback_min"])
        y=targets[s][L]
        raw=repl.m04_event(zmap[s])&y.notna()&pd.Series(valid_mask,index=idx)
        ep=repl.cooldown_first(idx,raw.to_numpy(),repl.COOLDOWN_MIN)
        yy=y.to_numpy(dtype=float)[ep];tt=idx[ep]
        fit=cluster_test(yy,tt.normalize().strftime("%Y-%m-%d").to_numpy(dtype=object))

        year_means={}
        for year in [2018,2019,2020,2021,2022]:
            vals=yy[tt.year==year]
            m=float(np.mean(vals)) if len(vals) else np.nan
            year_means[year]=m
            annual.append({"id":sv["id"],"year":year,"episodes":int(len(vals)),
                           "mean_endpoint":m,
                           "median_endpoint":float(np.median(vals)) if len(vals) else np.nan,
                           "positive_frac":float(np.mean(vals>0)) if len(vals) else np.nan})
        positive_years=int(sum(np.isfinite(v) and v>0 for v in year_means.values()))

        loo_means={}
        for year in [2018,2019,2020,2021,2022]:
            vals=yy[tt.year!=year]
            m=float(np.mean(vals)) if len(vals) else np.nan
            loo_means[year]=m
            loo.append({"id":sv["id"],"left_out_year":year,"mean_endpoint":m})
        loo_min=float(np.nanmin(list(loo_means.values()))) if loo_means else np.nan

        trim1=trim_best_mean(yy,0.01)
        trim2=trim_best_mean(yy,0.02)

        pass_primary=bool(
            fit["n"]>=MIN_EPISODES and fit["days"]>=MIN_DAYS and
            fit["mean"]>0 and fit["p_one"]<=P_MAX
        )

        rows.append({
          "id":sv["id"],"target":s,"peer":sv["peer"],"relation":sv["relation"],
          "lookback_min":L,"horizon_min":int(sv["horizon_min"]),
          "episodes":fit["n"],"days":fit["days"],"mean_endpoint":fit["mean"],
          "median_endpoint":fit["median"],"positive_frac":fit["positive_frac"],
          "se":fit["se"],"t":fit["t"],"p_one":fit["p_one"],
          "positive_years":positive_years,"loo_min_mean":loo_min,
          "trim_best_1pct_mean":trim1,"trim_best_2pct_mean":trim2,
          "validation_pass":pass_primary
        })

        # Specificity diagnostics only.
        event_times=tt
        for shift_min in [-60,60]:
            shifted=event_times+pd.Timedelta(minutes=shift_min)
            vals=y.reindex(shifted).to_numpy(dtype=float)
            vals=vals[np.isfinite(vals)]
            placebo.append({
              "id":sv["id"],"shift_min":shift_min,"episodes":int(len(vals)),
              "mean_endpoint":float(np.mean(vals)) if len(vals) else np.nan,
              "median_endpoint":float(np.median(vals)) if len(vals) else np.nan,
              "positive_frac":float(np.mean(vals>0)) if len(vals) else np.nan
            })

    R=pd.DataFrame(rows);A=pd.DataFrame(annual);L=pd.DataFrame(loo);P=pd.DataFrame(placebo)
    R.to_csv(out/"VALIDATION_RESULTS.csv",index=False)
    A.to_csv(out/"VALIDATION_YEARLY.csv",index=False)
    L.to_csv(out/"VALIDATION_LEAVE_ONE_YEAR_OUT.csv",index=False)
    P.to_csv(out/"VALIDATION_PLACEBO_SHIFTS.csv",index=False)

    pass_count=int(R["validation_pass"].sum())
    frozen=R[R["validation_pass"]].copy()
    frozen.to_csv(out/"FROZEN_VALIDATION_SURVIVORS.csv",index=False)
    frozen_sha=sha256(out/"FROZEN_VALIDATION_SURVIVORS.csv")

    receipt={
      "run_id":rid,"status":"COMPLETE_M04_2018_2022_VALIDATION",
      "engine_version":ENGINE_VERSION,
      "parent_replication_run":spec["parent_replication_run"],
      "parent_replication_survivor_sha256":spec["parent_replication_survivor_sha256"],
      "pre2018_reference_run":ref_receipt["run_id"],
      "pre2018_reference_sha256":ref_receipt["reference_sha256"],
      "frozen_variants_tested":5,
      "valid_support_tests":int(((R["episodes"]>=MIN_EPISODES)&(R["days"]>=MIN_DAYS)).sum()),
      "validation_survivors":pass_count,
      "survivors":R.loc[R["validation_pass"],"id"].tolist(),
      "family_validation_rule":"no new mechanical family threshold; report individual validation count",
      "frozen_validation_survivor_sha256":frozen_sha,
      "pre2018_parity_pass":bool(all(x["pass"] for x in parity)),
      "2023_2025_accessed":False,"2026_accessed":False,
      "next":"STOP FOR HUMAN REVIEW. IF ONE OR MORE VARIANTS VALIDATE, DECIDE WHETHER TO PREREGISTER LOCKED 2023-2025 OOS; ELSE CLOSE M04 LINEAGE"
    }
    write_json(out/"RUN_RECEIPT.json",receipt)
    write_json(out/"RUNTIME_PROVENANCE.json",{
      "engine_version":ENGINE_VERSION,"validation_spec_sha256":sha256(specp),
      "raw_years":list(range(2011,2023)),"validation_window":"2018-2022",
      "forbidden_from":"2023-01-01","trim_best_rule":"remove ceil(N*p) highest endpoint_scores",
      "negative_control_shifts_min":[-60,60]
    })

    print("[M5-VALID] 4/9 | five frozen variants scored",flush=True)
    print("[M5-VALID] 5/9 | annual/LOO/trim robustness complete",flush=True)
    print("[M5-VALID] 6/9 | placebo diagnostics complete",flush=True)
    print("[M5-VALID] 7/9 | validation freeze written",flush=True)
    print("[M5-VALID] 8/9 | 2023+ remains unopened",flush=True)
    print("[M5-VALID] 9/9 | DONE",flush=True)

    print("\n=== M04 VALIDATION RECEIPT ===")
    print(json.dumps(receipt,indent=2))
    print("\n=== PRE-2018 PARITY ===")
    print(pd.DataFrame(parity).to_string(index=False))
    print("\n=== VALIDATION RESULTS ===")
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
