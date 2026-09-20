param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v12_integrity.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,re
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); B=ROOT/"Research"/"Autonomous"; REPO=ROOT/"guardian-research"; DL=ROOT/"DataLake"
OUTB=B/"guardian_edge_factory_v12_integrity";OUTB.mkdir(parents=True,exist_ok=True);started=time.time()
def prog(o,s,i,n,m=""):
 e=time.time()-started;eta=e/i*(n-i) if i else 0
 print(f"[GEF12] {s:<20} {i}/{n} {100*i/n:6.2f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {m}",flush=True)
 (o/"STATUS.json").write_text(json.dumps({"stage":s,"done":i,"total":n,"pct":100*i/n,"elapsed_s":e,"eta_s":eta,"message":m},indent=2))
rid="GEF12-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");OUT=OUTB/rid;OUT.mkdir()
# 1) Static audit of research source for dangerous aggregation/time semantics.
patterns=[r'resample\(',r'label\s*=\s*["\']left',r'closed\s*=\s*["\']left',r'rolling\(',r'shift\(',r'cache5',r'AVAILABLE_AT',r'available_at']
files=[]
for rr in [REPO,B]:
 if rr.exists(): files += [p for p in rr.rglob("*") if p.is_file() and p.suffix.lower() in [".py",".ps1"] and "guardian_edge_factory_v12_integrity" not in str(p)]
hits=[]
for i,p in enumerate(files,1):
 try:
  txt=p.read_text(errors="ignore")
  for ln,line in enumerate(txt.splitlines(),1):
   kinds=[pat for pat in patterns if re.search(pat,line,re.I)]
   if kinds: hits.append({"file":str(p),"line":ln,"patterns":"|".join(kinds),"text":line[:1200]})
 except Exception as e: hits.append({"file":str(p),"line":-1,"patterns":"READ_ERROR","text":str(e)})
 if i%100==0:prog(OUT,"STATIC AUDIT",i,len(files),p.name)
H=pd.DataFrame(hits);H.to_csv(OUT/"time_semantics_code_hits.csv",index=False)
# 2) Audit all pre-2023 HistData raw parquet cadence. No 2023+ file is opened.
rawroot=DL/"raw"/"histdata"; pars=[p for p in rawroot.rglob("*.parquet") if re.search(r'_(19|20)\d{2}\.parquet$',p.name)]
pars=[p for p in pars if int(re.search(r'_(\d{4})\.parquet$',p.name).group(1))<=2022]
rows=[]
for i,p in enumerate(pars,1):
 try:
  d=pd.read_parquet(p);dtc=next((c for c in d.columns if str(c).lower() in ["datetime","time","timestamp","date"]),None)
  idx=pd.to_datetime(d.index if isinstance(d.index,pd.DatetimeIndex) else d[dtc]);dif=pd.Series(idx).diff().dt.total_seconds()/60
  rows.append({"file":str(p),"rows":len(d),"start":str(idx.min()),"end":str(idx.max()),"mode_gap_min":float(dif.mode().iloc[0]),"median_gap_min":float(dif.median()),"duplicates":int(pd.Index(idx).duplicated().sum()),"nonmonotonic":bool(not pd.Index(idx).is_monotonic_increasing)})
 except Exception as e: rows.append({"file":str(p),"error":str(e)})
 if i%25==0 or i==len(pars):prog(OUT,"RAW CADENCE",i,len(pars),p.name)
R=pd.DataFrame(rows);R.to_csv(OUT/"raw_pre2023_cadence.csv",index=False)
# 3) Write mandatory temporal contract for all future research.
contract="""# GUARDIAN TEMPORAL CAUSALITY CONTRACT V1
1. EVENT_TIME is the source/bucket timestamp. AVAILABLE_AT is the earliest instant all information in that row is knowable.
2. Signals may consume a row only when decision_time >= AVAILABLE_AT.
3. For M1 -> M5 aggregation of [t,t+5), a left label t MUST NOT imply availability at t. AVAILABLE_AT is the right boundary t+5 (or later if source publication latency requires).
4. Features inherit max(AVAILABLE_AT) of all inputs used.
5. Targets begin at or after decision_time; no overlapping source interval may enter both feature and future target.
6. rolling(N) is N BARS, not N minutes. Names/docs must state bars and elapsed-time equivalent.
7. shift(N) is N ROWS unless exact timestamp logic is explicitly implemented.
8. External macro/event data require publication/release availability timestamps; revised series are forbidden for historical decisions unless vintage-correct.
9. Every new cache must pass synthetic causality tests plus raw->cache timestamp spot checks before research use.
10. Locked OOS 2023-2025 and protected 2026 remain unread until explicit human authorization.
"""
(OUT/"TEMPORAL_CAUSALITY_CONTRACT_V1.md").write_text(contract)
summary={"run_id":rid,"status":"COMPLETE","research_max":"2022-12-31","locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"source_files_scanned":len(files),"semantic_hits":len(H),"raw_parquets_opened":len(R),"raw_errors":int(R.error.notna().sum()) if "error" in R else 0,"purpose":"infrastructure integrity audit only; no alpha search, no threshold selection","next_gate":"Review suspicious aggregation/timestamp hits; patch shared causal cache/feature primitives and tests before starting a new discovery lineage.","errors":[]}
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(summary,indent=2));prog(OUT,"COMPLETE",1,1,"INTEGRITY_AUDIT_COMPLETE")
print("\n=== V12 INTEGRITY RECEIPT ===");print(json.dumps(summary,indent=2))
if len(H):
 print("\n=== MOST RELEVANT TIME-SEMANTICS HITS ===")
 q=H[H.patterns.str.contains("resample|label|cache5",case=False,na=False)].head(80);print(q.to_string(index=False))
print("\nRUN:",OUT)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V12 compile failed"}
Write-Host "=== GEF V12 — TEMPORAL INTEGRITY AUDIT / NO ALPHA SEARCH / OOS LOCKED ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V12 run failed"}
