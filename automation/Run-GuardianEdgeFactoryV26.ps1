param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v26_final_preoos.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,hashlib,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");RAW=ROOT/"DataLake"/"raw"/"histdata";V24=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v24";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v26";OUT.mkdir(parents=True,exist_ok=True)
SHA="471e6564b7743885ecef1a385adca7f4f92e939f04688e8b04bf8377673cad79"
runs=sorted([p for p in V24.glob("GEF24-*") if (p/"FROZEN_VALIDATION_CANDIDATES.csv").exists()]);src=runs[-1];fp=src/"FROZEN_VALIDATION_CANDIDATES.csv"
if hashlib.sha256(fp.read_bytes()).hexdigest()!=SHA:raise RuntimeError("V24 hash mismatch")
F=pd.read_csv(fp);r=F[(F.target=="XAGUSD")&(F.driver=="XAUUSD")&(F.feature=="divret_6b")&(F.horizon_min==240)]
if len(r)!=1:raise RuntimeError("Frozen survivor identity mismatch")
r=r.iloc[0];thr=float(r.threshold_abs);direction=int(r.direction);h=240;started=time.time()
rid="GEF26-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-started;eta=e/i*(n-i) if i else 0;print(f"[GEF26] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
def load(m):
 z=[]
 for y in range(2010,2023):
  p=RAW/m/"M1"/f"{m}_M1_{y}.parquet"
  if p.exists():
   d=pd.read_parquet(p);tc=next(c for c in d if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc]);z.append(d[["close"]].sort_index().resample("5min",label="right",closed="left").last().dropna())
 return pd.concat(z).sort_index()
prog(1,6,"load 2010-2022 only");A=load("XAGUSD");B=load("XAUUSD");idx=A.index.intersection(B.index);a=A.close.reindex(idx);b=B.close.reindex(idx)
def feature(driver_shift=0):
 bb=b.shift(driver_shift);return np.log(a/a.shift(6))-np.log(bb/bb.shift(6))
def pnl(x,period,delay=0):
 lo,hi=period;xx=x[(x.index.year>=lo)&(x.index.year<=hi)];sel=xx[xx.abs()>=thr];sig=direction*np.sign(sel);en=a.reindex(sig.index+pd.Timedelta(minutes=delay));ex=a.reindex(sig.index+pd.Timedelta(minutes=delay+h));en.index=sig.index;ex.index=sig.index;return (sig*np.log(ex/en)*1e4).dropna()
base=feature();period=(2010,2022);p=pnl(base,period)
prog(2,6,"cost + concentration surfaces")
costs={str(c):float(p.mean()-c) for c in [0,.25,.5,1,1.5,2,2.5,3,5,7.5,10]}
trim={}
for q in [.001,.005,.01,.02,.05]:
 k=max(1,int(len(p)*q));trim[str(q)]=float(p.drop(p.nlargest(k).index).mean())
hour=pd.DataFrame({"hour":p.index.hour,"p":p.values}).groupby("hour").agg(n=("p","size"),mean_bp=("p","mean"),sum_bp=("p","sum")).reset_index();hour.to_csv(O/"VENDOR_HOUR_PROFILE.csv",index=False)
# remove best vendor-hour by total contribution
besth=int(hour.sort_values("sum_bp",ascending=False).iloc[0].hour);nohour=p[p.index.hour!=besth]
prog(3,6,"lead/lag anti-asynchronism")
# pandas shift +k = stale driver (older values); -k = future-driver placebo. 1 bar=5m.
ll=[]
for bars in [-12,-6,-3,-1,0,1,3,6,12]:
 pp=pnl(feature(bars),period)
 ll.append({"driver_shift_bars":bars,"minutes":bars*5,"semantics":"FUTURE_PLACEBO" if bars<0 else ("BASELINE" if bars==0 else "STALE_DRIVER"),"n":len(pp),"gross_bp":float(pp.mean())})
pd.DataFrame(ll).to_csv(O/"DRIVER_LEAD_LAG_PLACEBO.csv",index=False)
prog(4,6,"year/session concentration")
yr=p.groupby(p.index.year).agg(n="size",mean_bp="mean",sum_bp="sum").reset_index();yr.to_csv(O/"YEAR_PROFILE.csv",index=False)
# Exact common-grid occupancy in final minute proxy is impossible from resampled close alone; record limitation.
# Predeclared gate: baseline robust after costs 1bp, trim1%, remove best vendor hour; stale +5/+15 positive; future placebo must not exceed baseline by >50%.
stale5=next(x["gross_bp"] for x in ll if x["driver_shift_bars"]==1);stale15=next(x["gross_bp"] for x in ll if x["driver_shift_bars"]==3)
futuremax=max(x["gross_bp"] for x in ll if x["driver_shift_bars"]<0);baseline=float(p.mean())
gate=bool(costs["1"]>0 and trim["0.01"]>0 and nohour.mean()>0 and stale5>0 and stale15>0 and futuremax<=1.5*baseline)
prog(5,6,"evaluate final pre-OOS gate")
summary={"candidate":"XAGUSD<-XAUUSD divret_6b H240 P99 direction -1","threshold_abs":thr,"period":"2010-2022 only","n":len(p),"gross_bp":baseline,"cost_surface_bp_per_trade":costs,"trim_best_fraction":trim,"best_vendor_hour_by_sum":besth,"remove_best_vendor_hour_bp":float(nohour.mean()),"stale_driver_5m_bp":stale5,"stale_driver_15m_bp":stale15,"max_future_driver_placebo_bp":futuremax,"pre_oos_gate_pass":gate,"limitations":["vendor timestamp hour is not asserted to be UTC/exchange local time","future-driver placebo diagnoses lead/lag/asynchronism but does not prove economic causality","cost surface is sensitivity, not empirical broker cost"]}
(O/"FINAL_PREOOS_SUMMARY.json").write_text(json.dumps(summary,indent=2))
receipt={"run_id":rid,"status":"COMPLETE","freeze_sha256_verified":SHA,"data_period":"2010-2022 only","locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"pre_oos_gate_pass":gate,"instruction":"STOP FOR HUMAN REVIEW. Do not open 2023-2025 automatically.","errors":[]};(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(6,6,"STOP - OOS untouched");print("\n=== V26 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== FINAL PRE-OOS SUMMARY ===");print(json.dumps(summary,indent=2));print("\n=== LEAD LAG ===");print(pd.DataFrame(ll).to_string(index=False));print("\n=== YEAR PROFILE ===");print(yr.to_string(index=False));print("\n=== HOUR PROFILE ===");print(hour.to_string(index=False));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V26 compile failed"}
Write-Host "=== GEF V26 - FINAL PRE-OOS FORENSIC ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V26 failed"}
