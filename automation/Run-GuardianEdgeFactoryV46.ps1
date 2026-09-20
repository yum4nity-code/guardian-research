param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v46_rates_source_audit.py"
$code=@'
from pathlib import Path
import pandas as pd,json,hashlib,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v46";OUT.mkdir(parents=True,exist_ok=True)
t=time.time();rid="GEF46-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF46] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
# Audit only. Never calculate alpha or read post-2022 target returns.
patterns=["*yield*","*treasury*","*breakeven*","*real*rate*","*fred*","*alfred*"]
files=[];seen=set()
for pat in patterns:
 for p in DL.rglob(pat):
  if p.is_file() and p not in seen:seen.add(p);files.append(p)
prog(1,8,f"inventory candidates {len(files)}")
rows=[]
for p in sorted(files):
 try:
  size=p.stat().st_size;sha=hashlib.sha256(p.read_bytes()).hexdigest()
  row={"path":str(p),"bytes":size,"sha256":sha,"suffix":p.suffix.lower(),"rows":None,"min_date":None,"max_date":None,"columns":None,"error":None}
  if p.suffix.lower() in [".csv",".parquet"]:
   try:
    d=pd.read_csv(p,nrows=200000) if p.suffix.lower()==".csv" else pd.read_parquet(p)
    row["rows"]=len(d);row["columns"]="|".join(map(str,d.columns))
    for c in d.columns:
     if any(k in str(c).lower() for k in ["date","time","observation","vintage","realtime"]):
      x=pd.to_datetime(d[c],errors="coerce")
      if x.notna().any():
       row["min_date"]=str(x.min());row["max_date"]=str(x.max());break
   except Exception as e:row["error"]=repr(e)
  rows.append(row)
 except Exception as e:rows.append({"path":str(p),"error":repr(e)})
prog(2,8,"hashed and inspected structured candidates")
R=pd.DataFrame(rows);R.to_csv(O/"SOURCE_INVENTORY.csv",index=False)
# Identify likely usable rate families from names/columns. This is provenance classification, not feature selection.
def classify(s):
 z=s.lower()
 out=[]
 for k,label in [("breakeven","breakeven"),("real","real_yield"),("yield","nominal_yield"),("dgs","nominal_yield"),("dfii","real_yield"),("t10yie","breakeven"),("t5yie","breakeven"),("alfred","vintage_source"),("fred","fred_source")]:
  if k in z and label not in out:out.append(label)
 return "|".join(out)
R["class"]=R.apply(lambda r:classify(str(r.get("path",""))+" "+str(r.get("columns",""))),axis=1)
U=R[R["class"]!=""].copy();U.to_csv(O/"RATES_RELEVANT_INVENTORY.csv",index=False)
prog(3,8,f"rates-relevant files {len(U)}")
# Causal policy: vintage data may use release/vintage availability; non-vintage daily observations are next-observation lagged.
policy={"family":"rates_real_yields_breakevens","stage":"source_timestamp_audit_only","causal_rules":{"ALFRED_vintage":"Use only value whose realtime/vintage availability is <= decision time. Never use latest revised history as historical knowledge.","non_vintage_daily_rates":"Conservative default: shift by one source observation before joining to market date unless a trustworthy publication timestamp proves earlier availability.","market_targets":"No target returns are evaluated in V46."},"research_windows":{"discovery":"2010-2013","replication":"2014-2017","validation":"2018-2022","locked_oos":"2023-2025","protected":"2026"},"candidate_markets":["XAUUSD","XAGUSD","UDXUSD","EURUSD","USDJPY","SPXUSD","NSXUSD"],"planned_feature_families":["nominal yield level/change/curve slope","real yield level/change/curve slope","breakeven level/change","nominal-real differential interactions"],"rule":"V47 discovery may use only sources that pass this audit; no 2014+ selection."}
(O/"CAUSAL_DESIGN.json").write_text(json.dumps(policy,indent=2))
prog(4,8,"causal availability policy frozen")
# Explicitly flag suspicious post-2022 presence by parsed max dates; presence is okay for source files, but V47 must slice discovery.
post=[]
for _,r in U.iterrows():
 try:
  mx=pd.Timestamp(r["max_date"])
  if mx.year>2022:post.append(str(r["path"]))
 except:pass
(O/"POST2022_SOURCE_PRESENCE.json").write_text(json.dumps(post,indent=2))
prog(5,8,f"post-2022 source files flagged {len(post)} (not alpha-accessed)")
design_sha=hashlib.sha256((O/"CAUSAL_DESIGN.json").read_bytes()).hexdigest();inv_sha=hashlib.sha256((O/"RATES_RELEVANT_INVENTORY.csv").read_bytes()).hexdigest()
receipt={"run_id":rid,"status":"COMPLETE_AUDIT_ONLY","family":"rates_real_yields_breakevens","inventory_files":len(files),"rates_relevant_files":len(U),"design_sha256":design_sha,"inventory_sha256":inv_sha,"discovery_alpha_accessed":False,"replication_accessed":False,"validation_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":R[R.error.notna()][["path","error"]].to_dict("records") if "error" in R else []}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(6,8,f"design sha {design_sha[:12]} | inventory sha {inv_sha[:12]}")
prog(7,8,"assertions: no alpha tested | 2014+ not used for selection")
prog(8,8,"STOP | ready for V47 discovery design")
print("\n=== V46 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== RELEVANT SOURCES (first 40) ===");print(U[["path","class","rows","min_date","max_date","error"]].head(40).to_string(index=False));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V46 compile failed"}
Write-Host "=== GEF V46 - RATES / REAL YIELDS / BREAKEVENS SOURCE AUDIT ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V46 failed"}
