param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v56_cftc_discovery.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib,re
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); DL=ROOT/"DataLake"; OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v56";OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v55b"/"GEF55B-20260920-182917"
EXPECTED="c73baf46640e2ad006c97bb9935733d728d064dc7ffa176455cae28d2f012971"
t=time.time();rid="GEF56-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF56] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
p=SRC/"CFTC_NORMALIZED_2009_2013.parquet"; sha=hashlib.sha256(p.read_bytes()).hexdigest()
if sha!=EXPECTED:raise RuntimeError("V55B normalized SHA mismatch")
C=pd.read_parquet(p); C["REPORT_DATE"]=pd.to_datetime(C["REPORT_DATE"]);C["AVAILABLE_AT"]=pd.to_datetime(C["AVAILABLE_AT"])
prog(1,10,f"verified V55B source sha={sha[:12]} rows={len(C)}")
# Exact primary contracts only; no consolidated/mini/ICE/swap ambiguity.
maps={"XAUUSD":"GOLD - COMMODITY EXCHANGE INC.","XAGUSD":"SILVER - COMMODITY EXCHANGE INC.","EURUSD":"EURO FX - CHICAGO MERCANTILE EXCHANGE","GBPUSD":"BRITISH POUND STERLING - CHICAGO MERCANTILE EXCHANGE","USDJPY":"JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE","AUDUSD":"AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE","USDCAD":"CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE","SPXUSD":"E-MINI S&P 500 STOCK INDEX - CHICAGO MERCANTILE EXCHANGE","NSXUSD":"NASDAQ-100 STOCK INDEX (MINI) - CHICAGO MERCANTILE EXCHANGE","WTIUSD":"CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE"}
# locate HistData parquet files without reading post-2013
def spot_daily(sym):
 cand=list(DL.rglob(f"*{sym}*2010*.parquet"))
 if not cand: cand=list(DL.rglob(f"*{sym}*.parquet"))
 frames=[]
 for q in cand:
  yrs=[int(x) for x in re.findall(r"20\d{2}",q.name)]
  if yrs and not any(2010<=y<=2013 for y in yrs):continue
  try:
   d=pd.read_parquet(q)
   dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
   pc=next((c for c in d.columns if str(c).lower() in ["close","bidclose","price"]),None)
   if dc is None:
    if isinstance(d.index,pd.DatetimeIndex):d=d.reset_index();dc=d.columns[0]
   if dc is None or pc is None:continue
   x=pd.DataFrame({"dt":pd.to_datetime(d[dc],errors="coerce"),"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
   x=x[(x.dt.dt.year>=2010)&(x.dt.dt.year<=2013)]
   if len(x):frames.append(x)
  except:pass
 if not frames:raise RuntimeError(f"No 2010-2013 spot parquet found for {sym}")
 x=pd.concat(frames).sort_values("dt").drop_duplicates("dt");return x.set_index("dt").px.resample("1D").last().dropna()
prog(2,10,"primary contract mapping frozen")
features=["noncomm_net_pct_oi","commercial_net_pct_oi"]; horizons=[1,5,10,20]; rows=[]; trials=0
for mi,(sym,name) in enumerate(maps.items(),1):
 cc=C[C["Market_and_Exchange_Names"]==name].sort_values("AVAILABLE_AT").copy()
 if len(cc)<100:continue
 for f in features:
  cc[f+"_chg1"]=cc[f].diff()
  cc[f+"_pct"]=cc[f].rolling(156,min_periods=52).rank(pct=True)
 s=spot_daily(sym); df=pd.DataFrame({"px":s})
 # merge_asof ensures only CFTC data already AVAILABLE_AT is visible
 df=df.reset_index().rename(columns={df.index.name or "index":"dt"}).sort_values("dt");df["dt"]=pd.to_datetime(df["dt"],errors="coerce");df=df.dropna(subset=["dt"]).reset_index(drop=True)
 use=cc[["AVAILABLE_AT"]+features+[f+"_chg1" for f in features]+[f+"_pct" for f in features]].sort_values("AVAILABLE_AT")
 df=pd.merge_asof(df,use,left_on="dt",right_on="AVAILABLE_AT",direction="backward")
 for h in horizons:df[f"r{h}"]=df.px.shift(-h)/df.px-1
 for base in features:
  specs=[(base+"_pct","lo",.10),(base+"_pct","hi",.90),(base+"_chg1","lo",.10),(base+"_chg1","hi",.90)]
  for col,tail,q in specs:
   if "chg1" in col:
    vals=df[col].dropna();thr=vals.quantile(q)
    mask=df[col]<=thr if tail=="lo" else df[col]>=thr
   else:mask=df[col]<=q if tail=="lo" else df[col]>=q
   for h in horizons:
    rr=df.loc[mask,f"r{h}"].dropna()
    if len(rr)<40:continue
    for mode,sg in [("continuation",1 if tail=="hi" else -1),("reversal",-1 if tail=="hi" else 1)]:
     x=rr*sg; trials+=1
     years=x.groupby(df.loc[x.index,"dt"].dt.year.to_numpy()).mean()
     rows.append({"key":f"{sym}|{base}|{col.split('_')[-1]}|{tail}|{q}|H{h}|{mode}","market":sym,"cftc_market":name,"feature":base,"transform":col,"tail":tail,"q":q,"h":h,"mode":mode,"n":len(x),"gross_bp":x.mean()*10000,"hit":(x>0).mean(),"positive_year_fraction":(years>0).mean() if len(years) else np.nan})
 prog(2+mi,12,f"{sym} complete | trials={trials}")
R=pd.DataFrame(rows);R.to_csv(O/"ALL_CELLS.csv",index=False)
screen=R[(R.n>=40)&(R.gross_bp>8)&(R.hit>=.54)&(R.positive_year_fraction>=.75)].copy()
# Diverse freeze: rank, max one per market/feature/transform/tail/h and max 24.
screen=screen.sort_values(["gross_bp","n"],ascending=[False,False])
frozen=[];seen=set()
for _,r in screen.iterrows():
 k=(r.market,r.feature,r["transform"],r.tail,r.h)
 if k in seen:continue
 seen.add(k);frozen.append(r)
 if len(frozen)>=24:break
F=pd.DataFrame(frozen);F.to_csv(O/"FROZEN_CANDIDATES.csv",index=False)
fsha=hashlib.sha256((O/"FROZEN_CANDIDATES.csv").read_bytes()).hexdigest()
receipt={"run_id":rid,"status":"COMPLETE_CFTC_DISCOVERY_FREEZE","source_v55b":"GEF55B-20260920-182917","verified_source_sha256":sha,"period":"2010-2013 only","cell_count":len(R),"screen_survivors":len(screen),"frozen_candidates":len(F),"freeze_sha256":fsha,"replication_2014_2017_accessed":False,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"retuning":False,"errors":[]}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(9,10,f"screen={len(screen)} frozen={len(F)} sha={fsha[:12]}")
prog(10,10,"STOP before replication")
print("\n=== V56 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== FROZEN CANDIDATES ===");print(F.to_string(index=False) if len(F) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V56 compile failed"}
Write-Host "=== GEF V56 - CFTC DISCOVERY 2010-2013 ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V56 failed"}
