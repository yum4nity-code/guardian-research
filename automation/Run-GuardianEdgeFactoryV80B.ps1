param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v80b_blocked_source_forensic.py"
$code=@'
from pathlib import Path
import pandas as pd,json,time,re
ROOT=Path(r"D:\MT5_Backtests")
V80=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v80").glob("GEF80-*"))[-1]
B=pd.read_csv(V80/"BLOCKED_SOURCE_TABLES.csv")
rid="GEF80B-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");O=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v80b"/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF80B] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
prog(1,7,f"forensic blocked tables={len(B)}; no market returns")
rows=[]
for k,r in B.iterrows():
 p=Path(r.path);info={"path":str(p),"family":r.family,"reason":r.reason,"ext":p.suffix.lower()}
 try:
  if p.suffix.lower()==".csv":d=pd.read_csv(p,nrows=12)
  elif p.suffix.lower()==".parquet":d=pd.read_parquet(p).head(12)
  elif p.suffix.lower() in [".xlsx",".xls"]:d=pd.read_excel(p,nrows=12)
  else:d=pd.DataFrame()
  info["columns"]=[str(c) for c in d.columns];info["sample"]=d.astype(str).head(5).to_dict("records")
  # Candidate date/time/release fields only; no automatic causal claim.
  info["candidate_time_columns"]=[str(c) for c in d.columns if any(x in str(c).lower() for x in ["date","time","release","publish","report","week","vintage","available"])]
 except Exception as e:info["error"]=str(e)[:300]
 rows.append(info)
 if (k+1)%5==0:prog(min(2+k//5,5),7,f"inspected {k+1}/{len(B)}")
(O/"BLOCKED_SOURCE_FORENSIC.json").write_text(json.dumps(rows,indent=2))
# Explicit remediation map based on actual schemas, for next implementation/research.
rem=[]
for x in rows:
 rem.append({"path":x["path"],"family":x["family"],"candidate_time_columns":";".join(x.get("candidate_time_columns",[])),"action":"RESOLVE_RELEASE_SEMANTICS_FROM_SCHEMA_OR_OFFICIAL_SOURCE","auto_join":False})
pd.DataFrame(rem).to_csv(O/"REMEDIATION_QUEUE.csv",index=False)
prog(6,7,"forensic + remediation queue written")
receipt={"run_id":rid,"status":"COMPLETE_BLOCKED_SOURCE_FORENSIC","blocked_tables":len(B),"families":sorted(B.family.unique().tolist()),"market_returns_accessed":False,"edge_trials":0,"next":"RESOLVE_CFE_ALFRED_EIA_THEN_REBUILD_MATRIX_BEFORE_V81"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(7,7,"STOP; do not run V81 yet")
print("\n=== V80B RECEIPT ===");print(json.dumps(receipt,indent=2))
print("\n=== BLOCKED SOURCE FORENSIC ===")
for x in rows:
 print("\n",x["family"],"::",x["path"]);print(" candidate_time_columns:",x.get("candidate_time_columns"));print(" columns:",x.get("columns"))
print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V80B compile failed"}
Write-Host "=== GEF V80B - BLOCKED SOURCE FORENSIC ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V80B failed"}
