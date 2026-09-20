param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v37_preoos_forensic.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); RAW=ROOT/"DataLake"/"raw"/"histdata"; V36=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v36"; OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v37"; OUT.mkdir(parents=True,exist_ok=True)
t=time.time(); rid="GEF37-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"); O=OUT/rid; O.mkdir()
def prog(i,n,msg):
 e=time.time()-t; eta=e/i*(n-i) if i else 0; print(f"[GEF37] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
runs=sorted([p for p in V36.glob("GEF36-*") if (p/"VALIDATION_RESULT.json").exists() and (p/"RUN_RECEIPT.json").exists()])
if not runs: raise RuntimeError("No V36 validation")
src=runs[-1]; rec=json.loads((src/"RUN_RECEIPT.json").read_text()); val=json.loads((src/"VALIDATION_RESULT.json").read_text())
if rec.get("validation_result")!="PASS" or rec.get("validation_period")!="2018-2022 only": raise RuntimeError("V36 not a PASS validation")
if rec.get("locked_oos_2023_2025_accessed") or rec.get("protected_2026_accessed"): raise RuntimeError("Protected period access flag unexpected")
prog(1,14,f"V36 PASS verified {src.name}")

z=[]
for i,y0 in enumerate(range(2010,2023),2):
 pth=RAW/"XAGUSD"/"M1"/f"XAGUSD_M1_{y0}.parquet"
 if not pth.exists(): raise RuntimeError(f"Missing {pth}")
 d=pd.read_parquet(pth); tc=next(c for c in d if c.lower() in ("datetime","time","timestamp")); d.index=pd.to_datetime(d[tc])
 z.append(d[["close"]].sort_index().resample("15min",label="right",closed="left").last().dropna())
 prog(i,14,f"loaded <=2022 forensic year {y0}")
a=pd.concat(z).sort_index().close
ret=np.log(a/a.shift(1)); rv=ret.rolling(16,min_periods=16).std(); slow=rv.rolling(320,min_periods=80).median(); ratio=rv/slow
reg=(ratio>.75)&(ratio<1.5); shock=ret.abs()>=ret.abs().rolling(20*96,min_periods=480).quantile(.95).shift(1)
base_y=np.log(a.shift(-16)/a)*1e4
q=pd.concat([ret.rename("r"),base_y.rename("y"),reg.rename("reg"),shock.rename("shock")],axis=1).dropna(); q=q[q.reg&q.shock]; p=-np.sign(q.r)*q.y

def series_with_offset(off_bars):
 y=np.log(a.shift(-(16+off_bars))/a.shift(-off_bars))*1e4
 qq=pd.concat([ret.rename("r"),y.rename("y"),reg.rename("reg"),shock.rename("shock")],axis=1).dropna(); qq=qq[qq.reg&qq.shock]
 return -np.sign(qq.r)*qq.y

leadlag={}
for mins in [-60,-30,-15,0,15,30,60]:
 bars=int(mins/15); s=series_with_offset(bars)
 leadlag[str(mins)]={"n":len(s),"gross_bp":float(s.mean())}
trim={}
for frac in [.001,.005,.01,.02,.05]:
 k=max(1,int(np.ceil(len(p)*frac))); s=p.drop(p.nlargest(k).index); trim[str(frac)]={"removed":k,"gross_bp":float(s.mean())}
day_sum=p.groupby(p.index.normalize()).sum().sort_values(ascending=False)
remove_days={}
for k in [1,3,5,10,20]:
 s=p[~p.index.normalize().isin(set(day_sum.head(k).index))]; remove_days[str(k)]={"gross_bp":float(s.mean())}
yrs=p.groupby(p.index.year).agg(["count","mean"])
hrs=p.groupby(p.index.hour).agg(["count","mean"])
# bootstrap by day
day_groups=[g.to_numpy() for _,g in p.groupby(p.index.normalize())]
rng=np.random.default_rng(370037)
boots=[]
for _ in range(3000):
 idx=rng.integers(0,len(day_groups),len(day_groups)); vals=np.concatenate([day_groups[i] for i in idx]); boots.append(float(vals.mean()))
ci=[float(np.quantile(boots,.025)),float(np.quantile(boots,.975))]
# sign-flip null
days=p.index.normalize(); uniq=pd.Index(days.unique()); inv=pd.Categorical(days,categories=uniq).codes; arr=p.to_numpy(); obs=abs(float(p.mean())); ge=0
rng=np.random.default_rng(370038)
for _ in range(5000):
 signs=rng.choice(np.array([-1.0,1.0]),size=len(uniq))
 if abs(float(np.mean(arr*signs[inv])))>=obs: ge+=1
null_p=(ge+1)/5001
future_max=max(v["gross_bp"] for k,v in leadlag.items() if int(k)<0)
baseline=float(p.mean())
forensic_pass=bool(trim["0.01"]["gross_bp"]>0 and trim["0.02"]["gross_bp"]>0 and remove_days["5"]["gross_bp"]>0 and ci[0]>0 and null_p<=.05 and future_max <= 1.5*baseline)
res={"candidate":{"market":"XAGUSD","regime":"normal","horizon_min":240,"mode":"reversal"},
"period":"2010-2022 only","n":len(p),"baseline_gross_bp":baseline,"hit":float((p>0).mean()),"trim":trim,"remove_best_days":remove_days,"leadlag_min":leadlag,
"yearly":{str(int(i)):{"n":int(r["count"]),"gross_bp":float(r["mean"])} for i,r in yrs.iterrows()},
"vendor_hour":{str(int(i)):{"n":int(r["count"]),"gross_bp":float(r["mean"])} for i,r in hrs.iterrows()},
"day_bootstrap_95_ci":ci,"daily_signflip_p":float(null_p),"future_placebo_max_bp":float(future_max),"future_placebo_ratio_to_baseline":float(future_max/baseline if baseline else np.nan),
"preoos_forensic_pass":forensic_pass,
"gate":{"trim_1pct":">0","trim_2pct":">0","remove_best_5_days":">0","bootstrap_lower_95":">0","daily_signflip_p":"<=0.05","future_driver_placebo":"not applicable; single-market temporal placebo must be <=1.5x baseline"}}
prog(14,14,f"forensic {'PASS' if forensic_pass else 'FAIL'} | baseline {baseline:.3f} trim2 {trim['0.02']['gross_bp']:.3f} CI [{ci[0]:.3f},{ci[1]:.3f}] null {null_p:.4f} future_ratio {res['future_placebo_ratio_to_baseline']:.2f}")
(O/"PREOOS_FORENSIC_RESULT.json").write_text(json.dumps(res,indent=2))
receipt={"run_id":rid,"status":"COMPLETE","source_v36":src.name,"period":"2010-2022 only","preoos_forensic_result":"PASS" if forensic_pass else "FAIL","locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":[],"instruction":"STOP. Human review required. Do not open 2023-2025 automatically."}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
print("\n=== V37 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== PRE-OOS FORENSIC ===");print(json.dumps(res,indent=2));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V37 compile failed"}
Write-Host "=== GEF V37 - FINAL PRE-OOS FORENSIC <=2022 ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V37 failed"}
