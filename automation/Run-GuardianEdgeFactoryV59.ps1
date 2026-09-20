param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v59_cftc_freeze.py"
$code=@'
from pathlib import Path
import pandas as pd,json,hashlib,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");SRC=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v58"/"GEF58-20260920-184149";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v59";OUT.mkdir(parents=True,exist_ok=True)
EXPECTED="e3d21714332ed160ac2a5a591159aff5d00bc43f2d55034e79724624bc98ad9b"
t=time.time();rid="GEF59-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def p(i,n,msg):
 e=time.time()-t;print(f"[GEF59] {i}/{n} {100*i/n:.0f}% | elapsed {e:.1f}s | {msg}",flush=True)
src=SRC/"V59_SURVIVORS.csv";sha=hashlib.sha256(src.read_bytes()).hexdigest()
if sha!=EXPECTED:raise RuntimeError("V58 survivor SHA mismatch")
p(1,5,f"verified V58 survivor sha={sha[:12]}")
s=pd.read_csv(src)
spec=pd.read_csv(ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v56c"/"GEF56C-20260920-183439"/"V57_FROZEN_INPUT.csv")
f=s[["key","market"]].merge(spec,on=["key","market"],how="left",validate="one_to_one")
if f.isna().any().any():raise RuntimeError("Incomplete frozen specification")
# Freeze exact specifications; validation gate is declared now, before 2018-2022 is read.
f.to_csv(O/"V60_IMMUTABLE_CANDIDATES.csv",index=False)
fsha=hashlib.sha256((O/"V60_IMMUTABLE_CANDIDATES.csv").read_bytes()).hexdigest();p(2,5,f"candidates frozen={len(f)} sha={fsha[:12]}")
gate={"window":"2018-2022","no_retuning":True,"candidate_spec_sha256":fsha,"requirements":{"n_min":40,"gross_bp_gt":0,"hit_rate_min":0.52,"positive_year_fraction_min":0.60,"trim_best_1pct_bp_gt":0,"remove_best_5_days_bp_gt":0,"true_nonoverlap_bp_gt":0},"stop_after_validation":True}
(O/"V60_VALIDATION_GATE.json").write_text(json.dumps(gate,indent=2));gsha=hashlib.sha256((O/"V60_VALIDATION_GATE.json").read_bytes()).hexdigest();p(3,5,f"validation gate frozen sha={gsha[:12]}")
receipt={"run_id":rid,"status":"COMPLETE_CFTC_IMMUTABLE_PREVALIDATION_FREEZE","source_v58_survivor_sha256":sha,"candidate_count":len(f),"candidate_sha256":fsha,"validation_gate_sha256":gsha,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"retuning":False}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));p(4,5,"receipt written; 2018+ untouched");p(5,5,"STOP before independent validation")
print("\n=== V59 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== IMMUTABLE CANDIDATES ===");print(f.to_string(index=False));print("\n=== V60 GATE ===");print(json.dumps(gate,indent=2));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V59 compile failed"}
Write-Host "=== GEF V59 - CFTC IMMUTABLE PRE-VALIDATION FREEZE ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V59 failed"}
