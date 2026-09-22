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

ENGINE_VERSION="V105.0"
EXPECTED_V104_RUN="GEF104-20260922-145941"
EXPECTED_FINAL_SHA="428ce6c9f5bd5b4acaaf4fbc619b1d07fd0c6abd5ec716403d6b2b4e01a9b68e"
FORBIDDEN_YEAR=2023
SLOW_MIN_PERIODS=500
BOOTSTRAPS=2000
BOOTSTRAP_SEED=105

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
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def mean_bp(x):
    x=np.asarray(x,dtype=float); x=x[np.isfinite(x)]
    return float(x.mean()*1e4) if len(x) else np.nan

def target_parts(target):
    m=re.fullmatch(r"([A-Z]+)_fwd_(\d+)m",str(target))
    if not m: raise RuntimeError(f"Unsupported target {target}")
    return m.group(1),int(m.group(2))

def causal_states(series,min_periods,zcut=1.0):
    s=pd.to_numeric(series,errors="coerce")
    mu=s.expanding(min_periods=min_periods).mean().shift(1)
    sd=s.expanding(min_periods=min_periods).std().shift(1).replace(0,np.nan)
    z=((s-mu)/sd).to_numpy(dtype=np.float32)
    finite=np.isfinite(z)
    return finite&(z<=-zcut),finite&(z>=zcut)

