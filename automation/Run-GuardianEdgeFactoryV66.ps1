param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v66_intraday_calendar_freeze.py"
$code=@'
from pathlib import Path
import pandas as pd,json,hashlib,time
ROOT=Path(r"D:\MT5_Backtests");PREV=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v65"
runs=sorted([p for p in PREV.glob("GEF65-*") if (p/"V66_PREVALIDATION_SURVIVORS.csv").exists()])
if not runs:raise RuntimeError("No V65 survivors")
P=runs[-1];src=P/"V66_PREVALIDATION_SURVIVORS.csv";EXPECTED="c692a4dc91b3520ce8b0813c9b2a1933d666d68df6933b83e305cd399437aefa"
sha=hashlib.sha256(src.read_bytes()).hexdigest()
if sha!=EXPECTED:raise RuntimeError(f"V65 SHA mismatch: {sha}")
F=pd.read_csv(src)
# Freeze all 9 robust survivors; no ranking/retuning after V65.
keep=["market","mechanism","bucket","mode"]
spec=F[keep].copy()
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v66";rid="GEF66-"+pd.Timestamp.utcnow().strftime("%Y%m%d-%H%M%S");O=BASE/rid;O.mkdir(parents=True,exist_ok=True)
spec.to_csv(O/"V67_FROZEN_VALIDATION_CANDIDATES.csv",index=False)
fsha=hashlib.sha256((O/"V67_FROZEN_VALIDATION_CANDIDATES.csv").read_bytes()).hexdigest()
gate={"window":"2018-2022","n_min":150,"gross_bp_gt":0,"hit_gte":0.50,"positive_year_fraction_gte":0.60,"trim_best_1pct_bp_gt":0,"trim_best_2pct_bp_gt":0,"remove_best_5_events_bp_gt":0,"no_retuning":True}
(O/"V67_VALIDATION_GATE.json").write_text(json.dumps(gate,indent=2))
gsha=hashlib.sha256((O/"V67_VALIDATION_GATE.json").read_bytes()).hexdigest()
receipt={"run_id":rid,"status":"IMMUTABLE_FREEZE_COMPLETE","family":"04_INTRADAY_CALENDAR_STRUCTURE","input_sha256":sha,"candidates":len(spec),"candidate_sha256":fsha,"validation_gate_sha256":gsha,"2018_plus_accessed":False,"next":"V67_INDEPENDENT_VALIDATION_2018_2022"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
print("[GEF66] 1/3 33% | verified V65 SHA | 2018+ untouched",flush=True)
print("[GEF66] 2/3 67% | frozen candidates=9 | validation gate frozen",flush=True)
print("[GEF66] 3/3 100% | HARD STOP before validation",flush=True)
print("\n=== V66 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== FROZEN VALIDATION SPECS ===");print(spec.to_string(index=False));print("\n=== V67 GATE ===");print(json.dumps(gate,indent=2));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V66 compile failed"}
Write-Host "=== GEF V66 - IMMUTABLE PREVALIDATION FREEZE ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V66 failed"}
