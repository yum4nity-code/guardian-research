param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v38_impliedvol_audit.py"
$code=@'
from pathlib import Path
import pandas as pd,json,time,hashlib,re
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); DL=ROOT/"DataLake"; OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v38"; OUT.mkdir(parents=True,exist_ok=True)
t=time.time(); rid="GEF38-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"); O=OUT/rid; O.mkdir()
TOKENS=("vix9d","vix","vvix","gvz","ovx","cfe")
def prog(i,n,msg):
 e=time.time()-t; eta=e/i*(n-i) if i else 0; print(f"[GEF38] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
prog(1,8,"audit only: locate implied-vol/CFE sources; no alpha calculation")
files=[p for p in DL.rglob("*") if p.is_file() and any(x in p.name.lower() or x in str(p.parent).lower() for x in TOKENS)]
prog(2,8,f"located {len(files)} candidate files")
rows=[]; errs=[]
for i,p in enumerate(files):
 rec={"path":str(p),"size":p.stat().st_size,"suffix":p.suffix.lower()}
 try:
  if p.suffix.lower()==".csv": d=pd.read_csv(p,nrows=8)
  elif p.suffix.lower()==".parquet": d=pd.read_parquet(p)
  else: continue
  rec["columns"]="|".join(map(str,d.columns)); rec["rows_probe"]=len(d)
  datecols=[c for c in d.columns if re.search(r"date|time|timestamp|available",str(c),re.I)]
  rec["date_columns"]="|".join(map(str,datecols))
  for c in datecols[:3]:
   s=pd.to_datetime(d[c],errors="coerce")
   if s.notna().any(): rec[f"{c}_min"]=str(s.min());rec[f"{c}_max"]=str(s.max())
 except Exception as e: errs.append({"path":str(p),"error":repr(e)})
 rows.append(rec)
prog(3,8,"parsed CSV/Parquet metadata")
R=pd.DataFrame(rows); R.to_csv(O/"SOURCE_INVENTORY.csv",index=False)
# classify causal readiness conservatively: daily observations without explicit intraday availability are usable only from next trading day in discovery.
summary={}
for token in ("vix","vix9d","vvix","gvz","ovx","cfe"):
 q=R[R.path.str.lower().str.contains(token,regex=False)] if len(R) else R
 summary[token]={"file_count":int(len(q)),"sample_paths":q.path.head(10).tolist() if len(q) else []}
prog(4,8,"classified source families")
design={"family":"implied volatility state / term structure","discovery_period":"2010-2013 only",
"causal_policy":"Unless an explicit trustworthy publication timestamp exists, daily Cboe/CFE observations are lagged to next trading day before joining spot. No same-day intraday use.",
"targets":{"VIX":["SPXUSD","NSXUSD"],"VIX9D":["SPXUSD","NSXUSD"],"VVIX":["SPXUSD","NSXUSD"],"GVZ":["XAUUSD"],"OVX":["WTIUSD"]},
"features_predeclared":["level percentile past 252 observations","1d change","5d change","20d z-score past-only","ratio VIX9D/VIX when both causally available"],
"states":["lower tail <=10th percentile","upper tail >=90th percentile","positive/negative change tails"],
"horizons":["next session","next 1 trading day","next 5 trading days"],
"directions":["continuation","reversal"],"selection":"broad discovery screen then diverse freeze; no 2014+ access",
"forbidden":["same-day use without proven timestamp","threshold selection using 2014+","using 2023-2026"]}
(O/"PREDECLARED_DISCOVERY_DESIGN.json").write_text(json.dumps(design,indent=2))
prog(5,8,"wrote predeclared causal discovery design")
design_sha=hashlib.sha256((O/"PREDECLARED_DISCOVERY_DESIGN.json").read_bytes()).hexdigest()
inventory_sha=hashlib.sha256((O/"SOURCE_INVENTORY.csv").read_bytes()).hexdigest()
prog(6,8,f"design frozen {design_sha[:12]}")
receipt={"run_id":rid,"status":"AUDIT_COMPLETE","alpha_computed":False,"candidate_files":len(files),"parsed_inventory_rows":len(R),"errors":errs[:50],
"source_summary":summary,"causal_policy":design["causal_policy"],"design_sha256":design_sha,"inventory_sha256":inventory_sha,
"discovery_2010_2013_accessed_for_alpha":False,"replication_2014_2017_accessed":False,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,
"instruction":"STOP. Inspect audit. Only then implement V39 discovery against confirmed source paths/semantics."}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(7,8,f"receipt written; errors={len(errs)}")
prog(8,8,"STOP - no alpha search performed")
print("\n=== V38 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== INVENTORY ===");print(R.to_string(index=False) if len(R) else "NO MATCHING FILES");print("\n=== FROZEN DESIGN SHA256 ===",design_sha);print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V38 compile failed"}
Write-Host "=== GEF V38 - IMPLIED VOL SOURCE/TIMESTAMP AUDIT ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V38 failed"}
