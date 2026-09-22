from pathlib import Path
import argparse, hashlib, json, math, time
import numpy as np
import pandas as pd

ENGINE_VERSION="V112.1"
UNLOCK="OPEN_LOCKED_OOS_2023_2025"
START=pd.Timestamp("2023-01-01 00:00")
END=pd.Timestamp("2026-01-01 00:00")
BOOTSTRAPS=2000
SEED=112

CANDIDATES=[
    {"candidate_id":"C3","family":"AUDUSD|H21","market":"AUDUSD","hour":21,"horizon":120,"orientation":-1},
    {"candidate_id":"C4","family":"USDCHF|H23","market":"USDCHF","hour":23,"horizon":240,"orientation":1},
    {"candidate_id":"C6","family":"USDCHF|H23","market":"USDCHF","hour":23,"horizon":120,"orientation":1},
]

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def mean_bp(x):
    x=np.asarray(x,dtype=float);x=x[np.isfinite(x)]
    return float(x.mean()*1e4) if len(x) else np.nan

def trimmed_best_mean_bp(x,pct):
    x=np.asarray(x,dtype=float);x=x[np.isfinite(x)]
    if not len(x):return np.nan
    k=int(math.ceil(len(x)*pct))
    if k<=0:return mean_bp(x)
    if k>=len(x):return np.nan
    return mean_bp(np.sort(x)[:-k])

def leave_one_year_out(times,vals):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,dtype=float)})
    d=d[np.isfinite(d["v"])].copy()
    if d.empty:return np.nan,{}
    d["year"]=d["t"].dt.year
    out={}
    for y in sorted(d["year"].unique()):
        z=d.loc[d["year"]!=y,"v"].to_numpy()
        out[str(int(y))]=mean_bp(z)
    return min(out.values()) if out else np.nan,out

def month_block_bootstrap(times,vals,draws,seed):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,dtype=float)})
    d=d[np.isfinite(d["v"])].copy()
    if d.empty:return np.nan,np.nan,np.nan
    d["month"]=d["t"].dt.to_period("M").astype(str)
    groups=[g["v"].to_numpy(dtype=float) for _,g in d.groupby("month") if len(g)]
    if len(groups)<2:return np.nan,np.nan,np.nan
    rng=np.random.default_rng(seed)
    out=np.empty(draws,dtype=float)
    for i in range(draws):
        pick=rng.integers(0,len(groups),size=len(groups))
        out[i]=mean_bp(np.concatenate([groups[j] for j in pick]))
    q=np.quantile(out,[.025,.5,.975])
    return float(q[0]),float(q[1]),float(q[2])

