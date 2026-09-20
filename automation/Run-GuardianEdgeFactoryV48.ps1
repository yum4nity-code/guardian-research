param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v48_rates_replication.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib,re,xml.etree.ElementTree as ET
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";RAW=DL/"raw"/"histdata"
V47=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v47";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v48";OUT.mkdir(parents=True,exist_ok=True)
EXP_FREEZE="53f4979d271f5c720d763c5d9f5e9bef64eaf39651a190cd19fb5b1ae8b8d7fe"
t=time.time();rid="GEF48-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF48] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
runs=sorted([p for p in V47.glob("GEF47-*") if (p/"FROZEN_CANDIDATES.csv").exists() and (p/"RUN_RECEIPT.json").exists()])
src=None
for p in reversed(runs):
 if hashlib.sha256((p/"FROZEN_CANDIDATES.csv").read_bytes()).hexdigest()==EXP_FREEZE:src=p;break
if src is None:raise RuntimeError("Exact V47 frozen candidate artifact not found")
fr=src/"FROZEN_CANDIDATES.csv";sha=hashlib.sha256(fr.read_bytes()).hexdigest()
if sha!=EXP_FREEZE:raise RuntimeError(f"V47 freeze mismatch {sha}")
F=pd.read_csv(fr)
if len(F)!=24:raise RuntimeError(f"Expected 24 frozen candidates, got {len(F)}")
prog(1,12,f"verified immutable V47 freeze {sha[:12]} | {len(F)} candidates")
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
 if dc is None:raise RuntimeError(f"No date parsed {folder}")
 dates=pd.to_datetime(d[dc],errors="coerce");keep=dates.notna().to_numpy();d=d.loc[keep].copy();dates=dates.loc[keep]
 d.index=pd.DatetimeIndex(dates.to_numpy()).tz_localize(None).normalize();d=d.sort_index()
 out={}
 for c in d.columns:
  if c==dc:continue
  s=pd.to_numeric(d[c],errors="coerce")
  if s.notna().sum()>300:out[f"{prefix}_{c}"]=pd.Series(s.to_numpy(),index=d.index)
 return out
nom=parse_dir("nominal_yield_curve","NOM");real=parse_dir("real_yield_curve","REAL")
def tenor(c):
 m=re.search(r"(?:BC_|TC_)(\d+)(MONTH|YEAR)",c)
 return (int(m.group(1))/12 if m and m.group(2)=="MONTH" else int(m.group(1)) if m else None)
nommap={tenor(k):v for k,v in nom.items() if tenor(k) is not None};realmap={tenor(k):v for k,v in real.items() if tenor(k) is not None}
base={}
for ty in [2,5,10,30]:
 if ty in nommap:base[f"NOM{ty}Y"]=nommap[ty]
 if ty in realmap:base[f"REAL{ty}Y"]=realmap[ty]
 if ty in nommap and ty in realmap:base[f"BE{ty}Y"]=nommap[ty]-realmap[ty]
if 2 in nommap and 10 in nommap:base["NOM10_2"]=nommap[10]-nommap[2]
if 5 in realmap and 10 in realmap:base["REAL10_5"]=realmap[10]-realmap[5]
needed=set(F.source_feature)
miss=needed-set(base)
if miss:raise RuntimeError(f"Missing frozen source features {sorted(miss)}")
prog(2,12,"parsed Treasury through 2017; frozen source features available")
markets=sorted(set(F.target));spot={}
for m in markets:
 z=[]
 for y in range(2014,2018):
  p=RAW/m/"M1"/f"{m}_M1_{y}.parquet"
  if not p.exists():continue
  d=pd.read_parquet(p);tc=next(c for c in d if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc]);z.append(d[["close"]])
 if z:
  a=pd.concat(z).sort_index()["close"].resample("1D").last().dropna();a.index=pd.DatetimeIndex(a.index).tz_localize(None).normalize();spot[m]=a
