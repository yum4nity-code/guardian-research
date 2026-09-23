from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json, math
import numpy as np
import pandas as pd

VERSION="EA01-V2-EXISTING-OOS-AUDIT-1.0"
EXP={
 "signals_sha":"35ab88bb139a9b8c23f0ad28287718af9c1906af1eae6cfe78087464a255c3ac",
 "result_sha":"b052f49ae30b54169a5e11fdd424d5c5e8c3281937474557a324dad402a44713",
 "verdict_sha":"3d7075fea4dd800cc3562707dadf139c14e45f289c9339ff35481a0c288dcc12",
 "raw_n":944,"non_overlap_n":654,
 "raw_mean":0.10856319491605436,"raw_pf":1.1564669738705082,
 "c010_mean":0.06216246499009125,"c010_pf":1.0868273589119208,
 "c020_mean":0.01576173506412815,"c020_pf":1.0213334511927052,
}

def sha256(p:Path):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def pf(x):
    a=np.asarray(x,dtype=float)
    pos=a[a>0].sum()
    neg=-a[a<0].sum()
    return float(pos/neg) if neg>0 else (float("inf") if pos>0 else float("nan"))

def stats(x):
    a=np.asarray(x,dtype=float)
    a=a[np.isfinite(a)]
    return {"n":int(len(a)),"mean":float(a.mean()) if len(a) else None,
            "sum":float(a.sum()) if len(a) else None,"pf":pf(a),
            "win_pct":float((a>0).mean()*100) if len(a) else None}

def choose_time_col(df):
    names=["entry_time_utc","entry_utc","entry_time","entry_open_utc","signal_time_utc",
           "signal_time","timestamp_utc","timestamp","time_utc","time"]
    lower={str(c).lower():c for c in df.columns}
    ordered=[]
    for n in names:
        if n in lower: ordered.append(lower[n])
    ordered += [c for c in df.columns if c not in ordered and any(k in str(c).lower() for k in ["time","date","utc"])]
    best=None
    for c in ordered:
        try:
            s=pd.to_datetime(df[c],utc=True,errors="coerce")
            score=float(s.notna().mean())
            if score>0.95:
                best=(c,s); break
        except Exception: pass
    if best is None: raise RuntimeError("No timestamp column identified with >95% parse rate.")
    return best

def find_non_overlap(df,times):
    # Prefer an explicit frozen ledger flag that selects exactly the published 654 rows.
    for c in df.columns:
        n=str(c).lower()
        if any(k in n for k in ["non_overlap","nonoverlap","selected","keep","eligible"]):
            s=df[c]
            vals=set(str(v).strip().lower() for v in s.dropna().unique()[:20])
            if vals <= {"0","1","true","false","yes","no"}:
                mask=s.astype(str).str.strip().str.lower().isin(["1","true","yes"])
                if int(mask.sum())==EXP["non_overlap_n"]:
                    return mask.to_numpy(),f"explicit:{c}"
            try:
                z=pd.to_numeric(s,errors="coerce")
                mask=(z==1)
                if int(mask.sum())==EXP["non_overlap_n"]:
                    return mask.to_numpy(),f"explicit:{c}"
            except Exception: pass

    # Frozen horizon is 12 x M5 = 60m. This fallback is permitted only if it
    # reproduces the published N and outcome aggregates exactly.
    order=np.argsort(times.values)
    keep=np.zeros(len(df),dtype=bool)
    last=None
    for i in order:
        t=times.iloc[i]
        if pd.isna(t): continue
        if last is None or t>=last+pd.Timedelta(minutes=60):
            keep[i]=True; last=t
    if int(keep.sum())!=EXP["non_overlap_n"]:
        raise RuntimeError(f"No explicit non-overlap flag and 60m deterministic fallback gives {int(keep.sum())}, expected 654.")
    return keep,"deterministic_60m"

def numeric_columns(df):
    out={}
    for c in df.columns:
        s=pd.to_numeric(df[c],errors="coerce")
        if s.notna().mean()>0.95:
            out[c]=s.astype(float)
    return out

