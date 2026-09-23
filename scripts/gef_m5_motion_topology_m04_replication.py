from pathlib import Path
import argparse, hashlib, json, math, time
import numpy as np
import pandas as pd
from scipy.stats import t as student_t

ENGINE_VERSION="M5-MOTION-TOPOLOGY-M04-REPLICATION-1.0"
START_YEAR=2011
END_YEAR=2017
REPL_START=pd.Timestamp("2015-01-01")
REPL_END=pd.Timestamp("2018-01-01")
FORBIDDEN_DATE=pd.Timestamp("2018-01-01")
FREQ="5min"
BUFFER_SLOTS=6
ZMIN=250
COOLDOWN_MIN=30
MIN_EPISODES=100
MIN_DAYS=60
P_MAX=0.05
MARKETS=["UDXUSD","EURUSD","GBPUSD","AUDUSD","USDCHF"]
TARGETS=["EURUSD","GBPUSD","AUDUSD","USDCHF"]

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for ch in iter(lambda:f.read(1024*1024),b""):
            h.update(ch)
    return h.hexdigest()

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
        if not p.exists(): raise RuntimeError(f"Missing {p}")
        d=pd.read_parquet(p)
        d,dc,op,hi,lo,close=detect_cols(d)
        if any(x is None for x in [op,hi,lo]): true_ohlc=False
        utc=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(hours=5)
        q=pd.DataFrame({"utc":utc,"close":pd.to_numeric(d[close],errors="coerce")})
        if true_ohlc and all(x is not None for x in [op,hi,lo]):
            q["open"]=pd.to_numeric(d[op],errors="coerce")
            q["high"]=pd.to_numeric(d[hi],errors="coerce")
            q["low"]=pd.to_numeric(d[lo],errors="coerce")
        q=q.dropna(subset=["utc","close"])
        q=q[q["utc"].dt.year==y].sort_values("utc").drop_duplicates("utc",keep="last")
        rows_by_year[str(y)]=len(q);parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last").set_index("utc")
    if true_ohlc and {"open","high","low","close"}.issubset(q.columns):
        bars=pd.DataFrame({
          "open":q["open"].resample(FREQ,label="right",closed="left").first(),
          "high":q["high"].resample(FREQ,label="right",closed="left").max(),
          "low":q["low"].resample(FREQ,label="right",closed="left").min(),
          "close":q["close"].resample(FREQ,label="right",closed="left").last(),
        })
        mode="raw_m1_ohlc"
    else:
        c=q["close"]
        bars=pd.DataFrame({
          "open":c.resample(FREQ,label="right",closed="left").first(),
          "high":c.resample(FREQ,label="right",closed="left").max(),
          "low":c.resample(FREQ,label="right",closed="left").min(),
          "close":c.resample(FREQ,label="right",closed="left").last(),
        })
        mode="close_path_proxy"
    grid=pd.date_range(f"{START_YEAR}-01-01 00:00",f"{END_YEAR}-12-31 23:55",freq=FREQ)
    bars=bars.reindex(grid);bars.index.name="decision_time_utc"
    return bars,{"ohlc_mode":mode,"m1_rows_by_year":rows_by_year}

def observed_tradability(close):
    present=close.notna().to_numpy(dtype=bool)
    mask=present.copy()
    for i in range(1,len(present)):
        if present[i-1] and not present[i]:
            mask[max(0,i-BUFFER_SLOTS):i]=False
        if (not present[i-1]) and present[i]:
            mask[i:min(len(present),i+BUFFER_SLOTS)]=False
    return pd.Series(mask,index=close.index,dtype=bool)

def continuous_window_mask(mask,back_steps=0,fwd_steps=0):
    a=mask.to_numpy(dtype=bool);out=a.copy()
    for k in range(1,back_steps+1):
        z=np.zeros(len(a),dtype=bool);z[k:]=a[:-k];out&=z
    for k in range(1,fwd_steps+1):
        z=np.zeros(len(a),dtype=bool);z[:-k]=a[k:];out&=z
    return out

