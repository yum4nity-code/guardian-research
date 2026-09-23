from pathlib import Path
import argparse, hashlib, json, math, time
import numpy as np
import pandas as pd
from scipy.stats import t as student_t

ENGINE_VERSION="M5-MOTION-TOPOLOGY-M01-M08-DISCOVERY-1.0"
DISCOVERY_START=pd.Timestamp("2012-01-01")
DISCOVERY_END=pd.Timestamp("2015-01-01")
FORBIDDEN_DATE=pd.Timestamp("2015-01-01")
EXPECTED_VARIANTS=291
SCALES=[15,30,60]
ZMIN=250
COOLDOWN_MIN=30
MIN_EPISODES=200
MIN_DAYS=120
BH_Q=0.05

MARKETS=["XAUUSD","XAGUSD","UDXUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","SPXUSD","NSXUSD","WTIUSD","BCOUSD"]

EDGES=[
 ("XAUUSD","XAGUSD", 1),
 ("XAUUSD","UDXUSD",-1),
 ("XAGUSD","UDXUSD",-1),
 ("USDCAD","WTIUSD",-1),
 ("USDCAD","BCOUSD",-1),
 ("WTIUSD","BCOUSD", 1),
 ("NSXUSD","SPXUSD", 1),
 ("EURUSD","UDXUSD",-1),
 ("GBPUSD","UDXUSD",-1),
 ("AUDUSD","UDXUSD",-1),
 ("USDJPY","UDXUSD", 1),
 ("USDCHF","UDXUSD", 1),
 ("USDCAD","UDXUSD", 1),
]

TURN_CLUSTER_TARGETS=["XAUUSD","XAGUSD","UDXUSD","USDCAD","WTIUSD","BCOUSD"]

PAIR_CACHE_ORDER=[
 ("XAUUSD","XAGUSD"),("XAUUSD","UDXUSD"),("XAGUSD","UDXUSD"),
 ("USDCAD","WTIUSD"),("USDCAD","BCOUSD"),("WTIUSD","BCOUSD"),
 ("NSXUSD","SPXUSD"),("UDXUSD","EURUSD"),("UDXUSD","GBPUSD"),
 ("UDXUSD","AUDUSD"),("UDXUSD","USDJPY"),("UDXUSD","USDCHF"),("UDXUSD","USDCAD"),
]

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for ch in iter(lambda:f.read(1024*1024),b""):
            h.update(ch)
    return h.hexdigest()

def latest_cache(root):
    base=root/"Research"/"Autonomous"/"guardian_m5_motion_topology_v1_1"
    runs=[p for p in sorted(base.glob("GEFM5T-*")) if (p/"RUN_RECEIPT.json").exists() and (p/"CACHE_MANIFEST.json").exists()]
    if not runs: raise RuntimeError("No completed M5 topology V1.1 cache")
    run=runs[-1]
    rc=json.loads((run/"RUN_RECEIPT.json").read_text())
    if rc.get("alpha_tests")!=0 or rc.get("edge_trials")!=0:
        raise RuntimeError("Refuse cache with prior alpha/edge trials")
    if rc.get("2015_plus_outcomes_accessed"):
        raise RuntimeError("Refuse cache that opened 2015+")
    return run

def causal_z(s,min_periods=ZMIN):
    s=pd.to_numeric(s,errors="coerce").astype(float)
    mu=s.expanding(min_periods=min_periods).mean().shift(1)
    sd=s.expanding(min_periods=min_periods).std().shift(1).replace(0,np.nan)
    return (s-mu)/sd

def rolling_beta(a,b,window=240,minp=120):
    a=pd.to_numeric(a,errors="coerce").astype(float)
    b=pd.to_numeric(b,errors="coerce").astype(float)
    cov=a.rolling(window,min_periods=minp).cov(b).shift(1)
    var=b.rolling(window,min_periods=minp).var().shift(1).replace(0,np.nan)
    return cov/var

