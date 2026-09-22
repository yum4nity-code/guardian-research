from pathlib import Path
import argparse, hashlib, json, math, re, time
import numpy as np
import pandas as pd
try:
    from scipy.stats import ttest_1samp
except Exception:
    ttest_1samp=None

ENGINE_VERSION="V107.2"
FORBIDDEN_YEAR=2023
HORIZONS=[60,120,240]
DISCOVERY_Q=.10
MAX_FROZEN=150
MIN_DISC=12
MIN_REP=12
MIN_VAL=15

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def mean_bp(x):
    x=np.asarray(x,dtype=float); x=x[np.isfinite(x)]
    return float(x.mean()*1e4) if len(x) else np.nan

def remove_best(x,k):
    x=np.asarray(x,dtype=float); x=x[np.isfinite(x)]
    if len(x)<=k:return np.nan
    return mean_bp(np.sort(x)[:-k])

def bh_qvalues(p):
    p=np.asarray(p,dtype=float); q=np.full(len(p),np.nan)
    finite=np.flatnonzero(np.isfinite(p))
    if not len(finite):return q
    order=finite[np.argsort(p[finite],kind="mergesort")]
    m=len(order); running=1.0
    for rev,idx in enumerate(order[::-1],1):
        rank=m-rev+1
        val=min(1.0,p[idx]*m/rank)
        running=min(running,val); q[idx]=running
    return q

def p_two_sided(x):
    x=np.asarray(x,dtype=float); x=x[np.isfinite(x)]
    if len(x)<3:return np.nan
    if ttest_1samp is not None:
        return float(ttest_1samp(x,0.0,nan_policy="omit").pvalue)
    sd=x.std(ddof=1)
    if not np.isfinite(sd) or sd==0:return 1.0 if abs(x.mean())<1e-15 else 0.0
    z=abs(x.mean())/(sd/math.sqrt(len(x)))
    return float(math.erfc(z/math.sqrt(2)))

def positive_year_fraction(times,vals):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,dtype=float)})
    d=d[np.isfinite(d["v"])].copy()
    if d.empty:return np.nan,{}
    d["year"]=d["t"].dt.year
    y=d.groupby("year")["v"].mean()*1e4
    return float((y>0).mean()),{str(int(k)):float(v) for k,v in y.items()}

def remove_best_month(times,vals):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,dtype=float)})
    d=d[np.isfinite(d["v"])].copy()
    if d.empty:return np.nan,None
    d["month"]=d["t"].dt.to_period("M").astype(str)
    totals=d.groupby("month")["v"].sum()
    best=str(totals.idxmax())
    return mean_bp(d.loc[d["month"]!=best,"v"].to_numpy()),best

def leave_one_year_out(times,vals):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,dtype=float)})
    d=d[np.isfinite(d["v"])].copy()
    if d.empty:return np.nan,{}
    d["year"]=d["t"].dt.year
    out={}
    for y in sorted(d["year"].unique()):
        out[str(int(y))]=mean_bp(d.loc[d["year"]!=y,"v"].to_numpy())
    return min(out.values()) if out else np.nan,out

