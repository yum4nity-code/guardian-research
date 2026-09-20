param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v10c.py"
$code=@'
from pathlib import Path
import pandas as pd, numpy as np, json, time, hashlib
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); DL=ROOT/"DataLake"; B=ROOT/"Research"/"Autonomous"; OUTB=B/"guardian_edge_factory_v10c"; OUTB.mkdir(parents=True,exist_ok=True)
RAW=DL/"raw"/"histdata"/"GBPUSD"/"M1"; CACHE=B/"guardian_edge_factory_v3"/"cache5"/"GBPUSD_2010_2022.parquet"
t0=time.time()
def prog(o,s,i,n,m=""):
 e=time.time()-t0;eta=e/i*(n-i) if i else 0
 print(f"[GEF10C] {s:<17} {i}/{n} {100*i/n:6.2f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {m}",flush=True)
 (o/"STATUS.json").write_text(json.dumps({"stage":s,"done":i,"total":n,"pct":100*i/n,"elapsed_s":e,"eta_s":eta,"message":m},indent=2))
rid="GEF10C-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");OUT=OUTB/rid;OUT.mkdir()
# absolutely pre-2023 only
files=[RAW/f"GBPUSD_M1_{y}.parquet" for y in range(2010,2023)]
rows=[]; samples={}
for i,p in enumerate(files,1):
 if not p.exists(): rows.append({"year":2009+i,"exists":False});continue
 d=pd.read_parquet(p); dtcol=next((c for c in d.columns if str(c).lower() in ["time","datetime","timestamp","date"]),None)
 if isinstance(d.index,pd.DatetimeIndex): idx=pd.to_datetime(d.index)
 elif dtcol: idx=pd.to_datetime(d[dtcol])
 else: raise RuntimeError(f"No datetime index/column in {p}")
 dif=pd.Series(idx).diff().dt.total_seconds().div(60); vc=dif.value_counts()
 rows.append({"year":2009+i,"exists":True,"rows":len(d),"start":str(idx.min()),"end":str(idx.max()),"mode_gap_min":float(dif.mode().iloc[0]),"median_gap_min":float(dif.median()),"pct_1m":float((dif==1).mean()),"pct_5m":float((dif==5).mean()),"pct_gt5m":float((dif>5).mean()),"duplicates":int(pd.Index(idx).duplicated().sum()),"columns":"|".join(map(str,d.columns)),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
 samples[2009+i]=(d,idx)
 prog(OUT,"RAW CADENCE",i,len(files),p.name)
R=pd.DataFrame(rows);R.to_csv(OUT/"raw_cadence_by_year.csv",index=False)
cache=pd.read_parquet(CACHE).sort_index();cache.index=pd.to_datetime(cache.index)
# Compare raw and cache at exact timestamps for known extreme events + random deterministic cache timestamps
events=pd.to_datetime(["2017-06-08 16:55","2016-10-06 18:40","2016-06-30 10:55","2022-11-02 13:30","2020-03-18 15:00","2022-10-13 08:20"])
rng=np.random.default_rng(10022026); eligible=cache.index[(cache.index.year>=2010)&(cache.index.year<=2022)]; extra=pd.DatetimeIndex(rng.choice(eligible.to_numpy(),size=500,replace=False)); checks=pd.DatetimeIndex(events).append(extra)
def raw_close_at(t):
 d,idx=samples[t.year]; cols={str(c).lower():c for c in d.columns}; cc=cols.get("close")
 if cc is None: raise RuntimeError(f"No close in raw {t.year}: {list(d.columns)}")
 pos=np.where(pd.DatetimeIndex(idx)==t)[0]
 return (float(d.iloc[pos[0]][cc]) if len(pos) else np.nan),len(pos)
cmp=[]
for i,t in enumerate(checks,1):
 rv,n=raw_close_at(t); cv=float(cache.loc[t,"close"]) if t in cache.index else np.nan
 cmp.append({"time":t,"is_extreme":t in events,"raw_exists":n>0,"cache_exists":t in cache.index,"raw_close":rv,"cache_close":cv,"abs_diff":abs(rv-cv) if np.isfinite(rv) and np.isfinite(cv) else np.nan})
 if i%50==0:prog(OUT,"RAW↔CACHE",i,len(checks),str(t))
C=pd.DataFrame(cmp);C.to_csv(OUT/"raw_cache_comparison.csv",index=False)
# Around extremes: dump raw ±70m and cache ±70m, and compare cache timestamps to raw.
er=[]
for i,t in enumerate(events,1):
 d,idx=samples[t.year]; dd=d.copy();dd.index=pd.DatetimeIndex(idx); w=dd.loc[(dd.index>=t-pd.Timedelta(minutes=70))&(dd.index<=t+pd.Timedelta(minutes=70))].copy()
 cw=cache.loc[(cache.index>=t-pd.Timedelta(minutes=70))&(cache.index<=t+pd.Timedelta(minutes=70)),["close"]].copy()
 w.to_csv(OUT/f"extreme_{i:02d}_{t.strftime('%Y%m%d_%H%M')}_RAW.csv");cw.to_csv(OUT/f"extreme_{i:02d}_{t.strftime('%Y%m%d_%H%M')}_CACHE.csv")
 rawdif=w.index.to_series().diff().dt.total_seconds().div(60)
 er.append({"time":t,"raw_rows_140m":len(w),"raw_mode_gap":float(rawdif.mode().iloc[0]) if rawdif.notna().any() else np.nan,"cache_rows_140m":len(cw),"cache_all_timestamps_in_raw":bool(cw.index.isin(w.index).all())})
 prog(OUT,"EXTREME TRACE",i,len(events),str(t))
E=pd.DataFrame(er);E.to_csv(OUT/"extreme_trace_summary.csv",index=False)
all_raw_m1=bool((R.loc[R.exists,"mode_gap_min"]==1).all())
all_raw_m5=bool((R.loc[R.exists,"mode_gap_min"]==5).all())
match=C.loc[C.raw_exists & C.cache_exists,"abs_diff"]; exact=float((match<1e-12).mean()) if len(match) else 0
if all_raw_m1 and exact>.999:
 verdict="RAW_M1_CACHE_M5_CONFIRMED_EXACT_SAMPLING"
 nextg="Inspect the cache5 construction code to prove causal M1→M5 sampling/resampling convention. If causal and frozen 60m rule unchanged, forensic issue can be closed before OOS."
elif all_raw_m5:
 verdict="RAW_FILES_MISLABELED_M5"
 nextg="Trace HistData import provenance. Do not open OOS until source labeling and execution assumptions are corrected."
else:
 verdict="MIXED_OR_UNRESOLVED"
 nextg="Resolve year-level cadence and raw/cache mismatches before OOS."
receipt={"run_id":rid,"status":"COMPLETE","research_max":"2022-12-31","locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"raw_years":list(range(2010,2023)),"raw_all_m1":all_raw_m1,"raw_all_m5":all_raw_m5,"raw_cache_exact_close_fraction":exact,"raw_cache_comparisons":len(C),"extreme_events_checked":len(events),"verdict":verdict,"next_gate":nextg,"errors":[]}
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(OUT,"COMPLETE",1,1,verdict)
print("\n=== V10C RECEIPT ===");print(json.dumps(receipt,indent=2))
print("\n=== RAW CADENCE BY YEAR ===");print(R.to_string(index=False))
print("\n=== EXTREME RAW↔CACHE ===");print(C[C.is_extreme].to_string(index=False))
print("\n=== EXTREME TRACE ===");print(E.to_string(index=False))
print("\nRUN:",OUT)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V10c compile failed"}
Write-Host "=== GEF V10c — RAW GBPUSD PROVENANCE / OOS STILL LOCKED ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V10c run failed"}
