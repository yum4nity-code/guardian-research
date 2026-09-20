param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v22_alignment_audit.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");RAW=ROOT/"DataLake"/"raw"/"histdata";V21B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v21";OUTB=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v22";OUTB.mkdir(parents=True,exist_ok=True)
started=time.time(); runs=sorted([p for p in V21B.glob("GEF21-*") if (p/"REPLICATION_PASSES.csv").exists()])
if not runs: raise RuntimeError("No V21 passes")
src=runs[-1];F=pd.read_csv(src/"REPLICATION_PASSES.csv")
rid="GEF22-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUTB/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-started;eta=e/i*(n-i) if i else 0
 print(f"[GEF22] {i}/{n} {100*i/n:6.2f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
 (O/"STATUS.json").write_text(json.dumps({"done":i,"total":n,"pct":100*i/n,"elapsed_s":e,"eta_s":eta,"message":msg},indent=2))
def raw(m,y):
 p=RAW/m/"M1"/f"{m}_M1_{y}.parquet"
 if not p.exists(): return None
 d=pd.read_parquet(p);tc=next(c for c in d.columns if c.lower() in ("datetime","time","timestamp"));t=pd.to_datetime(d[tc])
 return pd.DataFrame({"t":t,"close":pd.to_numeric(d["close"],errors="coerce")}).dropna().sort_values("t").drop_duplicates("t")
# audit only 2014-2017, no later data
pairs=F[["target","driver"]].drop_duplicates().reset_index(drop=True); rows=[]
for i,r in pairs.iterrows():
 a=[];b=[]
 for y in range(2014,2018):
  x=raw(r["target"],y);z=raw(r["driver"],y)
  if x is not None:a.append(x)
  if z is not None:b.append(z)
 A=pd.concat(a).set_index("t");B=pd.concat(b).set_index("t")
 ia=A.index;ib=B.index; inter=ia.intersection(ib)
 # exact M1 overlap and systematic nearest timestamp offsets
 sample=ia[::max(1,len(ia)//20000)]
 pos=ib.searchsorted(sample)
 diffs=[]
 for t,j in zip(sample,pos):
  cand=[]
  if j<len(ib):cand.append(abs((ib[j]-t).total_seconds()/60))
  if j>0:cand.append(abs((ib[j-1]-t).total_seconds()/60))
  if cand:diffs.append(min(cand))
 # 5m right-edge bar availability overlap
 ar=A.close.resample("5min",label="right",closed="left").last().dropna()
 br=B.close.resample("5min",label="right",closed="left").last().dropna()
 bi=ar.index.intersection(br.index)
 rows.append({"target":r["target"],"driver":r["driver"],"target_m1":len(A),"driver_m1":len(B),"exact_m1_overlap":len(inter),
 "target_exact_overlap_frac":len(inter)/len(A),"driver_exact_overlap_frac":len(inter)/len(B),
 "nearest_offset_median_min":float(np.median(diffs)) if diffs else np.nan,"nearest_offset_p99_min":float(np.quantile(diffs,.99)) if diffs else np.nan,
 "target_m5":len(ar),"driver_m5":len(br),"exact_m5_overlap":len(bi),"target_m5_overlap_frac":len(bi)/len(ar),"driver_m5_overlap_frac":len(bi)/len(br)})
 prog(i+1,len(pairs),f'{r["target"]} <-> {r["driver"]}')
R=pd.DataFrame(rows)
# Conservative alignment gate: exact timestamps dominate and nearest offsets are zero at median.
R["alignment_pass"]=(R.target_m5_overlap_frac>=.90)&(R.driver_m5_overlap_frac>=.90)&(R.nearest_offset_median_min==0)
R.to_csv(O/"PAIR_ALIGNMENT_AUDIT.csv",index=False)
P=F.merge(R[["target","driver","alignment_pass"]],on=["target","driver"],how="left")
P=P[P.alignment_pass==True].copy();P.to_csv(O/"ALIGNMENT_CLEARED_CANDIDATES.csv",index=False)
receipt={"run_id":rid,"status":"COMPLETE","source_v21":src.name,"audit_period":"2014-2017 only","validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"v21_passes":len(F),"unique_pairs":len(pairs),"alignment_cleared_candidates":len(P),"gate":"both markets >=90% exact common right-edge M5 labels; nearest raw M1 offset median=0","limitations":"This tests timestamp-grid compatibility and overlap, not vendor timezone truth or exchange-session economic equivalence. Cross-market signals remain provisional.","next_gate":"Only alignment-cleared candidates may proceed to stronger pre-validation robustness on 2010-2017. Do not open 2018+ yet.","errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
print("\n=== V22 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== PAIR ALIGNMENT ===");print(R.to_string(index=False));print("\n=== CLEARED CANDIDATES ===");print(P[["target","driver","feature","horizon_min","tail","rep_gross_bp","rep_posyears"]].to_string(index=False) if len(P) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V22 compile failed"}
Write-Host "=== GEF V22 - CROSS-MARKET ALIGNMENT AUDIT 2014-2017 ONLY ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V22 run failed"}
