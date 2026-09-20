param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v52_rates_final_forensic.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib,re,xml.etree.ElementTree as ET
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";RAW=DL/"raw"/"histdata";V51=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v51";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v52";OUT.mkdir(parents=True,exist_ok=True)
EXP="b42692779e3ae4bff5229c7d3ef173ac6e7e681d5463463eed446c7f56c1ecc8";KEY="NOM30Y|NSXUSD|level_pct|0.1|5|reversal"
t=time.time();rid="GEF52-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF52] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
runs=sorted([p for p in V51.glob("GEF51-*") if (p/"VALIDATION_SURVIVORS.csv").exists()])
src=None
for p in reversed(runs):
 if hashlib.sha256((p/"VALIDATION_SURVIVORS.csv").read_bytes()).hexdigest()==EXP:src=p;break
if src is None:raise RuntimeError("Exact V51 survivor artifact not found")
F=pd.read_csv(src/"VALIDATION_SURVIVORS.csv")
if len(F)!=1 or F.iloc[0]["key"]!=KEY:raise RuntimeError("Unexpected V51 survivor")
prog(1,14,f"verified sole V51 survivor {EXP[:12]} | {KEY}")
def parse_nom():
 rows=[]
 for y in range(2009,2023):
  p=DL/"raw"/"treasury"/"nominal_yield_curve"/f"nominal_yield_curve_{y}.xml"
  root=ET.parse(p).getroot()
  for entry in root.iter():
   vals={}
   for x in entry.iter():
    tag=x.tag.split("}")[-1];txt=(x.text or "").strip()
    if txt and (tag.startswith("NEW_DATE") or tag.startswith("BC_") or tag=="NEW_DATE"):vals[tag]=txt
   if vals:rows.append(vals)
 d=pd.DataFrame(rows).drop_duplicates().reset_index(drop=True);dc=next(c for c in d if "DATE" in c);dates=pd.to_datetime(d[dc],errors="coerce");keep=dates.notna().to_numpy();d=d.loc[keep].copy();dates=dates.loc[keep];d.index=pd.DatetimeIndex(dates.to_numpy()).tz_localize(None).normalize();d=d.sort_index()
 cands=[]
 for c in d:
  m=re.search(r"BC_(\d+)YEAR",c)
  if m and int(m.group(1))==30:cands.append(c)
 if not cands:raise RuntimeError("30Y nominal column not found")
 c=cands[0];s=pd.Series(pd.to_numeric(d[c],errors="coerce").to_numpy(),index=d.index).groupby(level=0).last().sort_index()
 return s,c
s0,col=parse_nom();assert s0.loc[:"2022-12-31"].notna().sum()>1000
prog(2,14,f"NOM30Y provenance reconstructed | column={col} | finite={s0.notna().sum()}")
z=[]
for y in range(2018,2023):
 p=RAW/"NSXUSD"/"M1"/f"NSXUSD_M1_{y}.parquet";d=pd.read_parquet(p);tc=next(c for c in d if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc]);z.append(d[["close"]])
px=pd.concat(z).sort_index()["close"].resample("1D").last().dropna();px.index=pd.DatetimeIndex(px.index).tz_localize(None).normalize()
raw=s0.rolling(252,min_periods=126).rank(pct=True)
def pnl(lag=0,thr=.10):
 x=raw.shift(1+lag);q=pd.DataFrame({"x":x}).dropna().join(px.rename("px"),how="inner").dropna();q=q[(q.index.year>=2018)&(q.index.year<=2022)];mask=q.x<=thr;ret=np.log(q.px.shift(-5)/q.px)*1e4;return ret[mask].dropna()
p=pnl();n=len(p);gross=float(p.mean());prog(3,14,f"baseline reconstructed | n={n} gross={gross:.3f}bp")
def trim(frac):
 k=max(1,int(np.floor(n*frac)));return float(p.sort_values().iloc[:-k].mean())
