param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v27_temporal_autopsy.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");RAW=ROOT/"DataLake"/"raw"/"histdata";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v27";OUT.mkdir(parents=True,exist_ok=True)
THR=.008340;DIR=-1;H=240;started=time.time();rid="GEF27-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-started;eta=e/i*(n-i) if i else 0;print(f"[GEF27] {i}/{n} {100*i/n:.1f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
def raw(m):
 z=[]
 for y in range(2010,2023):
  p=RAW/m/"M1"/f"{m}_M1_{y}.parquet"
  if p.exists():
   d=pd.read_parquet(p);tc=next(c for c in d if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc]);z.append(d[["close"]].sort_index())
 return pd.concat(z).sort_index()[~pd.concat(z).sort_index().index.duplicated(keep="last")]
prog(1,8,"load raw M1 2010-2022");A=raw("XAGUSD");B=raw("XAUUSD")
# Right-edge M5 closes: last observed raw minute in [t-5,t)
def m5(x):return x.close.resample("5min",label="right",closed="left").last().dropna()
a,b=m5(A),m5(B);idx=a.index.intersection(b.index);a=a.reindex(idx);b=b.reindex(idx)
def eval_signal(bb,label):
 x=np.log(a/a.shift(6))-np.log(bb/bb.shift(6));s=x[x.abs()>=THR];sig=DIR*np.sign(s);en=a.reindex(sig.index);ex=a.reindex(sig.index+pd.Timedelta(minutes=H));en.index=sig.index;ex.index=sig.index;p=(sig*np.log(ex/en)*1e4).dropna();return {"test":label,"n":len(p),"gross_bp":float(p.mean()),"hit":float((p>0).mean())}
prog(2,8,"minute lead/lag sweep")
ll=[]
for mins in range(-60,61,5):
 # positive = stale/older driver; negative = future driver
 ll.append(eval_signal(b.shift(mins//5),f"{mins:+d}m"))
pd.DataFrame(ll).to_csv(O/"MINUTE_LEAD_LAG.csv",index=False)
prog(3,8,"raw-bar freshness diagnostics")
# age in minutes of last raw observation before each right-edge decision label
def ages(R,labels):
 ri=R.index.values; q=(labels-pd.Timedelta(nanoseconds=1)).values;pos=np.searchsorted(ri,q,side="right")-1;valid=pos>=0;out=np.full(len(labels),np.nan);out[valid]=(labels.values[valid]-ri[pos[valid]])/np.timedelta64(1,"m");return out
fresh=pd.DataFrame({"t":idx,"xag_age_min":ages(A,idx),"xau_age_min":ages(B,idx)});fresh["age_diff_min"]=fresh.xag_age_min-fresh.xau_age_min
fresh.describe(percentiles=[.5,.9,.95,.99]).to_csv(O/"FRESHNESS_SUMMARY.csv")
prog(4,8,"freshness-restricted baseline")
x=np.log(a/a.shift(6))-np.log(b/b.shift(6));sel=x[x.abs()>=THR];sig=DIR*np.sign(sel);en=a.reindex(sig.index);ex=a.reindex(sig.index+pd.Timedelta(minutes=H));en.index=sig.index;ex.index=sig.index;p=(sig*np.log(ex/en)*1e4).dropna()
fr=fresh.set_index("t").reindex(p.index)
fresh_tests=[]
for lim in [1,2,5]:
 mask=(fr.xag_age_min<=lim)&(fr.xau_age_min<=lim)&(fr.age_diff_min.abs()<=1)
 q=p[mask.fillna(False)];fresh_tests.append({"max_age_min":lim,"n":len(q),"gross_bp":float(q.mean()) if len(q) else None})
pd.DataFrame(fresh_tests).to_csv(O/"FRESHNESS_RESTRICTED.csv",index=False)
prog(5,8,"whole-day driver placebo")
# deterministic circular whole-day shifts, preserving intraday clock structure approximately via 288 M5 bars/day
day=[]
for days in [-60,-30,-10,-5,5,10,30,60]:
 day.append(eval_signal(b.shift(days*288),f"{days:+d}d"))
pd.DataFrame(day).to_csv(O/"WHOLE_DAY_PLACEBO.csv",index=False)
prog(6,8,"session exclusion robustness")
sess=[]
for h0 in range(24):
 q=p[p.index.hour!=h0];sess.append({"excluded_vendor_hour":h0,"n":len(q),"gross_bp":float(q.mean())})
pd.DataFrame(sess).to_csv(O/"EXCLUDE_EACH_HOUR.csv",index=False)
prog(7,8,"diagnostic decision")
base=next(z["gross_bp"] for z in ll if z["test"]=="+0m");fut30=next(z["gross_bp"] for z in ll if z["test"]=="-30m");stale30=next(z["gross_bp"] for z in ll if z["test"]=="+30m")
fr1=next(z for z in fresh_tests if z["max_age_min"]==1)
daymax=max(abs(z["gross_bp"]) for z in day)
# Diagnostic, not alpha retuning. Require fresh subset positive, baseline > stale30, future30 <=2x baseline, and day placebo < baseline.
passed=bool(fr1["n"]>=500 and fr1["gross_bp"]>0 and base>stale30 and fut30<=2*base and daymax<base)
summary={"candidate":"XAGUSD<-XAUUSD divret_6b H240 P99 direction -1","period":"2010-2022 only","threshold_abs":THR,"baseline_bp":base,"future30_bp":fut30,"stale30_bp":stale30,"fresh_1m":fr1,"max_abs_whole_day_placebo_bp":daymax,"temporal_integrity_pass":passed,"interpretation":"Diagnostic only. No feature/threshold/direction selection performed.","limitations":["HistData vendor timezone truth still not independently established","whole-day shifts use 288 M5 bars as an approximate clock-preserving control across market gaps","no 2023+ data accessed"]}
(O/"TEMPORAL_AUTOPSY_SUMMARY.json").write_text(json.dumps(summary,indent=2));receipt={"run_id":rid,"status":"COMPLETE","data_period":"2010-2022 only","locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"temporal_integrity_pass":passed,"instruction":"STOP FOR HUMAN REVIEW; do not open OOS automatically.","errors":[]};(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(8,8,"STOP - OOS untouched");print("\n=== V27 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== TEMPORAL AUTOPSY ===");print(json.dumps(summary,indent=2));print("\n=== MINUTE LEAD/LAG ===");print(pd.DataFrame(ll).to_string(index=False));print("\n=== FRESHNESS ===");print(pd.DataFrame(fresh_tests).to_string(index=False));print("\n=== WHOLE-DAY PLACEBOS ===");print(pd.DataFrame(day).to_string(index=False));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V27 compile failed"}
Write-Host "=== GEF V27 - XAU/XAG TEMPORAL AUTOPSY ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V27 failed"}
