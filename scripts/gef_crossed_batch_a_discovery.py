from pathlib import Path
import argparse, hashlib, json, math, re, time
import numpy as np
import pandas as pd
from scipy.stats import t as student_t

ENGINE_VERSION="BATCH-A-DISCOVERY-1.1"
EXPECTED_VARIANTS=66
HORIZONS=[60,120,240]
TRAIN_START=pd.Timestamp("2010-01-01")
TRAIN_END=pd.Timestamp("2013-01-01")
HOLD_START=pd.Timestamp("2013-01-01")
HOLD_END=pd.Timestamp("2014-01-01")
BH_Q=0.05
HOLD_P_ONE=0.10
FAST_Z_MIN=250
SLOW_Z_MIN=126
BETA_WINDOW=480
BETA_MIN=240
EVENT_Z=1.5
COOLDOWN_MIN=240
MIN_TRAIN_N=120
MIN_TRAIN_CLUSTERS=80
MIN_HOLD_N=40
MIN_HOLD_CLUSTERS=20

CFTC_MAP={
"XAUUSD":"GOLD - COMMODITY EXCHANGE INC.",
"XAGUSD":"SILVER - COMMODITY EXCHANGE INC.",
"EURUSD":"EURO FX - CHICAGO MERCANTILE EXCHANGE",
"GBPUSD":"BRITISH POUND STERLING - CHICAGO MERCANTILE EXCHANGE",
"USDJPY":"JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE",
"AUDUSD":"AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",
"USDCAD":"CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",
"USDCHF":"SWISS FRANC - CHICAGO MERCANTILE EXCHANGE",
"SPXUSD":"E-MINI S&P 500 STOCK INDEX - CHICAGO MERCANTILE EXCHANGE",
"NSXUSD":"NASDAQ-100 STOCK INDEX (MINI) - CHICAGO MERCANTILE EXCHANGE",
"WTIUSD":"CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE",
}

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def normalize_dt(s):
    x=pd.to_datetime(s,errors="coerce")
    try:
        if getattr(x.dt,"tz",None) is not None:
            x=x.dt.tz_localize(None)
    except Exception:
        pass
    return x

def causal_z(s,min_periods):
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

def cooldown_mask(times,z,threshold=EVENT_Z,cooldown_min=COOLDOWN_MIN):
    z=np.asarray(z,dtype=float)
    out=np.zeros(len(z),dtype=bool)
    last=None
    cd=pd.Timedelta(minutes=cooldown_min)
    for i in np.flatnonzero(np.isfinite(z)&(np.abs(z)>=threshold)):
        t=times[i]
        if last is None or t-last>=cd:
            out[i]=True
            last=t
    return out

