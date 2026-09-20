param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v43_freeze.py"
$code=@'
from pathlib import Path
import pandas as pd,json,hashlib,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");V42=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v42";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v43";OUT.mkdir(parents=True,exist_ok=True)
EXPECTED="e5cc99538c1061df70e9e9242675e115f8a3887ecc1e43a1bd795bd21ec18491"
t=time.time();rid="GEF43-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;print(f"[GEF43] {i}/{n} {100*i/n:.0f}% | elapsed {e:.1f}s | {msg}",flush=True)
runs=sorted([p for p in V42.glob("GEF42-*") if (p/"FORENSIC_SURVIVORS.csv").exists() and (p/"RUN_RECEIPT.json").exists()])
if not runs:raise RuntimeError("No V42")
src=runs[-1];fp=src/"FORENSIC_SURVIVORS.csv";sha=hashlib.sha256(fp.read_bytes()).hexdigest()
if sha!=EXPECTED:raise RuntimeError(f"V42 survivor hash mismatch {sha}")
F=pd.read_csv(fp)
if len(F)!=5 or not F.forensic_pass.all():raise RuntimeError("Expected exactly five passing V42 candidates")
prog(1,6,f"verified V42 {src.name} sha {sha[:12]}")
cols=["source","target","feature","tail","horizon_days","mode"]
C=F[cols].copy()
C.insert(0,"candidate_id",[f"IV-{i:02d}" for i in range(1,len(C)+1)])
C["signal_semantics"]="Cboe daily observation; feature computed past-only; mandatory shift(1) before spot-date join"
C["entry_semantics"]="daily spot close on joined trading date after mandatory Cboe lag"
C["target_semantics"]="forward log return at frozen trading-day horizon"
C["discovery_period"]="2010-2013 (VIX9D availability as applicable)"
C["replication_period"]="2014-2017"
C["validation_period"]="2018-2022"
C.to_csv(O/"IMMUTABLE_CANDIDATE_MANIFEST.csv",index=False)
prog(2,6,"wrote immutable candidate manifest")
gate={"no_retuning":True,"validation_period":"2018-01-01..2022-12-31","pass_per_candidate":{"minimum_events":80,"gross_mean_bp":"> 0","positive_year_fraction":">= 0.60","trim_best_1pct_mean_bp":"> 0","trim_best_2pct_mean_bp":"> 0","remove_best_5_events_mean_bp":"> 0","nonoverlap_mean_bp":"> 0","extra_information_lag_1obs_mean_bp":"> 0"},"family_rule":"Report every candidate. No replacement, rescue, threshold/window change, or winner selection after validation is opened.","post_validation":"Regardless of result, STOP before locked OOS 2023-2025. Human review required."}
(O/"VALIDATION_GATE.json").write_text(json.dumps(gate,indent=2))
prog(3,6,"froze independent validation gate")
manifest_sha=hashlib.sha256((O/"IMMUTABLE_CANDIDATE_MANIFEST.csv").read_bytes()).hexdigest();gate_sha=hashlib.sha256((O/"VALIDATION_GATE.json").read_bytes()).hexdigest()
lock={"run_id":rid,"status":"FROZEN_AWAITING_VALIDATION","source_v42":src.name,"source_v42_sha256":sha,"candidate_count":5,"manifest_sha256":manifest_sha,"validation_gate_sha256":gate_sha,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"instruction":"Next step may independently validate exactly this manifest on 2018-2022. No retuning. Never open 2023-2025 in the same run."}
(O/"FREEZE_RECEIPT.json").write_text(json.dumps(lock,indent=2))
prog(4,6,f"manifest sha {manifest_sha[:12]} | gate sha {gate_sha[:12]}")
# self-verification
assert hashlib.sha256((O/"IMMUTABLE_CANDIDATE_MANIFEST.csv").read_bytes()).hexdigest()==manifest_sha
assert hashlib.sha256((O/"VALIDATION_GATE.json").read_bytes()).hexdigest()==gate_sha
prog(5,6,"self-verification passed")
prog(6,6,"STOP | immutable freeze complete | 2018+ untouched")
print("\n=== V43 FREEZE ===");print(json.dumps(lock,indent=2));print("\n=== MANIFEST ===");print(C.to_string(index=False));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V43 compile failed"}
Write-Host "=== GEF V43 - IMMUTABLE PRE-VALIDATION FREEZE ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V43 failed"}