def cooldown_first(times,raw,minutes=COOLDOWN_MIN):
    raw=np.asarray(raw,dtype=bool)
    out=np.zeros(len(raw),dtype=bool)
    last=None
    cd=pd.Timedelta(minutes=minutes)
    for i in np.flatnonzero(raw):
        t=times[i]
        if last is None or t-last>=cd:
            out[i]=True;last=t
    return out

def cluster_intercept_test(y,clusters):
    y=np.asarray(y,dtype=float)
    clusters=np.asarray(clusters,dtype=object)
    good=np.isfinite(y)&pd.notna(clusters)
    y=y[good];clusters=clusters[good]
    n=len(y)
    if n<2:
        return {"n":n,"clusters":0,"mean":np.nan,"se":np.nan,"t":np.nan,"p_one":np.nan,"median":np.nan,"positive_frac":np.nan}
    codes,_=pd.factorize(clusters,sort=False)
    uniq=np.unique(codes);g=len(uniq)
    if g<2:
        return {"n":n,"clusters":g,"mean":float(np.mean(y)),"se":np.nan,"t":np.nan,"p_one":np.nan,"median":float(np.median(y)),"positive_frac":float(np.mean(y>0))}
    mean=float(np.mean(y))
    resid=y-mean
    meat=0.0
    for c in uniq:
        meat+=float(np.sum(resid[codes==c]))**2
    vcov=(g/(g-1.0))*meat/(n*n)
    se=math.sqrt(vcov) if np.isfinite(vcov) and vcov>0 else np.nan
    tv=mean/se if np.isfinite(se) and se>0 else np.nan
    p_one=float(student_t.sf(tv,df=max(g-1,1))) if np.isfinite(tv) and mean>0 else 1.0 if np.isfinite(mean) else np.nan
    return {"n":n,"clusters":g,"mean":mean,"se":se,"t":float(tv) if np.isfinite(tv) else np.nan,
            "p_one":p_one,"median":float(np.median(y)),"positive_frac":float(np.mean(y>0))}

def bh_qvalues(p):
    p=np.asarray(p,dtype=float)
    q=np.full(len(p),np.nan)
    ok=np.flatnonzero(np.isfinite(p))
    if not len(ok): return q
    order=ok[np.argsort(p[ok],kind="mergesort")]
    m=len(order);running=1.0
    for rev,idx in enumerate(order[::-1],1):
        rank=m-rev+1
        val=min(1.0,p[idx]*m/rank)
        running=min(running,val)
        q[idx]=running
    return q

def pair_cache_prefix(a,b):
    if (a,b) in PAIR_CACHE_ORDER:return f"{a}__{b}"
    if (b,a) in PAIR_CACHE_ORDER:return f"{b}__{a}"
    raise RuntimeError(f"Pair not frozen in cache graph: {a},{b}")

def load_all(cache):
    manifest=json.loads((cache/"CACHE_MANIFEST.json").read_text())
    states={}
    targets={}
    for s in MARKETS:
        st=pd.read_parquet(Path(manifest["market_files"][s]["state"]))
        st.index=pd.to_datetime(st.index)
        if st.index.max()>=FORBIDDEN_DATE:
            # state cache may include 2014-12-31 23:55 only; hard fail if later.
            bad=st.index[st.index>=FORBIDDEN_DATE]
            if len(bad): raise RuntimeError(f"2015+ state rows in cache for {s}")
        tg=pd.read_parquet(Path(manifest["target_files"][s]))
        tg.index=pd.to_datetime(tg.index)
        if len(tg.index) and tg.index.max()>=FORBIDDEN_DATE:
            raise RuntimeError(f"2015+ target rows in cache for {s}")
        states[s]=st
        targets[s]=tg
    cross=pd.read_parquet(Path(manifest["cross_state_path"]))
    cross.index=pd.to_datetime(cross.index)
    if len(cross.index[cross.index>=FORBIDDEN_DATE]):
        raise RuntimeError("2015+ cross-state rows in cache")
    return manifest,states,targets,cross

