from pathlib import Path
import argparse, json, math, traceback
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

ROOT_DEFAULT=Path(r"D:\MT5_Backtests")
CAP=pd.Timestamp("2026-01-01 00:00")
EXPECTED_N=705
EXPECTED_MEAN_BP=1.1896855761203053
OFFSETS=list(range(-8,9))

def jd(p,o): p.write_text(json.dumps(o,indent=2,default=str),encoding="utf-8")

def mt5dt(x):
    t=pd.Timestamp(x)
    if t.tzinfo is None:t=t.tz_localize("UTC")
    else:t=t.tz_convert("UTC")
    return t.to_pydatetime()

def latest_source_run(root):
    base=root/"Research"/"Autonomous"/"v111_c1_xagusd_locked_oos_v2"
    runs=sorted([p for p in base.glob("XAGC1-*") if p.is_dir()],key=lambda p:p.name,reverse=True)
    for p in runs:
        s=p/"SUMMARY.json"; l=p/"V111_C1_XAGUSD_OOS_EVENT_LEDGER.csv"
        if not s.exists() or not l.exists(): continue
        obj=json.loads(s.read_text(encoding="utf-8"))
        if obj.get("2026_accessed") is not False: continue
        if int(obj.get("n",-1))!=EXPECTED_N: continue
        if abs(float(obj.get("mean_bp",999))-EXPECTED_MEAN_BP)>1e-9: continue
        c=obj.get("candidate",{})
        if c.get("candidate_id")!="C1" or c.get("market")!="XAGUSD" or int(c.get("hour",-1))!=11 or int(c.get("horizon_min",-1))!=60 or int(c.get("orientation",0))!=-1:
            continue
        E=pd.read_csv(l,parse_dates=["source_entry_label","source_exit_label"])
        if len(E)!=EXPECTED_N: continue
        return p,obj,E
    raise RuntimeError("No exact completed V111 C1 XAGUSD OOS source run found")

def resolve(base):
    if mt5.symbol_info(base):
        mt5.symbol_select(base,True);return base
    cand=[]
    for s in mt5.symbols_get() or []:
        u=s.name.upper();b=base.upper()
        if u==b:cand.append((0,len(s.name),s.name))
        elif u.startswith(b):cand.append((1,len(s.name),s.name))
        elif b in u:cand.append((2,len(s.name),s.name))
    if not cand: raise RuntimeError(f"Cannot resolve {base}")
    cand.sort();sym=cand[0][2];mt5.symbol_select(sym,True);return sym

def rates(symbol,a,b):
    a=pd.Timestamp(a);b=min(pd.Timestamp(b),CAP-pd.Timedelta(seconds=1))
    if a>=CAP: raise RuntimeError("2026 M1 access blocked")
    arr=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M1,mt5dt(a),mt5dt(b))
    if arr is None or len(arr)==0:return pd.DataFrame()
    d=pd.DataFrame(arr)
    d["time"]=pd.to_datetime(d["time"],unit="s",utc=True).dt.tz_localize(None)
    return d.sort_values("time").drop_duplicates("time")

def ticks(symbol,a,b):
    a=pd.Timestamp(a);b=min(pd.Timestamp(b),CAP-pd.Timedelta(milliseconds=1))
    if a>=CAP: raise RuntimeError("2026 tick access blocked")
    arr=mt5.copy_ticks_range(symbol,mt5dt(a),mt5dt(b),mt5.COPY_TICKS_ALL)
    if arr is None or len(arr)==0:return pd.DataFrame()
    d=pd.DataFrame(arr)
    d["time"]=pd.to_datetime(d["time_msc"],unit="ms",utc=True).dt.tz_localize(None)
    return d[(d["bid"]>0)&(d["ask"]>0)].sort_values("time")

def px_close_at(d,t):
    if d.empty:return np.nan
    t=pd.Timestamp(t).floor("min")
    z=d[d["time"]==t]
    return float(z.iloc[-1]["close"]) if len(z) else np.nan

