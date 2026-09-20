param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v56c_cftc_prefreeze.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,hashlib,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");SRC=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v56"/"GEF56-20260920-183240";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v56c";OUT.mkdir(parents=True,exist_ok=True)
EXPECTED="5a3eec6ceca2d951622619c00298e63c6ba2b35694abd60b5107bc3572e43c06"
t=time.time();rid="GEF56C-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF56C] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
p=SRC/"FROZEN_CANDIDATES.csv";sha=hashlib.sha256(p.read_bytes()).hexdigest()
if sha!=EXPECTED:raise RuntimeError("V56 freeze SHA mismatch")
F=pd.read_csv(p);prog(1,8,f"verified V56 freeze sha={sha[:12]} candidates={len(F)}")
# Structural dedup only: no new returns, dates or future periods are read.
# CFTC legacy accounting makes commercial/noncommercial opposite-side signals potentially redundant.
def side(row):
 tail=row["tail"];mode=row["mode"]
 raw=1 if tail=="hi" else -1
 return raw if mode=="continuation" else -raw
F["trade_side"]=F.apply(side,axis=1)
F["economic_family"]=F.apply(lambda r:f'{r.market}|CFTC_NET_EXTREME|{r["transform"].split("_")[-1]}|H{int(r.h)}|SIDE{int(r.trade_side)}',axis=1)
prog(2,8,f"structural families={F.economic_family.nunique()}")
# Within each economic family choose representative deterministically:
# larger n, then higher hit, then higher gross; no new data.
ranked=F.sort_values(["economic_family","n","hit","gross_bp"],ascending=[True,False,False,False])
R=ranked.drop_duplicates("economic_family",keep="first").copy()
# Also avoid counting H5/H10/H20 as independent discoveries: lineage groups collapse horizon.
R["lineage_family"]=R.apply(lambda r:f'{r.market}|CFTC_NET_EXTREME|{r["transform"].split("_")[-1]}|SIDE{int(r.trade_side)}',axis=1)
L=R.sort_values(["lineage_family","n","hit","gross_bp"],ascending=[True,False,False,False]).drop_duplicates("lineage_family",keep="first").copy()
prog(3,8,f"economic reps={len(R)} horizon-collapsed lineages={len(L)}")
# Cap is diversity, not performance optimization: one lineage per market/trade-side/transform class.
L=L.sort_values(["market","lineage_family","n"],ascending=[True,True,False]).reset_index(drop=True)
L.to_csv(O/"PRE_REPLICATION_LINEAGES.csv",index=False);R.to_csv(O/"ECONOMIC_FAMILY_REPRESENTATIVES.csv",index=False)
# Audit duplicates and exact metric coincidences.
dups=F.groupby("economic_family").agg(members=("key","count"),keys=("key",lambda x:" || ".join(x))).reset_index()
dups=dups[dups.members>1];dups.to_csv(O/"STRUCTURAL_DUPLICATES.csv",index=False)
metric_dups=F.groupby(["market","n","gross_bp","hit","positive_year_fraction"]).agg(members=("key","count"),keys=("key",lambda x:" || ".join(x))).reset_index()
metric_dups=metric_dups[metric_dups.members>1];metric_dups.to_csv(O/"EXACT_METRIC_DUPLICATES.csv",index=False)
prog(4,8,f"structural duplicate groups={len(dups)} exact-metric duplicate groups={len(metric_dups)}")
# Freeze exact lineage list before replication.
freeze_cols=["key","market","cftc_market","feature","transform","tail","q","h","mode","n","gross_bp","hit","positive_year_fraction","trade_side","economic_family","lineage_family"]
L=L[freeze_cols]
L.to_csv(O/"V57_FROZEN_INPUT.csv",index=False)
fsha=hashlib.sha256((O/"V57_FROZEN_INPUT.csv").read_bytes()).hexdigest()
prog(5,8,f"V57 frozen inputs={len(L)} sha={fsha[:12]}")
receipt={"run_id":rid,"status":"COMPLETE_PRE_REPLICATION_DEDUP_FREEZE","source_v56":"GEF56-20260920-183240","verified_v56_freeze_sha256":sha,"input_candidates":len(F),"economic_families":int(F.economic_family.nunique()),"economic_representatives":len(R),"horizon_collapsed_lineages":len(L),"structural_duplicate_groups":len(dups),"exact_metric_duplicate_groups":len(metric_dups),"v57_frozen_input_sha256":fsha,"new_returns_accessed":False,"replication_2014_2017_accessed":False,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"selection_note":"structural dedup only; representative uses already-frozen V56 n/hit/gross metrics; no new observations"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(6,8,"receipt written");prog(7,8,"2014+ untouched");prog(8,8,"STOP before replication")
print("\n=== V56C RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== V57 FROZEN INPUT ===");print(L.to_string(index=False));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V56C compile failed"}
Write-Host "=== GEF V56C - CFTC PRE-REPLICATION DEDUP ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V56C failed"}