def common_index(states):
    idx=states[MARKETS[0]].index
    for s in MARKETS[1:]:
        if not idx.equals(states[s].index):
            raise RuntimeError("State indexes differ")
    return idx

def build_objects(states,cross):
    idx=common_index(states)
    move_z={s:{} for s in MARKETS}
    rv30_z={}
    for s in MARKETS:
        for L in SCALES:
            move_z[s][L]=causal_z(states[s][f"ret_{L}m"])
        rv30_z[s]=causal_z(states[s]["rv_30m"])

    residual_z={}
    corr_break_z={}
    for target,peer,rel in EDGES:
        key=(target,peer,rel)
        rt=pd.to_numeric(states[target]["ret_5m"],errors="coerce")
        rp=rel*pd.to_numeric(states[peer]["ret_5m"],errors="coerce")
        beta=rolling_beta(rt,rp)
        resid=rt-beta*rp
        residual_z[key]=causal_z(resid)

        pref=pair_cache_prefix(target,peer)
        cb=pd.to_numeric(cross[f"{pref}__corr_break"],errors="coerce")
        corr_break_z[key]=causal_z(cb)
    return idx,move_z,rv30_z,residual_z,corr_break_z

def adjacency():
    out={s:[] for s in MARKETS}
    for t,p,r in EDGES:
        out[t].append((p,r))
        out[p].append((t,r))
    return out

def endpoint(targets,s,L):
    col=f"endpoint_score_{L}m_{L}m"
    y=targets[s][col].reindex(targets[s].index)
    return y

def raw_event_M01(states,move_z,target,peer,rel,L):
    tz=move_z[target][L]; pz=move_z[peer][L]
    tr=states[target][f"ret_{L}m"]; ta=states[target]["accel_5_vs_15"]
    pa=states[peer]["accel_5_vs_15"]
    sign=np.sign(tr)
    return (
        tz.abs().ge(1.5) &
        pz.abs().ge(1.0) &
        (np.sign(tz)==np.sign(rel*pz)) &
        ((sign*ta)<0) &
        ((sign*rel*pa)<0)
    )

def raw_event_M02(states,move_z,target,peer,rel,L):
    tz=move_z[target][L]; pz=move_z[peer][L]
    tr=states[target][f"ret_{L}m"]; pr=states[peer][f"ret_{L}m"]
    t5=states[target]["ret_5m"]; p5=states[peer]["ret_5m"]
    s=np.sign(tr)
    return (
        tz.abs().ge(1.5) &
        pz.abs().ge(1.0) &
        (np.sign(tr)==np.sign(rel*pr)) &
        (np.sign(t5)==s) &
        (np.sign(rel*p5)!=s)
    )

def raw_event_M03(residual_z,key):
    z=residual_z[key]
    prev_ext=z.abs().shift(1).rolling(3,min_periods=1).max()
    return prev_ext.ge(1.5) & z.abs().lt(1.0) & (z.abs()<z.abs().shift(1))

def raw_event_M04(corr_break_z,key):
    z=corr_break_z[key]
    prev_ext=z.abs().shift(1).rolling(3,min_periods=1).max()
    return prev_ext.ge(1.5) & z.abs().lt(1.0) & (z.abs()<z.abs().shift(1))

def raw_event_M05(states,cross,move_z,target,L):
    z=move_z[target][L]
    r=states[target][f"ret_{L}m"]
    breadth=pd.to_numeric(cross["breadth_positive_frac_5m"],errors="coerce")
    return z.abs().ge(1.5) & (((r>0)&(breadth<0.5)) | ((r<0)&(breadth>0.5)))

