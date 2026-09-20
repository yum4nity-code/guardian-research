param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v44_independent_validation.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");RAW=ROOT/"DataLake"/"raw"/"histdata";CBOE=ROOT/"DataLake"/"normalized"/"cboe_pre2023";V43=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v43";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v44";OUT.mkdir(parents=True,exist_ok=True)
EXP_MAN="7f91a922b5bf12d067c4d7bdba271903c38f19f2b24103bd4ac1ea9d33ac097b";EXP_GATE="1aa64b6d46ca1f465c1ef68f89e1f67cbc92fa633f10ab3f9a4dbf15cc58836e"
t=time.time();rid="GEF44-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF44] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
runs=sorted([p for p in V43.glob("GEF43-*") if (p/"IMMUTABLE_CANDIDATE_MANIFEST.csv").exists() and (p/"VALIDATION_GATE.json").exists()])
if not runs:raise RuntimeError("No V43 freeze")
src=runs[-1];mf=src/"IMMUTABLE_CANDIDATE_MANIFEST.csv";gf=src/"VALIDATION_GATE.json"
msha=hashlib.sha256(mf.read_bytes()).hexdigest();gsha=hashlib.sha256(gf.read_bytes()).hexdigest()
if msha!=EXP_MAN or gsha!=EXP_GATE:raise RuntimeError(f"Freeze hash mismatch manifest={msha} gate={gsha}")
F=pd.read_csv(mf);gate=json.loads(gf.read_text())
if len(F)!=5:raise RuntimeError("Expected 5 frozen candidates")
prog(1,12,f"V43 hashes verified | manifest {msha[:12]} gate {gsha[:12]}")
# Independent reconstruction. Cboe history allowed as feature warmup; target evaluation restricted 2018-2022.
spec={"VIX":("VIX_History_PRE2023.csv","CLOSE"),"VIX9D":("VIX9D_History_PRE2023.csv","CLOSE")}
ivs={}
for name,(fn,col) in spec.items():
 d=pd.read_csv(CBOE/fn);d["DATE"]=pd.to_datetime(d["DATE"]);s=pd.to_numeric(d[col],errors="coerce");s.index=d["DATE"];ivs[name]=s.sort_index()
prog(2,12,"Cboe sources loaded; feature logic reconstructed independently")
spot={}
for m in sorted(F["target"].unique()):
 z=[]
 for y in range(2017,2023): # 2017 warmup + validation only
  p=RAW/m/"M1"/f"{m}_M1_{y}.parquet"
  if not p.exists():raise RuntimeError(f"Missing {p}")
  d=pd.read_parquet(p);tc=next(c for c in d if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc]);z.append(d[["close"]])
 spot[m]=pd.concat(z).sort_index()["close"].resample("1D").last().dropna()
prog(3,12,"spot loaded: 2017 warmup + 2018-2022 validation only")
def rawfeat(source,feat):
 s=ivs[source]
 if feat=="chg1":return s.pct_change()
 if feat=="chg5":return s.pct_change(5)
 if feat=="level_pct":return s.rolling(252,min_periods=126).rank(pct=True)
 raise RuntimeError(feat)
def pnl(r,extra=0):
 source,target,feat=str(r["source"]),str(r["target"]),str(r["feature"]);tail=float(r["tail"]);h=int(r["horizon_days"]);mode=str(r["mode"])
 x=rawfeat(source,feat).shift(1+extra);a=spot[target];q=pd.concat([x.rename("x"),a.rename("px")],axis=1,join="inner").dropna()
 q=q[(q.index>=pd.Timestamp("2018-01-01"))&(q.index<=pd.Timestamp("2022-12-31"))]
 if feat=="level_pct":mask=q.x<=tail if tail<.5 else q.x>=tail
 else:
  lo=x.rolling(252,min_periods=126).quantile(.10).shift(1);hi=x.rolling(252,min_periods=126).quantile(.90).shift(1);mask=q.x<=lo.reindex(q.index) if tail<.5 else q.x>=hi.reindex(q.index)
 y=np.log(q.px.shift(-h)/q.px)*1e4;yy=y[mask].dropna();direction=1 if mode=="continuation" else -1
 return direction*(-1 if tail<.5 else 1)*yy
