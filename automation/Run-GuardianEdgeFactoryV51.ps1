param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v51_rates_validation.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib,re,xml.etree.ElementTree as ET
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";RAW=DL/"raw"/"histdata";V50=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v50";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v51";OUT.mkdir(parents=True,exist_ok=True)
EXP_MAN="8f48a2048c9f42d13dafd901361886525431cdd67efef08f2b0800eb7fa02fc0";EXP_GATE="4442489e774830a33d97d9bceb77053b81c676c2fbddb8eb52012112904fd06c"
t=time.time();rid="GEF51-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF51] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
runs=sorted([p for p in V50.glob("GEF50-*") if (p/"IMMUTABLE_VALIDATION_MANIFEST.csv").exists() and (p/"VALIDATION_GATE.json").exists()])
src=None
for p in reversed(runs):
 if hashlib.sha256((p/"IMMUTABLE_VALIDATION_MANIFEST.csv").read_bytes()).hexdigest()==EXP_MAN and hashlib.sha256((p/"VALIDATION_GATE.json").read_bytes()).hexdigest()==EXP_GATE:src=p;break
if src is None:raise RuntimeError("Exact V50 immutable freeze/gate not found")
F=pd.read_csv(src/"IMMUTABLE_VALIDATION_MANIFEST.csv");gate=json.loads((src/"VALIDATION_GATE.json").read_text())
if len(F)!=3:raise RuntimeError("Expected exactly 3 frozen candidates")
prog(1,12,f"verified V50 manifest {EXP_MAN[:12]} + gate {EXP_GATE[:12]} | n=3")
def parse_dir(folder,prefix):
 rows=[]
 for y in range(2009,2023):
  p=DL/"raw"/"treasury"/folder/f"{folder}_{y}.xml"
  if not p.exists():continue
  root=ET.parse(p).getroot()
  for entry in root.iter():
   vals={}
   for x in entry.iter():
    tag=x.tag.split("}")[-1];txt=(x.text or "").strip()
    if txt and (tag.startswith("NEW_DATE") or tag.startswith("BC_") or tag.startswith("TC_") or tag=="NEW_DATE"):vals[tag]=txt
   if vals:rows.append(vals)
 d=pd.DataFrame(rows).drop_duplicates().reset_index(drop=True);dc=next((c for c in d if "DATE" in c),None);dates=pd.to_datetime(d[dc],errors="coerce");keep=dates.notna().to_numpy();d=d.loc[keep].copy();dates=dates.loc[keep];d.index=pd.DatetimeIndex(dates.to_numpy()).tz_localize(None).normalize();d=d.sort_index();out={}
 for c in d.columns:
  if c==dc:continue
  z=pd.to_numeric(d[c],errors="coerce")
  if z.notna().sum()>300:out[f"{prefix}_{c}"]=pd.Series(z.to_numpy(),index=d.index)
 return out
nom=parse_dir("nominal_yield_curve","NOM");real=parse_dir("real_yield_curve","REAL")
def tenor(c):
 m=re.search(r"(?:BC_|TC_)(\d+)(MONTH|YEAR)",c);return (int(m.group(1))/12 if m and m.group(2)=="MONTH" else int(m.group(1)) if m else None)
nm={tenor(k):v for k,v in nom.items() if tenor(k)!=None};rm={tenor(k):v for k,v in real.items() if tenor(k)!=None};base={}
for y in [5,30]:
 if y in nm:base[f"NOM{y}Y"]=nm[y]
 if y in rm:base[f"REAL{y}Y"]=rm[y]
 if y in nm and y in rm:base[f"BE{y}Y"]=nm[y]-rm[y]
prog(2,12,"Treasury sources reconstructed causally through 2022")
keys=F.key.tolist();markets=sorted({k.split("|")[1] for k in keys});spot={}
for m in markets:
 z=[]
 for y in range(2018,2023):
  p=RAW/m/"M1"/f"{m}_M1_{y}.parquet"
  if not p.exists():raise RuntimeError(f"Missing target file {p}")
  d=pd.read_parquet(p);tc=next(c for c in d if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc]);z.append(d[["close"]])
 a=pd.concat(z).sort_index()["close"].resample("1D").last().dropna();a.index=pd.DatetimeIndex(a.index).tz_localize(None).normalize();spot[m]=a
