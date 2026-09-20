param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v50_rates_freeze.py"
$code=@'
from pathlib import Path
import pandas as pd,json,hashlib,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");V49=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v49";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v50";OUT.mkdir(parents=True,exist_ok=True)
EXP="cf3ea5222f8118e210aa5e83f2ec73856a805430ceaef9b37edf22f6d3e0557f"
t=time.time();rid="GEF50-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF50] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
runs=sorted([p for p in V49.glob("GEF49-*") if (p/"ROBUSTNESS_SURVIVORS.csv").exists()])
src=None
for p in reversed(runs):
 if hashlib.sha256((p/"ROBUSTNESS_SURVIVORS.csv").read_bytes()).hexdigest()==EXP:src=p;break
if src is None:raise RuntimeError("Exact V49 robust survivor artifact not found")
p=src/"ROBUSTNESS_SURVIVORS.csv";sha=hashlib.sha256(p.read_bytes()).hexdigest();F=pd.read_csv(p)
if sha!=EXP or len(F)!=3:raise RuntimeError(f"V49 mismatch sha={sha} n={len(F)}")
prog(1,6,f"verified V49 artifact {sha[:12]} | n=3")
cols=["key"]
manifest=F[cols].copy()
manifest["source_v49_run"]=src.name
manifest["source_v49_sha256"]=sha
manifest["frozen_before_validation"]=True
manifest.to_csv(O/"IMMUTABLE_VALIDATION_MANIFEST.csv",index=False)
msha=hashlib.sha256((O/"IMMUTABLE_VALIDATION_MANIFEST.csv").read_bytes()).hexdigest()
gate={"period":"2018-2022 only","definitions":"exact V49 keys; reconstruct identically to V48/V49","pass_gate":{"n_min":40,"gross_bp_gt":0,"hit_gte":0.52,"positive_year_fraction_gte":0.60,"trim_best_1pct_bp_gt":0,"remove_best_5_days_bp_gt":0,"nonoverlap_h5_bp_gt":0,"extra_lag1_bp_gt":0},"no_retuning":True,"no_rescue":True,"locked_oos_2023_2025":True,"protected_2026":True}
(O/"VALIDATION_GATE.json").write_text(json.dumps(gate,indent=2));gsha=hashlib.sha256((O/"VALIDATION_GATE.json").read_bytes()).hexdigest()
prog(2,6,f"immutable manifest written {msha[:12]}")
prog(3,6,f"validation gate frozen {gsha[:12]}")
receipt={"run_id":rid,"status":"COMPLETE_IMMUTABLE_PREVALIDATION_FREEZE","source_v49":src.name,"verified_v49_sha256":sha,"candidate_count":3,"manifest_sha256":msha,"validation_gate_sha256":gsha,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(4,6,"receipt written")
prog(5,6,"2018+ untouched")
prog(6,6,"STOP - ready for independent validation")
print("\n=== V50 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== FROZEN KEYS ===");print("\n".join(F.key));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V50 compile failed"}
Write-Host "=== GEF V50 - IMMUTABLE PRE-VALIDATION FREEZE ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V50 failed"}
