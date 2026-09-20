param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v17_freeze.py"
$code=@'
from pathlib import Path
import pandas as pd,json,hashlib,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v16"; OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v17"
OUT.mkdir(parents=True,exist_ok=True); started=time.time()
runs=sorted([p for p in B.glob("GEF16-*") if (p/"VALIDATION_ELIGIBLE.csv").exists()])
if not runs: raise RuntimeError("No completed V16")
src=runs[-1]; p=src/"VALIDATION_ELIGIBLE.csv"; df=pd.read_csv(p)
expected={("UDXUSD","ret_24b",240,.99),("XAGUSD","zret_12b",240,.975),("WTIUSD","ret_48b",60,.99)}
got={(r.market,r.feature,int(r.horizon_min),float(r.tail)) for _,r in df.iterrows()}
if got!=expected: raise RuntimeError(f"Freeze mismatch: {got}")
rid="GEF17-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");o=OUT/rid;o.mkdir()
print("[GEF17] 1/4 25% verify V16 survivors")
# Freeze exactly the candidate identity plus V16 evidence; no 2018+ reads.
cols=["market","feature","horizon_min","tail","rep_gross","rep_n","trim_best1pct","remove_best5days","null_p","delays","neighbors"]
f=df[cols].copy();f.to_csv(o/"FROZEN_VALIDATION_CANDIDATES.csv",index=False)
print("[GEF17] 2/4 50% write immutable candidate manifest")
sha=hashlib.sha256((o/"FROZEN_VALIDATION_CANDIDATES.csv").read_bytes()).hexdigest()
manifest={"run_id":rid,"status":"FROZEN_AWAITING_HUMAN_REVIEW","source_v16":src.name,"candidate_manifest_sha256":sha,"candidates":[{"market":r.market,"feature":r.feature,"horizon_min":int(r.horizon_min),"tail":float(r.tail)} for _,r in f.iterrows()],"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"instruction":"STOP. Human review required before opening 2018-2022 validation. Candidate definitions may not change after validation is opened."}
(o/"FREEZE_RECEIPT.json").write_text(json.dumps(manifest,indent=2))
print("[GEF17] 3/4 75% hash receipt")
print("candidate_manifest_sha256:",sha)
print("[GEF17] 4/4 100% STOP - HUMAN REVIEW REQUIRED - 2018+ UNTOUCHED")
print("\n=== V17 FREEZE RECEIPT ===");print(json.dumps(manifest,indent=2))
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V17 compile failed"}
Write-Host "=== GEF V17 - FREEZE ONLY; NO VALIDATION DATA ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V17 freeze failed"}
