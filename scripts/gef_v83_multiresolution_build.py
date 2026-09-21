from pathlib import Path
import pandas as pd
import numpy as np
import json, time, hashlib, re, xml.etree.ElementTree as ET

ROOT=Path(r"D:\MT5_Backtests")
DL=ROOT/"DataLake"
RID="GEF83-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v83"/RID
OUT.mkdir(parents=True,exist_ok=True)
T0=time.time()
MARKETS=["XAUUSD","XAGUSD","UDXUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","SPXUSD","NSXUSD","WTIUSD","BCOUSD"]
HORIZONS_MIN=[5,15,30,60,120,240]

def write_status(stage,message,**extra):
    payload={"run_id":RID,"stage":stage,"elapsed_s":round(time.time()-T0,1),"message":message,**extra}
    (OUT/"LIVE_STATUS.json").write_text(json.dumps(payload,indent=2,default=str),encoding="utf-8")
    extras=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF83] {stage} | elapsed {(time.time()-T0)/60:.1f}m | {message}"+(f" | {extras}" if extras else ""),flush=True)

def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def dedup_vectors(df):
    seen=set(); keep=[]
    for c in df.columns:
        s=df[c]
        h=hashlib.sha256(pd.util.hash_pandas_object(s.fillna(-9.87654321e307),index=False).values.tobytes()).hexdigest()
        if h not in seen:
            seen.add(h);keep.append(c)
    return df[keep].copy()

def merge_asof_to_grid(grid,src,time_col,value_cols):
    base=pd.DataFrame({"decision_time_utc":grid})
    q=src[[time_col]+value_cols].dropna(subset=[time_col]).sort_values(time_col).drop_duplicates(time_col,keep="last")
    z=pd.merge_asof(base,q,left_on="decision_time_utc",right_on=time_col,direction="backward")
    z.index=grid
    return z[value_cols]

write_status("1/14","locate frozen upstream artifacts; zero edge search")
v80c_runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v80c").glob("GEF80C-*"))
v82d_runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v82d").glob("GEF82D-*"))
if not v80c_runs or not v82d_runs: raise RuntimeError("Missing V80C or V82D upstream run")
V80C=v80c_runs[-1]
cftc_path=DL/"normalized"/"cftc_pre2023"/"CFTC_FUTURES_ONLY_2009_2013_CAUSAL_V82D.parquet"
if not cftc_path.exists(): raise RuntimeError(f"Missing validated CFTC file {cftc_path}")

write_status("2/14","load V80C and quarantine revised FRED + old hourly price state")
base=pd.read_parquet(V80C/"CAUSAL_STATE_MATRIX_2010_2013_FULL.parquet");base.index=pd.to_datetime(base.index)
safe_prefixes=("alfred_","cboe_vol_","cfe_","financial_conditions_","treasury_auctions_")
safe_cols=[c for c in base.columns if str(c).startswith(safe_prefixes)]
S=base[safe_cols].copy();S=S.loc[:,~S.columns.duplicated()]
write_status("3/14","safe inherited slow families selected",rows=len(S),features=S.shape[1],fred_quarantined=sum(str(c).startswith("fred_") for c in base.columns))

def parse_treasury(folder,prefix):
    records=[]
    for y in range(2009,2014):
        p=DL/"raw"/"treasury"/folder/f"{folder}_{y}.xml"
        if not p.exists(): continue
        root=ET.parse(p).getroot()
        for entry in root.iter():
            vals={}
            for x in entry.iter():
                tag=x.tag.split("}")[-1];txt=(x.text or "").strip()
                if txt and (tag.startswith("NEW_DATE") or tag.startswith("BC_") or tag.startswith("TC_") or tag=="NEW_DATE"):
                    vals[tag]=txt
            if vals: records.append(vals)
    if not records: return pd.DataFrame()
    d=pd.DataFrame(records).drop_duplicates()
    dc=next((c for c in d.columns if "DATE" in c),None)
    if dc is None: raise RuntimeError(f"No date field in Treasury {folder}")
    d["obs_date"]=pd.to_datetime(d[dc],errors="coerce").dt.normalize()
    d=d.dropna(subset=["obs_date"]).sort_values("obs_date").drop_duplicates("obs_date",keep="last")
    out=pd.DataFrame(index=d["obs_date"])
    for c in d.columns:
        if c in [dc,"obs_date"]: continue
        v=pd.to_numeric(d[c],errors="coerce")
        if v.notna().sum()>=250: out[f"{prefix}_{c}"]=v.to_numpy()
    return out

