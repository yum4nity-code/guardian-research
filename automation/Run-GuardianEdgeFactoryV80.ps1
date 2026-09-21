param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v80_external_causal_normalizer.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,re,time,hashlib
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake"
V79=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v79").glob("GEF79-*"))[-1]
M=pd.read_parquet(V79/"PRICE_STATE_MATRIX_2010_2013.parquet");M.index=pd.to_datetime(M.index)
rid="GEF80-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");O=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v80"/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF80] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
prog(1,14,"external causal normalization; discovery window only; no edge search")
files=[p for p in DL.rglob("*") if p.is_file() and p.suffix.lower() in [".csv",".parquet",".xlsx",".xls"] and "histdata" not in str(p).lower()]
def read(p):
 try:
  if p.suffix.lower()==".csv":return pd.read_csv(p)
  if p.suffix.lower()==".parquet":return pd.read_parquet(p)
  return pd.read_excel(p)
 except:return None
def classify(p,cols):
 s=(str(p)+" "+" ".join(map(str,cols))).lower()
 rules=[("cfe_volume_oi",["open_interest","open interest","cfe","futures_volume"]),("treasury_auctions",["auction_date","bid_to_cover","bid-to-cover","competitive_accepted"]),("financial_conditions",["financial conditions","nfci","stlfs"]),("alfred_vintage",["realtime_start","vintage_date","vintage_dates","alfred"]),("cftc",["cftc","commitment","commercial","noncommercial"]),("cboe_vol",["vix","vvix","vix9d","ovx","gvz","cboe"]),("eia_energy",["eia","wpsr","petroleum"]),("bls_macro",["bls"]),("fomc_fed",["fomc","federalreserve"]),("rates_yields",["yield","treasury","breakeven","real rate"]),("fred",["fred"])]
 for k,keys in rules:
  if any(x in s for x in keys):return k
 return "other"
catalog=[]
for p in files:
 d=read(p)
 if d is None or d.empty:continue
 catalog.append((p,d,classify(p,d.columns)))
prog(2,14,f"readable external tables={len(catalog)}")
# Conservative normalization: only datasets with defensible date semantics enter matrix automatically.
# Daily market/end-of-day series become available next UTC day 00:00 (conservative).
# ALFRED uses realtime_start/vintage date. Weekly CFTC assumed available Friday 20:30 UTC (conservative);
# exact historical DST/release semantics remain flagged for verification and are not auto-joined if ambiguous.
joined=[];blocked=[];X=pd.DataFrame(index=M.index)
def numeric_cols(d):
 return [c for c in d.columns if pd.api.types.is_numeric_dtype(d[c])][:40]
