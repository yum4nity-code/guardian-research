from pathlib import Path
import pandas as pd
import numpy as np
import json, time, re, hashlib, xml.etree.ElementTree as ET

ROOT=Path(r"D:\MT5_Backtests")
DL=ROOT/"DataLake"
RID="GEF83B-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v83b"/RID
OUT.mkdir(parents=True,exist_ok=True)
T0=time.time()

def status(i,n,msg,**extra):
    e=time.time()-T0
    payload={"run_id":RID,"step":i,"steps":n,"percent":round(100*i/n,1),
             "elapsed_s":round(e,1),"message":msg,**extra}
    (OUT/"LIVE_STATUS.json").write_text(json.dumps(payload,indent=2,default=str),encoding="utf-8")
    extras=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF83B] {i}/{n} {100*i/n:.0f}% | elapsed {e:.1f}s | {msg}"+(f" | {extras}" if extras else ""),flush=True)

def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def parse_treasury(folder,prefix):
    records=[]
    for y in range(2009,2014):
        p=DL/"raw"/"treasury"/folder/f"{folder}_{y}.xml"
        if not p.exists():
            continue
        root=ET.parse(p).getroot()
        for entry in root.iter():
            vals={}
            for x in entry.iter():
                tag=x.tag.split("}")[-1]
                txt=(x.text or "").strip()
                if txt and (tag.startswith("NEW_DATE") or tag.startswith("BC_") or tag.startswith("TC_") or tag=="NEW_DATE"):
                    vals[tag]=txt
            if vals:
                records.append(vals)
    if not records:
        return pd.DataFrame()
    d=pd.DataFrame(records).drop_duplicates()
    dc=next((c for c in d.columns if "DATE" in c),None)
    if dc is None:
        raise RuntimeError(f"No date field in Treasury {folder}")
    d["obs_date"]=pd.to_datetime(d[dc],errors="coerce").dt.normalize()
    d=d.dropna(subset=["obs_date"]).sort_values("obs_date").drop_duplicates("obs_date",keep="last")
    out=pd.DataFrame(index=d["obs_date"])
    for c in d.columns:
        if c in [dc,"obs_date"]:
            continue
        v=pd.to_numeric(d[c],errors="coerce")
        if v.notna().sum()>=250:
            out[f"{prefix}_{c}"]=v.to_numpy()
    return out

def tenor_from_col(c):
    m=re.search(r"(?:BC_|TC_)(\d+)(MONTH|YEAR)",c)
    if not m:
        return None
    n=int(m.group(1))
    return n/12 if m.group(2)=="MONTH" else float(n)

def featurewise_asof(grid, frame):
    base=pd.DataFrame({"decision_time_utc":grid})
    cols={}
    for c in frame.columns:
        if c=="AVAILABLE_AT":
            continue
        src=pd.DataFrame({
            "AVAILABLE_AT":frame["AVAILABLE_AT"],
            c:pd.to_numeric(frame[c],errors="coerce")
        }).dropna(subset=["AVAILABLE_AT",c]).sort_values("AVAILABLE_AT").drop_duplicates("AVAILABLE_AT",keep="last")
        if len(src)<4:
            continue
        z=pd.merge_asof(base,src,left_on="decision_time_utc",right_on="AVAILABLE_AT",direction="backward")
        cols[c]=z[c].to_numpy()
    return pd.DataFrame(cols,index=grid)

# Deterministic preflight for pandas column-access hazards used later in this script.
_test=pd.DataFrame({"coverage":[0.5],"nunique":[10],"feature":["x_level"]})
assert bool(((_test["coverage"]>=.45)&(_test["nunique"]>=10)).iloc[0])
assert bool(_test["feature"].str.endswith("_level",na=False).iloc[0])
del _test

status(1,9,"load latest completed V83; repair rates only, no edge search")
runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v83").glob("GEF83-*"))
runs=[p for p in runs if (p/"RUN_RECEIPT.json").exists()]
if not runs:
    raise RuntimeError("No completed V83")
V83=runs[-1]
r83=json.loads((V83/"RUN_RECEIPT.json").read_text())
if r83.get("status")!="COMPLETE_CORRECTED_MULTIRESOLUTION_CAUSAL_ARCHITECTURE":
    raise RuntimeError("Latest V83 is not complete")
S=pd.read_parquet(V83/"SLOW_CAUSAL_STATE_2010_2013.parquet")
S.index=pd.to_datetime(S.index)
old_rate_cols=[c for c in S.columns if str(c).startswith("rates_yields_")]
S=S.drop(columns=old_rate_cols)
status(2,9,"removed poisoned V83 rate columns",old_rate_columns=len(old_rate_cols),remaining_features=S.shape[1])

nom=parse_treasury("nominal_yield_curve","NOM")
real=parse_treasury("real_yield_curve","REAL")
if nom.empty or real.empty:
    raise RuntimeError(f"Treasury parse failed nominal={nom.shape} real={real.shape}")
status(3,9,"Treasury curves reparsed",nominal_columns=nom.shape[1],real_columns=real.shape[1])

rates=pd.concat([nom,real],axis=1).sort_index()
nom_by={tenor_from_col(c):c for c in nom.columns if tenor_from_col(c) is not None}
real_by={tenor_from_col(c):c for c in real.columns if tenor_from_col(c) is not None}
for ten in sorted(set(nom_by).intersection(real_by)):
    label=(f"{int(ten*12)}M" if ten<1 else f"{int(ten)}Y")
    rates[f"BE_{label}"]=rates[nom_by[ten]]-rates[real_by[ten]]
