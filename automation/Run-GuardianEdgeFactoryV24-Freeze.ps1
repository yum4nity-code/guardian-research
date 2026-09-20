param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v24_freeze.py"
$code=@'
from pathlib import Path
import pandas as pd,json,hashlib
from datetime import datetime,timezone

ROOT=Path(r"D:\MT5_Backtests")
V23B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v23"
V22B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v22"
OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v24"
OUT.mkdir(parents=True,exist_ok=True)

v23runs=sorted([p for p in V23B.glob("GEF23-*") if (p/"PREVALIDATION_CANDIDATES.csv").exists()])
v22runs=sorted([p for p in V22B.glob("GEF22-*") if (p/"ALIGNMENT_CLEARED_CANDIDATES.csv").exists()])
if not v23runs: raise RuntimeError("No V23 candidates")
if not v22runs: raise RuntimeError("No V22 candidate source")

v23=v23runs[-1]
v22=v22runs[-1]
surv=pd.read_csv(v23/"PREVALIDATION_CANDIDATES.csv")
src=pd.read_csv(v22/"ALIGNMENT_CLEARED_CANDIDATES.csv")

keys=["target","driver","feature","horizon_min","tail"]
expected={
 ("XAGUSD","XAUUSD","divret_24b",120,.99),
 ("SPXUSD","UDXUSD","drvret_24b",240,.99),
 ("XAGUSD","XAUUSD","divret_6b",240,.99),
 ("XAGUSD","XAUUSD","divret_3b",240,.975),
}
got={(r["target"],r["driver"],r["feature"],int(r["horizon_min"]),float(r["tail"])) for _,r in surv.iterrows()}
if got!=expected: raise RuntimeError(f"Unexpected V23 set: {got}")

rid="GEF24-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
o=OUT/rid
o.mkdir()

print("[GEF24] 1/5 20% verify V23 survivor identities")

# V23 intentionally did not copy direction/threshold_abs into its output.
# Recover these immutable discovery-frozen execution parameters from V22,
# which carried them forward unchanged from V21/V20.
needed=keys+["direction","threshold_abs"]
missing=[c for c in needed if c not in src.columns]
if missing: raise RuntimeError(f"V22 source missing immutable fields: {missing}")

imm=src[needed].drop_duplicates()
if imm.duplicated(keys).any():
 raise RuntimeError("Ambiguous immutable parameters in V22 source")

print("[GEF24] 2/5 40% recover direction + threshold from V22 provenance")

f=surv.merge(imm,on=keys,how="left",validate="one_to_one")
if f[["direction","threshold_abs"]].isna().any().any():
 bad=f[f[["direction","threshold_abs"]].isna().any(axis=1)][keys]
 raise RuntimeError(f"Could not recover immutable fields for: {bad.to_dict('records')}")

# Keep exact execution identity first, then V23 evidence.
front=["target","driver","feature","horizon_min","tail","direction","threshold_abs"]
rest=[c for c in f.columns if c not in front]
f=f[front+rest]

fp=o/"FROZEN_VALIDATION_CANDIDATES.csv"
f.to_csv(fp,index=False)
print("[GEF24] 3/5 60% write immutable manifest")

sha=hashlib.sha256(fp.read_bytes()).hexdigest()
receipt={
 "run_id":rid,
 "status":"FROZEN_AWAITING_HUMAN_REVIEW",
 "source_v23":v23.name,
 "immutable_parameter_source_v22":v22.name,
 "manifest_sha256":sha,
 "candidate_count":len(f),
 "validation_2018_2022_accessed":False,
 "locked_oos_2023_2025_accessed":False,
 "protected_2026_accessed":False,
 "provenance_note":"direction and threshold_abs recovered from V22 because V23 robustness output omitted those columns; no recomputation or retuning performed.",
 "instruction":"STOP. Candidate identity, direction, discovery threshold, horizon and tail are immutable before validation. No 2018+ access in V24."
}
(o/"FREEZE_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
print("[GEF24] 4/5 80% hash",sha)
print("[GEF24] 5/5 100% STOP - 2018+ UNTOUCHED")
print("\n=== V24 FREEZE RECEIPT ===")
print(json.dumps(receipt,indent=2))
print("\n=== FROZEN ===")
print(f.to_string(index=False))
print("\nRUN:",o)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V24 compile failed"}
Write-Host "=== GEF V24 - IMMUTABLE PRE-VALIDATION FREEZE ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V24 freeze failed"}
