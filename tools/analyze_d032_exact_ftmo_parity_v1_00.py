from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd

SEED=3201
BOOT=10000

def read_scsv(p):
    return pd.read_csv(p,sep=";")

def num(x):
    return pd.to_numeric(x,errors="coerce")

def clean_events(d):
    z=d.copy()
    z["feed_gap"]=num(z["feed_gap"]).fillna(1).astype(int)
    z["missing_horizons"]=num(z["missing_horizons"]).fillna(999).astype(int)
    z["exe_bps_24h"]=num(z["exe_bps_24h"])
    z["net_exe_bps_24h"]=num(z["net_exe_bps_24h"])
    z["exe_24h_R"]=num(z["exe_24h_R"])
    z["signal_dt"]=pd.to_datetime(z["signal_end_server"],errors="coerce")
    return z[(z["feed_gap"]==0)&(z["missing_horizons"]==0)&z["exe_bps_24h"].notna()&z["exe_24h_R"].notna()].copy()

def clean_controls(d):
    z=d.copy()
    z["feed_gap"]=num(z["feed_gap"]).fillna(1).astype(int)
    z["missing_horizons"]=num(z["missing_horizons"]).fillna(999).astype(int)
    z["exe_bps_24h"]=num(z["exe_bps_24h"])
    return z[(z["feed_gap"]==0)&(z["missing_horizons"]==0)&z["exe_bps_24h"].notna()].copy()

def boot_month(z,col):
    d=z.dropna(subset=["signal_dt",col]).copy()
    if d.empty:
        return {}
    d["month"]=d["signal_dt"].dt.to_period("M").astype(str)
    groups=[g[col].to_numpy(float) for _,g in d.groupby("month") if len(g)]
    if len(groups)<2:
        return {}
    rng=np.random.default_rng(SEED)
    vals=np.empty(BOOT,float)
    for i in range(BOOT):
        pick=rng.integers(0,len(groups),size=len(groups))
        vals[i]=np.concatenate([groups[j] for j in pick]).mean()
    q=np.quantile(vals,[.025,.10,.50,.90,.975])
    return {"q025":float(q[0]),"q10":float(q[1]),"q50":float(q[2]),"q90":float(q[3]),"q975":float(q[4]),"p_le_zero":float((vals<=0).mean())}

def summarize(z):
    if z.empty:
        return {"n":0}
    x=z["exe_bps_24h"].to_numpy(float)
    r=z["exe_24h_R"].to_numpy(float)
    return {
        "n":int(len(z)),
        "mean_exec24_bp":float(np.mean(x)),
        "median_exec24_bp":float(np.median(x)),
        "win_rate":float((x>0).mean()),
        "mean_exec24_R":float(np.mean(r)),
        "trim1_bp":float(np.mean(np.sort(x)[:-max(1,int(math.ceil(.01*len(x))))])) if len(x)>1 else np.nan,
        "bootstrap_month":boot_month(z,"exe_bps_24h")
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    root=Path(a.root); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)

    all_e=[]; all_c=[]; by={}
    for symdir in sorted([p for p in root.iterdir() if p.is_dir()]):
        ep=symdir/"CONFIRM_EVENTS.csv"
        cp=symdir/"CONTROL_POOL.csv"
        sp=symdir/"SUMMARY.csv"
        if not ep.exists():
            continue
        e=read_scsv(ep); ce=clean_events(e)
        c=read_scsv(cp) if cp.exists() else pd.DataFrame()
        cc=clean_controls(c) if len(c) else pd.DataFrame()
        all_e.append(ce)
        if len(cc): all_c.append(cc)

        s=summarize(ce)
        ctrl=float(cc["exe_bps_24h"].mean()) if len(cc) else np.nan
        s["control_mean_bp"]=ctrl
        s["doji_minus_control_bp"]=float(s["mean_exec24_bp"]-ctrl) if s.get("n",0) and np.isfinite(ctrl) else np.nan
        s["events_total_rows"]=int(len(e))
        s["controls_clean_n"]=int(len(cc))
        if sp.exists():
            try:
                sm=read_scsv(sp)
                if len(sm): s["scanner_summary_row"]=sm.iloc[-1].to_dict()
            except Exception: pass
        by[symdir.name]=s

    pooled=pd.concat(all_e,ignore_index=True) if all_e else pd.DataFrame()
    controls=pd.concat(all_c,ignore_index=True) if all_c else pd.DataFrame()

    p=summarize(pooled)
    ctrl=float(controls["exe_bps_24h"].mean()) if len(controls) else np.nan
    p["control_mean_bp"]=ctrl
    p["doji_minus_control_bp"]=float(p["mean_exec24_bp"]-ctrl) if p.get("n",0) and np.isfinite(ctrl) else np.nan
    p["controls_clean_n"]=int(len(controls))

    years={}
    if len(pooled):
        pooled["year"]=pooled["signal_dt"].dt.year
        for y,g in pooled.groupby("year"):
            years[str(int(y))]=summarize(g)

    verdict="FTMO_TRANSPORT_POSITIVE" if p.get("n",0)>=50 and p.get("mean_exec24_bp",np.nan)>0 and p.get("doji_minus_control_bp",np.nan)>0 else "FTMO_TRANSPORT_REJECTED"
    result={
        "method":"exact recovered D032_C1_CONFIRM_DojiStar_H1_v1_00.mq5 logic on FTMO, 1 minute OHLC, canonical clean feed-gap gate",
        "by_symbol":by,
        "pooled":p,
        "yearly":years,
        "verdict":verdict,
        "2026_accessed":False
    }
    (out/"EXACT_PARITY_ANALYSIS.json").write_text(json.dumps(result,indent=2,default=str),encoding="utf-8")
    print(json.dumps(result,indent=2),flush=True)

if __name__=="__main__":
    main()
