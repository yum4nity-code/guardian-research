#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, math, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

VERSION="D035-F1-FTMO-TRANSPORT-2026H1-1.0"
START=pd.Timestamp("2026-01-01T00:00:00Z")
END=pd.Timestamp("2026-07-01T00:00:00Z")
WARMUP=pd.Timestamp("2025-11-01T00:00:00Z")
DUAL_WINDOW_MIN=5
HORIZONS=(15,30)
COMMISSION_RATE=0.000325
MIN_N=100

def log(x): print(f"[D035-F1] {x}",flush=True)

def load_base(path:Path):
    spec=importlib.util.spec_from_file_location("d035_base_full",path)
    mod=importlib.util.module_from_spec(spec); sys.modules["d035_base_full"]=mod; spec.loader.exec_module(mod)
    need=["load_metrics","load_klines","exact_5m_source","causal_shocks","merge_source_events",
          "load_cfd_files","canonical_cfd_symbol","calibrate_offsets","apply_offsets",
          "build_event_exclusion_intervals","first_row_at_or_after","mid_short_return",
          "CONTROL_LOOKBACK_DAYS"]
    miss=[x for x in need if not hasattr(mod,x)]
    if miss: raise RuntimeError(f"Base analyzer missing API {miss}")
    return mod

def build_dual(btc,eth):
    raw=pd.concat([btc,eth],ignore_index=True).sort_values("event_time_utc").reset_index(drop=True)
    rows=[]; i=0
    while i<len(raw):
        first=raw.iloc[i].copy(); group=[first]; j=i+1
        while j<len(raw) and raw.loc[j,"event_time_utc"]-first["event_time_utc"]<=pd.Timedelta(minutes=DUAL_WINDOW_MIN):
            group.append(raw.iloc[j].copy()); j+=1
        sources=sorted(set(str(g["source"]) for g in group))
        if sources==["BTCUSD","ETHUSD"]:
            later=max(g["event_time_utc"] for g in group); earlier=min(g["event_time_utc"] for g in group)
            r=first.copy(); r["event_time_utc"]=later; r["first_source_time_utc"]=earlier
            r["confirmation_delay_min"]=(later-earlier).total_seconds()/60.0
            r["sources"]="BTCUSD+ETHUSD"; r["source_count"]=2
            r["ret5_pct"]=min(float(g["ret5_pct"]) for g in group)
            r["oi_chg5_pct"]=min(float(g["oi_chg5_pct"]) for g in group)
            rows.append(r)
        i=j
    return pd.DataFrame(rows).sort_values("event_time_utc").reset_index(drop=True) if rows else pd.DataFrame()

def gross_short_bps(entry_bid,exit_ask):
    return (entry_bid-exit_ask)/entry_bid*10000.0 if entry_bid>0 and exit_ask>0 else np.nan

def net_ftmo_short_bps(entry_bid,exit_ask):
    if entry_bid<=0 or exit_ask<=0: return np.nan
    pnl=entry_bid-exit_ask-COMMISSION_RATE*entry_bid-COMMISSION_RATE*exit_ask
    return pnl/entry_bid*10000.0

def near_event(ts,event_ns,mins=120):
    if event_ns.size==0: return False
    v=int(ts.value); pos=int(np.searchsorted(event_ns,v)); best=None
    if pos<event_ns.size: best=abs(int(event_ns[pos])-v)
    if pos>0:
        d=abs(int(event_ns[pos-1])-v); best=d if best is None else min(best,d)
    return best is not None and best<=mins*60*1_000_000_000

def control_net_median(x,ts,event_ns):
    hist=x[(x["utc_ts"]>=ts-pd.Timedelta(days=60))&(x["utc_ts"]<ts)].copy()
    hist=hist[(hist["utc_ts"].dt.dayofweek==ts.dayofweek)&(hist["utc_ts"].dt.hour==ts.hour)&(hist["utc_ts"].dt.minute%5==ts.minute%5)]
    vals=[]
    for _,r in hist.iterrows():
        t0=r["utc_ts"]
        if near_event(t0,event_ns): continue
        ex_idx=x["utc_ts"].array.searchsorted(t0+pd.Timedelta(minutes=15))
        if ex_idx>=len(x): continue
        ex=x.iloc[int(ex_idx)]
        if ex["utc_ts"]-(t0+pd.Timedelta(minutes=15))>pd.Timedelta(minutes=2): continue
        v=net_ftmo_short_bps(float(r["bid_first"]),float(ex["ask_first"]))
        if np.isfinite(v): vals.append(v)
    return float(np.median(vals)) if len(vals)>=8 else np.nan

