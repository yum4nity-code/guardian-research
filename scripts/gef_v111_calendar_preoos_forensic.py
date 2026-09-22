from pathlib import Path
import argparse, hashlib, json, math, time
import numpy as np
import pandas as pd

ENGINE_VERSION="V111.0"
SOURCE_RUN="GEF110-20260922-162255"
EXPECTED_SHA="3d89751fa6533b5f5290be3b9704480aea9455d4e3b069b10bb2728bd67a2bbc"
FORBIDDEN_YEAR=2023
BOOTSTRAPS=2000
SEED=111

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

def load_market(root,sym,end_year=2022):
    if end_year>=FORBIDDEN_YEAR:raise RuntimeError("V111 refuses 2023+")
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
    if not parts:raise RuntimeError(f"No price data {sym}")
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    return q.set_index("utc")["px"].resample("5min",label="right",closed="left").last().dropna().astype(float)

def hourly_returns(series,horizon,start,end,delay_min=0):
    idx=series.index
    base=idx[(idx.minute==0)&(idx>=pd.Timestamp(start))&(idx<pd.Timestamp(end))]
    entries=base+pd.Timedelta(minutes=int(delay_min))
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

def masks(times,row):
    hour=times.hour.to_numpy();wd=times.weekday.to_numpy();mp=month_pos(times);qe=quarter_end(times)
    h=int(row.hour)
    if str(row.cell_type)=="hour":
        cand=hour==h;ctrl=hour!=h
    elif str(row.cell_type)=="hour_weekday":
        cand=(hour==h)&(wd==int(row.weekday));ctrl=(hour==h)&(wd!=int(row.weekday))
    elif str(row.cell_type)=="hour_monthpos":
        cand=(hour==h)&(mp==str(row.month_pos));ctrl=(hour==h)&(mp!=str(row.month_pos))
    elif str(row.cell_type)=="hour_quarter_end":
        cand=(hour==h)&qe;ctrl=(hour==h)&(~qe)
    else:
        raise RuntimeError(f"Unknown cell type {row.cell_type}")
    return cand,ctrl