prog(3,12,f"VALIDATION WINDOW OPENED | loaded {len(spot)} targets | 2018-2022 only")
rows=[]
for j,key in enumerate(keys):
 sf,m,feat,tail,h,mode=key.split("|");tail=float(tail);h=int(h);s0=base[sf].groupby(level=0).last().sort_index();raw=s0.diff(5) if feat=="chg5" else s0.rolling(252,min_periods=126).rank(pct=True)
 def pnl(extra=0):
  x=raw.shift(1+extra)
  if feat=="level_pct":lo=pd.Series(.10,index=x.index);hi=pd.Series(.90,index=x.index)
  else:lo=x.rolling(252,min_periods=126).quantile(.10).shift(1);hi=x.rolling(252,min_periods=126).quantile(.90).shift(1)
  q=pd.DataFrame({"x":x,"lo":lo,"hi":hi}).dropna().join(spot[m].rename("px"),how="inner").dropna();q=q[(q.index.year>=2018)&(q.index.year<=2022)]
  mask=q.x<=q.lo if tail<.5 else q.x>=q.hi;ret=np.log(q.px.shift(-h)/q.px)*1e4;sg=(1 if tail>.5 else -1) if mode=="continuation" else (-1 if tail>.5 else 1)
  return (sg*ret[mask]).dropna()
 p=pnl();n=len(p);gross=float(p.mean()) if n else np.nan;hit=float((p>0).mean()) if n else np.nan;yrs=p.groupby(p.index.year).mean();pyf=float((yrs>0).mean()) if len(yrs) else 0
 k=max(1,int(np.floor(n*.01)));trim=float(p.sort_values().iloc[:-k].mean()) if n>k else np.nan
 bd=p.groupby(p.index.normalize()).sum().sort_values();rm5=float(bd.iloc[:-min(5,len(bd)-1)].mean()) if len(bd)>5 else np.nan
 non=float(p.iloc[::5].mean()) if n else np.nan;lag1=float(pnl(1).mean())
 passed=bool(n>=40 and gross>0 and hit>=.52 and pyf>=.60 and trim>0 and rm5>0 and non>0 and lag1>0)
 rows.append({"key":key,"n":n,"gross_bp":gross,"hit":hit,"positive_year_fraction":pyf,"trim1_bp":trim,"remove_best5days_bp":rm5,"nonoverlap_h5_bp":non,"extra_lag1_bp":lag1,"validation_pass":passed})
 prog(4+j,12,f"{j+1}/3 {key} | n={n} gross={gross:.2f} hit={hit:.3f} years={pyf:.2f} trim1={trim:.2f} rm5={rm5:.2f} nonov={non:.2f} lag1={lag1:.2f} | {'PASS' if passed else 'FAIL'}")
R=pd.DataFrame(rows);R.to_csv(O/"VALIDATION_RESULTS.csv",index=False);S=R[R.validation_pass].copy();S.to_csv(O/"VALIDATION_SURVIVORS.csv",index=False);ssha=hashlib.sha256((O/"VALIDATION_SURVIVORS.csv").read_bytes()).hexdigest()
prog(7,12,f"independent validation complete | survivors {len(S)}/3 | sha {ssha[:12]}")
receipt={"run_id":rid,"status":"COMPLETE_INDEPENDENT_VALIDATION_STOP_BEFORE_LOCKED_OOS","source_v50":src.name,"verified_manifest_sha256":EXP_MAN,"verified_gate_sha256":EXP_GATE,"period":"2018-2022 only","input_count":3,"validation_survivor_count":len(S),"validation_survivor_sha256":ssha,"retuning":False,"rescue_search":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(8,12,"results + receipt written")
prog(9,12,"no retuning / no rescue")
prog(10,12,"2023-2025 locked OOS remains sealed")
prog(11,12,"2026 remains protected")
prog(12,12,"STOP - human review before any OOS")
print("\n=== V51 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== VALIDATION RESULTS ===");print(R.to_string(index=False));print("\n=== VALIDATION SURVIVORS ===");print(S.to_string(index=False) if len(S) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V51 compile failed"}
Write-Host "=== GEF V51 - INDEPENDENT RATES VALIDATION 2018-2022 ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V51 failed"}
