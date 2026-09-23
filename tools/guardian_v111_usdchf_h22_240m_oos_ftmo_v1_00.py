from pathlib import Path
import argparse, json, math, traceback
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

SOURCE_RUN="GEF111-20260922-163321"
START=pd.Timestamp("2023-01-01 00:00")
END=pd.Timestamp("2026-01-01 00:00")
MARKET="USDCHF"
HOUR=22
HORIZON=240
ORIENTATION=1
EXPECTED_PREOOS_N=1047
OFFSETS=list(range(-8,9))
BOOTSTRAPS=5000
SEED=11105

def jd(p,o): p.write_text(json.dumps(o,indent=2,default=str),encoding="utf-8")

def mean_bp(x):
    x=np.asarray(x,float);x=x[np.isfinite(x)]
    return float(x.mean()*1e4) if len(x) else np.nan

def trim_best_bp(x,pct):
    x=np.asarray(x,float);x=x[np.isfinite(x)]
    if not len(x):return np.nan
    k=int(math.ceil(len(x)*pct))
    if k<=0:return mean_bp(x)
    if k>=len(x):return np.nan
    return mean_bp(np.sort(x)[:-k])

def remove_best_k_bp(x,k):
    x=np.asarray(x,float);x=x[np.isfinite(x)]
    if len(x)<=k:return np.nan
    return mean_bp(np.sort(x)[:-k])

def month_bootstrap(times,vals):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,float)})
    d=d[np.isfinite(d["v"])].copy();d["month"]=d["t"].dt.to_period("M").astype(str)
    groups=[g["v"].to_numpy(float) for _,g in d.groupby("month") if len(g)]
    if len(groups)<2:return (np.nan,)*5
    rng=np.random.default_rng(SEED);out=np.empty(BOOTSTRAPS,float)
    for i in range(BOOTSTRAPS):
        pick=rng.integers(0,len(groups),size=len(groups))
        out[i]=mean_bp(np.concatenate([groups[j] for j in pick]))
    return tuple(float(x) for x in np.quantile(out,[.025,.10,.50,.90,.975]))

def yearly(times,vals):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,float)})
    d=d[np.isfinite(d["v"])].copy();d["year"]=d["t"].dt.year
    y=d.groupby("year")["v"].mean()*1e4
    return {str(int(k)):float(v) for k,v in y.items()}

def loo(times,vals):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,float)})
    d=d[np.isfinite(d["v"])].copy();d["year"]=d["t"].dt.year
    out={}
    for y in sorted(d["year"].unique()):
        out[str(int(y))]=mean_bp(d.loc[d["year"]!=y,"v"].to_numpy())
    return (min(out.values()) if out else np.nan),out

def provenance(root):
    p=root/"Research"/"Autonomous"/"guardian_edge_factory_v111_calendar_preoos_forensic"/SOURCE_RUN/"FORENSIC_RESULTS.csv"
    if not p.exists():raise RuntimeError(f"Missing V111 provenance {p}")
    d=pd.read_csv(p)
    m=(d["target_market"].astype(str)==MARKET)&(d["cell_type"].astype(str)=="hour")&(d["horizon_min"].astype(int)==HORIZON)&(d["orientation"].astype(int)==ORIENTATION)&(d["n"].astype(int)==EXPECTED_PREOOS_N)
    q=d[m].copy()
    q=q[q["cell_id"].astype(str).str.contains("22",regex=False)]
    if len(q)!=1:
        raise RuntimeError(f"Expected one exact USDCHF H22 240m LONG row, got {len(q)}: {q.to_dict(orient='records')}")
    r=q.iloc[0]
    if float(r["mean_bp"])<=0:raise RuntimeError("Pre-OOS mean not positive")
    return r.to_dict()

