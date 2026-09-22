from pathlib import Path
import argparse, hashlib, json, math, re, time
import numpy as np
import pandas as pd
try:
    from scipy.stats import ttest_1samp
except Exception:
    ttest_1samp=None

ENGINE_VERSION="V109.0"
FORBIDDEN_YEAR=2023
HORIZONS=[60,120,240]
DISCOVERY_Q=.10
MAX_FROZEN=150
MIN_DISC=12
MIN_REP=12
MIN_VAL=15
GENERIC_COST_BP=1.0

RAW_PATTERNS=[
    "bid_to_cover","bid to cover",
    "high_yield","high yield","high_investment_rate","high investment rate",
    "high_discnt_rate","high_discount_rate","high discount rate","high_price","high price",
    "avg_med_yield","average median yield","avg_med_investment_rate","average median investment rate",
    "avg_med_discnt_rate","avg_med_discount_rate","average median discount rate","avg_med_price","average median price",
    "int_rate","interest_rate","interest rate","coupon_rate","coupon rate",
    "allocation_percentage","allocation percentage",
    "competitive_accepted","competitive accepted","competitive_tenders","competitive tenders",
    "direct_bidder_accepted","direct bidder accepted","direct_bidder_tenders","direct bidder tenders",
    "indirect_bidder_accepted","indirect bidder accepted","indirect_bidder_tenders","indirect bidder tenders",
    "primary_dealer_accepted","primary dealer accepted","primary_dealer_tenders","primary dealer tenders",
    "total_accepted","total accepted","total_tenders","total tendered","total_tendered",
    "noncomp_accepted","noncompetitive accepted","noncomp_tenders","noncompetitive tenders"
]

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def norm_name(x):
    return re.sub(r"[^a-z0-9]+","_",str(x).strip().lower()).strip("_")

def to_num(s):
    if pd.api.types.is_numeric_dtype(s):
        return pd.to_numeric(s,errors="coerce")
    z=s.astype("string").str.replace(",","",regex=False).str.replace("$","",regex=False).str.replace("%","",regex=False)
    z=z.str.replace(r"^\((.*)\)$",r"-\1",regex=True)
    return pd.to_numeric(z,errors="coerce")

def mean_bp(x):
    x=np.asarray(x,dtype=float);x=x[np.isfinite(x)]
    return float(x.mean()*1e4) if len(x) else np.nan

def remove_best(x,k):
    x=np.asarray(x,dtype=float);x=x[np.isfinite(x)]
    if len(x)<=k:return np.nan
    return mean_bp(np.sort(x)[:-k])

def p_two_sided(x):
    x=np.asarray(x,dtype=float);x=x[np.isfinite(x)]
    if len(x)<3:return np.nan
    if ttest_1samp is not None:
        return float(ttest_1samp(x,0.0,nan_policy="omit").pvalue)
    sd=x.std(ddof=1)
    if not np.isfinite(sd) or sd==0:return 1.0 if abs(x.mean())<1e-15 else 0.0
    z=abs(x.mean())/(sd/math.sqrt(len(x)))
    return float(math.erfc(z/math.sqrt(2)))

def bh_qvalues(p):
    p=np.asarray(p,dtype=float);q=np.full(len(p),np.nan)
    finite=np.flatnonzero(np.isfinite(p))
    if not len(finite):return q
    order=finite[np.argsort(p[finite],kind="mergesort")]
    m=len(order);running=1.0
    for rev,idx in enumerate(order[::-1],1):
        rank=m-rev+1;val=min(1.0,p[idx]*m/rank);running=min(running,val);q[idx]=running
    return q

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
    totals=d.groupby("month")["v"].sum();best=str(totals.idxmax())
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

def find_col(cols,candidates):
    norm={norm_name(c):c for c in cols}
    for x in candidates:
        nx=norm_name(x)
        if nx in norm:return norm[nx]
    return None

