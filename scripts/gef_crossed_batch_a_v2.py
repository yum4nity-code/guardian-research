from pathlib import Path
import argparse, hashlib, json, math, os, re, tempfile, time, zipfile
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

ENGINE_VERSION="BATCH-A-V2-DISCOVERY-1.2"
DISCOVERY_START=pd.Timestamp("2013-01-01")
DISCOVERY_END=pd.Timestamp("2017-01-01")
HOLD_START=pd.Timestamp("2017-01-01")
HOLD_END=pd.Timestamp("2018-01-01")
WARMUP_START_YEAR=2012
DISCOVERY_END_YEAR=2016
HOLDOUT_YEAR=2017
FORBIDDEN_YEAR=2018

HORIZONS=[60,120,240]
BH_Q=0.05
HOLD_P_ONE=0.10
FAST_Z_MIN=250
RATE_Z_MIN=126
BETA_WINDOW=480
BETA_MIN=240
EVENT_Z=1.5
COOLDOWN_MIN=240
MIN_TRAIN_N=120
MIN_TRAIN_CLUSTERS=80
MIN_HOLD_N=40
MIN_HOLD_CLUSTERS=20
EXPECTED_VARIANTS=66

MARKETS=["XAUUSD","XAGUSD","UDXUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","SPXUSD","NSXUSD","WTIUSD","BCOUSD"]

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
        for ch in iter(lambda:f.read(1024*1024),b""):
            h.update(ch)
    return h.hexdigest()

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
    # Pandas DatetimeIndex internal int64 resolution is not guaranteed to be ns
    # on every runtime. Convert explicitly to datetime64[m] before integer modulo.
    minute=pd.DatetimeIndex(times).to_numpy(dtype="datetime64[m]").astype(np.int64)
    return (minute%int(h))==0

def period_mask(times,start,end,h):
    return np.asarray((times>=start)&(times<end)&((times+pd.Timedelta(minutes=int(h)))<=end))

def cluster_ols(y,X,clusters,coef_index):
    y=np.asarray(y,dtype=float);X=np.asarray(X,dtype=float);clusters=np.asarray(clusters,dtype=object)
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
    inv=np.linalg.inv(xtx);beta=inv@(X.T@y);resid=y-X@beta
    meat=np.zeros((k,k),dtype=float)
    for c in uniq:
        sel=codes==c;score=X[sel].T@resid[sel];meat+=np.outer(score,score)
    corr=(g/(g-1.0))*((n-1.0)/(n-k))
    vcov=corr*(inv@meat@inv)
    vv=float(vcov[coef_index,coef_index])
    se=math.sqrt(max(vv,0.0)) if np.isfinite(vv) else np.nan
    coef=float(beta[coef_index])
    if not np.isfinite(se) or se<=0:
        return {"n":n,"clusters":g,"coef":coef,"se":se,"t":np.nan,"p_two":np.nan}
    tv=coef/se;p=2*student_t.sf(abs(tv),df=max(g-1,1))
    return {"n":n,"clusters":g,"coef":coef,"se":se,"t":float(tv),"p_two":float(p)}

def bh_qvalues(p):
    p=np.asarray(p,dtype=float);q=np.full(len(p),np.nan)
    ok=np.flatnonzero(np.isfinite(p))
    if not len(ok): return q
    order=ok[np.argsort(p[ok],kind="mergesort")]
    m=len(order);running=1.0
    for rev,idx in enumerate(order[::-1],1):
        rank=m-rev+1;val=min(1.0,p[idx]*m/rank);running=min(running,val);q[idx]=running
    return q

