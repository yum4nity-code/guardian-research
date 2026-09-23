from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd

SEED=17025
BOOT=10000

def read_csv(p):
    return pd.read_csv(p,sep=";",dtype=str)

def num(s):
    return pd.to_numeric(s,errors="coerce")

def parse_dt(s):
    return pd.to_datetime(s,errors="coerce")

def month_bootstrap(df):
    d=df.dropna(subset=["outcome_r","entry_dt"]).copy()
    if len(d)==0:
        return {"q025":np.nan,"q10":np.nan,"q50":np.nan,"q90":np.nan,"q975":np.nan,"p_le_zero":np.nan}
    d["month"]=d["entry_dt"].dt.to_period("M").astype(str)
    groups=[g["outcome_r"].to_numpy(float) for _,g in d.groupby("month") if len(g)]
    if len(groups)<2:
        return {"q025":np.nan,"q10":np.nan,"q50":np.nan,"q90":np.nan,"q975":np.nan,"p_le_zero":np.nan}
    rng=np.random.default_rng(SEED)
    vals=np.empty(BOOT,float)
    for i in range(BOOT):
        pick=rng.integers(0,len(groups),size=len(groups))
        vals[i]=np.concatenate([groups[j] for j in pick]).mean()
    q=np.quantile(vals,[.025,.10,.50,.90,.975])
    return {"q025":float(q[0]),"q10":float(q[1]),"q50":float(q[2]),"q90":float(q[3]),"q975":float(q[4]),"p_le_zero":float((vals<=0).mean())}

def summarize(d):
    rr=d[d["resolved"]].copy()
    ev=float(rr["outcome_r"].mean()) if len(rr) else np.nan
    hit=float((rr["target_first"]).mean()) if len(rr) else np.nan
    b=month_bootstrap(rr)
    return {
        "n_sell":int(len(d)),
        "resolved":int(len(rr)),
        "resolution_fraction":float(len(rr)/len(d)) if len(d) else 0.0,
        "ev_2p5R":ev,
        "target_first_rate":hit,
        "month_block_bootstrap":b,
        "mean_spread_pct_sl_at_signal":float(d["spread_pct_sl"].mean()) if d["spread_pct_sl"].notna().any() else np.nan,
        "mean_spread_R_at_signal":float((d["spread_pct_sl"]/100.0).mean()) if d["spread_pct_sl"].notna().any() else np.nan
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    raw=Path(a.raw);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)

    T=read_csv(raw/"trades.csv")
    O=read_csv(raw/"outcomes.csv")
    E=read_csv(raw/"events.csv")

    T=T[T["side"].str.upper().eq("SELL")].copy()
    T["entry_dt"]=parse_dt(T["entry_utc"])
    T["year"]=T["entry_dt"].dt.year

    O=O[(O["horizon"].str.upper().eq("48H")) & (O["side"].str.upper().eq("SELL"))].copy()
    for c in ["hit25_utc","stop_utc"]:
        O[c]=num(O[c]).fillna(0).astype("int64")

    valid=E[(E["transition"].str.upper().eq("VALID_SIGNAL")) & (E["side"].str.upper().eq("SELL"))].copy()
    valid["spread_pct_sl"]=num(valid["spread_pct_sl"])
    valid=valid[["session_id","event_id","spread_pct_sl"]].drop_duplicates(["session_id","event_id"],keep="last")

    M=T.merge(O[["session_id","event_id","hit25_utc","stop_utc","ambiguous_stop_target_m1"]],
              on=["session_id","event_id"],how="left")
    M=M.merge(valid,on=["session_id","event_id"],how="left")

    hit=M["hit25_utc"].fillna(0).astype("int64")
    stop=M["stop_utc"].fillna(0).astype("int64")
    amb=M["ambiguous_stop_target_m1"].fillna("").str.upper().eq("YES") | ((hit>0)&(stop>0)&(hit==stop))
    target=(hit>0)&((stop==0)|(hit<stop))&(~amb)
    stopped=(stop>0)&((hit==0)|(stop<hit))&(~amb)

    M["resolved"]=target|stopped
    M["target_first"]=target
    M["outcome_r"]=np.where(target,2.5,np.where(stopped,-1.0,np.nan))
    M["year"]=M["entry_dt"].dt.year
    M.to_csv(out/"D017_BTC_SELL_2P5R_ANALYZED_LEDGER.csv",index=False)

    fresh=M[M["year"]==2023].copy()
    transport=M[M["year"].isin([2024,2025])].copy()
    sf=summarize(fresh);st=summarize(transport);sa=summarize(M)

    if sf["resolved"]<50:
        label="SPARSE_POSITIVE" if np.isfinite(sf["ev_2p5R"]) and sf["ev_2p5R"]>0 else "NEGATIVE_OR_INSUFFICIENT"
    elif sf["ev_2p5R"]<=0:
        label="NEGATIVE"
    elif sf["month_block_bootstrap"]["q10"]>0:
        label="POSITIVE_CONFIRMED"
    else:
        label="POSITIVE_UNCERTAIN"

    yearly={}
    for y,g in M.groupby("year"):
        yearly[str(int(y))]=summarize(g)

    result={
        "candidate":"D017 BTCUSD SELL Momentum fixed +2.5R vs structural -1R",
        "fresh_2023":sf,
        "fresh_2023_v2_label":label,
        "transport_2024_2025":st,
        "all_2023_2025":sa,
        "yearly":yearly,
        "interpretation":"2023 is fresh temporal evidence for the frozen SELL +2.5R branch; 2024-2025 is FTMO feed transport only because those years informed branch selection.",
        "execution_warning":"Virtual path is not exact ASK-side SELL target/stop execution. A positive result requires later real-tick BID/ASK + commission/slippage audit.",
        "2026_accessed":False
    }
    (out/"ANALYSIS.json").write_text(json.dumps(result,indent=2,default=str),encoding="utf-8")
    print(json.dumps(result,indent=2),flush=True)

if __name__=="__main__":
    main()
