param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v78_total_multisource_audit.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,re,hashlib,time,os
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake"
OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v78"
rid="GEF78-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF78] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
def family(p):
 s=str(p).lower()
 rules=[("spot_m1",["histdata"]),("cboe_vol",["cboe","vix","vvix","vix9d","ovx","gvz"]),("cfe_volume_oi",["cfe"]),("cftc",["cftc"]),("rates_yields",["treasury","yield","breakeven"]),("alfred_vintage",["alfred"]),("fred",["fred"]),("financial_conditions",["financial_condition"]),("fomc_fed",["fomc","federal","/fed/","\\fed\\"]),("treasury_auctions",["auction"]),("eia_energy",["eia","wpsr"]),("bls_macro",["bls"]),("macro_calendar",["calendar","macro","release"])]
 for k,keys in rules:
  if any(x in s for x in keys):return k
 return "other"
prog(1,12,"TOTAL mode: recursive DataLake inventory; zero edge search")
files=[p for p in DL.rglob("*") if p.is_file()]
rows=[]
for p in files:
 try:sz=p.stat().st_size
 except:sz=None
 rows.append({"path":str(p),"family":family(p),"ext":p.suffix.lower(),"bytes":sz})
I=pd.DataFrame(rows);I.to_csv(O/"ALL_FILES.csv",index=False)
prog(2,12,f"files={len(I):,} bytes={int(I.bytes.fillna(0).sum()):,}")
summary=I.groupby("family").agg(files=("path","size"),bytes=("bytes","sum")).reset_index().sort_values("bytes",ascending=False)
summary.to_csv(O/"SOURCE_FAMILY_SUMMARY.csv",index=False);prog(3,12,f"families={len(summary)}")
# Inspect every tractable tabular schema, capped rows only. No return computation.
schemas=[];datecols=["available_at","published_at","publication_time","release_time","release_datetime","timestamp","datetime","date","time","observation_date","vintage_date","realtime_start"]
tabext={".csv",".parquet",".json",".jsonl",".xlsx",".xls"}
for j,r in I[I.ext.isin(tabext)].iterrows():
 p=Path(r.path)
 try:
  if p.suffix==".csv":d=pd.read_csv(p,nrows=8)
  elif p.suffix==".parquet":d=pd.read_parquet(p).head(8)
  elif p.suffix in [".xlsx",".xls"]:d=pd.read_excel(p,nrows=8)
  elif p.suffix==".json":
   obj=json.loads(p.read_text(encoding="utf-8",errors="ignore")[:1000000]);d=pd.DataFrame(obj[:8] if isinstance(obj,list) else [obj] if isinstance(obj,dict) else [])
  else:continue
  cols=[str(c) for c in d.columns];low=[c.lower() for c in cols]
  hits=[cols[i] for i,c in enumerate(low) if any(tok==c or tok in c for tok in datecols)]
  schemas.append({"path":str(p),"family":r.family,"columns":cols,"time_like_columns":hits,"sample_rows":len(d),"error":None})
 except Exception as e:schemas.append({"path":str(p),"family":r.family,"columns":[],"time_like_columns":[],"sample_rows":0,"error":str(e)[:240]})
(O/"TABULAR_SCHEMA_AUDIT.json").write_text(json.dumps(schemas,indent=2));prog(4,12,f"tabular schemas={len(schemas)}")
# Causal readiness registry: classify, never invent timestamps.
registry=[]
for fam in sorted(I.family.unique()):
 sf=[x for x in schemas if x["family"]==fam];hits=sorted(set(c for x in sf for c in x["time_like_columns"]))
 status="NEEDS_SEMANTIC_VERIFICATION"
 if fam=="spot_m1":status="PRICE_TIMESTAMP_AVAILABLE_VERIFY_SOURCE_TZ"
 elif fam=="alfred_vintage":status="VINTAGE_FIELDS_EXPECTED_VERIFY"
 elif fam=="eia_energy":status="BLOCKED_AVAILABLE_AT_NOT_BUILT"
 elif fam=="fomc_fed":status="PARTIAL_OFFICIAL_EVENT_TIMES_REQUIRE_EVENT_TABLE"
 registry.append({"family":fam,"files":int((I.family==fam).sum()),"timestamp_like_columns":hits,"causal_status":status})
