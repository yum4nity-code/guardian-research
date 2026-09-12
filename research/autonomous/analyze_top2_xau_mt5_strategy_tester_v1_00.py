#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, os
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd

def atomic(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    os.replace(tmp,path)

def metrics(df):
    vals=df["net"].to_numpy(float) if len(df) else np.array([],float)
    wins=vals[vals>0]; losses=vals[vals<0]
    equity=np.cumsum(vals) if len(vals) else np.array([],float)
    peak=np.maximum.accumulate(np.r_[0.0,equity]) if len(vals) else np.array([0.0])
    eq2=np.r_[0.0,equity]
    dd=peak-eq2
    def streak(pred):
        best=cur=0
        for x in vals:
            if pred(x): cur+=1; best=max(best,cur)
            else: cur=0
        return best
    gross_profit=float(wins.sum()) if len(wins) else 0.0
    gross_loss=float(-losses.sum()) if len(losses) else 0.0
    return {
        "trades":int(len(vals)),
        "net":float(vals.sum()) if len(vals) else 0.0,
        "profit_factor":(gross_profit/gross_loss) if gross_loss>0 else (None if gross_profit==0 else 999999.0),
        "win_rate":float((vals>0).mean()) if len(vals) else None,
        "avg_trade":float(vals.mean()) if len(vals) else None,
        "median_trade":float(np.median(vals)) if len(vals) else None,
        "gross_profit":gross_profit,
        "gross_loss":gross_loss,
        "max_drawdown_trade_close":float(dd.max()),
        "best_trade":float(vals.max()) if len(vals) else None,
        "worst_trade":float(vals.min()) if len(vals) else None,
        "ex_best_positive_net":float(vals.sum()-max(0.0,float(vals.max()))) if len(vals) else 0.0,
        "max_win_streak":streak(lambda x:x>0),
        "max_loss_streak":streak(lambda x:x<0),
    }

def load(path):
    z=pd.read_csv(path,sep=";")
    req={"candidate_id","entry_time","exit_time","net_account_currency"}
    if not req.issubset(z.columns): raise RuntimeError(f"bad trade csv {path}")
    z["entry_time"]=pd.to_datetime(z.entry_time,format="%Y.%m.%d %H:%M:%S",utc=True)
    z["exit_time"]=pd.to_datetime(z.exit_time,format="%Y.%m.%d %H:%M:%S",utc=True)
    z["net"]=pd.to_numeric(z.net_account_currency,errors="raise")
    z=z.sort_values("entry_time").reset_index(drop=True)
    return z

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input-dir",required=True)
    ap.add_argument("--output-dir",required=True)
    a=ap.parse_args()
    inp=Path(a.input_dir); out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    ids=["R6B-347","R6B-307"]
    result={"schema":1,"phase":"top2-xau-mt5-strategy-tester-analysis","status":"PASS","generated_at_utc":datetime.now(timezone.utc).isoformat(),"model":"actual MT5 Strategy Tester, 1-minute OHLC","candidates":{}}
    monthly_series={}
    rows=[]
    for cid in ids:
        z=load(inp/f"{cid}_TRADES.csv")
        full=metrics(z)
        years={}
        for year in range(2017,2027):
            y=z[z.entry_time.dt.year==year]
            years[str(year)]=metrics(y)
        months={}
        for month,g in z.groupby(z.entry_time.dt.strftime("%Y-%m")):
            months[str(month)]=metrics(g)
            rows.append({"candidate_id":cid,"month":str(month),**months[str(month)]})
        rolling={}
        month_index=pd.period_range("2017-01","2026-07",freq="M")
        net_by_month=z.groupby(z.entry_time.dt.to_period("M"))["net"].sum()
        vec=np.array([float(net_by_month.get(m,0.0)) for m in month_index],float)
        monthly_series[cid]=(month_index,vec)
        for width in (6,12):
            arr=[]
            for i in range(width-1,len(month_index)):
                start=month_index[i-width+1].start_time.tz_localize("UTC")
                end=(month_index[i].end_time+pd.Timedelta(nanoseconds=1)).tz_localize("UTC")
                g=z[(z.entry_time>=start)&(z.entry_time<end)]
                arr.append({"end_month":str(month_index[i]),**metrics(g)})
            rolling[f"{width}m"]=arr
        result["candidates"][cid]={
            "full":full,
            "yearly":years,
            "monthly":months,
            "rolling":rolling,
            "positive_years":sum(years[str(y)]["net"]>0 for y in range(2017,2026)),
            "negative_years":sum(years[str(y)]["net"]<0 for y in range(2017,2026)),
            "2026_jan_jul":years["2026"],
        }
    idx,a1=monthly_series[ids[0]]; _,a2=monthly_series[ids[1]]
    corr=float(np.corrcoef(a1,a2)[0,1]) if np.std(a1)>0 and np.std(a2)>0 else None
    comb=a1+a2
    result["pair"]={
        "monthly_net_correlation":corr,
        "simple_combined_net":float(comb.sum()),
        "positive_month_fraction":float((comb>0).mean()),
        "worst_combined_month":str(idx[int(np.argmin(comb))]),
        "worst_combined_month_net":float(comb.min()),
        "best_combined_month":str(idx[int(np.argmax(comb))]),
        "best_combined_month_net":float(comb.max()),
        "note":"Simple 1-lot sum, no shared-margin interaction model."
    }
    rp=out/"top2_mt5_strategy_tester_analysis.json"
    atomic(rp,result)
    pd.DataFrame(rows).to_csv(out/"top2_mt5_monthly_metrics.csv",index=False)
    print(json.dumps({"status":"PASS","R6B-347":result["candidates"]["R6B-347"]["full"],"R6B-307":result["candidates"]["R6B-307"]["full"],"pair_corr":corr}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