def load_m1(root,sym,start_year,end_year):
    if end_year>=FORBIDDEN_YEAR:raise RuntimeError("V107 refuses 2023+")
    parts=[]
    for year in range(start_year,end_year+1):
        p=root/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
        if not p.exists():
            if year<=2012:continue
            raise RuntimeError(f"Missing required price file {p}")
        d=pd.read_parquet(p)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        pc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None and isinstance(d.index,pd.DatetimeIndex):
            d=d.reset_index();dc=d.columns[0]
        if dc is None or pc is None:raise RuntimeError(f"Bad price schema {p}")
        utc=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(hours=5)
        q=pd.DataFrame({"utc":utc,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
        q=q[q["utc"].dt.year.between(start_year,end_year)]
        parts.append(q)
    if not parts:return None
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    return q.set_index("utc")["px"]

def build_prices(root,end_year):
    market_dirs=root/"DataLake"/"raw"/"histdata"
    markets=sorted([p.name for p in market_dirs.iterdir() if p.is_dir() and (p/"M1").exists()])
    grid=pd.date_range("2009-01-01 00:00",f"{end_year}-12-31 23:55",freq="5min")
    P={}; valid=[]
    for sym in markets:
        try:
            raw=load_m1(root,sym,2009,end_year)
            if raw is None:continue
            s=raw.resample("5min",label="right",closed="left").last().reindex(grid)
            if s.loc["2010":"2022"].notna().sum()<100000:continue
            P[sym]=s.astype("float64");valid.append(sym)
            print(f"[GEF107] price {len(valid)} {sym}",flush=True)
        except Exception as e:
            print(f"[GEF107] skip market {sym}: {e}",flush=True)
    return grid,P,valid

def target_at_event(series,grid,event_time,horizon):
    ns=grid.view("int64")
    start=int(np.searchsorted(ns,pd.Timestamp(event_time).value,side="left"))
    if start>=len(grid):return np.nan,None
    k=horizon//5
    minute=(grid[start:].view("int64")//60_000_000_000).astype(np.int64)
    rel=np.flatnonzero((minute%horizon)==0)
    # Search up to seven calendar days for first actually tradable entry.
    max_i=min(len(grid)-k,start+7*24*12)
    for rr in rel:
        i=start+int(rr)
        if i>max_i or i+k>=len(grid):break
        a=series.iloc[i];b=series.iloc[i+k]
        if np.isfinite(a) and np.isfinite(b) and a!=0:
            return float(b/a-1),grid[i]
    return np.nan,None

def causal_z(values,min_periods=12):
    s=pd.Series(values,dtype=float)
    mu=s.expanding(min_periods=min_periods).mean().shift(1)
    sd=s.expanding(min_periods=min_periods).std().shift(1).replace(0,np.nan)
    return ((s-mu)/sd).to_numpy()

def feature_events(path):
    d=pd.read_parquet(path)
    if "first_vintage" not in d.columns or "first_value" not in d.columns:return {}
    q=pd.DataFrame({
      "first_vintage":pd.to_datetime(d["first_vintage"],errors="coerce"),
      "first_value":pd.to_numeric(d["first_value"],errors="coerce")
    }).dropna()
    q=q[q["first_vintage"].dt.year<=2022].sort_values("first_vintage").drop_duplicates("first_vintage",keep="last")
    if len(q)<30:return {}
    q["AVAILABLE_AT"]=q["first_vintage"].dt.normalize()+pd.Timedelta(days=1)
    v=q["first_value"].astype(float)
    feats={"level":v,"d1":v.diff(1),"d3":v.diff(3)}
    mu=v.rolling(24,min_periods=12).mean().shift(1)
    sd=v.rolling(24,min_periods=12).std().shift(1).replace(0,np.nan)
    feats["z24"]=(v-mu)/sd
    out={}; stem=re.sub(r"[^A-Za-z0-9_]+","_",path.stem)
    for name,x in feats.items():
        x=pd.Series(x,dtype=float)
        if name in ("d1","d3"):
            # Macro release changes: directional sign is the natural high-support event state.
            state_score=np.sign(x.to_numpy(dtype=float))
            mode="directional_change"
        else:
            # Level-like series: compare current value only with the prior expanding median.
            med=x.expanding(min_periods=12).median().shift(1)
            state_score=(x-med).to_numpy(dtype=float)
            mode="causal_median_side"
        out[f"alfred_{stem}_{name}"]=pd.DataFrame({
          "AVAILABLE_AT":q["AVAILABLE_AT"].to_numpy(),
          "value":x.to_numpy(),
          "state_score":state_score,
          "state_mode":mode
        })
    return out

def event_sample(ev,market_series,grid,horizon,state,direction=1,start=None,end=None,delay_days=0):
    times=pd.to_datetime(ev["AVAILABLE_AT"])+pd.Timedelta(days=int(delay_days))
    score=pd.to_numeric(ev["state_score"],errors="coerce").to_numpy()
    if state=="NEG":
        mask=np.isfinite(score)&(score<0)
    elif state=="POS":
        mask=np.isfinite(score)&(score>0)
    else:
        raise RuntimeError(f"Unsupported V107.2 state {state}")
    rows=[]
    for t in times[mask]:
        if start is not None and t<pd.Timestamp(start):continue
        if end is not None and t>=pd.Timestamp(end):continue
        r,entry=target_at_event(market_series,grid,t,horizon)
        if entry is not None and np.isfinite(r):rows.append((entry,r*direction))
    if not rows:return pd.DatetimeIndex([]),np.asarray([],dtype=float)
    return pd.DatetimeIndex([x[0] for x in rows]),np.asarray([x[1] for x in rows],dtype=float)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root)
    src=root/"DataLake"/"normalized"/"alfred_pre2023"
    files=sorted(src.glob("*_revision_summary_PRE2023.parquet"))
    if not files:raise RuntimeError(f"No ALFRED revision summaries at {src}")

    base=root/"Research"/"Autonomous"/"guardian_edge_factory_v107_alfred_event_level";base.mkdir(parents=True,exist_ok=True)
    rid="GEF107-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");out=base/rid;out.mkdir(parents=True,exist_ok=False);t0=time.time()
    def status(step,total,msg,**extra):
        p={"run_id":rid,"engine_version":ENGINE_VERSION,"step":step,"steps":total,"percent":round(100*step/total,1),
           "elapsed_s":round(time.time()-t0,1),"message":msg,**extra}
        write_json(out/"LIVE_STATUS.json",p)
        tail=" | ".join(f"{k}={v}" for k,v in extra.items())
        print(f"[GEF107] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

    status(1,12,"load ALFRED first-vintage summaries; future revision fields forbidden",files=len(files))
    features={}; provenance=[]
    for p in files:
        for k,v in feature_events(p).items():
            features[k]=v;provenance.append({"feature":k,"source":str(p),"events":int(len(v)),"state_mode":str(v["state_mode"].iloc[0]) if len(v) else ""})
    if not features:raise RuntimeError("No usable ALFRED causal features")
    pd.DataFrame(provenance).to_csv(out/"FEATURE_PROVENANCE.csv",index=False)
    status(2,12,"causal ALFRED release features built",features=len(features))

    grid13,P13,markets=build_prices(root,2013)
    if not markets:raise RuntimeError("No discovery price markets")
    status(3,12,"discovery price targets loaded through 2013 only",markets=len(markets))

    rows=[]; total=len(features)*2*len(markets)*len(HORIZONS); done=0
    for fname,ev in features.items():
      for state in ["NEG","POS"]:
       for sym in markets:
        for h in HORIZONS:
            done+=1
            dtimes,raw=event_sample(ev,P13[sym],grid13,h,state,1,"2010-01-01","2014-01-01")
            raw=raw[np.isfinite(raw)]
            if len(raw)<MIN_DISC:continue
            disc_years=int(pd.DatetimeIndex(dtimes).year.nunique())
            if disc_years<3:continue
            mu=float(raw.mean())
            if not np.isfinite(mu) or mu==0:continue
            direction=1 if mu>0 else -1
            dvals=raw*direction
            rows.append({
              "feature":fname,"state":state,"target_market":sym,"horizon_min":h,
              "direction_sign":direction,"direction":"LONG" if direction>0 else "SHORT",
              "disc_n":int(len(dvals)),"disc_years":disc_years,
              "disc_mean_bp":mean_bp(dvals),"disc_p_two":p_two_sided(raw)
            })
            if done%500==0:print(f"[GEF107] discovery {done}/{total}",flush=True)
    A=pd.DataFrame(rows)
    if A.empty:raise RuntimeError("No finite ALFRED discovery tests")
    A["bh_q"]=bh_qvalues(A["disc_p_two"].to_numpy())
    A=A.sort_values(["bh_q","disc_p_two","disc_mean_bp"],ascending=[True,True,False],kind="mergesort").reset_index(drop=True)
    A.to_csv(out/"DISCOVERY_ALL.csv",index=False)
    frozen=A[A["disc_p_two"].le(.05)&A["bh_q"].le(DISCOVERY_Q)].head(MAX_FROZEN).copy()
    status(4,12,"discovery complete",finite_tests=len(A),frozen=len(frozen))
    if frozen.empty:
        receipt={"run_id":rid,"status":"COMPLETE_V107_NO_DISCOVERY_SURVIVORS","engine_version":ENGINE_VERSION,
                 "features":len(features),"finite_tests":len(A),"2014_plus_accessed":False,"2023_2025_accessed":False,"2026_accessed":False}
        write_json(out/"RUN_RECEIPT.json",receipt);status(12,12,"DONE");print(json.dumps(receipt,indent=2));return

    frozen.to_csv(out/"FROZEN_PRE_2014.csv",index=False)
    write_json(out/"DISCOVERY_FREEZE.json",{"run_id":rid,"frozen":len(frozen),"sha256":sha256(out/"FROZEN_PRE_2014.csv"),
      "2014_plus_accessed_at_freeze":False,"2023_2025_accessed":False,"2026_accessed":False})
    status(5,12,"2010-2013 discovery candidates frozen before 2014+",frozen=len(frozen))

    grid17,P17,markets17=build_prices(root,2017)
    missing17=sorted(set(frozen["target_market"].astype(str))-set(markets17))
    if missing17: raise RuntimeError(f"Replication markets missing through 2017: {missing17}")

    rep=[]
    for r in frozen.itertuples(index=False):
        ev=features[r.feature]
        times,vals=event_sample(ev,P17[r.target_market],grid17,int(r.horizon_min),r.state,int(r.direction_sign),"2014-01-01","2018-01-01")
        pyf,yearly=positive_year_fraction(times,vals)
        passed=(len(vals)>=MIN_REP and mean_bp(vals)>0 and mean_bp(vals)-1>0 and pyf>=.50 and remove_best(vals,2)>0)
        rep.append({**r._asdict(),"rep_n":len(vals),"rep_mean_bp":mean_bp(vals),"rep_net1bp":mean_bp(vals)-1,
                    "rep_positive_year_fraction":pyf,"rep_yearly_json":json.dumps(yearly,sort_keys=True),
                    "rep_remove_best2_bp":remove_best(vals,2),"replication_pass":bool(passed)})
    R=pd.DataFrame(rep);R.to_csv(out/"REPLICATION_RESULTS.csv",index=False)
    rp=R[R["replication_pass"].astype(bool)].copy()
    status(6,12,"replication complete",survivors=len(rp))
    if rp.empty:
        receipt={"run_id":rid,"status":"COMPLETE_V107_REPLICATION_FAIL_ALL","engine_version":ENGINE_VERSION,
                 "discovery_frozen":len(frozen),"replication_survivors":0,"2018_plus_accessed":False,
                 "2023_2025_accessed":False,"2026_accessed":False}
        write_json(out/"RUN_RECEIPT.json",receipt);status(12,12,"DONE");print(json.dumps(receipt,indent=2));return

    robust=[]
    for r in rp.itertuples(index=False):
        ev=features[r.feature]
        times,vals=event_sample(ev,P17[r.target_market],grid17,int(r.horizon_min),r.state,int(r.direction_sign),"2014-01-01","2018-01-01")
        rm,bm=remove_best_month(times,vals);loo,looj=leave_one_year_out(times,vals)
        _,vlag1=event_sample(ev,P17[r.target_market],grid17,int(r.horizon_min),r.state,int(r.direction_sign),"2014-01-01","2018-01-01",1)
        _,vlag2=event_sample(ev,P17[r.target_market],grid17,int(r.horizon_min),r.state,int(r.direction_sign),"2014-01-01","2018-01-01",2)
        passed=(remove_best(vals,3)>0 and rm>0 and loo>0 and mean_bp(vlag1)>0 and mean_bp(vlag2)>0)
        robust.append({**r._asdict(),"robust_remove_best3_bp":remove_best(vals,3),"robust_remove_best_month_bp":rm,
                       "robust_best_month":bm,"robust_loo_min_bp":loo,"robust_loo_json":json.dumps(looj,sort_keys=True),
                       "robust_delay1d_bp":mean_bp(vlag1),"robust_delay2d_bp":mean_bp(vlag2),
                       "robustness_pass":bool(passed)})
    B=pd.DataFrame(robust);B.to_csv(out/"ROBUSTNESS_RESULTS.csv",index=False)
    rb=B[B["robustness_pass"].astype(bool)].copy()
    status(7,12,"pre-validation robustness complete",survivors=len(rb))
    if rb.empty:
        receipt={"run_id":rid,"status":"COMPLETE_V107_ROBUSTNESS_FAIL_ALL","engine_version":ENGINE_VERSION,
                 "discovery_frozen":len(frozen),"replication_survivors":len(rp),"robustness_survivors":0,
                 "2018_plus_accessed":False,"2023_2025_accessed":False,"2026_accessed":False}
        write_json(out/"RUN_RECEIPT.json",receipt);status(12,12,"DONE");print(json.dumps(receipt,indent=2));return

    rb.to_csv(out/"FROZEN_PRE_VALIDATION.csv",index=False)
    write_json(out/"PRE_VALIDATION_FREEZE.json",{"run_id":rid,"survivors":len(rb),"sha256":sha256(out/"FROZEN_PRE_VALIDATION.csv"),
      "2018_plus_accessed_at_freeze":False,"2023_2025_accessed":False,"2026_accessed":False})
    status(8,12,"survivors frozen before 2018+",survivors=len(rb))

    grid22,P22,markets22=build_prices(root,2022)
    missing22=sorted(set(rb["target_market"].astype(str))-set(markets22))
    if missing22: raise RuntimeError(f"Validation markets missing through 2022: {missing22}")

    valsout=[]
    for r in rb.itertuples(index=False):
        ev=features[r.feature]
        times,vals=event_sample(ev,P22[r.target_market],grid22,int(r.horizon_min),r.state,int(r.direction_sign),"2018-01-01","2023-01-01")
        pyf,yearly=positive_year_fraction(times,vals)
        rm,bm=remove_best_month(times,vals);loo,looj=leave_one_year_out(times,vals)
        passed=(len(vals)>=MIN_VAL and mean_bp(vals)>0 and mean_bp(vals)-1>0 and pyf>=.60 and
                remove_best(vals,3)>0 and remove_best(vals,5)>0 and rm>0 and loo>0)
        valsout.append({**r._asdict(),"val_n":len(vals),"val_mean_bp":mean_bp(vals),"val_net1bp":mean_bp(vals)-1,
                        "val_positive_year_fraction":pyf,"val_yearly_json":json.dumps(yearly,sort_keys=True),
                        "val_remove_best3_bp":remove_best(vals,3),"val_remove_best5_bp":remove_best(vals,5),
                        "val_remove_best_month_bp":rm,"val_best_month":bm,"val_loo_min_bp":loo,
                        "val_loo_json":json.dumps(looj,sort_keys=True),"validation_pass":bool(passed)})
    V=pd.DataFrame(valsout);V.to_csv(out/"VALIDATION_RESULTS.csv",index=False)
    final=V[V["validation_pass"].astype(bool)].copy();final.to_csv(out/"FINAL_SURVIVORS.csv",index=False)
    status(9,12,"validation complete",final_survivors=len(final))

    receipt={"run_id":rid,"status":"COMPLETE_V107_ALFRED_EVENT_LEVEL","engine_version":ENGINE_VERSION,
      "source_files":len(files),"causal_features":len(features),"finite_discovery_tests":len(A),
      "discovery_frozen":len(frozen),"replication_survivors":len(rp),"robustness_survivors":len(rb),
      "validation_survivors":len(final),"final_survivors_sha256":sha256(out/"FINAL_SURVIVORS.csv"),
      "statistical_unit":"one ALFRED first-vintage release event","state_design":"directional change for d1/d3; causal prior-median side for level/z24","future_revision_fields_used":False,
      "2023_2025_accessed":False,"2026_accessed":False,
      "next":"HUMAN_REVIEW_V107; IF SURVIVORS, RUN SEPARATE PREOOS FORENSIC"}
    write_json(out/"RUN_RECEIPT.json",receipt)
    report=["# GEF V107 — ALFRED event-level","",f"Run: {rid}",
      f"- source files: {len(files)}",f"- causal features: {len(features)}",f"- finite tests: {len(A)}",
      f"- frozen: {len(frozen)}",f"- replication survivors: {len(rp)}",f"- robustness survivors: {len(rb)}",
      f"- validation survivors: {len(final)}","- unit: one first-vintage release event","- future revision fields used: false",
      "- 2023-2025 accessed: false","- 2026 accessed: false"]
    (out/"V107_REPORT.md").write_text("\n".join(report),encoding="utf-8")
    status(10,12,"receipt/report written");status(11,12,"firewalls asserted");status(12,12,"DONE")
    print("\n=== V107 RECEIPT ===");print(json.dumps(receipt,indent=2))
    if len(final):
        print("\n=== V107 FINAL SURVIVORS ===")
        print(final[["feature","state","target_market","horizon_min","direction","rep_mean_bp","val_mean_bp","val_n"]].to_string(index=False))
    print("\nRUN:",out)

if __name__=="__main__":
    main()