write_status("4/14","parse official Treasury nominal + real curves 2009-2013")
nom=parse_treasury("nominal_yield_curve","NOM");real=parse_treasury("real_yield_curve","REAL")
if nom.empty or real.empty: raise RuntimeError(f"Treasury parse failed nominal={nom.shape} real={real.shape}")

def tenor_from_col(c):
    m=re.search(r"(?:BC_|TC_)(\d+)(MONTH|YEAR)",c)
    if not m:return None
    n=int(m.group(1));return n/12 if m.group(2)=="MONTH" else float(n)

rates=pd.concat([nom,real],axis=1).sort_index()
nom_by={tenor_from_col(c):c for c in nom.columns if tenor_from_col(c) is not None}
real_by={tenor_from_col(c):c for c in real.columns if tenor_from_col(c) is not None}
for ten in sorted(set(nom_by).intersection(real_by)):
    label=(f"{int(ten*12)}M" if ten<1 else f"{int(ten)}Y")
    rates[f"BE_{label}"]=rates[nom_by[ten]]-rates[real_by[ten]]
for a,b in [(2,10),(5,10),(10,30),(5,30)]:
    if a in nom_by and b in nom_by: rates[f"NOM_SLOPE_{b}Y_{a}Y"]=rates[nom_by[b]]-rates[nom_by[a]]
    if a in real_by and b in real_by: rates[f"REAL_SLOPE_{b}Y_{a}Y"]=rates[real_by[b]]-rates[real_by[a]]

parts=[]
for c in rates.columns:
    s=pd.to_numeric(rates[c],errors="coerce")
    parts += [s.rename(f"rates_yields_{c}_level"),s.diff(1).rename(f"rates_yields_{c}_d1"),s.diff(5).rename(f"rates_yields_{c}_d5")]
    mu=s.rolling(252,min_periods=126).mean();sd=s.rolling(252,min_periods=126).std().replace(0,np.nan)
    parts.append(((s-mu)/sd).rename(f"rates_yields_{c}_z252"))
RF=pd.concat(parts,axis=1);RF["AVAILABLE_AT"]=pd.DatetimeIndex(RF.index)+pd.Timedelta(days=1);RF=RF.reset_index(drop=True)
Rjoined=merge_asof_to_grid(S.index,RF,"AVAILABLE_AT",[c for c in RF.columns if c!="AVAILABLE_AT"])
S=pd.concat([S,Rjoined],axis=1)
write_status("5/14","rates joined causally to hourly slow grid",rate_features=Rjoined.shape[1],slow_features=S.shape[1])

C=pd.read_parquet(cftc_path);C["report_date"]=pd.to_datetime(C["report_date"]);C["AVAILABLE_AT"]=pd.to_datetime(C["AVAILABLE_AT"])
CFTC_MAP={
"XAUUSD":"GOLD - COMMODITY EXCHANGE INC.","XAGUSD":"SILVER - COMMODITY EXCHANGE INC.","EURUSD":"EURO FX - CHICAGO MERCANTILE EXCHANGE",
"GBPUSD":"BRITISH POUND STERLING - CHICAGO MERCANTILE EXCHANGE","USDJPY":"JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE",
"AUDUSD":"AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE","USDCAD":"CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",
"USDCHF":"SWISS FRANC - CHICAGO MERCANTILE EXCHANGE","SPXUSD":"E-MINI S&P 500 STOCK INDEX - CHICAGO MERCANTILE EXCHANGE",
"NSXUSD":"NASDAQ-100 STOCK INDEX (MINI) - CHICAGO MERCANTILE EXCHANGE","WTIUSD":"CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE"}
missing=[(k,v) for k,v in CFTC_MAP.items() if not (C["market"].astype(str)==v).any()]
if missing: raise RuntimeError(f"Missing exact CFTC canonical mappings: {missing}")
write_status("6/14","exact CFTC mappings frozen",mapped_markets=len(CFTC_MAP),cftc_rows=len(C))