def scan_alignment(E,symbol):
    rows=[]
    for _,r in E.iterrows():
        e0=pd.Timestamp(r["source_entry_label"]);x0=pd.Timestamp(r["source_exit_label"])
        lo=e0+pd.Timedelta(hours=min(OFFSETS),minutes=-2)
        hi=x0+pd.Timedelta(hours=max(OFFSETS),minutes=2)
        d=rates(symbol,lo,hi)
        rec={
            "source_entry_label":e0,"source_exit_label":x0,
            "source_entry_px":float(r["source_entry_px"]),"source_exit_px":float(r["source_exit_px"]),
            "source_return":float(r["source_return"])
        }
        for off in OFFSETS:
            # source right-labelled boundary uses last M1 close immediately before boundary
            et=e0+pd.Timedelta(hours=off,minutes=-1)
            xt=x0+pd.Timedelta(hours=off,minutes=-1)
            rec[f"e_{off:+d}"]=px_close_at(d,et)
            rec[f"x_{off:+d}"]=px_close_at(d,xt)
        rows.append(rec)
    D=pd.DataFrame(rows)
    stats=[]
    for off in OFFSETS:
        ep=pd.to_numeric(D[f"e_{off:+d}"],errors="coerce")
        xp=pd.to_numeric(D[f"x_{off:+d}"],errors="coerce")
        ok=ep.notna()&xp.notna()
        if not ok.any():
            stats.append({"offset_hours":off,"n":0,"coverage":0.0});continue
        se=D.loc[ok,"source_entry_px"].to_numpy(float);sx=D.loc[ok,"source_exit_px"].to_numpy(float)
        fe=ep[ok].to_numpy(float);fx=xp[ok].to_numpy(float)
        de=np.abs((fe/se-1)*1e4);dx=np.abs((fx/sx-1)*1e4)
        src=D.loc[ok,"source_return"].to_numpy(float)
        gross=-(fx/fe-1.0)
        corr=float(np.corrcoef(src,gross)[0,1]) if len(gross)>2 and np.std(src)>0 and np.std(gross)>0 else np.nan
        stats.append({
            "offset_hours":off,"n":int(ok.sum()),"coverage":float(ok.mean()),
            "median_abs_entry_price_diff_bp":float(np.median(de)),
            "median_abs_exit_price_diff_bp":float(np.median(dx)),
            "median_abs_two_leg_price_diff_bp":float(np.median(np.r_[de,dx])),
            "mean_ftmo_bid_return_bp":float(gross.mean()*1e4),
            "source_vs_ftmo_return_corr":corr
        })
    S=pd.DataFrame(stats)
    elig=S[S["coverage"]>=0.90].copy()
    if elig.empty: raise RuntimeError("No alignment offset reaches >=90% two-leg coverage")
    best=elig.sort_values(["median_abs_two_leg_price_diff_bp","offset_hours"]).iloc[0].to_dict()
    return D,S,best

def first_exec(symbol,t,point,max_seconds=90):
    t=pd.Timestamp(t)
    q=ticks(symbol,t,t+pd.Timedelta(seconds=max_seconds))
    if not q.empty:
        r=q.iloc[0]
        return pd.Timestamp(r["time"]),float(r["bid"]),float(r["ask"]),"tick"
    m=rates(symbol,t,t+pd.Timedelta(minutes=2))
    if not m.empty:
        r=m.iloc[0]
        bid=float(r["open"]);ask=bid+float(r["spread"])*point
        return pd.Timestamp(r["time"]),bid,ask,"m1_fallback"
    return None

def execute(E,symbol,offset):
    point=float(mt5.symbol_info(symbol).point);rows=[]
    for _,r in E.iterrows():
        ebound=pd.Timestamp(r["source_entry_label"])+pd.Timedelta(hours=offset)
        xbound=pd.Timestamp(r["source_exit_label"])+pd.Timedelta(hours=offset)
        en=first_exec(symbol,ebound,point);ex=first_exec(symbol,xbound,point)
        base={**r.to_dict(),"mapped_entry_boundary":ebound,"mapped_exit_boundary":xbound,
              "execution_available":False,"entry_time":pd.NaT,"exit_time":pd.NaT,
              "entry_bid":np.nan,"entry_ask":np.nan,"exit_bid":np.nan,"exit_ask":np.nan,
              "entry_spread_bp":np.nan,"exit_spread_bp":np.nan,
              "ftmo_bid_gross_bp":np.nan,"ftmo_exec_bp":np.nan,
              "entry_source":None,"exit_source":None}
        if en is None or ex is None:
            rows.append(base);continue
        et,eb,ea,es=en;xt,xb,xa,xs=ex
        gross=-(xb/eb-1.0)*1e4
        net=(eb-xa)/eb*1e4
        base.update({
            "execution_available":True,"entry_time":et,"exit_time":xt,
            "entry_bid":eb,"entry_ask":ea,"exit_bid":xb,"exit_ask":xa,
            "entry_spread_bp":(ea-eb)/eb*1e4,"exit_spread_bp":(xa-xb)/xb*1e4,
            "ftmo_bid_gross_bp":gross,"ftmo_exec_bp":net,
            "entry_source":es,"exit_source":xs
        })
        rows.append(base)
    return pd.DataFrame(rows)

def trim_best(x,pct):
    x=np.asarray(x,float);x=x[np.isfinite(x)]
    if not len(x):return np.nan
    k=int(math.ceil(len(x)*pct))
    return float(np.sort(x)[:-k].mean()) if 0<k<len(x) else float(x.mean())

