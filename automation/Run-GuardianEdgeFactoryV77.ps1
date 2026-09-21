param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v77_fomc_initial_reaction.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,hashlib,time
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake"
V74=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v74").glob("GEF74-*"))[-1]
FP=V74/"FROZEN_FOMC_DISCOVERY_EVENTS_2010_2013.csv"; EXPECTED="cd4c1afbbc1f4cc8819ca37b463f22285908a0464517e7a55e16e2b34bd51201"
if hashlib.sha256(FP.read_bytes()).hexdigest()!=EXPECTED: raise RuntimeError("V74 event SHA mismatch")
E=pd.read_csv(FP)
markets=["EURUSD","GBPUSD","USDJPY","USDCHF","USDCAD","AUDUSD","XAUUSD","XAGUSD","SPXUSD","NSXUSD"]
reaction=[1,5,15]; forward=[15,30,60,120,240]; modes=["continuation","reversal"]
rid="GEF77-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");O=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v77"/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF77] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
prog(1,14,f"family 24 discovery; V74 SHA verified; events={len(E)}; 2010-2013 only")
def load(sym):
 z=[]
 for y in range(2010,2014):
  p=DL/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
  if not p.exists():continue
  d=pd.read_parquet(p);dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None);pc=next((c for c in d.columns if str(c).lower()=="close"),None)
  if dc is None and isinstance(d.index,pd.DatetimeIndex):d=d.reset_index();dc=d.columns[0]
  if dc is None or pc is None:continue
  q=pd.DataFrame({"dt":pd.to_datetime(d[dc],errors="coerce"),"px":pd.to_numeric(d[pc],errors="coerce")}).dropna();q=q[q.dt.dt.year.between(2010,2013)];z.append(q)
 return None if not z else pd.concat(z).sort_values("dt").drop_duplicates("dt").set_index("dt").px
events=[]
for _,r in E.iterrows():
 ts=pd.Timestamp(str(r.event_date)+" "+str(r.release_time_et)).tz_localize("America/New_York").tz_convert("UTC").tz_localize(None);events.append((pd.Timestamp(r.event_date),ts))
rows=[]
for mi,sym in enumerate(markets,1):
 s=load(sym)
 if s is None:continue
 for rw in reaction:
  for fw in forward:
   vals=[]
   for ed,ts in events:
    a=s[s.index>=ts]
    if a.empty or a.index[0]>ts+pd.Timedelta(minutes=3):continue
    p0=float(a.iloc[0])
    q=s[s.index>=ts+pd.Timedelta(minutes=rw)]
    if q.empty or q.index[0]>ts+pd.Timedelta(minutes=rw+3):continue
    pr=float(q.iloc[0]);sg=np.sign(pr/p0-1)
    if sg==0:continue
    b=s[s.index>=q.index[0]+pd.Timedelta(minutes=fw)]
    if b.empty or b.index[0]>q.index[0]+pd.Timedelta(minutes=fw+3):continue
    base=float(b.iloc[0]/pr-1);vals.append((ed,sg,base))
   for mode in modes:
    x=np.array([base*sg*(1 if mode=="continuation" else -1) for _,sg,base in vals]);n=len(x)
    rows.append({"market":sym,"reaction_min":rw,"forward_min":fw,"mode":mode,"n":n,"mean_bp":np.mean(x)*1e4 if n else np.nan,"hit":np.mean(x>0) if n else np.nan})
 prog(1+mi,14,f"{sym} complete")
R=pd.DataFrame(rows);R.to_csv(O/"DISCOVERY_ALL.csv",index=False)
# 300-cell discovery; stricter than V75 due selection multiplicity and tiny event count.
S=R[(R.n>=24)&(R.mean_bp>=3)&(R.hit>=.60)].copy();S["score"]=S.mean_bp*np.sqrt(S.n)
F=S.sort_values(["score","mean_bp"],ascending=False).head(12).drop(columns="score");F.to_csv(O/"V78_FROZEN_CANDIDATES.csv",index=False)
sha=hashlib.sha256((O/"V78_FROZEN_CANDIDATES.csv").read_bytes()).hexdigest()
prog(12,14,f"trials={len(R)} screen={len(S)} frozen={len(F)}")
spec={"family":"24_EVENT_X_INITIAL_REACTION","window":"2010-2013","event_sha256":EXPECTED,"reaction_windows_min":reaction,"forward_horizons_min":forward,"modes":modes,"markets":markets,"screen":{"n_min":24,"mean_bp_min":3,"hit_min":.60},"max_frozen":12,"mechanism":"sign of causal post-release reaction, then continuation/reversal from reaction endpoint","2014_plus_accessed":False}
(O/"DISCOVERY_SPEC.json").write_text(json.dumps(spec,indent=2));prog(13,14,f"candidate SHA={sha}")
receipt={"run_id":rid,"status":"COMPLETE_FOMC_INITIAL_REACTION_DISCOVERY","trials":len(R),"screen_survivors":len(S),"frozen":len(F),"candidate_sha256":sha,"2014_plus_market_returns_accessed":False,"2023_plus_accessed":False,"protected_2026_accessed":False,"next":"V78_REPLICATION_2014_2017" if len(F) else "CLOSE_FOMC_INITIAL_REACTION_LINEAGE"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(14,14,"STOP; replication unopened")
print("\n=== V77 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== FROZEN CANDIDATES ===");print(F.to_string(index=False) if len(F) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V77 compile failed"}
Write-Host "=== GEF V77 - FOMC EVENT x INITIAL REACTION DISCOVERY ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V77 failed"}