for sym,name in CFTC_MAP.items():
    q=C[C["market"].astype(str)==name].sort_values("report_date").copy()
    for field in ["commercial_net_pct_oi","noncomm_net_pct_oi"]:
        s=pd.to_numeric(q[field],errors="coerce");stem=f"cftc_{sym}_{field}"
        q[stem+"_level"]=s;q[stem+"_d1w"]=s.diff(1);q[stem+"_d4w"]=s.diff(4)
        mu=s.rolling(52,min_periods=26).mean();sd=s.rolling(52,min_periods=26).std().replace(0,np.nan)
        q[stem+"_z52"]=(s-mu)/sd
    vals=[c for c in q.columns if c.startswith("cftc_")]
    S=pd.concat([S,merge_asof_to_grid(S.index,q,"AVAILABLE_AT",vals)],axis=1)
S=S.loc[:,~S.columns.duplicated()];S=dedup_vectors(S)
slow_path=OUT/"SLOW_CAUSAL_STATE_2010_2013.parquet";S.to_parquet(slow_path)
write_status("7/14","corrected slow matrix written",rows=len(S),features=S.shape[1],sha=sha256(slow_path)[:12])

def load_m1(sym):
    ps=[]
    for y in range(2009,2014):
        p=DL/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
        if not p.exists():continue
        d=pd.read_parquet(p);dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None);pc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None and isinstance(d.index,pd.DatetimeIndex):d=d.reset_index();dc=d.columns[0]
        if dc is None or pc is None:continue
        utc=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(hours=5)
        q=pd.DataFrame({"utc":utc,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
        q=q[q["utc"].dt.year.between(2009,2013)];ps.append(q)
    if not ps:return None
    q=pd.concat(ps,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    return q.set_index("utc")["px"]

grid=pd.date_range("2010-01-01 00:00","2013-12-31 23:55",freq="5min")
P=pd.DataFrame(index=grid);coverage=[]
write_status("8/14","build 5-minute causal price grid",grid_rows=len(grid),markets=len(MARKETS))
for i,sym in enumerate(MARKETS,1):
    raw=load_m1(sym)
    if raw is None:
        coverage.append({"market":sym,"status":"MISSING"});write_status("8/14",f"price {i}/{len(MARKETS)} {sym} MISSING");continue
    five=raw.resample("5min",label="right",closed="left").last().reindex(grid)
    P[sym]=five.astype("float64")
    coverage.append({"market":sym,"status":"OK","non_null":int(five.notna().sum()),"first":str(five.first_valid_index()),"last":str(five.last_valid_index())})
    write_status("8/14",f"price {i}/{len(MARKETS)} {sym}",market_progress=f"{i}/{len(MARKETS)}",non_null=int(five.notna().sum()))
if sum(x["status"]=="OK" for x in coverage)!=len(MARKETS):raise RuntimeError(f"Missing price markets: {[x for x in coverage if x['status']!='OK']}")
P.index.name="decision_time_utc";price_path=OUT/"PRICE_5M_2010_2013.parquet";P.to_parquet(price_path);pd.DataFrame(coverage).to_csv(OUT/"PRICE_COVERAGE.csv",index=False)
write_status("9/14","5-minute price matrix written",price_rows=len(P),price_markets=P.shape[1],sha=sha256(price_path)[:12])

F=pd.DataFrame(index=grid)
for sym in MARKETS:
    p=P[sym];r5=p.pct_change(1,fill_method=None)
    for mins in HORIZONS_MIN:
        k=mins//5;F[f"price_{sym}_ret_{mins}m"]=(p/p.shift(k)-1).astype("float32")
    for mins in [30,60,240]:
        k=mins//5;F[f"price_{sym}_rv_{mins}m"]=r5.rolling(k,min_periods=max(3,k//2)).std().astype("float32")
    for mins in [60,240]:
        k=mins//5;F[f"price_{sym}_trend_{mins}m"]=(p/p.shift(k)-1).astype("float32")
        mu=r5.rolling(k,min_periods=max(3,k//2)).mean();sd=r5.rolling(k,min_periods=max(3,k//2)).std().replace(0,np.nan)
        F[f"price_{sym}_zret_{mins}m"]=((r5-mu)/sd).astype("float32")
ret5=[f"price_{s}_ret_5m" for s in MARKETS]
F["price_cross_dispersion_5m"]=F[ret5].std(axis=1).astype("float32")
F["price_cross_positive_fraction_5m"]=((F[ret5]>0).sum(axis=1)/F[ret5].notna().sum(axis=1).replace(0,np.nan)).astype("float32")
mod=grid.hour*60+grid.minute
F["time_sin_day"]=np.sin(2*np.pi*mod/1440).astype("float32");F["time_cos_day"]=np.cos(2*np.pi*mod/1440).astype("float32")
F["time_sin_week"]=np.sin(2*np.pi*(grid.dayofweek*1440+mod)/(7*1440)).astype("float32");F["time_cos_week"]=np.cos(2*np.pi*(grid.dayofweek*1440+mod)/(7*1440)).astype("float32")
feature_path=OUT/"PRICE_STATE_5M_2010_2013.parquet";F.to_parquet(feature_path)
write_status("10/14","5-minute price-state features written",features=F.shape[1],sha=sha256(feature_path)[:12])

Y=pd.DataFrame(index=grid)
for sym in MARKETS:
    p=P[sym]
    for mins in HORIZONS_MIN:
        k=mins//5;y=p.shift(-k)/p-1
        Y[f"{sym}_fwd_{mins}m"]=y.astype("float32");Y[f"{sym}_sign_{mins}m"]=(y>0).where(y.notna()).astype("float32")
Y.index.name="decision_time_utc";target_path=OUT/"FUTURE_TARGETS_5M_2010_2013.parquet";Y.to_parquet(target_path)
write_status("11/14","minute targets written separately",target_columns=Y.shape[1],horizons=HORIZONS_MIN,sha=sha256(target_path)[:12])

slow_idx=S.index.values.astype("datetime64[ns]");fast_idx=grid.values.astype("datetime64[ns]")
bridge=np.searchsorted(slow_idx,fast_idx,side="right")-1;bridge[bridge<0]=-1
np.save(OUT/"SLOW_ROW_ASOF_FOR_5M.npy",bridge.astype(np.int32))
bridge_spec={"fast_rows":len(grid),"slow_rows":len(S),"rule":"latest slow row timestamp <= 5m decision time","negative_rows":int((bridge<0).sum())}
(OUT/"ASOF_BRIDGE_SPEC.json").write_text(json.dumps(bridge_spec,indent=2),encoding="utf-8")
write_status("12/14","5m->slow causal bridge written",**bridge_spec)

family_counts={"slow_safe_inherited":sum(not (str(c).startswith("rates_yields_") or str(c).startswith("cftc_")) for c in S.columns),"rates_yields":sum(str(c).startswith("rates_yields_") for c in S.columns),"cftc":sum(str(c).startswith("cftc_") for c in S.columns),"price_state_5m":F.shape[1],"targets_return":sum("_fwd_" in c for c in Y.columns),"targets_sign":sum("_sign_" in c for c in Y.columns)}
exclusions={"revised_fred":"excluded; observation_date+1d is not vintage reconstruction","eia":"blocked until exact AVAILABLE_AT semantics","old_hourly_price_state":"replaced by 5m price layer","old_hour_targets":"coarse diagnostics only; not used by corrected intraday search"}
(OUT/"FEATURE_FAMILY_COUNTS.json").write_text(json.dumps(family_counts,indent=2),encoding="utf-8");(OUT/"EXCLUSIONS.json").write_text(json.dumps(exclusions,indent=2),encoding="utf-8")
write_status("13/14","family accounting + exclusions written",families=family_counts)

receipt={"run_id":RID,"status":"COMPLETE_CORRECTED_MULTIRESOLUTION_CAUSAL_ARCHITECTURE","window":"2010-2013 discovery only; 2009 warmup where available","slow_rows":len(S),"slow_features":S.shape[1],"price_rows_5m":len(P),"price_markets":P.shape[1],"price_features_5m":F.shape[1],"target_columns":Y.shape[1],"target_horizons_minutes":HORIZONS_MIN,"family_counts":family_counts,"histdata_timezone":"raw HistData fixed EST UTC-5 -> UTC +5h","targets_separate":True,"edge_trials":0,"2014_plus_accessed":False,"2023_plus_accessed":False,"protected_2026_accessed":False,"next":"V84_VECTORIZED_HIERARCHICAL_CONCORDANCE_BENCHMARK_ON_CORRECTED_LAYERS"}
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
write_status("14/14","DONE; corrected layers ready for benchmark",next=receipt["next"])
print("\n=== V83 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== PRICE COVERAGE ===");print(pd.DataFrame(coverage).to_string(index=False));print("\n=== EXCLUSIONS ===");print(json.dumps(exclusions,indent=2));print("\nRUN:",OUT)