def bootstrap(df,col,reps=20000,seed=35151):
    z=df.dropna(subset=[col]).copy(); z["day"]=z["event_time_utc"].dt.floor("D")
    groups=[g[col].to_numpy(float) for _,g in z.groupby("day",sort=True)]
    if len(groups)<10: return {"days":len(groups),"q10_one_sided90_lower":None,"p_boot_mean_le_0":None}
    rng=np.random.default_rng(seed); vals=np.empty(reps)
    for i in range(reps):
        picks=rng.integers(0,len(groups),size=len(groups))
        arr=np.concatenate([groups[j] for j in picks]); vals[i]=arr.mean()
    return {"days":len(groups),"reps":reps,"q10_one_sided90_lower":float(np.quantile(vals,.10)),
            "q025_two_sided95_lower":float(np.quantile(vals,.025)),
            "median_bootstrap_mean":float(np.median(vals)),"p_boot_mean_le_0":float(np.mean(vals<=0))}

def trim_best(a,p=.01):
    a=np.sort(pd.Series(a).dropna().to_numpy(float)); k=max(1,int(math.ceil(len(a)*p)))
    kept=a[:-k] if k<len(a) else np.array([])
    return {"removed":k,"n":len(kept),"mean":float(kept.mean()) if len(kept) else None}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base-analyzer",required=True,type=Path)
    ap.add_argument("--cfd-dir",required=True,type=Path)
    ap.add_argument("--cache-dir",required=True,type=Path)
    ap.add_argument("--out-dir",required=True,type=Path)
    args=ap.parse_args(); args.out_dir.mkdir(parents=True,exist_ok=True); args.cache_dir.mkdir(parents=True,exist_ok=True)
    base=load_base(args.base_analyzer)

    source5={}; klines={}
    for sym in ["BTCUSDT","ETHUSDT"]:
        m,_=base.load_metrics(args.cache_dir,sym,WARMUP,END)
        k,_=base.load_klines(args.cache_dir,sym,WARMUP,END)
        klines[sym]=k; source5[sym]=base.exact_5m_source(k,m)
    btc=base.causal_shocks(source5["BTCUSDT"],"BTCUSDT"); eth=base.causal_shocks(source5["ETHUSDT"],"ETHUSDT")
    all_events=base.merge_source_events(btc,eth)
    dual=build_dual(btc,eth); dual=dual[(dual["event_time_utc"]>=START)&(dual["event_time_utc"]<END)].copy()
    log(f"source events={len(dual)}")

    cfd=base.load_cfd_files(args.cfd_dir)
    canon={k:base.canonical_cfd_symbol(k) for k in cfd}; seen=set(canon.values())
    if seen!={"BTCUSD","XLMUSD"}: raise RuntimeError(f"Expected BTCUSD+XLMUSD only, found {sorted(seen)}")
    btc_key=next(k for k,v in canon.items() if v=="BTCUSD"); xlm_key=next(k for k,v in canon.items() if v=="XLMUSD")

    qa=base.calibrate_offsets(cfd[btc_key],klines["BTCUSDT"],fixed_offset=None)
    qa.to_csv(args.out_dir/"D035_F1_OFFSET_QA.csv",index=False)
    usable=int(qa["usable"].sum())
    if usable<max(4,int(.70*len(qa))): raise RuntimeError(f"UTC alignment QA failed {usable}/{len(qa)}")

    x=base.apply_offsets(cfd[xlm_key],qa)
    x=x[(x["utc_ts"]>=START)&(x["utc_ts"]<END+pd.Timedelta(minutes=31))].copy()
    if x.empty or x["utc_ts"].min()>pd.Timestamp("2026-01-07T00:00:00Z") or x["utc_ts"].max()<pd.Timestamp("2026-06-25T00:00:00Z"):
        raise RuntimeError(f"Insufficient FTMO XLMUSD coverage {x['utc_ts'].min() if not x.empty else None} -> {x['utc_ts'].max() if not x.empty else None}")

    event_ns=base.build_event_exclusion_intervals(all_events); rows=[]
    for idx,(_,e) in enumerate(dual.iterrows(),1):
        ts=e["event_time_utc"]; ent=base.first_row_at_or_after(x,ts,tolerance_min=2)
        if ent is None: continue
        row={"event_time_utc":ts,"entry_time_utc":ent["utc_ts"],"entry_bid":float(ent["bid_first"]),
             "entry_ask":float(ent["ask_first"]),"entry_spread_bps":(float(ent["ask_first"])-float(ent["bid_first"]))/float(ent["mid_first"])*10000.0}
        for h in HORIZONS:
            ex=base.first_row_at_or_after(x,ts+pd.Timedelta(minutes=h),tolerance_min=2)
            if ex is None:
                row[f"gross_exec_{h}m_bps"]=np.nan; row[f"net_ftmo_{h}m_bps"]=np.nan
            else:
                eb=float(ent["bid_first"]); ea=float(ex["ask_first"])
                row[f"gross_exec_{h}m_bps"]=gross_short_bps(eb,ea)
                row[f"net_ftmo_{h}m_bps"]=net_ftmo_short_bps(eb,ea)
        row["control_net_15m_bps"]=control_net_median(x,ts,event_ns)
        row["diff_net_15m_bps"]=row["net_ftmo_15m_bps"]-row["control_net_15m_bps"] if np.isfinite(row["net_ftmo_15m_bps"]) and np.isfinite(row["control_net_15m_bps"]) else np.nan
        rows.append(row)
        if idx%100==0: log(f"{idx}/{len(dual)}")
    er=pd.DataFrame(rows); er.to_csv(args.out_dir/"D035_F1_FTMO_XLM_EVENT_RETURNS.csv",index=False)
    dual.to_csv(args.out_dir/"D035_F1_CAUSAL_DUAL_EVENTS.csv",index=False)

    n=int(er["net_ftmo_15m_bps"].notna().sum()) if not er.empty else 0
    mean=float(er["net_ftmo_15m_bps"].mean()) if n else None
    boot=bootstrap(er,"net_ftmo_15m_bps") if n else {"q10_one_sided90_lower":None}
    if n<MIN_N:
        existence="SPARSE_POSITIVE" if mean is not None and mean>0 else "NEGATIVE"; support="SPARSE"
    elif mean is None or mean<=0:
        existence="NEGATIVE"; support="ADEQUATE"
    elif boot["q10_one_sided90_lower"] is not None and boot["q10_one_sided90_lower"]>0:
        existence="POSITIVE_CONFIRMED"; support="ADEQUATE"
    else:
        existence="POSITIVE_UNCERTAIN"; support="ADEQUATE"

    months=[]
    if n:
        z=er.copy(); z["month"]=z["event_time_utc"].dt.strftime("%Y-%m")
        for m,g in z.groupby("month",sort=True):
            months.append({"month":m,"n":int(g["net_ftmo_15m_bps"].notna().sum()),"mean_net_15m_bps":float(g["net_ftmo_15m_bps"].mean())})

    primary={
      "n":n,
      "mean_entry_spread_bps":float(er["entry_spread_bps"].mean()) if n else None,
      "mean_gross_exec_15m_bps":float(er["gross_exec_15m_bps"].mean()) if n else None,
      "mean_net_ftmo_15m_bps":mean,
      "median_net_ftmo_15m_bps":float(er["net_ftmo_15m_bps"].median()) if n else None,
      "mean_net_ftmo_30m_bps":float(er["net_ftmo_30m_bps"].mean()) if n else None,
      "mean_control_net_15m_bps":float(er["control_net_15m_bps"].mean()) if n else None,
      "mean_diff_net_15m_bps":float(er["diff_net_15m_bps"].mean()) if n else None,
      "bootstrap_net15":boot,
      "trim_best_1pct":trim_best(er["net_ftmo_15m_bps"]) if n else None
    }
    result={"schema":1,"version":VERSION,"status":"COMPLETE_FTMO_TRANSPORT_CONFIRMATION",
      "candidate":"D035-F1-XLMUSD","source_events":int(len(dual)),
      "commission_rate_per_side":COMMISSION_RATE,"primary":primary,"monthly":months,
      "classification":{"existence":existence,"support":support,"economic_size":"MINI_EDGE" if mean is not None and mean>0 else "NO_POSITIVE_EXECUTABLE_EDGE",
                        "production_status":"NOT_PRODUCTION_READY"},
      "scope":{"ftmo_xlm_target_outcomes_opened":True,"jul_dec_2026_opened":False,"other_targets_opened":False},
      "retuning_performed":False,"live_deployment_authorized":False}
    (args.out_dir/"D035_F1_RESULT.json").write_text(json.dumps(result,indent=2,default=str)+"\n",encoding="utf-8")

    print("=== D035-F1 FTMO TRANSPORT RECEIPT ===")
    print(json.dumps({"version":VERSION,"source_events":len(dual),"primary":primary,"classification":result["classification"],
                      "jul_dec_2026_opened":False,"other_targets_opened":False,"retuning_performed":False,
                      "output":str(args.out_dir)},indent=2,default=str))

if __name__=="__main__": main()