def load_source(root):
    p=root/"DataLake"/"normalized"/"treasury_auctions_pre2023"/"treasury_auctions_PRE2023.csv"
    if not p.exists():raise RuntimeError(f"Missing canonical Treasury source {p}")
    d=pd.read_csv(p,low_memory=False)
    ac=find_col(d.columns,["auction_date"])
    if ac is None:raise RuntimeError("Treasury source missing auction_date")
    d["_auction_date"]=pd.to_datetime(d[ac],errors="coerce").dt.normalize()
    d=d[d["_auction_date"].notna()&(d["_auction_date"].dt.year<=2022)].copy()
    if d.empty:raise RuntimeError("Treasury source empty <=2022")
    if int(d["_auction_date"].dt.year.max())<2022:raise RuntimeError("Treasury source does not reach 2022")
    tc=find_col(d.columns,["security_type","security type"])
    term=find_col(d.columns,["security_term","security term"])
    if tc is None and term is None:raise RuntimeError("Cannot identify Treasury security_type/security_term bucket")
    parts=[]
    if tc is not None:parts.append(d[tc].astype("string").fillna("NA").str.strip())
    if term is not None:parts.append(d[term].astype("string").fillna("NA").str.strip())
    bucket=parts[0]
    for s in parts[1:]:bucket=bucket+"|"+s
    d["_bucket"]=bucket
    d["_AVAILABLE_AT"]=d["_auction_date"]+pd.Timedelta(days=1)
    return p,d,ac,tc,term

def semantic_numeric_columns(d,pre):
    out=[]
    for c in d.columns:
        if str(c).startswith("_"):continue
        n=norm_name(c)
        if not any(norm_name(p) in n or n in norm_name(p) for p in RAW_PATTERNS):continue
        v=to_num(pre[c])
        if v.notna().sum()<40 or v.nunique(dropna=True)<5:continue
        out.append(c)
    return sorted(set(out),key=lambda x:norm_name(x))

def first_matching(cols,patterns):
    for p in patterns:
        c=find_col(cols,[p])
        if c is not None:return c
    return None

def add_derived(d,pre):
    specs=[
      ("competitive_acceptance_rate",["competitive_accepted"],["competitive_tenders"]),
      ("total_acceptance_rate",["total_accepted"],["total_tendered","total_tenders"]),
      ("direct_accepted_share",["direct_bidder_accepted"],["competitive_accepted"]),
      ("indirect_accepted_share",["indirect_bidder_accepted"],["competitive_accepted"]),
      ("primary_dealer_accepted_share",["primary_dealer_accepted"],["competitive_accepted"])
    ]
    made=[]
    for name,npats,dpats in specs:
        num=first_matching(d.columns,npats);den=first_matching(d.columns,dpats)
        if num is None or den is None:continue
        a=to_num(d[num]);b=to_num(d[den]).replace(0,np.nan)
        x=a/b
        xp=x.loc[pre.index]
        if xp.notna().sum()<40 or xp.nunique(dropna=True)<5:continue
        d[name]=x;made.append(name)
    return made

def build_event_features(d,rawcols):
    features={};meta=[]
    for bucket,g in d.sort_values("_auction_date").groupby("_bucket",sort=True):
        gp=g[g["_auction_date"].dt.year.between(2009,2013)]
        if len(gp)<20:continue
        for c in rawcols:
            v=to_num(g[c])
            if v.notna().sum()<20:continue
            # Level relative to prior median.
            med=v.expanding(min_periods=8).median().shift(1)
            score_level=np.sign((v-med).to_numpy(dtype=float))
            # One-auction change.
            score_d1=np.sign(v.diff(1).to_numpy(dtype=float))
            for kind,score in [("level",score_level),("d1",score_d1)]:
                name=f"treasury_{norm_name(bucket)}_{norm_name(c)}_{kind}"
                ev=pd.DataFrame({
                    "AVAILABLE_AT":g["_AVAILABLE_AT"].to_numpy(),
                    "score":score
                })
                m=(pd.to_datetime(ev["AVAILABLE_AT"]).dt.year.between(2010,2013))&np.isfinite(score)&(score!=0)
                years=pd.DatetimeIndex(pd.to_datetime(ev.loc[m,"AVAILABLE_AT"])).year.nunique() if m.any() else 0
                if int(m.sum())<MIN_DISC or years<3:continue
                features[name]=ev
                meta.append({"feature":name,"bucket":str(bucket),"raw_column":str(c),"transform":kind,
                             "disc_source_events":int(m.sum()),"disc_source_years":int(years)})
    return features,pd.DataFrame(meta)

