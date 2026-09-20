param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v39_impliedvol_discovery.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); RAW=ROOT/"DataLake"/"raw"/"histdata"; CBOE=ROOT/"DataLake"/"normalized"/"cboe_pre2023"; V38=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v38"; OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v39";OUT.mkdir(parents=True,exist_ok=True)
t=time.time();rid="GEF39-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
EXPECTED="55cc16eb815dd45d6c1965c0348ba278a0014a699dd616e0ed6a803a870c8b89"
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF39] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
vr=sorted([p for p in V38.glob("GEF38-*") if (p/"PREDECLARED_DISCOVERY_DESIGN.json").exists() and (p/"RUN_RECEIPT.json").exists()])
if not vr:raise RuntimeError("No V38 audit")
design=vr[-1]/"PREDECLARED_DISCOVERY_DESIGN.json"; sha=hashlib.sha256(design.read_bytes()).hexdigest()
if sha!=EXPECTED:raise RuntimeError(f"V38 design hash mismatch {sha}")
prog(1,10,f"V38 design verified {sha[:12]}")
spec={"VIX":("VIX_History_PRE2023.csv","CLOSE",["SPXUSD","NSXUSD"]),"VIX9D":("VIX9D_History_PRE2023.csv","CLOSE",["SPXUSD","NSXUSD"]),"VVIX":("VVIX_History_PRE2023.csv","VVIX",["SPXUSD","NSXUSD"]),"GVZ":("GVZ_History_PRE2023.csv","GVZ",["XAUUSD"]),"OVX":("OVX_History_PRE2023.csv","OVX",["WTIUSD"])}
ivs={}
for name,(fn,col,targets) in spec.items():
 d=pd.read_csv(CBOE/fn); d["DATE"]=pd.to_datetime(d["DATE"]); s=pd.to_numeric(d[col],errors="coerce"); s.index=d["DATE"]; ivs[name]=s.sort_index()
prog(2,10,"loaded normalized Cboe daily series")
# daily spot close; signal from Cboe date D is deliberately shifted to next spot trading observation before use.
spot={}
for m in sorted(set(x for _,_,ts in spec.values() for x in ts)):
 z=[]
 for y in range(2010,2014):
  p=RAW/m/"M1"/f"{m}_M1_{y}.parquet"
  if not p.exists():continue
  d=pd.read_parquet(p);tc=next(c for c in d if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc]);z.append(d[["close"]])
 a=pd.concat(z).sort_index().close.resample("1D").last().dropna();spot[m]=a
prog(3,10,"loaded discovery spot 2010-2013 only")
rows=[]
for name,(fn,col,targets) in spec.items():
 s=ivs[name]
 # compute features on full past history, then restrict signal dates to 2010-13; all are lagged one observation before joining.
 pct=s.rolling(252,min_periods=126).rank(pct=True)
 z20=(s-s.rolling(20,min_periods=10).mean())/s.rolling(20,min_periods=10).std()
 feats={"level_pct":pct,"chg1":s.pct_change(),"chg5":s.pct_change(5),"z20":z20}
 for m in targets:
  a=spot[m]
  for feat,x0 in feats.items():
   x=x0.shift(1) # mandatory next-observation causal lag
   q=pd.concat([x.rename("x"),a.rename("px")],axis=1,join="inner").dropna()
   q=q[(q.index.year>=2010)&(q.index.year<=2013)]
   for h in [1,5]:
    y=np.log(q.px.shift(-h)/q.px)*1e4
    for tail in [.10,.90]:
     if feat in ("level_pct",):
      mask=q.x<=tail if tail==.10 else q.x>=tail
     else:
      lo=q.x.rolling(252,min_periods=126).quantile(.10).shift(1);hi=q.x.rolling(252,min_periods=126).quantile(.90).shift(1);mask=q.x<=lo if tail==.10 else q.x>=hi
     yy=y[mask].dropna()
     for mode,direction in [("continuation",1),("reversal",-1)]:
      # state sign: low/negative tail=-1, high/positive tail=+1
      p=direction*(-1 if tail==.10 else 1)*yy; yrs=p.groupby(p.index.year).mean()
      rows.append({"source":name,"target":m,"feature":feat,"tail":tail,"horizon_days":h,"mode":mode,"n":len(p),"gross_bp":float(p.mean()) if len(p) else np.nan,"hit":float((p>0).mean()) if len(p) else np.nan,"posyears":float((yrs>0).mean()) if len(yrs) else 0})
