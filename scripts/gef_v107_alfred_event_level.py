from pathlib import Path
import argparse, hashlib, json, math, re, time
import numpy as np
import pandas as pd
try:
    from scipy.stats import ttest_1samp
except Exception:
    ttest_1samp=None

ENGINE_VERSION="V107.3"
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
    if not len(finite): return q
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

def build_prices(root,end_year,required=None):
    market_dirs=root/"DataLake"/"raw"/"histdata"
    markets=sorted([p.name for p in market_dirs.iterdir() if p.is_dir() and (p/"M1").exists()])
    if required is not None:
        req=set(map(str,required)); markets=[m for m in markets if m in req]
    grid=pd.date_range("2009-01-01 00:00",f"{end_year}-12-31 23:55",freq="5min")
    P={}; valid=[]
    for sym in markets:
        try:
            raw=load_m1(root,sym,2009,end_year)
            if raw is None:continue
            s=raw.resample("5min",label="right",closed="left").last().reindex(grid)
            if s.loc["2010":str(end_year)].notna().sum()<1000:continue
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
    max_i=min(len(grid)-k,start+7*24*12)
    for i in range(start,max_i+1):
        minute=int(grid[i].value//60_000_000_000)
        if minute%horizon!=0:continue
        a=series.iloc[i]; b=series.iloc[i+k]
        if np.isfinite(a) and np.isfinite(b) and a!=0:
            return float(b/a-1),grid[i]
    return np.nan,None

def first_existing(cols,names):
    low={str(c).lower():c for c in cols}
    for n in names:
        if n in low:return low[n]
    return None

def read_table(path):
    ext=path.suffix.lower()
    if ext==".parquet":return pd.read_parquet(path)
    if ext==".csv":return pd.read_csv(path,low_memory=False)
    return None

def extract_first_release_series(path):
    try:
        d=read_table(path)
    except Exception as e:
        return None,{"source":str(path),"status":"READ_ERROR","reason":repr(e)[:300]}
    if d is None or d.empty:
        return None,{"source":str(path),"status":"EMPTY_OR_UNSUPPORTED"}

    cols=list(d.columns)
    fv=first_existing(cols,["first_vintage"])
    fval=first_existing(cols,["first_value"])
    if fv is not None and fval is not None:
        q=pd.DataFrame({
            "AVAILABLE_AT":pd.to_datetime(d[fv],errors="coerce").dt.normalize()+pd.Timedelta(days=1),
            "value":pd.to_numeric(d[fval],errors="coerce")
        }).dropna().sort_values("AVAILABLE_AT").drop_duplicates("AVAILABLE_AT",keep="last")
        q=q[q["AVAILABLE_AT"].dt.year<=2022]
        return q,{"source":str(path),"status":"USED","schema":"revision_summary_first_vintage_first_value","events":int(len(q))}

    rt=first_existing(cols,["realtime_start","vintage_date","initial_vintage_date","available_date"])
    obs=first_existing(cols,["observation_date","date","period","observation_period"])
    val=first_existing(cols,["value","observation_value","first_value"])
    if rt is not None and val is not None:
        tmp=pd.DataFrame({
            "release":pd.to_datetime(d[rt],errors="coerce"),
            "value":pd.to_numeric(d[val],errors="coerce")
        })
        if obs is not None:
            tmp["obs"]=pd.to_datetime(d[obs],errors="coerce")
            tmp=tmp.dropna(subset=["release","value","obs"]).sort_values(["obs","release"]).drop_duplicates("obs",keep="first")
        else:
            tmp=tmp.dropna(subset=["release","value"]).sort_values("release").drop_duplicates("release",keep="first")
        q=pd.DataFrame({
            "AVAILABLE_AT":tmp["release"].dt.normalize()+pd.Timedelta(days=1),
            "value":tmp["value"]
        }).dropna().sort_values("AVAILABLE_AT").drop_duplicates("AVAILABLE_AT",keep="last")
        q=q[q["AVAILABLE_AT"].dt.year<=2022]
        return q,{"source":str(path),"status":"USED","schema":"raw_vintage_earliest_release","events":int(len(q))}

    return None,{"source":str(path),"status":"BLOCKED_SCHEMA","columns":"|".join(map(str,cols[:80]))}

def causal_centered_score(x,kind):
    s=pd.Series(x,dtype=float)
    if kind in ("d1","d3"):
        return np.sign(s.to_numpy(dtype=float))
    med=s.expanding(min_periods=8).median().shift(1)
    return np.sign((s-med).to_numpy(dtype=float))

def build_feature_catalog(src,out):
    files=sorted([p for p in src.rglob("*") if p.is_file() and p.suffix.lower() in (".parquet",".csv")])
    features={}; diag=[]
    for path in files:
        q,info=extract_first_release_series(path); diag.append(info)
        if q is None or len(q)<12:continue
        v=q["value"].astype(float).reset_index(drop=True)
        transforms={"level":v,"d1":v.diff(1),"d3":v.diff(3)}
        mu=v.rolling(24,min_periods=8).mean().shift(1)
        sd=v.rolling(24,min_periods=8).std().shift(1).replace(0,np.nan)
        transforms["z24"]=(v-mu)/sd
        stem=re.sub(r"[^A-Za-z0-9_]+","_",path.stem)
        for kind,x in transforms.items():
            score=causal_centered_score(x,kind)
            name=f"alfred_{stem}_{kind}"
            # Duplicate filenames can exist in nested dirs; disambiguate deterministically.
            if name in features:
                tag=hashlib.sha256(str(path).encode()).hexdigest()[:8]
                name=f"{name}_{tag}"
            features[name]=pd.DataFrame({
                "AVAILABLE_AT":q["AVAILABLE_AT"].to_numpy(),
                "value":x.to_numpy(),
                "score":score
            })
    pd.DataFrame(diag).to_csv(out/"ALFRED_SOURCE_DIAGNOSTICS.csv",index=False)
    return features,diag

def support_table(features,start,end):
    rows=[]
    a=pd.Timestamp(start); b=pd.Timestamp(end)
    for name,ev in features.items():
        t=pd.to_datetime(ev["AVAILABLE_AT"]); s=pd.to_numeric(ev["score"],errors="coerce").to_numpy()
        m=(t>=a)&(t<b)&np.isfinite(s)&(s!=0)
        tt=t[m]
        rows.append({
            "feature":name,
            "events_window":int(m.sum()),
            "years_window":int(pd.DatetimeIndex(tt).year.nunique()) if len(tt) else 0,
            "positive_score_events":int((s[m]>0).sum()),
            "negative_score_events":int((s[m]<0).sum())
        })
    return pd.DataFrame(rows)

def strategy_sample(ev,market_series,grid,horizon,orientation=1,start=None,end=None,delay_days=0):
    times=pd.to_datetime(ev["AVAILABLE_AT"])+pd.Timedelta(days=int(delay_days))
    score=pd.to_numeric(ev["score"],errors="coerce").to_numpy()
    rows=[]
    for t,s in zip(times,score):
        if not np.isfinite(s) or s==0:continue
        if start is not None and t<pd.Timestamp(start):continue
        if end is not None and t>=pd.Timestamp(end):continue
        r,entry=target_at_event(market_series,grid,t,horizon)
        if entry is not None and np.isfinite(r):
            rows.append((entry,r*np.sign(s)*orientation))
    if not rows:return pd.DatetimeIndex([]),np.asarray([],dtype=float)
    return pd.DatetimeIndex([x[0] for x in rows]),np.asarray([x[1] for x in rows],dtype=float)

def finish_no_support(out,rid,features,support,markets,reason):
    empty=pd.DataFrame(columns=["feature","target_market","horizon_min","orientation","disc_n","disc_mean_bp","disc_p_two","bh_q"])
    empty.to_csv(out/"DISCOVERY_ALL.csv",index=False)
    receipt={
        "run_id":rid,"status":"COMPLETE_V107_NO_DISCOVERY_SUPPORT","engine_version":ENGINE_VERSION,
        "causal_features":int(len(features)),"markets":int(len(markets)),
        "max_feature_events_2010_2013":int(support["events_window"].max()) if len(support) else 0,
        "reason":reason,"scientific_alpha_result":False,
        "2014_plus_market_returns_accessed":False,"2023_2025_accessed":False,"2026_accessed":False,
        "next":"CLOSE_ALFRED_FAMILY_AND_MOVE_TO_NEXT_AUDITED_SOURCE"
    }
    write_json(out/"RUN_RECEIPT.json",receipt)
    (out/"V107_REPORT.md").write_text("# V107.3\n\nNo adequate ALFRED discovery support. Family closed without alpha conclusion.\n",encoding="utf-8")
    print("\n=== V107 RECEIPT ===");print(json.dumps(receipt,indent=2))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root)
    src=root/"DataLake"/"normalized"/"alfred_pre2023"
    if not src.exists():raise RuntimeError(f"Missing {src}")

    base=root/"Research"/"Autonomous"/"guardian_edge_factory_v107_alfred_event_level";base.mkdir(parents=True,exist_ok=True)
    rid="GEF107-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");out=base/rid;out.mkdir(parents=True,exist_ok=False);t0=time.time()
    def status(step,total,msg,**extra):
        p={"run_id":rid,"engine_version":ENGINE_VERSION,"step":step,"steps":total,"percent":round(100*step/total,1),
           "elapsed_s":round(time.time()-t0,1),"message":msg,**extra}
        write_json(out/"LIVE_STATUS.json",p)
        tail=" | ".join(f"{k}={v}" for k,v in extra.items())
        print(f"[GEF107] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

    status(1,12,"audit every ALFRED pre-2023 table; future revision fields forbidden")
    features,diag=build_feature_catalog(src,out)
    if not features:
        support=pd.DataFrame(columns=["feature","events_window","years_window","positive_score_events","negative_score_events"])
        support.to_csv(out/"EVENT_SUPPORT_2010_2013.csv",index=False)
        finish_no_support(out,rid,features,support,[],"NO_USABLE_FIRST_RELEASE_SERIES")
        status(12,12,"DONE - no usable ALFRED first-release series");return
    status(2,12,"causal first-release feature catalog built",features=len(features),source_tables_used=sum(x.get("status")=="USED" for x in diag))

    support=support_table(features,"2010-01-01","2014-01-01")
    support.to_csv(out/"EVENT_SUPPORT_2010_2013.csv",index=False)
    eligible_support=set(support.loc[(support["events_window"]>=MIN_DISC)&(support["years_window"]>=3),"feature"].astype(str))
    status(3,12,"event support measured before reading discovery returns",
           eligible_features=len(eligible_support),
           max_events=int(support["events_window"].max()) if len(support) else 0)
    if not eligible_support:
        finish_no_support(out,rid,features,support,[],"NO_FEATURE_HAS_12_EVENTS_SPANNING_3_YEARS")
        status(12,12,"DONE - ALFRED support insufficient");return

    features={k:v for k,v in features.items() if k in eligible_support}
    grid13,P13,markets=build_prices(root,2013)
    if not markets:
        finish_no_support(out,rid,features,support,[],"NO_DISCOVERY_PRICE_MARKETS")
        status(12,12,"DONE - no discovery price markets");return
    status(4,12,"discovery prices loaded through 2013 only",markets=len(markets))

    rows=[];total=len(features)*len(markets)*len(HORIZONS);done=0
    for fname,ev in features.items():
        for sym in markets:
            for h in HORIZONS:
                done+=1
                dt,raw=strategy_sample(ev,P13[sym],grid13,h,1,"2010-01-01","2014-01-01")
                if len(raw)<MIN_DISC:continue
                years=int(dt.year.nunique())
                if years<3:continue
                m=float(np.mean(raw))
                if not np.isfinite(m) or m==0:continue
                orientation=1 if m>0 else -1
                vals=raw*orientation
                rows.append({
                    "feature":fname,"target_market":sym,"horizon_min":h,
                    "orientation":orientation,"direction_rule":"sign(feature_score)*orientation",
                    "disc_n":int(len(vals)),"disc_years":years,
                    "disc_mean_bp":mean_bp(vals),"disc_p_two":p_two_sided(raw)
                })
                if done%500==0:print(f"[GEF107] discovery {done}/{total}",flush=True)
    A=pd.DataFrame(rows)
    if A.empty:
        finish_no_support(out,rid,features,support,markets,"FEATURE_SUPPORT_EXISTS_BUT_NO_TRADABLE_DISCOVERY_SAMPLES")
        status(12,12,"DONE - no tradable discovery samples");return

    A["bh_q"]=bh_qvalues(A["disc_p_two"].to_numpy())
    A=A.sort_values(["bh_q","disc_p_two","disc_mean_bp"],ascending=[True,True,False],kind="mergesort").reset_index(drop=True)
    A.to_csv(out/"DISCOVERY_ALL.csv",index=False)
    frozen=A[A["disc_p_two"].le(.05)&A["bh_q"].le(DISCOVERY_Q)].head(MAX_FROZEN).copy()
    status(5,12,"discovery complete",finite_tests=len(A),frozen=len(frozen))
    if frozen.empty:
        receipt={"run_id":rid,"status":"COMPLETE_V107_NO_DISCOVERY_SURVIVORS","engine_version":ENGINE_VERSION,
                 "causal_features":len(features),"finite_tests":len(A),"discovery_frozen":0,
                 "2014_plus_market_returns_accessed":False,"2023_2025_accessed":False,"2026_accessed":False,
                 "next":"CLOSE_ALFRED_FAMILY_OR_REVIEW_ONLY_NON_RETURN_DIAGNOSTICS"}
        write_json(out/"RUN_RECEIPT.json",receipt);status(12,12,"DONE - no discovery survivors")
        print("\n=== V107 RECEIPT ===");print(json.dumps(receipt,indent=2));return

    frozen.to_csv(out/"FROZEN_PRE_2014.csv",index=False)
    write_json(out/"DISCOVERY_FREEZE.json",{"run_id":rid,"frozen":len(frozen),"sha256":sha256(out/"FROZEN_PRE_2014.csv"),
      "2014_plus_accessed_at_freeze":False,"2023_2025_accessed":False,"2026_accessed":False})
    status(6,12,"2010-2013 candidates frozen before 2014+",frozen=len(frozen))

    req=sorted(set(frozen["target_market"].astype(str)))
    grid17,P17,markets17=build_prices(root,2017,req)
    missing17=sorted(set(req)-set(markets17))
    if missing17:raise RuntimeError(f"Replication markets missing through 2017: {missing17}")

    rep=[]
    for r in frozen.itertuples(index=False):
        ev=features[r.feature]
        times,vals=strategy_sample(ev,P17[r.target_market],grid17,int(r.horizon_min),int(r.orientation),"2014-01-01","2018-01-01")
        pyf,yearly=positive_year_fraction(times,vals)
        passed=(len(vals)>=MIN_REP and mean_bp(vals)>0 and mean_bp(vals)-1>0 and pyf>=.50 and remove_best(vals,2)>0)
        rep.append({**r._asdict(),"rep_n":len(vals),"rep_mean_bp":mean_bp(vals),"rep_net1bp":mean_bp(vals)-1,
                    "rep_positive_year_fraction":pyf,"rep_yearly_json":json.dumps(yearly,sort_keys=True),
                    "rep_remove_best2_bp":remove_best(vals,2),"replication_pass":bool(passed)})
    R=pd.DataFrame(rep);R.to_csv(out/"REPLICATION_RESULTS.csv",index=False)
    rp=R[R["replication_pass"].astype(bool)].copy()
    status(7,12,"replication complete",survivors=len(rp))
    if rp.empty:
        receipt={"run_id":rid,"status":"COMPLETE_V107_REPLICATION_FAIL_ALL","engine_version":ENGINE_VERSION,
                 "discovery_frozen":len(frozen),"replication_survivors":0,"2018_plus_accessed":False,
                 "2023_2025_accessed":False,"2026_accessed":False}
        write_json(out/"RUN_RECEIPT.json",receipt);status(12,12,"DONE")
        print("\n=== V107 RECEIPT ===");print(json.dumps(receipt,indent=2));return

    robust=[]
    for r in rp.itertuples(index=False):
        ev=features[r.feature]
        times,vals=strategy_sample(ev,P17[r.target_market],grid17,int(r.horizon_min),int(r.orientation),"2014-01-01","2018-01-01")
        rm,bm=remove_best_month(times,vals);loo,looj=leave_one_year_out(times,vals)
        _,lag1=strategy_sample(ev,P17[r.target_market],grid17,int(r.horizon_min),int(r.orientation),"2014-01-01","2018-01-01",1)
        _,lag2=strategy_sample(ev,P17[r.target_market],grid17,int(r.horizon_min),int(r.orientation),"2014-01-01","2018-01-01",2)
        passed=(remove_best(vals,3)>0 and rm>0 and loo>0 and mean_bp(lag1)>0 and mean_bp(lag2)>0)
        robust.append({**r._asdict(),"robust_remove_best3_bp":remove_best(vals,3),"robust_remove_best_month_bp":rm,
                       "robust_best_month":bm,"robust_loo_min_bp":loo,"robust_loo_json":json.dumps(looj,sort_keys=True),
                       "robust_delay1d_bp":mean_bp(lag1),"robust_delay2d_bp":mean_bp(lag2),"robustness_pass":bool(passed)})
    B=pd.DataFrame(robust);B.to_csv(out/"ROBUSTNESS_RESULTS.csv",index=False)
    rb=B[B["robustness_pass"].astype(bool)].copy()
    status(8,12,"pre-validation robustness complete",survivors=len(rb))
    if rb.empty:
        receipt={"run_id":rid,"status":"COMPLETE_V107_ROBUSTNESS_FAIL_ALL","engine_version":ENGINE_VERSION,
                 "discovery_frozen":len(frozen),"replication_survivors":len(rp),"robustness_survivors":0,
                 "2018_plus_accessed":False,"2023_2025_accessed":False,"2026_accessed":False}
        write_json(out/"RUN_RECEIPT.json",receipt);status(12,12,"DONE")
        print("\n=== V107 RECEIPT ===");print(json.dumps(receipt,indent=2));return

    rb.to_csv(out/"FROZEN_PRE_VALIDATION.csv",index=False)
    write_json(out/"PRE_VALIDATION_FREEZE.json",{"run_id":rid,"survivors":len(rb),"sha256":sha256(out/"FROZEN_PRE_VALIDATION.csv"),
      "2018_plus_accessed_at_freeze":False,"2023_2025_accessed":False,"2026_accessed":False})
    status(9,12,"survivors frozen before 2018+",survivors=len(rb))

    req22=sorted(set(rb["target_market"].astype(str)))
    grid22,P22,markets22=build_prices(root,2022,req22)
    missing22=sorted(set(req22)-set(markets22))
    if missing22:raise RuntimeError(f"Validation markets missing through 2022: {missing22}")

    valsout=[]
    for r in rb.itertuples(index=False):
        ev=features[r.feature]
        times,vals=strategy_sample(ev,P22[r.target_market],grid22,int(r.horizon_min),int(r.orientation),"2018-01-01","2023-01-01")
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
    status(10,12,"validation complete",final_survivors=len(final))

    receipt={"run_id":rid,"status":"COMPLETE_V107_ALFRED_EVENT_LEVEL","engine_version":ENGINE_VERSION,
      "causal_features":len(features),"finite_discovery_tests":len(A),"discovery_frozen":len(frozen),
      "replication_survivors":len(rp),"robustness_survivors":len(rb),"validation_survivors":len(final),
      "final_survivors_sha256":sha256(out/"FINAL_SURVIVORS.csv"),
      "statistical_unit":"one ALFRED first-release event",
      "signal_rule":"sign(causal feature score) times discovery-frozen orientation",
      "future_revision_fields_used":False,"2023_2025_accessed":False,"2026_accessed":False,
      "next":"HUMAN_REVIEW_V107; IF SURVIVORS, RUN SEPARATE PREOOS FORENSIC"}
    write_json(out/"RUN_RECEIPT.json",receipt)
    (out/"V107_REPORT.md").write_text(
        "# GEF V107.3 — ALFRED event-level\n\n"
        f"Finite discovery tests: {len(A)}\n\nFrozen: {len(frozen)}\n\nReplication: {len(rp)}\n\n"
        f"Robustness: {len(rb)}\n\nValidation survivors: {len(final)}\n",encoding="utf-8")
    status(11,12,"receipt/report written");status(12,12,"DONE")
    print("\n=== V107 RECEIPT ===");print(json.dumps(receipt,indent=2))
    if len(final):
        print("\n=== V107 FINAL SURVIVORS ===")
        print(final[["feature","target_market","horizon_min","orientation","rep_mean_bp","val_mean_bp","val_n"]].to_string(index=False))
    print("\nRUN:",out)

if __name__=="__main__":
    main()