def load_m1(root,sym,start_year,end_year):
    if end_year>=FORBIDDEN_YEAR:raise RuntimeError("V109 refuses 2023+")
    parts=[]
    for year in range(start_year,end_year+1):
        p=root/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
        if not p.exists():
            if year<=2012:continue
            raise RuntimeError(f"Missing price file {p}")
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
    # Actual tradable 5-minute bars only.
    s=q.set_index("utc")["px"].resample("5min",label="right",closed="left").last().dropna()
    return s.astype(float)

def build_prices(root,end_year,required=None):
    base=root/"DataLake"/"raw"/"histdata"
    markets=sorted([p.name for p in base.iterdir() if p.is_dir() and (p/"M1").exists()])
    if required is not None:
        req=set(map(str,required));markets=[m for m in markets if m in req]
    P={};valid=[]
    for sym in markets:
        try:
            s=load_m1(root,sym,2009,end_year)
            if s is None or len(s)<1000:continue
            P[sym]=s;valid.append(sym);print(f"[GEF109] price {len(valid)} {sym}",flush=True)
        except Exception as e:
            print(f"[GEF109] skip market {sym}: {e}",flush=True)
    return P,valid

def target_return(series,event_time,horizon):
    idx=series.index
    t=pd.Timestamp(event_time)
    i=int(idx.searchsorted(t,side="left"))
    if i>=len(idx):return np.nan,None
    entry=idx[i]
    if entry>t+pd.Timedelta(days=7):return np.nan,None
    desired=entry+pd.Timedelta(minutes=int(horizon))
    j=int(idx.searchsorted(desired,side="left"))
    if j>=len(idx):return np.nan,None
    exit_t=idx[j]
    if exit_t>desired+pd.Timedelta(minutes=30):return np.nan,None
    a=float(series.iloc[i]);b=float(series.iloc[j])
    if not np.isfinite(a) or not np.isfinite(b) or a==0:return np.nan,None
    return b/a-1.0,entry

def event_sample(ev,series,horizon,orientation=1,start=None,end=None,delay_days=0):
    times=pd.to_datetime(ev["AVAILABLE_AT"])+pd.Timedelta(days=int(delay_days))
    scores=pd.to_numeric(ev["score"],errors="coerce").to_numpy()
    rows=[]
    for t,s in zip(times,scores):
        if not np.isfinite(s) or s==0:continue
        if start is not None and t<pd.Timestamp(start):continue
        if end is not None and t>=pd.Timestamp(end):continue
        r,entry=target_return(series,t,horizon)
        if entry is not None and np.isfinite(r):rows.append((entry,r*np.sign(s)*orientation))
    if not rows:return pd.DatetimeIndex([]),np.asarray([],dtype=float)
    return pd.DatetimeIndex([x[0] for x in rows]),np.asarray([x[1] for x in rows],dtype=float)

