param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v11.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); B=ROOT/"Research"/"Autonomous"
RAW=ROOT/"DataLake"/"raw"/"histdata"/"GBPUSD"/"M1"; V3=B/"guardian_edge_factory_v3"; OUTB=B/"guardian_edge_factory_v11";OUTB.mkdir(parents=True,exist_ok=True)
started=time.time()
def prog(o,s,i,n,m=""):
 e=time.time()-started;eta=e/i*(n-i) if i else 0
 print(f"[GEF11] {s:<18} {i}/{n} {100*i/n:6.2f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {m}",flush=True)
 (o/"STATUS.json").write_text(json.dumps({"stage":s,"done":i,"total":n,"pct":100*i/n,"elapsed_s":e,"eta_s":eta,"message":m},indent=2))
rid="GEF11-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");OUT=OUTB/rid;OUT.mkdir()
# Frozen actual components observed in V9/V10; no component/threshold/horizon optimization.
components=["rangepos_60","z_30"]; horizon=60; q=.90
# Build causal 5m bars: bucket label is shifted to bar availability time (right edge).
ys=[]
for j,y in enumerate(range(2010,2023),1):
 d=pd.read_parquet(RAW/f"GBPUSD_M1_{y}.parquet");d.index=pd.to_datetime(d["datetime"]);x=d[["open","high","low","close"]].sort_index()
 g=x.resample("5min",label="right",closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()
 # label t means [t-5,t), last raw minute normally t-1; therefore information is known by t.
 g["year"]=y;ys.append(g);prog(OUT,"CAUSAL CACHE",j,13,str(y))
z=pd.concat(ys).sort_index()
# sanity: causal bar close at label t must equal last raw close strictly before t for sampled events.
san=[]
for t in pd.to_datetime(["2017-06-08 17:00","2016-10-06 18:45","2016-06-30 11:00","2022-11-02 13:35","2020-03-18 15:05","2022-10-13 08:25"]):
 d=pd.read_parquet(RAW/f"GBPUSD_M1_{t.year}.parquet");d.index=pd.to_datetime(d["datetime"]);prev=d.loc[d.index<t,"close"].iloc[-1]
 san.append({"label":t,"causal_close":float(z.loc[t,"close"]),"last_raw_before_label":float(prev),"exact":bool(abs(float(z.loc[t,"close"])-float(prev))<1e-12)})
pd.DataFrame(san).to_csv(OUT/"causal_timestamp_sanity.csv",index=False)
if not all(x["exact"] for x in san): raise RuntimeError("Causal timestamp sanity failed")
# Features exactly defined on available 5m closes.
c=z.close.astype(float); ret=np.log(c/c.shift(1))
z["z_30"]=(ret-ret.rolling(30,min_periods=30).mean())/ret.rolling(30,min_periods=30).std()
lo=c.rolling(60,min_periods=60).min();hi=c.rolling(60,min_periods=60).max();z["rangepos_60"]=(c-lo)/(hi-lo)
# Reproduce V9/V10 sign convention from Discovery only: Spearman(feature, forward return) on 2010-13.
# Forward target is 60 minutes = 12 causal M5 bars.
z["fwd"]=np.log(c.shift(-12)/c)*10000
disc=z[(z.index.year>=2010)&(z.index.year<=2013)]
signs={}
for f in components:
 rho=disc[[f,"fwd"]].corr(method="spearman").iloc[0,1];signs[f]=-1 if rho>0 else 1
# Discovery ECDF percentile ranks frozen from Discovery distribution.
def ecdf_apply(train,s):
 a=np.sort(train.dropna().to_numpy());v=s.to_numpy();return pd.Series(np.searchsorted(a,v,side="right")/len(a),index=s.index)
scores=[]
for f in components:
 p=ecdf_apply(disc[f],z[f]);scores.append((p-.5)*2*signs[f])
z["score"]=pd.concat(scores,axis=1).mean(axis=1)
thr=float(np.quantile(np.abs(pd.concat(scores,axis=1).loc[disc.index].mean(axis=1).dropna()),q))
# Same frozen P90 tail; observed direction follows score sign. No new filtering.
rows=[]; yearly=[]
for delay in [0,15]:
 db=delay//5
 sig=z.score.shift(db); target=np.log(c.shift(-(12+db))/c.shift(-db))*10000 if db else z.fwd
 mask=(np.abs(sig)>=thr)&target.notna()
 pnl=np.sign(sig[mask])*target[mask]
 # Preserve empirically frozen short-only tail if P90 geometry yields it; report, don't force.
 for cost in [0,.05,.10,.15,.20,.25,.30,.35,.40,.50]:
  net=pnl-cost
  yp=net.groupby(net.index.year).mean()
  rows.append({"delay":delay,"cost_bp":cost,"n":len(net),"gross_bp_trade":float(pnl.mean()),"net_bp_trade":float(net.mean()),"hit":float((pnl>0).mean()),"long_fraction":float((np.sign(sig[mask])>0).mean()),"positive_year_fraction":float((yp>0).mean())})
 for y,g in pnl.groupby(pnl.index.year): yearly.append({"delay":delay,"year":int(y),"n":len(g),"gross_bp_trade":float(g.mean()),"hit":float((g>0).mean())})
 prog(OUT,"REPRODUCTION",1 if delay==0 else 2,2,f"delay={delay}")
R=pd.DataFrame(rows);Y=pd.DataFrame(yearly);R.to_csv(OUT/"cost_surface.csv",index=False);Y.to_csv(OUT/"yearly.csv",index=False)
base=R[(R.delay==0)&(R.cost_bp==0)].iloc[0]; stress=R[(R.delay==15)&(R.cost_bp==0)].iloc[0]
receipt={"run_id":rid,"status":"COMPLETE","research_max":"2022-12-31","locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"lineage":"GBP60_CAUSAL_REPAIR_V1","parent_rule":"GBP60_LOCAL_P90_PREOOS_V1_INVALID_TIMESTAMPING","components":components,"threshold_quantile":q,"horizon_minutes":60,"bar_semantics":"5m bars labeled at right edge; label t aggregates [t-5,t), hence no t+future data","discovery_signs":signs,"discovery_threshold":thr,"delay0_gross_bp_trade":float(base.gross_bp_trade),"delay0_n":int(base.n),"delay0_hit":float(base.hit),"delay0_long_fraction":float(base.long_fraction),"delay0_positive_year_fraction":float(base.positive_year_fraction),"delay15_gross_bp_trade":float(stress.gross_bp_trade),"delay15_positive_year_fraction":float(stress.positive_year_fraction),"errors":[]}
receipt["verdict"]="CAUSAL_EDGE_SURVIVES_PREOOS" if base.gross_bp_trade>0 and base.positive_year_fraction>=.69 else "CAUSAL_EDGE_FAILS_PREOOS"
receipt["next_gate"]="Human review only. Do not open OOS automatically."
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(OUT,"COMPLETE",1,1,receipt["verdict"])
print("\n=== V11 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== V11 COST SURFACE ===");print(R.to_string(index=False));print("\n=== V11 YEARLY ===");print(Y.to_string(index=False));print("\n=== CAUSAL SANITY ===");print(pd.DataFrame(san).to_string(index=False));print("\nRUN:",OUT)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V11 compile failed"}
Write-Host "=== GEF V11 — CAUSAL REPAIR / STRICT GBP60 REPRODUCTION / OOS LOCKED ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V11 run failed"}
