param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v47_rates_discovery.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib,re,xml.etree.ElementTree as ET
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";RAW=DL/"raw"/"histdata";V46=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v46";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v47";OUT.mkdir(parents=True,exist_ok=True)
EXP="1a330d39b80581f13d719de29416058da0c2f59407e53e82515f671d32c3d72b"
t=time.time();rid="GEF47-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF47] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
runs=sorted([p for p in V46.glob("GEF46-*") if (p/"CAUSAL_DESIGN.json").exists()]);src=runs[-1];sha=hashlib.sha256((src/"CAUSAL_DESIGN.json").read_bytes()).hexdigest()
if sha!=EXP:raise RuntimeError(f"V46 design mismatch {sha}")
prog(1,12,f"verified V46 design {sha[:12]}")
# Parse Treasury XML generically from 2009-2013 for warmup+discovery; local-name tags become columns.
def parse_dir(folder,prefix):
 rows=[]
 for y in range(2009,2014):
  p=DL/"raw"/"treasury"/folder/f"{folder}_{y}.xml"
  if not p.exists():continue
  root=ET.parse(p).getroot()
  for entry in root.iter():
   vals={}
   for x in entry.iter():
    tag=x.tag.split("}")[-1]
    txt=(x.text or "").strip()
    if txt and (tag.startswith("NEW_DATE") or tag.startswith("BC_") or tag.startswith("TC_") or tag=="NEW_DATE"):vals[tag]=txt
   if vals:rows.append(vals)
 d=pd.DataFrame(rows).drop_duplicates().reset_index(drop=True)
 dc=next((c for c in d if "DATE" in c),None)
 if dc is None:raise RuntimeError(f"No date parsed {folder}; cols={list(d)[:20]}")
 dates=pd.to_datetime(d[dc],errors="coerce"); keep=dates.notna().to_numpy(); d=d.loc[keep].copy(); dates=dates.loc[keep]; d.index=pd.DatetimeIndex(dates.to_numpy()).tz_localize(None).normalize(); d=d.sort_index()
 out={}
 for c in d.columns:
  if c==dc:continue
  s=pd.to_numeric(d[c],errors="coerce")
  if s.notna().sum()>300:out[f"{prefix}_{c}"]=pd.Series(s.to_numpy(),index=d.index)
 return out
nom=parse_dir("nominal_yield_curve","NOM");real=parse_dir("real_yield_curve","REAL");series={**nom,**real}
if not series:raise RuntimeError("No Treasury rate series parsed")
prog(2,12,f"parsed Treasury warmup/discovery | {len(series)} raw rate series")
# Keep a compact economically distinct tenor set by available column names, then derive slopes/breakevens from matching tenors.
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
if 5 in base and False:pass
if len(base)<4:raise RuntimeError(f"Too few canonical rate series {list(base)}")
for k,v0 in base.items():
 if v0.notna().sum()<300:raise RuntimeError(f"Rate series {k} has only {v0.notna().sum()} finite observations")
prog(3,12,"canonical features validated: "+",".join(f"{k}[{v0.notna().sum()}]" for k,v0 in base.items()))
markets=["XAUUSD","XAGUSD","UDXUSD","EURUSD","USDJPY","SPXUSD","NSXUSD"]
spot={}
for m in markets:
 z=[]
 for y in range(2010,2014):
  p=RAW/m/"M1"/f"{m}_M1_{y}.parquet"
  if not p.exists():continue
  d=pd.read_parquet(p);tc=next(c for c in d if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc]);z.append(d[["close"]])
 if z:spot[m]=pd.concat(z).sort_index()["close"].resample("1D").last().dropna(); spot[m].index=pd.DatetimeIndex(spot[m].index).tz_localize(None).normalize()
prog(4,12,f"loaded discovery targets {len(spot)} | 2010-2013 only")
for k,v0 in base.items():
 ov={m:len(v0.index.intersection(a.index)) for m,a in spot.items()}
 if max(ov.values(),default=0)<100:raise RuntimeError(f"Insufficient date overlap for {k}: {ov}")