def identify_outcome(cols,mask,target_mean,target_pf,label):
    scored=[]
    for c,s in cols.items():
        a=s.to_numpy()[mask]
        a=a[np.isfinite(a)]
        if len(a)!=EXP["non_overlap_n"]: continue
        m=float(a.mean()); p=pf(a)
        if not math.isfinite(p): continue
        score=abs(m-target_mean)+0.25*abs(p-target_pf)
        scored.append((score,c,m,p))
    scored.sort()
    if not scored: raise RuntimeError(f"No numeric candidates for {label}.")
    score,c,m,p=scored[0]
    # Exact ledger parity should be very close. Stop rather than guessing.
    if abs(m-target_mean)>5e-5 or abs(p-target_pf)>5e-4:
        preview=scored[:10]
        raise RuntimeError(f"{label} parity not found. Best={preview}")
    return c

def trim_best(a,pct):
    a=np.asarray(a,dtype=float)
    k=max(1,int(math.ceil(len(a)*pct)))
    idx=np.argsort(a)
    return stats(a[idx[:-k]]) if k<len(a) else stats([])

def remove_best(a,k):
    a=np.asarray(a,dtype=float)
    idx=np.argsort(a)
    return stats(a[idx[:-k]]) if k<len(a) else stats([])

def max_drawdown(a):
    eq=np.cumsum(np.asarray(a,dtype=float))
    if not len(eq): return None
    peak=np.maximum.accumulate(np.r_[0.0,eq])
    dd=np.r_[0.0,eq]-peak
    return float(dd.min())

