param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v36_validation.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); RAW=ROOT/"DataLake"/"raw"/"histdata"; V35=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v35"; OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v36"; OUT.mkdir(parents=True,exist_ok=True)
t=time.time(); rid="GEF36-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"); O=OUT/rid; O.mkdir()
def prog(i,n,msg):
 e=time.time()-t; eta=e/i*(n-i) if i else 0; print(f"[GEF36] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
runs=sorted([p for p in V35.glob("GEF35-*") if (p/"FROZEN_VALIDATION_MANIFEST.json").exists() and (p/"RUN_RECEIPT.json").exists()])
if not runs: raise RuntimeError("No V35 freeze")
src=runs[-1]; rb=json.loads((src/"RUN_RECEIPT.json").read_text()); mf=src/"FROZEN_VALIDATION_MANIFEST.json"; actual=hashlib.sha256(mf.read_bytes()).hexdigest()
EXPECTED="9438361bd3e8112619c1f0214d621ce57b4db04929e23a6423b69408cbe60369"
if rb.get("status")!="FROZEN_AWAITING_VALIDATION" or actual!=rb.get("manifest_sha256") or actual!=EXPECTED: raise RuntimeError("V35 manifest integrity failure")
M=json.loads(mf.read_text()); C=M["candidate"]; prog(1,9,f"V35 manifest verified {actual[:12]}")
if C["market"]!="XAGUSD" or C["regime"]!="normal" or int(C["horizon_min"])!=240 or C["mode"]!="reversal" or int(C["bar_minutes"])!=15: raise RuntimeError("Frozen candidate identity mismatch")
prog(2,9,"candidate identity locked; no parameter selection")
z=[]
for k,y0 in enumerate(range(2018,2023),3):
 pth=RAW/"XAGUSD"/"M1"/f"XAGUSD_M1_{y0}.parquet"
 if not pth.exists(): raise RuntimeError(f"Missing validation file {pth}")
 d=pd.read_parquet(pth); tc=next(c for c in d if c.lower() in ("datetime","time","timestamp")); d.index=pd.to_datetime(d[tc])
 z.append(d[["close"]].sort_index().resample("15min",label="right",closed="left").last().dropna()); prog(k,9,f"opened validation year {y0}")
a=pd.concat(z).sort_index().close; ret=np.log(a/a.shift(1)); rv=ret.rolling(16,min_periods=16).std(); slow=rv.rolling(320,min_periods=80).median(); ratio=rv/slow
reg=(ratio>.75)&(ratio<1.5); shock=ret.abs()>=ret.abs().rolling(20*96,min_periods=480).quantile(.95).shift(1)
y=np.log(a.shift(-16)/a)*1e4; q=pd.concat([ret.rename("r"),y.rename("y"),reg.rename("reg"),shock.rename("shock")],axis=1).dropna(); q=q[q.reg&q.shock]; p=-np.sign(q.r)*q.y
yy=np.log(a.shift(-17)/a.shift(-1))*1e4; qq=pd.concat([ret.rename("r"),yy.rename("y"),reg.rename("reg"),shock.rename("shock")],axis=1).dropna(); qq=qq[qq.reg&qq.shock]; p15=-np.sign(qq.r)*qq.y
trim=p.drop(p.nlargest(max(1,int(np.ceil(len(p)*.01)))).index); ds=p.groupby(p.index.normalize()).sum().sort_values(ascending=False); p5days=p[~p.index.normalize().isin(set(ds.head(5).index))]
chosen=[];last=None
for ts,v in p.items():
 if last is None or (ts-last).total_seconds()>=240*60: chosen.append((ts,v));last=ts
no=pd.Series([v for _,v in chosen],index=[x for x,_ in chosen]); yrs=p.groupby(p.index.year).agg(["count","mean"]); pos=float((yrs["mean"]>0).mean())
result={"market":"XAGUSD","regime":"normal","horizon_min":240,"mode":"reversal","n":len(p),"gross_bp":float(p.mean()),"hit":float((p>0).mean()),"delay15_bp":float(p15.mean()),"trim_best1pct_bp":float(trim.mean()),"remove_best5days_bp":float(p5days.mean()),"nonoverlap_n":len(no),"nonoverlap_bp":float(no.mean()),"positive_year_fraction":pos,"all_five_years_present":len(yrs)==5,"yearly":{str(int(i)):{"n":int(r["count"]),"gross_bp":float(r["mean"])} for i,r in yrs.iterrows()}}
result["validation_pass"]=bool(len(p)>=300 and result["gross_bp"]>0 and result["delay15_bp"]>0 and result["trim_best1pct_bp"]>0 and result["remove_best5days_bp"]>0 and result["nonoverlap_bp"]>0 and len(yrs)==5 and pos>=.8)
prog(8,9,f"validation computed | gross {result['gross_bp']:.3f} trim1 {result['trim_best1pct_bp']:.3f} nonoverlap {result['nonoverlap_bp']:.3f} | {'PASS' if result['validation_pass'] else 'FAIL'}")
(O/"VALIDATION_RESULT.json").write_text(json.dumps(result,indent=2)); receipt={"run_id":rid,"status":"COMPLETE","source_v35":src.name,"verified_manifest_sha256":actual,"validation_period":"2018-2022 only","candidate_count":1,"retuning":False,"validation_result":"PASS" if result["validation_pass"] else "FAIL","locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":[],"instruction":"STOP. Do not open locked OOS. If PASS, perform pre-OOS forensic on <=2022 and human review."}; (O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2)); prog(9,9,"STOP - 2023+ untouched")
print("\n=== V36 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== INDEPENDENT VALIDATION ===");print(json.dumps(result,indent=2));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V36 compile failed"}
Write-Host "=== GEF V36 - INDEPENDENT 2018-2022 VALIDATION ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V36 failed"}