for a,b in [(2,10),(5,10),(10,30),(5,30)]:
    if a in nom_by and b in nom_by:
        rates[f"NOM_SLOPE_{b}Y_{a}Y"]=rates[nom_by[b]]-rates[nom_by[a]]
    if a in real_by and b in real_by:
        rates[f"REAL_SLOPE_{b}Y_{a}Y"]=rates[real_by[b]]-rates[real_by[a]]

parts=[]
for c in rates.columns:
    s=pd.to_numeric(rates[c],errors="coerce")
    parts += [
        s.rename(f"rates_yields_{c}_level"),
        s.diff(1).rename(f"rates_yields_{c}_d1"),
        s.diff(5).rename(f"rates_yields_{c}_d5")
    ]
    mu=s.rolling(252,min_periods=126).mean()
    sd=s.rolling(252,min_periods=126).std().replace(0,np.nan)
    parts.append(((s-mu)/sd).rename(f"rates_yields_{c}_z252"))
RF=pd.concat(parts,axis=1)
RF["AVAILABLE_AT"]=pd.DatetimeIndex(RF.index)+pd.Timedelta(days=1)
RF=RF.reset_index(drop=True)
status(4,9,"rate feature source built",source_features=RF.shape[1]-1)

Rjoined=featurewise_asof(S.index,RF)
if Rjoined.empty:
    raise RuntimeError("Featurewise rates as-of produced no columns")
S2=pd.concat([S,Rjoined],axis=1)
status(5,9,"featurewise as-of join complete",joined_rate_features=Rjoined.shape[1],total_features=S2.shape[1])

diag=[]
for c in Rjoined.columns:
    s=pd.to_numeric(Rjoined[c],errors="coerce")
    diag.append({
        "feature":c,
        "non_null":int(s.notna().sum()),
        "coverage":float(s.notna().mean()),
        "nunique":int(s.nunique(dropna=True)),
        "first_valid":str(s.first_valid_index()) if s.notna().any() else None,
        "last_valid":str(s.last_valid_index()) if s.notna().any() else None
    })
D=pd.DataFrame(diag)
D.to_csv(OUT/"RATES_FEATURE_COVERAGE.csv",index=False)
level=D[D["feature"].str.endswith("_level",na=False)]
if level.empty:
    raise RuntimeError("No level rate features after repair")
max_cov=float(level["coverage"].max())
med_cov=float(level["coverage"].median())
eligible=int(((D["coverage"]>=.45)&(D["nunique"]>=10)).sum())
if max_cov<0.90 or eligible<20:
    raise RuntimeError(f"Rates repair failed validation max_cov={max_cov:.3f} eligible={eligible}")
status(6,9,"rates validation passed",max_level_coverage=round(max_cov,4),median_level_coverage=round(med_cov,4),eligible_rate_features=eligible)

slow_path=OUT/"SLOW_CAUSAL_STATE_2010_2013_RATES_REPAIRED.parquet"
S2.to_parquet(slow_path)
manifest={
    "source_v83":V83.name,
    "slow_state_repaired_path":str(slow_path),
    "price_state_5m_path":str(V83/"PRICE_STATE_5M_2010_2013.parquet"),
    "targets_5m_path":str(V83/"FUTURE_TARGETS_5M_2010_2013.parquet"),
    "bridge_path":str(V83/"SLOW_ROW_ASOF_FOR_5M.npy"),
    "repair":"rate columns rejoined independently after dropping NaN source rows per feature; prevents sparse daily row NaNs from poisoning carried state",
    "slow_sha256":sha256(slow_path)
}
(OUT/"REPAIRED_ARCHITECTURE_MANIFEST.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
status(7,9,"repaired slow matrix written",slow_features=S2.shape[1],sha=manifest["slow_sha256"][:12])

family_counts={
    "rates_yields":sum(str(c).startswith("rates_yields_") for c in S2.columns),
    "cftc":sum(str(c).startswith("cftc_") for c in S2.columns),
    "alfred":sum(str(c).startswith("alfred_") for c in S2.columns),
    "cboe_vol":sum(str(c).startswith("cboe_vol_") for c in S2.columns),
    "cfe":sum(str(c).startswith("cfe_") for c in S2.columns),
    "financial_conditions":sum(str(c).startswith("financial_conditions_") for c in S2.columns),
    "treasury_auctions":sum(str(c).startswith("treasury_auctions_") for c in S2.columns)
}
status(8,9,"family accounting complete",families=family_counts)

receipt={
    "run_id":RID,
    "status":"COMPLETE_V83_RATES_REPAIR",
    "source_v83":V83.name,
    "old_rate_columns_removed":len(old_rate_cols),
    "new_rate_columns":Rjoined.shape[1],
    "eligible_rate_features_ge45pct_nunique10":eligible,
    "max_level_coverage":max_cov,
    "median_level_coverage":med_cov,
    "family_counts":family_counts,
    "edge_trials":0,
    "market_returns_accessed":False,
    "2014_plus_accessed":False,
    "2023_plus_accessed":False,
    "protected_2026_accessed":False,
    "next":"V84C_CORRECTED_ELIGIBILITY_AND_ENGINE_BENCHMARK"
}
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
status(9,9,"DONE",next=receipt["next"])
print("\n=== V83B RECEIPT ===");print(json.dumps(receipt,indent=2))
print("\n=== RATES COVERAGE TOP ===");print(D.sort_values(["coverage","nunique"],ascending=False).head(30).to_string(index=False))
print("\nRUN:",OUT)
