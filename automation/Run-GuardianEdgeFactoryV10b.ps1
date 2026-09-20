param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v10b.py"
$code=@'
from pathlib import Path
import pandas as pd, numpy as np, json, time, hashlib
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); B=ROOT/"Research"/"Autonomous"; V10B=B/"guardian_edge_factory_v10"; V3B=B/"guardian_edge_factory_v3"; CACHE=V3B/"cache5"; OUTB=B/"guardian_edge_factory_v10b"; OUTB.mkdir(parents=True,exist_ok=True)
t0=time.time()
def prog(o,s,i,n,m=""):
 e=time.time()-t0; eta=e/i*(n-i) if i else 0
 print(f"[GEF10B] {s:<16} {i}/{n} {100*i/n:6.2f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {m}",flush=True)
 (o/"STATUS.json").write_text(json.dumps({"stage":s,"done":i,"total":n,"pct":100*i/n,"elapsed_s":e,"eta_s":eta,"message":m},indent=2))
# locate completed V10 and frozen rule
vv=[]
for p in V10B.glob("GEF10-*"):
 r=p/"RUN_RECEIPT.json"
 if r.exists():
  j=json.loads(r.read_text())
  if j.get("status")=="COMPLETE" and not j.get("locked_oos_2023_2025_accessed"): vv.append((p.stat().st_mtime,p))
V10=sorted(vv)[-1][1]; rule=json.loads((V10/"FROZEN_RULE.json").read_text())
rid="GEF10B-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"); OUT=OUTB/rid;OUT.mkdir()
z=pd.read_parquet(CACHE/"GBPUSD_2010_2022.parquet").sort_index();z.index=pd.to_datetime(z.index)
tops=pd.read_csv(V10/"top100_data_quality.csv",parse_dates=["time"])
# global cadence / integrity
idx=z.index; dif=idx.to_series().diff().dt.total_seconds().div(60)
cad=dif.value_counts().sort_index()
integrity={"rows":len(z),"start":str(idx.min()),"end":str(idx.max()),"duplicate_timestamps":int(idx.duplicated().sum()),"nonmonotonic":bool(not idx.is_monotonic_increasing),"nan_close":int(z.close.isna().sum()),"nonpositive_close":int((z.close<=0).sum()),"median_gap_min":float(dif.median()),"mode_gap_min":float(dif.mode().iloc[0]),"pct_gap_1m":float((dif==1).mean()),"pct_gap_5m":float((dif==5).mean()),"pct_gap_gt5m":float((dif>5).mean())}
(OUT/"global_integrity.json").write_text(json.dumps(integrity,indent=2));cad.to_csv(OUT/"gap_distribution.csv")
prog(OUT,"GLOBAL CADENCE",1,1,f"mode={integrity['mode_gap_min']}m median={integrity['median_gap_min']}m")
# inspect raw lake candidates, without touching post-2022
raw_candidates=[]
for pat in ["*GBPUSD*","*GBP*"]:
 for p in (ROOT/"DataLake").rglob(pat):
  if p.is_file():
   s=str(p).lower()
   if any(x in s for x in ["2023","2024","2025","2026"]): continue
   raw_candidates.append(p)
raw_candidates=list(dict.fromkeys(raw_candidates))
manifest=[]
for i,p in enumerate(raw_candidates,1):
 try:
  manifest.append({"path":str(p),"size":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest() if p.stat().st_size<100_000_000 else "SKIPPED_GT100MB"})
 except Exception as e: manifest.append({"path":str(p),"error":str(e)})
 if i%25==0: prog(OUT,"SOURCE SCAN",i,len(raw_candidates),p.name)