def load_m1(root,sym,start_year,end_year):
    if end_year>=FORBIDDEN_YEAR: raise RuntimeError("V105 refuses 2023+")
    parts=[]
    for year in range(start_year,end_year+1):
        p=root/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
        if not p.exists():
            if year<=2012: continue
            raise RuntimeError(f"Missing <=2022 price file {p}")
        d=pd.read_parquet(p)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        pc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None and isinstance(d.index,pd.DatetimeIndex):
            d=d.reset_index(); dc=d.columns[0]
        if dc is None or pc is None: raise RuntimeError(f"Bad price schema {p}")
        utc=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(hours=5)
        q=pd.DataFrame({"utc":utc,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
        q=q[q["utc"].dt.year.between(start_year,end_year)]
        parts.append(q)
    if not parts: raise RuntimeError(f"No price data {sym}")
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    return q.set_index("utc")["px"]

def build_target(P,grid,target):
    sym,mins=target_parts(target); k=mins//5
    raw=P[sym].shift(-k)/P[sym]-1
    y=np.array(raw.reindex(grid),dtype=float,copy=True)
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
    if direct is not None: return pd.to_datetime(d[direct],errors="coerce")
    compact=find_col(cols,["as_of_date_in_form_yymmdd","as of date in form yymmdd"])
    if compact is not None:
        s=d[compact].astype("string").str.replace(r"\.0$","",regex=True).str.zfill(6)
        return pd.to_datetime(s,format="%y%m%d",errors="coerce")
    return pd.Series(pd.NaT,index=d.index)

def load_cftc_normalized(root,end_year):
    if end_year>=FORBIDDEN_YEAR: raise RuntimeError("V105 refuses CFTC 2023+")
    src=root/"DataLake"/"raw"/"cftc"/"futures_only_reports"
    archives=[]
    for y in range(2009,end_year+1):
        archives.extend([p for p in sorted(src.glob("*.zip")) if str(y) in p.name and "excel" in p.name.lower()])
    archives=list(dict.fromkeys(archives))
    parts=[]
    for j,p in enumerate(archives,1):
        with zipfile.ZipFile(p) as z:
            members=[m for m in z.namelist() if m.lower().endswith((".xls",".xlsx"))]
            for member in members:
                suffix=Path(member).suffix
                with tempfile.NamedTemporaryFile(suffix=suffix,delete=False) as tf:
                    tf.write(z.read(member)); tmp=tf.name
                try: d=pd.read_excel(tmp)
                finally:
                    try: os.unlink(tmp)
                    except OSError: pass
                cols=list(d.columns); rd=parse_report_date(d,cols)
                market=find_col(cols,["market and exchange names","market_and_exchange_names"])
                oi=find_col(cols,["open interest (all)","open_interest_all"])
                ncl=find_col(cols,["noncommercial positions-long","noncomm_positions_long_all"])
                ncs=find_col(cols,["noncommercial positions-short","noncomm_positions_short_all"])
                cl=find_col(cols,["commercial positions-long","comm_positions_long_all"])
                cs=find_col(cols,["commercial positions-short","comm_positions_short_all"])
                if any(x is None for x in [market,oi,ncl,ncs,cl,cs]): continue
                q=pd.DataFrame({
                  "report_date":rd,"market":d[market].astype("string"),
                  "open_interest":pd.to_numeric(d[oi],errors="coerce"),
                  "noncomm_long":pd.to_numeric(d[ncl],errors="coerce"),
                  "noncomm_short":pd.to_numeric(d[ncs],errors="coerce"),
                  "comm_long":pd.to_numeric(d[cl],errors="coerce"),
                  "comm_short":pd.to_numeric(d[cs],errors="coerce")
                })
                q=q[q["report_date"].notna()&q["market"].notna()&(q["open_interest"]>0)].copy()
                if q.empty: continue
                q["noncomm_net_pct_oi"]=(q["noncomm_long"]-q["noncomm_short"])/q["open_interest"]
                q["commercial_net_pct_oi"]=(q["comm_long"]-q["comm_short"])/q["open_interest"]
                parts.append(q)
        if j==1 or j==len(archives) or j%5==0:
            print(f"[GEF105] CFTC archives {j}/{len(archives)}",flush=True)
    if not parts: raise RuntimeError("No CFTC rows")
    D=pd.concat(parts,ignore_index=True)
    D=D[D["report_date"].dt.year.between(2009,end_year)].copy()
    wd=D["report_date"].dt.weekday
    days=(7-wd)%7; days=days.where(days>0,7)
    D["AVAILABLE_AT"]=D["report_date"].dt.normalize()+pd.to_timedelta(days,unit="D")
    D=D.sort_values(["market","report_date"]).drop_duplicates(["market","report_date"],keep="last")
    return D

def feature_source_table(D,feature):
    m=re.fullmatch(r"cftc_([A-Z]+)_(commercial|noncomm)_net_pct_oi_(level|d1w|d4w|z52)",feature)
    if not m: raise RuntimeError(f"Unsupported frozen CFTC feature {feature}")
    sym,who,transform=m.groups()
    if sym not in CFTC_MAP: raise RuntimeError(f"Unknown CFTC mapped market {sym}")
    q=D[D["market"].astype(str)==CFTC_MAP[sym]].sort_values("report_date").copy()
    field="commercial_net_pct_oi" if who=="commercial" else "noncomm_net_pct_oi"
    s=pd.to_numeric(q[field],errors="coerce")
    if transform=="level": v=s
    elif transform=="d1w": v=s.diff(1)
    elif transform=="d4w": v=s.diff(4)
    else:
        mu=s.rolling(52,min_periods=26).mean()
        sd=s.rolling(52,min_periods=26).std().replace(0,np.nan)
        v=(s-mu)/sd
    return pd.DataFrame({
      "report_date":q["report_date"].to_numpy(),
      "AVAILABLE_AT":q["AVAILABLE_AT"].to_numpy(),
      "value":v.to_numpy()
    }).dropna(subset=["AVAILABLE_AT","value"]).sort_values("AVAILABLE_AT").drop_duplicates("AVAILABLE_AT",keep="last")

def asof_one(grid,src,delay_days=0):
    q=src.copy()
    q["effective_available_at"]=pd.to_datetime(q["AVAILABLE_AT"])+pd.Timedelta(days=int(delay_days))
    base=pd.DataFrame({"decision_time_utc":grid})
    z=pd.merge_asof(base,q[["effective_available_at","AVAILABLE_AT","report_date","value"]],
                    left_on="decision_time_utc",right_on="effective_available_at",direction="backward")
    z.index=grid
    return z

def trimmed_best(x,pct):
    x=np.asarray(x,dtype=float); x=x[np.isfinite(x)]
    if not len(x): return np.nan
    k=int(math.ceil(len(x)*pct))
    if k<=0:return mean_bp(x)
    if k>=len(x):return np.nan
    return mean_bp(np.sort(x)[:-k])

def remove_best(x,k):
    x=np.asarray(x,dtype=float); x=x[np.isfinite(x)]
    if len(x)<=k:return np.nan
    return mean_bp(np.sort(x)[:-k])

def remove_best_month(times,vals):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,dtype=float)})
    d=d[np.isfinite(d["v"])].copy()
    if d.empty:return np.nan,None
    d["month"]=d["t"].dt.to_period("M").astype(str)
    totals=d.groupby("month")["v"].sum()
    best=str(totals.idxmax())
    return mean_bp(d.loc[d["month"]!=best,"v"].to_numpy()),best

