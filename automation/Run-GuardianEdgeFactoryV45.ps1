param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v45_iv03_preoos_forensic.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");RAW=ROOT/"DataLake"/"raw"/"histdata";CBOE=ROOT/"DataLake"/"normalized"/"cboe_pre2023";V44=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v44";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v45";OUT.mkdir(parents=True,exist_ok=True)
EXP="772c2b2b5541223c96af312608bcc9a871efd22c5a1e1d3ddf55373cdf615702"
t=time.time();rid="GEF45-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF45] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
runs=sorted([p for p in V44.glob("GEF44-*") if (p/"VALIDATION_SURVIVORS.csv").exists()])
src=runs[-1];sf=src/"VALIDATION_SURVIVORS.csv";sha=hashlib.sha256(sf.read_bytes()).hexdigest()
if sha!=EXP:raise RuntimeError(f"V44 survivor hash mismatch {sha}")
F=pd.read_csv(sf)
if len(F)!=1 or F.iloc[0]["candidate_id"]!="IV-03":raise RuntimeError("Expected sole IV-03")
prog(1,12,f"verified sole V44 survivor IV-03 sha {sha[:12]}")
# Reconstruct frozen IV-03, <=2022 only.
d=pd.read_csv(CBOE/"VIX_History_PRE2023.csv");d["DATE"]=pd.to_datetime(d["DATE"]);v=pd.to_numeric(d["CLOSE"],errors="coerce");v.index=d["DATE"];v=v.sort_index()
x=v.rolling(252,min_periods=126).rank(pct=True).shift(1)
z=[]
for y in range(2017,2023):
 p=RAW/"NSXUSD"/"M1"/f"NSXUSD_M1_{y}.parquet";q=pd.read_parquet(p);tc=next(c for c in q if c.lower() in ("datetime","time","timestamp"));q.index=pd.to_datetime(q[tc]);z.append(q[["close"]])
px=pd.concat(z).sort_index()["close"].resample("1D").last().dropna()
q=pd.concat([x.rename("x"),px.rename("px")],axis=1,join="inner").dropna();q=q[(q.index>="2018-01-01")&(q.index<="2022-12-31")]
p=(np.log(q.px.shift(-5)/q.px)*1e4)[q.x>=.90].dropna()
prog(2,12,f"reconstructed frozen signal | n={len(p)} gross={p.mean():.2f}bp")
# Predeclared final forensic gate. Diagnostics never retune specification.
year=p.groupby(p.index.year).agg(["count","mean","median"]);year.to_csv(O/"YEAR_ATTRIBUTION.csv")
loo={int(y):float(p[p.index.year!=y].mean()) for y in sorted(p.index.year.unique())}
months=p.groupby(p.index.to_period("M")).agg(["count","mean","sum"]).sort_values("sum",ascending=False);months.to_csv(O/"MONTH_ATTRIBUTION.csv")
events=p.sort_values(ascending=False).rename("pnl_bp").to_frame();events["signal_pct"]=q.loc[events.index,"x"];events.to_csv(O/"EVENTS_SORTED.csv")
# Concentration: remove best 1/2/5/10 events and best month.
rem={}
for k in [1,2,5,10]: rem[f"remove_best_{k}_bp"]=float(p.drop(p.nlargest(k).index).mean())
best_month=months.index[0];without_best_month=p[p.index.to_period("M")!=best_month]
# Delay/info lag: 1/2/3 additional VIX observations, frozen threshold .90.
def calc(extra):
 xx=v.rolling(252,min_periods=126).rank(pct=True).shift(1+extra);qq=pd.concat([xx.rename("x"),px.rename("px")],axis=1,join="inner").dropna();qq=qq[(qq.index>="2018-01-01")&(qq.index<="2022-12-31")];return (np.log(qq.px.shift(-5)/qq.px)*1e4)[qq.x>=.90].dropna()
lags={f"extra_lag_{k}_bp":float(calc(k).mean()) for k in [1,2,3]}
prog(3,12,f"concentration | LOO min={min(loo.values()):.2f} remove10={rem['remove_best_10_bp']:.2f} best-month-out={without_best_month.mean():.2f}")
prog(4,12,f"causal lag | +1={lags['extra_lag_1_bp']:.2f} +2={lags['extra_lag_2_bp']:.2f} +3={lags['extra_lag_3_bp']:.2f}")
# Threshold neighborhood diagnostics only, no selection.
neigh={}
for th in [.85,.875,.90,.925,.95]:
 pp=(np.log(q.px.shift(-5)/q.px)*1e4)[q.x>=th].dropna();neigh[str(th)]={"n":len(pp),"mean_bp":float(pp.mean())}
