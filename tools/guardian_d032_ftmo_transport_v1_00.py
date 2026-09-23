from pathlib import Path
import argparse, json, math, traceback
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

START=pd.Timestamp("2018-06-01 00:00")
PRE_CUTOFF=pd.Timestamp("2024-01-01 00:00")
END=pd.Timestamp("2026-01-01 00:00")
ALIASES={
    "BTC":["BTCUSD","BTCUSD.","BTCUSDm"],
    "ETH":["ETHUSD","ETHUSD.","ETHUSDm"],
    "DOG":["DOGUSD","DOGEUSD","DOGUSD.","DOGEUSD.","DOGUSDm","DOGEUSDm"]
}

def jd(p,o): p.write_text(json.dumps(o,indent=2,default=str),encoding="utf-8")

def mt5dt(x):
    t=pd.Timestamp(x)
    if t.tzinfo is None:t=t.tz_localize("UTC")
    else:t=t.tz_convert("UTC")
    return t.to_pydatetime()

def resolve_aliases():
    syms=list(mt5.symbols_get() or [])
    names=[s.name for s in syms]
    upper={n.upper():n for n in names}
    out={}
    for key,cands in ALIASES.items():
        found=None
        for c in cands:
            if c.upper() in upper:
                found=upper[c.upper()];break
        if found is None:
            # conservative prefix/contains fallback
            target="DOG" if key=="DOG" else key
            pool=[]
            for n in names:
                u=n.upper()
                if key=="DOG":
                    if ("DOGE" in u or "DOGUSD" in u) and "USD" in u: pool.append(n)
                else:
                    if u.startswith(key+"USD"): pool.append(n)
            if pool: found=sorted(pool,key=len)[0]
        if found:
            mt5.symbol_select(found,True)
        out[key]=found
    return out

def rates(sym,tf,a,b):
    a=pd.Timestamp(a);b=min(pd.Timestamp(b),END-pd.Timedelta(seconds=1))
    if a>=END:raise RuntimeError("2026 market access blocked")
    arr=mt5.copy_rates_range(sym,tf,mt5dt(a),mt5dt(b))
    if arr is None or len(arr)==0:return pd.DataFrame()
    d=pd.DataFrame(arr)
    d["time"]=pd.to_datetime(d["time"],unit="s",utc=True).dt.tz_localize(None)
    return d.sort_values("time").drop_duplicates("time")

def ticks(sym,a,b):
    a=pd.Timestamp(a);b=min(pd.Timestamp(b),END-pd.Timedelta(milliseconds=1))
    if a>=END:raise RuntimeError("2026 tick access blocked")
    arr=mt5.copy_ticks_range(sym,mt5dt(a),mt5dt(b),mt5.COPY_TICKS_ALL)
    if arr is None or len(arr)==0:return pd.DataFrame()
    d=pd.DataFrame(arr)
    d["time"]=pd.to_datetime(d["time_msc"],unit="ms",utc=True).dt.tz_localize(None)
    return d[(d["bid"]>0)&(d["ask"]>0)].sort_values("time")

def first_exec(sym,t,point):
    t=pd.Timestamp(t)
    if t>=END:raise RuntimeError("2026 execution access blocked")
    q=ticks(sym,t,t+pd.Timedelta(seconds=120))
    if not q.empty:
        r=q.iloc[0]
        return pd.Timestamp(r["time"]),float(r["bid"]),float(r["ask"]),"tick"
    m=rates(sym,mt5.TIMEFRAME_M1,t,t+pd.Timedelta(minutes=3))
    if not m.empty:
        r=m.iloc[0]
        bid=float(r["open"]);ask=bid+float(r["spread"])*point
        return pd.Timestamp(r["time"]),bid,ask,"m1_fallback"
    return None

def build_signal_frame(h):
    d=h.copy().reset_index(drop=True)
    body=(d["close"]-d["open"]).abs()
    rng=(d["high"]-d["low"]).abs()
    body_long_avg=body.rolling(10,min_periods=10).mean().shift(1)
    body_doji_avg=(rng.rolling(10,min_periods=10).mean().shift(1))*0.1
    prev_bear=d["close"].shift(1)<d["open"].shift(1)
    prev_long=body.shift(1)>body_long_avg.shift(1)
    doji=body<=body_doji_avg
    curr_top=pd.concat([d["open"],d["close"]],axis=1).max(axis=1)
    prev_bottom=pd.concat([d["open"].shift(1),d["close"].shift(1)],axis=1).min(axis=1)
    gap_down=curr_top<prev_bottom

    ma=d["close"].rolling(144,min_periods=144).mean()
    falling=pd.Series(True,index=d.index)
    for k in range(6,0,-1):
        falling &= ma.shift(k)>ma.shift(k-1)

    ret=d["close"].pct_change()
    sigma24=ret.rolling(24,min_periods=24).std(ddof=1)
    sig=prev_bear&prev_long&doji&gap_down&falling
    d["signal"]=sig.fillna(False)
    d["sigma24"]=sigma24
    d["risk_frac"]=2.0*sigma24
    d["signal_time"]=d["time"]+pd.Timedelta(hours=1)
    return d

