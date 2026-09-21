param([string]$Root="D:\MT5_Backtests",[switch]$Full)
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v81b_audit_and_benchmark.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,re,time,hashlib,sys
ROOT=Path(r"D:\MT5_Backtests"); DL=ROOT/"DataLake"
V80C=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v80c").glob("GEF80C-*"))[-1]
V79=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v79").glob("GEF79-*"))[-1]
X=pd.read_parquet(V80C/"CAUSAL_STATE_MATRIX_2010_2013_FULL.parquet"); X.index=pd.to_datetime(X.index)
Y=pd.read_parquet(V79/"FUTURE_TARGETS_2010_2013.parquet").reindex(X.index)
rid="GEF81B-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
O=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v81b"/rid; O.mkdir(parents=True,exist_ok=True)
t0=time.time()
def status(stage,msg,**kw):
 d={"run_id":rid,"stage":stage,"elapsed_s":round(time.time()-t0,2),"message":msg,**kw}
 (O/"LIVE_STATUS.json").write_text(json.dumps(d,indent=2),encoding="utf-8")
 print("[GEF81B]",json.dumps(d),flush=True)
status("AUDIT","starting; no return mining yet",rows=len(X),cols=X.shape[1])
# Audit actual matrix prefixes first. Never call it full if mandatory families are absent.
prefixes=["cftc_","rates_yields_","fred_","alfred_","cboe_vol_","cfe_","financial_conditions_","treasury_auctions_"]
counts={p.rstrip("_"):sum(str(c).startswith(p) for c in X.columns) for p in prefixes}
# Revised FRED is not vintage-safe merely because observation_date was lagged one day.
unsafe_fred=[c for c in X.columns if str(c).startswith("fred_")]
missing=[k for k in ["cftc","rates_yields"] if counts.get(k,0)==0]
audit={"matrix":str(V80C/"CAUSAL_STATE_MATRIX_2010_2013_FULL.parquet"),"family_counts":counts,
       "mandatory_missing":missing,"revised_fred_columns_quarantined":len(unsafe_fred),
       "hourly_targets_only":all(str(c).endswith("h") for c in Y.columns),
       "scientific_decision":"DO_NOT_FREEZE_V81_CANDIDATES; repair source coverage and build minute target layer before definitive concordance discovery"}
(O/"ARCHITECTURE_AUDIT.json").write_text(json.dumps(audit,indent=2),encoding="utf-8")
status("AUDIT_COMPLETE","matrix audited",**audit)
# Safe benchmark subset: exclude revised FRED; label price by market so cross-asset price pairs are legal.
def family(c):
 s=str(c)
 for p in ["cftc","rates_yields","alfred","cboe_vol","cfe","financial_conditions","treasury_auctions"]:
  if s.startswith(p+"_"): return p
 m=re.match(r"^([A-Z]{3,6}USD)_",s)
 if m:return "price_"+m.group(1)
 return "price_derived"
cols=[]
for c in X.columns:
 if str(c).startswith("fred_") or str(c).endswith("_px"):continue
 s=pd.to_numeric(X[c],errors="coerce")
 if s.notna().mean()>=.50 and s.nunique(dropna=True)>=10:cols.append(c)
# Build causal states once as dense numpy bool arrays.
states={}
for c in cols:
 s=pd.to_numeric(X[c],errors="coerce")
 mu=s.expanding(min_periods=500).mean().shift(1); sd=s.expanding(min_periods=500).std().shift(1).replace(0,np.nan)
 z=((s-mu)/sd).to_numpy()
 states[c]=(np.nan_to_num(z<=-1,nan=False),np.nan_to_num(z>=1,nan=False))
targets=[c for c in Y.columns if re.search(r"_fwd_(1|5|15|30|60|120|240)h$",str(c))]
YA=np.column_stack([pd.to_numeric(Y[c],errors="coerce").to_numpy(dtype=float) for c in targets])
valid=np.isfinite(YA)
pairs=[(a,b) for i,a in enumerate(cols) for b in cols[i+1:] if family(a)!=family(b)]
bench=min(1000,len(pairs)); trials=0; provisional=0; bt=time.time()
for k,(a,b) in enumerate(pairs[:bench],1):
 for ma in states[a]:
  for mb in states[b]:
   m=ma & mb
   if m.sum()<80:continue
   q=valid & m[:,None]; n=q.sum(axis=0)
   good=n>=80
   if not good.any():continue
   sums=np.where(q,YA,0.0).sum(axis=0); means=np.divide(sums,n,out=np.full(len(targets),np.nan),where=n>0)
   pos=((YA>0)&q).sum(axis=0); hits=np.divide(pos,n,out=np.full(len(targets),np.nan),where=n>0)
   trials+=int(good.sum()); provisional+=int((good & (np.abs(means)*1e4>=2) & (np.maximum(hits,1-hits)>=.57)).sum())
 if k%100==0:
  rate=k/max(time.time()-bt,1e-9); eta=(len(pairs)-k)/rate
  status("BENCHMARK",f"{k}/{bench} benchmark pairs",benchmark_pairs=k,total_pairs=len(pairs),pairs_per_s=round(rate,3),projected_full_minutes=round(len(pairs)/rate/60,1),trials=trials,provisional=provisional)
elapsed=time.time()-bt; rate=bench/max(elapsed,1e-9); projected=len(pairs)/rate/60
receipt={"run_id":rid,"status":"BENCHMARK_COMPLETE","eligible_safe_features":len(cols),"cross_family_pairs":len(pairs),
         "benchmark_pairs":bench,"benchmark_seconds":elapsed,"pairs_per_second":rate,"projected_full_minutes":projected,
         "trials":trials,"provisional":provisional,"full_run_executed":False,
         "2014_plus_accessed":False,"2023_plus_accessed":False,"protected_2026_accessed":False,
         "blocking_issues":["missing CFTC/rates in V80C matrix" if missing else None,
                            "revised FRED quarantined","minute-horizon target layer not yet built"]}
receipt["blocking_issues"]=[x for x in receipt["blocking_issues"] if x]
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
status("DONE","benchmark only; intentionally stops before full scan",**receipt)
print("\n=== V81B AUDIT ===");print(json.dumps(audit,indent=2))
print("\n=== V81B BENCHMARK RECEIPT ===");print(json.dumps(receipt,indent=2))
print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V81B compile failed"}
Write-Host "=== GEF V81B - ARCHITECTURE AUDIT + VECTORIZED BENCHMARK ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V81B failed"}
