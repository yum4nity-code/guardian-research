param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v75_fomc_discovery.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,hashlib,time
from zoneinfo import ZoneInfo
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";SRC=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v74"
runs=sorted([p for p in SRC.glob("GEF74-*") if (p/"FROZEN_FOMC_DISCOVERY_EVENTS_2010_2013.csv").exists()]);assert runs
V=runs[-1];fp=V/"FROZEN_FOMC_DISCOVERY_EVENTS_2010_2013.csv";EXPECTED="cd4c1afbbc1f4cc8819ca37b463f22285908a0464517e7a55e16e2b34bd51201"
if hashlib.sha256(fp.read_bytes()).hexdigest()!=EXPECTED:raise RuntimeError("V74 event SHA mismatch")
E=pd.read_csv(fp);OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v75";rid="GEF75-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
markets=["EURUSD","GBPUSD","USDJPY","USDCHF","USDCAD","AUDUSD","XAUUSD","XAGUSD","SPXUSD","NSXUSD"]
horiz=[5,15,30,60,120,240];delays=[1,5]
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF75] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
prog(1,14,f"V74 SHA verified; events={len(E)}; discovery 2010-2013 only")
# HistData timestamps are treated as UTC for this lineage; convert official ET release via DST-aware America/New_York.
def load(sym):
 z=[]
 for y in range(2010,2014):
  p=DL/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
  if not p.exists():continue
  d=pd.read_parquet(p);dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None);pc=next((c for c in d.columns if str(c).lower()=="close"),None)
  if dc is None and isinstance(d.index,pd.DatetimeIndex):d=d.reset_index();dc=d.columns[0]
  if dc is None or pc is None:continue
  q=pd.DataFrame({"dt":pd.to_datetime(d[dc],errors="coerce"),"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
  q=q[q.dt.dt.year.between(2010,2013)];z.append(q)
 if not z:return None
 return pd.concat(z).sort_values("dt").drop_duplicates("dt").set_index("dt").px
events=[]
for _,r in E.iterrows():
 local=pd.Timestamp(str(r.event_date)+" "+str(r.release_time_et)).tz_localize("America/New_York")
 events.append((pd.Timestamp(r.event_date),local.tz_convert("UTC").tz_localize(None)))
# Mechanism: post-release directional drift only. Both long/short tested symmetrically.
allr=[];total=len(markets)
for mi,sym in enumerate(markets,1):
 s=load(sym)
 if s is None:continue
 for dly in delays:
  for h in horiz:
   vals=[]
   for ed,ts in events:
    a=s[s.index>=ts+pd.Timedelta(minutes=dly)]
    if a.empty:continue
    at=a.index[0]
    if at>ts+pd.Timedelta(minutes=dly+3):continue
    b=s[s.index>=at+pd.Timedelta(minutes=h)]
    if b.empty:continue
    bt=b.index[0]
    if bt>at+pd.Timedelta(minutes=h+3):continue
    vals.append((ed,float(b.iloc[0]/a.iloc[0]-1)))
   for side in [1,-1]:
    x=np.array([v*side for _,v in vals],float);n=len(x)
    allr.append({"market":sym,"delay_min":dly,"horizon_min":h,"side":"long" if side==1 else "short","n":n,"mean_bp":np.mean(x)*1e4 if n else np.nan,"hit":np.mean(x>0) if n else np.nan})
 prog(1+mi,14,f"{sym} complete")
R=pd.DataFrame(allr);R.to_csv(O/"DISCOVERY_ALL.csv",index=False)
# Predeclared broad screen; small N acknowledged. Freeze max 12, no 2014+ access.
screen=R[(R.n>=24)&(R.mean_bp>=3)&(R.hit>=.58)].copy()
screen["score"]=screen.mean_bp*np.sqrt(screen.n)
F=screen.sort_values(["score","mean_bp"],ascending=False).head(12).drop(columns="score")
F.to_csv(O/"V76_FROZEN_CANDIDATES.csv",index=False);sha=hashlib.sha256((O/"V76_FROZEN_CANDIDATES.csv").read_bytes()).hexdigest()
prog(12,14,f"trials={len(R)} screen={len(screen)} frozen={len(F)}")
spec={"event_sha256":EXPECTED,"window":"2010-2013","markets":markets,"delays_min":delays,"horizons_min":horiz,"sides":["long","short"],"screen":{"n_min":24,"mean_bp_min":3,"hit_min":.58},"max_frozen":12,"timestamp_rule":"official ET -> DST-aware America/New_York -> UTC; first quote >= release+delay, max 3m slop","2014_plus_accessed":False}
(O/"DISCOVERY_SPEC.json").write_text(json.dumps(spec,indent=2));prog(13,14,f"candidate SHA={sha}")
receipt={"run_id":rid,"status":"COMPLETE_FOMC_DISCOVERY_2010_2013","trials":len(R),"screen_survivors":len(screen),"frozen":len(F),"candidate_sha256":sha,"2014_plus_market_returns_accessed":False,"2023_plus_accessed":False,"protected_2026_accessed":False,"next":"V76_REPLICATION_2014_2017" if len(F) else "CLOSE_SIMPLE_FOMC_DRIFT_LINEAGE"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(14,14,"STOP; replication unopened")
print("\n=== V75 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== FROZEN CANDIDATES ===");print(F.to_string(index=False) if len(F) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V75 compile failed"}
Write-Host "=== GEF V75 - FOMC DISCOVERY 2010-2013 ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V75 failed"}
