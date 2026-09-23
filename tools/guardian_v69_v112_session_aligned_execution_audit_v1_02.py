from pathlib import Path
import argparse, json, math, traceback
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

ROOT_DEFAULT=Path(r"D:\MT5_Backtests")
CAP=pd.Timestamp("2026-01-01 00:00")
V112_CLOCK_OFFSET_H=2

def js(p,o): p.write_text(json.dumps(o,indent=2,default=str),encoding="utf-8")
def bpmean(a):
    a=np.asarray(a,float);a=a[np.isfinite(a)]
    return float(a.mean()*1e4) if len(a) else np.nan
def maxdd_bp_from_bp(a):
    a=np.asarray(a,float);a=a[np.isfinite(a)]
    if not len(a): return np.nan
    e=np.r_[0,np.cumsum(a)];pk=np.maximum.accumulate(e)
    return float((e-pk).min())
def mt5dt(x):
    t=pd.Timestamp(x)
    if t.tzinfo is None:t=t.tz_localize("UTC")
    else:t=t.tz_convert("UTC")
    return t.to_pydatetime()

def load_hist(root,sym):
    parts=[]
    for y in [2023,2024,2025]:
        p=root/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
        if not p.exists(): raise RuntimeError(f"Missing {p}")
        d=pd.read_parquet(p)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        pc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None and isinstance(d.index,pd.DatetimeIndex):
            d=d.reset_index();dc=d.columns[0]
        if dc is None or pc is None: raise RuntimeError(f"Bad schema {p}")
        dt=pd.to_datetime(d[dc],errors="coerce")
        if (dt.dt.year>=2026).any(): raise RuntimeError(f"2026 contamination {p}")
        q=pd.DataFrame({"dt":dt,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
        q=q[q["dt"].dt.year==y]
        parts.append(q)
    return pd.concat(parts,ignore_index=True).sort_values("dt").drop_duplicates("dt",keep="last")

def build_v69(root):
    d=load_hist(root,"USDCHF")
    q=d.set_index("dt")["px"].resample("1D").last().dropna().to_frame("px")
    q["next_day"]=pd.Series(q.index,index=q.index).shift(-1)
    q["ret"]=q["px"].shift(-1)/q["px"]-1
    q=q.dropna()
    q=q[q.index.dayofweek==4]
    dd=d.copy();dd["day"]=dd["dt"].dt.floor("D")
    last=dd.sort_values("dt").groupby("day").tail(1).set_index("day")
    rows=[]
    for day,r in q.iterrows():
        nxt=pd.Timestamp(r["next_day"])
        if day not in last.index or nxt not in last.index: continue
        e=last.loc[day];x=last.loc[nxt]
        et=pd.Timestamp(e["dt"]);xt=pd.Timestamp(x["dt"])
        after=d[(d["dt"]>et)&(d["dt"]<=xt)]
        if after.empty: continue
        reopen=pd.Timestamp(after.iloc[0]["dt"])
        rows.append({
            "source_entry_time":et,"source_reopen_time":reopen,"source_exit_time":xt,
            "source_entry_px":float(e["px"]),"source_exit_px":float(x["px"]),
            "source_return":float(x["px"]/e["px"]-1),
            "source_weekend_gap_hours":(reopen-et).total_seconds()/3600,
            "source_reopen_to_exit_minutes":(xt-reopen).total_seconds()/60,
        })
    E=pd.DataFrame(rows)
    if len(E)!=155 or abs(E["source_return"].mean()*1e4-4.639075481195655)>1e-9:
        raise RuntimeError("V69 source parity failed")
    return E

def build_v112(root):
    d=load_hist(root,"AUDUSD")
    pseudo=pd.to_datetime(d["dt"])+pd.Timedelta(hours=5)
    s=pd.Series(pd.to_numeric(d["px"]).to_numpy(),index=pseudo).sort_index()
    s=s[~s.index.duplicated(keep="last")]
    s=s.resample("5min",label="right",closed="left").last().dropna()
    s=s[(s.index>=pd.Timestamp("2023-01-01"))&(s.index<CAP)]
    base=s.index[(s.index.minute==0)&(s.index.hour==21)]
    ex=base+pd.Timedelta(minutes=120)
    a=s.reindex(base).to_numpy(float);b=s.reindex(ex).to_numpy(float)
    ok=np.isfinite(a)&np.isfinite(b)&(a!=0)
    E=pd.DataFrame({
        "source_entry_label":base[ok],"source_exit_label":ex[ok],
        "source_entry_px":a[ok],"source_exit_px":b[ok],
        "source_return":-(b[ok]/a[ok]-1)
    })
    if len(E)!=556 or abs(E["source_return"].mean()*1e4-1.4552352492311669)>1e-9:
        raise RuntimeError("V112 source parity failed")
    return E

def resolve(base):
    if mt5.symbol_info(base):
        mt5.symbol_select(base,True);return base
    c=[]
    for s in mt5.symbols_get() or []:
        u=s.name.upper();b=base.upper()
        if u==b:c.append((0,len(s.name),s.name))
        elif u.startswith(b):c.append((1,len(s.name),s.name))
        elif b in u:c.append((2,len(s.name),s.name))
    if not c: raise RuntimeError(f"Could not resolve {base}")
    c.sort();mt5.symbol_select(c[0][2],True);return c[0][2]

def rates(symbol,a,b):
    a=pd.Timestamp(a);b=min(pd.Timestamp(b),CAP-pd.Timedelta(seconds=1))
    if a>=CAP: raise RuntimeError("2026 access blocked")
    x=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M1,mt5dt(a),mt5dt(b))
    if x is None or len(x)==0:return pd.DataFrame()
    d=pd.DataFrame(x)
    d["time"]=pd.to_datetime(d["time"],unit="s",utc=True).dt.tz_localize(None)
    return d.sort_values("time").drop_duplicates("time")

def ticks(symbol,a,b):
    a=pd.Timestamp(a);b=min(pd.Timestamp(b),CAP-pd.Timedelta(milliseconds=1))
    if a>=CAP: raise RuntimeError("2026 access blocked")
    x=mt5.copy_ticks_range(symbol,mt5dt(a),mt5dt(b),mt5.COPY_TICKS_ALL)
    if x is None or len(x)==0:return pd.DataFrame()
    d=pd.DataFrame(x)
    d["time"]=pd.to_datetime(d["time_msc"],unit="ms",utc=True).dt.tz_localize(None)
    return d[(d["bid"]>0)&(d["ask"]>0)].sort_values("time")

def last_exec_in_minute(symbol,t,point):
    t=pd.Timestamp(t).floor("min")
    q=ticks(symbol,t,t+pd.Timedelta(seconds=59,milliseconds=999))
    if not q.empty:
        r=q.iloc[-1];return pd.Timestamp(r["time"]),float(r["bid"]),float(r["ask"]),"tick"
    m=rates(symbol,t,t+pd.Timedelta(minutes=1))
    if not m.empty:
        r=m.iloc[0];bid=float(r["close"]);ask=bid+float(r["spread"])*point
        return pd.Timestamp(r["time"])+pd.Timedelta(seconds=59),bid,ask,"m1_fallback"
    return None

def nearest_bar_time(d,target,tolerance_min=5):
    if d.empty:return None
    t=pd.Timestamp(target)
    delta=(d["time"]-t).abs()
    i=delta.idxmin()
    if delta.loc[i]>pd.Timedelta(minutes=tolerance_min):return None
    return pd.Timestamp(d.loc[i,"time"])

def find_weekend_gap(d):
    if len(d)<2:return None
    x=d.copy().sort_values("time").reset_index(drop=True)
    dif=x["time"].diff()
    cand=dif[dif>=pd.Timedelta(hours=24)]
    if cand.empty:return None
    i=cand.idxmax()
    if i<=0:return None
    return pd.Timestamp(x.loc[i-1,"time"]),pd.Timestamp(x.loc[i,"time"]),float(cand.loc[i].total_seconds()/3600)

def audit_v69(E,symbol):
    info=mt5.symbol_info(symbol);point=float(info.point);rows=[]
    for _,r in E.iterrows():
        # Broad same-week window; structural mapping uses the largest >=24h no-quote weekend gap.
        a=pd.Timestamp(r["source_entry_time"])-pd.Timedelta(hours=12)
        b=pd.Timestamp(r["source_exit_time"])+pd.Timedelta(hours=12)
        m=rates(symbol,a,b)
        gap=find_weekend_gap(m)
        base={**r.to_dict(),"execution_available":False,"mapping_error":"",
              "ftmo_entry_minute":pd.NaT,"ftmo_reopen_minute":pd.NaT,"ftmo_exit_minute":pd.NaT,
              "entry_bid":np.nan,"entry_ask":np.nan,"exit_bid":np.nan,"exit_ask":np.nan,
              "entry_spread_bp":np.nan,"exit_spread_bp":np.nan,"exec_return":np.nan,"exec_bp":np.nan,
              "entry_source":None,"exit_source":None,"ftmo_weekend_gap_hours":np.nan}
        if gap is None:
            base["mapping_error"]="weekend_gap_not_found";rows.append(base);continue
        fent,freopen,gaph=gap
        target_exit=freopen+pd.Timedelta(minutes=float(r["source_reopen_to_exit_minutes"]))
        fexit=nearest_bar_time(m,target_exit,5)
        if fexit is None:
            base.update({"ftmo_entry_minute":fent,"ftmo_reopen_minute":freopen,
                         "ftmo_weekend_gap_hours":gaph,"mapping_error":"exit_bar_not_found"})
            rows.append(base);continue
        en=last_exec_in_minute(symbol,fent,point);ex=last_exec_in_minute(symbol,fexit,point)
        if en is None or ex is None:
            base.update({"ftmo_entry_minute":fent,"ftmo_reopen_minute":freopen,"ftmo_exit_minute":fexit,
                         "ftmo_weekend_gap_hours":gaph,"mapping_error":"execution_quote_missing"})
            rows.append(base);continue
        et,eb,ea,es=en;xt,xb,xa,xs=ex
        ret=xb/ea-1
        base.update({
            "execution_available":True,"ftmo_entry_minute":fent,"ftmo_reopen_minute":freopen,
            "ftmo_exit_minute":fexit,"ftmo_weekend_gap_hours":gaph,
            "entry_bid":eb,"entry_ask":ea,"exit_bid":xb,"exit_ask":xa,
            "entry_spread_bp":(ea-eb)/eb*1e4,"exit_spread_bp":(xa-xb)/xb*1e4,
            "exec_return":ret,"exec_bp":ret*1e4,"entry_source":es,"exit_source":xs,
            "ftmo_hold_hours":(xt-et).total_seconds()/3600,
            "ftmo_reopen_to_exit_minutes":(fexit-freopen).total_seconds()/60,
        });rows.append(base)
    return pd.DataFrame(rows)

def audit_v112(E,symbol):
    info=mt5.symbol_info(symbol);point=float(info.point);rows=[]
    for _,r in E.iterrows():
        # Forensic alignment: source right-labelled H21/H23 -> final M1 close at :59,
        # then +2h into the FTMO clock. Offset was selected by source-price proximity only.
        ent=pd.Timestamp(r["source_entry_label"])+pd.Timedelta(hours=V112_CLOCK_OFFSET_H,minutes=-1)
        ext=pd.Timestamp(r["source_exit_label"])+pd.Timedelta(hours=V112_CLOCK_OFFSET_H,minutes=-1)
        base={**r.to_dict(),"execution_available":False,"ftmo_entry_minute":ent,"ftmo_exit_minute":ext,
              "entry_bid":np.nan,"entry_ask":np.nan,"exit_bid":np.nan,"exit_ask":np.nan,
              "entry_spread_bp":np.nan,"exit_spread_bp":np.nan,"exec_return":np.nan,"exec_bp":np.nan,
              "entry_source":None,"exit_source":None}
        en=last_exec_in_minute(symbol,ent,point);ex=last_exec_in_minute(symbol,ext,point)
        if en is None or ex is None:
            rows.append(base);continue
        et,eb,ea,es=en;xt,xb,xa,xs=ex
        ret=(eb-xa)/eb
        base.update({
            "execution_available":True,"entry_bid":eb,"entry_ask":ea,"exit_bid":xb,"exit_ask":xa,
            "entry_spread_bp":(ea-eb)/eb*1e4,"exit_spread_bp":(xa-xb)/xb*1e4,
            "exec_return":ret,"exec_bp":ret*1e4,"entry_source":es,"exit_source":xs,
            "ftmo_hold_hours":(xt-et).total_seconds()/3600,
        });rows.append(base)
    return pd.DataFrame(rows)

def summarize(X):
    z=X[X["execution_available"]==True].copy()
    bp=pd.to_numeric(z["exec_bp"],errors="coerce").dropna().to_numpy(float)
    byyr={}
    if len(z):
        tc="source_entry_time" if "source_entry_time" in z.columns else "source_entry_label"
        yr=pd.to_datetime(z[tc]).dt.year
        for y,g in z.assign(_yr=yr).groupby("_yr"):
            a=pd.to_numeric(g["exec_bp"],errors="coerce").dropna().to_numpy(float)
            byyr[str(int(y))]={"n":int(len(a)),"mean_bp":float(a.mean()) if len(a) else np.nan,
                              "win_rate":float((a>0).mean()) if len(a) else np.nan}
    return {
        "source_events":int(len(X)),"execution_events":int(len(bp)),
        "coverage":float(len(bp)/len(X)) if len(X) else 0,
        "mean_exec_bp":float(bp.mean()) if len(bp) else np.nan,
        "median_exec_bp":float(np.median(bp)) if len(bp) else np.nan,
        "win_rate":float((bp>0).mean()) if len(bp) else np.nan,
        "trim_best_1pct_bp":float(np.sort(bp)[:-max(1,int(math.ceil(len(bp)*.01)))].mean()) if len(bp)>2 else np.nan,
        "remove_best5_bp":float(np.sort(bp)[:-5].mean()) if len(bp)>5 else np.nan,
        "max_drawdown_cumsum_bp":maxdd_bp_from_bp(bp),
        "mean_entry_spread_bp":float(z["entry_spread_bp"].mean()) if len(z) else np.nan,
        "mean_exit_spread_bp":float(z["exit_spread_bp"].mean()) if len(z) else np.nan,
        "years":byyr
    }

def grid(X,name):
    z=X[X["execution_available"]==True]
    x=pd.to_numeric(z["exec_bp"],errors="coerce").dropna().to_numpy(float)
    rows=[]
    for c in [0,.25,.5,.75,1,1.5,2,2.5,3,4,5]:
        y=x-c
        rows.append({"strategy":name,"extra_cost_bp":c,"n":len(y),
                     "mean_net_bp":float(y.mean()) if len(y) else np.nan,
                     "win_rate":float((y>0).mean()) if len(y) else np.nan,
                     "max_drawdown_cumsum_bp":maxdd_bp_from_bp(y)})
    return pd.DataFrame(rows)

def meta(sym):
    i=mt5.symbol_info(sym)
    keys=["name","point","digits","spread","swap_mode","swap_long","swap_short","swap_rollover3days",
          "trade_contract_size","trade_tick_size","trade_tick_value"]
    return {k:getattr(i,k,None) for k in keys}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=str(ROOT_DEFAULT));ap.add_argument("--out",required=True)
    a=ap.parse_args();root=Path(a.root);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    e69=build_v69(root);e112=build_v112(root)
    print("SOURCE PARITY PASS: V69=155/+4.639075481195655bp; V112=556/+1.4552352492311669bp",flush=True)
    print("PANDAS ROW ACCESS: HARDENED v1.02",flush=True)
    print("V69 source exits:",pd.to_datetime(e69["source_exit_time"]).dt.day_name().value_counts().to_dict(),flush=True)
    print("V69 source reopen->exit minutes:",e69["source_reopen_to_exit_minutes"].value_counts().head(10).to_dict(),flush=True)
    if not mt5.initialize():raise RuntimeError("MT5 init failed "+str(mt5.last_error()))
    try:
        ai=mt5.account_info()
        ident=" ".join(str(x or "") for x in [getattr(ai,"server",""),getattr(ai,"company",""),getattr(ai,"name","")])
        if "ftmo" not in ident.lower():raise RuntimeError(f"FTMO guard failed {ident}")
        chf=resolve("USDCHF");aud=resolve("AUDUSD")
        x69=audit_v69(e69,chf);x112=audit_v112(e112,aud)
        x69.to_csv(out/"V69_SESSION_MAPPED_FTMO_LEDGER.csv",index=False)
        x112.to_csv(out/"V112_ALIGNED_FTMO_LEDGER.csv",index=False)
        grid(x69,"V69_USDCHF_WEEKEND").to_csv(out/"V69_EXTRA_COST_GRID.csv",index=False)
        grid(x112,"V112_AUDUSD_H21_SHORT_120M").to_csv(out/"V112_EXTRA_COST_GRID.csv",index=False)
        res={
            "source_parity":{"V69":{"n":155,"mean_bp":4.639075481195655},
                             "V112":{"n":556,"mean_bp":1.4552352492311669}},
            "V69":{"mapping":"FTMO last M1 before >=24h weekend gap -> same source minutes after first M1 after gap",
                   "source_exit_weekdays":pd.to_datetime(e69["source_exit_time"]).dt.day_name().value_counts().to_dict(),
                   "stats":summarize(x69),"current_ftmo_symbol_metadata":meta(chf),
                   "swap_note":"Historical swap/carry is not invented. Current symbol swap metadata is context only."},
            "V112":{"mapping":"source H21/H23 right-labelled 5m -> final M1 at :59 -> +2h FTMO clock, fixed from price-alignment forensic",
                    "alignment_evidence":{"coverage":0.9712230215827338,"median_two_leg_price_diff_bp":0.5789173054537855,
                                          "source_return_corr":0.9375998924507134,"bid_gross_bp":2.0336882221296855},
                    "stats":summarize(x112),"current_ftmo_symbol_metadata":meta(aud)},
            "ftmo_identity":ident,"2026_accessed":False
        }
        js(out/"SUMMARY.json",res)
        (out/"SUCCESS.flag").write_text("OK\n2026_ACCESS=false\n",encoding="utf-8")
        print("V69:",json.dumps(res["V69"]["stats"],indent=2,default=str),flush=True)
        print("V112:",json.dumps(res["V112"]["stats"],indent=2,default=str),flush=True)
        print("=== SESSION-ALIGNED EXECUTION AUDIT COMPLETE ===",flush=True)
    finally: mt5.shutdown()

if __name__=="__main__":
    try:main()
    except Exception as e:
        print("FAILED:",e,flush=True);traceback.print_exc();raise