def sample_cell(series,row,delay_min=0):
    times,rets=hourly_returns(series,int(row.horizon_min),"2018-01-01","2023-01-01",delay_min)
    cand,ctrl=masks(times,row)
    orientation=int(row.orientation)
    return times[cand],rets[cand]*orientation,rets[ctrl]*orientation

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root)
    src=root/"Research"/"Autonomous"/"guardian_edge_factory_v110_utc_calendar"/SOURCE_RUN
    rec=json.loads((src/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
    final_path=src/"FINAL_SURVIVORS.csv"
    if rec.get("status")!="COMPLETE_V110_UTC_CALENDAR":raise RuntimeError("Wrong V110 source status")
    if sha256(final_path)!=EXPECTED_SHA:raise RuntimeError("V110 final survivor SHA mismatch")
    C=pd.read_csv(final_path)
    if len(C)!=8:raise RuntimeError(f"Expected exactly 8 V110 survivors, got {len(C)}")

    base=root/"Research"/"Autonomous"/"guardian_edge_factory_v111_calendar_preoos_forensic";base.mkdir(parents=True,exist_ok=True)
    rid="GEF111-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");out=base/rid;out.mkdir(parents=True,exist_ok=False);t0=time.time()
    def status(step,total,msg,**extra):
        p={"run_id":rid,"engine_version":ENGINE_VERSION,"step":step,"steps":total,"percent":round(100*step/total,1),
           "elapsed_s":round(time.time()-t0,1),"message":msg,**extra}
        write_json(out/"LIVE_STATUS.json",p)
        tail=" | ".join(f"{k}={v}" for k,v in extra.items())
        print(f"[GEF111] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

    status(1,8,"exact V110 survivor panel verified",sha=EXPECTED_SHA[:16],candidates=len(C))
    markets=sorted(C["target_market"].astype(str).unique())
    P={}
    for i,sym in enumerate(markets,1):
        P[sym]=load_market(root,sym,2022)
        print(f"[GEF111] price {i}/{len(markets)} {sym}",flush=True)
    status(2,8,"2018-2022 source markets loaded only",markets=len(markets))

    rows=[];event_sets={};series_map={}
    for idx,r in C.reset_index(drop=True).iterrows():
        cid=f"C{idx+1}"
        row=type("R",(),r.to_dict())()
        times,a,b=sample_cell(P[str(r["target_market"])],row,0)
        effect=mean_bp(a)-mean_bp(b)
        rm,bm=remove_best_month(times,a)
        loo,looj=leave_one_year_out(times,a)
        q025,q50,q975=month_block_bootstrap(times,a,BOOTSTRAPS,SEED+idx)
        shifts={}
        for dm in [-10,-5,5,10]:
            _,aa,_=sample_cell(P[str(r["target_market"])],row,dm)
            shifts[dm]=mean_bp(aa)
        event_sets[cid]=pd.DatetimeIndex(times)
        series_map[cid]=pd.Series(a,index=times)
        baseline=mean_bp(a)
        recrow={
            "candidate_id":cid,
            "cell_id":str(r["cell_id"]),
            "cell_type":str(r["cell_type"]),
            "target_market":str(r["target_market"]),
            "horizon_min":int(r["horizon_min"]),
            "orientation":int(r["orientation"]),
            "structural_family_key":f"{r['target_market']}|{r['cell_id']}",
            "n":int(len(a)),
            "control_n":int(len(b)),
            "mean_bp":baseline,
            "control_mean_bp":mean_bp(b),
            "effect_bp":effect,
            "median_bp":float(np.median(a)*1e4) if len(a) else np.nan,
            "win_rate_pct":float((a>0).mean()*100) if len(a) else np.nan,
            "net1bp_mean_bp":baseline-1,
            "net2bp_mean_bp":baseline-2,
            "net3bp_mean_bp":baseline-3,
            "net5bp_mean_bp":baseline-5,
            "trim1_mean_bp":trimmed_best_mean_bp(a,.01),
            "trim2_mean_bp":trimmed_best_mean_bp(a,.02),
            "trim5_mean_bp":trimmed_best_mean_bp(a,.05),
            "remove_best10_mean_bp":remove_best_k_mean_bp(a,10),
            "remove_best20_mean_bp":remove_best_k_mean_bp(a,20),
            "remove_best_month_mean_bp":rm,
            "removed_best_month":bm,
            "leave_one_year_out_min_mean_bp":loo,
            "leave_one_year_out_json":json.dumps(looj,sort_keys=True),
            "shift_minus10m_mean_bp":shifts[-10],
            "shift_minus5m_mean_bp":shifts[-5],
            "shift_plus5m_mean_bp":shifts[5],
            "shift_plus10m_mean_bp":shifts[10],
            "bootstrap_month_q025_bp":q025,
            "bootstrap_month_q50_bp":q50,
            "bootstrap_month_q975_bp":q975
        }
        gates=[
            recrow["mean_bp"]>0,
            recrow["effect_bp"]>0,
            recrow["net1bp_mean_bp"]>0,
            recrow["trim5_mean_bp"]>0,
            recrow["remove_best20_mean_bp"]>0,
            recrow["remove_best_month_mean_bp"]>0,
            recrow["leave_one_year_out_min_mean_bp"]>0,
            recrow["shift_minus5m_mean_bp"]>0,
            recrow["shift_plus5m_mean_bp"]>0,
            recrow["shift_plus10m_mean_bp"]>0,
            recrow["bootstrap_month_q025_bp"]>0
        ]
        recrow["final_preoos_pass"]=bool(all(gates))
        recrow["failed_gate_count"]=int(sum(not bool(x) for x in gates))
        rows.append(recrow)

    R=pd.DataFrame(rows)
    R.to_csv(out/"FORENSIC_RESULTS.csv",index=False)
    passing=R[R["final_preoos_pass"].astype(bool)].copy()
    passing.to_csv(out/"FINAL_PREOOS_SURVIVORS.csv",index=False)
    status(3,8,"candidate forensic complete",passes=len(passing))

    ids=R["candidate_id"].tolist()
    jac=pd.DataFrame(np.nan,index=ids,columns=ids)
    corr=pd.DataFrame(np.nan,index=ids,columns=ids)
    for a in ids:
        sa=set(event_sets[a])
        for b in ids:
            sb=set(event_sets[b]);u=len(sa|sb);i=len(sa&sb)
            jac.loc[a,b]=i/u if u else np.nan
            common=series_map[a].index.intersection(series_map[b].index)
            if len(common)>=3:
                x=series_map[a].loc[common].to_numpy(dtype=float)
                y=series_map[b].loc[common].to_numpy(dtype=float)
                if np.std(x)>0 and np.std(y)>0:
                    corr.loc[a,b]=float(np.corrcoef(x,y)[0,1])
    jac.to_csv(out/"EVENT_JACCARD.csv")
    corr.to_csv(out/"COMMON_TIMESTAMP_RETURN_CORRELATION.csv")

    fam=R.groupby("structural_family_key").agg(
        candidate_count=("candidate_id","count"),
        passing_candidates=("final_preoos_pass","sum")
    ).reset_index()
    fam["family_pass"]=fam["passing_candidates"]>0
    fam.to_csv(out/"STRUCTURAL_FAMILY_SUMMARY.csv",index=False)
    unique_all=int(R["structural_family_key"].nunique())
    unique_pass=int(passing["structural_family_key"].nunique()) if len(passing) else 0
    status(4,8,"dependency audit complete",unique_families=unique_all,passing_families=unique_pass)

    cols=["candidate_id","cell_id","target_market","horizon_min","mean_bp","effect_bp","net1bp_mean_bp",
          "trim5_mean_bp","remove_best20_mean_bp","remove_best_month_mean_bp",
          "leave_one_year_out_min_mean_bp","shift_minus5m_mean_bp","shift_plus5m_mean_bp",
          "shift_plus10m_mean_bp","bootstrap_month_q025_bp","final_preoos_pass"]
    report=["# GEF V111 — UTC calendar final pre-OOS forensic","",f"Run: {rid}",
            f"- candidates audited: {len(R)}",f"- candidate passes: {len(passing)}",
            f"- unique structural families: {unique_all}",f"- passing structural families: {unique_pass}",
            "- 2023-2025 accessed: false","- 2026 accessed: false","",
            "## Forensic","",R[cols].to_markdown(index=False),"",
            "## Structural families","",fam.to_markdown(index=False),
            "","STOP. Do not open locked OOS automatically."]
    (out/"V111_REPORT.md").write_text("\n".join(report),encoding="utf-8")
    status(5,8,"report written")

    receipt={
        "run_id":rid,
        "status":"COMPLETE_V111_CALENDAR_PREOOS_FORENSIC",
        "engine_version":ENGINE_VERSION,
        "source_v110":SOURCE_RUN,
        "source_final_sha256":EXPECTED_SHA,
        "candidates_audited":int(len(R)),
        "candidate_preoos_passes":int(len(passing)),
        "unique_structural_families_all":unique_all,
        "unique_structural_families_passing":unique_pass,
        "forensic_results_sha256":sha256(out/"FORENSIC_RESULTS.csv"),
        "final_preoos_survivors_sha256":sha256(out/"FINAL_PREOOS_SURVIVORS.csv"),
        "2023_2025_accessed":False,
        "2026_accessed":False,
        "next":"STOP_FOR_HUMAN_REVIEW; IF ANY STRUCTURAL FAMILY PASSES, PREDECLARE SEPARATE LOCKED-OOS PROTOCOL"
    }
    write_json(out/"RUN_RECEIPT.json",receipt)
    status(6,8,"receipt written")
    status(7,8,"firewalls asserted")
    status(8,8,"DONE")
    print("\n=== V111 RECEIPT ===");print(json.dumps(receipt,indent=2))
    print("\n=== V111 FORENSIC RESULTS ===")
    print(R[cols].to_string(index=False))
    print("\n=== V111 STRUCTURAL FAMILIES ===")
    print(fam.to_string(index=False))
    print("\nRUN:",out)

if __name__=="__main__":
    main()