def load_hour_prices(root,start_year,end_year):
    if end_year>=FORBIDDEN_YEAR:
        raise RuntimeError(f"Price loader refuses {end_year} >= {FORBIDDEN_YEAR}")
    grid=pd.date_range(f"{start_year}-01-01 00:00",f"{end_year}-12-31 23:00",freq="1h")
    P=pd.DataFrame(index=grid)
    for si,sym in enumerate(MARKETS,1):
        parts=[]
        for year in range(start_year,end_year+1):
            if year>=FORBIDDEN_YEAR: raise RuntimeError("Forbidden price year")
            p=root/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
            if not p.exists(): raise RuntimeError(f"Missing required price file {p}")
            d=pd.read_parquet(p)
            dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
            pc=next((c for c in d.columns if str(c).lower()=="close"),None)
            if dc is None and isinstance(d.index,pd.DatetimeIndex):
                d=d.reset_index();dc=d.columns[0]
            if dc is None or pc is None: raise RuntimeError(f"Cannot identify datetime/close in {p}")
            utc=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(hours=5)
            q=pd.DataFrame({"utc":utc,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
            q=q[q["utc"].dt.year==year]
            parts.append(q)
        q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
        five=q.set_index("utc")["px"].resample("5min",label="right",closed="left").last()
        P[sym]=five.reindex(grid).astype(float)
        print(f"[BATCH-A-V2] price {si}/{len(MARKETS)} {sym} {start_year}-{end_year}",flush=True)
    return P

def forward_return(P,sym,h):
    k=h//60
    return P[sym].shift(-k)/P[sym]-1

def parse_treasury(root,folder,prefix,end_year):
    if end_year>=FORBIDDEN_YEAR: raise RuntimeError("Treasury parser forbidden year")
    records=[]
    for y in range(2009,end_year+1):
        p=root/"DataLake"/"raw"/"treasury"/folder/f"{folder}_{y}.xml"
        if not p.exists(): continue
        tree=ET.parse(p).getroot()
        for entry in tree.iter():
            vals={}
            for x in entry.iter():
                tag=x.tag.split("}")[-1];txt=(x.text or "").strip()
                if txt and (tag.startswith("NEW_DATE") or tag.startswith("BC_") or tag.startswith("TC_") or tag=="NEW_DATE"):
                    vals[tag]=txt
            if vals: records.append(vals)
    if not records: raise RuntimeError("No Treasury records")
    d=pd.DataFrame(records).drop_duplicates()
    dc=next((c for c in d.columns if "DATE" in c),None)
    if dc is None: raise RuntimeError("Treasury date missing")
    d["obs_date"]=pd.to_datetime(d[dc],errors="coerce").dt.normalize()
    d=d.dropna(subset=["obs_date"]).sort_values("obs_date").drop_duplicates("obs_date",keep="last")
    out=pd.DataFrame(index=d["obs_date"])
    for c in d.columns:
        if c in [dc,"obs_date"]: continue
        v=pd.to_numeric(d[c],errors="coerce")
        if v.notna().sum()>=250: out[f"{prefix}_{c}"]=v.to_numpy()
    return out

def tenor_from_col(c):
    m=re.search(r"(?:BC_|TC_)(\d+)(MONTH|YEAR)",c)
    if not m:return None
    n=int(m.group(1));return n/12 if m.group(2)=="MONTH" else float(n)

def build_rate_objects(root,end_year,times):
    real=parse_treasury(root,"real_yield_curve","REAL",end_year)
    real_by={tenor_from_col(c):c for c in real.columns if tenor_from_col(c) is not None}
    out={};meta={}
    for ten in [5,10,30]:
        if ten not in real_by: raise RuntimeError(f"Missing REAL {ten}Y")
        col=real_by[ten]
        s=pd.to_numeric(real[col],errors="coerce")
        d1=s.diff(1)
        mu=d1.expanding(min_periods=RATE_Z_MIN).mean().shift(1)
        sd=d1.expanding(min_periods=RATE_Z_MIN).std().shift(1).replace(0,np.nan)
        z=(d1-mu)/sd
        src=pd.DataFrame({"AVAILABLE_AT":pd.DatetimeIndex(real.index)+pd.Timedelta(days=1),
                          "d1":d1.to_numpy(),"z":z.to_numpy()}).dropna(subset=["AVAILABLE_AT","z"]).sort_values("AVAILABLE_AT")
        base=pd.DataFrame({"decision_time":times})
        j=pd.merge_asof(base,src,left_on="decision_time",right_on="AVAILABLE_AT",direction="backward")
        out[ten]=pd.Series(pd.to_numeric(j["z"],errors="coerce").to_numpy(dtype=float),index=times)
        meta[ten]={"raw_column":col}
    return out,meta

def find_col(cols,needles):
    for c in cols:
        z=str(c).strip().lower()
        if any(n in z for n in needles):return c
    return None

def parse_report_date(d,cols):
    direct=find_col(cols,["report_date_as_mm_dd_yyyy","report date as mm dd yyyy","report_date_as_yyyy-mm-dd"])
    if direct is not None:return pd.to_datetime(d[direct],errors="coerce")
    compact=find_col(cols,["as_of_date_in_form_yymmdd","as of date in form yymmdd"])
    if compact is not None:
        s=d[compact].astype("string").str.replace(r"\.0$","",regex=True).str.zfill(6)
        return pd.to_datetime(s,format="%y%m%d",errors="coerce")
    return pd.Series(pd.NaT,index=d.index)

def load_cftc_normalized(root,end_year):
    if end_year>=FORBIDDEN_YEAR: raise RuntimeError("CFTC parser forbidden year")
    src=root/"DataLake"/"raw"/"cftc"/"futures_only_reports"
    archives=[];year_hits={}
    for y in range(2009,end_year+1):
        aa=[p for p in sorted(src.glob("*.zip")) if str(y) in p.name and "excel" in p.name.lower()]
        if aa: archives.extend(aa);year_hits[y]=len(aa)
    missing=[y for y in range(2013,end_year+1) if y not in year_hits]
    if missing: raise RuntimeError(f"Missing CFTC archives {missing}")
    parts=[]
    for j,p in enumerate(dict.fromkeys(archives),1):
        with zipfile.ZipFile(p) as zf:
            members=[m for m in zf.namelist() if m.lower().endswith((".xls",".xlsx"))]
            for member in members:
                suffix=Path(member).suffix
                with tempfile.NamedTemporaryFile(suffix=suffix,delete=False) as tf:
                    tf.write(zf.read(member));tmp=tf.name
                try:d=pd.read_excel(tmp)
                finally:
                    try:os.unlink(tmp)
                    except OSError:pass
                cols=list(d.columns)
                report_date=parse_report_date(d,cols)
                market=find_col(cols,["market and exchange names","market_and_exchange_names"])
                oi=find_col(cols,["open interest (all)","open_interest_all"])
                ncl=find_col(cols,["noncommercial positions-long","noncomm_positions_long_all"])
                ncs=find_col(cols,["noncommercial positions-short","noncomm_positions_short_all"])
                if any(x is None for x in [market,oi,ncl,ncs]): continue
                q=pd.DataFrame({"report_date":report_date,"market":d[market].astype("string"),
                    "open_interest":pd.to_numeric(d[oi],errors="coerce"),
                    "noncomm_long":pd.to_numeric(d[ncl],errors="coerce"),
                    "noncomm_short":pd.to_numeric(d[ncs],errors="coerce")})
                q=q[q["report_date"].notna()&q["market"].notna()&(q["open_interest"]>0)].copy()
                if q.empty:continue
                q["noncomm_net_pct_oi"]=(q["noncomm_long"]-q["noncomm_short"])/q["open_interest"]
                parts.append(q)
        if j==1 or j==len(archives) or j%5==0:
            print(f"[BATCH-A-V2] CFTC archive {j}/{len(archives)}",flush=True)
    if not parts:raise RuntimeError("No CFTC rows")
    D=pd.concat(parts,ignore_index=True)
    D=D[D["report_date"].dt.year.between(2009,end_year)].copy()
    wd=D["report_date"].dt.weekday;days=(7-wd)%7;days=days.where(days>0,7)
    D["AVAILABLE_AT"]=D["report_date"].dt.normalize()+pd.to_timedelta(days,unit="D")
    D=D.sort_values(["market","report_date"]).drop_duplicates(["market","report_date"],keep="last")
    return D

def build_cftc_objects(root,end_year,times):
    D=load_cftc_normalized(root,end_year)
    out={}
    for sym,name in CFTC_MAP.items():
        q=D[D["market"].astype(str)==name].sort_values("report_date").copy()
        if q.empty:raise RuntimeError(f"No CFTC market {sym}")
        s=pd.to_numeric(q["noncomm_net_pct_oi"],errors="coerce")
        mu=s.rolling(52,min_periods=26).mean();sd=s.rolling(52,min_periods=26).std().replace(0,np.nan)
        q["z52"]=(s-mu)/sd
        src=q[["AVAILABLE_AT","report_date","z52"]].dropna(subset=["AVAILABLE_AT"]).sort_values("AVAILABLE_AT").drop_duplicates("AVAILABLE_AT",keep="last")
        base=pd.DataFrame({"decision_time":times})
        j=pd.merge_asof(base,src,left_on="decision_time",right_on="AVAILABLE_AT",direction="backward")
        crowd=pd.Series(pd.to_numeric(j["z52"],errors="coerce").to_numpy(dtype=float),index=times)
        cluster=j["report_date"].dt.strftime("%Y-%m-%d").to_numpy(dtype=object)
        out[sym]=(crowd,cluster)
    return out

def latest_v83b(root):
    runs=sorted((root/"Research"/"Autonomous"/"guardian_edge_factory_v83b").glob("GEF83B-*"))
    runs=[p for p in runs if (p/"RUN_RECEIPT.json").exists() and (p/"REPAIRED_ARCHITECTURE_MANIFEST.json").exists()]
    if not runs:raise RuntimeError("No V83B")
    return runs[-1]

def parity_check_2013(root,P,out):
    v83b=latest_v83b(root)
    m=json.loads((v83b/"REPAIRED_ARCHITECTURE_MANIFEST.json").read_text())
    cols=[f"price_{s}_ret_60m" for s in MARKETS]
    oldF=pd.read_parquet(Path(m["price_state_5m_path"]),columns=cols)
    oldF.index=pd.to_datetime(oldF.index);oldF=oldF[(oldF.index.year==2013)&(oldF.index.minute==0)]
    tcols=[f"{s}_fwd_{h}m" for s in MARKETS for h in HORIZONS]
    oldY=pd.read_parquet(Path(m["targets_5m_path"]),columns=tcols)
    oldY.index=pd.to_datetime(oldY.index);oldY=oldY[(oldY.index.year==2013)&(oldY.index.minute==0)]
    rows=[]
    for s in MARKETS:
        now=P[s]/P[s].shift(1)-1
        a=now.reindex(oldF.index).to_numpy(dtype=float);b=pd.to_numeric(oldF[f"price_{s}_ret_60m"],errors="coerce").to_numpy(dtype=float)
        ok=np.isfinite(a)&np.isfinite(b);mx=float(np.max(np.abs(a[ok]-b[ok]))) if ok.any() else np.nan
        rows.append({"object":f"{s}_ret60","n":int(ok.sum()),"max_abs":mx})
        for h in HORIZONS:
            a=forward_return(P,s,h).reindex(oldY.index).to_numpy(dtype=float)
            b=pd.to_numeric(oldY[f"{s}_fwd_{h}m"],errors="coerce").to_numpy(dtype=float)
            ok=np.isfinite(a)&np.isfinite(b);mx=float(np.max(np.abs(a[ok]-b[ok]))) if ok.any() else np.nan
            rows.append({"object":f"{s}_fwd{h}","n":int(ok.sum()),"max_abs":mx})
    R=pd.DataFrame(rows);R.to_csv(out/"PRICE_PARITY_2013.csv",index=False)
    bad=R[(R["n"]<100)|(R["max_abs"]>2e-6)|(~np.isfinite(R["max_abs"]))]
    if len(bad):raise RuntimeError(f"2013 price parity failed: {bad.head(20).to_dict('records')}")
    return {"source_v83b":v83b.name,"objects":len(R),"max_abs":float(R["max_abs"].max()),"min_n":int(R["n"].min())}

class Variant:
    def __init__(self,lineage,variant,h,y,X,primary,event,clusters,meta):
        self.lineage=lineage;self.variant=variant;self.h=int(h);self.y=np.asarray(y,float);self.X=np.asarray(X,float)
        self.primary=int(primary);self.event=np.asarray(event,bool);self.clusters=np.asarray(clusters,object);self.meta=meta

def build_variants(root,P,end_year):
    times=P.index
    day=times.normalize().strftime("%Y-%m-%d").to_numpy(dtype=object)
    r60={s:P[s]/P[s].shift(1)-1 for s in MARKETS}
    rz={s:causal_z(r60[s],FAST_Z_MIN) for s in MARKETS}
    b_xau_udx=rolling_beta(r60["XAUUSD"],r60["UDXUSD"])
    b_cad_udx=rolling_beta(r60["USDCAD"],r60["UDXUSD"])
    b_nsx_spx=rolling_beta(r60["NSXUSD"],r60["SPXUSD"])
    b_xau_xag=rolling_beta(r60["XAUUSD"],r60["XAGUSD"])
    z_nsx_spx=causal_z(r60["NSXUSD"]-b_nsx_spx*r60["SPXUSD"],FAST_Z_MIN)
    z_xau_xag=causal_z(r60["XAUUSD"]-b_xau_xag*r60["XAGUSD"],FAST_Z_MIN)
    synthetic=pd.concat([-rz["EURUSD"],-rz["GBPUSD"],-rz["AUDUSD"],rz["USDJPY"],rz["USDCHF"],rz["USDCAD"]],axis=1).mean(axis=1,skipna=False)
    z_breadth=causal_z(rz["UDXUSD"]-synthetic,FAST_Z_MIN)
    rate_z,rate_meta=build_rate_objects(root,end_year,times)
    cftc=build_cftc_objects(root,end_year,times)
    ev_oil={s:cooldown_mask(times,rz[s].to_numpy()) for s in ["WTIUSD","BCOUSD"]}
    ev_breadth=cooldown_mask(times,z_breadth.to_numpy())
    ev_xau_xag=cooldown_mask(times,z_xau_xag.to_numpy())
    variants=[]
    for ten in [5,10,30]:
        zr=rate_z[ten].to_numpy();zu=rz["UDXUSD"].to_numpy()
        X=np.column_stack([np.ones(len(times)),zr,zu,zr*zu])
        for h in HORIZONS:
            y=forward_return(P,"XAUUSD",h).to_numpy()-b_xau_udx.to_numpy()*forward_return(P,"UDXUSD",h).to_numpy()
            variants.append(Variant("P01",f"REAL{ten}YxUDX",h,y,X,3,np.ones(len(times),bool),day,{"real_tenor":ten,**rate_meta[ten]}))
    for leader in ["WTIUSD","BCOUSD"]:
        z=rz[leader].to_numpy();X=np.column_stack([np.ones(len(times)),z])
        for h in HORIZONS:
            y=forward_return(P,"USDCAD",h).to_numpy()-b_cad_udx.to_numpy()*forward_return(P,"UDXUSD",h).to_numpy()
            variants.append(Variant("P04",leader,h,y,X,1,ev_oil[leader],day,{"leader":leader}))
    zd=z_nsx_spx.to_numpy()
    for ten in [5,10,30]:
        zr=rate_z[ten].to_numpy();X=np.column_stack([np.ones(len(times)),zd,zr,zd*zr])
        for h in HORIZONS:
            y=forward_return(P,"NSXUSD",h).to_numpy()-b_nsx_spx.to_numpy()*forward_return(P,"SPXUSD",h).to_numpy()
            variants.append(Variant("P06",f"NSXSPXxREAL{ten}Y",h,y,X,3,np.ones(len(times),bool),day,{"real_tenor":ten,**rate_meta[ten]}))
    zb=z_breadth.to_numpy();Xb=np.column_stack([np.ones(len(times)),zb])
    for target in ["UDXUSD","XAUUSD","XAGUSD"]:
        for h in [60,120]:
            variants.append(Variant("P08",f"BREADTH->{target}",h,forward_return(P,target,h).to_numpy(),Xb,1,ev_breadth,day,{"target":target}))
    zx=z_xau_xag.to_numpy();Xx=np.column_stack([np.ones(len(times)),zx])
    for h in HORIZONS:
        y=forward_return(P,"XAUUSD",h).to_numpy()-b_xau_xag.to_numpy()*forward_return(P,"XAGUSD",h).to_numpy()
        variants.append(Variant("P11","XAU_RESID_XAG",h,y,Xx,1,ev_xau_xag,day,{}))
    for sym in CFTC_MAP:
        crowd,clusters=cftc[sym];shock=rz[sym];ev=cooldown_mask(times,shock.to_numpy())
        X=np.column_stack([np.ones(len(times)),crowd.to_numpy(),shock.to_numpy(),crowd.to_numpy()*shock.to_numpy()])
        for h in HORIZONS:
            variants.append(Variant("P12",sym,h,forward_return(P,sym,h).to_numpy(),X,3,ev,clusters,{"market":sym}))
    if len(variants)!=EXPECTED_VARIANTS:raise RuntimeError(f"Variant count {len(variants)} != {EXPECTED_VARIANTS}")
    return variants

def score_period(variants,times,start,end,min_n,min_clusters):
    rows=[]
    for i,v in enumerate(variants,1):
        mask=period_mask(times,start,end,v.h)&aligned_mask(times,v.h)&v.event
        fit=cluster_ols(np.where(mask,v.y,np.nan),v.X,v.clusters,v.primary)
        valid=bool(fit["n"]>=min_n and fit["clusters"]>=min_clusters and np.isfinite(fit["p_two"]))
        rows.append({"lineage":v.lineage,"variant":v.variant,"horizon_min":v.h,"n":fit["n"],"clusters":fit["clusters"],
                     "coef":fit["coef"],"coef_bp":fit["coef"]*1e4 if np.isfinite(fit["coef"]) else np.nan,
                     "t":fit["t"],"p_two":fit["p_two"],"valid":valid,"meta_json":json.dumps(v.meta,sort_keys=True)})
        if i==1 or i==len(variants) or i%10==0:print(f"[BATCH-A-V2] score {i}/{len(variants)}",flush=True)
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root);repo=root/"guardian-research"
    spec=repo/"research"/"campaigns"/"GEF_BATCH_A_V2_FROZEN_SPEC_2026_09_22.json"
    if not spec.exists():raise RuntimeError("Missing V2 frozen spec")
    so=json.loads(spec.read_text())
    if so.get("status")!="FROZEN_BEFORE_V2_COMPUTE":raise RuntimeError("V2 spec not frozen")
    base=root/"Research"/"Autonomous"/"guardian_crossed_batch_a_v2"
    base.mkdir(parents=True,exist_ok=True)
    rid="GEFBA2-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    out=base/rid;out.mkdir(parents=True,exist_ok=False)
    t0=time.time()
    def status(i,n,msg,**extra):
        p={"run_id":rid,"engine_version":ENGINE_VERSION,"step":i,"steps":n,"elapsed_s":round(time.time()-t0,1),"message":msg,**extra}
        write_json(out/"LIVE_STATUS.json",p)
        tail=" | ".join(f"{k}={v}" for k,v in extra.items());print(f"[BATCH-A-V2] {i}/{n} | {msg}"+(f" | {tail}" if tail else ""),flush=True)

    status(1,14,"load 2012-2016 prices only; 2017 holdout still unopened")
    P=load_hour_prices(root,2012,2016)
    status(2,14,"2012-2016 hourly price matrix built",rows=len(P),markets=P.shape[1])

    parity=parity_check_2013(root,P,out)
    status(3,14,"2013 reconstruction parity exact vs V83/V83B",**parity)

    variants=build_variants(root,P,2016)
    status(4,14,"2013-2016 economic objects built from raw rates/CFTC",variants=len(variants))

    D=score_period(variants,P.index,DISCOVERY_START,DISCOVERY_END,MIN_TRAIN_N,MIN_TRAIN_CLUSTERS)
    D["bh_q"]=np.nan
    for lin,g in D.groupby("lineage"):
        idx=g.index.to_numpy();pv=np.where(g["valid"].to_numpy(bool),g["p_two"].to_numpy(float),np.nan)
        D.loc[idx,"bh_q"]=bh_qvalues(pv)
    D["bh_pass"]=D["valid"]&(D["bh_q"]<=BH_Q)
    D.to_csv(out/"DISCOVERY_2013_2016_ALL.csv",index=False)
    status(5,14,"2013-2016 discovery complete",valid_tests=int(D["valid"].sum()),bh_discoveries=int(D["bh_pass"].sum()))

    frozen=D[D["bh_pass"]].copy()
    frozen.to_csv(out/"FROZEN_AFTER_DISCOVERY_BEFORE_2017.csv",index=False)
    frozen_sha=sha256(out/"FROZEN_AFTER_DISCOVERY_BEFORE_2017.csv")
    write_json(out/"DISCOVERY_FREEZE_RECEIPT.json",{
        "run_id":rid,"status":"DISCOVERY_FROZEN_BEFORE_2017","frozen_count":len(frozen),"frozen_sha256":frozen_sha,
        "2017_accessed":False,"2018_plus_accessed":False,"2023_2025_accessed":False,"2026_accessed":False})
    status(6,14,"discovery freeze physically written before any 2017 access",frozen=len(frozen),sha=frozen_sha[:16])

    if frozen.empty:
        summary=D.groupby("lineage").agg(predeclared_tests=("lineage","size"),valid_tests=("valid","sum"),bh_discoveries=("bh_pass","sum")).reset_index()
        summary["holdout_tested"]=0;summary["temporal_survivors"]=0
        summary.to_csv(out/"LINEAGE_SUMMARY.csv",index=False)
        receipt={"run_id":rid,"status":"COMPLETE_BATCH_A_V2_NO_DISCOVERY_SURVIVORS","engine_version":ENGINE_VERSION,
                 "predeclared_variants":EXPECTED_VARIANTS,"valid_discovery_tests":int(D["valid"].sum()),"bh_discoveries":0,
                 "2017_accessed":False,"2018_plus_accessed":False,"2023_2025_accessed":False,"2026_accessed":False,
                 "next":"CLOSE_V2_BATCH_A_LINEAGES_AT_DISCOVERY_NO_RETUNING"}
        write_json(out/"RUN_RECEIPT.json",receipt);status(14,14,"DONE; 2017 never opened")
        print("\n=== BATCH A V2 RECEIPT ===");print(json.dumps(receipt,indent=2))
        print("\n=== BATCH A V2 LINEAGE SUMMARY ===");print(summary.to_string(index=False))
        print("\n=== BATCH A V2 FROZEN PRE-REPLICATION SURVIVORS ===\nNONE")
        print("\nRUN:",out);return

    status(7,14,"BH discoveries exist; now opening only 2017 holdout")
    P17=load_hour_prices(root,2012,2017)
    status(8,14,"2017 prices opened after discovery freeze",rows=len(P17))
    variants17=build_variants(root,P17,2017)
    lookup={(v.lineage,v.variant,v.h):v for v in variants17}

    rows=[]
    for r in frozen.itertuples(index=False):
        v=lookup[(r.lineage,r.variant,int(r.horizon_min))]
        mask=period_mask(P17.index,HOLD_START,HOLD_END,v.h)&aligned_mask(P17.index,v.h)&v.event
        fit=cluster_ols(np.where(mask,v.y,np.nan),v.X,v.clusters,v.primary)
        sign=1 if r.coef>0 else -1
        same=bool(np.isfinite(fit["coef"]) and fit["coef"]!=0 and np.sign(fit["coef"])==sign)
        p_one=float(student_t.sf(abs(fit["t"]),df=max(fit["clusters"]-1,1))) if same and np.isfinite(fit["t"]) else np.nan
        passed=bool(fit["n"]>=MIN_HOLD_N and fit["clusters"]>=MIN_HOLD_CLUSTERS and same and np.isfinite(p_one) and p_one<=HOLD_P_ONE)
        rows.append({"lineage":r.lineage,"variant":r.variant,"horizon_min":int(r.horizon_min),
                     "discovery_coef_bp":float(r.coef_bp),"discovery_bh_q":float(r.bh_q),
                     "holdout_n":fit["n"],"holdout_clusters":fit["clusters"],"holdout_coef":fit["coef"],
                     "holdout_coef_bp":fit["coef"]*1e4 if np.isfinite(fit["coef"]) else np.nan,
                     "holdout_t":fit["t"],"holdout_p_one_frozen_sign":p_one,"same_sign_2017":same,
                     "holdout_pass":passed,"meta_json":r.meta_json})
    H=pd.DataFrame(rows);H.to_csv(out/"TEMPORAL_HOLDOUT_2017.csv",index=False)
    survivors=H[H["holdout_pass"]].copy();survivors.to_csv(out/"FROZEN_PRE_REPLICATION_SURVIVORS.csv",index=False)
    status(9,14,"2017 holdout complete",tested=len(H),survivors=len(survivors))

    summary=[]
    for lin in ["P01","P04","P06","P08","P11","P12"]:
        g=D[D["lineage"]==lin];h=H[H["lineage"]==lin];s=survivors[survivors["lineage"]==lin]
        summary.append({"lineage":lin,"predeclared_tests":len(g),"valid_tests":int(g["valid"].sum()),
                        "bh_discoveries":int(g["bh_pass"].sum()),"holdout_tested":len(h),"temporal_survivors":len(s)})
    S=pd.DataFrame(summary);S.to_csv(out/"LINEAGE_SUMMARY.csv",index=False)
    status(10,14,"lineage accounting complete")

    write_json(out/"RUNTIME_PROVENANCE.json",{
        "run_id":rid,"engine_version":ENGINE_VERSION,"frozen_spec_sha256":sha256(spec),"price_parity":parity,
        "discovery_years":[2013,2014,2015,2016],"holdout_year":[2017],"2018_plus_accessed":False,
        "2023_2025_accessed":False,"2026_accessed":False})
    status(11,14,"runtime provenance written")

    receipt={"run_id":rid,"status":"COMPLETE_CROSSED_PHENOMENA_BATCH_A_V2","engine_version":ENGINE_VERSION,
             "predeclared_variants":EXPECTED_VARIANTS,"valid_discovery_tests":int(D["valid"].sum()),
             "bh_discoveries":int(D["bh_pass"].sum()),"holdout_tested":len(H),"temporal_survivors":len(survivors),
             "survivors_by_lineage":{r.lineage:int(r.temporal_survivors) for r in S.itertuples()},
             "frozen_survivor_sha256":sha256(out/"FROZEN_PRE_REPLICATION_SURVIVORS.csv"),
             "2017_accessed":True,"2018_plus_accessed":False,"2023_2025_accessed":False,"2026_accessed":False,
             "next":"IF SURVIVORS: PREREGISTER 2018-2019 REPLICATION WITHOUT RETUNING; ELSE CLOSE V2 LINEAGES"}
    write_json(out/"RUN_RECEIPT.json",receipt)
    status(12,14,"receipt written")
    status(13,14,"2018+ remains unopened")
    status(14,14,"DONE")

    print("\n=== BATCH A V2 RECEIPT ===");print(json.dumps(receipt,indent=2))
    print("\n=== BATCH A V2 LINEAGE SUMMARY ===");print(S.to_string(index=False))
    print("\n=== BATCH A V2 FROZEN PRE-REPLICATION SURVIVORS ===")
    if len(survivors):
        print(survivors[["lineage","variant","horizon_min","discovery_coef_bp","discovery_bh_q","holdout_n","holdout_clusters","holdout_coef_bp","holdout_p_one_frozen_sign"]].to_string(index=False))
    else:print("NONE")
    print("\nRUN:",out)

if __name__=="__main__":
    main()