prog(6,10,"base implied-vol grid complete")
# VIX9D/VIX term structure, available from 2011; same conservative lag.
r=(ivs["VIX9D"]/ivs["VIX"]).replace([np.inf,-np.inf],np.nan)
for m in ["SPXUSD","NSXUSD"]:
 a=spot[m]; x=r.shift(1); q=pd.concat([x.rename("x"),a.rename("px")],axis=1,join="inner").dropna();q=q[(q.index.year>=2011)&(q.index.year<=2013)]
 lo=x.rolling(252,min_periods=126).quantile(.10).shift(1);hi=x.rolling(252,min_periods=126).quantile(.90).shift(1)
 for h in [1,5]:
  y=np.log(q.px.shift(-h)/q.px)*1e4
  for tail,mask in [(.10,q.x<=lo.reindex(q.index)),(.90,q.x>=hi.reindex(q.index))]:
   yy=y[mask].dropna()
   for mode,direction in [("continuation",1),("reversal",-1)]:
    p=direction*(-1 if tail==.10 else 1)*yy;yrs=p.groupby(p.index.year).mean()
    rows.append({"source":"VIX9D/VIX","target":m,"feature":"term_ratio","tail":tail,"horizon_days":h,"mode":mode,"n":len(p),"gross_bp":float(p.mean()) if len(p) else np.nan,"hit":float((p>0).mean()) if len(p) else np.nan,"posyears":float((yrs>0).mean()) if len(yrs) else 0})
prog(7,10,"term-structure grid complete")
R=pd.DataFrame(rows);R.to_csv(O/"DISCOVERY_GRID.csv",index=False)
# discovery screen only; require enough events and >=3/4 positive years (term ratio: >=2/3 due 2011 start)
def ok(r):
 need=.75 if r.source!="VIX9D/VIX" else 2/3
 return r.n>=60 and r.gross_bp>0 and r.posyears>=need
S=R[R.apply(ok,axis=1)].copy()
# diversity freeze: at most one per source/target/feature, max 20.
F=S.sort_values("gross_bp",ascending=False).drop_duplicates(["source","target","feature"]).head(20).copy();F["selection_period"]="2010-2013 (VIX9D/VIX 2011-2013)";F.to_csv(O/"FROZEN_REPLICATION_CANDIDATES.csv",index=False)
freeze_sha=hashlib.sha256((O/"FROZEN_REPLICATION_CANDIDATES.csv").read_bytes()).hexdigest()
prog(8,10,f"{len(R)} cells; screen {len(S)}; freeze {len(F)} diverse candidates")
receipt={"run_id":rid,"status":"COMPLETE","family":"implied volatility state / term structure","verified_v38_design_sha256":sha,"discovery_period":"2010-2013 only; VIX9D term ratio begins 2011","causal_lag":"all Cboe daily observations shifted one observation before spot join","cells":len(R),"screen_survivors":len(S),"frozen_count":len(F),"freeze_sha256":freeze_sha,"replication_2014_2017_accessed":False,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(9,10,f"freeze sha256 {freeze_sha[:12]}");prog(10,10,"STOP - 2014+ untouched")
print("\n=== V39 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== FROZEN ===");print(F.to_string(index=False) if len(F) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V39 compile failed"}
Write-Host "=== GEF V39 - IMPLIED VOL DISCOVERY ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V39 failed"}
