from pathlib import Path
import argparse, json, traceback, math
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

ROOT_DEFAULT=Path(r"D:\MT5_Backtests")
CAP=pd.Timestamp("2026-01-01 00:00")
OFFSET_H=2
EXPECTED_N=556
EXPECTED_MEAN_BP=1.4552352492311669

def jdump(p,o):
    p.write_text(json.dumps(o,indent=2,default=str),encoding="utf-8")

def mt5dt(x):
    t=pd.Timestamp(x)
    if t.tzinfo is None:
        t=t.tz_localize("UTC")
    else:
        t=t.tz_convert("UTC")
    return t.to_pydatetime()

def load_hist(root):
    parts=[]
    for y in [2023,2024,2025]:
        p=root/"DataLake"/"raw"/"histdata"/"AUDUSD"/"M1"/f"AUDUSD_M1_{y}.parquet"
        if not p.exists():
            raise RuntimeError(f"Missing {p}")
        d=pd.read_parquet(p)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        pc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None and isinstance(d.index,pd.DatetimeIndex):
            d=d.reset_index(); dc=d.columns[0]
        if dc is None or pc is None:
            raise RuntimeError(f"Bad schema {p}")
        dt=pd.to_datetime(d[dc],errors="coerce")
        if (dt.dt.year>=2026).any():
            raise RuntimeError(f"2026 contamination {p}")
        q=pd.DataFrame({"dt":dt,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
        q=q[q["dt"].dt.year==y]
        parts.append(q)
    return pd.concat(parts,ignore_index=True).sort_values("dt").drop_duplicates("dt",keep="last")

def build_events(root):
    d=load_hist(root)
    pseudo=pd.to_datetime(d["dt"])+pd.Timedelta(hours=5)
    s=pd.Series(pd.to_numeric(d["px"]).to_numpy(),index=pseudo).sort_index()
    s=s[~s.index.duplicated(keep="last")]
    s=s.resample("5min",label="right",closed="left").last().dropna()
    s=s[(s.index>=pd.Timestamp("2023-01-01"))&(s.index<CAP)]
    base=s.index[(s.index.minute==0)&(s.index.hour==21)]
    exits=base+pd.Timedelta(minutes=120)
    a=s.reindex(base).to_numpy(float)
    b=s.reindex(exits).to_numpy(float)
    ok=np.isfinite(a)&np.isfinite(b)&(a!=0)
    E=pd.DataFrame({
        "source_entry_label":base[ok],
        "source_exit_label":exits[ok],
        "source_entry_px":a[ok],
        "source_exit_px":b[ok],
        "source_return":-(b[ok]/a[ok]-1.0),
    })
    mean_bp=float(E["source_return"].mean()*1e4)
    if len(E)!=EXPECTED_N or abs(mean_bp-EXPECTED_MEAN_BP)>1e-9:
        raise RuntimeError(f"Source parity failed n={len(E)} mean_bp={mean_bp}")
    return E

def resolve(base):
    if mt5.symbol_info(base):
        mt5.symbol_select(base,True)
        return base
    cand=[]
    for s in mt5.symbols_get() or []:
        u=s.name.upper(); b=base.upper()
        if u==b: cand.append((0,len(s.name),s.name))
        elif u.startswith(b): cand.append((1,len(s.name),s.name))
        elif b in u: cand.append((2,len(s.name),s.name))
    if not cand:
        raise RuntimeError(f"Could not resolve {base}")
    cand.sort()
    mt5.symbol_select(cand[0][2],True)
    return cand[0][2]

def ticks(symbol,a,b):
    a=pd.Timestamp(a); b=min(pd.Timestamp(b),CAP-pd.Timedelta(milliseconds=1))
    if a>=CAP:
        raise RuntimeError("2026 tick access blocked")
    arr=mt5.copy_ticks_range(symbol,mt5dt(a),mt5dt(b),mt5.COPY_TICKS_ALL)
    if arr is None or len(arr)==0:
        return pd.DataFrame()
    d=pd.DataFrame(arr)
    d["time"]=pd.to_datetime(d["time_msc"],unit="ms",utc=True).dt.tz_localize(None)
    return d[(d["bid"]>0)&(d["ask"]>0)].sort_values("time")

def rates(symbol,a,b):
    a=pd.Timestamp(a); b=min(pd.Timestamp(b),CAP-pd.Timedelta(seconds=1))
    if a>=CAP:
        raise RuntimeError("2026 M1 access blocked")
    arr=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M1,mt5dt(a),mt5dt(b))
    if arr is None or len(arr)==0:
        return pd.DataFrame()
    d=pd.DataFrame(arr)
    d["time"]=pd.to_datetime(d["time"],unit="s",utc=True).dt.tz_localize(None)
    return d.sort_values("time")

def first_exec_at_or_after(symbol,t,point,max_seconds=90):
    t=pd.Timestamp(t)
    q=ticks(symbol,t,t+pd.Timedelta(seconds=max_seconds))
    if not q.empty:
        r=q.iloc[0]
        return pd.Timestamp(r["time"]),float(r["bid"]),float(r["ask"]),"tick"
    m=rates(symbol,t,t+pd.Timedelta(minutes=2))
    if not m.empty:
        r=m.iloc[0]
        bid=float(r["open"]); ask=bid+float(r["spread"])*point
        return pd.Timestamp(r["time"]),bid,ask,"m1_fallback"
    return None

def last_exec_before(symbol,t,point):
    t=pd.Timestamp(t)
    start=t-pd.Timedelta(minutes=1)
    q=ticks(symbol,start,t-pd.Timedelta(milliseconds=1))
    if not q.empty:
        r=q.iloc[-1]
        return pd.Timestamp(r["time"]),float(r["bid"]),float(r["ask"]),"tick"
    m=rates(symbol,start,t)
    if not m.empty:
        r=m.iloc[-1]
        bid=float(r["close"]); ask=bid+float(r["spread"])*point
        return pd.Timestamp(r["time"])+pd.Timedelta(seconds=59),bid,ask,"m1_fallback"
    return None

def audit(E,symbol,mode):
    info=mt5.symbol_info(symbol); point=float(info.point)
    rows=[]
    for _,r in E.iterrows():
        entry_boundary=pd.Timestamp(r["source_entry_label"])+pd.Timedelta(hours=OFFSET_H)
        exit_boundary=pd.Timestamp(r["source_exit_label"])+pd.Timedelta(hours=OFFSET_H)
        if mode=="first_after":
            en=first_exec_at_or_after(symbol,entry_boundary,point)
            ex=first_exec_at_or_after(symbol,exit_boundary,point)
        else:
            en=last_exec_before(symbol,entry_boundary,point)
            ex=last_exec_before(symbol,exit_boundary,point)

        base={
            **r.to_dict(),
            "mode":mode,
            "mapped_entry_boundary":entry_boundary,
            "mapped_exit_boundary":exit_boundary,
            "execution_available":False,
            "entry_time":pd.NaT,"exit_time":pd.NaT,
            "entry_bid":np.nan,"entry_ask":np.nan,"exit_bid":np.nan,"exit_ask":np.nan,
            "entry_spread_bp":np.nan,"exit_spread_bp":np.nan,
            "bid_gross_bp":np.nan,"exec_bp":np.nan,
            "entry_source":None,"exit_source":None,
        }
        if en is None or ex is None:
            rows.append(base); continue
        et,eb,ea,es=en; xt,xb,xa,xs=ex
        bid_gross=-(xb/eb-1.0)*1e4
        exec_bp=((eb-xa)/eb)*1e4
        base.update({
            "execution_available":True,
            "entry_time":et,"exit_time":xt,
            "entry_bid":eb,"entry_ask":ea,"exit_bid":xb,"exit_ask":xa,
            "entry_spread_bp":(ea-eb)/eb*1e4,
            "exit_spread_bp":(xa-xb)/xb*1e4,
            "bid_gross_bp":bid_gross,
            "exec_bp":exec_bp,
            "entry_source":es,"exit_source":xs,
        })
        rows.append(base)
    return pd.DataFrame(rows)

def summarize(X):
    z=X[X["execution_available"]==True].copy()
    src=z["source_return"].to_numpy(float)*1e4
    gross=pd.to_numeric(z["bid_gross_bp"],errors="coerce").to_numpy(float)
    exe=pd.to_numeric(z["exec_bp"],errors="coerce").to_numpy(float)
    corr=float(np.corrcoef(src,gross)[0,1]) if len(z)>2 else np.nan
    byyr={}
    years=pd.to_datetime(z["source_entry_label"]).dt.year
    for y,g in z.assign(_year=years).groupby("_year"):
        a=pd.to_numeric(g["exec_bp"],errors="coerce").dropna().to_numpy(float)
        byyr[str(int(y))]={"n":int(len(a)),"mean_exec_bp":float(a.mean()) if len(a) else np.nan}
    return {
        "source_events":int(len(X)),
        "execution_events":int(len(z)),
        "coverage":float(len(z)/len(X)) if len(X) else 0,
        "source_mean_bp_on_exec_sample":float(src.mean()) if len(src) else np.nan,
        "bid_gross_mean_bp":float(gross.mean()) if len(gross) else np.nan,
        "source_vs_bid_gross_corr":corr,
        "mean_entry_spread_bp":float(z["entry_spread_bp"].mean()) if len(z) else np.nan,
        "mean_exit_spread_bp":float(z["exit_spread_bp"].mean()) if len(z) else np.nan,
        "mean_exec_bp":float(exe.mean()) if len(exe) else np.nan,
        "median_exec_bp":float(np.median(exe)) if len(exe) else np.nan,
        "win_rate":float((exe>0).mean()) if len(exe) else np.nan,
        "years":byyr,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(ROOT_DEFAULT))
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    root=Path(a.root); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)

    E=build_events(root)
    print("SOURCE PARITY PASS: V112 n=556 mean=+1.4552352492311669 bp",flush=True)

    if not mt5.initialize():
        raise RuntimeError("MT5 init failed "+str(mt5.last_error()))
    try:
        ai=mt5.account_info()
        ident=" ".join(str(x or "") for x in [getattr(ai,"server",""),getattr(ai,"company",""),getattr(ai,"name","")])
        if "ftmo" not in ident.lower():
            raise RuntimeError(f"FTMO guard failed: {ident}")
        sym=resolve("AUDUSD")

        before=audit(E,sym,"last_before")
        after=audit(E,sym,"first_after")
        before.to_csv(out/"V112_LAST_BEFORE_BASELINE.csv",index=False)
        after.to_csv(out/"V112_FIRST_AFTER_BOUNDARY.csv",index=False)

        result={
            "source_parity":{"n":EXPECTED_N,"mean_bp":EXPECTED_MEAN_BP},
            "alignment_offset_hours":OFFSET_H,
            "selection_rule":"No PnL timing selection. Compare only the frozen mapped boundary under last-before versus causally executable first-at-or-after convention.",
            "last_before":summarize(before),
            "first_after":summarize(after),
            "ftmo_identity":ident,
            "2026_accessed":False,
        }
        jdump(out/"SUMMARY.json",result)
        (out/"SUCCESS.flag").write_text("OK\n2026_ACCESS=false\n",encoding="utf-8")
        print("LAST_BEFORE:",json.dumps(result["last_before"],indent=2),flush=True)
        print("FIRST_AFTER:",json.dumps(result["first_after"],indent=2),flush=True)
        print("=== V112 BOUNDARY EXECUTION FORENSIC COMPLETE ===",flush=True)
    finally:
        mt5.shutdown()

if __name__=="__main__":
    try:
        main()
    except Exception as e:
        print("FAILED:",e,flush=True)
        traceback.print_exc()
        raise
