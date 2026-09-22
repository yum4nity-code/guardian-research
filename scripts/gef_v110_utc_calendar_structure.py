from pathlib import Path
import argparse, hashlib, json, math, time
import numpy as np
import pandas as pd
try:
    from scipy.stats import ttest_ind
except Exception:
    ttest_ind=None

ENGINE_VERSION="V110.0"
FORBIDDEN_YEAR=2023
HORIZONS=[30,60,120,240]
DISCOVERY_Q=.05
MAX_FROZEN=150
MIN_DISC=120
MIN_REP=120
MIN_VAL=150
GENERIC_COST_BP=1.0

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

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

def remove_best_k_mean_bp(x,k):
    x=np.asarray(x,dtype=float);x=x[np.isfinite(x)]
    if len(x)<=k:return np.nan
    return mean_bp(np.sort(x)[:-k])

def bh_qvalues(p):
    p=np.asarray(p,dtype=float);q=np.full(len(p),np.nan)
    finite=np.flatnonzero(np.isfinite(p))
    if not len(finite):return q
    order=finite[np.argsort(p[finite],kind="mergesort")]
    m=len(order);running=1.0
    for rev,idx in enumerate(order[::-1],1):
        rank=m-rev+1;val=min(1.0,p[idx]*m/rank);running=min(running,val);q[idx]=running
    return q

def welch_p(a,b):
    a=np.asarray(a,dtype=float);a=a[np.isfinite(a)]
    b=np.asarray(b,dtype=float);b=b[np.isfinite(b)]
    if len(a)<3 or len(b)<3:return np.nan
    if ttest_ind is not None:
        return float(ttest_ind(a,b,equal_var=False,nan_policy="omit").pvalue)
    ma,mb=a.mean(),b.mean();va=a.var(ddof=1);vb=b.var(ddof=1)
    se=math.sqrt(va/len(a)+vb/len(b))
    if not np.isfinite(se) or se==0:return 1.0 if abs(ma-mb)<1e-15 else 0.0
    z=abs(ma-mb)/se
    return float(math.erfc(z/math.sqrt(2)))

def positive_year_fraction(times,vals):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,dtype=float)})
    d=d[np.isfinite(d["v"])].copy()
    if d.empty:return np.nan,{}
    d["year"]=d["t"].dt.year
    y=d.groupby("year")["v"].mean()*1e4
    return float((y>0).mean()),{str(int(k)):float(v) for k,v in y.items()}

def leave_one_year_out(times,vals):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,dtype=float)})
    d=d[np.isfinite(d["v"])].copy()
    if d.empty:return np.nan,{}
    d["year"]=d["t"].dt.year
    out={}
    for y in sorted(d["year"].unique()):
        out[str(int(y))]=mean_bp(d.loc[d["year"]!=y,"v"].to_numpy())
    return min(out.values()) if out else np.nan,out

def load_market(root,sym,end_year):
    if end_year>=FORBIDDEN_YEAR:raise RuntimeError("V110 refuses 2023+")
    parts=[]
    for year in range(2009,end_year+1):
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
        q=q[q["utc"].dt.year.between(2009,end_year)]
        parts.append(q)
    if not parts:return None
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    return q.set_index("utc")["px"].resample("5min",label="right",closed="left").last().dropna().astype(float)

def build_prices(root,end_year,required=None):
    base=root/"DataLake"/"raw"/"histdata"
    markets=sorted([p.name for p in base.iterdir() if p.is_dir() and (p/"M1").exists()])
    if required is not None:
        req=set(map(str,required));markets=[m for m in markets if m in req]
    P={};valid=[]
    for sym in markets:
        try:
            s=load_market(root,sym,end_year)
            if s is None or len(s)<1000:continue
            P[sym]=s;valid.append(sym);print(f"[GEF110] price {len(valid)} {sym}",flush=True)
        except Exception as e:
            print(f"[GEF110] skip market {sym}: {e}",flush=True)
    return P,valid

def hourly_returns(series,horizon,start,end,delay_min=0):
    idx=series.index
    base=idx[(idx.minute==0)&(idx>=pd.Timestamp(start))&(idx<pd.Timestamp(end))]
    if delay_min:
        entries=base+pd.Timedelta(minutes=int(delay_min))
    else:
        entries=base
    exits=entries+pd.Timedelta(minutes=int(horizon))
    a=series.reindex(entries).to_numpy(dtype=float)
    b=series.reindex(exits).to_numpy(dtype=float)
    ok=np.isfinite(a)&np.isfinite(b)&(a!=0)
    return pd.DatetimeIndex(base[ok]),(b[ok]/a[ok]-1.0)

def month_pos(t):
    d=t.day.to_numpy()
    out=np.full(len(t),"MID",dtype=object)
    out[d<=5]="START";out[d>=26]="END"
    return out