for p,d,fam in catalog:
 cols={str(c).lower():c for c in d.columns}; av=None; rule=None
 try:
  if fam=="alfred_vintage":
   c=next((cols[x] for x in ["realtime_start","vintage_date","available_date","initial_vintage_date"] if x in cols),None)
   if c is not None: av=pd.to_datetime(d[c],errors="coerce")+pd.Timedelta(days=1);rule=f"{c}+1d conservative"
  elif fam in ["cboe_vol","financial_conditions","fred","rates_yields"]:
   c=next((cols[x] for x in ["date","observation_date"] if x in cols),None)
   if c is not None: av=pd.to_datetime(d[c],errors="coerce")+pd.Timedelta(days=1);rule=f"{c}+1d conservative"
  elif fam=="cftc":
   c=next((v for k,v in cols.items() if "report_date" in k or k in ["date","as_of_date"]),None)
   if c is not None: av=pd.to_datetime(d[c],errors="coerce")+pd.Timedelta(days=3,hours=21);rule=f"{c}+3d21h conservative Friday-after-Tuesday"
  elif fam=="treasury_auctions":
   c=next((v for k,v in cols.items() if k=="auction_date"),None)
   if c is not None: av=pd.to_datetime(d[c],errors="coerce")+pd.Timedelta(days=1);rule=f"{c}+1d conservative; intraday auction time not asserted"
  if av is None:
   blocked.append({"path":str(p),"family":fam,"reason":"NO_DEFENSIBLE_AVAILABLE_AT_RULE"});continue
  q=d.copy();q["_available_at"]=av;q=q.dropna(subset=["_available_at"]);q=q[(q._available_at.dt.year>=2009)&(q._available_at.dt.year<=2013)]
  nums=numeric_cols(q)
  if not nums:blocked.append({"path":str(p),"family":fam,"reason":"NO_NUMERIC_FEATURES"});continue
  # dedup columns and cap per table; merge_asof strictly backward.
  q=q.sort_values("_available_at").drop_duplicates("_available_at",keep="last")
  base=pd.DataFrame({"decision_time_utc":X.index}).sort_values("decision_time_utc")
  added=0
  for c in nums[:20]:
   vals=pd.to_numeric(q[c],errors="coerce")
   if vals.notna().sum()<4:continue
   nm=re.sub(r"[^A-Za-z0-9_]+","_",f"{fam}_{p.stem}_{c}")[:120]
   src=pd.DataFrame({"_available_at":q["_available_at"],nm:vals}).dropna().sort_values("_available_at")
   z=pd.merge_asof(base,src,left_on="decision_time_utc",right_on="_available_at",direction="backward")
   X[nm]=z[nm].to_numpy();added+=1
  if added:joined.append({"path":str(p),"family":fam,"rule":rule,"features":added})
 except Exception as e:blocked.append({"path":str(p),"family":fam,"reason":"NORMALIZATION_ERROR:"+str(e)[:160]})
prog(3,14,f"joined tables={len(joined)} blocked={len(blocked)} raw external features={X.shape[1]}")
# Remove unusable/duplicate feature vectors, preserving provenance.
keep=[];seen={}
for c in X.columns:
 s=X[c];nn=s.notna().sum()
 if nn<100:continue
 arr=pd.util.hash_pandas_object(s.fillna(-9.87654321e307),index=False).values.tobytes();h=hashlib.sha256(arr).hexdigest()
 if h in seen:continue
 seen[h]=c;keep.append(c)
X=X[keep]
prog(4,14,f"usable unique external features={X.shape[1]}")
# Add causal transforms of external states: change, rolling rank/z-score on hourly carried state.
Z=pd.DataFrame(index=X.index)
for c in X.columns:
 s=X[c]
 Z[c]=s
 # state changes only where value actually changes; 24h/120h differences and long rolling z
 Z[c+"_d24h"]=s-s.shift(24)
 Z[c+"_d120h"]=s-s.shift(120)
 mu=s.rolling(24*60,min_periods=24*10).mean();sd=s.rolling(24*60,min_periods=24*10).std()
 Z[c+"_z60d"]=(s-mu)/sd.replace(0,np.nan)
prog(5,14,f"external transformed columns={Z.shape[1]}")
# Combine with V79 price state. Targets remain separate.
C=pd.concat([M,Z],axis=1)
C.to_parquet(O/"CAUSAL_STATE_MATRIX_2010_2013.parquet")
pd.DataFrame(joined).to_csv(O/"JOINED_SOURCE_TABLES.csv",index=False)
pd.DataFrame(blocked).to_csv(O/"BLOCKED_SOURCE_TABLES.csv",index=False)
prog(6,14,f"combined matrix rows={len(C):,} cols={C.shape[1]:,}")
# Family coverage
famcov=[]
for fam in sorted(set([x[2] for x in catalog])):
 js=[x for x in joined if x["family"]==fam];bs=[x for x in blocked if x["family"]==fam]
 famcov.append({"family":fam,"readable_tables":sum(1 for x in catalog if x[2]==fam),"joined_tables":len(js),"blocked_tables":len(bs),"joined_features":sum(x["features"] for x in js)})
