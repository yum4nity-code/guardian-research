from pathlib import Path
import pandas as pd
import numpy as np
import json, re, time

ROOT=Path(r"D:\MT5_Backtests")
RID="GEF84B-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v84b"/RID
OUT.mkdir(parents=True,exist_ok=True)
T0=time.time()

MARKETS=["XAUUSD","XAGUSD","UDXUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","SPXUSD","NSXUSD","WTIUSD","BCOUSD"]

def status(i,n,msg,**extra):
    e=time.time()-T0
    payload={"run_id":RID,"step":i,"steps":n,"percent":round(100*i/n,1),"elapsed_s":round(e,2),"message":msg,**extra}
    (OUT/"LIVE_STATUS.json").write_text(json.dumps(payload,indent=2,default=str),encoding="utf-8")
    print(f"[GEF84B] {i}/{n} {100*i/n:.0f}% | elapsed {e:.1f}s | {msg}",flush=True)

def family(c):
    s=str(c)
    for m in MARKETS:
        if s.startswith(f"price_{m}_"):
            return f"price_{m}"
        if s.startswith(f"cftc_{m}_"):
            return f"cftc_{m}"
    for pref in ["rates_yields_","alfred_","cboe_vol_","cfe_","financial_conditions_","treasury_auctions_"]:
        if s.startswith(pref):
            return pref.rstrip("_")
    if s.startswith("price_cross_"): return "price_cross"
    if s.startswith("time_"): return "time_state"
    return "other"

status(1,7,"load latest completed V83; diagnostic only")
runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v83").glob("GEF83-*"))
runs=[p for p in runs if (p/"RUN_RECEIPT.json").exists()]
if not runs: raise RuntimeError("No completed V83")
V83=runs[-1]
S=pd.read_parquet(V83/"SLOW_CAUSAL_STATE_2010_2013.parquet")
F=pd.read_parquet(V83/"PRICE_STATE_5M_2010_2013.parquet")
S.index=pd.to_datetime(S.index);F.index=pd.to_datetime(F.index)
status(2,7,"matrices loaded",slow_rows=len(S),slow_cols=S.shape[1],fast_rows=len(F),fast_cols=F.shape[1])

rate_cols=[c for c in S.columns if str(c).startswith("rates_yields_")]
rate_diag=[]
for c in rate_cols:
    s=pd.to_numeric(S[c],errors="coerce")
    valid=s.notna()
    rate_diag.append({
        "feature":c,
        "non_null":int(valid.sum()),
        "coverage":float(valid.mean()),
        "nunique":int(s.nunique(dropna=True)),
        "first_valid":str(s.first_valid_index()) if valid.any() else None,
        "last_valid":str(s.last_valid_index()) if valid.any() else None
    })
R=pd.DataFrame(rate_diag)
R.to_csv(OUT/"RATES_FEATURE_DIAGNOSTIC.csv",index=False)
status(3,7,"rates feature coverage inspected",rate_columns=len(rate_cols),rates_eligible=int(((R["coverage"]>=.45)&(R["nunique"]>=10)).sum()) if len(R) else 0)

train_s=S.index.year<=2012
train_f=F.index.year<=2012
records=[]
for layer,df,mask in [("slow",S,train_s),("fast",F,train_f)]:
    for c in df.columns:
        s=pd.to_numeric(df.loc[mask,c],errors="coerce")
        if s.notna().mean()>=.45 and s.nunique(dropna=True)>=10:
            records.append({"layer":layer,"feature":c,"family":family(c),"coverage_train":float(s.notna().mean())})
C=pd.DataFrame(records)
C.to_csv(OUT/"CORRECTED_ELIGIBLE_CATALOG.csv",index=False)
bad=C[C.family=="other"] if len(C) else pd.DataFrame()
status(4,7,"corrected taxonomy built",eligible=len(C),other_features=len(bad))

counts=C.groupby(["layer","family"]).size().reset_index(name="features") if len(C) else pd.DataFrame()
counts.to_csv(OUT/"CORRECTED_FAMILY_COUNTS.csv",index=False)
status(5,7,"family counts written")

rate_summary={
    "rate_columns_present":len(rate_cols),
    "rate_columns_coverage_ge_45pct":int((R["coverage"]>=.45).sum()) if len(R) else 0,
    "rate_columns_nunique_ge_10":int((R["nunique"]>=10).sum()) if len(R) else 0,
    "rate_columns_eligible_both":int(((R["coverage"]>=.45)&(R["nunique"]>=10)).sum()) if len(R) else 0,
    "max_rate_coverage":float(R["coverage"].max()) if len(R) else 0.0,
    "median_rate_coverage":float(R["coverage"].median()) if len(R) else 0.0
}
status(6,7,"diagnosis complete",**rate_summary)

receipt={
    "run_id":RID,
    "status":"COMPLETE_PRE_V85_ARCHITECTURE_DIAGNOSTIC",
    "source_v83":V83.name,
    "rate_summary":rate_summary,
    "corrected_family_counts":{f"{r.layer}::{r.family}":int(r.features) for r in counts.itertuples()} if len(counts) else {},
    "unclassified_eligible_features":bad.feature.tolist()[:100] if len(bad) else [],
    "edge_trials":0,
    "market_returns_accessed":False,
    "2014_plus_accessed":False,
    "2023_plus_accessed":False,
    "protected_2026_accessed":False,
    "decision":"BLOCK_V85_IF_RATES_NOT_ELIGIBLE_OR_OTHER_FEATURES_REMAIN"
}
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
status(7,7,"STOP before V85")
print("\n=== V84B RECEIPT ===");print(json.dumps(receipt,indent=2))
print("\n=== CORRECTED FAMILY COUNTS ===");print(counts.to_string(index=False) if len(counts) else "NONE")
print("\n=== RATES DIAGNOSTIC TOP ===");print(R.sort_values(["coverage","nunique"],ascending=False).head(30).to_string(index=False) if len(R) else "NO RATES COLUMNS")
print("\nRUN:",OUT)
