param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v29_xag_clean_lineage.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); RAW=ROOT/"DataLake"/"raw"/"histdata"; OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v29";OUT.mkdir(parents=True,exist_ok=True)
started=time.time(); rid="GEF29-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"); O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-started;eta=e/i*(n-i) if i else 0;print(f"[GEF29] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
def load(y):
 p=RAW/"XAGUSD"/"M1"/f"XAGUSD_M1_{y}.parquet"
 if not p.exists(): return None
 d=pd.read_parquet(p);tc=next(c for c in d if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc])
 return d[["close"]].sort_index().resample("5min",label="right",closed="left").last().dropna()
prog(1,6,"load XAG discovery 2010-2013 ONLY")
ds=[load(y) for y in range(2010,2014)]; a=pd.concat([x for x in ds if x is not None]).sort_index().close
# New lineage: XAG-only past returns. No XAU. No 2014+ access.
windows=[3,6,12,24,48]; horizons=[30,60,120,240]; tails=[.95,.975,.99,.995]
rows=[]; total=len(windows)*len(horizons)*len(tails);k=0
prog(2,6,f"discovery grid {total} cells")
for w in windows:
 x=np.log(a/a.shift(w))
 for h in horizons:
  y=np.log(a.shift(-h//5)/a)*1e4
  q=pd.concat([x.rename("x"),y.rename("y")],axis=1).dropna()
  for tail in tails:
   k+=1;thr=float(q.x.abs().quantile(tail));sel=q[q.x.abs()>=thr]
   # Predeclared mean-reversion only; no direction search.
   p=-np.sign(sel.x)*sel.y
   yrs=p.groupby(p.index.year).mean()
   rows.append({"window_bars":w,"window_min":w*5,"horizon_min":h,"tail":tail,"threshold_abs":thr,"n":len(p),"gross_bp":float(p.mean()),"hit":float((p>0).mean()),"posyears":float((yrs>0).mean())})
R=pd.DataFrame(rows);R.to_csv(O/"DISCOVERY_GRID.csv",index=False)
prog(3,6,"apply discovery screen")
# Broad discovery only. Require enough observations, positive effect, >=3/4 positive years.
S=R[(R.n>=300)&(R.gross_bp>0)&(R.posyears>=.75)].copy()
# Freeze a diverse small set WITHOUT reading 2014+: best per (window,horizon), then top 12 by gross.
F=S.sort_values("gross_bp",ascending=False).drop_duplicates(["window_bars","horizon_min"]).head(12).copy()
F["direction"]=-1;F["feature"]="XAG_ret";F["selection_period"]="2010-2013"
F.to_csv(O/"FROZEN_REPLICATION_CANDIDATES.csv",index=False)
prog(4,6,f"freeze {len(F)} candidates for later replication")
manifest={"run_id":rid,"lineage":"XAG-only extreme-return mean reversion","hypothesis":"Extreme XAGUSD 5-minute-bar cumulative returns mean-revert over subsequent 30-240 minutes.","discovery_period":"2010-2013 only","replication_2014_2017_accessed":False,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"grid":{"windows_bars":windows,"horizons_min":horizons,"tails":tails,"direction":"mean reversion only"},"cells":total,"screen_survivors":len(S),"frozen_count":len(F),"anti_contamination":"V28 motivated the XAG-only hypothesis, but V29 does not import V28 thresholds, event timestamps, quadrant rules, or XAU information. Parameters are selected solely from 2010-2013 XAG data."}
(O/"RUN_RECEIPT.json").write_text(json.dumps(manifest,indent=2))
sha=hashlib.sha256((O/"FROZEN_REPLICATION_CANDIDATES.csv").read_bytes()).hexdigest();manifest["freeze_sha256"]=sha;(O/"RUN_RECEIPT.json").write_text(json.dumps(manifest,indent=2))
prog(5,6,"write immutable freeze hash")
print("\n=== V29 RECEIPT ===");print(json.dumps(manifest,indent=2));print("\n=== FROZEN FOR REPLICATION ===");print(F.to_string(index=False))
prog(6,6,"STOP - 2014+ untouched");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V29 compile failed"}
Write-Host "=== GEF V29 - CLEAN XAG MEAN-REVERSION LINEAGE ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V29 failed"}