def precursor(states,move_z,s,L):
    return move_z[s][L].abs().ge(1.0) & (np.sign(states[s]["ret_5m"])!=np.sign(states[s]["ret_15m"]))

def raw_event_M06(states,move_z,target,L,adj):
    tr=states[target][f"ret_{L}m"]
    tsign=np.sign(tr)
    target_prec=precursor(states,move_z,target,L).rolling(2,min_periods=1).max().astype(bool)
    count=target_prec.astype(int)
    for peer,rel in adj[target]:
        pprec=precursor(states,move_z,peer,L)
        aligned=(np.sign(rel*states[peer][f"ret_{L}m"])==tsign)
        active=(pprec&aligned).rolling(2,min_periods=1).max().fillna(0).astype(bool)
        count=count+active.astype(int)
    return move_z[target][L].abs().ge(1.0) & (count>=2)

def raw_event_M07(states,move_z,target,peer,rel,L):
    tr=states[target][f"ret_{L}m"]
    pr=states[peer][f"ret_{L}m"]
    ts=np.sign(tr)
    target_now=precursor(states,move_z,target,L)
    peer_turn=precursor(states,move_z,peer,L)
    peer_prior=peer_turn.shift(1).rolling(3,min_periods=1).max().fillna(0).astype(bool)
    return (
        move_z[target][L].abs().ge(1.0) &
        (np.sign(states[target]["ret_5m"])==ts) &
        (np.sign(rel*pr)==ts) &
        peer_prior &
        (~target_now)
    )

def raw_event_M08(states,move_z,rv30_z,target,L):
    return (
        move_z[target][L].abs().ge(1.5) &
        rv30_z[target].ge(1.0) &
        states[target]["failure_extend_after_shock"].astype(bool)
    )

