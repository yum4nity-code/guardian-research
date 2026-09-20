param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v35_freeze.py"
$code=@'
from pathlib import Path
import pandas as pd,json,hashlib,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); V34=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v34"; OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v35"; OUT.mkdir(parents=True,exist_ok=True)
t=time.time(); rid="GEF35-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"); O=OUT/rid; O.mkdir()
def p(i,n,msg):
 e=time.time()-t; eta=e/i*(n-i) if i else 0; print(f"[GEF35] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
runs=sorted([x for x in V34.glob("GEF34-*") if (x/"ROBUST_SURVIVORS.csv").exists() and (x/"RUN_RECEIPT.json").exists()])
if not runs: raise RuntimeError("No V34 result")
src=runs[-1]; rec=json.loads((src/"RUN_RECEIPT.json").read_text()); p(1,4,f"source {src.name}")
if rec.get("status")!="COMPLETE" or rec.get("period")!="2014-2017 only" or rec.get("robust_pass_count")!=1: raise RuntimeError("V34 receipt mismatch")
F=pd.read_csv(src/"ROBUST_SURVIVORS.csv")
if len(F)!=1: raise RuntimeError(f"Expected exactly one survivor, got {len(F)}")
r=F.iloc[0]
identity={"market":str(r["market"]),"regime":str(r["regime"]),"horizon_min":int(r["horizon_min"]),"mode":str(r["mode"]),
"bar_minutes":15,"rv_window_bars":16,"rv_slow_median_bars":320,"normal_regime":"0.75 < RV16/past_median_RV < 1.5",
"shock":"abs M15 log return >= past-only rolling 20-day 95th percentile; threshold shifted one M15 bar",
"signal_direction":"reversal of shock sign","entry":"causal M15 right-edge close at signal availability","target":"log return over next 240 minutes"}
p(2,4,"verified sole robust survivor identity")
manifest={"lineage":"volatility-regime conditional shock continuation/reversal","source_v34":src.name,
"source_v34_survivors_sha256":hashlib.sha256((src/"ROBUST_SURVIVORS.csv").read_bytes()).hexdigest(),
"candidate":identity,"selection_periods_used":"discovery 2010-2013; replication/robustness 2014-2017",
"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,
"frozen_at_utc":datetime.now(timezone.utc).isoformat(),"next_gate":"independent 2018-2022 validation; no retuning"}
txt=json.dumps(manifest,indent=2,sort_keys=True); (O/"FROZEN_VALIDATION_MANIFEST.json").write_text(txt); sha=hashlib.sha256((O/"FROZEN_VALIDATION_MANIFEST.json").read_bytes()).hexdigest()
receipt={"run_id":rid,"status":"FROZEN_AWAITING_VALIDATION","source_v34":src.name,"candidate_count":1,"manifest_sha256":sha,
"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2)); p(3,4,f"manifest frozen sha256={sha}")
p(4,4,"STOP - no market data opened")
print("\n=== V35 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== FROZEN CANDIDATE ===");print(json.dumps(identity,indent=2));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V35 compile failed"}
Write-Host "=== GEF V35 - IMMUTABLE PRE-VALIDATION FREEZE ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V35 failed"}
