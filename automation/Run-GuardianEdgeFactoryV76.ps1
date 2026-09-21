param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v76_fomc_replication.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,hashlib,time
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake"
SRC=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v75"
runs=sorted([p for p in SRC.glob("GEF75-*") if (p/"V76_FROZEN_CANDIDATES.csv").exists()])
if not runs: raise RuntimeError("No V75 frozen candidates")
V=runs[-1];fp=V/"V76_FROZEN_CANDIDATES.csv"
EXPECTED="51d98e6af98dd26be11c6be7e157eec56dd6cd00b6da5bfde0adcf333c05d322"
if hashlib.sha256(fp.read_bytes()).hexdigest()!=EXPECTED: raise RuntimeError("V75 candidate SHA mismatch")
C=pd.read_csv(fp)
# Reconstruct scheduled statement dates 2014-2017 from local FOMC corpus, using statement rows only.
V73root=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v73"
v73=sorted([p for p in V73root.glob("GEF73-*") if (p/"FOMC_DATED_DOCUMENTS_UNTIMED.csv").exists()])[-1]
D=pd.read_csv(v73/"FOMC_DATED_DOCUMENTS_UNTIMED.csv");D["event_date"]=pd.to_datetime(D.event_date)
E=D[(D.document_type=="statement")&(D.event_date.dt.year.between(2014,2017))][["event_date"]].drop_duplicates().sort_values("event_date")
# From 2013-03-20 onward regular FOMC statements at 14:00 ET.
E["release_time_et"]="14:00"
rid="GEF76-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
O=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v76"/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF76] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
prog(1,10,f"V75 SHA verified; frozen={len(C)}; replication 2014-2017 only")
def load(sym):
 z=[]
 for y in range(2014,2018):
  p=DL/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
  if not p.exists():continue
  d=pd.read_parquet(p);dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None);pc=next((c for c in d.columns if str(c).lower()=="close"),None)
  if dc is None and isinstance(d.index,pd.DatetimeIndex): d=d.reset_index(); dc=d.columns[0]
  if dc is None or pc is None: continue
  q=pd.DataFrame({"dt":pd.to_datetime(d[dc],errors="coerce"),"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
  q=q[q.dt.dt.year.between(2014,2017)];z.append(q)
 if not z:return None
 return pd.concat(z).sort_values("dt").drop_duplicates("dt").set_index("dt").px
events=[]
for _,r in E.iterrows():
 local=pd.Timestamp(str(r.event_date.date())+" 14:00").tz_localize("America/New_York")
 events.append((r.event_date,local.tz_convert("UTC").tz_localize(None)))
out=[]
for i,r in C.iterrows():
 s=load(r.market)
 vals=[]
 if s is not None:
  for ed,ts in events:
   a=s[s.index>=ts+pd.Timedelta(minutes=int(r.delay_min))]
   if a.empty: continue
   at=a.index[0]
   if at>ts+pd.Timedelta(minutes=int(r.delay_min)+3):continue
   b=s[s.index>=at+pd.Timedelta(minutes=int(r.horizon_min))]
   if b.empty:continue
   bt=b.index[0]
   if bt>at+pd.Timedelta(minutes=int(r.horizon_min)+3):continue
   ret=float(b.iloc[0]/a.iloc[0]-1)*(1 if r.side=="long" else -1)
   vals.append((ed,ret))
 x=np.array([v for _,v in vals],float); n=len(x)
 yrs={}
 for y in range(2014,2018):
  xy=[v for d,v in vals if d.year==y]; yrs[y]=(float(np.mean(xy)*1e4) if xy else np.nan)
 pos=np.mean([v>0 for v in yrs.values() if np.isfinite(v)]) if yrs else np.nan
 out.append({**r.to_dict(),"rep_n":n,"rep_mean_bp":float(np.mean(x)*1e4) if n else np.nan,"rep_hit":float(np.mean(x>0)) if n else np.nan,"positive_year_fraction":float(pos) if np.isfinite(pos) else np.nan,**{f"y{y}_bp":yrs[y] for y in yrs}})
 prog(2+i,10,f"{r.market} d{int(r.delay_min)} h{int(r.horizon_min)} {r.side} complete")
R=pd.DataFrame(out)
# Predeclared replication gate: enough events, same sign, hit >= .52, at least 3/4 positive years.
R["pass"]=(R.rep_n>=24)&(R.rep_mean_bp>0)&(R.rep_hit>=.52)&(R.positive_year_fraction>=.75)
S=R[R["pass"]].copy()
R.to_csv(O/"REPLICATION_ALL.csv",index=False);S.to_csv(O/"V77_SURVIVORS.csv",index=False)
sha=hashlib.sha256((O/"V77_SURVIVORS.csv").read_bytes()).hexdigest()
prog(8,10,f"tested={len(R)} passed={len(S)}")
spec={"input_sha256":EXPECTED,"window":"2014-2017","release_time":"14:00 ET DST-aware","gate":{"n_min":24,"mean_bp_gt":0,"hit_min":.52,"positive_year_fraction_min":.75},"retuning":False,"2018_plus_accessed":False}
(O/"REPLICATION_SPEC.json").write_text(json.dumps(spec,indent=2));prog(9,10,f"survivor SHA={sha}")
receipt={"run_id":rid,"status":"COMPLETE_FOMC_REPLICATION_2014_2017","tested":len(R),"passed":len(S),"survivor_sha256":sha,"retuning":False,"2018_plus_market_returns_accessed":False,"2023_plus_accessed":False,"protected_2026_accessed":False,"next":"V77_PREVALIDATION_ROBUSTNESS_2010_2017" if len(S) else "CLOSE_SIMPLE_FOMC_DRIFT_LINEAGE"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(10,10,"STOP; 2018+ unopened")
print("\n=== V76 RECEIPT ===");print(json.dumps(receipt,indent=2))
print("\n=== REPLICATION RESULTS ===");print(R.to_string(index=False))
print("\n=== SURVIVORS ===");print(S.to_string(index=False) if len(S) else "NONE")
print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V76 compile failed"}
Write-Host "=== GEF V76 - FOMC REPLICATION 2014-2017 ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V76 failed"}
