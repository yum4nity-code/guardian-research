from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import re
import tempfile
import time
import zipfile

import numpy as np
import pandas as pd

ENGINE_VERSION="V104.1"
STATE_Z=1.0
SLOW_MIN_PERIODS=500
GENERIC_COST_BP=1.0
DISCOVERY_Q=0.10
MAX_FROZEN=200
FORBIDDEN_YEAR=2023
MIN_TRAIN_N=120
MIN_HOLD_N=40
MIN_REP_N=60
MIN_VAL_N=80

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

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def bh_qvalues(pvals):
    p=np.asarray(pvals,dtype=np.float64)
    q=np.full(len(p),np.nan)
    finite=np.flatnonzero(np.isfinite(p))
    if not len(finite): return q
    order=finite[np.argsort(p[finite],kind="mergesort")]
    m=len(order); running=1.0
    for rev_rank,idx in enumerate(order[::-1],1):
        rank=m-rev_rank+1
        val=min(1.0,p[idx]*m/rank)
        running=min(running,val); q[idx]=running
    return q

def causal_states(series,min_periods,zcut=1.0):
    s=pd.to_numeric(series,errors="coerce")
    mu=s.expanding(min_periods=min_periods).mean().shift(1)
    sd=s.expanding(min_periods=min_periods).std().shift(1).replace(0,np.nan)
    z=((s-mu)/sd).to_numpy(dtype=np.float32)
    finite=np.isfinite(z)
    return finite&(z<=-zcut), finite&(z>=zcut)

def mean_bp(x):
    x=np.asarray(x,dtype=np.float64); x=x[np.isfinite(x)]
    return float(x.mean()*1e4) if len(x) else np.nan

def trimmed_best_mean_bp(x,pct):
    x=np.asarray(x,dtype=np.float64); x=x[np.isfinite(x)]
    if not len(x): return np.nan
    k=int(math.ceil(len(x)*pct))
    if k<=0: return mean_bp(x)
    if k>=len(x): return np.nan
    return mean_bp(np.sort(x)[:-k])

def remove_best_k_mean_bp(x,k):
    x=np.asarray(x,dtype=np.float64); x=x[np.isfinite(x)]
    if len(x)<=k: return np.nan
    return mean_bp(np.sort(x)[:-k])

def positive_year_fraction(times,vals):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,dtype=float)})
    d=d[np.isfinite(d["v"])].copy()
    if d.empty: return np.nan,{}
    d["year"]=d["t"].dt.year
    y=d.groupby("year")["v"].mean()*1e4
    return float((y>0).mean()),{str(int(k)):float(v) for k,v in y.items()}

def nonoverlap_mean_bp(times,vals,horizon_min):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,dtype=float)})
    d=d[np.isfinite(d["v"])].sort_values("t")
    keep=[]; next_allowed=None; gap=pd.Timedelta(minutes=int(horizon_min))
    for row in d.itertuples(index=False):
        if next_allowed is None or row.t>=next_allowed:
            keep.append(row.v); next_allowed=row.t+gap
    return mean_bp(keep),len(keep)

def metrics(times,vals,horizon_min,remove_best=0):
    vals=np.asarray(vals,dtype=np.float64)
    ok=np.isfinite(vals); vals=vals[ok]; times=pd.DatetimeIndex(times)[ok]
    pyf,yearly=positive_year_fraction(times,vals)
    no,nn=nonoverlap_mean_bp(times,vals,horizon_min)
    out={
      "n":int(len(vals)),"mean_bp":mean_bp(vals),
      "net1bp_mean_bp":mean_bp(vals)-GENERIC_COST_BP if len(vals) else np.nan,
      "median_bp":float(np.median(vals)*1e4) if len(vals) else np.nan,
      "win_rate_pct":float((vals>0).mean()*100) if len(vals) else np.nan,
      "positive_year_fraction":pyf,"yearly_mean_bp_json":json.dumps(yearly,sort_keys=True),
      "trim_best_1pct_mean_bp":trimmed_best_mean_bp(vals,.01),
      "trim_best_2pct_mean_bp":trimmed_best_mean_bp(vals,.02),
      "nonoverlap_mean_bp":no,"nonoverlap_n":int(nn)
    }
    if remove_best: out[f"remove_best_{remove_best}_mean_bp"]=remove_best_k_mean_bp(vals,remove_best)
    return out