def endpoint_target(bars,tradable,L):
    c=bars["close"].astype(float)
    r5=c.pct_change(fill_method=None)
    prior_rv=r5.rolling(12,min_periods=6).std().shift(1)
    k=L//5
    pm=c/c.shift(k)-1
    d=np.sign(pm).to_numpy(dtype=float)
    back_ok=continuous_window_mask(tradable,back_steps=k)
    A=np.column_stack([(c.shift(-j)/c-1).to_numpy(dtype=float) for j in range(1,k+1)])
    signed=A*d[:,None]
    scale=prior_rv.to_numpy(dtype=float)*math.sqrt(k)
    future_ok=continuous_window_mask(tradable,fwd_steps=k)
    eligible=back_ok&future_ok&np.isfinite(d)&(d!=0)&np.isfinite(scale)&(scale>0)&np.all(np.isfinite(A),axis=1)
    score=np.full(len(c),np.nan,dtype=float)
    if np.any(eligible):
        cont=np.max(signed[eligible],axis=1)
        rev=np.max(-signed[eligible],axis=1)
        score[eligible]=(rev-cont)/scale[eligible]
    return pd.Series(score,index=bars.index,dtype="float32")

def causal_z(s,min_periods=ZMIN):
    s=pd.to_numeric(s,errors="coerce").astype(float)
    mu=s.expanding(min_periods=min_periods).mean().shift(1)
    sd=s.expanding(min_periods=min_periods).std().shift(1).replace(0,np.nan)
    return (s-mu)/sd

def corr_break(ret_a,ret_b):
    a=pd.to_numeric(ret_a,errors="coerce").astype(float)
    b=pd.to_numeric(ret_b,errors="coerce").astype(float)
    cs=a.rolling(12,min_periods=8).corr(b)
    cl=a.rolling(72,min_periods=36).corr(b)
    return (cs-cl).astype("float32")

def m04_event(z):
    prev_ext=z.abs().shift(1).rolling(3,min_periods=1).max()
    return prev_ext.ge(1.5)&z.abs().lt(1.0)&(z.abs()<z.abs().shift(1))

def cooldown_first(times,raw,minutes=COOLDOWN_MIN):
    raw=np.asarray(raw,dtype=bool);out=np.zeros(len(raw),dtype=bool)
    last=None;cd=pd.Timedelta(minutes=minutes)
    for i in np.flatnonzero(raw):
        t=times[i]
        if last is None or t-last>=cd:
            out[i]=True;last=t
    return out

def cluster_test(y,clusters):
    y=np.asarray(y,dtype=float);clusters=np.asarray(clusters,dtype=object)
    good=np.isfinite(y)&pd.notna(clusters);y=y[good];clusters=clusters[good]
    n=len(y)
    if n<2:return dict(n=n,days=0,mean=np.nan,median=np.nan,positive_frac=np.nan,se=np.nan,t=np.nan,p_one=np.nan)
    codes,_=pd.factorize(clusters,sort=False);u=np.unique(codes);g=len(u)
    mean=float(np.mean(y));median=float(np.median(y));pos=float(np.mean(y>0))
    if g<2:return dict(n=n,days=g,mean=mean,median=median,positive_frac=pos,se=np.nan,t=np.nan,p_one=np.nan)
    resid=y-mean;meat=sum(float(np.sum(resid[codes==c]))**2 for c in u)
    v=(g/(g-1.0))*meat/(n*n);se=math.sqrt(v) if np.isfinite(v) and v>0 else np.nan
    tv=mean/se if np.isfinite(se) and se>0 else np.nan
    p=float(student_t.sf(tv,df=max(g-1,1))) if np.isfinite(tv) and mean>0 else 1.0
    return dict(n=n,days=g,mean=mean,median=median,positive_frac=pos,se=se,t=float(tv) if np.isfinite(tv) else np.nan,p_one=p)