def load_market(root,sym):
    parts=[]
    for year in [2023,2024,2025]:
        p=root/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
        if not p.exists():raise RuntimeError(f"Missing LOCKED OOS price file {p}")
        d=pd.read_parquet(p)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        pc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None and isinstance(d.index,pd.DatetimeIndex):
            d=d.reset_index();dc=d.columns[0]
        if dc is None or pc is None:raise RuntimeError(f"Bad price schema {p}")
        utc=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(hours=5)
        q=pd.DataFrame({"utc":utc,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
        q=q[(q["utc"]>=START)&(q["utc"]<END)]
        parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    if len(q) and q["utc"].max()>=END:
        raise RuntimeError("V112 raw input contains 2026+ data")
    s=q.set_index("utc")["px"].resample("5min",label="right",closed="left").last().dropna().astype(float)
    # right-labelled resampling can emit a synthetic 2026-01-01 00:00 label
    # from the final minutes of 2025. This is not 2026 raw data; clip the
    # resampled index back to the locked OOS window.
    s=s[(s.index>=START)&(s.index<END)]
    if len(s.index) and s.index.max()>=END:
        raise RuntimeError("V112 resampled series escaped locked OOS boundary")
    return s

def hourly_returns(series,horizon):
    idx=series.index
    base=idx[(idx.minute==0)&(idx>=START)&(idx<END)]
    exits=base+pd.Timedelta(minutes=int(horizon))
    a=series.reindex(base).to_numpy(dtype=float)
    b=series.reindex(exits).to_numpy(dtype=float)
    ok=np.isfinite(a)&np.isfinite(b)&(a!=0)
    return pd.DatetimeIndex(base[ok]),(b[ok]/a[ok]-1.0)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=r"D:\MT5_Backtests")
    ap.add_argument("--unlock",default="")
    args=ap.parse_args()
    if args.unlock!=UNLOCK:
        print("LOCKED: no 2023-2025 market file read.")
        return

    root=Path(args.root)
    base=root/"Research"/"Autonomous"/"guardian_edge_factory_v112_calendar_locked_oos"
    base.mkdir(parents=True,exist_ok=True)
    rid="GEF112-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    out=base/rid;out.mkdir(parents=True,exist_ok=False);t0=time.time()

    def status(step,total,msg,**extra):
        p={"run_id":rid,"engine_version":ENGINE_VERSION,"step":step,"steps":total,"percent":round(100*step/total,1),
           "elapsed_s":round(time.time()-t0,1),"message":msg,**extra}
        write_json(out/"LIVE_STATUS.json",p)
        tail=" | ".join(f"{k}={v}" for k,v in extra.items())
        print(f"[GEF112] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

    frozen=pd.DataFrame(CANDIDATES)
    frozen.to_csv(out/"FROZEN_OOS_CANDIDATES.csv",index=False)
    status(1,6,"exact locked-OOS candidates frozen",candidates=len(frozen),families=frozen["family"].nunique())

    markets=sorted(frozen["market"].unique())
    P={}
    for i,sym in enumerate(markets,1):
        P[sym]=load_market(root,sym)
        print(f"[GEF112] locked OOS price {i}/{len(markets)} {sym}",flush=True)
    status(2,6,"2023-2025 locked OOS market files opened",markets=len(markets))

    rows=[]
    for idx,r in frozen.iterrows():
        times,rets=hourly_returns(P[r["market"]],int(r["horizon"]))
        cand=times.hour.to_numpy()==int(r["hour"])
        ctrl=~cand
        orientation=int(r["orientation"])
        a=rets[cand]*orientation
        b=rets[ctrl]*orientation
        ct=times[cand]
        loo,looj=leave_one_year_out(ct,a)
        q025,q50,q975=month_block_bootstrap(ct,a,BOOTSTRAPS,SEED+idx)
        rec={
            "candidate_id":r["candidate_id"],
            "structural_family_key":r["family"],
            "target_market":r["market"],
            "hour":int(r["hour"]),
            "horizon_min":int(r["horizon"]),
            "orientation":orientation,
            "n":int(len(a)),
            "control_n":int(len(b)),
            "mean_bp":mean_bp(a),
            "control_mean_bp":mean_bp(b),
            "effect_bp":mean_bp(a)-mean_bp(b),
            "net1bp_mean_bp":mean_bp(a)-1,
            "trim2_mean_bp":trimmed_best_mean_bp(a,.02),
            "leave_one_year_out_min_mean_bp":loo,
            "leave_one_year_out_json":json.dumps(looj,sort_keys=True),
            "bootstrap_month_q025_bp":q025,
            "bootstrap_month_q50_bp":q50,
            "bootstrap_month_q975_bp":q975
        }
        gates=[
            rec["n"]>=500,
            rec["mean_bp"]>0,
            rec["effect_bp"]>0,
            rec["net1bp_mean_bp"]>0,
            rec["trim2_mean_bp"]>0,
            rec["leave_one_year_out_min_mean_bp"]>0,
            rec["bootstrap_month_q025_bp"]>0
        ]
        rec["locked_oos_candidate_pass"]=bool(all(gates))
        rec["failed_gate_count"]=int(sum(not bool(x) for x in gates))
        rows.append(rec)

    R=pd.DataFrame(rows)
    R.to_csv(out/"LOCKED_OOS_RESULTS.csv",index=False)
    status(3,6,"candidate locked-OOS scoring complete",candidate_passes=int(R["locked_oos_candidate_pass"].sum()))

    family_rows=[]
    aud=R[R["structural_family_key"]=="AUDUSD|H21"]
    chf=R[R["structural_family_key"]=="USDCHF|H23"]
    family_rows.append({
        "structural_family_key":"AUDUSD|H21",
        "required_candidates":1,
        "passing_candidates":int(aud["locked_oos_candidate_pass"].sum()),
        "family_oos_pass":bool(len(aud)==1 and aud["locked_oos_candidate_pass"].all())
    })
    family_rows.append({
        "structural_family_key":"USDCHF|H23",
        "required_candidates":2,
        "passing_candidates":int(chf["locked_oos_candidate_pass"].sum()),
        "family_oos_pass":bool(len(chf)==2 and chf["locked_oos_candidate_pass"].all())
    })
    F=pd.DataFrame(family_rows)
    F.to_csv(out/"LOCKED_OOS_FAMILY_RESULTS.csv",index=False)
    family_passes=int(F["family_oos_pass"].sum())
    status(4,6,"structural-family locked-OOS scoring complete",family_passes=family_passes)

    receipt={
        "run_id":rid,
        "status":"COMPLETE_V112_LOCKED_OOS_2023_2025",
        "engine_version":ENGINE_VERSION,
        "candidate_count":int(len(R)),
        "candidate_passes":int(R["locked_oos_candidate_pass"].sum()),
        "structural_family_count":int(len(F)),
        "structural_family_passes":family_passes,
        "2023_2025_accessed":True,
        "2026_accessed":False,
        "next":"HUMAN_REVIEW_ONLY; DO_NOT AUTO_ACTIVATE OR OPTIMIZE"
    }
    write_json(out/"RUN_RECEIPT.json",receipt)
    status(5,6,"receipt written");status(6,6,"DONE")
    print("\n=== V112 RECEIPT ===");print(json.dumps(receipt,indent=2))
    print("\n=== V112 CANDIDATE RESULTS ===");print(R.to_string(index=False))
    print("\n=== V112 FAMILY RESULTS ===");print(F.to_string(index=False))
    print("\nRUN:",out)

if __name__=="__main__":
    main()