pd.DataFrame([{"threshold":k,**v0} for k,v0 in neigh.items()]).to_csv(O/"THRESHOLD_NEIGHBORHOOD.csv",index=False)
prog(5,12,"threshold neighborhood 85/87.5/90/92.5/95 computed as diagnostic only")
# Non-overlap and simple execution-cost sensitivity. Costs are round-trip bp deductions, diagnostic gate requires 5bp.
chosen=[];last=None
for ts,val in p.items():
 if last is None or ts-last>=pd.Timedelta(days=5):chosen.append((ts,val));last=ts
non=pd.Series([v0 for _,v0 in chosen],index=[a for a,_ in chosen],dtype=float)
costs={f"net_{c}bp_cost":float(p.mean()-c) for c in [1,2,5,10]}
prog(6,12,f"nonoverlap n={len(non)} mean={non.mean():.2f} | net@5bp={costs['net_5bp_cost']:.2f}")
# Bootstrap CI on event-level mean + year-block bootstrap; descriptive robustness, fixed seed.
rng=np.random.default_rng(450045);arr=p.to_numpy();boots=np.array([rng.choice(arr,len(arr),replace=True).mean() for _ in range(5000)])
years=sorted(p.index.year.unique());yb=[]
for _ in range(5000):
 ys=rng.choice(years,len(years),replace=True);vals=np.concatenate([p[p.index.year==y].to_numpy() for y in ys]);yb.append(vals.mean())
ci=[float(np.quantile(boots,.025)),float(np.quantile(boots,.975))];yci=[float(np.quantile(yb,.025)),float(np.quantile(yb,.975))]
prog(7,12,f"bootstrap 95% CI {ci[0]:.2f}..{ci[1]:.2f} | year-block {yci[0]:.2f}..{yci[1]:.2f}")
# Explicit final pre-OOS gate, fixed before seeing 2023+.
checks={
"gross_positive":bool(p.mean()>0),
"all_validation_years_positive":bool((year["mean"]>0).all()),
"leave_one_year_out_positive":bool(min(loo.values())>0),
"remove_best_10_events_positive":bool(rem["remove_best_10_bp"]>0),
"remove_best_month_positive":bool(without_best_month.mean()>0),
"nonoverlap_positive":bool(non.mean()>0),
"extra_lag_1_2_3_all_positive":bool(min(lags.values())>0),
"five_bp_cost_positive":bool(costs["net_5bp_cost"]>0),
"neighbor_85_and_95_positive":bool(neigh["0.85"]["mean_bp"]>0 and neigh["0.95"]["mean_bp"]>0),
"event_bootstrap_lower95_positive":bool(ci[0]>0)
}
passed=all(checks.values())
prog(8,12,"gate | "+("PASS" if passed else "FAIL")+" | "+", ".join(k for k,v0 in checks.items() if not v0))
summary={"candidate":"IV-03","n":len(p),"gross_bp":float(p.mean()),"yearly":{str(int(k)):float(v0) for k,v0 in year["mean"].items()},"leave_one_year_out":loo,**rem,"remove_best_month":str(best_month),"remove_best_month_bp":float(without_best_month.mean()),"nonoverlap_n":len(non),"nonoverlap_bp":float(non.mean()),**lags,"threshold_neighborhood":neigh,"cost_sensitivity":costs,"event_bootstrap_95":ci,"year_block_bootstrap_95":yci,"gate_checks":checks,"final_preoos_pass":passed}
(O/"FINAL_PREOOS_FORENSIC.json").write_text(json.dumps(summary,indent=2))
ssha=hashlib.sha256((O/"FINAL_PREOOS_FORENSIC.json").read_bytes()).hexdigest()
receipt={"run_id":rid,"status":"COMPLETE_STOP_BEFORE_LOCKED_OOS","source_v44":src.name,"verified_survivor_sha256":sha,"candidate":"IV-03","period":"2018-2022 forensic only; 2017 warmup","final_preoos_pass":passed,"forensic_sha256":ssha,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"retuning":False,"instruction":"If PASS: create immutable OOS gate, then require human approval before opening 2023-2025. If FAIL: close lineage without OOS."}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(9,12,f"forensic sha {ssha[:12]}")
prog(10,12,f"2019 attribution: n={int(year.loc[2019,'count'])} mean={year.loc[2019,'mean']:.2f} median={year.loc[2019,'median']:.2f}")
prog(11,12,"assertions: no retuning | 2023-2025 untouched | 2026 untouched")
prog(12,12,"STOP - "+("READY TO FREEZE OOS GATE" if passed else "CLOSE LINEAGE"))
print("\n=== V45 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== FORENSIC SUMMARY ===");print(json.dumps(summary,indent=2));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V45 compile failed"}
Write-Host "=== GEF V45 - IV-03 FINAL PRE-OOS FORENSIC ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V45 failed"}
