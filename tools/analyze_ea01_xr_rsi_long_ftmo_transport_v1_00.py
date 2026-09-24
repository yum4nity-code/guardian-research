from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json, math
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

VERSION="EA01-XR-RSI-LONG-V1-FTMO-TRANSPORT-1.0"
START=pd.Timestamp("2023-01-01 00:00:00", tz="UTC")
END=pd.Timestamp("2026-01-01 00:00:00", tz="UTC")
EXPECTED_SHA="35ab88bb139a9b8c23f0ad28287718af9c1906af1eae6cfe78087464a255c3ac"
EXPECTED_RAW_N=944
EXPECTED_NONOVERLAP_N=654
EXPECTED_RAW_MEAN=0.10856319491605436
EXPECTED_RAW_PF=1.1564669738705082
EXPECTED_C010_MEAN=0.06216246499009125
EXPECTED_C010_PF=1.0868273589119208
HOLD_MIN=60
OFFSETS=list(range(-4,5))
BOOT=20000
SEED=10120260924
METAL_COMMISSION_RATE_SIDE=0.000007

def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def pf(a):
    a=np.asarray(a,float);a=a[np.isfinite(a)]
    pos=a[a>0].sum();neg=-a[a<0].sum()
    return float(pos/neg) if neg>0 else (float("inf") if pos>0 else np.nan)

def trim_best(a,pct):
    a=np.asarray(a,float);a=a[np.isfinite(a)]
    if len(a)<2:return np.nan
    k=max(1,int(math.ceil(len(a)*pct)))
    return float(np.sort(a)[:-k].mean()) if k<len(a) else np.nan

def month_boot(times,vals):
    d=pd.DataFrame({"t":pd.to_datetime(times,utc=True),"x":np.asarray(vals,float)}).dropna()
    d["m"]=d["t"].dt.to_period("M").astype(str)
    groups=[g.x.to_numpy(float) for _,g in d.groupby("m") if len(g)]
    if len(groups)<2:return {}
    rng=np.random.default_rng(SEED);out=np.empty(BOOT,float)
    for i in range(BOOT):
        pick=rng.integers(0,len(groups),size=len(groups))
        out[i]=np.concatenate([groups[j] for j in pick]).mean()
    q=np.quantile(out,[.025,.10,.50,.90,.975])
    return {"q025":float(q[0]),"q10":float(q[1]),"q50":float(q[2]),"q90":float(q[3]),"q975":float(q[4]),"p_le_zero":float((out<=0).mean())}

def non_overlap(df):
    d=df.sort_values("entry_time_utc").copy()
    keep=[];last_exit=None
    for i,r in d.iterrows():
        t=r["entry_time_utc"]
        if last_exit is None or t>=last_exit:
            keep.append(i);last_exit=t+pd.Timedelta(minutes=HOLD_MIN)
    return d.loc[keep].copy().sort_values("entry_time_utc").reset_index(drop=True)

def mt5dt(t):
    p=pd.Timestamp(t)
    if p.tzinfo is None:p=p.tz_localize("UTC")
    else:p=p.tz_convert("UTC")
    return p.to_pydatetime()

def resolve_symbol(base):
    if mt5.symbol_info(base):
        mt5.symbol_select(base,True);return base
    c=[]
    for s in mt5.symbols_get() or []:
        u=s.name.upper();b=base.upper()
        if u==b:c.append((0,len(s.name),s.name))
        elif u.startswith(b):c.append((1,len(s.name),s.name))
        elif b in u:c.append((2,len(s.name),s.name))
    if not c:raise RuntimeError("Cannot resolve "+base)
    c.sort();sym=c[0][2];mt5.symbol_select(sym,True);return sym