def load_source(root):
    parts=[]
    for y in [2023,2024,2025]:
        p=root/"DataLake"/"raw"/"histdata"/MARKET/"M1"/f"{MARKET}_M1_{y}.parquet"
        if not p.exists():raise RuntimeError(f"Missing locked OOS file {p}")
        d=pd.read_parquet(p)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        pc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None and isinstance(d.index,pd.DatetimeIndex):
            d=d.reset_index();dc=d.columns[0]
        if dc is None or pc is None:raise RuntimeError(f"Bad schema {p}")
        raw=pd.to_datetime(d[dc],errors="coerce")
        if (raw.dt.year>=2026).any():raise RuntimeError(f"2026 contamination {p}")
        pseudo=raw+pd.Timedelta(hours=5)
        q=pd.DataFrame({"pseudo_utc":pseudo,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
        q=q[(q["pseudo_utc"]>=START)&(q["pseudo_utc"]<END)]
        parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("pseudo_utc").drop_duplicates("pseudo_utc",keep="last")
    s=q.set_index("pseudo_utc")["px"].resample("5min",label="right",closed="left").last().dropna().astype(float)
    return s[(s.index>=START)&(s.index<END)]

def source_stage(root,out):
    prov=provenance(root)
    print("PROVENANCE PASS:",{k:prov.get(k) for k in ["candidate_id","cell_id","target_market","horizon_min","orientation","n","mean_bp","net1bp_mean_bp","trim5_mean_bp","leave_one_year_out_min_mean_bp","bootstrap_month_q025_bp"]},flush=True)
    s=load_source(root);idx=s.index
    base=idx[(idx.minute==0)&(idx>=START)&(idx<END)]
    exits=base+pd.Timedelta(minutes=HORIZON)
    ep=s.reindex(base).to_numpy(float);xp=s.reindex(exits).to_numpy(float)
    ok=np.isfinite(ep)&np.isfinite(xp)&(ep!=0)
    times=pd.DatetimeIndex(base[ok]);raw=(xp[ok]/ep[ok]-1.0)
    cand=times.hour.to_numpy()==HOUR;ctrl=~cand
    ct=times[cand];a=raw[cand]*ORIENTATION;b=raw[ctrl]*ORIENTATION
    ce=ep[ok][cand];cx=xp[ok][cand]
    q025,q10,q50,q90,q975=month_bootstrap(ct,a);lm,lj=loo(ct,a);m=mean_bp(a);cm=mean_bp(b)
    existence="NEGATIVE" if m<=0 else ("POSITIVE_CONFIRMED" if np.isfinite(q10) and q10>0 else "POSITIVE_UNCERTAIN")
    E=pd.DataFrame({"source_entry_label":ct,"source_exit_label":ct+pd.Timedelta(minutes=HORIZON),
                    "source_entry_px":ce,"source_exit_px":cx,"source_return":a,"source_bp":a*1e4,
                    "orientation":ORIENTATION,"direction":"LONG"})
    E.to_csv(out/"USDCHF_SOURCE_OOS_EVENT_LEDGER.csv",index=False)
    res={"candidate_id":str(prov["candidate_id"]),"cell_id":str(prov["cell_id"]),"n":int(len(a)),"control_n":int(len(b)),
         "mean_bp":m,"control_mean_bp":cm,"effect_bp":m-cm,"median_bp":float(np.median(a)*1e4),"win_rate":float((a>0).mean()),
         "net1bp_mean_bp":m-1,"net2bp_mean_bp":m-2,"net3bp_mean_bp":m-3,
         "trim1_mean_bp":trim_best_bp(a,.01),"trim2_mean_bp":trim_best_bp(a,.02),"trim5_mean_bp":trim_best_bp(a,.05),
         "remove_best10_mean_bp":remove_best_k_bp(a,10),"remove_best20_mean_bp":remove_best_k_bp(a,20),
         "yearly_mean_bp":yearly(ct,a),"leave_one_year_out_min_bp":lm,"leave_one_year_out":lj,
         "month_bootstrap_q025_bp":q025,"month_bootstrap_q10_bp":q10,"month_bootstrap_q50_bp":q50,
         "month_bootstrap_q90_bp":q90,"month_bootstrap_q975_bp":q975,
         "v2_existence":existence,"2026_accessed":False}
    jd(out/"SOURCE_OOS_SUMMARY.json",res);return res,E

def mt5dt(x):
    t=pd.Timestamp(x)
    if t.tzinfo is None:t=t.tz_localize("UTC")
    else:t=t.tz_convert("UTC")
    return t.to_pydatetime()

def resolve(base):
    if mt5.symbol_info(base):
        mt5.symbol_select(base,True);return base
    c=[]
    for s in mt5.symbols_get() or []:
        u=s.name.upper();b=base.upper()
        if u==b:c.append((0,len(s.name),s.name))
        elif u.startswith(b):c.append((1,len(s.name),s.name))
        elif b in u:c.append((2,len(s.name),s.name))
    if not c:raise RuntimeError(f"Cannot resolve {base}")
    c.sort();sym=c[0][2];mt5.symbol_select(sym,True);return sym

def rates(sym,a,b):
    a=pd.Timestamp(a);b=min(pd.Timestamp(b),END-pd.Timedelta(seconds=1))
    if a>=END:raise RuntimeError("2026 M1 access blocked")
    arr=mt5.copy_rates_range(sym,mt5.TIMEFRAME_M1,mt5dt(a),mt5dt(b))
    if arr is None or len(arr)==0:return pd.DataFrame()
    d=pd.DataFrame(arr);d["time"]=pd.to_datetime(d["time"],unit="s",utc=True).dt.tz_localize(None)
    return d.sort_values("time").drop_duplicates("time")

def ticks(sym,a,b):
    a=pd.Timestamp(a);b=min(pd.Timestamp(b),END-pd.Timedelta(milliseconds=1))
    if a>=END:raise RuntimeError("2026 tick access blocked")
    arr=mt5.copy_ticks_range(sym,mt5dt(a),mt5dt(b),mt5.COPY_TICKS_ALL)
    if arr is None or len(arr)==0:return pd.DataFrame()
    d=pd.DataFrame(arr);d["time"]=pd.to_datetime(d["time_msc"],unit="ms",utc=True).dt.tz_localize(None)
    return d[(d["bid"]>0)&(d["ask"]>0)].sort_values("time")

def pxclose(d,t):
    if d.empty:return np.nan
    z=d[d["time"]==pd.Timestamp(t).floor("min")]
    return float(z.iloc[-1]["close"]) if len(z) else np.nan

def align(E,sym):
    rows=[]
    for _,r in E.iterrows():
        e0=pd.Timestamp(r["source_entry_label"]);x0=pd.Timestamp(r["source_exit_label"])
        d=rates(sym,e0+pd.Timedelta(hours=-9),x0+pd.Timedelta(hours=9))
        rec={k:r[k] for k in ["source_entry_label","source_exit_label","source_entry_px","source_exit_px","source_return","source_bp"]}
        for off in OFFSETS:
            rec[f"e_{off:+d}"]=pxclose(d,e0+pd.Timedelta(hours=off,minutes=-1))
            rec[f"x_{off:+d}"]=pxclose(d,x0+pd.Timedelta(hours=off,minutes=-1))
        rows.append(rec)
    D=pd.DataFrame(rows);stats=[]
    for off in OFFSETS:
        ep=pd.to_numeric(D[f"e_{off:+d}"],errors="coerce");xp=pd.to_numeric(D[f"x_{off:+d}"],errors="coerce")
        ok=ep.notna()&xp.notna()
        if not ok.any():stats.append({"offset_hours":off,"n":0,"coverage":0.0});continue
        se=D.loc[ok,"source_entry_px"].to_numpy(float);sx=D.loc[ok,"source_exit_px"].to_numpy(float)
        fe=ep[ok].to_numpy(float);fx=xp[ok].to_numpy(float)
        de=np.abs((fe/se-1)*1e4);dx=np.abs((fx/sx-1)*1e4)
        src=D.loc[ok,"source_return"].to_numpy(float);gross=(fx/fe-1.0)
        corr=float(np.corrcoef(src,gross)[0,1]) if len(gross)>2 and np.std(src)>0 and np.std(gross)>0 else np.nan
        stats.append({"offset_hours":off,"n":int(ok.sum()),"coverage":float(ok.mean()),
                      "median_abs_entry_price_diff_bp":float(np.median(de)),"median_abs_exit_price_diff_bp":float(np.median(dx)),
                      "median_abs_two_leg_price_diff_bp":float(np.median(np.r_[de,dx])),
                      "mean_ftmo_bid_return_bp":float(gross.mean()*1e4),"source_vs_ftmo_return_corr":corr})
    S=pd.DataFrame(stats);elig=S[S["coverage"]>=.90].copy()
    if elig.empty:raise RuntimeError("No offset >=90% coverage")
    best=elig.sort_values(["median_abs_two_leg_price_diff_bp","offset_hours"]).iloc[0].to_dict()
    return D,S,best

def first_exec(sym,t,point):
    t=pd.Timestamp(t);q=ticks(sym,t,t+pd.Timedelta(seconds=90))
    if not q.empty:
        r=q.iloc[0];return pd.Timestamp(r["time"]),float(r["bid"]),float(r["ask"]),"tick"
    m=rates(sym,t,t+pd.Timedelta(minutes=2))
    if not m.empty:
        r=m.iloc[0];bid=float(r["open"]);ask=bid+float(r["spread"])*point
        return pd.Timestamp(r["time"]),bid,ask,"m1_fallback"
    return None

def execute(E,sym,off):
    point=float(mt5.symbol_info(sym).point);rows=[]
    for _,r in E.iterrows():
        eb=pd.Timestamp(r["source_entry_label"])+pd.Timedelta(hours=off);xb=pd.Timestamp(r["source_exit_label"])+pd.Timedelta(hours=off)
        en=first_exec(sym,eb,point);ex=first_exec(sym,xb,point)
        base={**r.to_dict(),"mapped_entry_boundary":eb,"mapped_exit_boundary":xb,"execution_available":False,
              "entry_time":pd.NaT,"exit_time":pd.NaT,"entry_bid":np.nan,"entry_ask":np.nan,"exit_bid":np.nan,"exit_ask":np.nan,
              "entry_spread_bp":np.nan,"exit_spread_bp":np.nan,"ftmo_bid_gross_bp":np.nan,"ftmo_exec_bp":np.nan}
        if en is None or ex is None:rows.append(base);continue
        et,ebi,eask,es=en;xt,xbi,xask,xs=ex
        gross=(xbi/ebi-1)*1e4
        net=(xbi-eask)/eask*1e4
        base.update({"execution_available":True,"entry_time":et,"exit_time":xt,"entry_bid":ebi,"entry_ask":eask,"exit_bid":xbi,"exit_ask":xask,
                     "entry_spread_bp":(eask-ebi)/ebi*1e4,"exit_spread_bp":(xask-xbi)/xbi*1e4,
                     "ftmo_bid_gross_bp":gross,"ftmo_exec_bp":net,"entry_source":es,"exit_source":xs})
        rows.append(base)
    return pd.DataFrame(rows)

def exec_summary(X):
    z=X[X["execution_available"]==True].copy()
    src=z["source_bp"].to_numpy(float);g=z["ftmo_bid_gross_bp"].to_numpy(float);n=z["ftmo_exec_bp"].to_numpy(float)
    corr=float(np.corrcoef(src,g)[0,1]) if len(z)>2 and np.std(src)>0 and np.std(g)>0 else np.nan
    yrs=pd.to_datetime(z["source_entry_label"]).dt.year;yy={}
    for y,h in z.assign(_y=yrs).groupby("_y"):
        a=h["ftmo_exec_bp"].to_numpy(float);yy[str(int(y))]={"n":int(len(a)),"mean_exec_bp":float(a.mean())}
    return {"source_events":int(len(X)),"execution_events":int(len(z)),"coverage":float(len(z)/len(X)),
            "source_mean_bp_on_exec_sample":float(src.mean()),"ftmo_bid_gross_mean_bp":float(g.mean()),
            "source_vs_ftmo_bid_return_corr":corr,"mean_entry_spread_bp":float(z["entry_spread_bp"].mean()),
            "mean_exit_spread_bp":float(z["exit_spread_bp"].mean()),"mean_exec_bp":float(n.mean()),
            "median_exec_bp":float(np.median(n)),"win_rate":float((n>0).mean()),
            "trim1_exec_bp":trim_best_bp(n/1e4,.01),"trim2_exec_bp":trim_best_bp(n/1e4,.02),"trim5_exec_bp":trim_best_bp(n/1e4,.05),
            "years":yy}

def meta(sym):
    i=mt5.symbol_info(sym)
    return {k:getattr(i,k,None) for k in ["name","point","digits","spread","swap_mode","swap_long","swap_short","swap_rollover3days","trade_contract_size"]}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");ap.add_argument("--out",required=True)
    a=ap.parse_args();root=Path(a.root);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    src,E=source_stage(root,out);print("SOURCE OOS:",json.dumps(src,indent=2),flush=True)
    if float(src["mean_bp"])<=0:
        jd(out/"FINAL_SUMMARY.json",{"source_oos":src,"ftmo_execution":"NOT_RUN_SOURCE_MEAN_NONPOSITIVE","2026_accessed":False})
        (out/"SUCCESS.flag").write_text("OK\nSTAGE_B_NOT_RUN\n2026_ACCESS=false\n",encoding="utf-8");return
    if not mt5.initialize():raise RuntimeError("MT5 init failed "+str(mt5.last_error()))
    try:
        ai=mt5.account_info();ident=" ".join(str(x or "") for x in [getattr(ai,"server",""),getattr(ai,"company",""),getattr(ai,"name","")])
        if "ftmo" not in ident.lower():raise RuntimeError(f"FTMO guard failed: {ident}")
        sym=resolve(MARKET);D,S,best=align(E,sym)
        D.to_csv(out/"USDCHF_ALIGNMENT_EVENT_MATRIX.csv",index=False);S.to_csv(out/"USDCHF_ALIGNMENT_SCAN.csv",index=False)
        print("BEST ALIGNMENT:",best,flush=True)
        X=execute(E,sym,int(best["offset_hours"]));X.to_csv(out/"USDCHF_FTMO_EXECUTION_LEDGER.csv",index=False)
        ex=exec_summary(X)
        vals=X.loc[X["execution_available"]==True,"ftmo_exec_bp"].to_numpy(float)
        pd.DataFrame([{"extra_cost_bp":c,"n":int(len(vals)),"mean_net_bp":float((vals-c).mean()),"win_rate":float(((vals-c)>0).mean())} for c in [0,.25,.5,.75,1,1.5,2,2.5,3,4,5]]).to_csv(out/"USDCHF_EXTRA_COST_GRID.csv",index=False)
        final={"source_oos":src,"best_alignment":best,"execution":ex,"current_ftmo_symbol_metadata":meta(sym),
               "swap_note":"Current metadata only; historical swap not reconstructed.","ftmo_identity":ident,"2026_accessed":False}
        jd(out/"FINAL_SUMMARY.json",final);(out/"SUCCESS.flag").write_text("OK\n2026_ACCESS=false\n",encoding="utf-8")
        print("EXECUTION:",json.dumps(ex,indent=2),flush=True)
        print("=== USDCHF V111 H22 240M PIPELINE COMPLETE ===",flush=True)
    finally:mt5.shutdown()

if __name__=="__main__":
    try:main()
    except Exception as e:
        print("FAILED:",e,flush=True);traceback.print_exc();raise
