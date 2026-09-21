param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v71_usdchf_weekend_gap_forensic.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake"
OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v71";rid="GEF71-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF71] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
def load():
 z=[]
 for y in range(2010,2026):
  p=DL/"raw"/"histdata"/"USDCHF"/"M1"/f"USDCHF_M1_{y}.parquet"
  if not p.exists():raise RuntimeError(f"Missing {p}")
  d=pd.read_parquet(p);dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None);pc=next((c for c in d.columns if str(c).lower()=="close"),None)
  if dc is None and isinstance(d.index,pd.DatetimeIndex):d=d.reset_index();dc=d.columns[0]
  q=pd.DataFrame({"dt":pd.to_datetime(d[dc],errors="coerce"),"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
  if (q.dt.dt.year>=2026).any():raise RuntimeError("2026 contamination")
  z.append(q)
 return pd.concat(z).sort_values("dt").drop_duplicates("dt")
prog(1,7,"loading USDCHF 2010-2025; 2026 forbidden")
d=load();prog(2,7,f"loaded {len(d):,} M1 rows")
# Calendar-week reconstruction from ACTUAL observed quotes, not midnight resampling.
d["iso_year"]=d.dt.dt.isocalendar().year.astype(int);d["iso_week"]=d.dt.dt.isocalendar().week.astype(int);d["dow"]=d.dt.dt.dayofweek
rows=[]
for (iy,iw),w in d.groupby(["iso_year","iso_week"],sort=True):
 fri=w[w.dow==4]
 if fri.empty:continue
 last=fri.iloc[-1]
 future=d[d.dt>last["dt"]]
 # first actual quote after Friday, require <=96h so holidays are visible but bounded
 future=future[future.dt<=last["dt"]+pd.Timedelta(hours=96)]
 if future.empty:continue
 first=future.iloc[0]
 rows.append({"iso_year":iy,"iso_week":iw,"entry_dt":last["dt"],"entry_px":last["px"],"exit_dt":first["dt"],"exit_px":first["px"],"gap_hours":(first["dt"]-last["dt"]).total_seconds()/3600,"ret":first["px"]/last["px"]-1})
g=pd.DataFrame(rows);g["year"]=g.entry_dt.dt.year;g["era"]=np.where(g.year<=2022,"PRE_2010_2022","OOS_2023_2025")
if (g.year>=2026).any():raise RuntimeError("2026 contamination")
prog(3,7,f"actual close->reopen weekends reconstructed n={len(g)}")
# Audit actual boundary timestamps and DST-like seasonal shifts.
g["entry_hm"]=g.entry_dt.dt.strftime("%H:%M");g["exit_hm"]=g.exit_dt.dt.strftime("%H:%M");g["exit_dow"]=g.exit_dt.dt.dayofweek;g["month"]=g.entry_dt.dt.month
pd.crosstab(g.era,g.entry_hm).to_csv(O/"ACTUAL_ENTRY_TIMES.csv");pd.crosstab(g.era,[g.exit_dow,g.exit_hm]).to_csv(O/"ACTUAL_REOPEN_TIMES.csv")
pd.crosstab([g.era,g.month],[g.entry_hm,g.exit_hm]).to_csv(O/"SEASONAL_BOUNDARY_TIMES.csv")
# Frozen-period reporting; no parameter selection.
def stats(h):
 r=h.ret
 a=np.sort(r.values);n=len(r)
 trim=lambda p:np.mean(a[:max(1,int(np.floor((1-p)*n)))])*1e4
 byy=h.groupby("year").ret.mean()*1e4
 return {"n":n,"gross_bp":r.mean()*1e4,"hit":(r>0).mean(),"trim1_bp":trim(.01),"trim2_bp":trim(.02),"remove_best5_bp":r.drop(r.nlargest(min(5,n)).index).mean()*1e4,"positive_year_fraction":(byy>0).mean(),"median_gap_hours":h.gap_hours.median(),"min_gap_hours":h.gap_hours.min(),"max_gap_hours":h.gap_hours.max()}
S=pd.DataFrame([{"era":era,**stats(h)} for era,h in g.groupby("era")]);S.to_csv(O/"WEEKEND_GAP_STATS.csv",index=False);prog(4,7,"weekend-gap stats complete")
# Compare V70 midnight-resample return to actual quote close->reopen on matching Friday dates.
q=d.set_index("dt").px.resample("1D").last().dropna().to_frame("px");q["v70_ret"]=q.px.shift(-1)/q.px-1;q=q[q.index.dayofweek==4].reset_index().rename(columns={"dt":"date"});q["key"]=q.date.dt.date
g["key"]=g.entry_dt.dt.date
c=g.merge(q[["key","v70_ret"]],on="key",how="inner");c["delta_bp"]=(c.ret-c.v70_ret)*1e4
cmp=c.groupby("era").agg(n=("ret","size"),actual_gap_bp=("ret",lambda s:s.mean()*1e4),v70_bp=("v70_ret",lambda s:s.mean()*1e4),mean_delta_bp=("delta_bp","mean"),median_abs_delta_bp=("delta_bp",lambda s:s.abs().median()),corr=("ret",lambda s:s.corr(c.loc[s.index,"v70_ret"]))).reset_index()
cmp.to_csv(O/"V70_VS_ACTUAL_GAP.csv",index=False);prog(5,7,"V70 vs actual-gap comparison complete")
# Cost sensitivity only; no assumed broker spread/swap.
cost=[]
for era,h in g.groupby("era"):
 gross=h.ret.mean()*1e4
 for bp in [0,1,2,3,4,5]:cost.append({"era":era,"roundtrip_cost_bp":bp,"net_bp":gross-bp})
pd.DataFrame(cost).to_csv(O/"COST_SENSITIVITY.csv",index=False)
# Full event ledger for manual forensic.
g.drop(columns=["key"]).to_csv(O/"WEEKEND_EVENT_LEDGER.csv",index=False);prog(6,7,"event ledger + cost sensitivity written")
receipt={"run_id":rid,"status":"COMPLETE_ACTUAL_QUOTE_WEEKEND_GAP_FORENSIC","market":"USDCHF","definition":"last actual Friday M1 quote -> first actual subsequent M1 quote, max 96h","retuning":False,"protected_2026_accessed":False,"next":"INTERPRET_ACTUAL_EXECUTABILITY"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(7,7,"STOP; 2026 untouched")
print("\n=== V71 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== ACTUAL WEEKEND GAP STATS ===");print(S.to_string(index=False));print("\n=== V70 VS ACTUAL GAP ===");print(cmp.to_string(index=False));print("\n=== TOP ENTRY TIMES ===");print(g.groupby(["era","entry_hm"]).size().sort_values(ascending=False).head(20).to_string());print("\n=== TOP REOPEN TIMES ===");print(g.groupby(["era","exit_dow","exit_hm"]).size().sort_values(ascending=False).head(20).to_string());print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V71 compile failed"}
Write-Host "=== GEF V71 - USDCHF ACTUAL WEEKEND GAP FORENSIC ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V71 failed"}
