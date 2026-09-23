from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd

SEED=25023
BOOT=10000

def read_csv(p):
    return pd.read_csv(p,sep=";",dtype=str)

def num(s):
    return pd.to_numeric(s,errors="coerce")

def parse_dt(s):
    return pd.to_datetime(s,errors="coerce")

def month_bootstrap(df):
    d=df.dropna(subset=["outcome_r","entry_dt"]).copy()
    if d.empty:return {"q025":np.nan,"q10":np.nan,"q50":np.nan,"q90":np.nan,"q975":np.nan,"p_le_zero":np.nan}
    d["month"]=d["entry_dt"].dt.to_period("M").astype(str)
    groups=[g["outcome_r"].to_numpy(float) for _,g in d.groupby("month") if len(g)]
    if len(groups)<2:return {"q025":np.nan,"q10":np.nan,"q50":np.nan,"q90":np.nan,"q975":np.nan,"p_le_zero":np.nan}
    rng=np.random.default_rng(SEED);vals=np.empty(BOOT,float)
    for i in range(BOOT):
        pick=rng.integers(0,len(groups),size=len(groups))
        vals[i]=np.concatenate([groups[j] for j in pick]).mean()
    q=np.quantile(vals,[.025,.10,.50,.90,.975])
    return {"q025":float(q[0]),"q10":float(q[1]),"q50":float(q[2]),"q90":float(q[3]),"q975":float(q[4]),"p_le_zero":float((vals<=0).mean())}

def summarize(d):
    n_total=len(d)
    r=d[d["resolved"]].copy()
    ev=float(r["outcome_r"].mean()) if len(r) else np.nan
    hit=float((r["outcome_r"]==2.0).mean()) if len(r) else np.nan
    b=month_bootstrap(r)
    side={}
    for s,g in d.groupby("side"):
        rr=g[g["resolved"]]
        side[str(s)]={"n":int(len(g)),"resolved":int(len(rr)),"ev2_R":float(rr["outcome_r"].mean()) if len(rr) else np.nan,
                      "target_first_rate":float((rr["outcome_r"]==2).mean()) if len(rr) else np.nan,
                      "mean_entry_spread_R":float(g["entry_spread_r"].mean()) if g["entry_spread_r"].notna().any() else np.nan}
    stress=d[d["resolved"]].copy()
    if len(stress):
        stress["payoff_one_spread_stress_r"]=stress["outcome_r"]
        m=stress["side"].str.upper().eq("SHORT") & stress["entry_spread_r"].notna()
        stress.loc[m,"payoff_one_spread_stress_r"]=stress.loc[m,"outcome_r"]-stress.loc[m,"entry_spread_r"]
        stress_ev=float(stress["payoff_one_spread_stress_r"].mean())
    else: stress_ev=np.nan
    return {"n_retest":int(n_total),"resolved":int(len(r)),"resolution_fraction":float(len(r)/n_total) if n_total else 0,
            "ev2_R":ev,"target_first_rate":hit,"month_block_bootstrap":b,"by_side":side,
            "mean_entry_spread_R":float(d["entry_spread_r"].mean()) if d["entry_spread_r"].notna().any() else np.nan,
            "payoff_only_one_spread_stress_ev_R":stress_ev}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--raw",required=True);ap.add_argument("--out",required=True)
    a=ap.parse_args();raw=Path(a.raw);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    T=read_csv(raw/"trades.csv");O=read_csv(raw/"outcomes.csv")
    T=T[T["path"].str.upper().eq("RETEST")].copy()
    if "entry_spread_r" not in T.columns:T["entry_spread_r"]=np.nan
    T["entry_spread_r"]=num(T["entry_spread_r"])
    T["entry_dt"]=parse_dt(T["entry_utc"])
    O=O[O["horizon"].str.upper().eq("48H")].copy()
    for c in ["hit2_utc","stop_utc"]:
        O[c]=num(O[c]).fillna(0).astype("int64")
    M=T.merge(O[["session_id","event_id","hit2_utc","stop_utc","ambiguous_same_m1"]],on=["session_id","event_id"],how="left")
    hit=M["hit2_utc"].fillna(0).astype("int64")
    stop=M["stop_utc"].fillna(0).astype("int64")
    amb=M["ambiguous_same_m1"].fillna("").str.upper().eq("YES") | ((hit>0)&(stop>0)&(hit==stop))
    target=(hit>0)&((stop==0)|(hit<stop))&(~amb)
    stopped=(stop>0)&((hit==0)|(stop<hit))&(~amb)
    M["resolved"]=target|stopped
    M["target_first"]=target
    M["outcome_r"]=np.where(target,2.0,np.where(stopped,-1.0,np.nan))
    M["year"]=M["entry_dt"].dt.year
    M.to_csv(out/"D025_ETH_RETEST_ANALYZED_LEDGER.csv",index=False)

    fresh=M[M["year"]==2023].copy()
    transport=M[M["year"].isin([2024,2025])].copy()
    sf=summarize(fresh);st=summarize(transport);sa=summarize(M)

    if sf["resolved"]<50:
        label="SPARSE_POSITIVE" if np.isfinite(sf["ev2_R"]) and sf["ev2_R"]>0 else "NEGATIVE_OR_INSUFFICIENT"
    elif sf["ev2_R"]<=0:
        label="NEGATIVE"
    elif sf["month_block_bootstrap"]["q10"]>0:
        label="POSITIVE_CONFIRMED"
    else:
        label="POSITIVE_UNCERTAIN"

    yearly={}
    for y,g in M.groupby("year"):
        yearly[str(int(y))]=summarize(g)

    result={
      "candidate":"D025 ETHUSD RETEST fixed +2R vs structural -1R",
      "fresh_2023":sf,
      "fresh_2023_v2_label":label,
      "transport_2024_2025":st,
      "all_2023_2025":sa,
      "yearly":yearly,
      "interpretation":"2023 is fresh temporal evidence for the frozen branch; 2024-2025 is FTMO feed transport only because those years informed branch selection.",
      "cost_warning":"VirtualPath is not a full historical commission/slippage/ask-side SHORT execution model. One-spread SHORT payoff stress is diagnostic only.",
      "2026_accessed":False
    }
    (out/"ANALYSIS.json").write_text(json.dumps(result,indent=2,default=str),encoding="utf-8")
    print(json.dumps(result,indent=2),flush=True)

if __name__=="__main__":main()
