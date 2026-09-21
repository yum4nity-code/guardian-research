param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v82c_cftc_date_forensic.py"
$code=@'
from pathlib import Path
import pandas as pd,json,zipfile,tempfile,os,time,re
ROOT=Path(r"D:\MT5_Backtests");SRC=ROOT/"DataLake"/"raw"/"cftc"/"futures_only_reports"
rid="GEF82C-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");O=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v82c"/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF82C] {i}/{n} {100*i/n:.0f}% | elapsed {e:.1f}s | ETA {eta:.1f}s | {msg}",flush=True)
prog(1,6,"inspect raw CFTC date representation; no normalization, no edge search")
use=[p for p in sorted(SRC.glob("*.zip")) if any(str(y) in p.name for y in range(2009,2014)) and "excel" in p.name.lower()]
rows=[];samples=[]
for j,p in enumerate(use,1):
 with zipfile.ZipFile(p) as z:
  for m in [x for x in z.namelist() if x.lower().endswith((".xls",".xlsx"))]:
   with tempfile.NamedTemporaryFile(suffix=Path(m).suffix,delete=False) as tf:tf.write(z.read(m));tmp=tf.name
   try:
    d=pd.read_excel(tmp)
    cols=list(d.columns)
    datecols=[c for c in cols if any(k in str(c).lower() for k in ["date","yymmdd","yyyy"])]
    marketcols=[c for c in cols if "market" in str(c).lower() and "exchange" in str(c).lower()]
    for c in datecols[:8]:
     s=d[c]
     samples.append({"archive":p.name,"member":m,"column":str(c),"dtype":str(s.dtype),"non_null":int(s.notna().sum()),"sample_values":[str(x) for x in s.dropna().head(12).tolist()]})
    rows.append({"archive":p.name,"member":m,"rows":len(d),"date_columns":"|".join(map(str,datecols)),"market_columns":"|".join(map(str,marketcols))})
   finally:
    try:os.unlink(tmp)
 if j==1 or j==len(use) or j%2==0:prog(2,6,f"inspected {j}/{len(use)} archives")
pd.DataFrame(rows).to_csv(O/"TABLES.csv",index=False);(O/"DATE_SAMPLES.json").write_text(json.dumps(samples,indent=2))
prog(3,6,f"date fields sampled={len(samples)}")
# Determine parser rule from actual values, but do not rewrite source yet.
rules=[]
for x in samples:
 vals=x["sample_values"]; rule="UNRESOLVED"
 if vals:
  compact=[re.sub(r"\.0$","",v.strip()) for v in vals]
  if sum(bool(re.fullmatch(r"\d{6}",v)) for v in compact)>=max(1,len(compact)//2):rule="YYMMDD_EXPLICIT_FORMAT_%y%m%d"
  elif sum(bool(re.fullmatch(r"\d{8}",v)) for v in compact)>=max(1,len(compact)//2):rule="YYYYMMDD_EXPLICIT_FORMAT_%Y%m%d"
  else:rule="GENERIC_DATETIME"
 rules.append({**x,"recommended_parser":rule})
pd.DataFrame(rules).to_csv(O/"DATE_PARSER_RECOMMENDATIONS.csv",index=False)
prog(4,6,"parser recommendations derived from raw samples")
counts=pd.DataFrame(rules).recommended_parser.value_counts().to_dict() if rules else {}
receipt={"run_id":rid,"status":"COMPLETE_CFTC_DATE_FORENSIC","archives":len(use),"date_fields":len(samples),"parser_rule_counts":counts,"edge_trials":0,"2014_plus_accessed":False,"2023_plus_accessed":False,"protected_2026_accessed":False,"next":"repair V82B date parser only after inspecting this receipt"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(5,6,f"rules={counts}")
prog(6,6,"STOP")
print("\n=== V82C RECEIPT ===");print(json.dumps(receipt,indent=2))
print("\n=== DATE PARSER RECOMMENDATIONS ===");print(pd.DataFrame(rules)[["archive","column","dtype","sample_values","recommended_parser"]].head(30).to_string(index=False) if rules else "NONE")
print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V82C compile failed"}
Write-Host "=== GEF V82C - CFTC DATE FORENSIC ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V82C failed"}