def talib_parity(d):
    try:
        import talib
    except Exception:
        return {"talib_available":False}
    vals=talib.CDLDOJISTAR(d["open"].to_numpy(float),d["high"].to_numpy(float),d["low"].to_numpy(float),d["close"].to_numpy(float))
    raw=pd.Series(vals>0,index=d.index)
    ma=d["close"].rolling(144,min_periods=144).mean()
    falling=pd.Series(True,index=d.index)
    for k in range(6,0,-1):
        falling &= ma.shift(k)>ma.shift(k-1)
    ref=(raw&falling).fillna(False)
    ours=d["signal"].astype(bool)
    mismatch=int((ref!=ours).sum())
    positives=int(ref.sum())
    ours_n=int(ours.sum())
    return {"talib_available":True,"talib_positive_with_trend":positives,"manual_positive_with_trend":ours_n,"mismatch_count":mismatch}

def trim_best(x,pct):
    x=np.asarray(x,float);x=x[np.isfinite(x)]
    if not len(x):return np.nan
    k=int(math.ceil(len(x)*pct))
    if k<=0:return float(x.mean())
    if k>=len(x):return np.nan
    return float(np.sort(x)[:-k].mean())

def summarize(E,mask=None):
    z=E.copy() if mask is None else E.loc[mask].copy()
    z=z[z["execution_available"]==True]
    x=z["exec_bp"].to_numpy(float)
    r=z["exec_R"].to_numpy(float)
    out={
        "n_signals":int(len(E if mask is None else E.loc[mask])),
        "n_executable":int(len(z)),
        "coverage":float(len(z)/max(1,len(E if mask is None else E.loc[mask]))),
        "mean_exec_bp":float(np.mean(x)) if len(x) else np.nan,
        "median_exec_bp":float(np.median(x)) if len(x) else np.nan,
        "win_rate":float((x>0).mean()) if len(x) else np.nan,
        "mean_exec_R":float(np.nanmean(r)) if len(r) else np.nan,
        "trim1_bp":trim_best(x,.01),"trim2_bp":trim_best(x,.02),"trim5_bp":trim_best(x,.05)
    }
    return out