def leave_one_year_out(times,vals):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,dtype=float)})
    d=d[np.isfinite(d["v"])].copy()
    if d.empty:return np.nan,{}
    d["year"]=d["t"].dt.year
    out={}
    for y in sorted(d["year"].unique()):
        out[str(int(y))]=mean_bp(d.loc[d["year"]!=y,"v"].to_numpy())
    return min(out.values()) if out else np.nan,out

def positive_year_fraction(times,vals):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,dtype=float)})
    d=d[np.isfinite(d["v"])].copy()
    if d.empty:return np.nan,{}
    d["year"]=d["t"].dt.year
    y=d.groupby("year")["v"].mean()*1e4
    return float((y>0).mean()),{str(int(k)):float(v) for k,v in y.items()}

def nonoverlap(times,vals,horizon_min):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,dtype=float)})
    d=d[np.isfinite(d["v"])].sort_values("t")
    keep=[]; next_allowed=None; gap=pd.Timedelta(minutes=int(horizon_min))
    for row in d.itertuples(index=False):
        if next_allowed is None or row.t>=next_allowed:
            keep.append((row.t,row.v)); next_allowed=row.t+gap
    if not keep:return np.asarray([]),pd.DatetimeIndex([])
    return np.asarray([x[1] for x in keep]),pd.DatetimeIndex([x[0] for x in keep])

def first_per_report(times,vals,report_keys):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,dtype=float),
                    "report":pd.to_datetime(report_keys)})
    d=d[np.isfinite(d["v"])&d["report"].notna()].sort_values("t")
    if d.empty:return pd.DataFrame(columns=["t","v","report"])
    return d.groupby("report",as_index=False).first().sort_values("t")

def first_per_episode(mask,grid,target_vals):
    m=np.asarray(mask,dtype=bool); y=np.asarray(target_vals,dtype=float)
    starts=np.flatnonzero(m&~np.r_[False,m[:-1]])
    ends=np.flatnonzero(m&~np.r_[m[1:],False])+1
    vals=[];times=[]
    for a,b in zip(starts,ends):
        elig=np.flatnonzero(np.isfinite(y[a:b]))
        if not len(elig):continue
        i=a+int(elig[0]); vals.append(float(y[i]));times.append(grid[i])
    return np.asarray(vals),pd.DatetimeIndex(times)