def summary(X):
    z=X[X["execution_available"]==True].copy()
    src=z["source_bp"].to_numpy(float)
    gross=pd.to_numeric(z["ftmo_bid_gross_bp"],errors="coerce").to_numpy(float)
    net=pd.to_numeric(z["ftmo_exec_bp"],errors="coerce").to_numpy(float)
    years=pd.to_datetime(z["source_entry_label"]).dt.year
    yy={}
    for y,g in z.assign(_y=years).groupby("_y"):
        a=pd.to_numeric(g["ftmo_exec_bp"],errors="coerce").dropna().to_numpy(float)
        yy[str(int(y))]={"n":int(len(a)),"mean_exec_bp":float(a.mean()) if len(a) else np.nan}
    corr=float(np.corrcoef(src,gross)[0,1]) if len(z)>2 and np.std(src)>0 and np.std(gross)>0 else np.nan
    return {
        "source_events":int(len(X)),"execution_events":int(len(z)),
        "coverage":float(len(z)/len(X)) if len(X) else 0,
        "source_mean_bp_on_exec_sample":float(src.mean()) if len(src) else np.nan,
        "ftmo_bid_gross_mean_bp":float(gross.mean()) if len(gross) else np.nan,
        "source_vs_ftmo_bid_return_corr":corr,
        "mean_entry_spread_bp":float(z["entry_spread_bp"].mean()) if len(z) else np.nan,
        "mean_exit_spread_bp":float(z["exit_spread_bp"].mean()) if len(z) else np.nan,
        "mean_exec_bp":float(net.mean()) if len(net) else np.nan,
        "median_exec_bp":float(np.median(net)) if len(net) else np.nan,
        "win_rate":float((net>0).mean()) if len(net) else np.nan,
        "trim1_exec_bp":trim_best(net,.01),
        "trim2_exec_bp":trim_best(net,.02),
        "trim5_exec_bp":trim_best(net,.05),
        "years":yy
    }

def grid(X):
    z=X[X["execution_available"]==True]
    x=pd.to_numeric(z["ftmo_exec_bp"],errors="coerce").dropna().to_numpy(float)
    rows=[]
    for c in [0,.25,.5,.75,1,1.5,2,2.5,3,4,5]:
        y=x-c
        rows.append({"extra_cost_bp_after_observed_spread":c,"n":int(len(y)),
                     "mean_net_bp":float(y.mean()) if len(y) else np.nan,
                     "win_rate":float((y>0).mean()) if len(y) else np.nan})
    return pd.DataFrame(rows)

def meta(sym):
    i=mt5.symbol_info(sym)
    keys=["name","point","digits","spread","swap_mode","swap_long","swap_short","swap_rollover3days",
          "trade_contract_size","trade_tick_size","trade_tick_value"]
    return {k:getattr(i,k,None) for k in keys}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=str(ROOT_DEFAULT));ap.add_argument("--out",required=True)
    a=ap.parse_args();root=Path(a.root);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    src,obj,E=latest_source_run(root)
    print("SOURCE LOCK VERIFIED:",src,flush=True)
    print("SOURCE RESULT: n=705 mean=+1.1896855761203053 bp; 2026=false",flush=True)

    if not mt5.initialize(): raise RuntimeError("MT5 init failed "+str(mt5.last_error()))
    try:
        ai=mt5.account_info()
        ident=" ".join(str(x or "") for x in [getattr(ai,"server",""),getattr(ai,"company",""),getattr(ai,"name","")])
        if "ftmo" not in ident.lower(): raise RuntimeError(f"FTMO guard failed: {ident}")
        sym=resolve("XAGUSD")
        print("FTMO SYMBOL:",sym,flush=True)

        D,S,best=scan_alignment(E,sym)
        D.to_csv(out/"XAGUSD_ALIGNMENT_EVENT_MATRIX.csv",index=False)
        S.to_csv(out/"XAGUSD_ALIGNMENT_SCAN.csv",index=False)
        print("BEST ALIGNMENT (price proximity only):",best,flush=True)

        off=int(best["offset_hours"])
        X=execute(E,sym,off)
        X.to_csv(out/"XAGUSD_FTMO_EXECUTION_LEDGER.csv",index=False)
        grid(X).to_csv(out/"XAGUSD_EXTRA_COST_GRID.csv",index=False)
        res={
            "source_run":str(src),
            "source_result":{"n":EXPECTED_N,"mean_bp":EXPECTED_MEAN_BP,"v2_existence":obj.get("v2_existence")},
            "alignment_selection_rule":">=90% coverage then minimum median absolute two-leg source-vs-FTMO price difference; PnL excluded",
            "best_alignment":best,
            "execution_convention":"first FTMO tick at/after mapped H11 entry boundary and H12 exit boundary; SHORT bid->ask",
            "execution":summary(X),
            "current_ftmo_symbol_metadata":meta(sym),
            "commission_note":"Historical commission is not invented; extra-cost grid is provided after observed spread.",
            "ftmo_identity":ident,
            "2026_accessed":False
        }
        jd(out/"SUMMARY.json",res)
        (out/"SUCCESS.flag").write_text("OK\n2026_ACCESS=false\n",encoding="utf-8")
        print("EXECUTION:",json.dumps(res["execution"],indent=2),flush=True)
        print("=== XAGUSD FTMO EXECUTION AUDIT COMPLETE ===",flush=True)
    finally:
        mt5.shutdown()

if __name__=="__main__":
    try:main()
    except Exception as e:
        print("FAILED:",e,flush=True);traceback.print_exc();raise