pd.DataFrame(famcov).to_csv(O/"FAMILY_CAUSAL_COVERAGE.csv",index=False);prog(7,14,"family causal coverage written")
# Explicit blocked families: no silent imputation.
blocked_fams=sorted(set(x["family"] for x in blocked))
policy={"strict_backward_join":True,"future_fill":False,"targets_separate":True,"auto_join_rules":{"daily_market_series":"date + 1 day conservative","ALFRED":"realtime/vintage +1 day conservative","CFTC":"report/as-of date +3d21h conservative","Treasury_auctions":"auction_date +1 day conservative"},"not_auto_joined":["EIA without AVAILABLE_AT","BLS without exact release timestamp","FOMC documents without verified event table","ambiguous tables"],"warning":"Conservative lags protect causality but may sacrifice signal. Exact source release semantics should replace conservative rules before promotion."}
(O/"CAUSAL_JOIN_POLICY.json").write_text(json.dumps(policy,indent=2));prog(8,14,f"blocked families={blocked_fams}")
# Missingness + provenance
miss=pd.DataFrame({"feature":C.columns,"non_null":C.notna().sum().values,"coverage":C.notna().mean().values})
miss.to_csv(O/"FEATURE_COVERAGE.csv",index=False);prog(9,14,f"features coverage>=50%: {int((miss.coverage>=.5).sum())}")
# Pair-search input catalog: source family inferred from prefix; price gets market family.
fc=[]
for c in C.columns:
 fam="price_state"
 for f in ["alfred_vintage","cboe_vol","cfe_volume_oi","cftc","financial_conditions","fred","rates_yields","treasury_auctions"]:
  if c.startswith(f+"_"):fam=f;break
 fc.append({"feature":c,"family":fam,"coverage":float(C[c].notna().mean())})
pd.DataFrame(fc).to_csv(O/"FEATURE_CATALOG.csv",index=False);prog(10,14,"feature catalog ready for cross-family search")
# No return mining here.
manifest={"run_id":rid,"v79_run":V79.name,"rows":len(C),"price_features":M.shape[1],"external_features":Z.shape[1],"total_features":C.shape[1],"joined_tables":len(joined),"blocked_tables":len(blocked),"edge_trials":0,"2014_plus_accessed":False,"2023_plus_accessed":False,"protected_2026_accessed":False}
(O/"MATRIX_MANIFEST.json").write_text(json.dumps(manifest,indent=2));prog(11,14,"manifest written")
# Next-stage requirements are frozen now.
nextspec={"name":"V81_CROSS_SOURCE_CONCORDANCE_DISCOVERY","window":"2010-2013","input":"CAUSAL_STATE_MATRIX_2010_2013.parquet + V79 FUTURE_TARGETS","search":"cross-family pairs first","requirements":["minimum coverage","continuous rank/tertile/extreme encodings","incremental value vs each singleton","complete trial ledger","permutation/max-T or FDR","purged overlapping targets","no 2014+ access"],"triple_rule":"only components from replicated pair structures; not in V81"}
(O/"V81_FROZEN_SEARCH_PLAN.json").write_text(json.dumps(nextspec,indent=2));prog(12,14,"V81 cross-source plan frozen")
sha=hashlib.sha256((O/"CAUSAL_STATE_MATRIX_2010_2013.parquet").read_bytes()).hexdigest();prog(13,14,f"matrix SHA={sha[:16]}...")
receipt={"run_id":rid,"status":"COMPLETE_EXTERNAL_CAUSAL_JOIN_2010_2013","rows":len(C),"total_features":C.shape[1],"external_features":Z.shape[1],"joined_tables":len(joined),"blocked_tables":len(blocked),"matrix_sha256":sha,"edge_trials":0,"2014_plus_accessed":False,"2023_plus_accessed":False,"protected_2026_accessed":False,"next":"V81_CROSS_SOURCE_CONCORDANCE_DISCOVERY"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(14,14,"DONE; concordance discovery can start")
print("\n=== V80 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== FAMILY CAUSAL COVERAGE ===");print(pd.DataFrame(famcov).to_string(index=False));print("\n=== BLOCKED REASONS TOP ===");print(pd.DataFrame(blocked).groupby(["family","reason"]).size().sort_values(ascending=False).head(30).to_string() if blocked else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V80 compile failed"}
Write-Host "=== GEF V80 - EXTERNAL CAUSAL NORMALIZATION + JOIN ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V80 failed"}
