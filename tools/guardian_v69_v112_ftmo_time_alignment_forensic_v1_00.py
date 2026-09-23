from pathlib import Path
import argparse, json, math, traceback
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

ROOT_DEFAULT=Path(r"D:\MT5_Backtests")
CAP=pd.Timestamp("2026-01-01 00:00:00")
OFFSETS=list(range(-8,9))

def outjson(p,o): p.write_text(json.dumps(o,indent=2,default=str),encoding="utf-8")
def mt5dt(x):
    t=pd.Timestamp(x)
    if t.tzinfo is None:t=t.tz_localize("UTC")
    else:t=t.tz_convert("UTC")
    return t.to_pydatetime()

def load_hist(root,sym):
    parts=[]
    for y in [2023,2024,2025]:
        p=root/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
        d=pd.read_parquet(p)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        pc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None and isinstance(d.index,pd.DatetimeIndex):
            d=d.reset_index();dc=d.columns[0]
        dt=pd.to_datetime(d[dc],errors="coerce")
        if (dt.dt.year>=2026).any(): raise RuntimeError(f"2026 contamination: {p}")
        q=pd.DataFrame({"dt":dt,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
        q=q[q.dt.dt.year==y];parts.append(q)
    return pd.concat(parts,ignore_index=True).sort_values("dt").drop_duplicates("dt",keep="last")

def events_v69(root):
    d=load_hist(root,"USDCHF")
    q=d.set_index("dt").px.resample("1D").last().dropna().to_frame("px")
    q["next_day"]=pd.Series(q.index,index=q.index).shift(-1)
    q["ret"]=q.px.shift(-1)/q.px-1
    q=q.dropna()
    q=q[q.index.dayofweek==4]
    dd=d.copy();dd["day"]=dd.dt.dt.floor("D")
    last=dd.sort_values("dt").groupby("day").tail(1).set_index("day")
    rows=[]
    for day,r in q.iterrows():
        nxt=pd.Timestamp(r.next_day)
        if day in last.index and nxt in last.index:
            e=last.loc[day];x=last.loc[nxt]
            rows.append({"source_entry_time":pd.Timestamp(e["dt"]),"source_exit_time":pd.Timestamp(x["dt"]),
                         "source_entry_px":float(e.px),"source_exit_px":float(x.px),
                         "source_return":float(x.px/e.px-1)})
    E=pd.DataFrame(rows)
    if len(E)!=155 or abs(E.source_return.mean()*1e4-4.639075481195655)>1e-9:
        raise RuntimeError("V69 exact source parity failed")
    return E

def events_v112(root):
    d=load_hist(root,"AUDUSD")
    pseudo=pd.to_datetime(d.dt)+pd.Timedelta(hours=5)
    s=pd.Series(pd.to_numeric(d.px).to_numpy(),index=pseudo).sort_index()
    s=s[~s.index.duplicated(keep="last")]
    s=s.resample("5min",label="right",closed="left").last().dropna()
    s=s[(s.index>=pd.Timestamp("2023-01-01"))&(s.index<CAP)]
    base=s.index[(s.index.minute==0)&(s.index.hour==21)]
    exits=base+pd.Timedelta(minutes=120)
    a=s.reindex(base).to_numpy(float);b=s.reindex(exits).to_numpy(float)
    ok=np.isfinite(a)&np.isfinite(b)&(a!=0)
    E=pd.DataFrame({"source_entry_label":base[ok],"source_exit_label":exits[ok],
                    "source_entry_px":a[ok],"source_exit_px":b[ok],
                    "source_return":-(b[ok]/a[ok]-1)})
    if len(E)!=556 or abs(E.source_return.mean()*1e4-1.4552352492311669)>1e-9:
        raise RuntimeError("V112 exact source parity failed")
    return E

def resolve(base):
    if mt5.symbol_info(base): mt5.symbol_select(base,True);return base
    c=[]
    for s in mt5.symbols_get() or []:
        u=s.name.upper();b=base.upper()
        if u==b:c.append((0,len(s.name),s.name))
        elif u.startswith(b):c.append((1,len(s.name),s.name))
        elif b in u:c.append((2,len(s.name),s.name))
    if not c:raise RuntimeError(f"symbol missing {base}")
    c.sort();mt5.symbol_select(c[0][2],True);return c[0][2]

def m1_window(symbol,center):
    a=pd.Timestamp(center)-pd.Timedelta(hours=9)
    b=pd.Timestamp(center)+pd.Timedelta(hours=9)
    if a>=CAP:raise RuntimeError("2026 access blocked")
    b=min(b,CAP-pd.Timedelta(seconds=1))
    x=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M1,mt5dt(a),mt5dt(b))
    if x is None or len(x)==0:return pd.DataFrame()
    d=pd.DataFrame(x);d["time"]=pd.to_datetime(d.time,unit="s",utc=True).dt.tz_localize(None)
    return d.set_index("time").sort_index()

def px_at_close(d,t):
    # Source values are M1 closes. Use exact minute close if available.
    t=pd.Timestamp(t).floor("min")
    if t in d.index:return float(d.loc[t].close)
    return np.nan

def scan_alignment(E,symbol,kind):
    rows=[]
    cache={}
    for _,r in E.iterrows():
        if kind=="V69":
            e0=r.source_entry_time;x0=r.source_exit_time
            source_e=float(r.source_entry_px);source_x=float(r.source_exit_px)
            # source timestamps are themselves M1 close timestamps
            e_adjust=0;x_adjust=0
        else:
            e0=r.source_entry_label;x0=r.source_exit_label
            source_e=float(r.source_entry_px);source_x=float(r.source_exit_px)
            # right-labelled 5m bar at H21 uses final M1 close at H20:59
            e_adjust=-1;x_adjust=-1

        keye=str(pd.Timestamp(e0).date())+"E"+str(_)
        keyx=str(pd.Timestamp(x0).date())+"X"+str(_)
        de=m1_window(symbol,e0);dx=m1_window(symbol,x0)

        rec={"source_entry_px":source_e,"source_exit_px":source_x,
             "source_return":float(r.source_return)}
        if kind=="V69":
            rec["source_entry_time"]=e0;rec["source_exit_time"]=x0
        else:
            rec["source_entry_label"]=e0;rec["source_exit_label"]=x0

        for off in OFFSETS:
            et=pd.Timestamp(e0)+pd.Timedelta(hours=off)+pd.Timedelta(minutes=e_adjust)
            xt=pd.Timestamp(x0)+pd.Timedelta(hours=off)+pd.Timedelta(minutes=x_adjust)
            ep=px_at_close(de,et);xp=px_at_close(dx,xt)
            rec[f"e_{off:+d}"]=ep;rec[f"x_{off:+d}"]=xp
        rows.append(rec)
    D=pd.DataFrame(rows)

    stats=[]
    for off in OFFSETS:
        ep=pd.to_numeric(D[f"e_{off:+d}"],errors="coerce")
        xp=pd.to_numeric(D[f"x_{off:+d}"],errors="coerce")
        ok=ep.notna()&xp.notna()
        if not ok.any():
            stats.append({"offset_hours":off,"coverage":0,"n":0})
            continue
        src_e=D.loc[ok,"source_entry_px"].to_numpy(float)
        src_x=D.loc[ok,"source_exit_px"].to_numpy(float)
        fe=ep[ok].to_numpy(float);fx=xp[ok].to_numpy(float)
        entry_abs=np.abs((fe/src_e-1)*1e4)
        exit_abs=np.abs((fx/src_x-1)*1e4)
        src_ret=D.loc[ok,"source_return"].to_numpy(float)
        if kind=="V69": ftmo_ret=fx/fe-1
        else: ftmo_ret=-(fx/fe-1)
        corr=float(np.corrcoef(src_ret,ftmo_ret)[0,1]) if len(ftmo_ret)>2 else np.nan
        stats.append({
            "offset_hours":off,"n":int(ok.sum()),"coverage":float(ok.mean()),
            "median_abs_entry_price_diff_bp":float(np.median(entry_abs)),
            "median_abs_exit_price_diff_bp":float(np.median(exit_abs)),
            "median_abs_two_leg_price_diff_bp":float(np.median(np.r_[entry_abs,exit_abs])),
            "mean_ftmo_bid_return_bp":float(np.mean(ftmo_ret)*1e4),
            "source_vs_ftmo_return_corr":corr,
        })
    S=pd.DataFrame(stats)
    eligible=S[S.coverage>=0.90].copy()
    if eligible.empty: raise RuntimeError(f"{kind}: no offset has >=90% FTMO M1 coverage")
    # Selection criterion is ONLY source-vs-FTMO price proximity, never PnL.
    best=eligible.sort_values(["median_abs_two_leg_price_diff_bp","offset_hours"]).iloc[0].to_dict()
    return D,S,best

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=str(ROOT_DEFAULT));ap.add_argument("--out",required=True)
    a=ap.parse_args();root=Path(a.root);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    E69=events_v69(root);E112=events_v112(root)
    print("SOURCE PARITY PASS: V69 155 / V112 556",flush=True)

    if not mt5.initialize():raise RuntimeError("MT5 init failed "+str(mt5.last_error()))
    try:
        ai=mt5.account_info()
        ident=" ".join(str(x or "") for x in [getattr(ai,"server",""),getattr(ai,"company",""),getattr(ai,"name","")])
        if "ftmo" not in ident.lower():raise RuntimeError(f"FTMO guard failed: {ident}")
        chf=resolve("USDCHF");aud=resolve("AUDUSD")
        d69,s69,b69=scan_alignment(E69,chf,"V69")
        d112,s112,b112=scan_alignment(E112,aud,"V112")
        d69.to_csv(out/"V69_ALIGNMENT_EVENT_MATRIX.csv",index=False)
        s69.to_csv(out/"V69_ALIGNMENT_SCAN.csv",index=False)
        d112.to_csv(out/"V112_ALIGNMENT_EVENT_MATRIX.csv",index=False)
        s112.to_csv(out/"V112_ALIGNMENT_SCAN.csv",index=False)
        result={
            "selection_rule":"Choose offset with >=90% coverage and minimum median absolute two-leg source-vs-FTMO price difference. PnL is not used for alignment selection.",
            "V69_best_alignment":b69,
            "V112_best_alignment":b112,
            "2026_accessed":False,
            "ftmo_identity":ident,
        }
        outjson(out/"ALIGNMENT_VERDICT.json",result)
        print("V69 BEST:",b69,flush=True)
        print("V112 BEST:",b112,flush=True)
        print("=== ALIGNMENT FORENSIC COMPLETE ===",flush=True)
    finally:
        mt5.shutdown()

if __name__=="__main__":
    try:main()
    except Exception as e:
        print("FAILED:",e,flush=True);traceback.print_exc();raise