def current_meta(sym):
    i=mt5.symbol_info(sym)
    keys=["name","point","digits","spread","swap_mode","swap_long","swap_short","swap_rollover3days","trade_contract_size","trade_tick_size","trade_tick_value"]
    return {k:getattr(i,k,None) for k in keys}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)

    if not mt5.initialize():raise RuntimeError("MT5 init failed "+str(mt5.last_error()))
    try:
        ai=mt5.account_info()
        ident=" ".join(str(x or "") for x in [getattr(ai,"server",""),getattr(ai,"company",""),getattr(ai,"name","")])
        if "ftmo" not in ident.lower():raise RuntimeError(f"FTMO guard failed: {ident}")
        resolved=resolve_aliases()
        print("RESOLVED:",resolved,flush=True)

        all_events=[]
        parity={}
        metadata={}
        missing=[]
        for key,sym in resolved.items():
            if not sym:
                missing.append(key);continue
            h=rates(sym,mt5.TIMEFRAME_H1,START,END)
            if h.empty:
                missing.append(key);continue
            d=build_signal_frame(h)
            parity[key]=talib_parity(d)
            if parity[key].get("talib_available") and parity[key].get("mismatch_count",0)>0:
                raise RuntimeError(f"Manual/TA-Lib signal mismatch for {key}: {parity[key]}")
            metadata[key]=current_meta(sym)
            sig=d[d["signal"]].copy()
            # require +24h endpoint strictly before 2026
            sig=sig[(sig["signal_time"]>=pd.Timestamp("2018-07-01"))&((sig["signal_time"]+pd.Timedelta(hours=24))<END)]
            point=float(mt5.symbol_info(sym).point)
            print(f"{key} {sym}: signals={len(sig)}",flush=True)
            for _,r in sig.iterrows():
                st=pd.Timestamp(r["signal_time"]);xt=st+pd.Timedelta(hours=24)
                en=first_exec(sym,st,point);ex=first_exec(sym,xt,point)
                rec={
                    "asset":key,"symbol":sym,"bar_time":pd.Timestamp(r["time"]),"signal_time":st,"exit_target":xt,
                    "open":float(r["open"]),"high":float(r["high"]),"low":float(r["low"]),"close":float(r["close"]),
                    "risk_frac":float(r["risk_frac"]) if np.isfinite(r["risk_frac"]) else np.nan,
                    "execution_available":False,"entry_time":pd.NaT,"exit_time":pd.NaT,
                    "entry_bid":np.nan,"entry_ask":np.nan,"exit_bid":np.nan,"exit_ask":np.nan,
                    "entry_spread_bp":np.nan,"exit_spread_bp":np.nan,"exec_bp":np.nan,"exec_R":np.nan,
                    "entry_source":None,"exit_source":None
                }
                if en is not None and ex is not None:
                    et,eb,ea,es=en;xx,xb,xa,xs=ex
                    ret=(xb/ea-1.0)
                    risk=float(r["risk_frac"]) if np.isfinite(r["risk_frac"]) and r["risk_frac"]>0 else np.nan
                    rec.update({
                        "execution_available":True,"entry_time":et,"exit_time":xx,
                        "entry_bid":eb,"entry_ask":ea,"exit_bid":xb,"exit_ask":xa,
                        "entry_spread_bp":(ea-eb)/eb*1e4,"exit_spread_bp":(xa-xb)/xb*1e4,
                        "exec_bp":ret*1e4,"exec_R":ret/risk if np.isfinite(risk) and risk>0 else np.nan,
                        "entry_source":es,"exit_source":xs
                    })
                all_events.append(rec)

        E=pd.DataFrame(all_events)
        if not E.empty:
            E=E.sort_values(["signal_time","asset"]).reset_index(drop=True)
        E.to_csv(out/"D032_FTMO_EVENTS.csv",index=False)

        if E.empty:
            summary={"status":"NO_SIGNALS","resolved_symbols":resolved,"missing_core":missing,"talib_parity":parity,"metadata":metadata,"2026_accessed":False}
        else:
            pre=E["exit_target"]<PRE_CUTOFF
            post=(E["signal_time"]>=PRE_CUTOFF)&(E["exit_target"]<END)
            by_asset={}
            for asset,g in E.groupby("asset"):
                by_asset[asset]={"all":summarize(g),"pre2024":summarize(g,g["exit_target"]<PRE_CUTOFF),
                                 "post2024_2025":summarize(g,(g["signal_time"]>=PRE_CUTOFF)&(g["exit_target"]<END))}
            yrs={}
            z=E[E["execution_available"]==True].copy()
            if len(z):
                z["year"]=pd.to_datetime(z["signal_time"]).dt.year
                for y,g in z.groupby("year"):
                    yrs[str(int(y))]={"n":int(len(g)),"mean_exec_bp":float(g["exec_bp"].mean()),"mean_exec_R":float(g["exec_R"].mean())}
            summary={
                "status":"COMPLETE",
                "resolved_symbols":resolved,"missing_core":missing,"talib_parity":parity,
                "pooled":{"all":summarize(E),"pre2024":summarize(E,pre),"post2024_2025":summarize(E,post)},
                "by_asset":by_asset,"yearly":yrs,"current_ftmo_symbol_metadata":metadata,
                "interpretation_note":"Feed/execution transport only; D032 pattern/trend/horizon remained frozen. Current metadata is not historical swap/commission.",
                "2026_accessed":False
            }
            vals=E.loc[E["execution_available"]==True,"exec_bp"].to_numpy(float)
            grid=[]
            for c in [0,5,10,20,30,40,50,75,100]:
                y=vals-c
                grid.append({"extra_round_trip_cost_bp":c,"n":int(len(y)),"mean_net_bp":float(y.mean()) if len(y) else np.nan,"win_rate":float((y>0).mean()) if len(y) else np.nan})
            pd.DataFrame(grid).to_csv(out/"D032_EXTRA_COST_GRID.csv",index=False)

        jd(out/"SUMMARY.json",summary)
        (out/"SUCCESS.flag").write_text("OK\n2026_ACCESS=false\n",encoding="utf-8")
        print(json.dumps(summary,indent=2),flush=True)
        print("=== D032 FTMO TRANSPORT COMPLETE ===",flush=True)
    finally:
        mt5.shutdown()

if __name__=="__main__":
    try:main()
    except Exception as e:
        print("FAILED:",e,flush=True);traceback.print_exc();raise