if set(markets)-set(spot):raise RuntimeError(f"Missing replication targets {sorted(set(markets)-set(spot))}")
prog(3,12,f"loaded replication targets {len(spot)} | 2014-2017 only")
rows=[]
for i,r in F.iterrows():
 s0=base[r.source_feature].groupby(level=0).last().sort_index()
 feats={"level_pct":s0.rolling(252,min_periods=126).rank(pct=True),"chg1":s0.diff(1),"chg5":s0.diff(5),"z20":(s0-s0.rolling(20,min_periods=15).mean())/s0.rolling(20,min_periods=15).std()}
 raw=feats[r.feature];x=raw.shift(1)
 if r.feature=="level_pct":lo=pd.Series(.10,index=x.index);hi=pd.Series(.90,index=x.index)
 else:lo=x.rolling(252,min_periods=126).quantile(.10).shift(1);hi=x.rolling(252,min_periods=126).quantile(.90).shift(1)
 q=pd.DataFrame({"x":x,"lo":lo,"hi":hi}).dropna().join(spot[r.target].rename("px"),how="inner").dropna()
 q=q[(q.index.year>=2014)&(q.index.year<=2017)]
 mask=q.x<=q.lo if float(r.tail)<.5 else q.x>=q.hi
 h=int(r.horizon_days);ret=np.log(q.px.shift(-h)/q.px)*1e4
 sgn=(1 if float(r.tail)>.5 else -1) if r["mode"]=="continuation" else (-1 if float(r.tail)>.5 else 1)
 p=(sgn*ret[mask]).dropna();yrs=p.groupby(p.index.year).mean()
 rec={"key":r.key,"source_feature":r.source_feature,"target":r.target,"feature":r.feature,"tail":float(r.tail),"horizon_days":h,"mode":r["mode"],"n":len(p),"gross_bp":float(p.mean()) if len(p) else np.nan,"hit":float((p>0).mean()) if len(p) else np.nan,"positive_year_fraction":float((yrs>0).mean()) if len(yrs) else 0.0}
 rec["replication_pass"]=bool(rec["n"]>=40 and rec["gross_bp"]>0 and rec["hit"]>=.52 and rec["positive_year_fraction"]>=.50)
 rows.append(rec)
 prog(4+i,36,f"{i+1}/24 {r.key} | n={rec['n']} gross={rec['gross_bp']:.2f}bp | {'PASS' if rec['replication_pass'] else 'FAIL'}")
R=pd.DataFrame(rows);R.to_csv(O/"REPLICATION_RESULTS.csv",index=False);S=R[R.replication_pass].copy();S.to_csv(O/"REPLICATION_SURVIVORS.csv",index=False)
ssha=hashlib.sha256((O/"REPLICATION_SURVIVORS.csv").read_bytes()).hexdigest()
prog(28,36,f"replication complete | survivors {len(S)}/24")
# No retuning, no rescue. Frozen definitions only.
receipt={"run_id":rid,"status":"COMPLETE_FROZEN_REPLICATION","source_v47":src.name,"verified_freeze_sha256":sha,"period":"2014-2017 only","frozen_candidate_count":24,"replication_survivor_count":len(S),"survivor_sha256":ssha,"retuning":False,"rescue_search":False,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(29,36,"results + receipt written")
prog(30,36,"assertion: 2018+ target data not loaded")
prog(31,36,"assertion: frozen V47 definitions unchanged")
prog(32,36,"assertion: no rescue search")
prog(33,36,"next gate: pre-validation robustness on replication survivors only")
prog(34,36,"2018-2022 remains sealed")
prog(35,36,"2023-2025 locked OOS remains sealed")
prog(36,36,"STOP")
print("\n=== V48 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== REPLICATION SURVIVORS ===");print(S.to_string(index=False) if len(S) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V48 compile failed"}
Write-Host "=== GEF V48 - RATES FROZEN REPLICATION 2014-2017 ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V48 failed"}
