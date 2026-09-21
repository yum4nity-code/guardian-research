param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v63_intraday_calendar_discovery.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,time,json,hashlib
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v63"
rid="GEF63-"+pd.Timestamp.utcnow().strftime("%Y%m%d-%H%M%S");O=BASE/rid;O.mkdir(parents=True,exist_ok=True)
t=time.time()
markets=["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","XAUUSD","XAGUSD","SPXUSD","NSXUSD","WTIUSD","BCOUSD"]
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0
 print(f"[GEF63] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
def load(sym):
 fs=[DL/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet" for y in range(2010,2014)]
 fs=[p for p in fs if p.exists()]
 if not fs:return None
 z=[]
 for p in fs:
  d=pd.read_parquet(p);dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None);pc=next((c for c in d.columns if str(c).lower()=="close"),None)
  if dc is None and isinstance(d.index,pd.DatetimeIndex):d=d.reset_index();dc=d.columns[0]
  if dc is None or pc is None:continue
  x=pd.DataFrame({"dt":pd.to_datetime(d[dc],errors="coerce"),"px":pd.to_numeric(d[pc],errors="coerce")}).dropna();z.append(x)
 if not z:return None
 return pd.concat(z).sort_values("dt").drop_duplicates("dt")
prog(1,16,"DISCOVERY ONLY 2010-2013; 2014+ forbidden")
rows=[];loaded={}
for j,sym in enumerate(markets,2):
 d=load(sym)
 if d is None:prog(j,16,f"{sym} unavailable");continue
 assert d.dt.dt.year.max()<=2013
 loaded[sym]=d
 # Hour-of-day continuation/reversal: return over prior 60m -> next 60m, sampled once/hour.
 x=d.set_index("dt").px.resample("1h").last().dropna().to_frame("px")
 x["prev"]=x.px.pct_change();x["fwd"]=x.px.shift(-1)/x.px-1;x=x.dropna()
 for h,g in x.groupby(x.index.hour):
  if len(g)<100:continue
  for mode,side in [("continuation",1),("reversal",-1)]:
   r=np.sign(g.prev.values)*g.fwd.values*side
   rows.append({"market":sym,"mechanism":"hour_prev1h","bucket":int(h),"mode":mode,"n":len(r),"mean_bp":float(np.mean(r)*1e4),"hit":float(np.mean(r>0))})
 # Weekday unconditional next-day direction, both sides; simple calendar structure.
 q=d.set_index("dt").px.resample("1D").last().dropna().to_frame("px");q["fwd"]=q.px.shift(-1)/q.px-1;q=q.dropna()
 for wd,g in q.groupby(q.index.dayofweek):
  for side in [1,-1]:
   r=g.fwd.values*side
   rows.append({"market":sym,"mechanism":"weekday","bucket":int(wd),"mode":"long" if side==1 else "short","n":len(r),"mean_bp":float(np.mean(r)*1e4),"hit":float(np.mean(r>0))})
 prog(j,16,f"{sym} rows={len(d):,} trials_so_far={len(rows)}")
R=pd.DataFrame(rows);R.to_csv(O/"DISCOVERY_ALL.csv",index=False)
# Frozen screening rule declared in code: n>=100, mean>=2bp, hit>=0.53; cap top 24 by |mean| with mechanism diversity.
S=R[(R.n>=100)&(R.mean_bp>=2)&(R.hit>=.53)].copy().sort_values(["mean_bp","hit"],ascending=False)
F=S.head(24).copy();F.to_csv(O/"V64_FROZEN_CANDIDATES.csv",index=False)
sha=hashlib.sha256((O/"V64_FROZEN_CANDIDATES.csv").read_bytes()).hexdigest()
receipt={"run_id":rid,"status":"COMPLETE_DISCOVERY_2010_2013","family":"04_INTRADAY_CALENDAR_STRUCTURE","markets_loaded":list(loaded),"trials":len(R),"screen_survivors":len(S),"frozen":len(F),"freeze_sha256":sha,"later_period_accessed":False,"next":"V64_REPLICATION_2014_2017"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(15,16,f"screen={len(S)} frozen={len(F)} sha={sha[:12]}")
prog(16,16,"HARD STOP before 2014+")
print();print("=== V63 RECEIPT ===");print(json.dumps(receipt,indent=2))
print();print("=== TOP FROZEN ===");print(F.head(24).to_string(index=False))
print();print("RUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V63 compile failed"}
Write-Host "=== GEF V63 - INTRADAY/CALENDAR DISCOVERY 2010-2013 ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V63 failed"}
