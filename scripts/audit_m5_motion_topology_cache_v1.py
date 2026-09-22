from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

MARKETS=["XAUUSD","XAGUSD","UDXUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","SPXUSD","NSXUSD","WTIUSD","BCOUSD"]
GRAPH=[
 ("XAUUSD","XAGUSD"),("XAUUSD","UDXUSD"),("XAGUSD","UDXUSD"),
 ("USDCAD","WTIUSD"),("USDCAD","BCOUSD"),("WTIUSD","BCOUSD"),
 ("NSXUSD","SPXUSD"),("UDXUSD","EURUSD"),("UDXUSD","GBPUSD"),
 ("UDXUSD","AUDUSD"),("UDXUSD","USDJPY"),("UDXUSD","USDCHF"),("UDXUSD","USDCAD"),
]
LOOKBACKS=[15,30,60]; HORIZONS=[15,30,60]

def latest_run(root):
    base=root/"Research"/"Autonomous"/"guardian_m5_motion_topology_v1"
    runs=[p for p in sorted(base.glob("GEFM5T-*")) if (p/"RUN_RECEIPT.json").exists() and (p/"CACHE_MANIFEST.json").exists()]
    if not runs: raise RuntimeError("No completed M5 topology cache run")
    return runs[-1]

def contiguous_runs(slots):
    slots=sorted(set(int(x) for x in slots))
    if not slots:return []
    arr=np.zeros(2016,dtype=bool);arr[slots]=True
    # break circular week at first false
    if arr.all(): return [(0,2015,2016)]
    start0=int(np.flatnonzero(~arr)[0])
    seq=[]
    inrun=False;s=None
    for k in range(1,2017):
        i=(start0+k)%2016
        if arr[i] and not inrun:
            s=i;inrun=True
        if inrun and (not arr[i] or k==2016):
            e=(i-1)%2016
            length=((e-s)%2016)+1
            seq.append((s,e,length))
            inrun=False
    return seq

