from pathlib import Path
import argparse, hashlib, json, math, time
import numpy as np
import pandas as pd

ENGINE_VERSION="V111-C1-XAG-OOS-V2.0"
UNLOCK="OPEN_V111_C1_XAGUSD_OOS_2023_2025"
SOURCE_RUN="GEF111-20260922-163321"
START=pd.Timestamp("2023-01-01 00:00")
END=pd.Timestamp("2026-01-01 00:00")
MARKET="XAGUSD"
HOUR=11
HORIZON=60
ORIENTATION=-1
BOOTSTRAPS=5000
SEED=11101

def write_json(p,o):
    p.write_text(json.dumps(o,indent=2,default=str),encoding="utf-8")

def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def mean_bp(x):
    x=np.asarray(x,float);x=x[np.isfinite(x)]
    return float(x.mean()*1e4) if len(x) else np.nan

def trim_best_bp(x,pct):
    x=np.asarray(x,float);x=x[np.isfinite(x)]
    if not len(x): return np.nan
    k=int(math.ceil(len(x)*pct))
    if k<=0:return mean_bp(x)
    if k>=len(x):return np.nan
    return mean_bp(np.sort(x)[:-k])

def remove_best_k_bp(x,k):
    x=np.asarray(x,float);x=x[np.isfinite(x)]
    if len(x)<=k:return np.nan
    return mean_bp(np.sort(x)[:-k])

def month_bootstrap(times,vals,draws=BOOTSTRAPS,seed=SEED):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,float)})
    d=d[np.isfinite(d["v"])].copy()
    d["month"]=d["t"].dt.to_period("M").astype(str)
    groups=[g["v"].to_numpy(float) for _,g in d.groupby("month") if len(g)]
    if len(groups)<2:return (np.nan,)*5
    rng=np.random.default_rng(seed)
    out=np.empty(draws,float)
    for i in range(draws):
        pick=rng.integers(0,len(groups),size=len(groups))
        out[i]=mean_bp(np.concatenate([groups[j] for j in pick]))
    q=np.quantile(out,[.025,.10,.50,.90,.975])
    return tuple(float(v) for v in q)

def yearly(times,vals):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,float)})
    d=d[np.isfinite(d["v"])].copy()
    d["year"]=d["t"].dt.year
    y=d.groupby("year")["v"].mean()*1e4
    return {str(int(k)):float(v) for k,v in y.items()}

def loo(times,vals):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,float)})
    d=d[np.isfinite(d["v"])].copy()
    d["year"]=d["t"].dt.year
    out={}
    for y in sorted(d["year"].unique()):
        out[str(int(y))]=mean_bp(d.loc[d["year"]!=y,"v"].to_numpy())
    return (min(out.values()) if out else np.nan),out

def provenance(root):
    p=root/"Research"/"Autonomous"/"guardian_edge_factory_v111_calendar_preoos_forensic"/SOURCE_RUN/"FORENSIC_RESULTS.csv"
    if not p.exists(): raise RuntimeError(f"Missing V111 provenance file: {p}")
    d=pd.read_csv(p)
    q=d[d["candidate_id"].astype(str)=="C1"].copy()
    if len(q)!=1: raise RuntimeError(f"Expected exactly one C1 row, got {len(q)}")
    r=q.iloc[0]
    checks={
        "target_market":str(r["target_market"])==MARKET,
        "horizon_min":int(r["horizon_min"])==HORIZON,
        "orientation":int(r["orientation"])==ORIENTATION,
        "cell_type_hour":str(r["cell_type"])=="hour",
        "cell_id_contains_H11":"11" in str(r["cell_id"]),
        "preoos_mean_positive":float(r["mean_bp"])>0,
    }
    if not all(checks.values()):
        raise RuntimeError(f"V111 C1 provenance mismatch: {checks}; row={r.to_dict()}")
    return p,r.to_dict(),checks