# Conservative next-observation availability. Feature families frozen: level percentile, 1d/5d changes, z20.
cells=[];pnls={}
join_diag=[]
for name,s0 in base.items():
 s0=s0.groupby(level=0).last().sort_index()
 feats={"level_pct":s0.rolling(252,min_periods=126).rank(pct=True),"chg1":s0.diff(1),"chg5":s0.diff(5),"z20":(s0-s0.rolling(20,min_periods=15).mean())/s0.rolling(20,min_periods=15).std()}
 for fn,raw in feats.items():
  x=raw.shift(1)
  if fn=="level_pct":
   lo=pd.Series(.10,index=x.index);hi=pd.Series(.90,index=x.index)
  else:
   lo=x.rolling(252,min_periods=126).quantile(.10).shift(1);hi=x.rolling(252,min_periods=126).quantile(.90).shift(1)
  for m,a in spot.items():
   pre=pd.DataFrame({"x":x,"lo":lo,"hi":hi}).dropna()
   q=pre.join(a.rename("px"),how="inner").dropna();q=q[(q.index.year>=2010)&(q.index.year<=2013)]
   join_diag.append((name,fn,m,int(x.notna().sum()),len(pre),len(q),int((q.x<=q.lo).sum()),int((q.x>=q.hi).sum())))
   for tail,mask in [(.1,q.x<=q.lo),(.9,q.x>=q.hi)]:
    for h in [1,5]:
     ret=np.log(q.px.shift(-h)/q.px)*1e4
     for mode,sgn in [("continuation",1 if tail>.5 else -1),("reversal",-1 if tail>.5 else 1)]:
      p=(sgn*ret[mask]).dropna();n=len(p)
      if n<40:continue
      mu=float(p.mean());hit=float((p>0).mean());yrs=p.groupby(p.index.year).mean();pos=float((yrs>0).mean())
      key=f"{name}|{m}|{fn}|{tail}|{h}|{mode}";pnls[key]=p
      cells.append({"source_feature":name,"target":m,"feature":fn,"tail":tail,"horizon_days":h,"mode":mode,"n":n,"gross_bp":mu,"hit":hit,"positive_year_fraction":pos,"key":key})
prog(5,12,f"evaluated {len(cells)} cells")
if not cells:
 pd.DataFrame(join_diag,columns=["source_feature","feature","target","x_finite","threshold_ready","join_n","low_n","high_n"]).to_csv(O/"JOIN_DIAGNOSTICS.csv",index=False)
 raise RuntimeError("No discovery cells after validated source/spot overlaps; JOIN_DIAGNOSTICS.csv written")
R=pd.DataFrame(cells)
# Screen is deliberately modest; replication is the real filter.
S=R[(R.gross_bp>8)&(R.hit>=.54)&(R.positive_year_fraction>=.75)].copy().sort_values("gross_bp",ascending=False)
S.to_csv(O/"SCREEN_SURVIVORS.csv",index=False)
prog(6,12,f"screen survivors {len(S)}")
# Diverse freeze: at most one per source_feature/target/feature, max 24 total.
F=S.drop_duplicates(["source_feature","target","feature"],keep="first").head(24).copy()
F.to_csv(O/"FROZEN_CANDIDATES.csv",index=False);fsha=hashlib.sha256((O/"FROZEN_CANDIDATES.csv").read_bytes()).hexdigest()
prog(7,12,f"diverse frozen candidates {len(F)} | sha {fsha[:12]}")
# Simple discovery null diagnostics, not gate: event sign flip 1000 for frozen.
rng=np.random.default_rng(470047);nulls=[]
for _,r in F.iterrows():
 p=pnls[r["key"]].to_numpy();obs=abs(p.mean());ge=sum(abs((p*rng.choice([-1.,1.],len(p))).mean())>=obs for _ in range(1000));nulls.append((ge+1)/1001)
F["signflip_p_1000"]=nulls;F.to_csv(O/"FROZEN_CANDIDATES_WITH_NULL.csv",index=False)
prog(8,12,"discovery sign-flip diagnostics complete")
receipt={"run_id":rid,"status":"COMPLETE_DISCOVERY_FREEZE","source_v46":src.name,"verified_design_sha256":sha,"period":"2010-2013 only","cell_count":len(R),"screen_survivor_count":len(S),"frozen_candidate_count":len(F),"freeze_sha256":fsha,"replication_2014_2017_accessed":False,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":[]}
R.to_csv(O/"ALL_CELLS.csv",index=False);(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(9,12,"all cells + receipt written")
prog(10,12,"assertions: no 2014+ target data loaded")
prog(11,12,"next: frozen replication 2014-2017 only")
prog(12,12,"STOP")
print("\n=== V47 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== FROZEN CANDIDATES ===");print(F.to_string(index=False) if len(F) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V47 compile failed"}
Write-Host "=== GEF V47 - RATES DISCOVERY 2010-2013 ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V47 failed"}
