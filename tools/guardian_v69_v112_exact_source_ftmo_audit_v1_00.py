from pathlib import Path
from datetime import timedelta
import argparse, json, math, traceback
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

ROOT_DEFAULT=Path(r"D:\MT5_Backtests")
START=pd.Timestamp("2023-01-01 00:00")
END=pd.Timestamp("2026-01-01 00:00")
EXPECTED_V69_N=155
EXPECTED_V69_MEAN=4.639075481195655
EXPECTED_V112_N=556
EXPECTED_V112_MEAN=1.4552352492311669

def write_json(p,o):
    p.write_text(json.dumps(o,indent=2,default=str),encoding="utf-8")

def mean_bp(x):
    x=np.asarray(x,dtype=float);x=x[np.isfinite(x)]
    return float(x.mean()*1e4) if len(x) else np.nan

def trim_best_bp(x,pct):
    x=np.asarray(x,dtype=float);x=x[np.isfinite(x)]
    if not len(x): return np.nan
    k=int(math.ceil(len(x)*pct))
    if k<=0:return mean_bp(x)
    if k>=len(x):return np.nan
    return mean_bp(np.sort(x)[:-k])

def remove_best_bp(x,k):
    x=np.asarray(x,dtype=float);x=x[np.isfinite(x)]
    if len(x)<=k:return np.nan
    return mean_bp(np.sort(x)[:-k])

def max_dd_bp(x):
    x=np.asarray(x,dtype=float);x=x[np.isfinite(x)]*1e4
    if not len(x):return np.nan
    eq=np.r_[0,np.cumsum(x)]
    peak=np.maximum.accumulate(eq)
    return float((eq-peak).min())

