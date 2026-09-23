from pathlib import Path
import argparse, json, math, traceback
import numpy as np
import pandas as pd

SEED=3201
BOOT=10000

def read_scsv(p):
    # MQL5 FileOpen(... FILE_CSV ...) defaults to Unicode unless FILE_ANSI is supplied.
    # The recovered D032 scanner therefore writes UTF-16LE CSV files.
    last=None
    for enc in ("utf-16","utf-16-le","utf-8-sig","utf-8","cp1252"):
        try:
            return pd.read_csv(p,sep=";",encoding=enc)
        except Exception as e:
            last=e
    raise RuntimeError(f"Cannot parse {p}: {last}")

def num(x):
    return pd.to_numeric(x,errors="coerce")

def parse_dt(x):
    return pd.to_datetime(x,errors="coerce",dayfirst=False)

def clean_events(d):
    needed=["feed_gap","missing_horizons","exe_bps_24h","exe_24h_R","signal_end_server"]
    missing=[c for c in needed if c not in d.columns]
    if missing: raise RuntimeError(f"CONFIRM_EVENTS missing columns {missing}; got {list(d.columns)}")
    z=d.copy()
    z["feed_gap"]=num(z["feed_gap"]).fillna(1).astype(int)
    z["missing_horizons"]=num(z["missing_horizons"]).fillna(999).astype(int)
    z["exe_bps_24h"]=num(z["exe_bps_24h"])
    z["net_exe_bps_24h"]=num(z["net_exe_bps_24h"]) if "net_exe_bps_24h" in z.columns else z["exe_bps_24h"]
    z["exe_24h_R"]=num(z["exe_24h_R"])
    z["signal_dt"]=parse_dt(z["signal_end_server"])
    # Canonical C1 clean gate.
    return z[(z["feed_gap"]==0)&(z["missing_horizons"]==0)&z["exe_bps_24h"].notna()&z["exe_24h_R"].notna()].copy()

def clean_controls(d):
    needed=["feed_gap","missing_horizons","exe_bps_24h"]
    missing=[c for c in needed if c not in d.columns]
    if missing: raise RuntimeError(f"CONTROL_POOL missing columns {missing}; got {list(d.columns)}")
    z=d.copy()
    z["feed_gap"]=num(z["feed_gap"]).fillna(1).astype(int)
    z["missing_horizons"]=num(z["missing_horizons"]).fillna(999).astype(int)
    z["exe_bps_24h"]=num(z["exe_bps_24h"])
    return z[(z["feed_gap"]==0)&(z["missing_horizons"]==0)&z["exe_bps_24h"].notna()].copy()

def boot_month(z,col):
    d=z.dropna(subset=["signal_dt",col]).copy()
    if d.empty:return {}
    d["month"]=d["signal_dt"].dt.to_period("M").astype(str)
    groups=[g[col].to_numpy(float) for _,g in d.groupby("month") if len(g)]
    if len(groups)<2:return {}
    rng=np.random.default_rng(SEED); vals=np.empty(BOOT,float)
    for i in range(BOOT):
        pick=rng.integers(0,len(groups),size=len(groups))
        vals[i]=np.concatenate([groups[j] for j in pick]).mean()
    q=np.quantile(vals,[.025,.10,.50,.90,.975])
    return {"q025":float(q[0]),"q10":float(q[1]),"q50":float(q[2]),"q90":float(q[3]),"q975":float(q[4]),"p_le_zero":float((vals<=0).mean())}

def trim_best(x,pct):
    x=np.asarray(x,float);x=x[np.isfinite(x)]
    if len(x)<2:return np.nan
    k=max(1,int(math.ceil(pct*len(x))))
    if k>=len(x):return np.nan
    return float(np.sort(x)[:-k].mean())

def summarize(z):
    if z.empty:return {"n":0}
    x=z["exe_bps_24h"].to_numpy(float); r=z["exe_24h_R"].to_numpy(float)
    return {
        "n":int(len(z)),
        "mean_exec24_bp":float(np.mean(x)),
        "median_exec24_bp":float(np.median(x)),
        "win_rate":float((x>0).mean()),
        "mean_exec24_R":float(np.mean(r)),
        "trim1_bp":trim_best(x,.01),
        "trim2_bp":trim_best(x,.02),
        "trim5_bp":trim_best(x,.05),
        "bootstrap_month":boot_month(z,"exe_bps_24h")
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",required=True);ap.add_argument("--out",required=True)
    a=ap.parse_args();root=Path(a.root);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    print(f"ANALYZE ROOT: {root}",flush=True)
    all_e=[];all_c=[];by={};diagnostics={}
    dirs=sorted([p for p in root.iterdir() if p.is_dir()])
    if not dirs:raise RuntimeError(f"No symbol directories under {root}")
    for symdir in dirs:
        ep=symdir/"CONFIRM_EVENTS.csv";cp=symdir/"CONTROL_POOL.csv";sp=symdir/"SUMMARY.csv"
        print(f"{symdir.name}: events={ep.exists()} controls={cp.exists()} summary={sp.exists()}",flush=True)
        if not ep.exists():continue
        try:
            e=read_scsv(ep); ce=clean_events(e)
            c=read_scsv(cp) if cp.exists() else pd.DataFrame()
            cc=clean_controls(c) if len(c) else pd.DataFrame()
            all_e.append(ce)
            if len(cc):all_c.append(cc)
            s=summarize(ce)
            ctrl=float(cc["exe_bps_24h"].mean()) if len(cc) else np.nan
            s["control_mean_bp"]=ctrl
            s["doji_minus_control_bp"]=float(s["mean_exec24_bp"]-ctrl) if s.get("n",0) and np.isfinite(ctrl) else np.nan
            s["events_total_rows"]=int(len(e));s["events_clean_n"]=int(len(ce));s["controls_clean_n"]=int(len(cc))
            if sp.exists():
                sm=read_scsv(sp)
                if len(sm):s["scanner_summary_row"]={str(k):str(v) for k,v in sm.iloc[-1].to_dict().items()}
            by[symdir.name]=s
            diagnostics[symdir.name]={"event_columns":list(e.columns),"event_rows":int(len(e)),"clean_rows":int(len(ce)),
                                      "control_rows":int(len(c)),"control_clean_rows":int(len(cc))}
            print(f"{symdir.name}: total={len(e)} clean={len(ce)} mean={s.get('mean_exec24_bp')}",flush=True)
        except Exception as e:
            diagnostics[symdir.name]={"error":repr(e)}
            print(f"{symdir.name} FAILED: {e}",flush=True)
            traceback.print_exc()
            raise

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
            if pd.notna(y):years[str(int(y))]=summarize(g)

    verdict="FTMO_TRANSPORT_POSITIVE" if p.get("n",0)>=50 and p.get("mean_exec24_bp",np.nan)>0 and p.get("doji_minus_control_bp",np.nan)>0 else "FTMO_TRANSPORT_REJECTED"
    result={
      "method":"exact recovered D032_C1_CONFIRM_DojiStar_H1_v1_00.mq5 output; canonical clean feed-gap/missing-horizon gate",
      "by_symbol":by,"pooled":p,"yearly":years,"diagnostics":diagnostics,
      "verdict":verdict,"2026_accessed":False
    }
    (out/"EXACT_PARITY_ANALYSIS.json").write_text(json.dumps(result,indent=2,default=str),encoding="utf-8")
    print(json.dumps(result,indent=2),flush=True)

if __name__=="__main__":
    main()
