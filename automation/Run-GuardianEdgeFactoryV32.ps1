param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v32_regime_discovery.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");RAW=ROOT/"DataLake"/"raw"/"histdata";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v32";OUT.mkdir(parents=True,exist_ok=True)
started=time.time();rid="GEF32-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
MARKETS=["XAUUSD","XAGUSD","SPXUSD","NSXUSD","WTIUSD","EURUSD","GBPUSD","USDJPY"];H=[30,60,120,240]
def prog(i,n,msg):
 e=time.time()-started;eta=e/i*(n-i) if i else 0;print(f"[GEF32] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
def load(m):
 z=[]
 for y in range(2010,2014):
  p=RAW/m/"M1"/f"{m}_M1_{y}.parquet"
  if p.exists():
   d=pd.read_parquet(p);tc=next(c for c in d if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc]);z.append(d[["close"]].sort_index().resample("15min",label="right",closed="left").last().dropna())
 return pd.concat(z).sort_index().close if z else pd.Series(dtype=float)
prog(1,11,"new phenomenon: volatility-regime conditional continuation/reversal; discovery 2010-2013 only")
rows=[]
for mi,m in enumerate(MARKETS):
 a=load(m);ret=np.log(a/a.shift(1));rv=ret.rolling(16,min_periods=16).std();rvslow=rv.rolling(20*16,min_periods=80).median();ratio=rv/rvslow
 # Regimes fixed a priori, not optimized: compressed <=0.75, normal 0.75-1.5, expanded >=1.5.
 regimes={"compressed":ratio<=.75,"normal":(ratio>.75)&(ratio<1.5),"expanded":ratio>=1.5}
 # Shock fixed a priori: |1-bar return| >= rolling 95th percentile using past-only 20 trading days, shifted one bar.
 shock=ret.abs()>=ret.abs().rolling(20*96,min_periods=480).quantile(.95).shift(1)
 for reg,mask in regimes.items():
  for h in H:
   y=np.log(a.shift(-h//15)/a)*1e4;q=pd.concat([ret.rename("r"),y.rename("y"),mask.rename("reg"),shock.rename("shock")],axis=1).dropna();q=q[q.reg&q.shock]
   for mode,direction in [("continuation",1),("reversal",-1)]:
    p=direction*np.sign(q.r)*q.y;yrs=p.groupby(p.index.year).mean()
    rows.append({"market":m,"regime":reg,"horizon_min":h,"mode":mode,"n":len(p),"gross_bp":float(p.mean()) if len(p) else np.nan,"hit":float((p>0).mean()) if len(p) else np.nan,"posyears":float((yrs>0).mean()) if len(yrs) else 0})
 prog(mi+2,11,f"{m} complete")
R=pd.DataFrame(rows);R.to_csv(O/"DISCOVERY_GRID.csv",index=False)
# Broad screen, then freeze diverse max 16: positive, n>=300, >=3/4 positive years; one best per market/regime/mode.
S=R[(R.n>=300)&(R.gross_bp>0)&(R.posyears>=.75)].copy();F=S.sort_values("gross_bp",ascending=False).drop_duplicates(["market","regime","mode"]).head(16).copy();F["selection_period"]="2010-2013";F.to_csv(O/"FROZEN_REPLICATION_CANDIDATES.csv",index=False)
prog(10,11,f"screen {len(S)} survivors; freeze {len(F)} diverse candidates")
receipt={"run_id":rid,"status":"COMPLETE","lineage":"volatility-regime conditional shock continuation/reversal","discovery_period":"2010-2013 only","markets":MARKETS,"bar_minutes":15,"regime_definition":{"compressed":"RV16 / past median RV <= 0.75","normal":"0.75 < ratio < 1.5","expanded":"ratio >= 1.5"},"shock_definition":"absolute M15 return >= past-only rolling 20-day 95th percentile, threshold shifted one bar","horizons_min":H,"directions":["continuation","reversal"],"cells":len(R),"screen_survivors":len(S),"frozen_count":len(F),"replication_2014_2017_accessed":False,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(11,11,"STOP - 2014+ untouched");print("\n=== V32 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== FROZEN FOR REPLICATION ===");print(F.to_string(index=False));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V32 compile failed"}
Write-Host "=== GEF V32 - REGIME/SHOCK DISCOVERY ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V32 failed"}