pd.DataFrame(manifest).to_csv(OUT/"source_manifest.csv",index=False)
# forensic each top winner on cached source: exact timestamps and surrounding bars
rows=[]
for i,r in tops.iterrows():
 t=r.time; w=z.loc[(z.index>=t-pd.Timedelta(minutes=90))&(z.index<=t+pd.Timedelta(minutes=120)),["close"]].copy()
 w["gap_min"]=w.index.to_series().diff().dt.total_seconds().div(60);w["ret_bp"]=np.log(w.close/w.close.shift(1))*10000
 pre=z.close.loc[:t].tail(2); post=z.close.loc[t:].head(14)
 rows.append({"rank":i+1,"time":t,"reported_gross_bp":r.gross_bp,"bars_210m":len(w),"mode_gap":float(w.gap_min.mode().iloc[0]) if w.gap_min.notna().any() else np.nan,"max_gap":w.gap_min.max(),"max_abs_bar_bp":w.ret_bp.abs().max(),"exact_entry_exists":bool(t in z.index),"exact_exit_exists":bool(t+pd.Timedelta(minutes=60) in z.index),"entry_close":float(z.close.loc[t]) if t in z.index else np.nan,"exit_close":float(z.close.loc[t+pd.Timedelta(minutes=60)]) if t+pd.Timedelta(minutes=60) in z.index else np.nan})
 if i<25: w.to_csv(OUT/f"event_{i+1:03d}_{t.strftime('%Y%m%d_%H%M')}.csv")
 if (i+1)%10==0: prog(OUT,"EVENT FORENSIC",i+1,len(tops),str(t))
F=pd.DataFrame(rows);F.to_csv(OUT/"forensic_top100.csv",index=False)
# classify whether the "M1" assumption was false; do NOT alter frozen rule
classification="M1_LIKE" if integrity["mode_gap_min"]==1 else ("M5_LIKE" if integrity["mode_gap_min"]==5 else "OTHER_CADENCE")
summary={"run_id":rid,"status":"COMPLETE","source_v10":V10.name,"frozen_rule":rule["rule_id"],"research_max":"2022-12-31","locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"cadence_classification":classification,"global_integrity":integrity,"top100_exact_entry_fraction":float(F.exact_entry_exists.mean()),"top100_exact_exit_fraction":float(F.exact_exit_exists.mean()),"top100_max_bar_bp_median":float(F.max_abs_bar_bp.median()),"top100_max_bar_bp_max":float(F.max_abs_bar_bp.max()),"raw_source_candidates_found":len(raw_candidates),"errors":[]}
# gate is conservative: if M5-like, cached data is not M1 and earlier language must be corrected, but 60m rule may still be testable on 5m closes.
if classification=="M5_LIKE":
 summary["verdict"]="CADENCE_CORRECTION_REQUIRED"
 summary["next_gate"]="Do not open OOS yet. Treat research source as 5-minute cadence, verify original HistData provenance/format and recompute execution/data-quality assumptions for the frozen 60-minute rule without changing its signal definition."
elif classification=="M1_LIKE" and F.exact_entry_exists.all() and F.exact_exit_exists.all():
 summary["verdict"]="FORENSIC_PASS_WITH_FILLABILITY_CAVEAT"
 summary["next_gate"]="Human may approve opening locked OOS 2023-2025 with the frozen rule unchanged; historical close-only data still cannot prove fills/spread."
else:
 summary["verdict"]="FORENSIC_HOLD"
 summary["next_gate"]="Resolve cadence/timestamp anomalies before OOS."
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(summary,indent=2));prog(OUT,"COMPLETE",1,1,summary["verdict"])
print("\n=== V10B FORENSIC RECEIPT ===");print(json.dumps(summary,indent=2))
print("\n=== GAP DISTRIBUTION TOP ===");print(cad.sort_values(ascending=False).head(15).to_string())
print("\n=== TOP 25 FORENSIC ===");print(F.head(25).to_string(index=False))
print("\n=== SOURCE MANIFEST SAMPLE ===");print(pd.DataFrame(manifest).head(30).to_string(index=False))
print("\nRUN:",OUT)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V10b compile failed"}
Write-Host "=== GUARDIAN EDGE FACTORY V10b — FORENSIC ONLY / OOS LOCKED ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V10b run failed"}
