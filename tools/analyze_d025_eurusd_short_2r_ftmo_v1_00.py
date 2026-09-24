from pathlib import Path
import argparse,json,math
import numpy as np
import pandas as pd

SEED=25024
BOOT=10000
CONTRACT_SIZE=100000.0
COMMISSION_RT_USD_PER_LOT=5.0

def read_csv(p): return pd.read_csv(p,sep=";",dtype=str)
def num(s): return pd.to_numeric(s,errors="coerce")
def parse_dt(s): return pd.to_datetime(s,errors="coerce")

def boot_month(d,col):
    z=d.dropna(subset=[col,"entry_dt"]).copy()
    if z.empty:return {"q025":np.nan,"q10":np.nan,"q50":np.nan,"q90":np.nan,"q975":np.nan,"p_le_zero":np.nan}
    z["month"]=z["entry_dt"].dt.to_period("M").astype(str)
    groups=[g[col].to_numpy(float) for _,g in z.groupby("month") if len(g)]
    if len(groups)<2:return {"q025":np.nan,"q10":np.nan,"q50":np.nan,"q90":np.nan,"q975":np.nan,"p_le_zero":np.nan}
    rng=np.random.default_rng(SEED); vals=np.empty(BOOT,float)
    for i in range(BOOT):
        pick=rng.integers(0,len(groups),size=len(groups))
        vals[i]=np.concatenate([groups[j] for j in pick]).mean()
    q=np.quantile(vals,[.025,.10,.50,.90,.975])
    return {"q025":float(q[0]),"q10":float(q[1]),"q50":float(q[2]),"q90":float(q[3]),"q975":float(q[4]),"p_le_zero":float((vals<=0).mean())}

def summarize(d):
    rr=d[d["resolved"]].copy()
    if len(rr):
        raw=float(rr["outcome_r"].mean())
        stress=float(rr["stressed_outcome_r"].mean())
        hit=float((rr["outcome_r"]==2.0).mean())
    else:
        raw=stress=hit=np.nan
    paths={}
    for p,g in d.groupby("path"):
        r=g[g["resolved"]]
        paths[str(p)]={"n":int(len(g)),"resolved":int(len(r)),
                       "raw_ev_R":float(r["outcome_r"].mean()) if len(r) else np.nan,
                       "stressed_ev_R":float(r["stressed_outcome_r"].mean()) if len(r) else np.nan}
    return {
      "signals":int(len(d)),"resolved":int(len(rr)),"resolution_fraction":float(len(rr)/len(d)) if len(d) else 0.0,
      "target_first_rate":hit,"raw_ev_R":raw,"stressed_ev_R":stress,
      "mean_entry_spread_R":float(d["entry_spread_r"].mean()) if d["entry_spread_r"].notna().any() else np.nan,
      "mean_commission_R":float(d["commission_r"].mean()) if d["commission_r"].notna().any() else np.nan,
      "raw_bootstrap":boot_month(rr,"outcome_r"),"stressed_bootstrap":boot_month(rr,"stressed_outcome_r"),
      "by_path_diagnostic":paths
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--raw",required=True);ap.add_argument("--out",required=True)
    a=ap.parse_args();raw=Path(a.raw);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    T=read_csv(raw/"trades.csv");O=read_csv(raw/"outcomes.csv")
    T=T[T["side"].str.upper().eq("SHORT")].copy()
    for c in ["entry_spread_r","risk_price","entry"]:
        T[c]=num(T[c])
    T["entry_dt"]=parse_dt(T["entry_utc"])
    # $5 RT commission per 1 lot, normalized by 1R dollar value = risk_price*100000.
    T["commission_r"]=COMMISSION_RT_USD_PER_LOT/(CONTRACT_SIZE*T["risk_price"])
    O=O[O["horizon"].str.upper().eq("48H")].copy()
    for c in ["hit2_utc","stop_utc"]:
        O[c]=num(O[c]).fillna(0).astype("int64")
    M=T.merge(O[["session_id","event_id","hit2_utc","stop_utc","ambiguous_same_m1"]],on=["session_id","event_id"],how="left")
    hit=M["hit2_utc"].fillna(0).astype("int64"); stop=M["stop_utc"].fillna(0).astype("int64")
    amb=M["ambiguous_same_m1"].fillna("").str.upper().eq("YES") | ((hit>0)&(stop>0)&(hit==stop))
    target=(hit>0)&((stop==0)|(hit<stop))&(~amb)
    stopped=(stop>0)&((hit==0)|(stop<hit))&(~amb)
    M["resolved"]=target|stopped
    M["outcome_r"]=np.where(target,2.0,np.where(stopped,-1.0,np.nan))
    M["stressed_outcome_r"]=M["outcome_r"]-M["entry_spread_r"].fillna(0.0)-M["commission_r"].fillna(0.0)
    M["year"]=M["entry_dt"].dt.year
    M.to_csv(out/"D025_EURUSD_SHORT_2R_ANALYZED_LEDGER.csv",index=False)

    fresh=M[M["year"]==2023].copy()
    transport=M[M["year"].isin([2024,2025])].copy()
    sf=summarize(fresh); st=summarize(transport); sa=summarize(M)

    if sf["resolved"]<50:
        label="SPARSE_POSITIVE" if np.isfinite(sf["stressed_ev_R"]) and sf["stressed_ev_R"]>0 else "NEGATIVE_OR_INSUFFICIENT"
    elif not np.isfinite(sf["raw_ev_R"]) or sf["raw_ev_R"]<=0:
        label="NEGATIVE"
    elif not np.isfinite(sf["stressed_ev_R"]) or sf["stressed_ev_R"]<=0:
        label="SIGNAL_POSITIVE_ECONOMIC_NEGATIVE"
    elif sf["stressed_bootstrap"]["q10"]>0:
        label="POSITIVE_CONFIRMED"
    else:
        label="POSITIVE_UNCERTAIN"

    yearly={str(int(y)):summarize(g) for y,g in M.groupby("year")}
    result={
      "candidate":"D025 EURUSD SHORT all frozen LER paths, +2R vs structural -1R",
      "fresh_2023":sf,"fresh_2023_label":label,
      "transport_2024_2025":st,"all_2023_2025":sa,"yearly":yearly,
      "cost_model":"screening stress only: entry spread R + exact normalized $5/lot RT commission; not exact Ask-side path execution",
      "exact_tick_followup_permitted": bool(label in ["POSITIVE_CONFIRMED","POSITIVE_UNCERTAIN"]),
      "2026_accessed":False
    }
    (out/"ANALYSIS.json").write_text(json.dumps(result,indent=2,default=str)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,default=str),flush=True)

if __name__=="__main__":main()