pd.DataFrame(registry).to_csv(O/"CAUSAL_SOURCE_REGISTRY.csv",index=False);prog(5,12,"causal source registry built")
# Feature universe: explicit transforms to be generated only after causal alignment.
feature_plan={
"spot_m1":["returns 1/5/15/30/60/120/240m","realized vol","range","trend","mean-reversion state","session/hour/day","cross-market lagged returns","correlation/dispersion","relative strength"],
"cboe_vol":["level","change","zscore","percentile","term spreads VIX9D/VIX","VVIX/VIX","asset vol GVZ/OVX"],
"cfe_volume_oi":["volume level/change/zscore","open-interest level/change/zscore","volume/OI interactions"],
"cftc":["net positioning","weekly change","percentile","zscore","commercial/noncommercial spreads"],
"rates_yields":["nominal curve levels/slopes/changes","real yields","breakevens","rate differentials"],
"alfred_vintage":["vintage-correct macro level/change/surprise where forecast exists","macro regime"],
"fred":["non-vintage features only when revision-safe or lagged conservatively"],
"financial_conditions":["level/change/zscore/regime"],
"fomc_fed":["scheduled-event flag","statement timing","initial reaction","event x state interactions"],
"treasury_auctions":["auction event","tail/bid-cover/indirect-direct where present","event x rates state"],
"eia_energy":["BLOCKED until AVAILABLE_AT","inventory surprise/change after causal build"],
"bls_macro":["release event only after exact AVAILABLE_AT verification"],
"macro_calendar":["event flags after source-specific timestamp verification"]
}
(O/"FEATURE_UNIVERSE.json").write_text(json.dumps(feature_plan,indent=2));prog(6,12,"feature universe frozen")
# Concordance search architecture: hierarchical to control combinatorial explosion.
search={
"stage_A":"single features as baselines, not final objective",
"stage_B":"all causal cross-source PAIRS; require incremental value vs each component",
"stage_C":"TRIPLES only from replicated pair components; no arbitrary brute-force triples",
"state_encodings":["continuous rank/zscore","sign","tertiles","extreme tails predeclared"],
"targets":["+5m","+15m","+30m","+60m","+120m","+240m","session","J+1","sign","vol-scaled","path"],
"asymmetry":"long/short allowed",
"selection_control":["complete trial ledger","family-aware permutation/max-T or FDR","purged/embargoed overlap","neighbor stability","year stability","tail removal","cost/delay stress","negative controls"],
"temporal":["discovery 2010-2013","replication 2014-2017","validation 2018-2022","locked OOS 2023-2025","protected 2026"],
"hard_rule":"No 2014+ feature/threshold/model selection during discovery; no 2023+ before immutable pre-OOS gate."
}
(O/"CONCORDANCE_SEARCH_PROTOCOL.json").write_text(json.dumps(search,indent=2));prog(7,12,"multi-source concordance protocol frozen")
# Build join plan: each family must expose AVAILABLE_AT semantics before inclusion.
joinplan=[]
for r in registry:
 joinplan.append({"family":r["family"],"join_key":"latest record with AVAILABLE_AT <= decision_time","causal_status":r["causal_status"],"eligible_now":r["causal_status"] not in ["BLOCKED_AVAILABLE_AT_NOT_BUILT"]})
pd.DataFrame(joinplan).to_csv(O/"CAUSAL_JOIN_PLAN.csv",index=False);prog(8,12,"causal join plan built")
# Produce machine-readable work queue; prioritize verification/build, not hand-picked alpha hypotheses.
queue=[]
for r in registry:
 queue.append({"family":r["family"],"action":"VERIFY_AVAILABLE_AT_AND_NORMALIZE","status":r["causal_status"]})
queue += [{"family":"ALL_CAUSAL","action":"BUILD_2010_2013_CAUSAL_STATE_MATRIX","status":"PENDING"},
{"family":"ALL_CAUSAL","action":"GENERATE_FEATURES_WITH_PROVENANCE","status":"PENDING"},
{"family":"ALL_CAUSAL","action":"RUN_PAIRWISE_CONCORDANCE_DISCOVERY","status":"BLOCKED_UNTIL_MATRIX"},
{"family":"ALL_CAUSAL","action":"FREEZE_AND_REPLICATE_2014_2017","status":"BLOCKED_UNTIL_DISCOVERY"}]
pd.DataFrame(queue).to_csv(O/"WORK_QUEUE.csv",index=False);prog(9,12,"work queue written")
# Coverage diagnostics by family/path names; conservative year inference only.
cov=[]
for _,r in I.iterrows():
 ys=[int(x) for x in re.findall(r"(?<!\d)(20\d{2}|19\d{2})(?!\d)",Path(r.path).name)]
 cov.append({"family":r.family,"path":r.path,"years_in_filename":sorted(set(ys))})
(O/"FILENAME_YEAR_COVERAGE.json").write_text(json.dumps(cov,indent=2));prog(10,12,"coverage diagnostics written")
manifest={"run_id":rid,"mode":"TOTAL_MULTISOURCE_CAUSAL_ARCHITECTURE","source_families":summary.to_dict("records"),"feature_universe_sha256":hashlib.sha256((O/"FEATURE_UNIVERSE.json").read_bytes()).hexdigest(),"protocol_sha256":hashlib.sha256((O/"CONCORDANCE_SEARCH_PROTOCOL.json").read_bytes()).hexdigest(),"edge_trials":0,"market_returns_tested":False,"oos_2023_2025_accessed":False,"protected_2026_accessed":False}
(O/"ARCHITECTURE_MANIFEST.json").write_text(json.dumps(manifest,indent=2));prog(11,12,"architecture manifest hashed")
receipt={"run_id":rid,"status":"COMPLETE_TOTAL_MULTISOURCE_AUDIT_AND_ARCHITECTURE","files":len(I),"families":len(summary),"edge_trials":0,"market_returns_tested":False,"oos_2023_2025_accessed":False,"protected_2026_accessed":False,"next":"V79_CAUSAL_NORMALIZATION_AND_STATE_MATRIX_2010_2013"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(12,12,"DONE; ready for causal normalization")
print("\n=== V78 RECEIPT ===");print(json.dumps(receipt,indent=2))
print("\n=== SOURCE FAMILY SUMMARY ===");print(summary.to_string(index=False))
print("\n=== CAUSAL SOURCE REGISTRY ===");print(pd.DataFrame(registry).to_string(index=False))
print("\n=== WORK QUEUE ===");print(pd.DataFrame(queue).to_string(index=False))
print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V78 compile failed"}
Write-Host "=== GEF V78 - TOTAL MULTISOURCE CAUSAL AUDIT ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V78 failed"}
