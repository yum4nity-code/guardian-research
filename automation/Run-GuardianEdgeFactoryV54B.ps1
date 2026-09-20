param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v54b_cftc_zip_probe.py"
$code=@'
from pathlib import Path
import zipfile,json,time,hashlib
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";SRC=DL/"raw"/"cftc"/"futures_only_reports";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v54b";OUT.mkdir(parents=True,exist_ok=True)
t=time.time();rid="GEF54B-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF54B] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
files=sorted(SRC.glob("*.zip"))
use=[p for p in files if any(str(y) in p.name for y in range(2009,2014))]
prog(1,6,f"archives={len(use)}")
diag=[]
for j,p in enumerate(use,1):
 item={"archive":str(p),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"members":[]}
 try:
  with zipfile.ZipFile(p) as z:
   for m in z.infolist()[:25]:
    rec={"name":m.filename,"size":m.file_size}
    if not m.is_dir():
     b=z.read(m.filename)[:1500]
     rec["head_latin1"]=b.decode("latin1",errors="replace")
    item["members"].append(rec)
 except Exception as e:item["error"]=repr(e)
 diag.append(item)
 if j==1 or j==len(use) or j%5==0: prog(1+j,6+len(use),f"probed {j}/{len(use)}")
(O/"ZIP_MEMBER_DIAGNOSTICS.json").write_text(json.dumps(diag,indent=2),encoding="utf-8")
prog(5,6,"diagnostics written")
print("\n=== FIRST ARCHIVE MEMBERS ===")
if diag:
 print(json.dumps(diag[0],indent=2)[:12000])
receipt={"run_id":rid,"status":"COMPLETE_ZIP_FORMAT_PROBE","archive_count":len(use),"target_returns_accessed":False,"oos_accessed":False}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(6,6,"STOP")
print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V54B compile failed"}
Write-Host "=== GEF V54B - CFTC ZIP FORMAT PROBE ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V54B failed"}
