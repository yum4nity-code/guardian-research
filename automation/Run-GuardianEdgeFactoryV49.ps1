param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v49_rates_robustness.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib,re,xml.etree.ElementTree as ET
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";RAW=DL/"raw"/"histdata"
V48=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v48";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v49";OUT.mkdir(parents=True,exist_ok=True)
EXP="06d9f3ab60d8ff8837b3764559decd82c062ee7293406bd842ff145d9986a828"
t=time.time();rid="GEF49-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF49] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
runs=sorted([p for p in V48.glob("GEF48-*") if (p/"REPLICATION_SURVIVORS.csv").exists()])
src=None
for p in reversed(runs):
 if hashlib.sha256((p/"REPLICATION_SURVIVORS.csv").read_bytes()).hexdigest()==EXP:src=p;break
if src is None:raise RuntimeError("Exact V48 survivor artifact not found")
fr=src/"REPLICATION_SURVIVORS.csv";sha=hashlib.sha256(fr.read_bytes()).hexdigest();F=pd.read_csv(fr)
if sha!=EXP or len(F)!=12:raise RuntimeError(f"V48 survivor mismatch sha={sha} n={len(F)}")
prog(1,20,f"verified immutable V48 survivors {sha[:12]} | n=12")
def parse_dir(folder,prefix):
 rows=[]
 for y in range(2009,2018):
  p=DL/"raw"/"treasury"/folder/f"{folder}_{y}.xml"
  if not p.exists():continue
  root=ET.parse(p).getroot()
  for entry in root.iter():
   vals={}
   for x in entry.iter():
    tag=x.tag.split("}")[-1];txt=(x.text or "").strip()
    if txt and (tag.startswith("NEW_DATE") or tag.startswith("BC_") or tag.startswith("TC_") or tag=="NEW_DATE"):vals[tag]=txt
   if vals:rows.append(vals)
 d=pd.DataFrame(rows).drop_duplicates().reset_index(drop=True);dc=next((c for c in d if "DATE" in c),None)
 dates=pd.to_datetime(d[dc],errors="coerce");keep=dates.notna().to_numpy();d=d.loc[keep].copy();dates=dates.loc[keep]
 d.index=pd.DatetimeIndex(dates.to_numpy()).tz_localize(None).normalize();d=d.sort_index();out={}
 for c in d.columns:
  if c==dc:continue
  z=pd.to_numeric(d[c],errors="coerce")
  if z.notna().sum()>300:out[f"{prefix}_{c}"]=pd.Series(z.to_numpy(),index=d.index)
 return out
nom=parse_dir("nominal_yield_curve","NOM");real=parse_dir("real_yield_curve","REAL")
def tenor(c):
 m=re.search(r"(?:BC_|TC_)(\d+)(MONTH|YEAR)",c)
 return (int(m.group(1))/12 if m and m.group(2)=="MONTH" else int(m.group(1)) if m else None)
nm={tenor(k):v for k,v in nom.items() if tenor(k)!=None};rm={tenor(k):v for k,v in real.items() if tenor(k)!=None};base={}
for y in [2,5,10,30]:
 if y in nm:base[f"NOM{y}Y"]=nm[y]
 if y in rm:base[f"REAL{y}Y"]=rm[y]
 if y in nm and y in rm:base[f"BE{y}Y"]=nm[y]-rm[y]
if 2 in nm and 10 in nm:base["NOM10_2"]=nm[10]-nm[2]
if 5 in rm and 10 in rm:base["REAL10_5"]=rm[10]-rm[5]
prog(2,20,"Treasury source reconstructed through 2017 only")
spot={}
for m in sorted(set(F.target)):
 z=[]
 for y in range(2014,2018):
  p=RAW/m/"M1"/f"{m}_M1_{y}.parquet";d=pd.read_parquet(p);tc=next(c for c in d if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc]);z.append(d[["close"]])
 a=pd.concat(z).sort_index()["close"].resample("1D").last().dropna();a.index=pd.DatetimeIndex(a.index).tz_localize(None).normalize();spot[m]=a