def aligned_mask(times,h):
    minute=(times.view("int64")//60_000_000_000).astype(np.int64)
    return (minute%int(h))==0

def period_mask(times,start,end,h):
    return np.asarray((times>=start)&(times<end)&((times+pd.Timedelta(minutes=int(h)))<=end))

def cluster_ols(y,X,clusters,coef_index):
    y=np.asarray(y,dtype=float)
    X=np.asarray(X,dtype=float)
    clusters=np.asarray(clusters)
    good=np.isfinite(y)&np.all(np.isfinite(X),axis=1)&pd.notna(clusters)
    y=y[good];X=X[good];clusters=clusters[good]
    n=len(y);k=X.shape[1]
    if n<=k:
        return {"n":n,"clusters":0,"coef":np.nan,"se":np.nan,"t":np.nan,"p_two":np.nan}
    codes,_=pd.factorize(clusters,sort=False)
    uniq=np.unique(codes);g=len(uniq)
    if g<2:
        return {"n":n,"clusters":g,"coef":np.nan,"se":np.nan,"t":np.nan,"p_two":np.nan}
    xtx=X.T@X
    if np.linalg.matrix_rank(xtx)<k:
        return {"n":n,"clusters":g,"coef":np.nan,"se":np.nan,"t":np.nan,"p_two":np.nan}
    inv=np.linalg.inv(xtx)
    beta=inv@(X.T@y)
    resid=y-X@beta
    meat=np.zeros((k,k),dtype=float)
    for c in uniq:
        sel=codes==c
        score=X[sel].T@resid[sel]
        meat+=np.outer(score,score)
    if g<=1 or n<=k:
        return {"n":n,"clusters":g,"coef":float(beta[coef_index]),"se":np.nan,"t":np.nan,"p_two":np.nan}
    corr=(g/(g-1.0))*((n-1.0)/(n-k))
    vcov=corr*(inv@meat@inv)
    vv=float(vcov[coef_index,coef_index])
    se=math.sqrt(max(vv,0.0)) if np.isfinite(vv) else np.nan
    coef=float(beta[coef_index])
    if not np.isfinite(se) or se<=0:
        return {"n":n,"clusters":g,"coef":coef,"se":se,"t":np.nan,"p_two":np.nan}
    tv=coef/se
    p=2*student_t.sf(abs(tv),df=max(g-1,1))
    return {"n":n,"clusters":g,"coef":coef,"se":se,"t":float(tv),"p_two":float(p)}

def bh_qvalues(p):
    p=np.asarray(p,dtype=float)
    q=np.full(len(p),np.nan)
    ok=np.flatnonzero(np.isfinite(p))
    if not len(ok):
        return q
    order=ok[np.argsort(p[ok],kind="mergesort")]
    m=len(order);running=1.0
    for rev,idx in enumerate(order[::-1],1):
        rank=m-rev+1
        val=min(1.0,p[idx]*m/rank)
        running=min(running,val)
        q[idx]=running
    return q

def report_rate_features(S):
    found={}
    for ten in [5,10,30]:
        pat=re.compile(rf"^rates_yields_REAL_.*(?:^|_){ten}YEAR_d1$",re.I)
        xs=[c for c in S.columns if pat.search(str(c))]
        if not xs:
            xs=[c for c in S.columns if str(c).startswith("rates_yields_REAL_") and f"{ten}YEAR" in str(c) and str(c).endswith("_d1")]
        if len(xs)!=1:
            raise RuntimeError(f"Expected one REAL {ten}Y d1 feature; got {xs}")
        found[ten]=xs[0]
    return found

def slow_to_hour(S,bridge,hour_pos,col,hour_times):
    vals=np.full(len(hour_pos),np.nan,dtype=float)
    b=bridge[hour_pos]
    ok=b>=0
    raw=pd.to_numeric(S[col],errors="coerce").to_numpy(dtype=float)
    vals[ok]=raw[b[ok]]
    return pd.Series(vals,index=hour_times,name=col)

def rate_release_mask(S):
    level=[c for c in S.columns if str(c).startswith("rates_yields_") and str(c).endswith("_level")]
    if not level:
        raise RuntimeError("No rate level columns for release-day detection")
    D=S[level].apply(pd.to_numeric,errors="coerce").resample("1D").last()
    changed=D.ne(D.shift(1)).any(axis=1)
    if len(changed):
        changed.iloc[0]=False
    return changed

def causal_daily_release_z(hour_series,release_mask,hour_times):
    D=hour_series.resample("1D").last()
    rel=release_mask.reindex(D.index,fill_value=False)
    obs=D.where(rel)
    mu=obs.expanding(min_periods=SLOW_Z_MIN).mean().shift(1)
    sd=obs.expanding(min_periods=SLOW_Z_MIN).std().shift(1).replace(0,np.nan)
    z=(obs-mu)/sd
    z=z.ffill()
    vals=z.reindex(hour_times.normalize()).to_numpy(dtype=float)
    return pd.Series(vals,index=hour_times)

def load_cftc_market(root,sym):
    p=root/"DataLake"/"normalized"/"cftc_pre2023"/"CFTC_FUTURES_ONLY_2009_2013_CAUSAL_V82D.parquet"
    if not p.exists():
        raise RuntimeError(f"Missing CFTC causal file {p}")
    cols=["market","report_date","AVAILABLE_AT","noncomm_net_pct_oi"]
    d=pd.read_parquet(p,columns=cols)
    q=d[d["market"].astype(str)==CFTC_MAP[sym]].copy()
    if q.empty:
        raise RuntimeError(f"No CFTC rows for {sym}")
    q["AVAILABLE_AT"]=normalize_dt(q["AVAILABLE_AT"])
    q["report_date"]=normalize_dt(q["report_date"])
    q["noncomm_net_pct_oi"]=pd.to_numeric(q["noncomm_net_pct_oi"],errors="coerce")
    q=q.dropna(subset=["AVAILABLE_AT","report_date"]).sort_values("report_date").drop_duplicates("report_date",keep="last")
    # Exact V83 transform: current report is known at AVAILABLE_AT, so the
    # 52-report rolling standardization legitimately includes the current report.
    s=q["noncomm_net_pct_oi"]
    mu=s.rolling(52,min_periods=26).mean()
    sd=s.rolling(52,min_periods=26).std().replace(0,np.nan)
    q["noncomm_net_pct_oi_z52"]=(s-mu)/sd
    q=q.sort_values("AVAILABLE_AT").drop_duplicates("AVAILABLE_AT",keep="last")
    return q

def cftc_crowding_and_cluster(root,sym,hour_times):
    q=load_cftc_market(root,sym)
    base=pd.DataFrame({"decision_time":hour_times})
    z=pd.merge_asof(
        base,
        q[["AVAILABLE_AT","report_date","noncomm_net_pct_oi_z52"]],
        left_on="decision_time",
        right_on="AVAILABLE_AT",
        direction="backward",
    )
    crowd=pd.Series(
        pd.to_numeric(z["noncomm_net_pct_oi_z52"],errors="coerce").to_numpy(dtype=float),
        index=hour_times,
        name=f"cftc_{sym}_noncomm_net_pct_oi_z52",
    )
    clusters=z["report_date"].dt.strftime("%Y-%m-%d").to_numpy(dtype=object)
    return crowd,clusters

class Variant:
    def __init__(self,lineage,variant,horizon,y,X,primary_idx,event_mask,clusters,meta):
        self.lineage=lineage;self.variant=variant;self.horizon=int(horizon)
        self.y=np.asarray(y,dtype=float);self.X=np.asarray(X,dtype=float)
        self.primary_idx=int(primary_idx);self.event_mask=np.asarray(event_mask,dtype=bool)
        self.clusters=np.asarray(clusters,dtype=object);self.meta=meta

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=r"D:\MT5_Backtests")
    args=ap.parse_args()
    root=Path(args.root)
    repo=root/"guardian-research"
    spec=repo/"research"/"campaigns"/"GEF_BATCH_A_FROZEN_SPEC_2026_09_22.json"
    if not spec.exists():
        raise RuntimeError(f"Missing frozen spec {spec}")
    spec_obj=json.loads(spec.read_text(encoding="utf-8"))
    if spec_obj.get("status")!="FROZEN_BEFORE_COMPUTE":
        raise RuntimeError("Batch A spec is not frozen")

    base=root/"Research"/"Autonomous"/"guardian_crossed_batch_a_discovery"
    base.mkdir(parents=True,exist_ok=True)
    rid="GEFBA-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    out=base/rid;out.mkdir(parents=True,exist_ok=False)
    t0=time.time()
    def status(step,total,msg,**extra):
        payload={"run_id":rid,"engine_version":ENGINE_VERSION,"step":step,"steps":total,
                 "percent":round(step*100/total,1),"elapsed_s":round(time.time()-t0,1),
                 "message":msg,**extra}
        write_json(out/"LIVE_STATUS.json",payload)
        tail=" | ".join(f"{k}={v}" for k,v in extra.items())
        print(f"[BATCH-A] {step}/{total} {step*100/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

    status(1,12,"locate frozen V83B architecture; 2014+ forbidden")
    runs=sorted((root/"Research"/"Autonomous"/"guardian_edge_factory_v83b").glob("GEF83B-*"))
    runs=[p for p in runs if (p/"RUN_RECEIPT.json").exists() and (p/"REPAIRED_ARCHITECTURE_MANIFEST.json").exists()]
    if not runs:
        raise RuntimeError("No completed V83B architecture")
    v83b=runs[-1]
    receipt83=json.loads((v83b/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
    if receipt83.get("status")!="COMPLETE_V83_RATES_REPAIR":
        raise RuntimeError("Latest V83B not complete")
    manifest=json.loads((v83b/"REPAIRED_ARCHITECTURE_MANIFEST.json").read_text(encoding="utf-8"))

    S=pd.read_parquet(Path(manifest["slow_state_repaired_path"]))
    F=pd.read_parquet(Path(manifest["price_state_5m_path"]))
    Y=pd.read_parquet(Path(manifest["targets_5m_path"]))
    bridge=np.load(Path(manifest["bridge_path"]))
    S.index=pd.to_datetime(S.index);F.index=pd.to_datetime(F.index);Y.index=pd.to_datetime(Y.index)
    if F.index.max()>=pd.Timestamp("2014-01-01") or S.index.max()>=pd.Timestamp("2014-01-01") or Y.index.max()>=pd.Timestamp("2014-01-01"):
        raise RuntimeError("Batch A discovery source escapes 2010-2013 firewall")
    if len(bridge)!=len(F):
        raise RuntimeError("Slow-fast bridge length mismatch")
    status(2,12,"2010-2013 causal layers loaded",slow_features=S.shape[1],fast_features=F.shape[1],targets=Y.shape[1])

    hour_mask=(F.index.minute==0)&(F.index.second==0)
    hour_pos=np.flatnonzero(hour_mask)
    H=F.iloc[hour_pos].copy()
    H.index=pd.DatetimeIndex(H.index)
    YH=Y.reindex(H.index)
    times=H.index
    day_clusters=times.normalize().strftime("%Y-%m-%d").to_numpy(dtype=object)

    required_price=["XAUUSD","XAGUSD","UDXUSD","USDCAD","WTIUSD","BCOUSD","NSXUSD","SPXUSD",
                    "EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF"]
    for sym in required_price:
        for col in [f"price_{sym}_ret_60m"]:
            if col not in H.columns:
                raise RuntimeError(f"Missing fast feature {col}")
        for h in HORIZONS:
            tc=f"{sym}_fwd_{h}m"
            if tc not in YH.columns:
                raise RuntimeError(f"Missing target {tc}")
    status(3,12,"required price/target schema verified",hour_rows=len(H))

    rate_cols=report_rate_features(S)
    release_mask=rate_release_mask(S)
    rate_z={}
    for ten,col in rate_cols.items():
        hs=slow_to_hour(S,bridge,hour_pos,col,times)
        rate_z[ten]=causal_daily_release_z(hs,release_mask,times)
    status(4,12,"REAL 5Y/10Y/30Y d1 causal z objects built",rate_columns=rate_cols)

    # Common fast objects.
    rz={}
    for sym in required_price:
        rz[sym]=causal_z(H[f"price_{sym}_ret_60m"],FAST_Z_MIN)

    beta_xau_udx=rolling_beta(H["price_XAUUSD_ret_60m"],H["price_UDXUSD_ret_60m"])
    beta_cad_udx=rolling_beta(H["price_USDCAD_ret_60m"],H["price_UDXUSD_ret_60m"])
    beta_nsx_spx=rolling_beta(H["price_NSXUSD_ret_60m"],H["price_SPXUSD_ret_60m"])
    beta_xau_xag=rolling_beta(H["price_XAUUSD_ret_60m"],H["price_XAGUSD_ret_60m"])

    cur_nsx_spx=H["price_NSXUSD_ret_60m"]-beta_nsx_spx*H["price_SPXUSD_ret_60m"]
    z_nsx_spx=causal_z(cur_nsx_spx,FAST_Z_MIN)
    cur_xau_xag=H["price_XAUUSD_ret_60m"]-beta_xau_xag*H["price_XAGUSD_ret_60m"]
    z_xau_xag=causal_z(cur_xau_xag,FAST_Z_MIN)

    fx_signed=[
        -rz["EURUSD"],-rz["GBPUSD"],-rz["AUDUSD"],
        rz["USDJPY"],rz["USDCHF"],rz["USDCAD"]
    ]
    synthetic=pd.concat(fx_signed,axis=1).mean(axis=1,skipna=False)
    divergence=rz["UDXUSD"]-synthetic
    z_usd_breadth=causal_z(divergence,FAST_Z_MIN)

    ev_oil={s:cooldown_mask(times,rz[s].to_numpy(),EVENT_Z,COOLDOWN_MIN) for s in ["WTIUSD","BCOUSD"]}
    ev_breadth=cooldown_mask(times,z_usd_breadth.to_numpy(),EVENT_Z,COOLDOWN_MIN)
    ev_xau_xag=cooldown_mask(times,z_xau_xag.to_numpy(),EVENT_Z,COOLDOWN_MIN)
    status(5,12,"causal beta/residual/breadth objects built")

    variants=[]

    # P01: real-yield x USD pressure -> XAU residual future return.
    for ten in [5,10,30]:
        zr=rate_z[ten].to_numpy(dtype=float)
        zu=rz["UDXUSD"].to_numpy(dtype=float)
        X=np.column_stack([np.ones(len(times)),zr,zu,zr*zu])
        for h in HORIZONS:
            y=pd.to_numeric(YH[f"XAUUSD_fwd_{h}m"],errors="coerce").to_numpy(dtype=float) - \
              beta_xau_udx.to_numpy(dtype=float)*pd.to_numeric(YH[f"UDXUSD_fwd_{h}m"],errors="coerce").to_numpy(dtype=float)
            variants.append(Variant("P01",f"REAL{ten}YxUDX",h,y,X,3,np.ones(len(times),bool),day_clusters,
                                    {"real_tenor":ten,"rate_feature":rate_cols[ten]}))

    # P04: oil shock -> USD-residualized CAD.
    for leader in ["WTIUSD","BCOUSD"]:
        z=rz[leader].to_numpy(dtype=float)
        X=np.column_stack([np.ones(len(times)),z])
        for h in HORIZONS:
            y=pd.to_numeric(YH[f"USDCAD_fwd_{h}m"],errors="coerce").to_numpy(dtype=float) - \
              beta_cad_udx.to_numpy(dtype=float)*pd.to_numeric(YH[f"UDXUSD_fwd_{h}m"],errors="coerce").to_numpy(dtype=float)
            variants.append(Variant("P04",leader,h,y,X,1,ev_oil[leader],day_clusters,{"leader":leader}))

    # P06: NSX/SPX relative-value divergence x real-rate shock.
    zd=z_nsx_spx.to_numpy(dtype=float)
    for ten in [5,10,30]:
        zr=rate_z[ten].to_numpy(dtype=float)
        X=np.column_stack([np.ones(len(times)),zd,zr,zd*zr])
        for h in HORIZONS:
            y=pd.to_numeric(YH[f"NSXUSD_fwd_{h}m"],errors="coerce").to_numpy(dtype=float) - \
              beta_nsx_spx.to_numpy(dtype=float)*pd.to_numeric(YH[f"SPXUSD_fwd_{h}m"],errors="coerce").to_numpy(dtype=float)
            variants.append(Variant("P06",f"NSXSPXxREAL{ten}Y",h,y,X,3,np.ones(len(times),bool),day_clusters,
                                    {"real_tenor":ten,"rate_feature":rate_cols[ten]}))

    # P08: UDX vs synthetic-FX breadth divergence.
    zb=z_usd_breadth.to_numpy(dtype=float)
    Xb=np.column_stack([np.ones(len(times)),zb])
    for target in ["UDXUSD","XAUUSD","XAGUSD"]:
        for h in [60,120]:
            y=pd.to_numeric(YH[f"{target}_fwd_{h}m"],errors="coerce").to_numpy(dtype=float)
            variants.append(Variant("P08",f"BREADTH->{target}",h,y,Xb,1,ev_breadth,day_clusters,{"target":target}))

    # P11: XAU/XAG relative-value residual.
    zx=z_xau_xag.to_numpy(dtype=float)
    Xx=np.column_stack([np.ones(len(times)),zx])
    for h in HORIZONS:
        y=pd.to_numeric(YH[f"XAUUSD_fwd_{h}m"],errors="coerce").to_numpy(dtype=float) - \
          beta_xau_xag.to_numpy(dtype=float)*pd.to_numeric(YH[f"XAGUSD_fwd_{h}m"],errors="coerce").to_numpy(dtype=float)
        variants.append(Variant("P11","XAU_RESID_XAG",h,y,Xx,1,ev_xau_xag,day_clusters,{}))

    # P12: CFTC crowding x own-price shock.
    # Reconstruct the exact V83 z52 transform directly from the canonical V82D
    # CFTC source. V83 dedup_vectors() may legitimately remove an equivalent
    # carried state column from the final slow parquet; source semantics remain intact.
    for sym in CFTC_MAP:
        ccol=f"cftc_{sym}_noncomm_net_pct_oi_z52"
        crowd,report_clusters=cftc_crowding_and_cluster(root,sym,times)
        shock=rz[sym]
        ev=cooldown_mask(times,shock.to_numpy(),EVENT_Z,COOLDOWN_MIN)
        X=np.column_stack([np.ones(len(times)),crowd.to_numpy(dtype=float),shock.to_numpy(dtype=float),
                           crowd.to_numpy(dtype=float)*shock.to_numpy(dtype=float)])
        for h in HORIZONS:
            y=pd.to_numeric(YH[f"{sym}_fwd_{h}m"],errors="coerce").to_numpy(dtype=float)
            variants.append(Variant("P12",sym,h,y,X,3,ev,report_clusters,{"market":sym,"cftc_feature":ccol}))

    if len(variants)!=EXPECTED_VARIANTS:
        raise RuntimeError(f"Variant count mismatch expected={EXPECTED_VARIANTS} got={len(variants)}")
    status(6,12,"exact preregistered variant universe materialized",variants=len(variants))

    # Discovery only.
    discovery=[]
    model_by_key={}
    for i,v in enumerate(variants,1):
        mask=period_mask(times,TRAIN_START,TRAIN_END,v.horizon)&aligned_mask(times,v.horizon)&v.event_mask
        fit=cluster_ols(np.where(mask,v.y,np.nan),v.X,v.clusters,v.primary_idx)
        valid=bool(fit["n"]>=MIN_TRAIN_N and fit["clusters"]>=MIN_TRAIN_CLUSTERS and np.isfinite(fit["p_two"]))
        row={"lineage":v.lineage,"variant":v.variant,"horizon_min":v.horizon,
             "discovery_n":fit["n"],"discovery_clusters":fit["clusters"],
             "discovery_coef":fit["coef"],"discovery_coef_bp":fit["coef"]*1e4 if np.isfinite(fit["coef"]) else np.nan,
             "discovery_t":fit["t"],"discovery_p_two":fit["p_two"],"discovery_valid":valid,
             "meta_json":json.dumps(v.meta,sort_keys=True)}
        discovery.append(row)
        model_by_key[(v.lineage,v.variant,v.horizon)]=v
        if i==1 or i==len(variants) or i%10==0:
            print(f"[BATCH-A] discovery {i}/{len(variants)}",flush=True)

    D=pd.DataFrame(discovery)
    D["bh_q"]=np.nan
    for lin,g in D.groupby("lineage"):
        idx=g.index.to_numpy()
        p=np.where(g["discovery_valid"].to_numpy(bool),g["discovery_p_two"].to_numpy(float),np.nan)
        D.loc[idx,"bh_q"]=bh_qvalues(p)
    D["discovery_bh_pass"]=D["discovery_valid"]&(D["bh_q"]<=BH_Q)
    D.to_csv(out/"DISCOVERY_2010_2012_ALL.csv",index=False)
    status(7,12,"2010-2012 discovery + within-lineage BH complete",
           valid_tests=int(D["discovery_valid"].sum()),bh_survivors=int(D["discovery_bh_pass"].sum()))

    # Only BH discoveries may see 2013 holdout.
    hold_rows=[]
    for r in D[D["discovery_bh_pass"]].itertuples(index=False):
        v=model_by_key[(r.lineage,r.variant,int(r.horizon_min))]
        mask=period_mask(times,HOLD_START,HOLD_END,v.horizon)&aligned_mask(times,v.horizon)&v.event_mask
        fit=cluster_ols(np.where(mask,v.y,np.nan),v.X,v.clusters,v.primary_idx)
        sign=1 if r.discovery_coef>0 else -1
        same=bool(np.isfinite(fit["coef"]) and fit["coef"]!=0 and np.sign(fit["coef"])==sign)
        p_one=float(student_t.sf(abs(fit["t"]),df=max(fit["clusters"]-1,1))) if same and np.isfinite(fit["t"]) else np.nan
        passed=bool(fit["n"]>=MIN_HOLD_N and fit["clusters"]>=MIN_HOLD_CLUSTERS and same and np.isfinite(p_one) and p_one<=HOLD_P_ONE)
        hold_rows.append({
            "lineage":r.lineage,"variant":r.variant,"horizon_min":int(r.horizon_min),
            "discovery_coef_bp":float(r.discovery_coef_bp),"discovery_p_two":float(r.discovery_p_two),
            "discovery_bh_q":float(r.bh_q),"holdout_n":fit["n"],"holdout_clusters":fit["clusters"],
            "holdout_coef":fit["coef"],"holdout_coef_bp":fit["coef"]*1e4 if np.isfinite(fit["coef"]) else np.nan,
            "holdout_t":fit["t"],"holdout_p_one_frozen_sign":p_one,
            "same_sign_2013":same,"holdout_pass":passed,"meta_json":r.meta_json
        })
    HLD=pd.DataFrame(hold_rows)
    HLD.to_csv(out/"TEMPORAL_HOLDOUT_2013.csv",index=False)
    survivors=HLD[HLD["holdout_pass"]].copy() if len(HLD) else HLD.copy()
    survivors.to_csv(out/"FROZEN_PRE_REPLICATION_SURVIVORS.csv",index=False)
    status(8,12,"2013 temporal holdout complete",holdout_tested=len(HLD),survivors=len(survivors))

    # Lineage accounting.
    summaries=[]
    expected={"P01":9,"P04":6,"P06":9,"P08":6,"P11":3,"P12":33}
    for lin in expected:
        g=D[D["lineage"]==lin]
        hs=HLD[HLD["lineage"]==lin] if len(HLD) else HLD
        ss=survivors[survivors["lineage"]==lin] if len(survivors) else survivors
        summaries.append({
            "lineage":lin,"predeclared_tests":expected[lin],"materialized_tests":len(g),
            "valid_discovery_tests":int(g["discovery_valid"].sum()),
            "bh_discoveries":int(g["discovery_bh_pass"].sum()),
            "holdout_tested":len(hs),"temporal_survivors":len(ss)
        })
    SUM=pd.DataFrame(summaries)
    SUM.to_csv(out/"LINEAGE_SUMMARY.csv",index=False)
    status(9,12,"lineage accounting complete")

    runtime={
        "run_id":rid,"engine_version":ENGINE_VERSION,"source_v83b":v83b.name,
        "frozen_spec_sha256":sha256(spec),"resolved_real_rate_features":rate_cols,
        "variant_count":len(variants),"expected_variant_count":EXPECTED_VARIANTS,
        "train":"2010-2012","holdout":"2013",
        "2014_plus_market_returns_accessed":False,"2023_2025_accessed":False,"2026_accessed":False
    }
    write_json(out/"RUNTIME_PROVENANCE.json",runtime)
    status(10,12,"runtime provenance written")

    lineage_survivors={r.lineage:int(r.temporal_survivors) for r in SUM.itertuples()}
    receipt={
        "run_id":rid,
        "status":"COMPLETE_CROSSED_PHENOMENA_BATCH_A_DISCOVERY",
        "engine_version":ENGINE_VERSION,
        "source_v83b":v83b.name,
        "predeclared_variants":EXPECTED_VARIANTS,
        "valid_discovery_tests":int(D["discovery_valid"].sum()),
        "bh_discoveries":int(D["discovery_bh_pass"].sum()),
        "holdout_tested":int(len(HLD)),
        "temporal_survivors":int(len(survivors)),
        "survivors_by_lineage":lineage_survivors,
        "frozen_survivor_sha256":sha256(out/"FROZEN_PRE_REPLICATION_SURVIVORS.csv"),
        "2014_plus_market_returns_accessed":False,
        "2023_2025_accessed":False,
        "2026_accessed":False,
        "next":"IF SURVIVORS: PREREGISTER 2014-2017 REPLICATION WITHOUT RETUNING; ELSE CLOSE FAILED LINEAGES"
    }
    write_json(out/"RUN_RECEIPT.json",receipt)
    status(11,12,"receipt written",survivors=len(survivors))
    status(12,12,"DONE; 2014+ remains unopened")

    print("\n=== BATCH A RECEIPT ===")
    print(json.dumps(receipt,indent=2))
    print("\n=== BATCH A LINEAGE SUMMARY ===")
    print(SUM.to_string(index=False))
    print("\n=== BATCH A FROZEN PRE-REPLICATION SURVIVORS ===")
    if len(survivors):
        cols=["lineage","variant","horizon_min","discovery_coef_bp","discovery_bh_q",
              "holdout_n","holdout_clusters","holdout_coef_bp","holdout_p_one_frozen_sign"]
        print(survivors[cols].to_string(index=False))
    else:
        print("NONE")
    print("\nRUN:",out)

if __name__=="__main__":
    main()
