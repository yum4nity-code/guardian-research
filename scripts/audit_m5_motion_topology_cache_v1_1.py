from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd

MARKETS=["XAUUSD","XAGUSD","UDXUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","SPXUSD","NSXUSD","WTIUSD","BCOUSD"]
GRAPH=[
 ("XAUUSD","XAGUSD"),("XAUUSD","UDXUSD"),("XAGUSD","UDXUSD"),
 ("USDCAD","WTIUSD"),("USDCAD","BCOUSD"),("WTIUSD","BCOUSD"),
 ("NSXUSD","SPXUSD"),("UDXUSD","EURUSD"),("UDXUSD","GBPUSD"),
 ("UDXUSD","AUDUSD"),("UDXUSD","USDJPY"),("UDXUSD","USDCHF"),("UDXUSD","USDCAD"),
]

def latest_run(root):
    base=root/"Research"/"Autonomous"/"guardian_m5_motion_topology_v1_1"
    runs=[p for p in sorted(base.glob("GEFM5T-*")) if (p/"RUN_RECEIPT.json").exists() and (p/"CACHE_MANIFEST.json").exists()]
    if not runs: raise RuntimeError("No completed M5 topology V1.1 cache run")
    return runs[-1]

def run_lengths(mask):
    a=np.asarray(mask,dtype=bool)
    if not len(a): return []
    out=[];n=0
    for v in a:
        if v:n+=1
        elif n:
            out.append(n);n=0
    if n:out.append(n)
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root);run=latest_run(root)
    print("=== M5 TOPOLOGY V1.1 CACHE AUDIT ===")
    print("RUN:",run)

    receipt=json.loads((run/"RUN_RECEIPT.json").read_text())
    if receipt.get("edge_trials")!=0 or receipt.get("alpha_tests")!=0: raise RuntimeError("Audit refuses alpha-tested cache")
    if receipt.get("2015_plus_outcomes_accessed"): raise RuntimeError("Firewall violated")

    manifest=json.loads((run/"CACHE_MANIFEST.json").read_text())
    cov=pd.read_csv(run/"MARKET_COVERAGE.csv")
    tm=pd.read_parquet(run/"TRADABILITY_MASK_2011_2014.parquet");tm.index=pd.to_datetime(tm.index)
    cross=pd.read_parquet(run/"CROSS_STATE_2011_2014.parquet");cross.index=pd.to_datetime(cross.index)

    print("\n=== OBSERVED-RUN TRADABILITY SUMMARY ===")
    rows=[]
    disc=(tm.index>=pd.Timestamp("2012-01-01"))&(tm.index<pd.Timestamp("2015-01-01"))
    for s in MARKETS:
        x=tm.loc[disc,s].astype(bool).to_numpy()
        rl=np.array(run_lengths(x),dtype=float)
        rows.append({
          "market":s,
          "tradable_rows":int(x.sum()),
          "tradable_days":int(tm.loc[disc & tm[s].astype(bool)].index.normalize().nunique()),
          "run_count":int(len(rl)),
          "median_run_min":float(np.median(rl)*5) if len(rl) else np.nan,
          "p10_run_min":float(np.quantile(rl,.10)*5) if len(rl) else np.nan,
          "p90_run_min":float(np.quantile(rl,.90)*5) if len(rl) else np.nan,
          "max_run_min":float(np.max(rl)*5) if len(rl) else np.nan
        })
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n=== YEARLY TRADABLE COVERAGE ===")
    yr=[]
    for s in MARKETS:
        for y in [2012,2013,2014]:
            m=tm.index.year==y
            z=tm.loc[m,s].astype(bool)
            yr.append({"market":s,"year":y,"tradable_rows":int(z.sum()),"days":int(tm.loc[m & tm[s].astype(bool)].index.normalize().nunique())})
    print(pd.DataFrame(yr).to_string(index=False))

    print("\n=== OHLC INTEGRITY ===")
    integ=[]
    for s in MARKETS:
        d=pd.read_parquet(Path(manifest["market_files"][s]["ohlc"]))
        good=d.dropna()
        integ.append({
          "market":s,"rows":len(good),
          "bad_high":int((good["high"]<good[["open","close"]].max(axis=1)).sum()),
          "bad_low":int((good["low"]>good[["open","close"]].min(axis=1)).sum()),
          "bad_range":int((good["high"]<good["low"]).sum()),
          "nonpositive_close":int((good["close"]<=0).sum())
        })
    print(pd.DataFrame(integ).to_string(index=False))

    print("\n=== ENDPOINT SUPPORT ===")
    sup=pd.read_csv(run/"ENDPOINT_SUPPORT.csv")
    print(sup.groupby(["lookback_min","horizon_min"])["finite_endpoint_scores"].agg(["min","median","max"]).reset_index().to_string(index=False))

    print("\n=== JOINT GRAPH SUPPORT ===")
    gr=[]
    for a,b in GRAPH:
        col=f"{a}__{b}__joint_tradable"
        z=cross[col].astype(bool)
        m=z&(cross.index>=pd.Timestamp("2012-01-01"))&(cross.index<pd.Timestamp("2015-01-01"))
        gr.append({"A":a,"B":b,"joint_rows":int(m.sum()),"joint_days":int(cross.index[m].normalize().nunique())})
    print(pd.DataFrame(gr).to_string(index=False))

    print("\n=== CROSS FEATURE FINITE SUPPORT ===")
    fs=[]
    disc=(cross.index>=pd.Timestamp("2012-01-01"))&(cross.index<pd.Timestamp("2015-01-01"))
    for c in cross.columns:
        if c.endswith("__joint_tradable") or c=="all13_tradable":continue
        x=pd.to_numeric(cross.loc[disc,c],errors="coerce")
        fs.append({"feature":c,"finite":int(x.notna().sum()),"distinct_days":int(cross.loc[disc].index[x.notna()].normalize().nunique())})
    F=pd.DataFrame(fs).sort_values("finite")
    print(F.head(40).to_string(index=False))
    print("\nMIN_CROSS_FINITE:",int(F.finite.min()),"MEDIAN:",float(F.finite.median()),"MAX:",int(F.finite.max()))

if __name__=="__main__":
    main()