def month_block_bootstrap(times,vals,draws=2000,seed=105):
    d=pd.DataFrame({"t":pd.DatetimeIndex(times),"v":np.asarray(vals,dtype=float)})
    d=d[np.isfinite(d["v"])].copy()
    if d.empty:return (np.nan,np.nan,np.nan)
    d["month"]=d["t"].dt.to_period("M").astype(str)
    groups=[g["v"].to_numpy() for _,g in d.groupby("month") if len(g)]
    if len(groups)<2:return (np.nan,np.nan,np.nan)
    rng=np.random.default_rng(seed); means=np.empty(draws)
    for i in range(draws):
        pick=rng.integers(0,len(groups),size=len(groups))
        means[i]=mean_bp(np.concatenate([groups[j] for j in pick]))
    return tuple(float(x) for x in np.quantile(means,[.025,.5,.975]))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root)
    v104=root/"Research"/"Autonomous"/"guardian_edge_factory_v104_standalone_cftc"/EXPECTED_V104_RUN
    rec=json.loads((v104/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
    final_path=v104/"FINAL_SURVIVORS.csv"
    if rec.get("status")!="COMPLETE_V104_STANDALONE_CFTC":raise RuntimeError("Wrong V104 source status")
    if sha256(final_path)!=EXPECTED_FINAL_SHA:raise RuntimeError("V104 final SHA mismatch")
    C=pd.read_csv(final_path)
    if len(C)!=7:raise RuntimeError(f"Expected 7 frozen V104 survivors, got {len(C)}")

    base=root/"Research"/"Autonomous"/"guardian_edge_factory_v105_cftc_preoos_forensic";base.mkdir(parents=True,exist_ok=True)
    rid="GEF105-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");out=base/rid;out.mkdir(parents=True,exist_ok=False);t0=time.time()
    def status(step,total,msg,**extra):
        p={"run_id":rid,"engine_version":ENGINE_VERSION,"step":step,"steps":total,"percent":round(100*step/total,1),
           "elapsed_s":round(time.time()-t0,1),"message":msg,**extra}
        write_json(out/"LIVE_STATUS.json",p)
        tail=" | ".join(f"{k}={v}" for k,v in extra.items())
        print(f"[GEF105] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)
    status(1,10,"exact V104 panel verified",sha=EXPECTED_FINAL_SHA[:16])

    v83b=root/"Research"/"Autonomous"/"guardian_edge_factory_v83b"/str(rec["source_v83b"])
    manifest=json.loads((v83b/"REPAIRED_ARCHITECTURE_MANIFEST.json").read_text(encoding="utf-8"))
    S=pd.read_parquet(manifest["slow_state_repaired_path"]);S.index=pd.to_datetime(S.index)

    targets=sorted(C["target"].astype(str).unique())
    markets=sorted({target_parts(t)[0] for t in targets})
    grid=pd.date_range("2010-01-01 00:00","2022-12-31 23:55",freq="5min")
    P=pd.DataFrame(index=grid)
    for i,sym in enumerate(markets,1):
        raw=load_m1(root,sym,2009,2022)
        P[sym]=raw.resample("5min",label="right",closed="left").last().reindex(grid).astype("float64")
        print(f"[GEF105] price {i}/{len(markets)} {sym}",flush=True)
    T={t:build_target(P,grid,t) for t in targets}
    status(2,10,"target histories rebuilt through 2022 only",markets=len(markets))

    D=load_cftc_normalized(root,2022)
    features=sorted(C["feature"].astype(str).unique())
    diffs=pd.Series(S.index).diff().dropna();slow_freq=diffs.mode().iloc[0]
    slow_grid=pd.date_range(S.index.min(),"2022-12-31 23:00",freq=slow_freq)

    slow={}
    for f in features:
        src=feature_source_table(D,f)
        basej=asof_one(slow_grid,src,0)
        # Canonical anchor for the frozen baseline only.
        if f not in S.columns:raise RuntimeError(f"Missing V83B feature {f}")
        if not S.index.equals(slow_grid[:len(S.index)]):raise RuntimeError("V105 slow-grid prefix mismatch")
        basej.loc[S.index,"value"]=pd.to_numeric(S[f],errors="coerce").to_numpy()
        lo,hi=causal_states(basej["value"],SLOW_MIN_PERIODS,1.0)
        lo09,hi09=causal_states(basej["value"],SLOW_MIN_PERIODS,.9)
        lo11,hi11=causal_states(basej["value"],SLOW_MIN_PERIODS,1.1)

        # Delay source availability before as-of reconstruction. Preserve canonical prefix
        # only as warmup history; delayed semantics are evaluated on post-2013 data.
        j1=asof_one(slow_grid,src,1);j2=asof_one(slow_grid,src,2)
        j1.loc[S.index,"value"]=pd.to_numeric(S[f],errors="coerce").to_numpy()
        j2.loc[S.index,"value"]=pd.to_numeric(S[f],errors="coerce").to_numpy()
        lo1,hi1=causal_states(j1["value"],SLOW_MIN_PERIODS,1.0)
        lo2,hi2=causal_states(j2["value"],SLOW_MIN_PERIODS,1.0)
        slow[(f,"base","LO")]=lo;slow[(f,"base","HI")]=hi
        slow[(f,"z09","LO")]=lo09;slow[(f,"z09","HI")]=hi09
        slow[(f,"z11","LO")]=lo11;slow[(f,"z11","HI")]=hi11
        slow[(f,"lag1","LO")]=lo1;slow[(f,"lag1","HI")]=hi1
        slow[(f,"lag2","LO")]=lo2;slow[(f,"lag2","HI")]=hi2
        slow[(f,"base_report")]=pd.to_datetime(basej["AVAILABLE_AT"]).to_numpy()

    slow_ns=slow_grid.view("int64");fast_ns=grid.view("int64");bridge=np.searchsorted(slow_ns,fast_ns,side="right")-1;ok=bridge>=0
    def expand_bool(feature,label,state):
        src=slow[(feature,label,state)];z=np.zeros(len(grid),dtype=bool);z[ok]=src[bridge[ok]];return z
    def expand_report(feature):
        src=slow[(feature,"base_report")]
        out=np.full(len(grid),np.datetime64("NaT"),dtype="datetime64[ns]")
        out[ok]=src[bridge[ok]]
        return pd.DatetimeIndex(out)
    status(3,10,"CFTC states rebuilt with exact report lineage and delayed-availability diagnostics")

    val=(grid>=pd.Timestamp("2018-01-01"))&(grid<pd.Timestamp("2023-01-01"))
    rows=[];masks={};series={}
    for idx,r in C.reset_index(drop=True).iterrows():
        cid=f"C{idx+1}";f=str(r["feature"]);st=str(r["state"]);target=str(r["target"])
        direction=1 if str(r["direction"]).upper()=="LONG" else -1
        horizon=target_parts(target)[1]
        base_mask=expand_bool(f,"base",st)&val
        yall=T[target]*direction
        vals=yall[base_mask];times=grid[base_mask];finite=np.isfinite(vals);vals=vals[finite];times=times[finite]
        eligible=base_mask&np.isfinite(yall)
        masks[cid]=eligible;series[cid]=pd.Series(yall[eligible],index=grid[eligible])

        no,notimes=nonoverlap(times,vals,horizon)
        ep,ept=first_per_episode(base_mask,grid,yall)
        report_grid=expand_report(f)
        reports=report_grid[eligible]
        fr=first_per_report(grid[eligible],yall[eligible],reports)
        frv=fr["v"].to_numpy(dtype=float);frt=pd.DatetimeIndex(fr["t"])
        pyf,pyjson=positive_year_fraction(frt,frv)
        rm,bm=remove_best_month(times,vals)
        loo,looj=leave_one_year_out(times,vals)
        frm,frbm=remove_best_month(frt,frv)
        frloo,frlooj=leave_one_year_out(frt,frv)
        b025,b50,b975=month_block_bootstrap(frt,frv,BOOTSTRAPS,BOOTSTRAP_SEED+idx)

        def alt(label):
            m=expand_bool(f,label,st)&val
            return mean_bp(yall[m])

        m=mean_bp(vals)
        recrow={
          "candidate_id":cid,"feature":f,"state":st,"target":target,"direction":str(r["direction"]),
          "information_family_key":f"{f}|{st}",
          "upstream_cftc_market":re.match(r"cftc_([A-Z]+)_",f).group(1),
          "n":int(len(vals)),"mean_bp":m,"median_bp":float(np.median(vals)*1e4) if len(vals) else np.nan,
          "win_rate_pct":float((vals>0).mean()*100) if len(vals) else np.nan,
          "net1bp_mean_bp":m-1,"net2bp_mean_bp":m-2,"net3bp_mean_bp":m-3,"net5bp_mean_bp":m-5,
          "trim1_mean_bp":trimmed_best(vals,.01),"trim2_mean_bp":trimmed_best(vals,.02),"trim5_mean_bp":trimmed_best(vals,.05),
          "remove_best5_mean_bp":remove_best(vals,5),"remove_best10_mean_bp":remove_best(vals,10),
          "remove_best_month_mean_bp":rm,"removed_best_month":bm,
          "leave_one_year_out_min_mean_bp":loo,"leave_one_year_out_json":json.dumps(looj,sort_keys=True),
          "nonoverlap_n":int(len(no)),"nonoverlap_mean_bp":mean_bp(no),
          "episode_first_n":int(len(ep)),"episode_first_mean_bp":mean_bp(ep),
          "report_first_n":int(len(frv)),"report_first_mean_bp":mean_bp(frv),
          "report_first_positive_year_fraction":pyf,"report_first_yearly_json":json.dumps(pyjson,sort_keys=True),
          "report_first_remove_best3_mean_bp":remove_best(frv,3),
          "report_first_remove_best5_mean_bp":remove_best(frv,5),
          "report_first_remove_best_month_mean_bp":frm,"report_first_removed_best_month":frbm,
          "report_first_leave_one_year_out_min_mean_bp":frloo,"report_first_leave_one_year_out_json":json.dumps(frlooj,sort_keys=True),
          "report_first_bootstrap_month_q025_bp":b025,"report_first_bootstrap_month_q50_bp":b50,"report_first_bootstrap_month_q975_bp":b975,
          "z09_mean_bp":alt("z09"),"z11_mean_bp":alt("z11"),"lag1d_mean_bp":alt("lag1"),"lag2d_mean_bp":alt("lag2")
        }
        gates=[
          recrow["mean_bp"]>0,recrow["net1bp_mean_bp"]>0,recrow["trim5_mean_bp"]>0,
          recrow["remove_best10_mean_bp"]>0,recrow["remove_best_month_mean_bp"]>0,
          recrow["leave_one_year_out_min_mean_bp"]>0,recrow["nonoverlap_mean_bp"]>0,
          recrow["report_first_mean_bp"]>0,recrow["report_first_positive_year_fraction"]>=.60,
          recrow["report_first_remove_best3_mean_bp"]>0,recrow["report_first_remove_best5_mean_bp"]>0,
          recrow["report_first_remove_best_month_mean_bp"]>0,recrow["report_first_leave_one_year_out_min_mean_bp"]>0,
          recrow["episode_first_mean_bp"]>0,recrow["z09_mean_bp"]>0,recrow["z11_mean_bp"]>0,
          recrow["lag1d_mean_bp"]>0,recrow["lag2d_mean_bp"]>0,recrow["report_first_bootstrap_month_q025_bp"]>0
        ]
        recrow["final_preoos_pass"]=bool(all(gates));recrow["failed_gate_count"]=int(sum(not bool(x) for x in gates))
        rows.append(recrow)
    R=pd.DataFrame(rows);R.to_csv(out/"FORENSIC_RESULTS.csv",index=False)
    status(4,10,"candidate forensic complete",passes=int(R["final_preoos_pass"].sum()))

    ids=R["candidate_id"].tolist();jac=pd.DataFrame(np.nan,index=ids,columns=ids);corr=pd.DataFrame(np.nan,index=ids,columns=ids)
    for a in ids:
        for b in ids:
            ma=masks[a];mb=masks[b];u=int((ma|mb).sum());i=int((ma&mb).sum());jac.loc[a,b]=i/u if u else np.nan
            common=series[a].index.intersection(series[b].index)
            if len(common)>=3:
                corr.loc[a,b]=float(np.corrcoef(series[a].loc[common].to_numpy(),series[b].loc[common].to_numpy())[0,1])
    jac.to_csv(out/"SIGNAL_JACCARD.csv");corr.to_csv(out/"COMMON_TIMESTAMP_RETURN_CORRELATION.csv")

    families=R.groupby("information_family_key").agg(candidate_count=("candidate_id","count"),passing_candidates=("final_preoos_pass","sum")).reset_index()
    families["family_pass"]=families["passing_candidates"]>0
    families.to_csv(out/"INFORMATION_FAMILY_SUMMARY.csv",index=False)
    passing=R[R["final_preoos_pass"]].copy();passing.to_csv(out/"FINAL_PREOOS_SURVIVORS.csv",index=False)
    unique=int(passing["information_family_key"].nunique()) if len(passing) else 0
    status(5,10,"dependency audit complete",candidate_passes=len(passing),unique_information_families=unique)

    cols=["candidate_id","feature","state","target","direction","mean_bp","trim5_mean_bp","remove_best10_mean_bp",
          "remove_best_month_mean_bp","leave_one_year_out_min_mean_bp","nonoverlap_mean_bp","report_first_n",
          "report_first_mean_bp","report_first_positive_year_fraction","report_first_remove_best5_mean_bp",
          "report_first_remove_best_month_mean_bp","report_first_leave_one_year_out_min_mean_bp",
          "episode_first_mean_bp","lag1d_mean_bp","lag2d_mean_bp","report_first_bootstrap_month_q025_bp","final_preoos_pass"]
    report=["# GEF V105 — CFTC final pre-OOS forensic","",f"Run: {rid}",
            f"- candidate passes: {len(passing)}/7",f"- unique passing information families: {unique}",
            "- 2023-2025 accessed: false","- 2026 accessed: false","",
            "## Forensic", "", R[cols].to_markdown(index=False),"","## Information families","",families.to_markdown(index=False),
            "","STOP. Do not open locked OOS automatically."]
    (out/"V105_REPORT.md").write_text("\n".join(report),encoding="utf-8")
    status(6,10,"report written")

    receipt={"run_id":rid,"status":"COMPLETE_V105_CFTC_PREOOS_FORENSIC","engine_version":ENGINE_VERSION,
      "source_v104":EXPECTED_V104_RUN,"source_final_sha256":EXPECTED_FINAL_SHA,"candidates_audited":7,
      "candidate_preoos_passes":int(len(passing)),"unique_information_families_all":int(R["information_family_key"].nunique()),
      "unique_information_families_passing":unique,"forensic_results_sha256":sha256(out/"FORENSIC_RESULTS.csv"),
      "final_preoos_survivors_sha256":sha256(out/"FINAL_PREOOS_SURVIVORS.csv"),
      "2023_2025_accessed":False,"2026_accessed":False,
      "next":"STOP_FOR_HUMAN_REVIEW; IF ANY INFORMATION FAMILY PASSES, PREDECLARE SEPARATE LOCKED-OOS PROTOCOL"}
    write_json(out/"RUN_RECEIPT.json",receipt)
    status(7,10,"receipt written");status(8,10,"2023-2025 firewall asserted",accessed=False);status(9,10,"2026 firewall asserted",accessed=False);status(10,10,"DONE")
    print("\n=== V105 RECEIPT ===");print(json.dumps(receipt,indent=2))
    print("\n=== V105 FORENSIC RESULTS ===");print(R[cols].to_string(index=False))
    print("\n=== V105 INFORMATION FAMILIES ===");print(families.to_string(index=False))
    print("\nRUN:",out)

if __name__=="__main__":
    main()
