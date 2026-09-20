param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v10d.py"
$code=@'
from pathlib import Path
import pandas as pd, numpy as np, json, time, re, hashlib
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); B=ROOT/"Research"/"Autonomous"; REPO=ROOT/"guardian-research"
RAW=ROOT/"DataLake"/"raw"/"histdata"/"GBPUSD"/"M1"; CACHE=B/"guardian_edge_factory_v3"/"cache5"/"GBPUSD_2010_2022.parquet"
OUTB=B/"guardian_edge_factory_v10d";OUTB.mkdir(parents=True,exist_ok=True);run_started=time.time()
def prog(o,s,i,n,m=""):
 e=time.time()-run_started;eta=e/i*(n-i) if i else 0
 print(f"[GEF10D] {s:<18} {i}/{n} {100*i/n:6.2f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {m}",flush=True)
 (o/"STATUS.json").write_text(json.dumps({"stage":s,"done":i,"total":n,"pct":100*i/n,"elapsed_s":e,"eta_s":eta,"message":m},indent=2))
rid="GEF10D-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");OUT=OUTB/rid;OUT.mkdir()
hits=[]; roots=[REPO,B/"guardian_edge_factory_v3"]; files=[]
for rr in roots:
 if rr.exists(): files += [p for p in rr.rglob("*") if p.is_file() and p.suffix.lower() in [".py",".ps1",".md",".json"] and "GEF10D-" not in str(p)]
for i,p in enumerate(files,1):
 try:
  txt=p.read_text(errors="ignore")
  for ln,line in enumerate(txt.splitlines(),1):
   if re.search(r"cache5|resample\(|5min|5T|floor\(|ceil\(",line,re.I): hits.append({"file":str(p),"line":ln,"text":line[:1000]})
 except: pass
 if i%100==0: prog(OUT,"CODE TRACE",i,len(files),p.name)
pd.DataFrame(hits).to_csv(OUT/"cache5_code_trace.csv",index=False)
events=pd.to_datetime(["2017-06-08 16:55","2016-10-06 18:40","2016-06-30 10:55","2022-11-02 13:30","2020-03-18 15:00","2022-10-13 08:20"])
cache=pd.read_parquet(CACHE).sort_index();cache.index=pd.to_datetime(cache.index); raws={}
for y in sorted(set(events.year)):
 d=pd.read_parquet(RAW/f"GBPUSD_M1_{y}.parquet");d.index=pd.to_datetime(d["datetime"]);raws[y]=d
prog(OUT,"LOAD RAW",1,1,f"{len(raws)} years")
cands=[]
for t in events:
 d=raws[t.year];cc=float(cache.loc[t,"close"]);rec={"time":t,"cache_close":cc}
 for k in range(-5,6):
  tt=t+pd.Timedelta(minutes=k);rec[f"raw_t{k:+d}"]=float(d.loc[tt,"close"]) if tt in d.index else np.nan
 w=d.loc[(d.index>=t-pd.Timedelta(days=1))&(d.index<=t+pd.Timedelta(days=1)),["open","high","low","close"]]
 for label in ["left","right"]:
  for closed in ["left","right"]:
   rs=w.resample("5min",label=label,closed=closed).agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()
   rec[f"{label}_{closed}"]=float(rs.loc[t,"close"]) if t in rs.index else np.nan
 cands.append(rec)
C=pd.DataFrame(cands);candidate_cols=[c for c in C.columns if c not in ["time","cache_close"]];scores=[]
for col in candidate_cols:
 ok=np.isclose(C[col],C.cache_close,rtol=0,atol=1e-12,equal_nan=False)
 scores.append({"candidate":col,"matches":int(ok.sum()),"n":len(C),"fraction":float(ok.mean()),"causal_at_label":(col in ["raw_t+0","right_right","right_left"] or col.startswith("raw_t-"))})
S=pd.DataFrame(scores).sort_values(["matches","candidate"],ascending=[False,True]);S.to_csv(OUT/"candidate_semantics_scores.csv",index=False);C.to_csv(OUT/"event_semantics_matrix.csv",index=False);best=S.iloc[0].to_dict()
offset_stats=[]
for k in range(-5,6):
 n=match=0
 for event_t in events:
  d=raws[event_t.year];times=cache.loc[(cache.index>=event_t-pd.Timedelta(minutes=60))&(cache.index<=event_t+pd.Timedelta(minutes=60))].index
  for t in times:
   tt=t+pd.Timedelta(minutes=k)
   if tt in d.index: n+=1;match+=int(abs(float(cache.loc[t,"close"])-float(d.loc[tt,"close"]))<1e-12)
 offset_stats.append({"offset_min":k,"matches":match,"n":n,"fraction":match/n if n else np.nan,"available_by_cache_label":k<=0})
O=pd.DataFrame(offset_stats).sort_values("fraction",ascending=False);O.to_csv(OUT/"offset_match_scores.csv",index=False);bo=O.iloc[0]
if bo.fraction>.95 and bo.offset_min>0:
 verdict="CACHE_TIMESTAMP_LOOKAHEAD_CONFIRMED";gate=f"Cache close at label t overwhelmingly maps to raw close t+{int(bo.offset_min)}m. Do not open OOS. Rebuild causal cache and restart this lineage's pre-OOS measurements; frozen V10 rule is invalid as previously timestamped."
elif bo.fraction>.95 and bo.offset_min<=0:
 verdict="CACHE_CAUSAL_CLOSE_MAPPING_CONFIRMED";gate="Inspect code-trace provenance and feature timestamp semantics; if all inputs are available by label time, forensic can close without changing frozen rule."
else:
 verdict="CACHE_MAPPING_UNRESOLVED";gate="Inspect code trace and aggregation semantics manually; do not open OOS."
receipt={"run_id":rid,"status":"COMPLETE","research_max":"2022-12-31","locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"code_hits":len(hits),"best_event_semantics":best,"best_window_offset":bo.to_dict(),"verdict":verdict,"next_gate":gate,"errors":[]}
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2,default=str));prog(OUT,"COMPLETE",1,1,verdict)
print("\n=== V10D RECEIPT ===");print(json.dumps(receipt,indent=2,default=str));print("\n=== OFFSET MATCH SCORES ===");print(O.to_string(index=False));print("\n=== EVENT SEMANTICS ===");print(C.to_string(index=False));print("\n=== CODE TRACE (first 40) ===");print(pd.DataFrame(hits).head(40).to_string(index=False));print("\nRUN:",OUT)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V10d compile failed"}
Write-Host "=== GEF V10d — M1->M5 TIMESTAMP FORENSIC / OOS LOCKED ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V10d run failed"}