trims={str(x):trim(x) for x in [.01,.02,.05]}
days=p.groupby(p.index.normalize()).sum().sort_values();rm5=float(days.iloc[:-5].mean());rm10=float(days.iloc[:-10].mean())
months=p.groupby(p.index.to_period("M")).mean().sort_values();rmmonth=float(p[~p.index.to_period("M").isin([months.index[-1]])].mean())
prog(4,14,f"concentration | trim2={trims['0.02']:.2f} trim5={trims['0.05']:.2f} rm10days={rm10:.2f} rm_best_month={rmmonth:.2f}")
years=sorted(p.index.year.unique());loo={}
for y in years:loo[str(y)]=float(p[p.index.year!=y].mean())
prog(5,14,f"leave-one-year-out min={min(loo.values()):.2f}bp")
lags={str(k):float(pnl(k).mean()) for k in [1,2,3]}
neigh={str(x):float(pnl(0,x).mean()) for x in [.05,.075,.10,.125,.15]}
prog(6,14,f"lags + thresholds | lag3={lags['3']:.2f} | threshold min={min(neigh.values()):.2f}")
rng=np.random.default_rng(520052)
boots=np.array([rng.choice(p.to_numpy(),n,replace=True).mean() for _ in range(5000)]);event_ci=[float(np.quantile(boots,.025)),float(np.quantile(boots,.975))]
# year-block bootstrap: resample complete years and concatenate their event returns
byy={y:p[p.index.year==y].to_numpy() for y in years};yb=[]
for _ in range(5000):
 ys=rng.choice(years,len(years),replace=True);arr=np.concatenate([byy[int(y)] for y in ys]);yb.append(arr.mean())
year_ci=[float(np.quantile(yb,.025)),float(np.quantile(yb,.975))]
prog(7,14,f"bootstrap | event lo={event_ci[0]:.2f} | year-block lo={year_ci[0]:.2f}")
non=float(p.iloc[::5].mean());costs={str(c):gross-c for c in [5,10,20,30]}
# split validation window without selecting on it: descriptive forensic only
sub={"2018_2020":float(p[p.index.year<=2020].mean()),"2021_2022":float(p[p.index.year>=2021].mean())}
prog(8,14,f"nonoverlap={non:.2f} | after30bp={costs['30']:.2f} | halves={sub}")
# Final gate frozen in code before result inspection: all tail/concentration, temporal, perturbation and uncertainty diagnostics positive.
passed=bool(trims["0.02"]>0 and trims["0.05"]>0 and rm5>0 and rm10>0 and rmmonth>0 and min(loo.values())>0 and non>0 and min(lags.values())>0 and min(neigh.values())>0 and event_ci[0]>0 and year_ci[0]>0 and min(sub.values())>0 and costs["30"]>0)
res={"key":KEY,"n":n,"gross_bp":gross,"trim1_bp":trims["0.01"],"trim2_bp":trims["0.02"],"trim5_bp":trims["0.05"],"remove_best5days_bp":rm5,"remove_best10days_bp":rm10,"remove_best_month_bp":rmmonth,"leave_one_year_out_bp":loo,"extra_lags_bp":lags,"neighbor_thresholds_bp":neigh,"nonoverlap_h5_bp":non,"event_bootstrap_ci95_bp":event_ci,"year_block_bootstrap_ci95_bp":year_ci,"diagnostic_costs_bp":costs,"subperiod_bp":sub,"final_preoos_pass":passed}
(O/"FINAL_FORENSIC.json").write_text(json.dumps(res,indent=2));fsha=hashlib.sha256((O/"FINAL_FORENSIC.json").read_bytes()).hexdigest()
prog(9,14,f"FINAL PRE-OOS {'PASS' if passed else 'FAIL'} | forensic sha {fsha[:12]}")
receipt={"run_id":rid,"status":"COMPLETE_FINAL_PREOOS_FORENSIC","source_v51":src.name,"verified_v51_survivor_sha256":EXP,"candidate":KEY,"final_preoos_pass":passed,"forensic_sha256":fsha,"retuning":False,"rescue_search":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(10,14,"receipt written; no retuning/rescue")
prog(11,14,"2023-2025 remains sealed")
prog(12,14,"2026 remains protected")
prog(13,14,"human decision required before locked OOS")
prog(14,14,"STOP")
print("\n=== V52 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== FINAL FORENSIC ===");print(json.dumps(res,indent=2));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V52 compile failed"}
Write-Host "=== GEF V52 - FINAL PRE-OOS FORENSIC ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V52 failed"}