def latest_discovery_cache(root):
    base=root/"Research"/"Autonomous"/"guardian_m5_motion_topology_v1_1"
    runs=[p for p in sorted(base.glob("GEFM5T-*")) if (p/"RUN_RECEIPT.json").exists() and (p/"CACHE_MANIFEST.json").exists()]
    if not runs:raise RuntimeError("No V1.1 discovery cache")
    return runs[-1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root);repo=root/"guardian-research"
    specp=repo/"research"/"campaigns"/"GUARDIAN_M5_M04_REPLICATION_SPEC_2026_09_23.json"
    spec=json.loads(specp.read_text(encoding="utf-8"))
    if spec.get("status")!="FROZEN_BEFORE_REPLICATION_OUTCOMES":raise RuntimeError("Replication spec not frozen")
    survivors=spec["frozen_survivors"]
    if len(survivors)!=6:raise RuntimeError("Expected exactly six frozen survivors")

    base=root/"Research"/"Autonomous"/"guardian_m5_motion_topology_m04_replication"
    base.mkdir(parents=True,exist_ok=True)
    rid="GEFM5R-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    out=base/rid;out.mkdir(parents=True,exist_ok=False)
    t0=time.time()
    def status(i,n,msg,**extra):
        obj={"run_id":rid,"engine_version":ENGINE_VERSION,"step":i,"steps":n,"elapsed_s":round(time.time()-t0,1),"message":msg,**extra}
        write_json(out/"LIVE_STATUS.json",obj)
        print(f"[M5-REPL] {i}/{n} | {msg}"+(" | "+" | ".join(f"{k}={v}" for k,v in extra.items()) if extra else ""),flush=True)

    status(1,9,"load only 2011-2017 raw markets; 2018+ forbidden")
    bars={};trad={};ret5={};targets={}
    for s in MARKETS:
        b,meta=load_market_m5(root,s)
        if b.index.max()>=FORBIDDEN_DATE:raise RuntimeError("2018+ escaped raw loader")
        bars[s]=b;trad[s]=observed_tradability(b["close"])
        ret5[s]=b["close"].pct_change(fill_method=None).astype("float32")
        if s in TARGETS:
            targets[s]={L:endpoint_target(b,trad[s],L) for L in sorted(set(int(x["lookback_min"]) for x in survivors if x["target"]==s))}
    idx=bars["UDXUSD"].index
    status(2,9,"raw M5 reconstruction complete",rows=len(idx))

    corr={};zmap={}
    for s in TARGETS:
        cb=corr_break(ret5["UDXUSD"],ret5[s])
        corr[s]=cb
        zmap[s]=causal_z(cb)
    status(3,9,"M04 correlation-break objects built causally")

    # Mandatory pre-2015 parity check against frozen discovery cache.
    dcache=latest_discovery_cache(root)
    dman=json.loads((dcache/"CACHE_MANIFEST.json").read_text())
    frozen_cross=pd.read_parquet(Path(dman["cross_state_path"]))
    frozen_cross.index=pd.to_datetime(frozen_cross.index)
    parity=[]
    parity_window=(idx>=pd.Timestamp("2012-01-01"))&(idx<pd.Timestamp("2015-01-01"))
    for s in TARGETS:
        col=f"UDXUSD__{s}__corr_break"
        ref=pd.to_numeric(frozen_cross[col],errors="coerce").reindex(idx)
        cur=corr[s]
        m=parity_window&ref.notna().to_numpy()&cur.notna().to_numpy()
        if not np.any(m):raise RuntimeError(f"No parity overlap for {s}")
        maxdiff=float(np.max(np.abs(ref.to_numpy(dtype=float)[m]-cur.to_numpy(dtype=float)[m])))
        refz=causal_z(ref)
        curz=zmap[s]
        mz=parity_window&refz.notna().to_numpy()&curz.notna().to_numpy()
        maxzdiff=float(np.max(np.abs(refz.to_numpy(dtype=float)[mz]-curz.to_numpy(dtype=float)[mz]))) if np.any(mz) else np.nan
        passed=bool(maxdiff<=5e-7 and np.isfinite(maxzdiff) and maxzdiff<=5e-7)
        parity.append({"target":s,"corr_break_max_abs_diff":maxdiff,"corr_break_z_max_abs_diff":maxzdiff,"pass":passed})
        if not passed:raise RuntimeError(f"Parity failed for {s}: cb={maxdiff} z={maxzdiff}")
    pd.DataFrame(parity).to_csv(out/"PRE2015_PARITY.csv",index=False)
    status(4,9,"pre-2015 parity PASS",markets=len(parity))

    rows=[];annual=[]
    for sv in survivors:
        s=sv["target"];L=int(sv["lookback_min"])
        y=targets[s][L]
        repl=(idx>=REPL_START)&(idx<REPL_END)
        raw=m04_event(zmap[s])&y.notna()&pd.Series(repl,index=idx)
        ep=cooldown_first(idx,raw.to_numpy(),COOLDOWN_MIN)
        yy=y.to_numpy(dtype=float)[ep];tt=idx[ep]
        fit=cluster_test(yy,tt.normalize().strftime("%Y-%m-%d").to_numpy(dtype=object))
        passed=bool(fit["n"]>=MIN_EPISODES and fit["days"]>=MIN_DAYS and fit["mean"]>0 and fit["p_one"]<=P_MAX)
        rows.append({
          "id":sv["id"],"target":s,"peer":sv["peer"],"relation":sv["relation"],
          "lookback_min":L,"horizon_min":int(sv["horizon_min"]),
          "episodes":fit["n"],"days":fit["days"],"mean_endpoint":fit["mean"],"median_endpoint":fit["median"],
          "positive_frac":fit["positive_frac"],"se":fit["se"],"t":fit["t"],"p_one":fit["p_one"],
          "discovery_mean_endpoint":sv["discovery_mean_endpoint"],"replication_pass":passed
        })
        for yv in [2015,2016,2017]:
            ym=(tt.year==yv)
            vals=yy[ym]
            annual.append({
              "id":sv["id"],"year":yv,"episodes":int(len(vals)),
              "mean_endpoint":float(np.mean(vals)) if len(vals) else np.nan,
              "median_endpoint":float(np.median(vals)) if len(vals) else np.nan,
              "positive_frac":float(np.mean(vals>0)) if len(vals) else np.nan
            })
    R=pd.DataFrame(rows);A=pd.DataFrame(annual)
    R.to_csv(out/"REPLICATION_RESULTS.csv",index=False)
    A.to_csv(out/"REPLICATION_YEARLY.csv",index=False)
    status(5,9,"six frozen variants scored",survivors=int(R["replication_pass"].sum()))

    frozen=R[R["replication_pass"]].copy()
    frozen.to_csv(out/"FROZEN_REPLICATION_SURVIVORS.csv",index=False)
    fsha=sha256(out/"FROZEN_REPLICATION_SURVIVORS.csv")
    write_json(out/"REPLICATION_FREEZE_RECEIPT.json",{
      "run_id":rid,"status":"REPLICATION_FROZEN_BEFORE_2018",
      "tested":6,"survivors":int(len(frozen)),"sha256":fsha,
      "2018_plus_accessed":False,"2023_2025_accessed":False,"2026_accessed":False
    })
    status(6,9,"replication freeze written before any 2018+")

    summary={
      "run_id":rid,"status":"COMPLETE_M04_2015_2017_REPLICATION",
      "engine_version":ENGINE_VERSION,"parent_discovery_run":spec["parent_discovery_run"],
      "parent_survivor_sha256":spec["parent_survivor_sha256"],
      "frozen_variants_tested":6,"valid_tests":int(((R["episodes"]>=MIN_EPISODES)&(R["days"]>=MIN_DAYS)).sum()),
      "replication_survivors":int(R["replication_pass"].sum()),
      "survivors":R.loc[R["replication_pass"],"id"].tolist(),
      "frozen_replication_survivor_sha256":fsha,
      "pre2015_parity_pass":bool(all(x["pass"] for x in parity)),
      "2018_plus_accessed":False,"2023_2025_accessed":False,"2026_accessed":False,
      "next":"IF SURVIVORS: PREREGISTER 2018-2022 VALIDATION EXACTLY; ELSE CLOSE M04 LINEAGE"
    }
    write_json(out/"RUN_RECEIPT.json",summary)
    write_json(out/"RUNTIME_PROVENANCE.json",{
      "engine_version":ENGINE_VERSION,"spec_sha256":sha256(specp),
      "raw_years":[2011,2012,2013,2014,2015,2016,2017],
      "replication_window":"2015-2017","forbidden_from":"2018-01-01",
      "cooldown_min":COOLDOWN_MIN,"min_episodes":MIN_EPISODES,"min_days":MIN_DAYS,"p_max":P_MAX
    })
    status(7,9,"receipt written")
    status(8,9,"2018+ remains unopened")
    status(9,9,"DONE")

    print("\n=== M04 REPLICATION RECEIPT ===")
    print(json.dumps(summary,indent=2))
    print("\n=== PRE-2015 PARITY ===")
    print(pd.DataFrame(parity).to_string(index=False))
    print("\n=== REPLICATION RESULTS ===")
    print(R.to_string(index=False))
    print("\n=== YEARLY ===")
    print(A.to_string(index=False))
    print("\nRUN:",out)

if __name__=="__main__":
    main()
