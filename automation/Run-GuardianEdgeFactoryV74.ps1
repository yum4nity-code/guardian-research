param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v74_fomc_freeze.py"
$code=@'
from pathlib import Path
import pandas as pd,json,hashlib,re,time
ROOT=Path(r"D:\MT5_Backtests");SRC=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v73";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v74"
runs=sorted([p for p in SRC.glob("GEF73-*") if (p/"FOMC_DATED_DOCUMENTS_UNTIMED.csv").exists()]);assert runs
V=runs[-1];D=pd.read_csv(V/"FOMC_DATED_DOCUMENTS_UNTIMED.csv");D["event_date"]=pd.to_datetime(D.event_date)
# Only scheduled statement dates in discovery window. Deduplicate corpus artifacts.
S=D[(D.document_type=="statement")&(D.event_date.dt.year.between(2010,2013))][["event_date"]].drop_duplicates().sort_values("event_date")
# Official Fed timing semantics frozen from external verification:
# pre-2013-03-20 regular statements generally 14:15 ET, except 2011 press-briefing meetings released ~12:30 ET.
# From 2013-03-20 onward regular statements 14:00 ET. Special/unscheduled events excluded from this first lineage.
press_2011={pd.Timestamp(x) for x in ["2011-04-27","2011-06-22","2011-11-02"]}
def et_time(d):
 if d in press_2011:return "12:30"
 return "14:00" if d>=pd.Timestamp("2013-03-20") else "14:15"
S["release_time_et"]=S.event_date.map(et_time);S["verification_basis"]="OFFICIAL_FED_POLICY_TIMING";S["scheduled_only"]=True
rid="GEF74-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir(parents=True,exist_ok=True)
S.to_csv(O/"FROZEN_FOMC_DISCOVERY_EVENTS_2010_2013.csv",index=False)
sha=hashlib.sha256((O/"FROZEN_FOMC_DISCOVERY_EVENTS_2010_2013.csv").read_bytes()).hexdigest()
spec={"family":"15_FOMC_EVENTS","discovery_window":"2010-2013","event_type":"scheduled FOMC policy statement","availability":"official statement release time ET","timing_rules":{"2010_to_pre_2013_change":"14:15 ET","2011_press_briefing_dates":["2011-04-27","2011-06-22","2011-11-02"],"2011_press_briefing_release":"12:30 ET","from_2013_03_20":"14:00 ET"},"exclude":"unscheduled/special announcements in first lineage","event_count":len(S),"event_sha256":sha,"return_trials":0,"replication_2014_plus_accessed":False,"oos_2023_plus_accessed":False}
(O/"FROZEN_SPEC.json").write_text(json.dumps(spec,indent=2))
receipt={"run_id":rid,"status":"FOMC_CAUSAL_DISCOVERY_TABLE_FROZEN","events":len(S),"event_sha256":sha,"return_trials":0,"2014_plus_market_returns_accessed":False,"2023_plus_accessed":False,"protected_2026_accessed":False,"next":"V75_DISCOVERY_2010_2013"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
print("[GEF74] 1/4 25% | official timing semantics supplied and frozen")
print(f"[GEF74] 2/4 50% | scheduled discovery events={len(S)}")
print(f"[GEF74] 3/4 75% | event SHA={sha}")
print("[GEF74] 4/4 100% | STOP before returns; 2014+ unopened")
print("\n=== V74 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== FROZEN SPEC ===");print(json.dumps(spec,indent=2));print("\n=== EVENTS ===");print(S.to_string(index=False));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V74 compile failed"}
Write-Host "=== GEF V74 - FOMC CAUSAL DISCOVERY FREEZE ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V74 failed"}
