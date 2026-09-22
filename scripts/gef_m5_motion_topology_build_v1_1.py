from pathlib import Path
import argparse, hashlib, json, math, time
import numpy as np
import pandas as pd

ENGINE_VERSION="M5-MOTION-TOPOLOGY-BUILD-1.1.0"
START_YEAR=2011
END_YEAR=2014
DISCOVERY_START=pd.Timestamp("2012-01-01")
DISCOVERY_END=pd.Timestamp("2015-01-01")
FREQ="5min"
SLOTS_PER_WEEK=7*24*12
BUFFER_SLOTS=6
FAST_Z_MIN=250
BETA_WINDOW=240
BETA_MIN=120

MARKETS=["XAUUSD","XAGUSD","UDXUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","SPXUSD","NSXUSD","WTIUSD","BCOUSD"]
GRAPH=[
 ("XAUUSD","XAGUSD"),("XAUUSD","UDXUSD"),("XAGUSD","UDXUSD"),
 ("USDCAD","WTIUSD"),("USDCAD","BCOUSD"),("WTIUSD","BCOUSD"),
 ("NSXUSD","SPXUSD"),
 ("UDXUSD","EURUSD"),("UDXUSD","GBPUSD"),("UDXUSD","AUDUSD"),
 ("UDXUSD","USDJPY"),("UDXUSD","USDCHF"),("UDXUSD","USDCAD"),
]
LOOKBACKS=[15,30,60]
HORIZONS=[15,30,60]

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for ch in iter(lambda:f.read(1024*1024),b""):
            h.update(ch)
    return h.hexdigest()