def target_parts(target):
    m=re.fullmatch(r"([A-Z]+)_fwd_(\d+)m",str(target))
    if not m: raise RuntimeError(f"Unsupported target {target}")
    return m.group(1),int(m.group(2))

def load_m1(root,sym,start_year,end_year):
    if end_year>=FORBIDDEN_YEAR: raise RuntimeError("V104 refuses 2023+")
    parts=[]; skipped=[]
    for year in range(start_year,end_year+1):
        p=root/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
        if not p.exists():
            if year<=2012: skipped.append(year); continue
            raise RuntimeError(f"Missing required <=2022 price file {p}")
        d=pd.read_parquet(p)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        pc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None and isinstance(d.index,pd.DatetimeIndex):
            d=d.reset_index(); dc=d.columns[0]
        if dc is None or pc is None: raise RuntimeError(f"Bad price schema {p}")
        utc=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(hours=5)
        q=pd.DataFrame({"utc":utc,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
        q=q[q["utc"].dt.year.between(start_year,end_year)]; parts.append(q)
    if not parts: raise RuntimeError(f"No usable price for {sym}")
    if skipped: print(f"[GEF104] {sym} skipped legacy years {skipped}",flush=True)
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    return q.set_index("utc")["px"]

def build_target(P,grid,target):
    sym,mins=target_parts(target); k=mins//5
    raw=P[sym].shift(-k)/P[sym]-1
    y=np.array(raw.reindex(grid),dtype=np.float64,copy=True)
    minute=(grid.view("int64")//60_000_000_000).astype(np.int64)
    y[(minute%mins)!=0]=np.nan
    return y

def find_col(cols,needles):
    for c in cols:
        z=str(c).strip().lower()
        if any(n in z for n in needles): return c
    return None

def parse_report_date(d,cols):
    direct=find_col(cols,["report_date_as_mm_dd_yyyy","report date as mm dd yyyy","report_date_as_yyyy-mm-dd"])
    if direct is not None:
        return pd.to_datetime(d[direct],errors="coerce")
    compact=find_col(cols,["as_of_date_in_form_yymmdd","as of date in form yymmdd"])
    if compact is not None:
        s=d[compact].astype("string").str.replace(r"\.0$","",regex=True).str.zfill(6)
        return pd.to_datetime(s,format="%y%m%d",errors="coerce")
    return pd.Series(pd.NaT,index=d.index)

def load_cftc_normalized(root,end_year):
    if end_year>=FORBIDDEN_YEAR: raise RuntimeError("V104 refuses CFTC 2023+")
    src=root/"DataLake"/"raw"/"cftc"/"futures_only_reports"
    archives=[]
    year_hits={}
    for y in range(2009,end_year+1):
        aa=[p for p in sorted(src.glob("*.zip")) if str(y) in p.name and "excel" in p.name.lower()]
        if aa: archives.extend(aa); year_hits[y]=len(aa)
    missing=[y for y in range(2013,end_year+1) if y not in year_hits]
    if missing: raise RuntimeError(f"Missing required CFTC Excel archives for years {missing}")
    parts=[]
    for j,p in enumerate(dict.fromkeys(archives),1):
        with zipfile.ZipFile(p) as z:
            members=[m for m in z.namelist() if m.lower().endswith((".xls",".xlsx"))]
            for member in members:
                suffix=Path(member).suffix
                with tempfile.NamedTemporaryFile(suffix=suffix,delete=False) as tf:
                    tf.write(z.read(member)); tmp=tf.name
                try:
                    d=pd.read_excel(tmp)
                finally:
                    try: os.unlink(tmp)
                    except OSError: pass
                cols=list(d.columns)
                report_date=parse_report_date(d,cols)
                market=find_col(cols,["market and exchange names","market_and_exchange_names"])
                oi=find_col(cols,["open interest (all)","open_interest_all"])
                ncl=find_col(cols,["noncommercial positions-long","noncomm_positions_long_all"])
                ncs=find_col(cols,["noncommercial positions-short","noncomm_positions_short_all"])
                cl=find_col(cols,["commercial positions-long","comm_positions_long_all"])
                cs=find_col(cols,["commercial positions-short","comm_positions_short_all"])
                if any(x is None for x in [market,oi,ncl,ncs,cl,cs]): continue
                q=pd.DataFrame({
                  "report_date":report_date,"market":d[market].astype("string"),
                  "open_interest":pd.to_numeric(d[oi],errors="coerce"),
                  "noncomm_long":pd.to_numeric(d[ncl],errors="coerce"),
                  "noncomm_short":pd.to_numeric(d[ncs],errors="coerce"),
                  "comm_long":pd.to_numeric(d[cl],errors="coerce"),
                  "comm_short":pd.to_numeric(d[cs],errors="coerce"),
                })
                q=q[q["report_date"].notna() & q["market"].notna() & (q["open_interest"]>0)].copy()
                if q.empty: continue
                q["noncomm_net_pct_oi"]=(q["noncomm_long"]-q["noncomm_short"])/q["open_interest"]
                q["commercial_net_pct_oi"]=(q["comm_long"]-q["comm_short"])/q["open_interest"]
                parts.append(q)
        if j==1 or j==len(archives) or j%5==0:
            print(f"[GEF104] CFTC archives {j}/{len(archives)}",flush=True)
    if not parts: raise RuntimeError("No normalized CFTC rows")
    D=pd.concat(parts,ignore_index=True)
    D=D[D["report_date"].dt.year.between(2009,end_year)].copy()
    wd=D["report_date"].dt.weekday
    days=(7-wd)%7; days=days.where(days>0,7)
    D["AVAILABLE_AT"]=D["report_date"].dt.normalize()+pd.to_timedelta(days,unit="D")
    if not (D["AVAILABLE_AT"]>D["report_date"]).all(): raise RuntimeError("CFTC causality assertion failed")
    D=D.sort_values(["market","report_date"]).drop_duplicates(["market","report_date"],keep="last")
    return D

def build_cftc_feature_sources(root,end_year,selected_features):
    D=load_cftc_normalized(root,end_year)
    sources={}
    for sym,name in CFTC_MAP.items():
        q=D[D["market"].astype(str)==name].sort_values("report_date").copy()
        if q.empty: continue
        for field in ["commercial_net_pct_oi","noncomm_net_pct_oi"]:
            s=pd.to_numeric(q[field],errors="coerce")
            stem=f"cftc_{sym}_{field}"
            feats={
              stem+"_level":s,
              stem+"_d1w":s.diff(1),
              stem+"_d4w":s.diff(4),
            }
            mu=s.rolling(52,min_periods=26).mean()
            sd=s.rolling(52,min_periods=26).std().replace(0,np.nan)
            feats[stem+"_z52"]=(s-mu)/sd
            for fname,val in feats.items():
                if fname in selected_features:
                    sources[fname]=pd.DataFrame({"AVAILABLE_AT":q["AVAILABLE_AT"].to_numpy(),"value":val.to_numpy()})
    missing=sorted(set(selected_features)-set(sources))
    if missing: raise RuntimeError(f"Could not reconstruct selected CFTC features: {missing}")
    return sources

def asof_sources(grid,sources,features):
    base=pd.DataFrame({"decision_time_utc":grid})
    out={}
    for f in features:
        src=sources[f].dropna().sort_values("AVAILABLE_AT").drop_duplicates("AVAILABLE_AT",keep="last")
        z=pd.merge_asof(base,src,left_on="decision_time_utc",right_on="AVAILABLE_AT",direction="backward")
        out[f]=z["value"].to_numpy()
    return pd.DataFrame(out,index=grid)

def latest_run(base,prefix):
    runs=[p for p in sorted(base.glob(f"{prefix}-*")) if (p/"RUN_RECEIPT.json").exists()]
    if not runs: raise RuntimeError(f"No {prefix} run")
    return runs[-1]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=r"D:\MT5_Backtests"); args=ap.parse_args()
    root=Path(args.root)
    base=root/"Research"/"Autonomous"/"guardian_edge_factory_v104_standalone_cftc"; base.mkdir(parents=True,exist_ok=True)
    rid="GEF104-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    out=base/rid; out.mkdir(parents=True,exist_ok=False); t0=time.time()
    def status(step,total,msg,**extra):
        p={"run_id":rid,"engine_version":ENGINE_VERSION,"step":step,"steps":total,"percent":round(100*step/total,1),
           "elapsed_s":round(time.time()-t0,1),"message":msg,**extra}
        write_json(out/"LIVE_STATUS.json",p)
        tail=" | ".join(f"{k}={v}" for k,v in extra.items())
        print(f"[GEF104] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

    status(1,12,"load frozen V85/V83B CFTC lineage; 2023+ forbidden")
    v85=latest_run(root/"Research"/"Autonomous"/"guardian_edge_factory_v85","GEF85")
    design=json.loads((v85/"TRIAL_DESIGN.json").read_text(encoding="utf-8"))
    catalog=pd.read_csv(v85/"FROZEN_ELIGIBLE_FEATURES.csv").reset_index(drop=True)
    state_meta=json.loads((v85/"STATE_CACHE_META.json").read_text(encoding="utf-8"))
    v84c=root/"Research"/"Autonomous"/"guardian_edge_factory_v84c"/design["source_v84c"]
    r84=json.loads((v84c/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
    v83b=root/"Research"/"Autonomous"/"guardian_edge_factory_v83b"/r84["source_v83b"]
    manifest=json.loads((v83b/"REPAIRED_ARCHITECTURE_MANIFEST.json").read_text(encoding="utf-8"))
    F=pd.read_parquet(manifest["price_state_5m_path"]); F.index=pd.to_datetime(F.index)
    S=pd.read_parquet(manifest["slow_state_repaired_path"]); S.index=pd.to_datetime(S.index)
    Y=pd.read_parquet(manifest["targets_5m_path"]).reindex(F.index)

    targets=[c for c in Y.columns if "_fwd_" in str(c)]; nt=len(targets)
    train_rows=np.flatnonzero(F.index.year<=2012); hold_rows=np.flatnonzero(F.index.year==2013)
    ST=np.memmap(v85/"STATE_TRAIN.bool.dat",mode="r",dtype=np.bool_,shape=tuple(state_meta["train_shape"]))
    SH=np.memmap(v85/"STATE_HOLD.bool.dat",mode="r",dtype=np.bool_,shape=tuple(state_meta["hold_shape"]))
    YT=np.array(Y[targets],dtype=np.float32,copy=True)[train_rows,:]
    YH=np.array(Y[targets],dtype=np.float32,copy=True)[hold_rows,:]
    tm=(F.index[train_rows].view("int64")//60_000_000_000).astype(np.int64)
    hm=(F.index[hold_rows].view("int64")//60_000_000_000).astype(np.int64)
    horizons=[]
    for ti,t in enumerate(targets):
        _,h=target_parts(t); horizons.append(h)
        YT[(tm%h)!=0,ti]=np.nan; YH[(hm%h)!=0,ti]=np.nan
    pmap=np.memmap(v85/"TRAIN_PVALUES.float32.dat",mode="r",dtype=np.float32,shape=(int(design["predeclared_trial_slots"]),))
    singleton_slots=int(design["singleton_slots"])
    cftc_idx=catalog.index[catalog["family"].astype(str).str.startswith("cftc_")].tolist()
    if not cftc_idx: raise RuntimeError("No cftc_* market families in frozen V85 catalog")
    status(2,12,"frozen discovery data loaded",cftc_features=len(cftc_idx),targets=nt)

    rows=[]
    for fi in cftc_idx:
        feature=str(catalog.loc[fi,"feature"])
        for st in range(2):
            state=("LO","HI")[st]
            for ti,target in enumerate(targets):
                slot=fi*2*nt+st*nt+ti
                if slot>=singleton_slots: raise RuntimeError("singleton decode overflow")
                pv=float(pmap[slot])
                if not np.isfinite(pv): continue
                vt=YT[:,ti][np.asarray(ST[fi,st,:])]; vh=YH[:,ti][np.asarray(SH[fi,st,:])]
                vt=vt[np.isfinite(vt)]; vh=vh[np.isfinite(vh)]
                if len(vt)<MIN_TRAIN_N: continue
                raw=float(vt.mean())
                if not np.isfinite(raw) or raw==0: continue
                direction=1 if raw>0 else -1
                rows.append({
                  "feature_i":int(fi),"feature":feature,"state_i":int(st),"state":state,
                  "target_i":int(ti),"target":str(target),"horizon_min":int(horizons[ti]),
                  "direction_sign":int(direction),"direction":"LONG" if direction>0 else "SHORT",
                  "train_n":int(len(vt)),"train_mean_bp":mean_bp(vt*direction),"train_p_two":pv,
                  "hold2013_n":int(len(vh)),"hold2013_mean_bp":mean_bp(vh*direction)
                })
    A=pd.DataFrame(rows)
    if A.empty: raise RuntimeError("No finite CFTC singleton tests")
    A["bh_q"]=bh_qvalues(A["train_p_two"].to_numpy())
    A=A.sort_values(["bh_q","train_p_two","hold2013_mean_bp","train_mean_bp"],ascending=[True,True,False,False],kind="mergesort").reset_index(drop=True)
    A.to_csv(out/"CFTC_ATOMS_ALL.csv",index=False)
    frozen=A[A["train_p_two"].le(.05)&A["bh_q"].le(DISCOVERY_Q)&A["hold2013_n"].ge(MIN_HOLD_N)&A["hold2013_mean_bp"].gt(0)].head(MAX_FROZEN).copy()
    if frozen.empty:
        receipt={"run_id":rid,"status":"COMPLETE_V104_NO_DISCOVERY_SURVIVORS","engine_version":ENGINE_VERSION,
                 "finite_cftc_tests":int(len(A)),"2014_plus_accessed":False,"2023_2025_accessed":False,"2026_accessed":False}
        write_json(out/"RUN_RECEIPT.json",receipt); status(12,12,"DONE - no discovery survivors"); print(json.dumps(receipt,indent=2)); return
    frozen.to_csv(out/"FROZEN_CFTC_PRE_2014.csv",index=False)
    write_json(out/"DISCOVERY_FREEZE.json",{"run_id":rid,"status":"FROZEN_BEFORE_REPLICATION","frozen_candidates":int(len(frozen)),
      "frozen_csv_sha256":sha256(out/"FROZEN_CFTC_PRE_2014.csv"),"2014_plus_accessed_at_freeze":False,"2023_2025_accessed":False,"2026_accessed":False})
    status(3,12,"CFTC candidates frozen before 2014+",frozen=len(frozen))
    feature_lookup={str(r["feature"]):int(i) for i,r in catalog.iterrows()}

    def reconstruct(end_year,candidates,parity):
        if end_year>=FORBIDDEN_YEAR: raise RuntimeError("V104 reconstruct refuses 2023+")
        features=sorted(set(candidates["feature"])); target_names=sorted(set(candidates["target"]))
        markets=sorted({target_parts(t)[0] for t in target_names})
        grid=pd.date_range("2010-01-01 00:00",f"{end_year}-12-31 23:55",freq="5min")
        P=pd.DataFrame(index=grid)
        for j,sym in enumerate(markets,1):
            raw=load_m1(root,sym,2009,end_year)
            P[sym]=raw.resample("5min",label="right",closed="left").last().reindex(grid).astype("float64")
            print(f"[GEF104] target price {j}/{len(markets)} {sym}",flush=True)
        diffs=pd.Series(S.index).diff().dropna(); slow_freq=diffs.mode().iloc[0]
        slow_grid=pd.date_range(S.index.min(),f"{end_year}-12-31 23:00",freq=slow_freq)
        sources=build_cftc_feature_sources(root,end_year,features)
        X=asof_sources(slow_grid,sources,features)
        if not S.index.equals(slow_grid[:len(S.index)]): raise RuntimeError("V104 slow-grid prefix mismatch")
        for f in features:
            if f not in S.columns: raise RuntimeError(f"Missing canonical V83B CFTC feature {f}")
            X.loc[S.index,f]=pd.to_numeric(S[f],errors="coerce").to_numpy()
        sets={}; sets09={}; sets11={}; setslag={}
        for f in features:
            lo,hi=causal_states(X[f],SLOW_MIN_PERIODS,1.0)
            lo09,hi09=causal_states(X[f],SLOW_MIN_PERIODS,.9)
            lo11,hi11=causal_states(X[f],SLOW_MIN_PERIODS,1.1)
            lol,hil=causal_states(X[f].shift(24*7),SLOW_MIN_PERIODS,1.0)
            sets[(f,"LO")],sets[(f,"HI")]=lo,hi
            sets09[(f,"LO")],sets09[(f,"HI")]=lo09,hi09
            sets11[(f,"LO")],sets11[(f,"HI")]=lo11,hi11
            setslag[(f,"LO")],setslag[(f,"HI")]=lol,hil
        slow_ns=slow_grid.view("int64"); fast_ns=grid.view("int64"); bridge=np.searchsorted(slow_ns,fast_ns,side="right")-1; ok=bridge>=0
        def expand(src):
            out={}
            for key,v in src.items():
                z=np.zeros(len(grid),dtype=bool); z[ok]=v[bridge[ok]]; out[key]=z
            return out
        states,states09,states11,stateslag=map(expand,[sets,sets09,sets11,setslag])
        if parity:
            pr=[]
            if not F.index.equals(grid[:len(F.index)]): raise RuntimeError("V104 fast-grid prefix mismatch")
            for f in features:
                fi=feature_lookup[f]
                for si,st in enumerate(("LO","HI")):
                    rebuilt=states[(f,st)][:len(F.index)]
                    frozen_state=np.concatenate([np.asarray(ST[fi,si,:]),np.asarray(SH[fi,si,:])])
                    mismatch=int(np.count_nonzero(rebuilt!=frozen_state))
                    pr.append({"feature":f,"state":st,"mismatch_rows":mismatch,"parity_ok":mismatch==0})
            PR=pd.DataFrame(pr); PR.to_csv(out/"RECONSTRUCTION_PARITY_2010_2013.csv",index=False)
            if not bool(PR["parity_ok"].all()): raise RuntimeError("V104 canonical CFTC state parity failed")
        T={t:build_target(P,grid,t) for t in target_names}
        return grid,states,states09,states11,stateslag,T

    status(4,12,"rebuild CFTC through 2017 and verify 2010-2013 parity")
    grid17,s17,s09,s11,slag,T17=reconstruct(2017,frozen,True)
    status(5,12,"parity exact; score 2014-2017 replication")
    w=(grid17>=pd.Timestamp("2014-01-01"))&(grid17<pd.Timestamp("2018-01-01"))
    rep=[]
    for r in frozen.itertuples(index=False):
        m=s17[(r.feature,r.state)]&w; y=T17[r.target][m]*int(r.direction_sign); times=grid17[m]
        met=metrics(times,y,int(r.horizon_min),remove_best=3)
        passed=(met["n"]>=MIN_REP_N and met["mean_bp"]>0 and met["net1bp_mean_bp"]>0 and
                met["positive_year_fraction"]>=.50 and met["trim_best_1pct_mean_bp"]>0)
        rep.append({**r._asdict(),**{f"rep_{k}":v for k,v in met.items()},"replication_pass":bool(passed)})
    R=pd.DataFrame(rep); R.to_csv(out/"REPLICATION_RESULTS.csv",index=False)
    rp=R[R["replication_pass"].astype(bool)].copy()
    status(6,12,"replication complete",survivors=len(rp))
    if rp.empty:
        receipt={"run_id":rid,"status":"COMPLETE_V104_REPLICATION_FAIL_ALL","engine_version":ENGINE_VERSION,
                 "discovery_frozen":int(len(frozen)),"replication_survivors":0,"validation_accessed":False,
                 "2023_2025_accessed":False,"2026_accessed":False}
        write_json(out/"RUN_RECEIPT.json",receipt); status(12,12,"DONE"); print(json.dumps(receipt,indent=2)); return

    robust=[]
    for r in rp.itertuples(index=False):
        direction=int(r.direction_sign)
        def alt(src):
            m=src[(r.feature,r.state)]&w
            return mean_bp(T17[r.target][m]*direction)
        p=(r.rep_trim_best_2pct_mean_bp>0 and r.rep_remove_best_3_mean_bp>0 and r.rep_nonoverlap_mean_bp>0)
        z09=alt(s09); z11=alt(s11); lag=alt(slag)
        p=bool(p and z09>0 and z11>0 and lag>0)
        robust.append({**r._asdict(),"robust_z09_mean_bp":z09,"robust_z11_mean_bp":z11,
                       "robust_lag1w_mean_bp":lag,"robustness_pass":p})
    B=pd.DataFrame(robust); B.to_csv(out/"ROBUSTNESS_RESULTS.csv",index=False)
    rb=B[B["robustness_pass"].astype(bool)].copy()
    if rb.empty:
        receipt={"run_id":rid,"status":"COMPLETE_V104_ROBUSTNESS_FAIL_ALL","engine_version":ENGINE_VERSION,
                 "discovery_frozen":int(len(frozen)),"replication_survivors":int(len(rp)),"robustness_survivors":0,
                 "validation_accessed":False,"2023_2025_accessed":False,"2026_accessed":False}
        write_json(out/"RUN_RECEIPT.json",receipt); status(12,12,"DONE"); print(json.dumps(receipt,indent=2)); return

    rb.to_csv(out/"FROZEN_PRE_VALIDATION.csv",index=False)
    write_json(out/"PRE_VALIDATION_FREEZE.json",{"run_id":rid,"status":"FROZEN_BEFORE_VALIDATION","survivors":int(len(rb)),
      "frozen_csv_sha256":sha256(out/"FROZEN_PRE_VALIDATION.csv"),"2018_plus_accessed_at_freeze":False,
      "2023_2025_accessed":False,"2026_accessed":False})
    status(7,12,"robust survivors frozen before 2018+",survivors=len(rb))
    status(8,12,"rebuild through 2022; validation only")
    grid22,s22,_,_,_,T22=reconstruct(2022,rb,False)
    vw=(grid22>=pd.Timestamp("2018-01-01"))&(grid22<pd.Timestamp("2023-01-01"))
    vals=[]
    for r in rb.itertuples(index=False):
        m=s22[(r.feature,r.state)]&vw; y=T22[r.target][m]*int(r.direction_sign); times=grid22[m]
        met=metrics(times,y,int(r.horizon_min),remove_best=5)
        passed=(met["n"]>=MIN_VAL_N and met["mean_bp"]>0 and met["net1bp_mean_bp"]>0 and
                met["positive_year_fraction"]>=.60 and met["trim_best_1pct_mean_bp"]>0 and
                met["trim_best_2pct_mean_bp"]>0 and met["remove_best_5_mean_bp"]>0 and met["nonoverlap_mean_bp"]>0)
        vals.append({**r._asdict(),**{f"val_{k}":v for k,v in met.items()},"validation_pass":bool(passed)})
    V=pd.DataFrame(vals); V.to_csv(out/"VALIDATION_RESULTS.csv",index=False)
    final=V[V["validation_pass"].astype(bool)].copy(); final.to_csv(out/"FINAL_SURVIVORS.csv",index=False)
    status(9,12,"validation complete",final_survivors=len(final))
    receipt={"run_id":rid,"status":"COMPLETE_V104_STANDALONE_CFTC","engine_version":ENGINE_VERSION,
      "source_v85":v85.name,"source_v83b":v83b.name,"finite_cftc_tests":int(len(A)),
      "discovery_frozen":int(len(frozen)),"replication_survivors":int(len(rp)),
      "robustness_survivors":int(len(rb)),"validation_survivors":int(len(final)),
      "final_survivors_sha256":sha256(out/"FINAL_SURVIVORS.csv"),
      "2023_2025_accessed":False,"2026_accessed":False,
      "next":"HUMAN_REVIEW_V104; DO_NOT_OPEN_2023_2025_OR_2026"}
    write_json(out/"RUN_RECEIPT.json",receipt)
    report=["# GEF V104 — Standalone CFTC positioning","",f"Run: {rid}",
      f"- finite tests: {len(A)}",f"- discovery frozen: {len(frozen)}",
      f"- replication survivors: {len(rp)}",f"- robustness survivors: {len(rb)}",
      f"- validation survivors: {len(final)}","- 2023-2025 accessed: false","- 2026 accessed: false"]
    (out/"V104_REPORT.md").write_text("\n".join(report),encoding="utf-8")
    status(10,12,"receipt/report written"); status(11,12,"firewalls asserted"); status(12,12,"DONE")
    print("\n=== V104 RECEIPT ==="); print(json.dumps(receipt,indent=2))
    if len(final):
        print("\n=== V104 FINAL SURVIVORS ===")
        print(final[["feature","state","target","direction","rep_mean_bp","val_mean_bp","val_net1bp_mean_bp"]].to_string(index=False))
    print("\nRUN:",out)

if __name__=="__main__":
    main()