def load_market(root):
    parts=[]
    for y in [2023,2024,2025]:
        p=root/"DataLake"/"raw"/"histdata"/MARKET/"M1"/f"{MARKET}_M1_{y}.parquet"
        if not p.exists(): raise RuntimeError(f"Missing locked OOS file {p}")
        d=pd.read_parquet(p)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        pc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None and isinstance(d.index,pd.DatetimeIndex):
            d=d.reset_index();dc=d.columns[0]
        if dc is None or pc is None: raise RuntimeError(f"Bad schema {p}")
        raw=pd.to_datetime(d[dc],errors="coerce")
        if (raw.dt.year>=2026).any(): raise RuntimeError(f"2026 contamination {p}")
        pseudo=raw+pd.Timedelta(hours=5)
        q=pd.DataFrame({"pseudo_utc":pseudo,"raw_time":raw,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
        q=q[(q["pseudo_utc"]>=START)&(q["pseudo_utc"]<END)]
        parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("pseudo_utc").drop_duplicates("pseudo_utc",keep="last")
    s=q.set_index("pseudo_utc")["px"].resample("5min",label="right",closed="left").last().dropna().astype(float)
    s=s[(s.index>=START)&(s.index<END)]
    if len(s) and s.index.max()>=END: raise RuntimeError("Resampled series escaped OOS boundary")
    return s

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=r"D:\MT5_Backtests")
    ap.add_argument("--out",required=True)
    ap.add_argument("--unlock",default="")
    a=ap.parse_args()
    if a.unlock!=UNLOCK:
        print("LOCKED: no 2023-2025 XAGUSD market file read.")
        return

    root=Path(a.root);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    t0=time.time()
    prov_path,prov,checks=provenance(root)
    print("PROVENANCE PASS:",checks,flush=True)
    print("V111 C1:",{k:prov.get(k) for k in ["candidate_id","cell_id","cell_type","target_market","horizon_min","orientation","n","mean_bp","net1bp_mean_bp","trim5_mean_bp","leave_one_year_out_min_mean_bp","bootstrap_month_q025_bp"]},flush=True)

    s=load_market(root)
    idx=s.index
    base=idx[(idx.minute==0)&(idx>=START)&(idx<END)]
    exits=base+pd.Timedelta(minutes=HORIZON)
    entry=s.reindex(base).to_numpy(float)
    exitp=s.reindex(exits).to_numpy(float)
    ok=np.isfinite(entry)&np.isfinite(exitp)&(entry!=0)
    times=pd.DatetimeIndex(base[ok])
    rawrets=(exitp[ok]/entry[ok]-1.0)
    cand=times.hour.to_numpy()==HOUR
    ctrl=~cand
    ct=times[cand]
    a_ret=rawrets[cand]*ORIENTATION
    b_ret=rawrets[ctrl]*ORIENTATION
    ce=entry[ok][cand]
    cx=exitp[ok][cand]

    q025,q10,q50,q90,q975=month_bootstrap(ct,a_ret)
    loo_min,loo_json=loo(ct,a_ret)
    mean=mean_bp(a_ret)
    control=mean_bp(b_ret)
    if mean<=0:
        existence="NEGATIVE"
    elif np.isfinite(q10) and q10>0:
        existence="POSITIVE_CONFIRMED"
    else:
        existence="POSITIVE_UNCERTAIN"

    ledger=pd.DataFrame({
        "source_entry_label":ct,
        "source_exit_label":ct+pd.Timedelta(minutes=HORIZON),
        "source_entry_px":ce,
        "source_exit_px":cx,
        "source_return":a_ret,
        "source_bp":a_ret*1e4,
        "orientation":ORIENTATION,
        "direction":"SHORT",
    })
    ledger.to_csv(out/"V111_C1_XAGUSD_OOS_EVENT_LEDGER.csv",index=False)

    result={
        "engine_version":ENGINE_VERSION,
        "source_v111_run":SOURCE_RUN,
        "provenance_file":str(prov_path),
        "provenance_sha256":sha256(prov_path),
        "candidate":{"candidate_id":"C1","market":MARKET,"hour":HOUR,"horizon_min":HORIZON,"orientation":ORIENTATION,"direction":"SHORT"},
        "window":{"start":str(START),"end_exclusive":str(END)},
        "n":int(len(a_ret)),
        "control_n":int(len(b_ret)),
        "mean_bp":mean,
        "control_mean_bp":control,
        "effect_bp":mean-control,
        "median_bp":float(np.median(a_ret)*1e4) if len(a_ret) else np.nan,
        "win_rate":float((a_ret>0).mean()) if len(a_ret) else np.nan,
        "net1bp_mean_bp":mean-1,
        "net2bp_mean_bp":mean-2,
        "net3bp_mean_bp":mean-3,
        "trim1_mean_bp":trim_best_bp(a_ret,.01),
        "trim2_mean_bp":trim_best_bp(a_ret,.02),
        "trim5_mean_bp":trim_best_bp(a_ret,.05),
        "remove_best10_mean_bp":remove_best_k_bp(a_ret,10),
        "remove_best20_mean_bp":remove_best_k_bp(a_ret,20),
        "yearly_mean_bp":yearly(ct,a_ret),
        "leave_one_year_out_min_bp":loo_min,
        "leave_one_year_out":loo_json,
        "month_bootstrap_q025_bp":q025,
        "month_bootstrap_q10_bp":q10,
        "month_bootstrap_q50_bp":q50,
        "month_bootstrap_q90_bp":q90,
        "month_bootstrap_q975_bp":q975,
        "v2_existence":existence,
        "v2_source_economic_proxy":"MINI_EDGE_SOURCE_PROXY" if mean-1>0 else "COVARIATE_ONLY_SOURCE_PROXY",
        "production_status":"NOT_AUDITED",
        "2026_accessed":False,
        "next":"IF_MEAN_POSITIVE_RUN_SEPARATE_FTMO_BID_ASK_ALIGNMENT_AND_EXECUTION_AUDIT; NO_RETUNING"
    }
    write_json(out/"SUMMARY.json",result)
    (out/"SUCCESS.flag").write_text("OK\n2026_ACCESS=false\n",encoding="utf-8")
    print("\n=== V111-C1 XAGUSD LOCKED OOS V2 COMPLETE ===",flush=True)
    print(json.dumps(result,indent=2),flush=True)
    print("ELAPSED_S",round(time.time()-t0,1),flush=True)

if __name__=="__main__":
    main()
