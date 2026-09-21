param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v79_causal_price_state_matrix.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,hashlib,time
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake"
rid="GEF79-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
O=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v79"/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
markets=["XAUUSD","XAGUSD","UDXUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","SPXUSD","NSXUSD","WTIUSD","BCOUSD"]
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF79] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
prog(1,18,"canonical timebase: HistData EST fixed UTC-5 -> UTC +5h; discovery 2010-2013 only")
def load(sym):
 z=[]
 for y in range(2010,2014):
  p=DL/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{y}.parquet"
  if not p.exists():continue
  d=pd.read_parquet(p)
  dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
  pc=next((c for c in d.columns if str(c).lower()=="close"),None)
  if dc is None and isinstance(d.index,pd.DatetimeIndex):d=d.reset_index();dc=d.columns[0]
  if dc is None or pc is None:continue
  dt=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(hours=5) # source is EST fixed, no DST
  q=pd.DataFrame({"utc":dt,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
  q=q[q.utc.dt.year.between(2010,2013)];z.append(q)
 if not z:return None
 return pd.concat(z).sort_values("utc").drop_duplicates("utc").set_index("utc").px
# Hourly decision grid: last causally observed quote <= hour. No future fill.
grid=pd.date_range("2010-01-01","2013-12-31 23:00",freq="1h")
M=pd.DataFrame(index=grid)
coverage=[]
for i,sym in enumerate(markets,2):
 s=load(sym)
 if s is None:
  coverage.append({"market":sym,"status":"MISSING"});prog(i,18,f"{sym} missing");continue
 # last quote in each UTC hour; labels at hour end, then shift decision timestamp to next hour boundary.
 h=s.resample("1h",label="right",closed="left").last().reindex(grid)
 M[f"{sym}_px"]=h
 coverage.append({"market":sym,"status":"OK","non_null":int(h.notna().sum()),"first":str(h.first_valid_index()),"last":str(h.last_valid_index())})
 prog(i,18,f"{sym} normalized; hourly non-null={int(h.notna().sum()):,}")
# causal price-state features; all use current/past observations only.
for sym in markets:
 c=f"{sym}_px"
 if c not in M:continue
 p=M[c]
 for h in [1,5,15,30,60,120,240]:
  M[f"{sym}_ret_{h}h"]=p.pct_change(h,fill_method=None)
 r=p.pct_change(fill_method=None)
 for w in [6,24,120]:
  M[f"{sym}_rv_{w}h"]=r.rolling(w,min_periods=max(3,w//2)).std()
  mu=r.rolling(w,min_periods=max(3,w//2)).mean();sd=r.rolling(w,min_periods=max(3,w//2)).std()
  M[f"{sym}_zret_{w}h"]=(r-mu)/sd.replace(0,np.nan)
 M[f"{sym}_trend_24h"]=p/p.shift(24)-1
 M[f"{sym}_trend_120h"]=p/p.shift(120)-1
prog(15,18,f"price features={M.shape[1]:,}")
# cross-market state: lagged/current causal returns, rolling correlations and dispersion.
retcols=[f"{s}_ret_1h" for s in markets if f"{s}_ret_1h" in M]
M["cross_dispersion_1h"]=M[retcols].std(axis=1)
M["cross_positive_fraction_1h"]=(M[retcols]>0).sum(axis=1)/M[retcols].notna().sum(axis=1).replace(0,np.nan)
anchors=["XAUUSD","UDXUSD","SPXUSD","NSXUSD","WTIUSD"]
for a in anchors:
 for b in anchors:
  if a>=b:continue
  ca,cb=f"{a}_ret_1h",f"{b}_ret_1h"
  if ca in M and cb in M:M[f"corr24_{a}_{b}"]=M[ca].rolling(24,min_periods=12).corr(M[cb])
prog(16,18,f"cross-market features complete; columns={M.shape[1]:,}")
# Future targets are stored separately and NEVER used as features.
T=pd.DataFrame(index=M.index)
for sym in markets:
 c=f"{sym}_px"
 if c not in M:continue
 for h in [1,5,15,30,60,120,240]:
  T[f"{sym}_fwd_{h}h"]=M[c].shift(-h)/M[c]-1
# Save parquet, provenance and a strict no-OOS receipt.
M.index.name="decision_time_utc";T.index.name="decision_time_utc"
M.to_parquet(O/"PRICE_STATE_MATRIX_2010_2013.parquet");T.to_parquet(O/"FUTURE_TARGETS_2010_2013.parquet")
pd.DataFrame(coverage).to_csv(O/"MARKET_COVERAGE.csv",index=False)
provenance={"source":"HistData M1","source_timezone":"Eastern Standard Time fixed UTC-5, WITHOUT DST","normalization":"utc = raw_datetime + 5 hours","decision_grid":"hourly UTC; hourly price is last quote observed within completed preceding hour","feature_rule":"current/past only","targets_separate":True,"years":[2010,2011,2012,2013],"note":"This corrects the prior mistaken UTC treatment in FOMC V75/V76/V77 lineage; those event-timing results must not be reused."}
(O/"TIMEBASE_PROVENANCE.json").write_text(json.dumps(provenance,indent=2))
prog(17,18,f"matrix rows={len(M):,}; features={M.shape[1]:,}; targets={T.shape[1]:,}")
receipt={"run_id":rid,"status":"COMPLETE_CAUSAL_PRICE_STATE_MATRIX_2010_2013","rows":len(M),"feature_columns":M.shape[1],"target_columns":T.shape[1],"markets_ok":sum(x["status"]=="OK" for x in coverage),"histdata_timezone_corrected":True,"external_sources_joined":False,"edge_trials":0,"2014_plus_accessed":False,"2023_plus_accessed":False,"protected_2026_accessed":False,"next":"V80_NORMALIZE_AND_JOIN_ALL_EXTERNAL_CAUSAL_SOURCES"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(18,18,"DONE; external-source causal join is next, no edge search yet")
print("\n=== V79 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== MARKET COVERAGE ===");print(pd.DataFrame(coverage).to_string(index=False));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V79 compile failed"}
Write-Host "=== GEF V79 - CAUSAL PRICE STATE MATRIX 2010-2013 ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V79 failed"}
