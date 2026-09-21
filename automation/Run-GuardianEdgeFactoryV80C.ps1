param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v80c_rebuild_full_causal_matrix.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,re,hashlib,time
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake"
V80=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v80").glob("GEF80-*"))[-1]
C=pd.read_parquet(V80/"CAUSAL_STATE_MATRIX_2010_2013.parquet");C.index=pd.to_datetime(C.index)
rid="GEF80C-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");O=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v80c"/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF80C] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
def add_asof(frame,name,dates,vals):
 src=pd.DataFrame({"a":pd.to_datetime(dates,errors="coerce"),name:pd.to_numeric(vals,errors="coerce")}).dropna().sort_values("a").drop_duplicates("a",keep="last")
 if len(src)<4:return None
 base=pd.DataFrame({"t":frame.index})
 z=pd.merge_asof(base,src,left_on="t",right_on="a",direction="backward")
 return pd.Series(z[name].to_numpy(),index=frame.index,name=name)
prog(1,10,"repair CFE + ALFRED summaries; EIA remains blocked until release semantics; no edge search")
adds=[];prov=[]
# CFE normalized daily tables: use Date +1 calendar day 00:00 UTC, conservative EOD availability.
for p in (DL/"normalized"/"cboe_cfe_pre2023").glob("*.parquet"):
 d=pd.read_parquet(p)
 if "Date" not in d:continue
 av=pd.to_datetime(d["Date"],errors="coerce")+pd.Timedelta(days=1)
 for c in d.columns:
  if c=="Date":continue
  v=pd.to_numeric(d[c],errors="coerce")
  if v.notna().sum()<100:continue
  nm=re.sub(r"[^A-Za-z0-9_]+","_",f"cfe_{p.stem}_{c}")[:150]
  s=add_asof(C,nm,av,v)
  if s is not None:adds.append(s);prov.append({"feature":nm,"source":str(p),"available_at_rule":"Date +1d 00:00 UTC conservative"})
prog(2,10,f"CFE features added={sum(x['feature'].startswith('cfe_') for x in prov)}")
# ALFRED revision summaries: first_vintage is first known vintage. Use +1d conservatively.
# These are revision-structure descriptors; only first_value and revision metadata known by first_vintage are allowed.
for p in (DL/"normalized"/"alfred_pre2023").glob("*_revision_summary_PRE2023.parquet"):
 d=pd.read_parquet(p)
 if "first_vintage" not in d:continue
 av=pd.to_datetime(d["first_vintage"],errors="coerce")+pd.Timedelta(days=1)
 for c in ["first_value"]:
  if c not in d:continue
  nm=re.sub(r"[^A-Za-z0-9_]+","_",f"alfred_summary_{p.stem}_{c}")[:150]
  s=add_asof(C,nm,av,d[c])
  if s is not None:adds.append(s);prov.append({"feature":nm,"source":str(p),"available_at_rule":"first_vintage +1d conservative; first_value only"})
prog(3,10,f"ALFRED summary features added={sum(x['feature'].startswith('alfred_summary_') for x in prov)}")
# Explicitly do NOT leak last_vintage/last_value/was_revised/vintage_count: future knowledge.
blocked=[]
for p in (DL/"normalized"/"alfred_pre2023").glob("*_revision_summary_PRE2023.parquet"):
 blocked.append({"source":str(p),"reason":"future revision summary fields excluded: last_vintage,last_value,was_revised,vintage_count"})
# EIA period_end is observation period, not publication timestamp: remains blocked.
for p in (DL/"normalized"/"eia_pre2023").glob("*.parquet"):
 blocked.append({"source":str(p),"reason":"period_end is not AVAILABLE_AT; exact WPSR publication semantics required"})
prog(4,10,"future-revision leakage explicitly excluded; EIA held out")
if adds:
 A=pd.concat(adds,axis=1)
 # transforms in one concat, avoiding V80 fragmentation warnings
 parts=[A]
 parts.append(A.diff(24).add_suffix("_d24h"));parts.append(A.diff(120).add_suffix("_d120h"))
 Z=pd.concat(parts,axis=1)
 C=pd.concat([C,Z],axis=1)
prog(5,10,f"matrix rebuilt cols={C.shape[1]:,}")
# de-duplicate exact feature names and exact vectors
C=C.loc[:,~C.columns.duplicated()].copy()
seen=set();keep=[]
for c in C.columns:
 h=hashlib.sha256(pd.util.hash_pandas_object(C[c].fillna(-9.87654321e307),index=False).values.tobytes()).hexdigest()
 if h not in seen:seen.add(h);keep.append(c)
C=C[keep].copy()
prog(6,10,f"deduplicated cols={C.shape[1]:,}")
C.to_parquet(O/"CAUSAL_STATE_MATRIX_2010_2013_FULL.parquet")
pd.DataFrame(prov).to_csv(O/"ADDED_FEATURE_PROVENANCE.csv",index=False);pd.DataFrame(blocked).to_csv(O/"EXPLICIT_EXCLUSIONS.csv",index=False)
prog(7,10,"full matrix + provenance written")
# Family counts
families={}
for c in C.columns:
 k="price_state"
 for pref in ["cfe_","alfred_","cboe_vol_","cftc_","financial_conditions_","fred_","rates_yields_","treasury_auctions_"]:
  if c.startswith(pref):k=pref.rstrip("_");break
 families[k]=families.get(k,0)+1
(O/"FEATURE_FAMILY_COUNTS.json").write_text(json.dumps(families,indent=2));prog(8,10,f"families={families}")
sha=hashlib.sha256((O/"CAUSAL_STATE_MATRIX_2010_2013_FULL.parquet").read_bytes()).hexdigest()
spec={"input_v80":V80.name,"matrix_sha256":sha,"rows":len(C),"features":C.shape[1],"cfe_rule":"Date+1d conservative","alfred_summary_rule":"first_vintage+1d, first_value only","eia":"BLOCKED exact AVAILABLE_AT not established","search_next":"cross-family pair concordances only; singleton baselines mandatory; complete trial ledger; selection correction; 2014+ unopened"}
(O/"FULL_MATRIX_SPEC.json").write_text(json.dumps(spec,indent=2));prog(9,10,f"SHA={sha[:16]}...")
receipt={"run_id":rid,"status":"COMPLETE_FULL_CAUSAL_MATRIX_PRE_DISCOVERY","rows":len(C),"features":C.shape[1],"added_features":len(prov),"eia_blocked":True,"edge_trials":0,"2014_plus_accessed":False,"2023_plus_accessed":False,"protected_2026_accessed":False,"next":"V81_CROSS_SOURCE_CONCORDANCE_DISCOVERY"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(10,10,"DONE")
print("\n=== V80C RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== FEATURE FAMILY COUNTS ===");print(json.dumps(families,indent=2));print("\n=== EXCLUSIONS ===");print(pd.DataFrame(blocked).to_string(index=False));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V80C compile failed"}
Write-Host "=== GEF V80C - FULL CAUSAL MATRIX REBUILD ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V80C failed"}
