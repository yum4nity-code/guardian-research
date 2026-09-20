param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v41_impliedvol_robustness.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");RAW=ROOT/"DataLake"/"raw"/"histdata";CBOE=ROOT/"DataLake"/"normalized"/"cboe_pre2023";V40=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v40";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v41";OUT.mkdir(parents=True,exist_ok=True)
t=time.time();rid="GEF41-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
EXPECTED="dd23ecbcc8a6adde23518fe491c34dc7b012cbbf9c0cc13f32d4e1969fb14d3f"
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF41] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
runs=sorted([p for p in V40.glob("GEF40-*") if (p/"REPLICATION_SURVIVORS.csv").exists() and (p/"RUN_RECEIPT.json").exists()])
if not runs:raise RuntimeError("No V40")
src=runs[-1];fp=src/"REPLICATION_SURVIVORS.csv";sha=hashlib.sha256(fp.read_bytes()).hexdigest()
if sha!=EXPECTED:raise RuntimeError(f"V40 survivor hash mismatch {sha}")
F=pd.read_csv(fp)
if len(F)!=12:raise RuntimeError(f"Expected 12 survivors, got {len(F)}")
prog(1,16,f"verified V40 survivors {sha[:12]} | 12 candidates")
spec={"VIX":("VIX_History_PRE2023.csv","CLOSE"),"VIX9D":("VIX9D_History_PRE2023.csv","CLOSE"),"VVIX":("VVIX_History_PRE2023.csv","VVIX"),"GVZ":("GVZ_History_PRE2023.csv","GVZ"),"OVX":("OVX_History_PRE2023.csv","OVX")}
ivs={}
for name,(fn,col) in spec.items():
 d=pd.read_csv(CBOE/fn);d["DATE"]=pd.to_datetime(d["DATE"]);s=pd.to_numeric(d[col],errors="coerce");s.index=d["DATE"];ivs[name]=s.sort_index()
markets=sorted(F.target.unique());spot={}
for m in markets:
 z=[]
 for y0 in range(2010,2018):
  pth=RAW/m/"M1"/f"{m}_M1_{y0}.parquet"
  if pth.exists():
   d=pd.read_parquet(pth);tc=next(c for c in d if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc]);z.append(d[["close"]])
 spot[m]=pd.concat(z).sort_index().close.resample("1D").last().dropna()
prog(2,16,"loaded <=2017 sources only")
def feature(source,feat):
 if source=="VIX9D/VIX":return (ivs["VIX9D"]/ivs["VIX"]).replace([np.inf,-np.inf],np.nan)
 s=ivs[source]
 if feat=="level_pct":return s.rolling(252,min_periods=126).rank(pct=True)
 if feat=="chg1":return s.pct_change()
 if feat=="chg5":return s.pct_change(5)
 if feat=="z20":return (s-s.rolling(20,min_periods=10).mean())/s.rolling(20,min_periods=10).std()
 raise RuntimeError(feat)
def pnl_for(r,extra_lag=0):
 source,target,feat=str(r["source"]),str(r["target"]),str(r["feature"]);tail=float(r["tail"]);h=int(r["horizon_days"]);mode=str(r["mode"])
 raw=feature(source,feat);x=raw.shift(1+extra_lag);a=spot[target];q=pd.concat([x.rename("x"),a.rename("px")],axis=1,join="inner").dropna();q=q[(q.index.year>=2014)&(q.index.year<=2017)]
 if feat=="level_pct":mask=q.x<=tail if tail==.10 else q.x>=tail
 else:
  lo=x.rolling(252,min_periods=126).quantile(.10).shift(1);hi=x.rolling(252,min_periods=126).quantile(.90).shift(1);mask=q.x<=lo.reindex(q.index) if tail==.10 else q.x>=hi.reindex(q.index)
 y=np.log(q.px.shift(-h)/q.px)*1e4;yy=y[mask].dropna();direction=1 if mode=="continuation" else -1
 return direction*(-1 if tail==.10 else 1)*yy
rows=[];rng=np.random.default_rng(410041)
for j,r in F.iterrows():
 p=pnl_for(r,0);d1=pnl_for(r,1)
 k1=max(1,int(np.ceil(len(p)*.01)));k2=max(1,int(np.ceil(len(p)*.02)))
 tr1=p.drop(p.nlargest(k1).index);tr2=p.drop(p.nlargest(k2).index)
 # remove best 3 event dates (daily signals)
 rm3=p.drop(p.nlargest(min(3,len(p))).index)
 # non-overlap in calendar days by horizon
 chosen=[];last=None;gap=pd.Timedelta(days=int(r["horizon_days"]))
 for ts,v in p.items():
  if last is None or ts-last>=gap:chosen.append((ts,v));last=ts
 no=pd.Series([v for _,v in chosen],index=[x for x,_ in chosen],dtype=float)
 yrs=p.groupby(p.index.year).mean()
 # dependence-aware yearly/day sign flip: one sign per calendar month, 2000 reps
 months=pd.PeriodIndex(p.index,freq="M");u=months.unique();codes=pd.Categorical(months,categories=u).codes;arr=p.to_numpy();obs=abs(float(p.mean()));ge=0
 for _ in range(2000):
  signs=rng.choice(np.array([-1.,1.]),size=len(u))
  if abs(float(np.mean(arr*signs[codes])))>=obs:ge+=1
 nullp=(ge+1)/2001
 passed=bool(len(p)>=60 and p.mean()>0 and d1.mean()>0 and tr1.mean()>0 and tr2.mean()>0 and rm3.mean()>0 and len(no)>0 and no.mean()>0 and len(yrs)==4 and (yrs>0).mean()>=.75 and nullp<=.05)
 rows.append({"source":r["source"],"target":r["target"],"feature":r["feature"],"tail":r["tail"],"horizon_days":r["horizon_days"],"mode":r["mode"],"n":len(p),"gross_bp":float(p.mean()),"extra_lag_1obs_bp":float(d1.mean()),"trim1_bp":float(tr1.mean()),"trim2_bp":float(tr2.mean()),"remove_best3_events_bp":float(rm3.mean()),"nonoverlap_n":len(no),"nonoverlap_bp":float(no.mean()),"posyears":float((yrs>0).mean()),"month_signflip_p":float(nullp),"robust_pass":passed})
 prog(3+j,16,f"{j+1}/12 {r['source']}->{r['target']} | gross {p.mean():.2f} trim2 {tr2.mean():.2f} lag+1 {d1.mean():.2f} p {nullp:.4f} | {'PASS' if passed else 'FAIL'}")
R=pd.DataFrame(rows);R.to_csv(O/"ROBUSTNESS_RESULTS.csv",index=False);S=R[R.robust_pass].copy();S.to_csv(O/"ROBUST_SURVIVORS.csv",index=False)
ssha=hashlib.sha256((O/"ROBUST_SURVIVORS.csv").read_bytes()).hexdigest()
receipt={"run_id":rid,"status":"COMPLETE","source_v40":src.name,"verified_survivor_sha256":sha,"period":"2014-2017 only","candidate_count":12,"robust_pass_count":len(S),"robust_survivor_sha256":ssha,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(16,16,f"STOP | robust {len(S)}/12 | 2018+ untouched")
print("\n=== V41 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== ROBUST SURVIVORS ===");print(S.to_string(index=False) if len(S) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V41 compile failed"}
Write-Host "=== GEF V41 - IMPLIED VOL PRE-VALIDATION ROBUSTNESS ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V41 failed"}