prog(3,20,f"loaded {len(spot)} targets | 2014-2017 only")
rng=np.random.default_rng(490049);rows=[]
for j,r in F.iterrows():
 s0=base[r.source_feature].groupby(level=0).last().sort_index()
 feats={"level_pct":s0.rolling(252,min_periods=126).rank(pct=True),"chg5":s0.diff(5)}
 raw=feats[r.feature]
 def pnl(extra_lag=0,thr=None):
  x=raw.shift(1+extra_lag)
  if r.feature=="level_pct":
   lo=pd.Series(.10 if thr is None else thr,index=x.index);hi=pd.Series(.90 if thr is None else 1-thr,index=x.index)
  else:
   qlo=.10 if thr is None else thr;qhi=.90 if thr is None else 1-thr
   lo=x.rolling(252,min_periods=126).quantile(qlo).shift(1);hi=x.rolling(252,min_periods=126).quantile(qhi).shift(1)
  q=pd.DataFrame({"x":x,"lo":lo,"hi":hi}).dropna().join(spot[r.target].rename("px"),how="inner").dropna();q=q[(q.index.year>=2014)&(q.index.year<=2017)]
  mask=q.x<=q.lo if float(r["tail"])<.5 else q.x>=q.hi;h=int(r.horizon_days);ret=np.log(q.px.shift(-h)/q.px)*1e4
  sg=(1 if float(r["tail"])>.5 else -1) if r["mode"]=="continuation" else (-1 if float(r["tail"])>.5 else 1)
  return (sg*ret[mask]).dropna()
 p=pnl();n=len(p);gross=float(p.mean())
 def trim(frac):
  k=max(1,int(np.floor(n*frac)));return float(p.sort_values().iloc[:-k].mean()) if n>k else np.nan
 byday=p.groupby(p.index.normalize()).sum().sort_values();rm5=float(byday.iloc[:-min(5,len(byday)-1)].mean()) if len(byday)>5 else np.nan
 non=p.iloc[::5];nonmu=float(non.mean()) if len(non) else np.nan
 lag1=float(pnl(1).mean());lag2=float(pnl(2).mean())
 neigh=[float(pnl(0,x).mean()) for x in [.075,.10,.125]]
 yrs=p.groupby(p.index.year).mean();yrfrac=float((yrs>0).mean())
 boots=np.array([rng.choice(p.to_numpy(),size=n,replace=True).mean() for _ in range(1000)]);blo=float(np.quantile(boots,.025))
 signs=np.array([np.mean(p.to_numpy()*rng.choice([-1.,1.],n)) for _ in range(1000)]);nullp=float((np.sum(np.abs(signs)>=abs(gross))+1)/1001)
 passed=bool(n>=40 and gross>0 and trim(.01)>0 and trim(.02)>0 and rm5>0 and nonmu>0 and lag1>0 and lag2>0 and min(neigh)>0 and yrfrac>=.75 and blo>0 and nullp<.05)
 rows.append({"key":r.key,"n":n,"gross_bp":gross,"trim1_bp":trim(.01),"trim2_bp":trim(.02),"remove_best5days_bp":rm5,"nonoverlap5_bp":nonmu,"extra_lag1_bp":lag1,"extra_lag2_bp":lag2,"neighbor_075_bp":neigh[0],"neighbor_10_bp":neigh[1],"neighbor_125_bp":neigh[2],"positive_year_fraction":yrfrac,"bootstrap_lo95_bp":blo,"signflip_p":nullp,"robustness_pass":passed})
 prog(3+j+1,20,f"{j+1}/12 {r.key} | gross {gross:.2f} trim2 {trim(.02):.2f} nonov {nonmu:.2f} lag2 {lag2:.2f} | {'PASS' if passed else 'FAIL'}")
R=pd.DataFrame(rows);R.to_csv(O/"ROBUSTNESS_RESULTS.csv",index=False);S=R[R.robustness_pass].copy();S.to_csv(O/"ROBUSTNESS_SURVIVORS.csv",index=False);ssha=hashlib.sha256((O/"ROBUSTNESS_SURVIVORS.csv").read_bytes()).hexdigest()
prog(16,20,f"strict robustness complete | survivors {len(S)}/12 | sha {ssha[:12]}")
receipt={"run_id":rid,"status":"COMPLETE_PREVALIDATION_ROBUSTNESS","source_v48":src.name,"verified_survivor_sha256":sha,"period":"2014-2017 only","input_count":12,"robust_survivor_count":len(S),"robust_survivor_sha256":ssha,"gate_frozen_before_results":True,"retuning":False,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(17,20,"receipt written; no retuning/rescue")
prog(18,20,"2018-2022 remains sealed")
prog(19,20,"2023-2025 and 2026 remain sealed")
prog(20,20,"STOP")
print("\n=== V49 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== ROBUSTNESS SURVIVORS ===");print(S.to_string(index=False) if len(S) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V49 compile failed"}
Write-Host "=== GEF V49 - RATES PRE-VALIDATION ROBUSTNESS 2014-2017 ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V49 failed"}