def load_histdata(root,sym,years):
    parts=[]
    for y in years:
        p=root/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
        if not p.exists(): raise RuntimeError(f"Missing canonical HistData file: {p}")
        d=pd.read_parquet(p)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        pc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None and isinstance(d.index,pd.DatetimeIndex):
            d=d.reset_index();dc=d.columns[0]
        if dc is None or pc is None:raise RuntimeError(f"Bad schema {p}")
        dt=pd.to_datetime(d[dc],errors="coerce")
        if (dt.dt.year>=2026).any(): raise RuntimeError(f"2026 contamination in {p}")
        q=pd.DataFrame({"dt":dt,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
        q=q[q.dt.dt.year==y]
        parts.append(q)
    return pd.concat(parts,ignore_index=True).sort_values("dt").drop_duplicates("dt",keep="last")

def build_v69_events(root):
    d=load_histdata(root,"USDCHF",[2023,2024,2025])
    q=d.set_index("dt").px.resample("1D").last().dropna().to_frame("px")
    q["fwd"]=q.px.shift(-1)/q.px-1
    q["next_day"]=pd.Series(q.index,index=q.index).shift(-1)
    q=q.dropna(subset=["fwd","next_day"])
    g=q[q.index.dayofweek==4].copy()

    # Recover the actual source M1 timestamp that supplied each daily close.
    dd=d.copy()
    dd["day"]=dd.dt.dt.floor("D")
    last=dd.sort_values("dt").groupby("day",as_index=True).tail(1).set_index("day")
    rows=[]
    for day,r in g.iterrows():
        nxt=pd.Timestamp(r["next_day"])
        if day not in last.index or nxt not in last.index:continue
        e=last.loc[day];x=last.loc[nxt]
        rows.append({
            "source_day":day,
            "source_next_day":nxt,
            "source_entry_raw":e.dt,
            "source_exit_raw":x.dt,
            "entry_utc":pd.Timestamp(e.dt)+pd.Timedelta(hours=5),
            "exit_utc":pd.Timestamp(x.dt)+pd.Timedelta(hours=5),
            "source_entry_px":float(e.px),
            "source_exit_px":float(x.px),
            "source_return":float(x.px/e.px-1.0),
        })
    E=pd.DataFrame(rows)
    return E

def build_v112_events(root):
    d=load_histdata(root,"AUDUSD",[2023,2024,2025])
    utc=pd.to_datetime(d.dt,errors="coerce")+pd.Timedelta(hours=5)
    q=pd.DataFrame({"utc":utc,"px":pd.to_numeric(d.px,errors="coerce")}).dropna()
    q=q[(q.utc>=START)&(q.utc<END)]
    s=q.sort_values("utc").drop_duplicates("utc",keep="last").set_index("utc").px
    s=s.resample("5min",label="right",closed="left").last().dropna().astype(float)
    s=s[(s.index>=START)&(s.index<END)]
    idx=s.index
    base=idx[(idx.minute==0)&(idx>=START)&(idx<END)]
    exits=base+pd.Timedelta(minutes=120)
    a=s.reindex(base).to_numpy(float)
    b=s.reindex(exits).to_numpy(float)
    ok=np.isfinite(a)&np.isfinite(b)&(a!=0)
    times=pd.DatetimeIndex(base[ok]);rets=(b[ok]/a[ok]-1.0)
    cand=times.hour.to_numpy()==21
    times=times[cand];rets=rets[cand]
    vals_a=s.reindex(times).to_numpy(float)
    vals_b=s.reindex(times+pd.Timedelta(minutes=120)).to_numpy(float)
    E=pd.DataFrame({
        "entry_utc":times,
        "exit_utc":times+pd.Timedelta(minutes=120),
        "source_entry_px":vals_a,
        "source_exit_px":vals_b,
        "source_return":rets[cand]*-1.0,
    })
    return E

def parity(name,E,n_exp,mean_exp):
    n=len(E);m=mean_bp(E.source_return)
    out={"strategy":name,"expected_n":n_exp,"actual_n":n,"expected_mean_bp":mean_exp,
         "actual_mean_bp":m,"n_match":n==n_exp,
         "mean_abs_diff_bp":abs(m-mean_exp) if np.isfinite(m) else None}
    out["pass"]=bool(out["n_match"] and out["mean_abs_diff_bp"]<=1e-6)
    return out

def resolve(base):
    if mt5.symbol_info(base):
        mt5.symbol_select(base,True);return base
    c=[]
    for s in mt5.symbols_get() or []:
        u=s.name.upper();b=base.upper()
        if u==b:c.append((0,len(s.name),s.name))
        elif u.startswith(b):c.append((1,len(s.name),s.name))
        elif b in u:c.append((2,len(s.name),s.name))
    if not c:raise RuntimeError(f"Could not resolve {base}")
    c.sort();mt5.symbol_select(c[0][2],True);return c[0][2]

def ticks(symbol,start,end):
    if pd.Timestamp(start)>=END:raise RuntimeError("2026 tick access blocked")
    end=min(pd.Timestamp(end),END-pd.Timedelta(milliseconds=1))
    a=mt5.copy_ticks_range(symbol,pd.Timestamp(start).to_pydatetime(),end.to_pydatetime(),mt5.COPY_TICKS_ALL)
    if a is None or len(a)==0:return pd.DataFrame()
    d=pd.DataFrame(a);d["time"]=pd.to_datetime(d.time_msc,unit="ms",utc=True).dt.tz_localize(None)
    return d[(d.bid>0)&(d.ask>0)].sort_values("time")

def rates_m1(symbol,start,end):
    if pd.Timestamp(start)>=END:raise RuntimeError("2026 M1 access blocked")
    end=min(pd.Timestamp(end),END-pd.Timedelta(seconds=1))
    a=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M1,pd.Timestamp(start).to_pydatetime(),end.to_pydatetime())
    if a is None or len(a)==0:return pd.DataFrame()
    d=pd.DataFrame(a);d["time"]=pd.to_datetime(d.time,unit="s",utc=True).dt.tz_localize(None)
    return d.sort_values("time")

def exec_last_tick_in_min(symbol,when,point):
    when=pd.Timestamp(when)
    t=ticks(symbol,when,when+pd.Timedelta(seconds=59, milliseconds=999))
    if not t.empty:
        r=t.iloc[-1];return pd.Timestamp(r.time),float(r.bid),float(r.ask),"tick"
    m=rates_m1(symbol,when,when+pd.Timedelta(minutes=1))
    if not m.empty:
        r=m.iloc[0];bid=float(r.close);ask=bid+float(r.spread)*point
        return pd.Timestamp(r.time)+pd.Timedelta(seconds=59),bid,ask,"m1_fallback"
    return None

def exec_first_tick(symbol,when,point):
    when=pd.Timestamp(when)
    t=ticks(symbol,when,when+pd.Timedelta(seconds=90))
    if not t.empty:
        r=t.iloc[0];return pd.Timestamp(r.time),float(r.bid),float(r.ask),"tick"
    m=rates_m1(symbol,when,when+pd.Timedelta(minutes=2))
    if not m.empty:
        r=m.iloc[0];bid=float(r.open);ask=bid+float(r.spread)*point
        return pd.Timestamp(r.time),bid,ask,"m1_fallback"
    return None

def audit_execution(E,symbol,direction,mode):
    info=mt5.symbol_info(symbol);point=float(info.point)
    rows=[]
    for i,r in E.iterrows():
        if mode=="last_minute":
            en=exec_last_tick_in_min(symbol,r.entry_utc,point)
            ex=exec_last_tick_in_min(symbol,r.exit_utc,point)
        else:
            en=exec_first_tick(symbol,r.entry_utc,point)
            ex=exec_first_tick(symbol,r.exit_utc,point)
        if en is None or ex is None:
            rows.append({**r.to_dict(),"execution_available":False})
            continue
        et,ebid,eask,esrc=en;xt,xbid,xask,xsrc=ex
        if direction=="long":
            exec_ret=xbid/eask-1.0
            bid_ret=xbid/ebid-1.0
        else:
            exec_ret=(ebid-xask)/ebid
            bid_ret=-(xbid/ebid-1.0)
        rows.append({
            **r.to_dict(),"execution_available":True,
            "ftmo_entry_time":et,"ftmo_exit_time":xt,
            "entry_source":esrc,"exit_source":xsrc,
            "entry_bid":ebid,"entry_ask":eask,"exit_bid":xbid,"exit_ask":xask,
            "entry_spread_bp":(eask-ebid)/ebid*1e4,
            "exit_spread_bp":(xask-xbid)/xbid*1e4,
            "ftmo_bid_return":bid_ret,
            "ftmo_exec_return":exec_ret,
            "ftmo_exec_bp":exec_ret*1e4,
            "source_bp":float(r.source_return)*1e4,
            "entry_source_vs_ftmo_bid_bp":(ebid/float(r.source_entry_px)-1)*1e4,
            "exit_source_vs_ftmo_bid_bp":(xbid/float(r.source_exit_px)-1)*1e4,
            "hold_hours":(pd.Timestamp(xt)-pd.Timestamp(et)).total_seconds()/3600,
        })
    return pd.DataFrame(rows)

def stats(X):
    z=X[X.execution_available==True].copy()
    x=pd.to_numeric(z.ftmo_exec_return,errors="coerce").dropna().to_numpy(float)
    return {
        "source_events":int(len(X)),
        "execution_events":int(len(x)),
        "coverage":float(len(x)/len(X)) if len(X) else 0,
        "mean_exec_bp":mean_bp(x),
        "median_exec_bp":float(np.median(x)*1e4) if len(x) else np.nan,
        "win_rate":float((x>0).mean()) if len(x) else np.nan,
        "trim1_bp":trim_best_bp(x,.01),
        "trim2_bp":trim_best_bp(x,.02),
        "remove_best5_bp":remove_best_bp(x,5),
        "max_drawdown_cumsum_bp":max_dd_bp(x),
        "mean_entry_spread_bp":float(z.entry_spread_bp.mean()) if len(z) else np.nan,
        "mean_exit_spread_bp":float(z.exit_spread_bp.mean()) if len(z) else np.nan,
        "mean_hold_hours":float(z.hold_hours.mean()) if len(z) else np.nan,
    }

def metadata(sym):
    i=mt5.symbol_info(sym);a=mt5.account_info();t=mt5.terminal_info()
    keys=["name","digits","point","spread","spread_float","trade_contract_size","trade_tick_size","trade_tick_value",
          "swap_mode","swap_long","swap_short","swap_rollover3days","currency_base","currency_profit"]
    return {
        "symbol":{k:getattr(i,k) for k in keys if i is not None and hasattr(i,k)},
        "account":{"server":getattr(a,"server",None),"company":getattr(a,"company",None),"name":getattr(a,"name",None)},
        "terminal_path":getattr(t,"path",None) if t else None,
    }

def cost_grid(X,label):
    z=X[X.execution_available==True].copy()
    x=pd.to_numeric(z.ftmo_exec_bp,errors="coerce").dropna().to_numpy(float)
    rows=[]
    for c in [0,.25,.5,.75,1,1.5,2,2.5,3,4,5]:
        y=x-c
        rows.append({"strategy":label,"extra_cost_bp_after_observed_spread":c,"n":len(y),
                     "mean_net_bp":float(y.mean()) if len(y) else np.nan,
                     "win_rate":float((y>0).mean()) if len(y) else np.nan,
                     "max_drawdown_cumsum_bp":max_dd_bp(y/1e4) if len(y) else np.nan})
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=str(ROOT_DEFAULT));ap.add_argument("--out",required=True)
    args=ap.parse_args();root=Path(args.root);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)

    v69=build_v69_events(root);v112=build_v112_events(root)
    p69=parity("V69",v69,EXPECTED_V69_N,EXPECTED_V69_MEAN)
    p112=parity("V112_C3",v112,EXPECTED_V112_N,EXPECTED_V112_MEAN)
    v69.to_csv(out/"V69_ORIGINAL_SOURCE_EVENTS.csv",index=False)
    v112.to_csv(out/"V112_C3_ORIGINAL_SOURCE_EVENTS.csv",index=False)
    write_json(out/"SOURCE_PARITY.json",{"V69":p69,"V112":p112,"2026_accessed":False})
    print("SOURCE PARITY V69:",p69,flush=True);print("SOURCE PARITY V112:",p112,flush=True)
    if not (p69["pass"] and p112["pass"]):
        raise RuntimeError("SOURCE PARITY FAILED. Execution audit aborted before MT5 pricing.")

    if not mt5.initialize():
        raise RuntimeError("MT5 initialize failed: "+str(mt5.last_error()))
    try:
        a=mt5.account_info()
        ident=" ".join(str(x or "") for x in [getattr(a,"server",""),getattr(a,"company",""),getattr(a,"name","")])
        if "ftmo" not in ident.lower():
            raise RuntimeError(f"FTMO guard failed. Connected identity: {ident!r}")
        chf=resolve("USDCHF");aud=resolve("AUDUSD")
        print("FTMO symbols:",chf,aud,flush=True)
        x69=audit_execution(v69,chf,"long","last_minute")
        x112=audit_execution(v112,aud,"short","first_tick")
        x69.to_csv(out/"V69_FTMO_EXECUTION_LEDGER.csv",index=False)
        x112.to_csv(out/"V112_C3_FTMO_EXECUTION_LEDGER.csv",index=False)
        cost_grid(x69,"V69_USDCHF_FRIDAY_LONG").to_csv(out/"V69_EXTRA_COST_GRID.csv",index=False)
        cost_grid(x112,"V112_AUDUSD_H21_SHORT_120M").to_csv(out/"V112_EXTRA_COST_GRID.csv",index=False)

        result={
            "source_parity":{"V69":p69,"V112":p112},
            "V69":{"stats_after_observed_spread":stats(x69),"ftmo_metadata_now":metadata(chf),
                   "weekend_hold":True,
                   "swap_note":"Historical swap is NOT reconstructed here. V69 normally holds across the weekend, so carry/swap remains a required additional cost after spread."},
            "V112":{"stats_after_observed_spread":stats(x112),"ftmo_metadata_now":metadata(aud),
                    "swap_note":"Historical swap not reconstructed. H21->H23 may or may not cross broker rollover depending FTMO platform time; inspect current trading/swap specification separately."},
            "2026_accessed":False,
        }
        write_json(out/"SUMMARY.json",result)
        (out/"SUCCESS.flag").write_text("OK\nSOURCE_PARITY=PASS\n2026_ACCESS=false\n",encoding="utf-8")
        print("=== EXACT SOURCE -> FTMO EXECUTION AUDIT COMPLETE ===",flush=True)
        print(json.dumps(result,indent=2,default=str),flush=True)
    finally:
        mt5.shutdown()

if __name__=="__main__":
    try:main()
    except Exception as e:
        print("=== FAILED ===",e,flush=True)
        try:
            Path(__import__("sys").argv[__import__("sys").argv.index("--out")+1],"FAILED.txt").write_text(str(e)+"\n\n"+traceback.format_exc(),encoding="utf-8")
        except Exception:pass
        raise
