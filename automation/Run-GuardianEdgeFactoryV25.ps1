param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v25_validation.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,hashlib,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");RAW=ROOT/"DataLake"/"raw"/"histdata";B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v24";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v25";OUT.mkdir(parents=True,exist_ok=True)
EXPECTED_SHA="471e6564b7743885ecef1a385adca7f4f92e939f04688e8b04bf8377673cad79"
runs=sorted([p for p in B.glob("GEF24-*") if (p/"FROZEN_VALIDATION_CANDIDATES.csv").exists()])
if not runs:raise RuntimeError("No V24 freeze")
src=runs[-1];fp=src/"FROZEN_VALIDATION_CANDIDATES.csv";sha=hashlib.sha256(fp.read_bytes()).hexdigest()
if sha!=EXPECTED_SHA:raise RuntimeError(f"Freeze hash mismatch {sha}")
F=pd.read_csv(fp);started=time.time();rid="GEF25-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
print("[GEF25] 0/4 0% freeze hash verified",sha,flush=True)
def load(m):
 ys=[]
 for y in range(2018,2023):
  p=RAW/m/"M1"/f"{m}_M1_{y}.parquet"
  if not p.exists():continue
  d=pd.read_parquet(p);tc=next(c for c in d.columns if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc]);x=d[["open","high","low","close"]].sort_index()
  ys.append(x.resample("5min",label="right",closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna())
 return pd.concat(ys).sort_index()
cache={};rows=[]
for i,r in F.iterrows():
 t,dv,fn=r.target,r.driver,r.feature;h=int(r.horizon_min);direction=int(r.direction);thr=float(r.threshold_abs)
 if t not in cache:cache[t]=load(t)
 if dv not in cache:cache[dv]=load(dv)
 a,b=cache[t],cache[dv];idx=a.index.intersection(b.index);ca=a.close.reindex(idx);cb=b.close.reindex(idx);rb=np.log(cb/cb.shift(1));w=int(fn.split("_")[1][:-1])
 if fn.startswith("drvret_"):x=np.log(cb/cb.shift(w))
 elif fn.startswith("drvz_"):x=(rb-rb.rolling(w,min_periods=w).mean())/rb.rolling(w,min_periods=w).std()
 else:x=np.log(ca/ca.shift(w))-np.log(cb/cb.shift(w))
 sel=x[x.abs()>=thr];sig=direction*np.sign(sel)
 def pnl(delay):
  en=ca.reindex(sig.index+pd.Timedelta(minutes=delay));ex=ca.reindex(sig.index+pd.Timedelta(minutes=delay+h));en.index=sig.index;ex.index=sig.index
  return (sig*np.log(ex/en)*1e4).dropna()
 p=pnl(0);p5=pnl(5);p15=pnl(15);k=max(1,int(len(p)*.01));trim=p.drop(p.nlargest(k).index);day=p.groupby(p.index.floor("D")).sum();bd=set(day.nlargest(min(5,len(day))).index);no5=p[~p.index.floor("D").isin(bd)]
 keep=[];last=None
 for tt in p.index:
  if last is None or tt>=last+pd.Timedelta(minutes=h):keep.append(tt);last=tt
 pn=p.loc[keep];yrs=p.groupby(p.index.year).mean()
 passed=bool(len(p)>=500 and p.mean()>0 and p5.mean()>0 and p15.mean()>0 and trim.mean()>0 and no5.mean()>0 and pn.mean()>0 and (yrs>0).mean()>=.8)
 rows.append({"target":t,"driver":dv,"feature":fn,"horizon_min":h,"tail":r.tail,"direction":direction,"threshold_abs":thr,"n":len(p),"gross_bp":p.mean(),"hit":(p>0).mean(),"delay5":p5.mean(),"delay15":p15.mean(),"trim_best1pct":trim.mean(),"remove_best5days":no5.mean(),"nonoverlap_n":len(pn),"nonoverlap_bp":pn.mean(),"posyears":(yrs>0).mean(),"yearly":json.dumps({int(k):float(v) for k,v in yrs.items()}),"validation_pass":passed})
 e=time.time()-started;print(f"[GEF25] {i+1}/4 {(i+1)*25}% | elapsed {e/60:.1f}m | {t}<-{dv} {fn} pass={passed}",flush=True)
R=pd.DataFrame(rows);R.to_csv(O/"VALIDATION_RESULTS.csv",index=False)
receipt={"run_id":rid,"status":"COMPLETE","freeze_sha256_verified":sha,"validation_period":"2018-2022","candidate_count":4,"passes":int(R.validation_pass.sum()),"selection_or_retuning_on_validation":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"pass_rule":"n>=500; gross/delay5/delay15/remove-best1%/remove-best5days/non-overlap >0; >=4/5 positive years","instruction":"STOP after validation. Do not open 2023-2025 automatically.","errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));print("\n=== V25 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== VALIDATION RESULTS ===");print(R.to_string(index=False));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V25 compile failed"}
Write-Host "=== GEF V25 - INDEPENDENT VALIDATION 2018-2022 ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V25 validation failed"}
