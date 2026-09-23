from pathlib import Path
import argparse,json,math
import numpy as np
import pandas as pd

SEED=111120
BOOT=20000
COMMISSION_USD_PER_LOT_RT=5.0
CONTRACT_SIZE=100000.0

def jd(p,o): p.write_text(json.dumps(o,indent=2,default=str)+"\n",encoding="utf-8")

def trim_best(x,p):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    if len(x)<2:return np.nan
    k=max(1,int(math.ceil(len(x)*p)))
    if k>=len(x):return np.nan
    return float(np.sort(x)[:-k].mean())

def remove_best(x,k):
    x=np.asarray(x,float);x=x[np.isfinite(x)]
    if len(x)<=k:return np.nan
    return float(np.sort(x)[:-k].mean())

def maxdd(x):
    c=np.cumsum(np.asarray(x,float))
    if not len(c):return np.nan
    peaks=np.maximum.accumulate(np.r_[0.0,c])
    d=np.r_[0.0,c]-peaks
    return float(d.min())

def max_loss_streak(x):
    best=cur=0
    for v in np.asarray(x,float):
        if v<0:cur+=1;best=max(best,cur)
        else:cur=0
    return int(best)

def month_boot(times,vals):
    d=pd.DataFrame({"t":pd.to_datetime(times),"v":np.asarray(vals,float)}).dropna()
    d["month"]=d["t"].dt.to_period("M").astype(str)
    groups=[g["v"].to_numpy(float) for _,g in d.groupby("month") if len(g)]
    rng=np.random.default_rng(SEED)
    if len(groups)<2:return {}
    out=np.empty(BOOT,float)
    for i in range(BOOT):
        pick=rng.integers(0,len(groups),size=len(groups))
        out[i]=np.concatenate([groups[j] for j in pick]).mean()
    q=np.quantile(out,[.025,.10,.50,.90,.975])
    return {"q025_bp":float(q[0]),"q10_bp":float(q[1]),"q50_bp":float(q[2]),"q90_bp":float(q[3]),"q975_bp":float(q[4]),"p_mean_le_zero":float((out<=0).mean())}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=r"D:\MT5_Backtests")
    ap.add_argument("--out",required=True)
    a=ap.parse_args(); root=Path(a.root); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)

    base=root/"Research"/"ExecutionAudit"
    runs=sorted([p for p in base.glob("V111_EURUSD_H11_120M_*") if p.is_dir()],key=lambda p:p.stat().st_mtime,reverse=True)
    if not runs: raise RuntimeError("No existing V111_EURUSD_H11_120M_* audit folder found.")
    run=runs[0]
    led=run/"EURUSD_FTMO_EXECUTION_LEDGER.csv"
    final=run/"FINAL_SUMMARY.json"
    if not led.exists(): raise RuntimeError(f"Missing existing execution ledger {led}")
    if not final.exists(): raise RuntimeError(f"Missing existing final summary {final}")

    f=json.loads(final.read_text(encoding="utf-8"))
    if f.get("2026_accessed") is not False:
        raise RuntimeError("Existing run does not prove 2026_accessed=false")
    d=pd.read_csv(led)
    z=d[d["execution_available"].astype(str).str.lower().isin(["true","1"])].copy()
    if len(z)!=717: raise RuntimeError(f"Expected 717 executable rows, got {len(z)}")
    z["entry_bid"]=pd.to_numeric(z["entry_bid"],errors="coerce")
    z["ftmo_exec_bp"]=pd.to_numeric(z["ftmo_exec_bp"],errors="coerce")
    z=z.dropna(subset=["entry_bid","ftmo_exec_bp"]).copy()
    z["event_time"]=pd.to_datetime(z["source_entry_label"],errors="coerce")
    z["commission_bp"]=COMMISSION_USD_PER_LOT_RT/(z["entry_bid"]*CONTRACT_SIZE)*10000.0
    z["net_after_commission_bp"]=z["ftmo_exec_bp"]-z["commission_bp"]

    x=z["net_after_commission_bp"].to_numpy(float)
    mean=float(x.mean()); med=float(np.median(x)); win=float((x>0).mean())
    years={str(int(y)):{"n":int(len(g)),"mean_bp":float(g["net_after_commission_bp"].mean())}
           for y,g in z.groupby(z["event_time"].dt.year)}
    months={str(m):{"n":int(len(g)),"mean_bp":float(g["net_after_commission_bp"].mean())}
            for m,g in z.groupby(z["event_time"].dt.to_period("M").astype(str))}
    boot=month_boot(z["event_time"],x)

    friction=[]
    for extra in np.arange(0,1.5001,.10):
        y=x-extra
        friction.append({"extra_roundtrip_bp":round(float(extra),2),"mean_net_bp":float(y.mean()),"win_rate":float((y>0).mean())})
    pd.DataFrame(friction).to_csv(out/"EURUSD_C8_EXTRA_FRICTION_GRID.csv",index=False)

    mean_price=float(z["entry_bid"].mean())
    pip_bp=0.0001/mean_price*10000.0
    vol=[]
    for band,pips in [(1,0.0),(2,0.4),(3,0.8),(4,1.2)]:
        extra=pips*pip_bp
        y=x-extra
        vol.append({"illustrative_band":band,"illustrative_roundtrip_pips":pips,"extra_bp_at_mean_price":extra,
                    "mean_net_bp":float(y.mean()),"win_rate":float((y>0).mean()),
                    "NOTE":"scenario stress based on FTMO published illustrative EURUSD example; not current guaranteed band pricing"})
    pd.DataFrame(vol).to_csv(out/"EURUSD_C8_VOLUME_BAND_ILLUSTRATIVE_STRESS.csv",index=False)

    z.to_csv(out/"EURUSD_C8_COMMISSION_ADJUSTED_LEDGER.csv",index=False)
    classification=("ECONOMICALLY_REJECTED" if mean<=0 else
                    "FORWARD_SHADOW_WORTHY" if boot.get("q10_bp",np.nan)>0 and trim_best(x,.01)>0
                    else "FRAGILE_FORWARD_SHADOW")

    result={
      "schema":1,
      "candidate":"V111-C8-EURUSD-H11-SHORT-120M",
      "source_run":str(run),
      "reused_existing_market_data_only":True,
      "2026_accessed":False,
      "n":int(len(z)),
      "current_ftmo_forex_commission":{"usd_per_lot_per_side":2.5,"roundtrip_usd_per_lot":5.0,
        "mean_commission_bp":float(z["commission_bp"].mean())},
      "after_observed_spread_and_commission":{
        "mean_bp":mean,"median_bp":med,"win_rate":win,
        "yearly":years,"monthly":months,"bootstrap_month":boot,
        "trim1_bp":trim_best(x,.01),"trim2_bp":trim_best(x,.02),"trim5_bp":trim_best(x,.05),
        "remove_best10_bp":remove_best(x,10),"remove_best20_bp":remove_best(x,20),
        "max_drawdown_cumulative_bp":maxdd(x),"max_consecutive_losses":max_loss_streak(x)
      },
      "friction_budget":{
        "break_even_extra_bp":mean,
        "mean_entry_price":mean_price,
        "break_even_extra_pips":mean/pip_bp
      },
      "volume_band_scenarios":vol,
      "classification":classification,
      "news_compatibility":{
        "evaluation_process":"No selected-news restriction per current FTMO FAQ.",
        "standard_ftmo_account":"Open/close restricted from -2m through +2m around selected targeted releases.",
        "swing_account":"Selected-news restriction does not apply.",
        "historical_news_collision_not_measured_here":True
      },
      "retuning_performed":False,
      "live_deployment_authorized":False
    }
    jd(out/"V111_C8_PRODUCTION_READINESS_RESULT.json",result)
    print("=== V111 C8 PRODUCTION READINESS ===")
    print(json.dumps(result,indent=2,default=str))

if __name__=="__main__": main()