def slot_of_week(idx):
    idx=pd.DatetimeIndex(idx)
    return (idx.dayofweek.to_numpy()*288 + idx.hour.to_numpy()*12 + (idx.minute.to_numpy()//5)).astype(np.int16)

def explicit_minutes(idx):
    return pd.DatetimeIndex(idx).to_numpy(dtype="datetime64[m]").astype(np.int64)

def causal_expanding_z(s,min_periods=FAST_Z_MIN):
    s=pd.to_numeric(s,errors="coerce").astype(float)
    mu=s.expanding(min_periods=min_periods).mean().shift(1)
    sd=s.expanding(min_periods=min_periods).std().shift(1).replace(0,np.nan)
    return (s-mu)/sd

def rolling_beta(a,b):
    a=pd.to_numeric(a,errors="coerce").astype(float)
    b=pd.to_numeric(b,errors="coerce").astype(float)
    cov=a.rolling(BETA_WINDOW,min_periods=BETA_MIN).cov(b).shift(1)
    var=b.rolling(BETA_WINDOW,min_periods=BETA_MIN).var().shift(1).replace(0,np.nan)
    return cov/var

def rolling_efficiency(close,k):
    net=(close/close.shift(k)-1).abs()
    r=close.pct_change(fill_method=None).abs()
    path=r.rolling(k,min_periods=k).sum().replace(0,np.nan)
    return net/path

def run_length_sign(r):
    a=np.sign(pd.to_numeric(r,errors="coerce").to_numpy(dtype=float))
    out=np.zeros(len(a),dtype=np.int16)
    last=0.0;run=0
    for i,v in enumerate(a):
        if not np.isfinite(v) or v==0:
            last=0.0;run=0;out[i]=0
        elif v==last:
            run=min(run+1,32767);out[i]=run
        else:
            last=v;run=1;out[i]=1
    return pd.Series(out,index=r.index,dtype="int16")

def detect_cols(d):
    lower={str(c).strip().lower():c for c in d.columns}
    dc=next((lower[x] for x in ["datetime","timestamp","time","date"] if x in lower),None)
    if dc is None and isinstance(d.index,pd.DatetimeIndex):
        d=d.reset_index()
        dc=d.columns[0]
        lower={str(c).strip().lower():c for c in d.columns}
    close=lower.get("close")
    op=lower.get("open");hi=lower.get("high");lo=lower.get("low")
    if dc is None or close is None:
        raise RuntimeError("Cannot identify datetime/close columns")
    return d,dc,op,hi,lo,close

def load_market_m5(root,sym):
    parts=[];true_ohlc=True;rows_by_year={}
    for y in range(START_YEAR,END_YEAR+1):
        p=root/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
        if not p.exists():
            raise RuntimeError(f"Missing required M1 file {p}")
        d=pd.read_parquet(p)
        d,dc,op,hi,lo,close=detect_cols(d)
        if any(x is None for x in [op,hi,lo]):
            true_ohlc=False
        utc=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(hours=5)
        q=pd.DataFrame({"utc":utc,"close":pd.to_numeric(d[close],errors="coerce")})
        if true_ohlc and all(x is not None for x in [op,hi,lo]):
            q["open"]=pd.to_numeric(d[op],errors="coerce")
            q["high"]=pd.to_numeric(d[hi],errors="coerce")
            q["low"]=pd.to_numeric(d[lo],errors="coerce")
        q=q.dropna(subset=["utc","close"])
        q=q[q["utc"].dt.year==y].sort_values("utc").drop_duplicates("utc",keep="last")
        rows_by_year[str(y)]=len(q)
        parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last").set_index("utc")
    if true_ohlc and {"open","high","low","close"}.issubset(q.columns):
        bars=pd.DataFrame({
          "open":q["open"].resample(FREQ,label="right",closed="left").first(),
          "high":q["high"].resample(FREQ,label="right",closed="left").max(),
          "low":q["low"].resample(FREQ,label="right",closed="left").min(),
          "close":q["close"].resample(FREQ,label="right",closed="left").last(),
        })
        ohlc_mode="raw_m1_ohlc"
    else:
        c=q["close"]
        bars=pd.DataFrame({
          "open":c.resample(FREQ,label="right",closed="left").first(),
          "high":c.resample(FREQ,label="right",closed="left").max(),
          "low":c.resample(FREQ,label="right",closed="left").min(),
          "close":c.resample(FREQ,label="right",closed="left").last(),
        })
        ohlc_mode="close_path_proxy"
    grid=pd.date_range(f"{START_YEAR}-01-01 00:00",f"{END_YEAR}-12-31 23:55",freq=FREQ)
    bars=bars.reindex(grid)
    bars.index.name="decision_time_utc"
    return bars,{"ohlc_mode":ohlc_mode,"m1_rows_by_year":rows_by_year}

def observed_tradability(close):
    idx=close.index
    present=close.notna().to_numpy(dtype=bool)
    mask=present.copy()
    # Remove the final 30m of observed bars before every observed gap/closure
    # and the first 30m after every reopen/recovery. This is date-specific and
    # naturally absorbs DST/session changes instead of forcing fixed UTC slots.
    for i in range(1,len(present)):
        if present[i-1] and not present[i]:
            a=max(0,i-BUFFER_SLOTS); mask[a:i]=False
        if (not present[i-1]) and present[i]:
            b=min(len(present),i+BUFFER_SLOTS); mask[i:b]=False
    return pd.Series(mask,index=idx,dtype=bool)

def continuous_window_mask(mask,back_steps=0,fwd_steps=0):
    a=mask.to_numpy(dtype=bool)
    out=a.copy()
    for k in range(1,back_steps+1):
        z=np.zeros(len(a),dtype=bool);z[k:]=a[:-k];out&=z
    for k in range(1,fwd_steps+1):
        z=np.zeros(len(a),dtype=bool);z[:-k]=a[k:];out&=z
    return out

def build_state(bars,tradable):
    c=bars["close"].astype(float);o=bars["open"].astype(float);h=bars["high"].astype(float);l=bars["low"].astype(float)
    r5=c.pct_change(fill_method=None)
    F=pd.DataFrame(index=bars.index)
    F["ret_5m"]=r5
    for m in [10,15,30,60]:
        k=m//5;F[f"ret_{m}m"]=c/c.shift(k)-1
    F["accel_5_vs_15"]=F["ret_5m"]-F["ret_15m"]/3.0
    F["accel_10_vs_30"]=F["ret_10m"]-F["ret_30m"]/3.0
    for m in [15,30,60]:
        k=m//5
        F[f"rv_{m}m"]=r5.rolling(k,min_periods=k).std()
        rh=h.rolling(k,min_periods=k).max()
        rl=l.rolling(k,min_periods=k).min()
        F[f"dist_high_{m}m"]=c/rh-1
        F[f"dist_low_{m}m"]=c/rl-1
        F[f"path_eff_{m}m"]=rolling_efficiency(c,k)
    rng=(h-l).replace(0,np.nan)
    body=(c-o).abs()
    F["bar_range_pct"]=rng/c.replace(0,np.nan)
    prior_med=F["bar_range_pct"].rolling(12,min_periods=6).median().shift(1).replace(0,np.nan)
    F["range_expansion_60m"]=F["bar_range_pct"]/prior_med
    F["body_frac"]=body/rng
    F["upper_wick_frac"]=(h-np.maximum(o,c))/rng
    F["lower_wick_frac"]=(np.minimum(o,c)-l)/rng
    F["same_dir_run"]=run_length_sign(r5).astype(float)
    F["shock_z_5m"]=causal_expanding_z(r5,FAST_Z_MIN)
    F["shock_abs_ge_1p5"]=(F["shock_z_5m"].abs()>=1.5).astype("int8")
    F["failure_extend_after_shock"]=(F["shock_abs_ge_1p5"].shift(1).fillna(0).astype(bool) & (np.sign(F["ret_5m"])!=np.sign(F["ret_15m"]))).astype("int8")
    F["tradable"]=tradable.astype("int8")
    for col in F.columns:
        if col not in ["shock_abs_ge_1p5","failure_extend_after_shock","tradable"]:
            F[col]=pd.to_numeric(F[col],errors="coerce").astype("float32")
    return F

def build_endpoint_targets(bars,state,tradable):
    c=bars["close"].astype(float)
    r5=c.pct_change(fill_method=None)
    prior_rv=r5.rolling(12,min_periods=6).std().shift(1)
    T=pd.DataFrame(index=bars.index)
    for L in LOOKBACKS:
        kL=L//5
        pm=c/c.shift(kL)-1
        direction=np.sign(pm)
        back_ok=continuous_window_mask(tradable,back_steps=kL,fwd_steps=0)
        T[f"past_move_{L}m"]=pm.astype("float32")
        for H in HORIZONS:
            kH=H//5
            path=[]
            for j in range(1,kH+1):
                path.append((c.shift(-j)/c-1).to_numpy(dtype=float))
            A=np.column_stack(path)
            d=direction.to_numpy(dtype=float)
            signed=A*d[:,None]
            scale=(prior_rv.to_numpy(dtype=float)*math.sqrt(kH))
            future_ok=continuous_window_mask(tradable,back_steps=0,fwd_steps=kH)
            eligible=back_ok&future_ok&np.isfinite(d)&(d!=0)&np.isfinite(scale)&(scale>0)

            # Evaluate excursions only on rows that can actually become eligible.
            # This avoids noisy All-NaN/divide-by-zero warnings on boundary/gap rows
            # without changing any target semantics.
            cont=np.full(len(c),np.nan,dtype=float)
            rev=np.full(len(c),np.nan,dtype=float)
            score=np.full(len(c),np.nan,dtype=float)
            eval_mask=eligible&np.all(np.isfinite(A),axis=1)
            if np.any(eval_mask):
                cont[eval_mask]=np.max(signed[eval_mask],axis=1)
                rev[eval_mask]=np.max(-signed[eval_mask],axis=1)
                score[eval_mask]=(rev[eval_mask]-cont[eval_mask])/scale[eval_mask]
            eligible=eligible&eval_mask
            T[f"cont_exc_{L}m_{H}m"]=cont.astype("float32")
            T[f"rev_exc_{L}m_{H}m"]=rev.astype("float32")
            T[f"endpoint_score_{L}m_{H}m"]=score.astype("float32")
            T[f"top_label_{L}m_{H}m"]=np.where(eligible&(d>0),score>0,np.nan)
            T[f"bottom_label_{L}m_{H}m"]=np.where(eligible&(d<0),score>0,np.nan)
            T[f"eligible_{L}m_{H}m"]=eligible.astype("int8")
    return T

def cross_state_from_market_states(states):
    idx=next(iter(states.values())).index
    X=pd.DataFrame(index=idx)
    r5=pd.DataFrame({s:states[s]["ret_5m"] for s in MARKETS},index=idx)
    z5=pd.DataFrame({s:states[s]["shock_z_5m"] for s in MARKETS},index=idx)
    trad=pd.DataFrame({s:states[s]["tradable"].astype(bool) for s in MARKETS},index=idx)
    X["breadth_positive_frac_5m"]=(r5.gt(0).sum(axis=1)/r5.notna().sum(axis=1).replace(0,np.nan)).astype("float32")
    X["dispersion_ret5"]=r5.std(axis=1).astype("float32")
    X["shock_breadth_abs1p5"]=(z5.abs().ge(1.5).sum(axis=1)/z5.notna().sum(axis=1).replace(0,np.nan)).astype("float32")
    X["all13_tradable"]=trad.all(axis=1).astype("int8")
    for a,b in GRAPH:
        ra=pd.to_numeric(states[a]["ret_5m"],errors="coerce").astype(float)
        rb=pd.to_numeric(states[b]["ret_5m"],errors="coerce").astype(float)
        beta=rolling_beta(ra,rb)
        resid=ra-beta*rb
        rz=causal_expanding_z(resid,FAST_Z_MIN)
        cs=ra.rolling(12,min_periods=8).corr(rb)
        cl=ra.rolling(72,min_periods=36).corr(rb)
        edge=f"{a}__{b}"
        X[f"{edge}__same_sign"]=(np.sign(ra)==np.sign(rb)).where(ra.notna()&rb.notna()).astype("float32")
        X[f"{edge}__beta"]=beta.astype("float32")
        X[f"{edge}__resid"]=resid.astype("float32")
        X[f"{edge}__resid_z"]=rz.astype("float32")
        X[f"{edge}__corr_short"]=cs.astype("float32")
        X[f"{edge}__corr_long"]=cl.astype("float32")
        X[f"{edge}__corr_break"]=(cs-cl).astype("float32")
        X[f"{edge}__resid_zero_cross"]=((np.sign(resid)!=np.sign(resid.shift(1)))&resid.notna()&resid.shift(1).notna()).astype("int8")
        X[f"{edge}__joint_tradable"]=(trad[a]&trad[b]).astype("int8")
        for lag in [1,2,3]:
            X[f"{edge}__Aret5_lag{lag}"]=ra.shift(lag).astype("float32")
            X[f"{edge}__Bret5_lag{lag}"]=rb.shift(lag).astype("float32")
    return X

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root)
    repo=root/"guardian-research"
    spec=repo/"research"/"campaigns"/"GUARDIAN_M5_MOTION_TOPOLOGY_FACTORY_V1_1_2026_09_22.json"
    if not spec.exists(): raise RuntimeError("Missing frozen M5 Motion Topology spec")
    frozen=json.loads(spec.read_text(encoding="utf-8"))
    if frozen.get("status")!="FROZEN_BEFORE_ANY_ALPHA_TEST": raise RuntimeError("M5 topology V1.1 design not frozen")
    if int(frozen.get("first_engine_max_outcome_year",0))!=2014: raise RuntimeError("Unexpected firewall in frozen spec")

    base=root/"Research"/"Autonomous"/"guardian_m5_motion_topology_v1_1"
    base.mkdir(parents=True,exist_ok=True)
    rid="GEFM5T-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    out=base/rid;out.mkdir(parents=True,exist_ok=False)
    (out/"market").mkdir();(out/"targets").mkdir()
    t0=time.time()
    def status(i,n,msg,**extra):
        p={"run_id":rid,"engine_version":ENGINE_VERSION,"step":i,"steps":n,"elapsed_s":round(time.time()-t0,1),"message":msg,**extra}
        write_json(out/"LIVE_STATUS.json",p)
        tail=" | ".join(f"{k}={v}" for k,v in extra.items())
        print(f"[M5-TOPOLOGY] {i}/{n} | {msg}"+(f" | {tail}" if tail else ""),flush=True)

    status(1,10,"build M5 OHLC 2011-2014 only; 2015+ forbidden")
    states={};trad_cols={};coverage=[];market_files={};target_files={}
    for i,sym in enumerate(MARKETS,1):
        bars,meta=load_market_m5(root,sym)
        if bars.index.max()>=pd.Timestamp("2015-01-01"): raise RuntimeError("2015+ escaped M5 builder")
        trad=observed_tradability(bars["close"])
        state=build_state(bars,trad)
        target=build_endpoint_targets(bars,state,trad)
        bp=out/"market"/f"{sym}_M5_OHLC_2011_2014.parquet"
        sp=out/"market"/f"{sym}_STATE_2011_2014.parquet"
        tp=out/"targets"/f"{sym}_ENDPOINT_2012_2014.parquet"
        bars.astype("float32").to_parquet(bp)
        state.to_parquet(sp)
        target.loc[(target.index>=DISCOVERY_START)&(target.index<DISCOVERY_END)].to_parquet(tp)
        states[sym]=state;trad_cols[sym]=trad
        market_files[sym]={"ohlc":str(bp),"state":str(sp),"ohlc_mode":meta["ohlc_mode"]}
        target_files[sym]=str(tp)
        disc=(bars.index>=DISCOVERY_START)&(bars.index<DISCOVERY_END)
        coverage.append({
          "market":sym,"ohlc_mode":meta["ohlc_mode"],"m5_close_rows_discovery":int(bars.loc[disc,"close"].notna().sum()),
          "tradable_rows_discovery":int(trad.loc[disc].sum()),
          "tradable_fraction_of_present":float(trad.loc[disc].sum()/max(1,bars.loc[disc,"close"].notna().sum())),
          "m1_rows_by_year_json":json.dumps(meta["m1_rows_by_year"],sort_keys=True)
        })
        print(f"[M5-TOPOLOGY] market {i}/{len(MARKETS)} {sym} mode={meta['ohlc_mode']}",flush=True)
    status(2,10,"per-market OHLC/state/endpoint caches written",markets=len(MARKETS))

    idx=next(iter(states.values())).index
    TM=pd.DataFrame({s:trad_cols[s] for s in MARKETS},index=idx)
    tm_path=out/"TRADABILITY_MASK_2011_2014.parquet";TM.to_parquet(tm_path)
    cov=pd.DataFrame(coverage);cov.to_csv(out/"MARKET_COVERAGE.csv",index=False)
    status(3,10,"observed-continuity tradability masks frozen",mask_rows=len(TM))

    X=cross_state_from_market_states(states)
    xp=out/"CROSS_STATE_2011_2014.parquet";X.to_parquet(xp)
    status(4,10,"cross-market state cache written",features=X.shape[1])

    # Discovery-only support audit, no outcome association and no edge test.
    support=[]
    for sym in MARKETS:
        tp=pd.read_parquet(target_files[sym])
        for L in LOOKBACKS:
            for H in HORIZONS:
                c=f"endpoint_score_{L}m_{H}m"
                support.append({"market":sym,"lookback_min":L,"horizon_min":H,
                                "finite_endpoint_scores":int(pd.to_numeric(tp[c],errors="coerce").notna().sum())})
    sup=pd.DataFrame(support);sup.to_csv(out/"ENDPOINT_SUPPORT.csv",index=False)
    status(5,10,"endpoint support audit written",min_support=int(sup["finite_endpoint_scores"].min()),max_support=int(sup["finite_endpoint_scores"].max()))

    graph=pd.DataFrame(GRAPH,columns=["A","B"])
    graph.to_csv(out/"FROZEN_ECONOMIC_GRAPH.csv",index=False)
    status(6,10,"economic graph frozen",edges=len(graph))

    manifest={
      "run_id":rid,"engine_version":ENGINE_VERSION,"frozen_spec":str(spec),"frozen_spec_sha256":sha256(spec),
      "window":{"warmup":"2011","discovery_outcomes":"2012-2014","max_source_year_read":2014},
      "market_files":market_files,"target_files":target_files,
      "tradability_mask_path":str(tm_path),"cross_state_path":str(xp),
      "graph_path":str(out/"FROZEN_ECONOMIC_GRAPH.csv"),
      "endpoint_support_path":str(out/"ENDPOINT_SUPPORT.csv"),
      "tradability_rule":{"method":"observed_contiguous_source_runs","buffer_minutes":BUFFER_SLOTS*5,
                           "missing_is_nontradable":True,"pair_group_requires_joint_tradability":True},
      "endpoint_rule":{
        "past_move_lookbacks_min":LOOKBACKS,"forward_horizons_min":HORIZONS,
        "continuation":"max sign(past_move)*forward_return over path",
        "reversal":"max -sign(past_move)*forward_return over path",
        "normalizer":"prior rv5 rolling 60m shifted 1 * sqrt(H/5)",
        "score":"(reversal_excursion-continuation_excursion)/normalizer",
        "future_path_only_target":True
      },
      "state_rule":{"fast_z_min_prior_obs":FAST_Z_MIN,"pair_beta_window_m5":BETA_WINDOW,"pair_beta_min":BETA_MIN,
                    "corr_short_m5":12,"corr_long_m5":72},
      "edge_trials":0
    }
    write_json(out/"CACHE_MANIFEST.json",manifest)
    status(7,10,"cache manifest written")

    receipt={
      "run_id":rid,"status":"COMPLETE_M5_MOTION_TOPOLOGY_CACHE_BUILD_V1_1",
      "engine_version":ENGINE_VERSION,"markets":len(MARKETS),"graph_edges":len(GRAPH),
      "cross_features":int(X.shape[1]),"endpoint_objects":int(len(support)),
      "edge_trials":0,"alpha_tests":0,
      "2015_plus_outcomes_accessed":False,"2018_plus_accessed":False,
      "2023_2025_accessed":False,"2026_accessed":False,
      "next":"AUDIT V1.1 CACHE; IF SESSION/INTEGRITY SUPPORT PASSES, PREREGISTER M01-M08 BEFORE ANY OUTCOME ASSOCIATION"
    }
    write_json(out/"RUN_RECEIPT.json",receipt)
    status(8,10,"receipt written; no edge tests performed")
    status(9,10,"2015+ outcomes remain unopened")
    status(10,10,"DONE")
    print("\n=== M5 TOPOLOGY CACHE RECEIPT ===")
    print(json.dumps(receipt,indent=2))
    print("\n=== MARKET COVERAGE ===")
    print(cov.to_string(index=False))
    print("\n=== ENDPOINT SUPPORT ===")
    print(sup.groupby(["lookback_min","horizon_min"])["finite_endpoint_scores"].agg(["min","median","max"]).reset_index().to_string(index=False))
    print("\nRUN:",out)

if __name__=="__main__":
    main()
