param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v40_impliedvol_replication.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");RAW=ROOT/"DataLake"/"raw"/"histdata";CBOE=ROOT/"DataLake"/"normalized"/"cboe_pre2023";V39=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v39";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v40";OUT.mkdir(parents=True,exist_ok=True)
t=time.time();rid="GEF40-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
EXPECTED="902c2fbebd8fd7732a4663986ca96d89b2014930e97fd5ef6d12e88459c53ca2"
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF40] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
runs=sorted([p for p in V39.glob("GEF39-*") if (p/"FROZEN_REPLICATION_CANDIDATES.csv").exists() and (p/"RUN_RECEIPT.json").exists()])
if not runs:raise RuntimeError("No V39")
src=runs[-1]; fp=src/"FROZEN_REPLICATION_CANDIDATES.csv"; sha=hashlib.sha256(fp.read_bytes()).hexdigest()
if sha!=EXPECTED:raise RuntimeError(f"V39 freeze mismatch {sha}")
F=pd.read_csv(fp)
if len(F)!=20:raise RuntimeError(f"Expected 20 frozen candidates, got {len(F)}")
prog(1,10,f"verified V39 freeze {sha[:12]} | 20 candidates")
spec={"VIX":("VIX_History_PRE2023.csv","CLOSE"),"VIX9D":("VIX9D_History_PRE2023.csv","CLOSE"),"VVIX":("VVIX_History_PRE2023.csv","VVIX"),"GVZ":("GVZ_History_PRE2023.csv","GVZ"),"OVX":("OVX_History_PRE2023.csv","OVX")}
ivs={}
for name,(fn,col) in spec.items():
 d=pd.read_csv(CBOE/fn);d["DATE"]=pd.to_datetime(d["DATE"]);s=pd.to_numeric(d[col],errors="coerce");s.index=d["DATE"];ivs[name]=s.sort_index()
prog(2,10,"loaded Cboe sources")
markets=sorted(F.target.unique());spot={}
for m in markets:
 z=[]
 # load prehistory 2010-13 only for rolling state, plus replication 2014-17
 for y0 in range(2010,2018):
  p=RAW/m/"M1"/f"{m}_M1_{y0}.parquet"
  if p.exists():
   d=pd.read_parquet(p);tc=next(c for c in d if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc]);z.append(d[["close"]])
 spot[m]=pd.concat(z).sort_index().close.resample("1D").last().dropna()
prog(3,10,"loaded spot through replication 2017; no 2018+")
def source_feature(source,feat):
 if source=="VIX9D/VIX":
  s=(ivs["VIX9D"]/ivs["VIX"]).replace([np.inf,-np.inf],np.nan)
  return s.shift(1)
 s=ivs[source]
 if feat=="level_pct":x=s.rolling(252,min_periods=126).rank(pct=True)
 elif feat=="chg1":x=s.pct_change()
 elif feat=="chg5":x=s.pct_change(5)
 elif feat=="z20":x=(s-s.rolling(20,min_periods=10).mean())/s.rolling(20,min_periods=10).std()
 else:raise RuntimeError(feat)
 return x.shift(1)
rows=[]
for j,r in F.iterrows():
 source,target,feat=str(r.source),str(r.target),str(r.feature);tail=float(r["tail"]);h=int(r["horizon_days"]);mode=str(r["mode"])
 x=source_feature(source,feat);a=spot[target];q=pd.concat([x.rename("x"),a.rename("px")],axis=1,join="inner").dropna();q=q[(q.index.year>=2014)&(q.index.year<=2017)]
 if feat=="level_pct":mask=q.x<=tail if tail==.10 else q.x>=tail
 else:
  # thresholds use complete causal feature history, then are sampled on replication dates
  lo=x.rolling(252,min_periods=126).quantile(.10).shift(1);hi=x.rolling(252,min_periods=126).quantile(.90).shift(1)
  mask=q.x<=lo.reindex(q.index) if tail==.10 else q.x>=hi.reindex(q.index)
 y=np.log(q.px.shift(-h)/q.px)*1e4;yy=y[mask].dropna();direction=1 if mode=="continuation" else -1;p=direction*(-1 if tail==.10 else 1)*yy;yrs=p.groupby(p.index.year).mean()
 rows.append({**{k:r[k] for k in ["source","target","feature","tail","horizon_days","mode"]},"n":len(p),"gross_bp":float(p.mean()) if len(p) else np.nan,"hit":float((p>0).mean()) if len(p) else np.nan,"posyears":float((yrs>0).mean()) if len(yrs) else 0,"years_present":len(yrs),"yearly":";".join(f"{int(k)}:{v:.6f}" for k,v in yrs.items())})
 prog(4+j//4,10,f"replicated {j+1}/20 | provisional positive={sum(x['gross_bp']>0 for x in rows)}")
R=pd.DataFrame(rows)
# replication gate predeclared: n>=60, positive mean, >=3/4 positive years, all 4 years present.
R["replication_pass"]=(R.n>=60)&(R.gross_bp>0)&(R.posyears>=.75)&(R.years_present==4)
R.to_csv(O/"REPLICATION_RESULTS.csv",index=False);S=R[R.replication_pass].copy();S.to_csv(O/"REPLICATION_SURVIVORS.csv",index=False)
surv_sha=hashlib.sha256((O/"REPLICATION_SURVIVORS.csv").read_bytes()).hexdigest()
receipt={"run_id":rid,"status":"COMPLETE","source_v39":src.name,"verified_freeze_sha256":sha,"replication_period":"2014-2017 only","candidate_count":20,"replication_pass_count":len(S),"survivor_sha256":surv_sha,"retuning":False,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(10,10,f"STOP | survivors {len(S)}/20 | 2018+ untouched")
print("\n=== V40 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== REPLICATION SURVIVORS ===");print(S.to_string(index=False) if len(S) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V40 compile failed"}
Write-Host "=== GEF V40 - IMPLIED VOL FROZEN REPLICATION ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V40 failed"}
