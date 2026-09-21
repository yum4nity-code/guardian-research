param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\install_oos_spot_2023_2025.py"
$code=@'
from pathlib import Path
import subprocess,sys,hashlib,json,time
import pandas as pd
ROOT=Path(r"D:\MT5_Backtests")
DL=ROOT/"DataLake"
OUT=DL/"raw"/"histdata"
pairs=["EURUSD","USDCAD"]; years=[2023,2024,2025]
t=time.time()
def prog(i,n,msg):
 e=time.time()-t; eta=e/i*(n-i) if i else 0
 print(f"[OOS-DATA] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
prog(1,10,"preflight")
try:
 import histdata_fetcher
except ImportError:
 print("[OOS-DATA] installing histdata-fetcher",flush=True)
 subprocess.check_call([sys.executable,"-m","pip","install","histdata-fetcher"])
 from histdata_fetcher import fetch_data
else:
 from histdata_fetcher import fetch_data
prog(2,10,"downloader ready")
receipts=[]
k=2
for pair in pairs:
 for year in years:
  dest=OUT/pair/"M1"/f"{pair}_M1_{year}.parquet"
  dest.parent.mkdir(parents=True,exist_ok=True)
  print(f"[OOS-DATA] FETCH {pair} {year}",flush=True)
  r=fetch_data(pair=pair,start_date=f"{year}-01-01",end_date=f"{year}-12-31",timeframe="1min",output_format=None)
  if not r.ok or r.data is None or len(r.data)==0:
   raise RuntimeError(f"download failed {pair} {year}: {getattr(r,'failed_periods',None)}")
  d=r.data.copy()
  dtc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
  if dtc is None:
   if isinstance(d.index,pd.DatetimeIndex): d=d.reset_index();dtc=d.columns[0]
   else: raise RuntimeError(f"no datetime {pair} {year}")
  close=next((c for c in d.columns if str(c).lower()=="close"),None)
  if close is None: raise RuntimeError(f"no close {pair} {year}")
  d[dtc]=pd.to_datetime(d[dtc],errors="coerce")
  d=d[d[dtc].notna() & (d[dtc].dt.year==year)].sort_values(dtc).drop_duplicates(dtc)
  if len(d)<100000: raise RuntimeError(f"suspiciously few rows {pair} {year}: {len(d)}")
  d.to_parquet(dest,index=False)
  sha=hashlib.sha256(dest.read_bytes()).hexdigest()
  receipts.append({"pair":pair,"year":year,"rows":len(d),"min":str(d[dtc].min()),"max":str(d[dtc].max()),"sha256":sha,"path":str(dest),"failed_periods":[str(x) for x in getattr(r,"failed_periods",[])]})
  k+=1;prog(k,10,f"{pair} {year} rows={len(d):,} sha={sha[:12]}")
# integrity: ensure exact six files and no 2026
for x in receipts:
 if x["year"]>=2026: raise RuntimeError("2026 contamination")
manifest=DL/"manifests"/"oos_spot_2023_2025_receipt.json";manifest.parent.mkdir(parents=True,exist_ok=True);manifest.write_text(json.dumps(receipts,indent=2))
prog(9,10,f"manifest={manifest}")
prog(10,10,"COMPLETE; 2026 untouched")
print()
print("=== OOS SPOT DATA RECEIPT ===")
print(json.dumps(receipts,indent=2))
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "OOS data installer compile failed"}
Write-Host "=== INSTALL OOS SPOT 2023-2025 (EURUSD + USDCAD) ==="
py $Py
if($LASTEXITCODE -ne 0){throw "OOS data installer failed"}