def rates(sym,a,b):
    aa=pd.Timestamp(a);bb=pd.Timestamp(b)
    if aa.tzinfo is None:aa=aa.tz_localize("UTC")
    if bb.tzinfo is None:bb=bb.tz_localize("UTC")
    if bb>=END:bb=END-pd.Timedelta(seconds=1)
    if aa>=END:raise RuntimeError("2026 M1 access blocked")
    arr=mt5.copy_rates_range(sym,mt5.TIMEFRAME_M1,mt5dt(aa),mt5dt(bb))
    if arr is None or len(arr)==0:return pd.DataFrame()
    d=pd.DataFrame(arr);d["time"]=pd.to_datetime(d["time"],unit="s",utc=True)
    return d.sort_values("time").drop_duplicates("time")

def ticks(sym,a,b):
    aa=pd.Timestamp(a);bb=pd.Timestamp(b)
    if aa.tzinfo is None:aa=aa.tz_localize("UTC")
    if bb.tzinfo is None:bb=bb.tz_localize("UTC")
    if bb>=END:bb=END-pd.Timedelta(milliseconds=1)
    if aa>=END:raise RuntimeError("2026 tick access blocked")
    arr=mt5.copy_ticks_range(sym,mt5dt(aa),mt5dt(bb),mt5.COPY_TICKS_ALL)
    if arr is None or len(arr)==0:return pd.DataFrame()
    d=pd.DataFrame(arr);d["time"]=pd.to_datetime(d["time_msc"],unit="ms",utc=True)
    return d[(d.bid>0)&(d.ask>0)].sort_values("time")

def m1_open(d,t):
    if d.empty:return np.nan
    z=d[d.time==pd.Timestamp(t).floor("min")]
    return float(z.iloc[0].open) if len(z) else np.nan

def m1_close_before(d,t):
    if d.empty:return np.nan
    z=d[d.time==pd.Timestamp(t).floor("min")-pd.Timedelta(minutes=1)]
    return float(z.iloc[-1].close) if len(z) else np.nan