def quarter_end(t):
    return np.isin(t.month,[3,6,9,12])&(t.day>=20)

def frozen_cells():
    rows=[]
    for h in range(24):
        rows.append({"cell_type":"hour","hour":h,"weekday":-1,"month_pos":"","quarter_end":False,
                     "cell_id":f"H{h:02d}"})
    for h in range(24):
        for w in range(5):
            rows.append({"cell_type":"hour_weekday","hour":h,"weekday":w,"month_pos":"","quarter_end":False,
                         "cell_id":f"H{h:02d}_W{w}"})
    for h in range(24):
        for p in ["START","MID","END"]:
            rows.append({"cell_type":"hour_monthpos","hour":h,"weekday":-1,"month_pos":p,"quarter_end":False,
                         "cell_id":f"H{h:02d}_{p}"})
    for h in range(24):
        rows.append({"cell_type":"hour_quarter_end","hour":h,"weekday":-1,"month_pos":"","quarter_end":True,
                     "cell_id":f"H{h:02d}_QEND"})
    return pd.DataFrame(rows)

def masks(times,row):
    hour=times.hour.to_numpy();wd=times.weekday.to_numpy();mp=month_pos(times);qe=quarter_end(times)
    h=int(row.hour)
    if row.cell_type=="hour":
        cand=hour==h;ctrl=hour!=h
    elif row.cell_type=="hour_weekday":
        cand=(hour==h)&(wd==int(row.weekday));ctrl=(hour==h)&(wd!=int(row.weekday))
    elif row.cell_type=="hour_monthpos":
        cand=(hour==h)&(mp==str(row.month_pos));ctrl=(hour==h)&(mp!=str(row.month_pos))
    elif row.cell_type=="hour_quarter_end":
        cand=(hour==h)&qe;ctrl=(hour==h)&(~qe)
    else:
        raise RuntimeError(f"Unknown cell {row.cell_type}")
    return cand,ctrl

