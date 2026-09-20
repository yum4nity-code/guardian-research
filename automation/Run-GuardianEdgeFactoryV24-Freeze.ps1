param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v24_freeze.py"
$code=@'
from pathlib import Path
import pandas as pd,json,hashlib,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v23"; OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v24";OUT.mkdir(parents=True,exist_ok=True)
runs=sorted([p for p in B.glob("GEF23-*") if (p/"PREVALIDATION_CANDIDATES.csv").exists()])
if not runs: raise RuntimeError("No V23 candidates")
src=runs[-1];p=src/"PREVALIDATION_CANDIDATES.csv";df=pd.read_csv(p)
expected={("XAGUSD","XAUUSD","divret_24b",120,.99),("SPXUSD","UDXUSD","drvret_24b",240,.99),("XAGUSD","XAUUSD","divret_6b",240,.99),("XAGUSD","XAUUSD","divret_3b",240,.975)}
got={(r["target"],r["driver"],r["feature"],int(r["horizon_min"]),float(r["tail"])) for _,r in df.iterrows()}
if got!=expected:raise RuntimeError(f"Unexpected V23 set: {got}")
rid="GEF24-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");o=OUT/rid;o.mkdir()
print("[GEF24] 1/4 25% verify V23 survivors")
# Preserve exact identity AND discovery-frozen execution parameters needed for validation.
cols=["target","driver","feature","horizon_min","tail","direction","threshold_abs","n","gross_bp","delay5","delay15","trim_best1pct","remove_best5days","nonoverlap_n","nonoverlap_bp","posyears","null_p"]
missing=[c for c in cols if c not in df.columns]
if missing:raise RuntimeError(f"Missing frozen columns: {missing}")
f=df[cols].copy();fp=o/"FROZEN_VALIDATION_CANDIDATES.csv";f.to_csv(fp,index=False)
print("[GEF24] 2/4 50% write exact manifest")
sha=hashlib.sha256(fp.read_bytes()).hexdigest()
receipt={"run_id":rid,"status":"FROZEN_AWAITING_HUMAN_REVIEW","source_v23":src.name,"manifest_sha256":sha,"candidate_count":len(f),"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"instruction":"STOP. Candidate identity, direction, discovery threshold, horizon and tail are immutable before validation. No 2018+ access in V24."}
(o/"FREEZE_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
print("[GEF24] 3/4 75% hash",sha)
print("[GEF24] 4/4 100% STOP - 2018+ UNTOUCHED")
print("\n=== V24 FREEZE RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== FROZEN ===");print(f.to_string(index=False));print("\nRUN:",o)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V24 compile failed"}
Write-Host "=== GEF V24 - IMMUTABLE PRE-VALIDATION FREEZE ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V24 freeze failed"}
