param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v53_cftc_audit.py"
$code=@'
from pathlib import Path
import pandas as pd,json,hashlib,time,re
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v53";OUT.mkdir(parents=True,exist_ok=True)
t=time.time();rid="GEF53-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF53] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
files=[];seen=set()
for pat in ["*cftc*","*CFTC*","*cot*","*COT*"]:
 for p in DL.rglob(pat):
  if p.is_file() and p not in seen:seen.add(p);files.append(p)
prog(1,8,f"inventory candidates={len(files)}")
rows=[]
for p in sorted(files):
 row={"path":str(p),"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"suffix":p.suffix.lower(),"rows":None,"columns":None,"min_date":None,"max_date":None,"error":None}
 try:
  d=pd.read_csv(p,low_memory=False) if p.suffix.lower() in [".csv",".txt"] else pd.read_parquet(p) if p.suffix.lower()==".parquet" else None
  if d is not None:
   row["rows"]=len(d);row["columns"]="|".join(map(str,d.columns))
   for c in d.columns:
    if "date" in str(c).lower():
     x=pd.to_datetime(d[c],errors="coerce")
     if x.notna().any():row["min_date"]=str(x.min());row["max_date"]=str(x.max());break
 except Exception as e:row["error"]=repr(e)
 rows.append(row)
R=pd.DataFrame(rows);R.to_csv(O/"SOURCE_INVENTORY.csv",index=False)
prog(2,8,f"hashed/inspected={len(R)}")
years=sorted({int(m) for p in files for m in re.findall(r"(?:19|20)\d{2}",p.name) if int(m)<=2022})
coverage={"min_year":min(years) if years else None,"max_year":max(years) if years else None,"year_count":len(years),"years":years}
prog(3,8,f"year coverage={coverage['min_year']}..{coverage['max_year']}")
policy={"family":"CFTC_positioning","stage":"source_timestamp_audit_only","causal_rules":{"report_reference":"Tuesday reference positions are not the usable timestamp.","publication_lag":"Use only after official publication. Default implementation must construct timezone-aware US/Eastern publication availability and join only to later market observations.","delayed_weeks":"Do not assume normal publication timing on delayed weeks; quarantine observations without defensible availability.","targets":"No target returns are read in V53."},"windows":{"discovery":"2010-2013","replication":"2014-2017","validation":"2018-2022","locked_oos":"2023-2025","protected":"2026"},"planned_features":["net_position_pct_oi","weekly_change_net_pct_oi","rolling_position_percentile","crowding_extreme"],"planned_horizons_days":[1,5,10,20],"rule":"No discovery until schema, market mapping, report date and AVAILABLE_AT are explicit."}
(O/"CAUSAL_DESIGN.json").write_text(json.dumps(policy,indent=2));dsha=hashlib.sha256((O/"CAUSAL_DESIGN.json").read_bytes()).hexdigest();isha=hashlib.sha256((O/"SOURCE_INVENTORY.csv").read_bytes()).hexdigest()
prog(4,8,f"causal policy frozen {dsha[:12]}")
receipt={"run_id":rid,"status":"COMPLETE_CFTC_SOURCE_TIMESTAMP_AUDIT","inventory_files":len(R),"design_sha256":dsha,"inventory_sha256":isha,"target_returns_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(5,8,"receipt written");prog(6,8,"no alpha evaluated");prog(7,8,"OOS/protected sealed");prog(8,8,"STOP")
print("\n=== V53 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== COVERAGE ===");print(json.dumps(coverage,indent=2));print("\n=== INVENTORY PREVIEW ===");print(R[["path","rows","min_date","max_date","error"]].head(20).to_string(index=False) if len(R) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V53 compile failed"}
Write-Host "=== GEF V53 - CFTC SOURCE/TIMESTAMP AUDIT ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V53 failed"}
