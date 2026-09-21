param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v61_cftc_final_preoos.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");SRC=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v60"/"GEF60-20260920-184445";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v61";OUT.mkdir(parents=True,exist_ok=True)
EXPECTED="4ab91532618be89f6111e62b3a6c74804f40c656f90b8fd2397a2636a9a2e4c4"
t=time.time();rid="GEF61-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def p(i,n,msg):
 e=time.time()-t;print(f"[GEF61] {i}/{n} {100*i/n:.0f}% | elapsed {e:.1f}s | {msg}",flush=True)
fp=SRC/"PREOOS_SURVIVORS.csv";sha=hashlib.sha256(fp.read_bytes()).hexdigest()
if sha!=EXPECTED:raise RuntimeError("V60 survivor SHA mismatch")
R=pd.read_csv(fp);p(1,6,f"verified V60 survivors sha={sha[:12]} n={len(R)}")
# V61 is a forensic gate over already-produced independent validation statistics.
# It does NOT read market/CFTC data and cannot access 2023+.
# Predeclared concentration rules: validation trim1 >0, remove-best5 >0,
# true non-overlap >0 and >=8 non-overlap observations. USDCAD's n=9 is explicitly allowed
# but flagged LOW_SAMPLE; no threshold is changed after inspection.
rows=[]
for _,r in R.iterrows():
 reasons=[]
 if not (r.gross_bp>0):reasons.append("gross<=0")
 if not (r.trim1_bp>0):reasons.append("trim1<=0")
 if not (r.remove_best5days_bp>0):reasons.append("remove_best5<=0")
 if not (r.true_nonoverlap_bp>0):reasons.append("nonoverlap<=0")
 if int(r.nonoverlap_n)<8:reasons.append("nonoverlap_n<8")
 status="PASS_FINAL_PREOOS" if not reasons else "FAIL_FINAL_PREOOS"
 rows.append({**r.to_dict(),"forensic_status":status,"forensic_reasons":";".join(reasons),"sample_flag":"LOW_SAMPLE" if int(r.nonoverlap_n)<20 else "OK"})
p(2,6,"concentration checks applied")
F=pd.DataFrame(rows);F.to_csv(O/"FINAL_PREOOS_FORENSIC.csv",index=False);P=F[F.forensic_status=="PASS_FINAL_PREOOS"].copy();P.to_csv(O/"OOS_ELIGIBLE_CANDIDATES.csv",index=False)
psha=hashlib.sha256((O/"OOS_ELIGIBLE_CANDIDATES.csv").read_bytes()).hexdigest();p(3,6,f"OOS-eligible={len(P)} sha={psha[:12]}")
# Human-review manifest. No OOS runner is created here.
review={"decision_required":"HUMAN_REVIEW_BEFORE_LOCKED_OOS","eligible_count":len(P),"eligible_sha256":psha,"locked_oos_window":"2023-2025","protected_2026":"DO_NOT_OPEN","notes":["V61 uses only V60 output; no new observations accessed.","Passing V61 means eligible for OOS review, not proven deployable alpha.","LOW_SAMPLE flags must be considered before spending locked OOS."]}
(O/"HUMAN_REVIEW_REQUIRED.json").write_text(json.dumps(review,indent=2));p(4,6,"human-review stop manifest written")
receipt={"run_id":rid,"status":"COMPLETE_FINAL_PREOOS_FORENSIC","source_v60_survivor_sha256":sha,"tested":len(F),"oos_eligible":len(P),"oos_eligible_sha256":psha,"new_market_data_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"retuning":False,"hard_stop":"HUMAN_REVIEW_REQUIRED"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));p(5,6,"receipt written; 2023+ untouched");p(6,6,"HARD STOP")
print("\n=== V61 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== FINAL PRE-OOS FORENSIC ===");print(F.to_string(index=False));print("\n=== HUMAN REVIEW ===");print(json.dumps(review,indent=2));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V61 compile failed"}
Write-Host "=== GEF V61 - CFTC FINAL PRE-OOS FORENSIC ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V61 failed"}
