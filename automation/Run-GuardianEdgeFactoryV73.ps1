param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v73_fomc_causal_event_table.py"
$code=@'
from pathlib import Path
import pandas as pd,json,re,time,hashlib
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";SRC=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v72"
runs=sorted([p for p in SRC.glob("GEF72-*") if (p/"SOURCE_INVENTORY.csv").exists()])
if not runs:raise RuntimeError("No V72 inventory")
V72=runs[-1];inv=pd.read_csv(V72/"SOURCE_INVENTORY.csv");OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v73";rid="GEF73-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF73] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
prog(1,8,f"V72 inventory loaded files={len(inv)}; zero market-return testing")
# FOMC corpus: extract only dates/type clues from path/name/content. No invented release times.
F=inv[inv.fomc==True].copy();events=[]
date_patterns=[r"(?<!\d)((?:19|20)\d{2})[-_]?([01]\d)[-_]?([0-3]\d)(?!\d)",r"(?<!\d)([01]\d)[-_]([0-3]\d)[-_]((?:19|20)\d{2})(?!\d)"]
for _,r in F.iterrows():
 p=Path(r.path);name=p.name.lower();txt=""
 if p.suffix.lower() in [".txt",".html",".htm",".json",".md",".csv"]:
  try:txt=p.read_text(encoding="utf-8",errors="ignore")[:300000]
  except:pass
 blob=name+" "+txt[:50000]
 dates=[]
 for pat in date_patterns:
  for m in re.finditer(pat,blob):
   try:
    g=m.groups()
    if len(g)==3 and len(g[0])==4:y,mo,da=map(int,g)
    else:mo,da,y=map(int,g)
    d=pd.Timestamp(y,mo,da)
    if 2010<=y<=2022:dates.append(d)
   except:pass
 if not dates:continue
 d=min(dates)
 typ="statement" if "statement" in blob else ("minutes" if "minute" in blob else ("press_conference" if "press conference" in blob else ("speech" if "speech" in blob else "fomc_document")))
 events.append({"event_date":d.date().isoformat(),"document_type":typ,"source_path":str(p),"release_time_verified":False,"available_at":None})
prog(2,8,f"dated FOMC document candidates={len(events)}")
E=pd.DataFrame(events)
if len(E):E=E.sort_values(["event_date","document_type","source_path"]).drop_duplicates(["event_date","document_type"])
E.to_csv(O/"FOMC_DATED_DOCUMENTS_UNTIMED.csv",index=False);prog(3,8,"dated documents written; release time deliberately unset")
# Build meeting-date candidates separately. A date alone is NOT causal intraday availability.
if len(E):
 M=E[E.document_type.isin(["statement","fomc_document"])][["event_date"]].drop_duplicates().sort_values("event_date")
else:M=pd.DataFrame(columns=["event_date"])
M.to_csv(O/"FOMC_MEETING_DATE_CANDIDATES.csv",index=False);prog(4,8,f"meeting-date candidates={len(M)}")
# Inventory filename/content evidence for explicit time strings; evidence only, never automatically trusted.
ev=[]
timepat=re.compile(r"\b(?:1[0-2]|0?[1-9]):[0-5]\d\s*(?:a\.?m\.?|p\.?m\.?)|\b(?:[01]?\d|2[0-3]):[0-5]\d\b",re.I)
for _,r in F.iterrows():
 p=Path(r.path)
 if p.suffix.lower() not in [".txt",".html",".htm",".json",".md",".csv"]:continue
 try:txt=p.read_text(encoding="utf-8",errors="ignore")[:300000]
 except:continue
 hits=list(dict.fromkeys(m.group(0) for m in timepat.finditer(txt)))
 if hits:ev.append({"source_path":str(p),"time_strings":hits[:20]})
(O/"FOMC_TIME_STRING_EVIDENCE.json").write_text(json.dumps(ev,indent=2));prog(5,8,f"documents containing time-like strings={len(ev)}")
# Causal readiness gate: exact AVAILABLE_AT cannot be manufactured from event date or generic time text.
ready=pd.DataFrame(columns=["event_date","available_at","document_type","source_path","verification_basis"])
ready.to_csv(O/"CAUSAL_FOMC_EVENTS.csv",index=False)
block={"causal_events_ready":0,"reason":"Local corpus contains no verified publication timestamp field. Event dates/time-like text are insufficient to assign AVAILABLE_AT safely.","return_trials_allowed":False,"required_next":"Verify official FOMC release-time semantics externally or from source metadata, then freeze event table before any return test."}
(O/"CAUSALITY_GATE.json").write_text(json.dumps(block,indent=2));prog(6,8,"causality gate BLOCKED; no fabricated 14:00 timestamp")
# Macro sources: preserve separate path; ALFRED vintage correctness alone does not imply intraday release timestamp.
macro=inv[(inv.bls==True)|(inv.alfred==True)|(inv.macro==True)].copy();macro.to_csv(O/"MACRO_SOURCE_INVENTORY.csv",index=False);prog(7,8,f"macro-related local files={len(macro)}")
receipt={"run_id":rid,"status":"COMPLETE_FOMC_DATE_EXTRACTION_CAUSALITY_BLOCKED","dated_fomc_candidates":len(E),"verified_causal_events":0,"return_trials":0,"2018_plus_market_returns_accessed":False,"oos_2023_2025_accessed":False,"protected_2026_accessed":False,"next":"VERIFY_OFFICIAL_RELEASE_TIMES_THEN_FREEZE_EVENT_TABLE"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(8,8,"STOP before market returns")
print("\n=== V73 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== CAUSALITY GATE ===");print(json.dumps(block,indent=2));print("\n=== SAMPLE DATED FOMC CANDIDATES ===");print(E.head(25).to_string(index=False) if len(E) else "NONE");print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V73 compile failed"}
Write-Host "=== GEF V73 - FOMC CAUSAL EVENT TABLE BUILD ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V73 failed"}