def sample_cell(series,horizon,row,start,end,orientation=1,delay_min=0):
    times,rets=hourly_returns(series,horizon,start,end,delay_min)
    cand,ctrl=masks(times,row)
    return times[cand],rets[cand]*orientation,rets[ctrl]*orientation

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root)
    base=root/"Research"/"Autonomous"/"guardian_edge_factory_v110_utc_calendar";base.mkdir(parents=True,exist_ok=True)
    rid="GEF110-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");out=base/rid;out.mkdir(parents=True,exist_ok=False);t0=time.time()
    def status(step,total,msg,**extra):
        p={"run_id":rid,"engine_version":ENGINE_VERSION,"step":step,"steps":total,"percent":round(100*step/total,1),
           "elapsed_s":round(time.time()-t0,1),"message":msg,**extra}
        write_json(out/"LIVE_STATUS.json",p)
        tail=" | ".join(f"{k}={v}" for k,v in extra.items())
        print(f"[GEF110] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

    C=frozen_cells();C.to_csv(out/"FROZEN_CALENDAR_CELLS.csv",index=False)
    status(1,11,"calendar cells frozen before market returns",cells=len(C))

    P13,markets=build_prices(root,2013)
    if not markets:raise RuntimeError("No discovery markets")
    status(2,11,"discovery prices loaded through 2013 only",markets=len(markets))

    rows=[];total=len(markets)*len(HORIZONS)*len(C);done=0
    for sym in markets:
        for hor in HORIZONS:
            times,rets=hourly_returns(P13[sym],hor,"2010-01-01","2014-01-01",0)
            for cell in C.itertuples(index=False):
                done+=1
                cand,ctrl=masks(times,cell)
                a=rets[cand];b=rets[ctrl]
                if len(a)<MIN_DISC or len(b)<MIN_DISC:continue
                years=int(times[cand].year.nunique())
                if years<3:continue
                effect=float(np.mean(a)-np.mean(b))
                if not np.isfinite(effect) or effect==0:continue
                orientation=1 if effect>0 else -1
                trade=a*orientation
                if mean_bp(trade)<=0:continue
                rows.append({
                    **cell._asdict(),"target_market":sym,"horizon_min":hor,"orientation":orientation,
                    "disc_n":len(a),"disc_control_n":len(b),"disc_years":years,
                    "disc_effect_bp":float(effect*orientation*1e4),"disc_trade_mean_bp":mean_bp(trade),
                    "disc_p_two":welch_p(a,b)
                })
                if done%2000==0:print(f"[GEF110] discovery {done}/{total}",flush=True)
    A=pd.DataFrame(rows)
    if A.empty:
        receipt={"run_id":rid,"status":"COMPLETE_V110_NO_FINITE_DISCOVERY_TESTS","engine_version":ENGINE_VERSION,
                 "2014_plus_accessed":False,"2023_2025_accessed":False,"2026_accessed":False}
        write_json(out/"RUN_RECEIPT.json",receipt);status(11,11,"DONE");print(json.dumps(receipt,indent=2));return
    A["bh_q"]=bh_qvalues(A["disc_p_two"].to_numpy())
    A=A.sort_values(["bh_q","disc_p_two","disc_effect_bp"],ascending=[True,True,False],kind="mergesort").reset_index(drop=True)
    A.to_csv(out/"DISCOVERY_ALL.csv",index=False)
    frozen=A[A["disc_p_two"].le(.05)&A["bh_q"].le(DISCOVERY_Q)].head(MAX_FROZEN).copy()
    status(3,11,"discovery complete",finite_tests=len(A),frozen=len(frozen))
    if frozen.empty:
        receipt={"run_id":rid,"status":"COMPLETE_V110_NO_DISCOVERY_SURVIVORS","engine_version":ENGINE_VERSION,
                 "finite_tests":len(A),"discovery_frozen":0,"2014_plus_accessed":False,
                 "2023_2025_accessed":False,"2026_accessed":False}
        write_json(out/"RUN_RECEIPT.json",receipt);status(11,11,"DONE");print(json.dumps(receipt,indent=2));return

    frozen.to_csv(out/"FROZEN_PRE_2014.csv",index=False)
    write_json(out/"DISCOVERY_FREEZE.json",{"run_id":rid,"frozen":len(frozen),"sha256":sha256(out/"FROZEN_PRE_2014.csv"),
      "2014_plus_accessed_at_freeze":False,"2023_2025_accessed":False,"2026_accessed":False})
    status(4,11,"discovery frozen before 2014+",frozen=len(frozen))

    req=sorted(set(frozen["target_market"].astype(str)));P17,markets17=build_prices(root,2017,req)
    rep=[]
    for r in frozen.itertuples(index=False):
        if r.target_market not in P17:
            rep.append({**r._asdict(),"replication_pass":False,"rep_reason":"missing_market_data"});continue
        times,a,b=sample_cell(P17[r.target_market],int(r.horizon_min),r,"2014-01-01","2018-01-01",int(r.orientation),0)
        pyf,yearly=positive_year_fraction(times,a)
        effect=mean_bp(a)-mean_bp(b)
        passed=(len(a)>=MIN_REP and len(b)>=MIN_REP and effect>0 and mean_bp(a)>0 and mean_bp(a)-1>0 and
                pyf>=.50 and trimmed_best_mean_bp(a,.01)>0)
        rep.append({**r._asdict(),"rep_n":len(a),"rep_control_n":len(b),"rep_effect_bp":effect,
                    "rep_mean_bp":mean_bp(a),"rep_net1bp":mean_bp(a)-1,"rep_positive_year_fraction":pyf,
                    "rep_yearly_json":json.dumps(yearly,sort_keys=True),"rep_trim1_bp":trimmed_best_mean_bp(a,.01),
                    "replication_pass":bool(passed),"rep_reason":""})
    R=pd.DataFrame(rep);R.to_csv(out/"REPLICATION_RESULTS.csv",index=False)
    rp=R[R["replication_pass"].fillna(False).astype(bool)].copy()
    status(5,11,"replication complete",survivors=len(rp))
    if rp.empty:
        receipt={"run_id":rid,"status":"COMPLETE_V110_REPLICATION_FAIL_ALL","engine_version":ENGINE_VERSION,
                 "discovery_frozen":len(frozen),"replication_survivors":0,"2018_plus_accessed":False,
                 "2023_2025_accessed":False,"2026_accessed":False}
        write_json(out/"RUN_RECEIPT.json",receipt);status(11,11,"DONE");print(json.dumps(receipt,indent=2));return

    robust=[]
    for r in rp.itertuples(index=False):
        times,a,b=sample_cell(P17[r.target_market],int(r.horizon_min),r,"2014-01-01","2018-01-01",int(r.orientation),0)
        loo,looj=leave_one_year_out(times,a)
        _,a5,_=sample_cell(P17[r.target_market],int(r.horizon_min),r,"2014-01-01","2018-01-01",int(r.orientation),5)
        _,a10,_=sample_cell(P17[r.target_market],int(r.horizon_min),r,"2014-01-01","2018-01-01",int(r.orientation),10)
        passed=(trimmed_best_mean_bp(a,.02)>0 and remove_best_k_mean_bp(a,10)>0 and loo>0 and mean_bp(a5)>0 and mean_bp(a10)>0)
        robust.append({**r._asdict(),"robust_trim2_bp":trimmed_best_mean_bp(a,.02),
                       "robust_remove_best10_bp":remove_best_k_mean_bp(a,10),"robust_loo_min_bp":loo,
                       "robust_loo_json":json.dumps(looj,sort_keys=True),"robust_delay5m_bp":mean_bp(a5),
                       "robust_delay10m_bp":mean_bp(a10),"robustness_pass":bool(passed)})
    B=pd.DataFrame(robust);B.to_csv(out/"ROBUSTNESS_RESULTS.csv",index=False)
    rb=B[B["robustness_pass"].astype(bool)].copy()
    status(6,11,"pre-validation robustness complete",survivors=len(rb))
    if rb.empty:
        receipt={"run_id":rid,"status":"COMPLETE_V110_ROBUSTNESS_FAIL_ALL","engine_version":ENGINE_VERSION,
                 "discovery_frozen":len(frozen),"replication_survivors":len(rp),"robustness_survivors":0,
                 "2018_plus_accessed":False,"2023_2025_accessed":False,"2026_accessed":False}
        write_json(out/"RUN_RECEIPT.json",receipt);status(11,11,"DONE");print(json.dumps(receipt,indent=2));return

    rb.to_csv(out/"FROZEN_PRE_VALIDATION.csv",index=False)
    write_json(out/"PRE_VALIDATION_FREEZE.json",{"run_id":rid,"survivors":len(rb),"sha256":sha256(out/"FROZEN_PRE_VALIDATION.csv"),
      "2018_plus_accessed_at_freeze":False,"2023_2025_accessed":False,"2026_accessed":False})
    status(7,11,"survivors frozen before 2018+",survivors=len(rb))

    req22=sorted(set(rb["target_market"].astype(str)));P22,markets22=build_prices(root,2022,req22)
    vals=[]
    for r in rb.itertuples(index=False):
        if r.target_market not in P22:
            vals.append({**r._asdict(),"validation_pass":False,"val_reason":"missing_market_data"});continue
        times,a,b=sample_cell(P22[r.target_market],int(r.horizon_min),r,"2018-01-01","2023-01-01",int(r.orientation),0)
        pyf,yearly=positive_year_fraction(times,a);loo,looj=leave_one_year_out(times,a)
        effect=mean_bp(a)-mean_bp(b)
        passed=(len(a)>=MIN_VAL and len(b)>=MIN_VAL and effect>0 and mean_bp(a)>0 and mean_bp(a)-1>0 and
                pyf>=.60 and trimmed_best_mean_bp(a,.01)>0 and trimmed_best_mean_bp(a,.02)>0 and
                remove_best_k_mean_bp(a,10)>0 and loo>0)
        vals.append({**r._asdict(),"val_n":len(a),"val_control_n":len(b),"val_effect_bp":effect,
                     "val_mean_bp":mean_bp(a),"val_net1bp":mean_bp(a)-1,"val_positive_year_fraction":pyf,
                     "val_yearly_json":json.dumps(yearly,sort_keys=True),"val_trim1_bp":trimmed_best_mean_bp(a,.01),
                     "val_trim2_bp":trimmed_best_mean_bp(a,.02),"val_remove_best10_bp":remove_best_k_mean_bp(a,10),
                     "val_loo_min_bp":loo,"val_loo_json":json.dumps(looj,sort_keys=True),
                     "validation_pass":bool(passed),"val_reason":""})
    V=pd.DataFrame(vals);V.to_csv(out/"VALIDATION_RESULTS.csv",index=False)
    final=V[V["validation_pass"].fillna(False).astype(bool)].copy();final.to_csv(out/"FINAL_SURVIVORS.csv",index=False)
    status(8,11,"validation complete",final_survivors=len(final))

    receipt={"run_id":rid,"status":"COMPLETE_V110_UTC_CALENDAR","engine_version":ENGINE_VERSION,
      "calendar_cells":len(C),"finite_discovery_tests":len(A),"discovery_frozen":len(frozen),
      "replication_survivors":len(rp),"robustness_survivors":len(rb),"validation_survivors":len(final),
      "final_survivors_sha256":sha256(out/"FINAL_SURVIVORS.csv"),
      "statistical_unit":"one top-of-hour event","calendar_timezone":"UTC fixed data timeline",
      "2023_2025_accessed":False,"2026_accessed":False,
      "next":"HUMAN_REVIEW_V110; IF SURVIVORS, RUN SEPARATE PREOOS_FORENSIC"}
    write_json(out/"RUN_RECEIPT.json",receipt)
    status(9,11,"receipt written");status(10,11,"firewalls asserted");status(11,11,"DONE")
    print("\n=== V110 RECEIPT ===");print(json.dumps(receipt,indent=2))
    if len(final):
        print("\n=== V110 FINAL SURVIVORS ===")
        print(final[["cell_id","cell_type","target_market","horizon_min","orientation","rep_effect_bp","rep_mean_bp","val_effect_bp","val_mean_bp","val_n"]].to_string(index=False))
    print("\nRUN:",out)

if __name__=="__main__":
    main()
