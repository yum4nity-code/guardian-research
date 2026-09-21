param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v72_macro_fomc_inventory.py"
$code=@'
from pathlib import Path
import pandas as pd,json,time,hashlib,re
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v72";rid="GEF72-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF72] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
prog(1,8,"Family 14-16 causal inventory only; NO return testing")
# Find likely event/macro assets without reading any 2023+ spot returns.
patterns=["*fomc*","*federal*reserve*","*fed*","*bls*","*alfred*","*macro*","*release*","*calendar*"]
files=[];seen=set()
for pat in patterns:
 for p in DL.rglob(pat):
  if p.is_file() and str(p) not in seen:seen.add(str(p));files.append(p)
prog(2,8,f"candidate source files discovered={len(files)}")
rows=[]
for p in files:
 s=str(p).lower();ext=p.suffix.lower();size=p.stat().st_size
 rows.append({"path":str(p),"ext":ext,"bytes":size,"fomc":("fomc" in s),"fed":("fed" in s or "federal" in s),"bls":("bls" in s),"alfred":("alfred" in s),"macro":("macro" in s or "release" in s or "calendar" in s)})
inv=pd.DataFrame(rows);inv.to_csv(O/"SOURCE_INVENTORY.csv",index=False);prog(3,8,"source inventory written")
# Inspect schemas/samples for machine-readable tabular files, capped for safety.
schemas=[];samples=[]
for p in files:
 try:
  if p.suffix.lower()==".csv": d=pd.read_csv(p,nrows=5)
  elif p.suffix.lower()==".parquet": d=pd.read_parquet(p).head(5)
  elif p.suffix.lower() in [".json",".jsonl"]:
   txt=p.read_text(encoding="utf-8",errors="ignore")[:200000]; obj=json.loads(txt) if p.suffix.lower()==".json" else None
   if isinstance(obj,list):d=pd.DataFrame(obj[:5])
   elif isinstance(obj,dict):d=pd.DataFrame([obj])
   else:continue
  else:continue
  schemas.append({"path":str(p),"columns":[str(c) for c in d.columns],"rows_sampled":len(d)})
  samples.append({"path":str(p),"sample":d.astype(str).head(2).to_dict("records")})
 except Exception as e:schemas.append({"path":str(p),"error":str(e)[:300]})
(O/"TABULAR_SCHEMAS.json").write_text(json.dumps(schemas,indent=2));prog(4,8,f"tabular schemas inspected={len(schemas)}")
# Classify causal timestamp readiness from column names only; do not invent availability.
ready=[];tokens=["available_at","release_time","release_datetime","publication_time","published_at","timestamp","datetime"]
for z in schemas:
 cols=[c.lower() for c in z.get("columns",[])]
 hits=[c for c in cols if any(tok in c for tok in tokens)]
 ready.append({"path":z["path"],"timestamp_like_columns":hits,"causal_ready":bool(hits)})
pd.DataFrame(ready).to_csv(O/"CAUSAL_TIMESTAMP_AUDIT.csv",index=False);prog(5,8,"causal timestamp column audit complete")
# Explicitly inventory FOMC-like documents by filename/year, without interpreting text yet.
fomc=[p for p in files if "fomc" in str(p).lower()]
fr=[]
for p in fomc:
 yrs=[int(x) for x in re.findall(r"(?:19|20)\d{2}",p.name)]
 fr.append({"path":str(p),"bytes":p.stat().st_size,"years_in_name":yrs})
pd.DataFrame(fr).to_csv(O/"FOMC_DOCUMENT_INVENTORY.csv",index=False);prog(6,8,f"FOMC-like files={len(fomc)}")
# Decision: next phase may only build event table from source-supported timestamps.
causal_count=sum(x["causal_ready"] for x in ready)
decision={"family":"14_15_16_MACRO_FOMC","stage":"SOURCE_AND_CAUSALITY_INVENTORY","source_files":len(files),"fomc_files":len(fomc),"tabular_files_inspected":len(schemas),"tabular_files_with_timestamp_like_columns":causal_count,"return_trials":0,"oos_2023_2025_accessed":False,"protected_2026_accessed":False,"rule":"No event return search until AVAILABLE_AT/release timestamp semantics are verified from source metadata.","next":"BUILD_CAUSAL_EVENT_TABLE_FROM_VERIFIED_SOURCES"}
(O/"DECISION.json").write_text(json.dumps(decision,indent=2));prog(7,8,"decision frozen: zero return trials")
receipt={"run_id":rid,"status":"COMPLETE_MACRO_FOMC_CAUSAL_INVENTORY","return_trials":0,"2023_plus_spot_accessed":False,"protected_2026_accessed":False,"next":decision["next"]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(8,8,"STOP before event-return research")
print("\n=== V72 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== INVENTORY DECISION ===");print(json.dumps(decision,indent=2));print("\n=== TIMESTAMP-READY SOURCES (first 30) ===");rr=pd.DataFrame(ready);print(rr[rr.causal_ready].head(30).to_string(index=False) if len(rr) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V72 compile failed"}
Write-Host "=== GEF V72 - MACRO/FOMC CAUSAL SOURCE INVENTORY ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V72 failed"}
