param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v42_prevalidation_forensic.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");RAW=ROOT/"DataLake"/"raw"/"histdata";CBOE=ROOT/"DataLake"/"normalized"/"cboe_pre2023";V41=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v41";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v42";OUT.mkdir(parents=True,exist_ok=True)
t=time.time();rid="GEF42-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
EXPECTED="4bb33cbb287b3f0b65542fd9cbb89ec8a0c85d97206f6def3343a759f6dd6f66"
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF42] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
runs=sorted([p for p in V41.glob("GEF41-*") if (p/"ROBUST_SURVIVORS.csv").exists()])
src=runs[-1];fp=src/"ROBUST_SURVIVORS.csv";sha=hashlib.sha256(fp.read_bytes()).hexdigest()
if sha!=EXPECTED:raise RuntimeError(f"V41 hash mismatch {sha}")
F=pd.read_csv(fp)
if len(F)!=5:raise RuntimeError("Expected 5 V41 survivors")
prog(1,12,f"V41 frozen survivor set verified {sha[:12]}")
# Critical semantic audit: preserve Cboe observation date, use spot DAILY SERIES ONLY as a target.
# Test extra information lags 1/2/3 observations; no parameter selection.
spec={"VIX":("VIX_History_PRE2023.csv","CLOSE"),"VIX9D":("VIX9D_History_PRE2023.csv","CLOSE")}
ivs={}
for name,(fn,col) in spec.items():
 d=pd.read_csv(CBOE/fn);d["DATE"]=pd.to_datetime(d["DATE"]);s=pd.to_numeric(d[col],errors="coerce");s.index=d["DATE"];ivs[name]=s.sort_index()
spot={}
for m in sorted(F.target.unique()):
 z=[]
 for y in range(2010,2018):
  p=RAW/m/"M1"/f"{m}_M1_{y}.parquet";d=pd.read_parquet(p);tc=next(c for c in d if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc]);z.append(d[["close"]])
 spot[m]=pd.concat(z).sort_index().close.resample("1D").last().dropna()
prog(2,12,"loaded only <=2017; 2018+ untouched")
def rawfeat(source,feat):
 s=ivs[source]
 if feat=="level_pct":return s.rolling(252,min_periods=126).rank(pct=True)
 if feat=="chg1":return s.pct_change()
 if feat=="chg5":return s.pct_change(5)
 raise RuntimeError(feat)
def getp(r,lag,tail_override=None):
 x=rawfeat(str(r["source"]),str(r["feature"])).shift(lag);a=spot[str(r["target"])];q=pd.concat([x.rename("x"),a.rename("px")],axis=1,join="inner").dropna();q=q[(q.index.year>=2014)&(q.index.year<=2017)]
 tail=float(r["tail"]) if tail_override is None else tail_override
 if str(r["feature"])=="level_pct":mask=q.x<=tail if tail<.5 else q.x>=tail
 else:
  lo=x.rolling(252,min_periods=126).quantile(1-tail if tail>.5 else tail).shift(1);hi=x.rolling(252,min_periods=126).quantile(tail if tail>.5 else 1-tail).shift(1);mask=q.x<=lo.reindex(q.index) if float(r["tail"])<.5 else q.x>=hi.reindex(q.index)
 h=int(r["horizon_days"]);y=np.log(q.px.shift(-h)/q.px)*1e4;yy=y[mask].dropna();direction=1 if str(r["mode"])=="continuation" else -1
 return direction*(-1 if float(r["tail"])<.5 else 1)*yy
rows=[]
for j,r in F.iterrows():
 p1,p2,p3=getp(r,1),getp(r,2),getp(r,3)
 # neighboring tail only as robustness: 85/15, not selection
 neigh=.85 if float(r["tail"])>.5 else .15;pn=getp(r,1,neigh)
 # leave-one-year-out pooled means
 loo={}; 
 for y in range(2014,2018):
  s=p1[p1.index.year!=y];loo[str(y)]=float(s.mean())
 # remove each calendar quarter-of-year season to detect one-season dependence
 qs={}
 for qn in range(1,5):
  s=p1[p1.index.quarter!=qn];qs[str(qn)]=float(s.mean())
 # family-aware max-stat sign-flip handled after collecting pnl series
 rows.append({"source":r["source"],"target":r["target"],"feature":r["feature"],"tail":r["tail"],"horizon_days":r["horizon_days"],"mode":r["mode"],"n":len(p1),"lag1_bp":float(p1.mean()),"lag2_bp":float(p2.mean()),"lag3_bp":float(p3.mean()),"neighbor_tail_bp":float(pn.mean()),"loo_min_bp":min(loo.values()),"remove_quarter_min_bp":min(qs.values()),"_p":p1})
 prog(3+j,12,f"{j+1}/5 {r['source']}->{r['target']} {r['feature']} | lag1 {p1.mean():.1f} lag2 {p2.mean():.1f} lag3 {p3.mean():.1f} neigh {pn.mean():.1f}")
# Family-wise max-stat null over the 5 frozen candidates using monthly sign flips independently per candidate, 5000 reps.
rng=np.random.default_rng(420042);obsmax=max(abs(x["lag1_bp"]) for x in rows);ge=0
for _ in range(5000):
 vals=[]
 for x in rows:
  p=x["_p"];months=pd.PeriodIndex(p.index,freq="M");u=months.unique();codes=pd.Categorical(months,categories=u).codes;sg=rng.choice(np.array([-1.,1.]),len(u));vals.append(abs(float(np.mean(p.to_numpy()*sg[codes]))))
 if max(vals)>=obsmax:ge+=1
family_p=(ge+1)/5001
for x in rows:
 x.pop("_p");x["family_maxstat_p"]=float(family_p)
 # Strict forensic: all temporal lags positive, neighboring threshold positive, no single year/quarter necessary.
 x["forensic_pass"]=bool(x["lag1_bp"]>0 and x["lag2_bp"]>0 and x["lag3_bp"]>0 and x["neighbor_tail_bp"]>0 and x["loo_min_bp"]>0 and x["remove_quarter_min_bp"]>0 and family_p<=.05)
R=pd.DataFrame(rows);R.to_csv(O/"PREVALIDATION_FORENSIC.csv",index=False);S=R[R.forensic_pass].copy();S.to_csv(O/"FORENSIC_SURVIVORS.csv",index=False);ssha=hashlib.sha256((O/"FORENSIC_SURVIVORS.csv").read_bytes()).hexdigest()
prog(10,12,f"family max-stat null p={family_p:.5f}")
receipt={"run_id":rid,"status":"COMPLETE","source_v41":src.name,"verified_v41_sha256":sha,"period":"2014-2017 only","candidate_count":5,"forensic_pass_count":len(S),"family_maxstat_p":float(family_p),"survivor_sha256":ssha,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":[],"instruction":"If survivors remain, immutable freeze next. Do not validate yet."}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(11,12,f"survivors {len(S)}/5");prog(12,12,"STOP - 2018+ untouched")
print("\n=== V42 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== FORENSIC SURVIVORS ===");print(S.to_string(index=False) if len(S) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V42 compile failed"}
Write-Host "=== GEF V42 - FINAL PRE-VALIDATION FORENSIC ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V42 failed"}