def cluster_bootstrap_month(times,vals,reps=20000,seed=20260923):
    d=pd.DataFrame({"t":times,"x":vals}).dropna()
    d["m"]=d["t"].dt.to_period("M").astype(str)
    clusters=[g["x"].to_numpy(dtype=float) for _,g in d.groupby("m",sort=True)]
    rng=np.random.default_rng(seed)
    means=np.empty(reps,dtype=float)
    k=len(clusters)
    for r in range(reps):
        picks=rng.integers(0,k,size=k)
        total=0.0; n=0
        for j in picks:
            arr=clusters[j]; total+=float(arr.sum()); n+=len(arr)
        means[r]=total/n
    return {
      "clusters":k,"reps":reps,
      "q10_one_sided90_lower":float(np.quantile(means,0.10)),
      "q05_two_sided90_lower":float(np.quantile(means,0.05)),
      "q025_two_sided95_lower":float(np.quantile(means,0.025)),
      "median":float(np.median(means)),
      "p_boot_mean_le_0":float(np.mean(means<=0))
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=r"D:\\MT5_Backtests")
    args=ap.parse_args()
    root=Path(args.root)
    src=root/"Research"/"Autonomous"/"edge_atlas"/"EA01-XR-RSI-LONG-V1-OOS-2023-2025"
    sig=src/"signals.csv"; res=src/"result.json"; ver=src/"verdict.json"
    for p in [sig,res,ver]:
        if not p.exists(): raise SystemExit(f"Missing {p}")

    hashes={"signals":sha256(sig),"result":sha256(res),"verdict":sha256(ver)}
    expected={"signals":EXP["signals_sha"],"result":EXP["result_sha"],"verdict":EXP["verdict_sha"]}
    parity={k:(hashes[k]==expected[k]) for k in hashes}
    if not all(parity.values()):
        raise SystemExit(f"HASH PARITY FAIL: {json.dumps({'actual':hashes,'expected':expected},indent=2)}")

    verdict=json.loads(ver.read_text(encoding="utf-8-sig"))
    result=json.loads(res.read_text(encoding="utf-8-sig"))
    if verdict.get("protected_2026_opened") is not False or result.get("protected_2026_opened") is not False:
        raise SystemExit("Protected-2026 provenance flag is not false.")

    df=pd.read_csv(sig,low_memory=False)
    if len(df)!=EXP["raw_n"]:
        raise SystemExit(f"RAW N parity fail: {len(df)} != 944")
    tcol,times=choose_time_col(df)
    if (times>=pd.Timestamp("2026-01-01",tz="UTC")).any():
        raise SystemExit("2026 timestamp detected. Audit blocked.")
    if (times<pd.Timestamp("2023-01-01",tz="UTC")).any():
        raise SystemExit("Pre-2023 timestamp detected in canonical OOS signal ledger.")

    mask,mask_method=find_non_overlap(df,times)
    nums=numeric_columns(df)
    raw_col=identify_outcome(nums,mask,EXP["raw_mean"],EXP["raw_pf"],"raw")
    c010_col=identify_outcome(nums,mask,EXP["c010_mean"],EXP["c010_pf"],"cost0.10")
    c020_col=identify_outcome(nums,mask,EXP["c020_mean"],EXP["c020_pf"],"cost0.20")

    sel=pd.DataFrame({
      "time":times[mask].reset_index(drop=True),
      "raw":nums[raw_col].to_numpy()[mask],
      "c010":nums[c010_col].to_numpy()[mask],
      "c020":nums[c020_col].to_numpy()[mask],
    }).sort_values("time").reset_index(drop=True)

    # Exact aggregate parity.
    agg={"raw":stats(sel.raw),"cost010":stats(sel.c010),"cost020":stats(sel.c020)}
    checks={
      "raw_mean":abs(agg["raw"]["mean"]-EXP["raw_mean"])<5e-5,
      "raw_pf":abs(agg["raw"]["pf"]-EXP["raw_pf"])<5e-4,
      "c010_mean":abs(agg["cost010"]["mean"]-EXP["c010_mean"])<5e-5,
      "c010_pf":abs(agg["cost010"]["pf"]-EXP["c010_pf"])<5e-4,
      "c020_mean":abs(agg["cost020"]["mean"]-EXP["c020_mean"])<5e-5,
      "c020_pf":abs(agg["cost020"]["pf"]-EXP["c020_pf"])<5e-4,
    }
    if not all(checks.values()):
        raise SystemExit(f"AGGREGATE PARITY FAIL: {json.dumps({'agg':agg,'checks':checks},indent=2)}")

    sel["year"]=sel.time.dt.year
    sel["quarter"]=sel.time.dt.to_period("Q").astype(str)
    sel["month"]=sel.time.dt.to_period("M").astype(str)

    yearly={}
    for y,g in sel.groupby("year"):
        yearly[str(int(y))]={"cost010":stats(g.c010),"cost020":stats(g.c020)}

    monthly=[]
    for m,g in sel.groupby("month",sort=True):
        monthly.append({"month":m,**{f"c010_{k}":v for k,v in stats(g.c010).items()},
                         **{f"c020_{k}":v for k,v in stats(g.c020).items()}})

    quarterly=[]
    for q,g in sel.groupby("quarter",sort=True):
        quarterly.append({"quarter":q,**{f"c010_{k}":v for k,v in stats(g.c010).items()},
                           **{f"c020_{k}":v for k,v in stats(g.c020).items()}})

    loo={}
    years=sorted(sel.year.unique())
    for y in years:
        g=sel[sel.year!=y]
        loo[str(int(y))]={"cost010":stats(g.c010),"cost020":stats(g.c020)}

    boot010=cluster_bootstrap_month(sel.time,sel.c010)
    boot020=cluster_bootstrap_month(sel.time,sel.c020,seed=20260924)

    trims={
      "cost010":{"trim_best_1pct":trim_best(sel.c010,0.01),"trim_best_2pct":trim_best(sel.c010,0.02)},
      "cost020":{"trim_best_1pct":trim_best(sel.c020,0.01),"trim_best_2pct":trim_best(sel.c020,0.02)}
    }
    exbest={"cost010":{},"cost020":{}}
    for k in [1,3,5,10]:
        exbest["cost010"][str(k)]=remove_best(sel.c010,k)
        exbest["cost020"][str(k)]=remove_best(sel.c020,k)

    def concentration(a):
        a=np.asarray(a,float); pos=np.sort(a[a>0])[::-1]; total=pos.sum()
        def share(k): return float(pos[:min(k,len(pos))].sum()/total) if total>0 else None
        return {"positive_sum":float(total),"best1_share":share(1),"best5_share":share(5),
                "top1pct_share":share(max(1,int(math.ceil(len(a)*0.01))))}
    conc={"cost010":concentration(sel.c010),"cost020":concentration(sel.c020)}

    def rolling(a,w=100):
        s=pd.Series(a,dtype=float).rolling(w).mean().dropna()
        return {"window":w,"windows":int(len(s)),"min_mean":float(s.min()),"median_mean":float(s.median()),
                "max_mean":float(s.max()),"positive_fraction":float((s>0).mean())}
    rolling100={"cost010":rolling(sel.c010),"cost020":rolling(sel.c020)}

    month_pos010=float(np.mean([r["c010_mean"]>0 for r in monthly]))
    quarter_pos010=float(np.mean([r["c010_mean"]>0 for r in quarterly]))

    existence="NEGATIVE"
    if agg["cost010"]["mean"]>0:
        existence="POSITIVE_CONFIRMED" if boot010["q10_one_sided90_lower"]>0 else "POSITIVE_UNCERTAIN"

    economics="COVARIATE_ONLY"
    stress="STRESS_FRAGILE"
    if agg["cost010"]["mean"]>0:
        economics="MINI_EDGE"
    if agg["cost020"]["mean"]>=0:
        stress="STRESS_POSITIVE"

    report={
      "schema":1,"version":VERSION,"status":"COMPLETE_READ_ONLY_EXISTING_OOS_AUDIT",
      "candidate_id":"EA01-XR-RSI-LONG-V1","historical_verdict":"KILL_PRESERVED",
      "source_dir":str(src),"hash_parity":parity,"aggregate_parity":checks,
      "detected_schema":{"timestamp_column":tcol,"non_overlap_method":mask_method,
                         "raw_outcome_column":raw_col,"cost010_outcome_column":c010_col,
                         "cost020_outcome_column":c020_col},
      "aggregate":agg,"yearly":yearly,"leave_one_year_out":loo,
      "monthly":monthly,"quarterly":quarterly,
      "month_cluster_bootstrap":{"cost010":boot010,"cost020":boot020},
      "trim_best":trims,"remove_best":exbest,"positive_concentration":conc,
      "rolling100":rolling100,
      "cumulative":{"cost010_max_drawdown_R":max_drawdown(sel.c010),
                    "cost020_max_drawdown_R":max_drawdown(sel.c020)},
      "stability":{"positive_month_fraction_cost010":month_pos010,
                   "positive_quarter_fraction_cost010":quarter_pos010},
      "v2_classification":{"existence":existence,"economic_size":economics,"stress":stress,
                           "ensemble_status":"NOT_TESTED","production_status":"NOT_PRODUCTION_READY"},
      "protected_2026_opened":False,
      "new_market_data_accessed":False,
      "strategy_rerun":False,
      "parameter_search":False,
      "notes":["Diagnostics only. No subgroup selection is authorized.",
               "Historical KILL is preserved; V2 classification is additive.",
               "Dollar translation is intentionally omitted because this probe is endpoint-based and production sizing is unresolved."]
    }

    out=root/"Research"/"Autonomous"/"edge_atlas"/"EA01-XR-RSI-LONG-V1-V2-AUDIT"
    out.mkdir(parents=True,exist_ok=True)
    (out/"EA01_V2_AUDIT.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    pd.DataFrame(monthly).to_csv(out/"EA01_V2_MONTHLY.csv",index=False)
    pd.DataFrame(quarterly).to_csv(out/"EA01_V2_QUARTERLY.csv",index=False)

    print("=== EA01 V2 EXISTING-OOS AUDIT RECEIPT ===")
    print(json.dumps({
      "version":VERSION,"candidate":"EA01-XR-RSI-LONG-V1",
      "hash_parity":parity,"aggregate_parity":checks,
      "raw_signals":len(df),"non_overlap":int(mask.sum()),
      "aggregate":agg,"bootstrap_cost010":boot010,
      "trim_cost010":trims["cost010"],"loo_cost010":{y:v["cost010"] for y,v in loo.items()},
      "max_drawdown_R_cost010":report["cumulative"]["cost010_max_drawdown_R"],
      "positive_month_fraction_cost010":month_pos010,
      "v2_classification":report["v2_classification"],
      "protected_2026_opened":False,"output":str(out)
    },indent=2))

if __name__=="__main__":
    main()