rows=[]
for j,r in F.iterrows():
 p=pnl(r,0);px=pnl(r,1);n=len(p);k1=max(1,int(np.ceil(n*.01)));k2=max(1,int(np.ceil(n*.02)))
 tr1=p.drop(p.nlargest(k1).index);tr2=p.drop(p.nlargest(k2).index);rm5=p.drop(p.nlargest(min(5,n)).index)
 gap=pd.Timedelta(days=int(r["horizon_days"]));chosen=[];last=None
 for ts,v in p.items():
  if last is None or ts-last>=gap:chosen.append((ts,v));last=ts
 no=pd.Series([v for _,v in chosen],index=[x for x,_ in chosen],dtype=float)
 yrs=p.groupby(p.index.year).mean();pos=float((yrs>0).mean()) if len(yrs) else 0
 checks={"minimum_events":n>=80,"gross_mean_bp":p.mean()>0,"positive_year_fraction":pos>=.60,"trim_best_1pct_mean_bp":tr1.mean()>0,"trim_best_2pct_mean_bp":tr2.mean()>0,"remove_best_5_events_mean_bp":rm5.mean()>0,"nonoverlap_mean_bp":len(no)>0 and no.mean()>0,"extra_information_lag_1obs_mean_bp":px.mean()>0}
 passed=all(checks.values())
 rows.append({"candidate_id":r["candidate_id"],"source":r["source"],"target":r["target"],"feature":r["feature"],"tail":r["tail"],"horizon_days":r["horizon_days"],"mode":r["mode"],"n":n,"gross_bp":float(p.mean()),"hit":float((p>0).mean()),"positive_year_fraction":pos,"trim1_bp":float(tr1.mean()),"trim2_bp":float(tr2.mean()),"remove_best5_bp":float(rm5.mean()),"nonoverlap_n":len(no),"nonoverlap_bp":float(no.mean()),"extra_lag1_bp":float(px.mean()),"yearly":";".join(f"{int(y)}:{v:.6f}" for y,v in yrs.items()),"gate_checks":json.dumps(checks,sort_keys=True),"validation_pass":passed})
 prog(4+j,12,f"{r['candidate_id']} {r['source']}->{r['target']} | n={n} gross={p.mean():.2f} trim2={tr2.mean():.2f} nonov={no.mean():.2f} lag+1={px.mean():.2f} years+={pos:.0%} | {'PASS' if passed else 'FAIL'}")
R=pd.DataFrame(rows);R.to_csv(O/"INDEPENDENT_VALIDATION_RESULTS.csv",index=False);P=R[R.validation_pass].copy();P.to_csv(O/"VALIDATION_SURVIVORS.csv",index=False)
rsha=hashlib.sha256((O/"INDEPENDENT_VALIDATION_RESULTS.csv").read_bytes()).hexdigest();psha=hashlib.sha256((O/"VALIDATION_SURVIVORS.csv").read_bytes()).hexdigest()
prog(9,12,f"validation complete | pass {len(P)}/5")
receipt={"run_id":rid,"status":"COMPLETE_STOP_BEFORE_LOCKED_OOS","source_v43":src.name,"verified_manifest_sha256":msha,"verified_gate_sha256":gsha,"validation_period":"2018-2022","candidate_count":5,"validation_pass_count":len(P),"all_candidates_pass":bool(len(P)==5),"results_sha256":rsha,"survivors_sha256":psha,"retuning":False,"replacement_or_rescue":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"instruction":"STOP. Human review required before any 2023-2025 access."}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(10,12,f"results sha {rsha[:12]} | survivors sha {psha[:12]}")
prog(11,12,"assertions: no retuning; 2023-2025 untouched; 2026 untouched")
prog(12,12,"STOP - HUMAN REVIEW BEFORE LOCKED OOS")
print("\n=== V44 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== ALL VALIDATION RESULTS ===");print(R.to_string(index=False));print("\n=== VALIDATION SURVIVORS ===");print(P.to_string(index=False) if len(P) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V44 compile failed"}
Write-Host "=== GEF V44 - INDEPENDENT 2018-2022 VALIDATION ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V44 failed"}
