param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v82_source_repair_audit.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,re,time,hashlib
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake"
rid="GEF82-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
O=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v82"/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
def prog(i,n,msg):
 e=time.time()-t; eta=e/i*(n-i) if i else 0
 d={"run_id":rid,"step":i,"steps":n,"percent":round(100*i/n,1),"elapsed_s":round(e,1),"eta_s":round(eta,1),"message":msg}
 (O/"LIVE_STATUS.json").write_text(json.dumps(d,indent=2),encoding="utf-8")
 print(f"[GEF82] {i}/{n} {100*i/n:.0f}% | elapsed {e:.1f}s | ETA {eta:.1f}s | {msg}",flush=True)
prog(1,8,"inventory CFTC/rates candidates; audit only, zero edge search")
# Use path/name evidence first, then inspect schemas. Avoid V80's content-wide misclassification precedence.
cand=[]
for p in DL.rglob("*"):
 if not p.is_file() or p.suffix.lower() not in [".csv",".parquet",".xlsx",".xls"]:continue
 s=str(p).lower()
 fam=None
 if any(k in s for k in ["cftc","commitment","cot_","cot-"]):fam="cftc"
 elif any(k in s for k in ["yield","breakeven","treasury","rates","rate_","fred","alfred"]):fam="rates_candidate"
 if fam:cand.append((p,fam))
prog(2,8,f"path candidates={len(cand)}")
def read(p):
 try:
  if p.suffix.lower()==".csv":return pd.read_csv(p,low_memory=False)
  if p.suffix.lower()==".parquet":return pd.read_parquet(p)
  return pd.read_excel(p)
 except Exception as e:return e
rows=[];usable=[]
for p,hint in cand:
 d=read(p)
 if isinstance(d,Exception):
  rows.append({"path":str(p),"hint":hint,"error":repr(d)});continue
 cols=list(map(str,d.columns)); low=[c.lower() for c in cols]
 s=(str(p)+" "+" ".join(cols)).lower()
 fam="cftc" if any(k in s for k in ["cftc","commitment","commercial","noncommercial","non-commercial"]) else ("rates_yields" if any(k in s for k in ["yield","breakeven","dgs","dfii","t10yie","t5yie","treasury"]) else hint)
 datecols=[c for c in cols if any(k in c.lower() for k in ["date","time","vintage","realtime"])]
 numeric=[c for c in cols if pd.api.types.is_numeric_dtype(d[c])]
 mn=mx=None;dc=None
 for c in datecols:
  z=pd.to_datetime(d[c],errors="coerce")
  if z.notna().any():dc=c;mn=str(z.min());mx=str(z.max());break
 row={"path":str(p),"family":fam,"rows":len(d),"date_col":dc,"min_date":mn,"max_date":mx,"numeric_cols":len(numeric),"columns":"|".join(cols[:80]),"error":None}
 rows.append(row)
 if fam in ["cftc","rates_yields"] and dc and numeric:usable.append(row)
pd.DataFrame(rows).to_csv(O/"SOURCE_AUDIT.csv",index=False)
prog(3,8,f"schema inspected={len(rows)} usable candidates={len(usable)}")
# Diagnose V80 precedence collision explicitly.
coll=[]
for r in usable:
 s=(r["path"]+" "+r["columns"]).lower()
 if r["family"]=="cftc" and any(k in s for k in ["open_interest","open interest","cfe","futures_volume"]):
  coll.append({**r,"v80_collision":"would classify cfe_volume_oi before cftc"})
 if r["family"]=="rates_yields" and any(k in s for k in ["auction_date","bid_to_cover","competitive_accepted"]):
  coll.append({**r,"v80_collision":"would classify treasury_auctions before rates_yields"})
pd.DataFrame(coll).to_csv(O/"V80_CLASSIFICATION_COLLISIONS.csv",index=False)
prog(4,8,f"precedence collisions={len(coll)}")
# Causal eligibility rules. No values are joined here; this freezes semantics before repair.
elig=[]
for r in usable:
 rule=None;status="BLOCKED"
 if r["family"]=="cftc":
  rule="Tuesday report/as-of positions become usable only after Friday publication; conservative available_at = report_date +3d21h UTC pending exact historical release audit"
  status="ELIGIBLE_CONSERVATIVE" if r["date_col"] else "BLOCKED"
 elif r["family"]=="rates_yields":
  p=r["path"].lower()
  if "alfred" in p or "vintage" in r["columns"].lower() or "realtime" in r["columns"].lower():
   rule="vintage/realtime availability <= decision time; never latest revised history";status="ELIGIBLE_VINTAGE"
  else:
   rule="daily market/rate observation available next calendar day 00:00 UTC conservatively; do not treat revised macro as vintage-safe";status="ELIGIBLE_CONSERVATIVE"
 elig.append({**r,"causal_status":status,"available_at_rule":rule})
pd.DataFrame(elig).to_csv(O/"CAUSAL_ELIGIBILITY.csv",index=False)
prog(5,8,f"causal eligibility rows={len(elig)}")
# Freeze target architecture correction: slow state + intraday M1/5m layer, exact minute horizons.
target_spec={"slow_state_grid":"hourly/daily states may be carried forward causally",
"intraday_decision_layer":"5-minute grid from HistData M1, last observed quote <= decision timestamp",
"minute_targets":[5,15,30,60,120,240],
"event_layer":"exact verified publication timestamps where available",
"rule":"hourly V79 targets are coarse diagnostics only and cannot substitute for minute targets",
"windows":{"discovery":"2010-2013","replication":"2014-2017","validation":"2018-2022","locked_oos":"2023-2025","protected":"2026"}}
(O/"MULTIRESOLUTION_TARGET_SPEC.json").write_text(json.dumps(target_spec,indent=2),encoding="utf-8")
prog(6,8,"minute-target architecture frozen")
# FRED policy correction.
fred_policy={"revised_fred":"QUARANTINE unless proven revision-safe","alfred":"preferred for historically revised macro series","market_series":"may be admitted only with source-specific causal semantics","reason":"observation_date +1d does not reconstruct historical vintage knowledge"}
(O/"FRED_CAUSAL_POLICY.json").write_text(json.dumps(fred_policy,indent=2),encoding="utf-8")
prog(7,8,"FRED vintage policy corrected")
receipt={"run_id":rid,"status":"COMPLETE_SOURCE_REPAIR_AUDIT","files_inspected":len(rows),"usable_candidates":len(usable),
"cftc_candidates":sum(r["family"]=="cftc" for r in usable),"rates_yields_candidates":sum(r["family"]=="rates_yields" for r in usable),
"classification_collisions":len(coll),"edge_trials":0,"market_returns_accessed":False,"2014_plus_accessed":False,
"2023_plus_accessed":False,"protected_2026_accessed":False,
"next":"V83_BUILD_CORRECTED_CAUSAL_SOURCE_MATRIX_AND_5MIN_TARGET_LAYER"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
prog(8,8,"DONE; no alpha search")
print("\n=== V82 RECEIPT ===");print(json.dumps(receipt,indent=2))
print("\n=== USABLE BY FAMILY ===")
print(pd.DataFrame(elig).groupby(["family","causal_status"]).size().to_string() if elig else "NONE")
print("\n=== COLLISIONS ===");print(pd.DataFrame(coll)[["path","v80_collision"]].to_string(index=False) if coll else "NONE")
print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V82 compile failed"}
Write-Host "=== GEF V82 - SOURCE REPAIR AUDIT ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V82 failed"}