def score_variant(family,variant,target,L,raw,targets,idx,meta):
    y=targets[target][f"endpoint_score_{L}m_{L}m"].reindex(idx)
    eligible=y.notna()
    raw=pd.Series(raw,index=idx).fillna(False).astype(bool)&eligible
    ep=cooldown_first(idx,raw.to_numpy(),COOLDOWN_MIN)
    yy=y.to_numpy(dtype=float)[ep]
    tt=idx[ep]
    clusters=tt.normalize().strftime("%Y-%m-%d").to_numpy(dtype=object)
    fit=cluster_intercept_test(yy,clusters)
    valid=bool(fit["n"]>=MIN_EPISODES and fit["clusters"]>=MIN_DAYS and np.isfinite(fit["p_one"]))
    return {
      "family":family,"variant":variant,"target":target,"lookback_min":L,"horizon_min":L,
      "episodes":fit["n"],"days":fit["clusters"],"mean_endpoint":fit["mean"],"median_endpoint":fit["median"],
      "positive_frac":fit["positive_frac"],"t":fit["t"],"p_one":fit["p_one"],"valid":valid,
      "meta_json":json.dumps(meta,sort_keys=True)
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root);repo=root/"guardian-research"
    specp=repo/"research"/"campaigns"/"GUARDIAN_M5_M01_M08_DISCOVERY_SPEC_2026_09_23.json"
    if not specp.exists():raise RuntimeError("Missing frozen M01-M08 spec")
    spec=json.loads(specp.read_text())
    if spec.get("status")!="FROZEN_BEFORE_OUTCOME_ASSOCIATION":raise RuntimeError("Discovery spec not frozen")
    if int(spec.get("expected_variants",0))!=EXPECTED_VARIANTS:raise RuntimeError("Unexpected expected variant count")

    cache=latest_cache(root)
    base=root/"Research"/"Autonomous"/"guardian_m5_motion_topology_m01_m08"
    base.mkdir(parents=True,exist_ok=True)
    rid="GEFM5D-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    out=base/rid;out.mkdir(parents=True,exist_ok=False)
    t0=time.time()
    def status(i,n,msg,**extra):
        p={"run_id":rid,"engine_version":ENGINE_VERSION,"step":i,"steps":n,"elapsed_s":round(time.time()-t0,1),"message":msg,**extra}
        write_json(out/"LIVE_STATUS.json",p)
        tail=" | ".join(f"{k}={v}" for k,v in extra.items())
        print(f"[M5-DISCOVERY] {i}/{n} | {msg}"+(f" | {tail}" if tail else ""),flush=True)

    status(1,10,"load frozen V1.1 cache; 2015+ forbidden",cache=cache.name)
    manifest,states,targets,cross=load_all(cache)
    idx=common_index(states)
    if idx.max()>=FORBIDDEN_DATE:raise RuntimeError("2015+ index reached discovery engine")
    cross=cross.reindex(idx)
    status(2,10,"cache loaded",rows=len(idx),cross_features=cross.shape[1])

    idx,move_z,rv30_z,residual_z,corr_break_z=build_objects(states,cross)
    adj=adjacency()
    status(3,10,"causal discovery objects built")

    rows=[]
    # M01-M04 + M07 directed-edge families
    for target,peer,rel in EDGES:
        key=(target,peer,rel)
        for L in SCALES:
            rows.append(score_variant("M01",f"{target}<-{peer}|rel{rel:+d}|L{L}",target,L,
                         raw_event_M01(states,move_z,target,peer,rel,L),targets,idx,
                         {"peer":peer,"relation":rel}))
            rows.append(score_variant("M02",f"{target}<-{peer}|rel{rel:+d}|L{L}",target,L,
                         raw_event_M02(states,move_z,target,peer,rel,L),targets,idx,
                         {"peer":peer,"relation":rel}))
            rows.append(score_variant("M03",f"{target}<-{peer}|rel{rel:+d}|L{L}",target,L,
                         raw_event_M03(residual_z,key),targets,idx,
                         {"peer":peer,"relation":rel}))
            rows.append(score_variant("M04",f"{target}<-{peer}|rel{rel:+d}|L{L}",target,L,
                         raw_event_M04(corr_break_z,key),targets,idx,
                         {"peer":peer,"relation":rel}))
            rows.append(score_variant("M07",f"{target}<-{peer}|rel{rel:+d}|L{L}",target,L,
                         raw_event_M07(states,move_z,target,peer,rel,L),targets,idx,
                         {"peer":peer,"relation":rel}))
    status(4,10,"M01-M04/M07 variants scored",rows=len(rows))

    # M05
    for target in MARKETS:
        for L in SCALES:
            rows.append(score_variant("M05",f"{target}|L{L}",target,L,
                         raw_event_M05(states,cross,move_z,target,L),targets,idx,{}))
    status(5,10,"M05 breadth divergence scored",rows=len(rows))

    # M06
    for target in TURN_CLUSTER_TARGETS:
        for L in SCALES:
            rows.append(score_variant("M06",f"{target}|L{L}",target,L,
                         raw_event_M06(states,move_z,target,L,adj),targets,idx,
                         {"neighbors":[x[0] for x in adj[target]]}))
    status(6,10,"M06 turn clusters scored",rows=len(rows))

    # M08
    for target in MARKETS:
        for L in SCALES:
            rows.append(score_variant("M08",f"{target}|L{L}",target,L,
                         raw_event_M08(states,move_z,rv30_z,target,L),targets,idx,{}))
    if len(rows)!=EXPECTED_VARIANTS:raise RuntimeError(f"Materialized {len(rows)} != {EXPECTED_VARIANTS}")
    status(7,10,"all preregistered variants materialized",variants=len(rows))

    D=pd.DataFrame(rows)
    D["bh_q"]=np.nan
    D["bh_pass"]=False
    for fam,g in D.groupby("family"):
        ix=g.index.to_numpy()
        p=np.where(g["valid"].to_numpy(bool),g["p_one"].to_numpy(float),np.nan)
        q=bh_qvalues(p)
        D.loc[ix,"bh_q"]=q
        D.loc[ix,"bh_pass"]=g["valid"].to_numpy(bool)&(q<=BH_Q)&(g["mean_endpoint"].to_numpy(float)>0)
    D.to_csv(out/"DISCOVERY_ALL.csv",index=False)

    survivors=D[D["bh_pass"]].copy()
    survivors.to_csv(out/"FROZEN_DISCOVERY_SURVIVORS.csv",index=False)
    surv_sha=sha256(out/"FROZEN_DISCOVERY_SURVIVORS.csv")
    write_json(out/"DISCOVERY_FREEZE_RECEIPT.json",{
      "run_id":rid,"status":"DISCOVERY_FROZEN_BEFORE_2015",
      "survivors":int(len(survivors)),"sha256":surv_sha,
      "2015_plus_outcomes_accessed":False,"2018_plus_accessed":False,
      "2023_2025_accessed":False,"2026_accessed":False
    })

    summary=[]
    for fam in [f"M0{i}" for i in range(1,9)]:
        g=D[D["family"]==fam]
        summary.append({
          "family":fam,"predeclared_tests":len(g),"valid_tests":int(g["valid"].sum()),
          "bh_discoveries":int(g["bh_pass"].sum()),
          "min_episodes":int(g["episodes"].min()) if len(g) else 0,
          "max_episodes":int(g["episodes"].max()) if len(g) else 0
        })
    S=pd.DataFrame(summary);S.to_csv(out/"FAMILY_SUMMARY.csv",index=False)
    status(8,10,"BH applied within family and discovery freeze written",survivors=len(survivors))

    write_json(out/"RUNTIME_PROVENANCE.json",{
      "run_id":rid,"engine_version":ENGINE_VERSION,"cache_run":cache.name,
      "frozen_spec_sha256":sha256(specp),"expected_variants":EXPECTED_VARIANTS,
      "discovery_window":"2012-2014","cooldown_min":COOLDOWN_MIN,
      "min_episodes":MIN_EPISODES,"min_days":MIN_DAYS,"bh_q":BH_Q,
      "2015_plus_outcomes_accessed":False,"2018_plus_accessed":False,
      "2023_2025_accessed":False,"2026_accessed":False
    })
    receipt={
      "run_id":rid,"status":"COMPLETE_M5_M01_M08_DISCOVERY",
      "engine_version":ENGINE_VERSION,"cache_run":cache.name,
      "predeclared_variants":EXPECTED_VARIANTS,"materialized_variants":len(D),
      "valid_tests":int(D["valid"].sum()),"bh_discoveries":int(D["bh_pass"].sum()),
      "discoveries_by_family":{r.family:int(r.bh_discoveries) for r in S.itertuples()},
      "frozen_survivor_sha256":surv_sha,
      "2015_plus_outcomes_accessed":False,"2018_plus_accessed":False,
      "2023_2025_accessed":False,"2026_accessed":False,
      "next":"IF SURVIVORS: PREREGISTER 2015-2017 REPLICATION EXACTLY; ELSE CLOSE M01-M08 DISCOVERY LINEAGES"
    }
    write_json(out/"RUN_RECEIPT.json",receipt)
    status(9,10,"receipt written; 2015+ remains unopened")
    status(10,10,"DONE")

    print("\n=== M5 M01-M08 DISCOVERY RECEIPT ===")
    print(json.dumps(receipt,indent=2))
    print("\n=== FAMILY SUMMARY ===")
    print(S.to_string(index=False))
    print("\n=== FROZEN DISCOVERY SURVIVORS ===")
    if len(survivors):
        print(survivors[["family","variant","target","lookback_min","episodes","days","mean_endpoint","median_endpoint","positive_frac","p_one","bh_q"]].to_string(index=False))
    else:
        print("NONE")
    print("\nRUN:",out)

if __name__=="__main__":
    main()
