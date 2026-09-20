param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v34_regime_robustness.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib
from datetime import datetime,timezone

ROOT=Path(r"D:\MT5_Backtests")
RAW=ROOT/"DataLake"/"raw"/"histdata"
V33=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v33"
OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v34"; OUT.mkdir(parents=True,exist_ok=True)
started=time.time(); rid="GEF34-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"); O=OUT/rid; O.mkdir()
NNULL=2000

def prog(i,n,msg):
 e=time.time()-started; eta=e/i*(n-i) if i else 0
 print(f"[GEF34] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)

runs=sorted([p for p in V33.glob("GEF33-*") if (p/"REPLICATION_SURVIVORS.csv").exists() and (p/"RUN_RECEIPT.json").exists()])
if not runs: raise RuntimeError("No completed V33 run found")
src=runs[-1]
rec=json.loads((src/"RUN_RECEIPT.json").read_text())
if rec.get("status")!="COMPLETE" or rec.get("replication_period")!="2014-2017 only": raise RuntimeError("V33 receipt mismatch")
F=pd.read_csv(src/"REPLICATION_SURVIVORS.csv")
if len(F)!=9: raise RuntimeError(f"Expected 9 V33 survivors, got {len(F)}")
src_hash=hashlib.sha256((src/"REPLICATION_SURVIVORS.csv").read_bytes()).hexdigest()
prog(1,11,f"loaded immutable V33 survivors n={len(F)} sha256={src_hash[:12]}")

cache={}
def load(m):
 if m in cache:return cache[m]
 z=[]
 for y in range(2014,2018):
  p=RAW/m/"M1"/f"{m}_M1_{y}.parquet"
  if not p.exists(): raise RuntimeError(f"Missing required replication file {p}")
  d=pd.read_parquet(p); tc=next(c for c in d if c.lower() in ("datetime","time","timestamp"))
  d.index=pd.to_datetime(d[tc]); z.append(d[["close"]].sort_index().resample("15min",label="right",closed="left").last().dropna())
 a=pd.concat(z).sort_index().close
 cache[m]=a; return a

def pnl_series(r,delay_min=0):
 m=r["market"]; reg=r["regime"]; h=int(r["horizon_min"]); mode=r["mode"]; a=load(m)
 ret=np.log(a/a.shift(1)); rv=ret.rolling(16,min_periods=16).std(); slow=rv.rolling(20*16,min_periods=80).median(); ratio=rv/slow
 mask={"compressed":ratio<=.75,"normal":(ratio>.75)&(ratio<1.5),"expanded":ratio>=1.5}[reg]
 shock=ret.abs()>=ret.abs().rolling(20*96,min_periods=480).quantile(.95).shift(1)
 ds=delay_min//15
 entry=a.shift(-ds) if ds else a
 future=a.shift(-(ds+h//15))
 y=np.log(future/entry)*1e4
 q=pd.concat([ret.rename("r"),y.rename("y"),mask.rename("reg"),shock.rename("shock")],axis=1).dropna()
 q=q[q.reg&q.shock]
 direction=1 if mode=="continuation" else -1
 return direction*np.sign(q.r)*q.y

def remove_best_days(p,k=5):
 if p.empty:return np.nan
 daymean=p.groupby(p.index.normalize()).sum().sort_values(ascending=False)
 bad=set(daymean.head(k).index)
 return float(p[~p.index.normalize().isin(bad)].mean())

def nonoverlap(p,h):
 if p.empty:return p
 chosen=[]; last=None
 for t,v in p.items():
  if last is None or (t-last).total_seconds()>=h*60:
   chosen.append((t,v)); last=t
 return pd.Series([v for _,v in chosen],index=[t for t,_ in chosen],dtype=float)

def null_p(p,seed):
 if p.empty:return np.nan
 days=p.index.normalize(); uniq=pd.Index(days.unique()); obs=abs(float(p.mean()))
 arr=p.to_numpy(); inv=pd.Categorical(days,categories=uniq).codes
 rng=np.random.default_rng(seed); ge=0
 for _ in range(NNULL):
  signs=rng.choice(np.array([-1.0,1.0]),size=len(uniq))
  if abs(float(np.mean(arr*signs[inv])))>=obs: ge+=1
 return (ge+1)/(NNULL+1)

rows=[]
for j,(_,r) in enumerate(F.iterrows(),1):
 p=pnl_series(r,0); p5=pnl_series(r,5); p15=pnl_series(r,15)
 # M15 bars: +5/+15 cannot both be represented exactly from M15 closes.
 # +5 uses the next available M15 close, conservatively identical to +15 on this dataset.
 if 5%15!=0: p5=p15.copy()
 trim=p.drop(p.nlargest(max(1,int(np.ceil(len(p)*.01)))).index)
 no=nonoverlap(p,int(r["horizon_min"])); yrs=p.groupby(p.index.year).mean()
 seed=int(hashlib.sha256(f"{r['market']}|{r['regime']}|{r['horizon_min']}|{r['mode']}".encode()).hexdigest()[:8],16)
 row={"market":r["market"],"regime":r["regime"],"horizon_min":int(r["horizon_min"]),"mode":r["mode"],
      "n":len(p),"gross_bp":float(p.mean()),"delay5_bp":float(p5.mean()),"delay15_bp":float(p15.mean()),
      "trim_best1pct_bp":float(trim.mean()),"remove_best5days_bp":remove_best_days(p,5),
      "nonoverlap_n":len(no),"nonoverlap_bp":float(no.mean()),"posyears":float((yrs>0).mean()),
      "null_p":null_p(p,seed),"yearly":json.dumps({str(int(k)):float(v) for k,v in yrs.items()})}
 row["robust_pass"]=bool(row["n"]>=300 and row["gross_bp"]>0 and row["delay5_bp"]>0 and row["delay15_bp"]>0 and row["trim_best1pct_bp"]>0 and row["remove_best5days_bp"]>0 and row["nonoverlap_bp"]>0 and len(yrs)==4 and row["posyears"]>=.75 and row["null_p"]<=.05)
 rows.append(row)
 prog(j+1,11,f"{j}/9 {row['market']} {row['regime']} H{row['horizon_min']} {row['mode']} | gross {row['gross_bp']:.3f} trim1 {row['trim_best1pct_bp']:.3f} no {row['nonoverlap_bp']:.3f} p {row['null_p']:.4f} | {'PASS' if row['robust_pass'] else 'FAIL'}")

R=pd.DataFrame(rows); R.to_csv(O/"ROBUSTNESS_RESULTS.csv",index=False)
P=R[R.robust_pass].copy(); P.to_csv(O/"ROBUST_SURVIVORS.csv",index=False)
freeze_hash=hashlib.sha256((O/"ROBUST_SURVIVORS.csv").read_bytes()).hexdigest()
receipt={"run_id":rid,"status":"COMPLETE","source_v33":src.name,"source_survivors_sha256":src_hash,
"period":"2014-2017 only","candidate_count":len(F),"robust_pass_count":len(P),"null_reps_per_candidate":NNULL,
"gate":{"n_min":300,"gross_bp":">0","delay_5m":">0 (conservative next-M15 proxy; see caveat)","delay_15m":">0","trim_best_1pct":">0","remove_best_5_days":">0","nonoverlap":">0","positive_year_fraction":">=0.75 with all 4 years","daily_block_signflip_p":"<=0.05"},
"caveat_delay5":"Source is M15. Exact +5m execution is unavailable in this runner; +5m is conservatively proxied by the next M15 close and therefore equals the +15m test. Do not claim exact +5m robustness.",
"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,
"survivor_freeze_sha256":freeze_hash,"errors":[],"instruction":"STOP. If survivors exist, freeze/review before independent 2018-2022 validation."}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(11,11,f"STOP - {len(P)}/9 robust; 2018+ untouched; freeze {freeze_hash[:12]}")
print("\n=== V34 RECEIPT ===");print(json.dumps(receipt,indent=2))
print("\n=== ROBUSTNESS RESULTS ===");print(R.to_string(index=False))
print("\n=== ROBUST SURVIVORS ===");print(P.to_string(index=False) if len(P) else "NONE")
print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V34 compile failed"}
Write-Host "=== GEF V34 - PRE-VALIDATION ROBUSTNESS ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V34 failed"}