def first_tick(sym,t):
    q=ticks(sym,t,pd.Timestamp(t)+pd.Timedelta(seconds=90))
    if q.empty:return None
    r=q.iloc[0]
    return {"time":r.time,"bid":float(r.bid),"ask":float(r.ask)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=r"D:\MT5_Backtests")
    ap.add_argument("--out",required=True)
    a=ap.parse_args();root=Path(a.root);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)

    src=root/"Research"/"Autonomous"/"edge_atlas"/"EA01-XR-RSI-LONG-V1-OOS-2023-2025"/"signals.csv"
    if not src.exists():raise RuntimeError("Missing canonical ledger "+str(src))
    if sha256(src)!=EXPECTED_SHA:raise RuntimeError("EA01 canonical ledger SHA mismatch")
    d=pd.read_csv(src,low_memory=False)
    if len(d)!=EXPECTED_RAW_N:raise RuntimeError("Raw N mismatch "+str(len(d)))
    need=["entry_time","entry","risk","reversal_side","r_12","r_12_cost_0.10"]
    miss=[c for c in need if c not in d.columns]
    if miss:raise RuntimeError("Canonical ledger schema missing "+str(miss))
    d["entry_time_utc"]=pd.to_datetime(d["entry_time"],utc=True,errors="coerce")
    if d.entry_time_utc.isna().any():raise RuntimeError("Unparseable entry_time")
    if (d.entry_time_utc<START).any() or (d.entry_time_utc>=END).any():raise RuntimeError("Ledger outside 2023-2025 / 2026 blocked")
    for c in ["entry","risk","reversal_side","r_12","r_12_cost_0.10"]:
        d[c]=pd.to_numeric(d[c],errors="coerce")
    if d[need[1:]].isna().any().any():raise RuntimeError("NaN in required canonical fields")
    if not (d.reversal_side==1).all():raise RuntimeError("Candidate ledger is not LONG-only")

    no=non_overlap(d)
    if len(no)!=EXPECTED_NONOVERLAP_N:raise RuntimeError("Non-overlap mismatch "+str(len(no)))
    if abs(no.r_12.mean()-EXPECTED_RAW_MEAN)>5e-5 or abs(pf(no.r_12)-EXPECTED_RAW_PF)>5e-4:raise RuntimeError("Raw source parity fail")
    if abs(no["r_12_cost_0.10"].mean()-EXPECTED_C010_MEAN)>5e-5 or abs(pf(no["r_12_cost_0.10"])-EXPECTED_C010_PF)>5e-4:raise RuntimeError("Cost0.10 source parity fail")
    no["source_exit_time_utc"]=no.entry_time_utc+pd.Timedelta(minutes=HOLD_MIN)
    no["source_exit_px"]=no["entry"]+no["r_12"]*no["risk"]

    if not mt5.initialize():raise RuntimeError("MT5 init failed "+str(mt5.last_error()))
    try:
        ai=mt5.account_info()
        ident=" ".join(str(x or "") for x in [getattr(ai,"server",""),getattr(ai,"company",""),getattr(ai,"name","")])
        if "ftmo" not in ident.lower():raise RuntimeError("FTMO guard failed: "+ident)
        sym=resolve_symbol("XAUUSD")
        info=mt5.symbol_info(sym);contract=float(getattr(info,"trade_contract_size",0.0) or 0.0)
        if contract<=0:raise RuntimeError("Invalid XAU contract size")

        rows=[]
        for _,r in no.iterrows():
            e=r.entry_time_utc;x=r.source_exit_time_utc
            q=rates(sym,e-pd.Timedelta(hours=5),x+pd.Timedelta(hours=5))
            rec={"entry_time_utc":e,"exit_time_utc":x,"source_entry":float(r.entry),"source_exit":float(r.source_exit_px),"source_risk":float(r.risk),"source_r":float(r.r_12)}
            for off in OFFSETS:
                rec[f"e_{off:+d}"]=m1_open(q,e+pd.Timedelta(hours=off))
                rec[f"x_{off:+d}"]=m1_close_before(q,x+pd.Timedelta(hours=off))
            rows.append(rec)
        A=pd.DataFrame(rows)
        stats=[]
        for off in OFFSETS:
            ep=pd.to_numeric(A[f"e_{off:+d}"],errors="coerce");xp=pd.to_numeric(A[f"x_{off:+d}"],errors="coerce")
            ok=ep.notna()&xp.notna()
            if not ok.any():
                stats.append({"offset_hours":off,"n":0,"coverage":0.0});continue
            se=A.loc[ok,"source_entry"].to_numpy(float);sx=A.loc[ok,"source_exit"].to_numpy(float)
            fe=ep[ok].to_numpy(float);fx=xp[ok].to_numpy(float)
            de=np.abs((fe/se-1)*1e4);dx=np.abs((fx/sx-1)*1e4)
            src=A.loc[ok,"source_r"].to_numpy(float);risk=A.loc[ok,"source_risk"].to_numpy(float)
            fr=(fx-fe)/risk
            corr=float(np.corrcoef(src,fr)[0,1]) if len(src)>2 and np.std(src)>0 and np.std(fr)>0 else np.nan
            stats.append({"offset_hours":off,"n":int(ok.sum()),"coverage":float(ok.mean()),
                          "median_abs_entry_price_diff_bp":float(np.median(de)),
                          "median_abs_exit_price_diff_bp":float(np.median(dx)),
                          "median_abs_two_leg_price_diff_bp":float(np.median(np.r_[de,dx])),
                          "source_vs_ftmo_r_corr":corr})
        S=pd.DataFrame(stats);S.to_csv(out/"EA01_ALIGNMENT_SCAN.csv",index=False)
        elig=S[S.coverage>=.90].copy()
        if elig.empty:raise RuntimeError("No offset >=90% coverage")
        best=elig.sort_values(["median_abs_two_leg_price_diff_bp","offset_hours"]).iloc[0].to_dict()
        off=int(best["offset_hours"])

        exrows=[]
        for _,r in no.iterrows():
            eb=r.entry_time_utc+pd.Timedelta(hours=off);xb=r.source_exit_time_utc+pd.Timedelta(hours=off)
            en=first_tick(sym,eb);ex=first_tick(sym,xb)
            rec={"source_entry_time_utc":r.entry_time_utc,"source_exit_time_utc":r.source_exit_time_utc,
                 "mapped_entry_utc":eb,"mapped_exit_utc":xb,"source_entry":float(r.entry),
                 "source_risk":float(r.risk),"source_r":float(r.r_12),"available":False}
            if en is None or ex is None:
                exrows.append(rec);continue
            exec_r=(float(ex["bid"])-float(en["ask"]))/float(r.risk)
            comm_usd_per_lot=(float(en["ask"])+float(ex["bid"]))*contract*METAL_COMMISSION_RATE_SIDE
            risk_usd_per_lot=float(r.risk)*contract
            comm_r=comm_usd_per_lot/risk_usd_per_lot
            rec.update({"available":True,"entry_tick_utc":en["time"],"exit_tick_utc":ex["time"],
                        "entry_bid":en["bid"],"entry_ask":en["ask"],"exit_bid":ex["bid"],"exit_ask":ex["ask"],
                        "entry_spread_price":float(en["ask"]-en["bid"]),"exit_spread_price":float(ex["ask"]-ex["bid"]),
                        "exec_r_before_commission":exec_r,"commission_r":comm_r,"net_r":exec_r-comm_r})
            exrows.append(rec)
        X=pd.DataFrame(exrows);X.to_csv(out/"EA01_FTMO_EXECUTION_LEDGER.csv",index=False)
        z=X[X.available==True].copy()
        if len(z)<.90*len(X):raise RuntimeError(f"Execution coverage too low {len(z)}/{len(X)}")
        vals=z.net_r.to_numpy(float)
        years={str(int(y)):{"n":int(len(g)),"mean_net_r":float(g.net_r.mean())}
               for y,g in z.groupby(pd.to_datetime(z.source_entry_time_utc,utc=True).dt.year)}
        result={
          "version":VERSION,"candidate":"EA01-XR-RSI-LONG-V1","source_signals":int(len(d)),
          "non_overlap_n":int(len(no)),"best_alignment":best,"symbol":sym,"ftmo_identity":ident,
          "contract_size":contract,"metal_commission_rate_per_side":METAL_COMMISSION_RATE_SIDE,
          "execution":{"n":int(len(z)),"coverage":float(len(z)/len(X)),
             "source_mean_r_on_exec_sample":float(z.source_r.mean()),
             "mean_exec_r_before_commission":float(z.exec_r_before_commission.mean()),
             "mean_commission_r":float(z.commission_r.mean()),
             "mean_net_r":float(z.net_r.mean()),"median_net_r":float(z.net_r.median()),
             "pf_net":pf(vals),"win_rate":float((vals>0).mean()),
             "trim1_net_r":trim_best(vals,.01),"trim2_net_r":trim_best(vals,.02),
             "years":years,"bootstrap_month":month_boot(z.source_entry_time_utc,vals)},
          "classification":None,"2026_accessed":False,"retuning_performed":False
        }
        q10=result["execution"]["bootstrap_month"].get("q10",np.nan)
        if result["execution"]["mean_net_r"]<=0:
            result["classification"]="ECONOMICALLY_REJECTED_FTMO"
        elif np.isfinite(q10) and q10>0 and result["execution"]["trim1_net_r"]>0:
            result["classification"]="FTMO_EXECUTION_POSITIVE_CONFIRMED"
        else:
            result["classification"]="FTMO_EXECUTION_POSITIVE_UNCERTAIN"
        (out/"EA01_FTMO_TRANSPORT_RESULT.json").write_text(json.dumps(result,indent=2,default=str)+"\n",encoding="utf-8")
        print(json.dumps(result,indent=2,default=str))
    finally:
        mt5.shutdown()

if __name__=="__main__":
    main()
