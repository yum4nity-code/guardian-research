param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v30_xag_replication.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");RAW=ROOT/"DataLake"/"raw"/"histdata";V29=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v29";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v30";OUT.mkdir(parents=True,exist_ok=True)
EXPECTED="4ceba06332e5abbba62ce98e1df02582b2d69d40ca106d612932c9a75be9b163";started=time.time();rid="GEF30-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-started;eta=e/i*(n-i) if i else 0;print(f"[GEF30] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
runs=sorted([p for p in V29.glob("GEF29-*") if (p/"FROZEN_REPLICATION_CANDIDATES.csv").exists()]);fp=runs[-1]/"FROZEN_REPLICATION_CANDIDATES.csv"
got=hashlib.sha256(fp.read_bytes()).hexdigest()
if got!=EXPECTED:raise RuntimeError(f"V29 freeze hash mismatch {got}")
F=pd.read_csv(fp);prog(1,15,"V29 freeze hash verified")
z=[]
for y in range(2014,2018):
 p=RAW/"XAGUSD"/"M1"/f"XAGUSD_M1_{y}.parquet"
 if not p.exists():raise RuntimeError(f"missing {p}")
 d=pd.read_parquet(p);tc=next(c for c in d if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc]);z.append(d[["close"]].sort_index().resample("5min",label="right",closed="left").last().dropna())
a=pd.concat(z).sort_index().close;prog(2,15,"loaded replication 2014-2017 ONLY")
rows=[]
for j,(_,r) in enumerate(F.iterrows(),start=1):
 w=int(r["window_bars"]);h=int(r["horizon_min"]);thr=float(r["threshold_abs"])
 x=np.log(a/a.shift(w));y=np.log(a.shift(-h//5)/a)*1e4;q=pd.concat([x.rename("x"),y.rename("y")],axis=1).dropna();sel=q[q.x.abs()>=thr];p=-np.sign(sel.x)*sel.y;yrs=p.groupby(p.index.year).mean()
 row={"window_bars":w,"window_min":int(r["window_min"]),"horizon_min":h,"tail":float(r["tail"]),"threshold_abs":thr,"direction":-1,"feature":"XAG_ret","n":len(p),"gross_bp":float(p.mean()),"hit":float((p>0).mean()),"posyears":float((yrs>0).mean()),"yearly":json.dumps({str(int(k)):float(v) for k,v in yrs.items()})}
 row["replication_pass"]=bool(len(p)>=300 and row["gross_bp"]>0 and row["posyears"]>=.75)
 rows.append(row);prog(j+2,15,f"{j}/12 w={w} H={h} P{float(r['tail'])*100:g} gross={row['gross_bp']:.3f} {'PASS' if row['replication_pass'] else 'FAIL'}")
R=pd.DataFrame(rows);R.to_csv(O/"REPLICATION_RESULTS.csv",index=False);P=R[R.replication_pass].copy();P.to_csv(O/"REPLICATION_SURVIVORS.csv",index=False)
receipt={"run_id":rid,"status":"COMPLETE","source_v29":runs[-1].name,"freeze_sha256_verified":got,"replication_period":"2014-2017 only","candidate_count":len(F),"pass_count":len(P),"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"selection_or_retuning_on_replication":False,"errors":[],"instruction":"STOP. Robustness gate before any validation access."};(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(15,15,"STOP - 2018+ untouched");print("\n=== V30 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== REPLICATION RESULTS ===");print(R.to_string(index=False));print("\n=== SURVIVORS ===");print(P.to_string(index=False));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V30 compile failed"}
Write-Host "=== GEF V30 - XAG CLEAN REPLICATION ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V30 failed"}
