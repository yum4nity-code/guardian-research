param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v33_regime_replication.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");RAW=ROOT/"DataLake"/"raw"/"histdata";V32=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v32";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v33";OUT.mkdir(parents=True,exist_ok=True)
started=time.time();rid="GEF33-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-started;eta=e/i*(n-i) if i else 0;print(f"[GEF33] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
runs=sorted([p for p in V32.glob("GEF32-*") if (p/"FROZEN_REPLICATION_CANDIDATES.csv").exists()]);F=pd.read_csv(runs[-1]/"FROZEN_REPLICATION_CANDIDATES.csv")
if len(F)!=16:raise RuntimeError(f"Expected 16 frozen V32 candidates, got {len(F)}")
prog(1,18,"loaded 16 V32 frozen candidates")
cache={}
def load(m):
 if m in cache:return cache[m]
 z=[]
 for y in range(2014,2018):
  p=RAW/m/"M1"/f"{m}_M1_{y}.parquet"
  if not p.exists():continue
  d=pd.read_parquet(p);tc=next(c for c in d if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc]);z.append(d[["close"]].sort_index().resample("15min",label="right",closed="left").last().dropna())
 if not z:raise RuntimeError(f"No 2014-2017 data for {m}")
 cache[m]=pd.concat(z).sort_index().close;return cache[m]
rows=[]
for j,(_,r) in enumerate(F.iterrows(),1):
 m=r["market"];reg=r["regime"];h=int(r["horizon_min"]);mode=r["mode"];a=load(m)
 ret=np.log(a/a.shift(1));rv=ret.rolling(16,min_periods=16).std();rvslow=rv.rolling(20*16,min_periods=80).median();ratio=rv/rvslow
 mask={"compressed":ratio<=.75,"normal":(ratio>.75)&(ratio<1.5),"expanded":ratio>=1.5}[reg]
 shock=ret.abs()>=ret.abs().rolling(20*96,min_periods=480).quantile(.95).shift(1)
 y=np.log(a.shift(-h//15)/a)*1e4;q=pd.concat([ret.rename("r"),y.rename("y"),mask.rename("reg"),shock.rename("shock")],axis=1).dropna();q=q[q.reg&q.shock]
 direction=1 if mode=="continuation" else -1;p=direction*np.sign(q.r)*q.y;yrs=p.groupby(p.index.year).mean()
 row={"market":m,"regime":reg,"horizon_min":h,"mode":mode,"n":len(p),"gross_bp":float(p.mean()),"hit":float((p>0).mean()),"posyears":float((yrs>0).mean()),"yearly":json.dumps({str(int(k)):float(v) for k,v in yrs.items()})}
 row["replication_pass"]=bool(len(p)>=300 and row["gross_bp"]>0 and len(yrs)==4 and row["posyears"]>=.75)
 rows.append(row);prog(j+1,18,f"{j}/16 {m} {reg} H{h} {mode} gross={row['gross_bp']:.3f} {'PASS' if row['replication_pass'] else 'FAIL'}")
R=pd.DataFrame(rows);R.to_csv(O/"REPLICATION_RESULTS.csv",index=False);P=R[R.replication_pass].copy();P.to_csv(O/"REPLICATION_SURVIVORS.csv",index=False)
prog(18,18,f"STOP - {len(P)}/16 survive; 2018+ untouched")
receipt={"run_id":rid,"status":"COMPLETE","source_v32":runs[-1].name,"replication_period":"2014-2017 only","candidate_count":16,"pass_count":len(P),"all_four_replication_years_required":True,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"selection_or_retuning_on_replication":False,"errors":[],"instruction":"STOP. Robustness before validation."};(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
print("\n=== V33 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== REPLICATION RESULTS ===");print(R.to_string(index=False));print("\n=== SURVIVORS ===");print(P.to_string(index=False));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V33 compile failed"}
Write-Host "=== GEF V33 - REGIME/SHOCK REPLICATION ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V33 failed"}