def finish(out,receipt):
    write_json(out/"RUN_RECEIPT.json",receipt)
    print("\n=== V109 RECEIPT ===");print(json.dumps(receipt,indent=2))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root)
    base=root/"Research"/"Autonomous"/"guardian_edge_factory_v109_treasury_event_level";base.mkdir(parents=True,exist_ok=True)
    rid="GEF109-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");out=base/rid;out.mkdir(parents=True,exist_ok=False);t0=time.time()
    def status(step,total,msg,**extra):
        p={"run_id":rid,"engine_version":ENGINE_VERSION,"step":step,"steps":total,"percent":round(100*step/total,1),
           "elapsed_s":round(time.time()-t0,1),"message":msg,**extra}
        write_json(out/"LIVE_STATUS.json",p)
        tail=" | ".join(f"{k}={v}" for k,v in extra.items())
        print(f"[GEF109] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

    status(1,12,"load canonical Treasury auction source; no market returns yet")
    source,d,ac,tc,term=load_source(root)
    pre=d[d["_auction_date"].dt.year.between(2009,2013)].copy()
    rawcols=semantic_numeric_columns(d,pre)
    derived=add_derived(d,pre)
    rawcols=sorted(set(rawcols+derived),key=norm_name)
    if not rawcols:
        receipt={"run_id":rid,"status":"COMPLETE_V109_NO_SOURCE_FEATURES","engine_version":ENGINE_VERSION,
                 "edge_trials":0,"market_returns_accessed":False,"2023_2025_accessed":False,"2026_accessed":False}
        finish(out,receipt);status(12,12,"DONE");return
    pd.DataFrame({"raw_feature":rawcols}).to_csv(out/"FROZEN_RAW_FEATURE_CATALOG.csv",index=False)
    status(2,12,"raw auction feature catalog frozen from <=2013 source support",
           rows=len(d),raw_features=len(rawcols),derived_features=len(derived))

    features,meta=build_event_features(d,rawcols)
    meta.to_csv(out/"FROZEN_EVENT_FEATURES.csv",index=False)
    if not features:
        receipt={"run_id":rid,"status":"COMPLETE_V109_NO_EVENT_FEATURE_SUPPORT","engine_version":ENGINE_VERSION,
                 "raw_features":len(rawcols),"edge_trials":0,"market_returns_accessed":False,
                 "2023_2025_accessed":False,"2026_accessed":False}
        finish(out,receipt);status(12,12,"DONE");return
    status(3,12,"bucketed event features frozen before discovery returns",event_features=len(features),
           buckets=int(meta["bucket"].nunique()) if len(meta) else 0)

    P13,markets=build_prices(root,2013)
    if not markets:
        receipt={"run_id":rid,"status":"COMPLETE_V109_NO_DISCOVERY_MARKETS","engine_version":ENGINE_VERSION,
                 "market_returns_accessed":False,"2023_2025_accessed":False,"2026_accessed":False}
        finish(out,receipt);status(12,12,"DONE");return
    status(4,12,"discovery prices loaded through 2013 only",markets=len(markets))

    rows=[];total=len(features)*len(markets)*len(HORIZONS);done=0
    for fname,ev in features.items():
        for sym in markets:
            for h in HORIZONS:
                done+=1
                times,raw=event_sample(ev,P13[sym],h,1,"2010-01-01","2014-01-01")
                if len(raw)<MIN_DISC:continue
                years=int(times.year.nunique())
                if years<3:continue
                mu=float(np.mean(raw))
                if not np.isfinite(mu) or mu==0:continue
                orientation=1 if mu>0 else -1
                vals=raw*orientation
                rows.append({"feature":fname,"target_market":sym,"horizon_min":h,"orientation":orientation,
                             "disc_n":len(vals),"disc_years":years,"disc_mean_bp":mean_bp(vals),"disc_p_two":p_two_sided(raw)})
                if done%1000==0:print(f"[GEF109] discovery {done}/{total}",flush=True)
    A=pd.DataFrame(rows)
    if A.empty:
        receipt={"run_id":rid,"status":"COMPLETE_V109_NO_TRADABLE_DISCOVERY_SUPPORT","engine_version":ENGINE_VERSION,
                 "event_features":len(features),"markets":len(markets),"scientific_alpha_result":False,
                 "2014_plus_market_returns_accessed":False,"2023_2025_accessed":False,"2026_accessed":False}
        finish(out,receipt);status(12,12,"DONE");return
    A["bh_q"]=bh_qvalues(A["disc_p_two"].to_numpy())
    A=A.sort_values(["bh_q","disc_p_two","disc_mean_bp"],ascending=[True,True,False],kind="mergesort").reset_index(drop=True)
    A.to_csv(out/"DISCOVERY_ALL.csv",index=False)
    frozen=A[A["disc_p_two"].le(.05)&A["bh_q"].le(DISCOVERY_Q)].head(MAX_FROZEN).copy()
    status(5,12,"discovery complete",finite_tests=len(A),frozen=len(frozen))
    if frozen.empty:
        receipt={"run_id":rid,"status":"COMPLETE_V109_NO_DISCOVERY_SURVIVORS","engine_version":ENGINE_VERSION,
                 "finite_tests":len(A),"discovery_frozen":0,"2014_plus_market_returns_accessed":False,
                 "2023_2025_accessed":False,"2026_accessed":False}
        finish(out,receipt);status(12,12,"DONE");return

    frozen.to_csv(out/"FROZEN_PRE_2014.csv",index=False)
    write_json(out/"DISCOVERY_FREEZE.json",{"run_id":rid,"frozen":len(frozen),"sha256":sha256(out/"FROZEN_PRE_2014.csv"),
      "2014_plus_accessed_at_freeze":False,"2023_2025_accessed":False,"2026_accessed":False})
    status(6,12,"discovery frozen before 2014+",frozen=len(frozen))

    req=sorted(set(frozen["target_market"].astype(str)))
    P17,markets17=build_prices(root,2017,req)
    missing=sorted(set(req)-set(markets17))
    if missing:raise RuntimeError(f"Replication markets missing: {missing}")
    rep=[]
    for r in frozen.itertuples(index=False):
        ev=features[r.feature];times,vals=event_sample(ev,P17[r.target_market],int(r.horizon_min),int(r.orientation),"2014-01-01","2018-01-01")
        pyf,yearly=positive_year_fraction(times,vals)
        passed=(len(vals)>=MIN_REP and mean_bp(vals)>0 and mean_bp(vals)-GENERIC_COST_BP>0 and pyf>=.50 and remove_best(vals,2)>0)
        rep.append({**r._asdict(),"rep_n":len(vals),"rep_mean_bp":mean_bp(vals),"rep_net1bp":mean_bp(vals)-1,
                    "rep_positive_year_fraction":pyf,"rep_yearly_json":json.dumps(yearly,sort_keys=True),
                    "rep_remove_best2_bp":remove_best(vals,2),"replication_pass":bool(passed)})
    R=pd.DataFrame(rep);R.to_csv(out/"REPLICATION_RESULTS.csv",index=False)
    rp=R[R["replication_pass"].astype(bool)].copy()
    status(7,12,"replication complete",survivors=len(rp))
    if rp.empty:
        receipt={"run_id":rid,"status":"COMPLETE_V109_REPLICATION_FAIL_ALL","engine_version":ENGINE_VERSION,
                 "discovery_frozen":len(frozen),"replication_survivors":0,"2018_plus_accessed":False,
                 "2023_2025_accessed":False,"2026_accessed":False}
        finish(out,receipt);status(12,12,"DONE");return

    robust=[]
    for r in rp.itertuples(index=False):
        ev=features[r.feature]
        times,vals=event_sample(ev,P17[r.target_market],int(r.horizon_min),int(r.orientation),"2014-01-01","2018-01-01")
        rm,bm=remove_best_month(times,vals);loo,looj=leave_one_year_out(times,vals)
        _,lag1=event_sample(ev,P17[r.target_market],int(r.horizon_min),int(r.orientation),"2014-01-01","2018-01-01",1)
        _,lag2=event_sample(ev,P17[r.target_market],int(r.horizon_min),int(r.orientation),"2014-01-01","2018-01-01",2)
        passed=(remove_best(vals,3)>0 and rm>0 and loo>0 and mean_bp(lag1)>0 and mean_bp(lag2)>0)
        robust.append({**r._asdict(),"robust_remove_best3_bp":remove_best(vals,3),"robust_remove_best_month_bp":rm,
                       "robust_best_month":bm,"robust_loo_min_bp":loo,"robust_loo_json":json.dumps(looj,sort_keys=True),
                       "robust_delay1d_bp":mean_bp(lag1),"robust_delay2d_bp":mean_bp(lag2),"robustness_pass":bool(passed)})
    B=pd.DataFrame(robust);B.to_csv(out/"ROBUSTNESS_RESULTS.csv",index=False)
    rb=B[B["robustness_pass"].astype(bool)].copy()
    status(8,12,"pre-validation robustness complete",survivors=len(rb))
    if rb.empty:
        receipt={"run_id":rid,"status":"COMPLETE_V109_ROBUSTNESS_FAIL_ALL","engine_version":ENGINE_VERSION,
                 "discovery_frozen":len(frozen),"replication_survivors":len(rp),"robustness_survivors":0,
                 "2018_plus_accessed":False,"2023_2025_accessed":False,"2026_accessed":False}
        finish(out,receipt);status(12,12,"DONE");return

    rb.to_csv(out/"FROZEN_PRE_VALIDATION.csv",index=False)
    write_json(out/"PRE_VALIDATION_FREEZE.json",{"run_id":rid,"survivors":len(rb),"sha256":sha256(out/"FROZEN_PRE_VALIDATION.csv"),
      "2018_plus_accessed_at_freeze":False,"2023_2025_accessed":False,"2026_accessed":False})
    status(9,12,"survivors frozen before 2018+",survivors=len(rb))

    req22=sorted(set(rb["target_market"].astype(str)))
    P22,markets22=build_prices(root,2022,req22)
    missing22=sorted(set(req22)-set(markets22))
    if missing22:raise RuntimeError(f"Validation markets missing: {missing22}")
    valsout=[]
    for r in rb.itertuples(index=False):
        ev=features[r.feature];times,vals=event_sample(ev,P22[r.target_market],int(r.horizon_min),int(r.orientation),"2018-01-01","2023-01-01")
        pyf,yearly=positive_year_fraction(times,vals);rm,bm=remove_best_month(times,vals);loo,looj=leave_one_year_out(times,vals)
        passed=(len(vals)>=MIN_VAL and mean_bp(vals)>0 and mean_bp(vals)-GENERIC_COST_BP>0 and pyf>=.60 and
                remove_best(vals,3)>0 and remove_best(vals,5)>0 and rm>0 and loo>0)
        valsout.append({**r._asdict(),"val_n":len(vals),"val_mean_bp":mean_bp(vals),"val_net1bp":mean_bp(vals)-1,
                        "val_positive_year_fraction":pyf,"val_yearly_json":json.dumps(yearly,sort_keys=True),
                        "val_remove_best3_bp":remove_best(vals,3),"val_remove_best5_bp":remove_best(vals,5),
                        "val_remove_best_month_bp":rm,"val_best_month":bm,"val_loo_min_bp":loo,
                        "val_loo_json":json.dumps(looj,sort_keys=True),"validation_pass":bool(passed)})
    V=pd.DataFrame(valsout);V.to_csv(out/"VALIDATION_RESULTS.csv",index=False)
    final=V[V["validation_pass"].astype(bool)].copy();final.to_csv(out/"FINAL_SURVIVORS.csv",index=False)
    status(10,12,"validation complete",final_survivors=len(final))

    receipt={"run_id":rid,"status":"COMPLETE_V109_TREASURY_EVENT_LEVEL","engine_version":ENGINE_VERSION,
      "source_rows":len(d),"raw_features":len(rawcols),"event_features":len(features),"finite_discovery_tests":len(A),
      "discovery_frozen":len(frozen),"replication_survivors":len(rp),"robustness_survivors":len(rb),
      "validation_survivors":len(final),"final_survivors_sha256":sha256(out/"FINAL_SURVIVORS.csv"),
      "statistical_unit":"one Treasury auction event","availability_rule":"auction_date + 1 calendar day",
      "2023_2025_accessed":False,"2026_accessed":False,
      "next":"HUMAN_REVIEW_V109; IF SURVIVORS, RUN SEPARATE PREOOS FORENSIC"}
    finish(out,receipt)
    status(11,12,"receipt written");status(12,12,"DONE")
    if len(final):
        print("\n=== V109 FINAL SURVIVORS ===")
        print(final[["feature","target_market","horizon_min","orientation","rep_mean_bp","val_mean_bp","val_n"]].to_string(index=False))
    print("\nRUN:",out)

if __name__=="__main__":
    main()