def fmt_slot(s):
    d=s//288; rem=s%288; hh=rem//12; mm=(rem%12)*5
    return f"D{d} {hh:02d}:{mm:02d}"

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root);run=latest_run(root)
    print("=== M5 TOPOLOGY CACHE AUDIT ===")
    print("RUN:",run)

    receipt=json.loads((run/"RUN_RECEIPT.json").read_text())
    if receipt.get("edge_trials")!=0 or receipt.get("alpha_tests")!=0:
        raise RuntimeError("Audit refuses cache with alpha trials")
    if receipt.get("2015_plus_outcomes_accessed"):
        raise RuntimeError("Firewall violated")

    cov=pd.read_csv(run/"MARKET_COVERAGE.csv")
    slots=pd.read_csv(run/"TRADABILITY_SLOT_AUDIT.csv")
    tm=pd.read_parquet(run/"TRADABILITY_MASK_2011_2014.parquet")
    tm.index=pd.to_datetime(tm.index)
    cross=pd.read_parquet(run/"CROSS_STATE_2011_2014.parquet")
    cross.index=pd.to_datetime(cross.index)

    print("\n=== TRADABILITY SESSION SHAPES ===")
    sr=[]
    for s in MARKETS:
        g=slots[(slots.market==s)&(slots.recurring_post_buffer.astype(bool))]
        runs=contiguous_runs(g.slot_of_week.to_numpy())
        sr.append({
          "market":s,
          "valid_slots":len(g),
          "hours_per_week":round(len(g)*5/60,2),
          "session_blocks":len(runs),
          "blocks":" | ".join(f"{fmt_slot(a)}->{fmt_slot(b)} ({n*5/60:.1f}h)" for a,b,n in runs)
        })
    S=pd.DataFrame(sr)
    print(S.to_string(index=False))

    print("\n=== YEARLY TRADABLE COVERAGE ===")
    yr=[]
    for s in MARKETS:
        for y in [2012,2013,2014]:
            m=tm.index.year==y
            yr.append({"market":s,"year":y,"tradable_rows":int(tm.loc[m,s].astype(bool).sum()),"days":int(tm.loc[m & tm[s].astype(bool)].index.normalize().nunique())})
    print(pd.DataFrame(yr).to_string(index=False))

    print("\n=== OHLC INTEGRITY ===")
    integ=[]
    for s in MARKETS:
        p=Path(json.loads((run/"CACHE_MANIFEST.json").read_text())["market_files"][s]["ohlc"])
        d=pd.read_parquet(p)
        good=d.dropna()
        bad_hi=(good["high"]<good[["open","close"]].max(axis=1)).sum()
        bad_lo=(good["low"]>good[["open","close"]].min(axis=1)).sum()
        bad_range=(good["high"]<good["low"]).sum()
        zero_close=(good["close"]<=0).sum()
        integ.append({"market":s,"rows":len(good),"bad_high":int(bad_hi),"bad_low":int(bad_lo),"bad_range":int(bad_range),"nonpositive_close":int(zero_close)})
    print(pd.DataFrame(integ).to_string(index=False))

    print("\n=== ENDPOINT TARGET DISTRIBUTION ===")
    tr=[]
    manifest=json.loads((run/"CACHE_MANIFEST.json").read_text())
    for s in MARKETS:
        d=pd.read_parquet(Path(manifest["target_files"][s]))
        for L in LOOKBACKS:
            for H in HORIZONS:
                col=f"endpoint_score_{L}m_{H}m"
                top=f"top_label_{L}m_{H}m";bot=f"bottom_label_{L}m_{H}m"
                x=pd.to_numeric(d[col],errors="coerce").dropna()
                tr.append({
                  "market":s,"L":L,"H":H,"n":len(x),
                  "q01":float(x.quantile(.01)) if len(x) else np.nan,
                  "q10":float(x.quantile(.10)) if len(x) else np.nan,
                  "median":float(x.quantile(.50)) if len(x) else np.nan,
                  "q90":float(x.quantile(.90)) if len(x) else np.nan,
                  "q99":float(x.quantile(.99)) if len(x) else np.nan,
                  "positive_frac":float((x>0).mean()) if len(x) else np.nan,
                  "top_defined":int(pd.Series(d[top]).notna().sum()),
                  "bottom_defined":int(pd.Series(d[bot]).notna().sum())
                })
    T=pd.DataFrame(tr)
    print(T.to_string(index=False))

    print("\n=== JOINT GRAPH SUPPORT ===")
    gr=[]
    for a,b in GRAPH:
        col=f"{a}__{b}__joint_tradable"
        if col not in cross.columns: raise RuntimeError(f"Missing {col}")
        z=cross[col].astype(bool)
        disc=(cross.index>=pd.Timestamp("2012-01-01"))&(cross.index<pd.Timestamp("2015-01-01"))
        m=z&disc
        gr.append({"A":a,"B":b,"joint_rows":int(m.sum()),"joint_days":int(cross.index[m].normalize().nunique())})
    print(pd.DataFrame(gr).to_string(index=False))

    print("\n=== CROSS FEATURE FINITE SUPPORT ===")
    fs=[]
    disc=(cross.index>=pd.Timestamp("2012-01-01"))&(cross.index<pd.Timestamp("2015-01-01"))
    for c in cross.columns:
        if c.endswith("__joint_tradable") or c=="all13_tradable": continue
        x=pd.to_numeric(cross.loc[disc,c],errors="coerce")
        fs.append({"feature":c,"finite":int(x.notna().sum()),"distinct_days":int(cross.loc[disc].index[x.notna()].normalize().nunique())})
    F=pd.DataFrame(fs).sort_values("finite")
    print(F.head(40).to_string(index=False))
    print("\nMIN_CROSS_FINITE:",int(F.finite.min()),"MEDIAN:",float(F.finite.median()),"MAX:",int(F.finite.max()))

if __name__=="__main__":
    main()
