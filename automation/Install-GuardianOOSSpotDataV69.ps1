param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Tmp=Join-Path $Root "_tmp_histdata_v69"
$Out=Join-Path $Root "DataLake\raw\histdata"
New-Item -ItemType Directory -Force -Path $Tmp | Out-Null

$Py=Join-Path $Root "DataLake\tools\install_oos_spot_v69.py"
$code=@'
from pathlib import Path
import subprocess,sys,hashlib,json,time,pandas as pd,zipfile,shutil,os
ROOT=Path(r"D:\MT5_Backtests")
TMP=ROOT/"_tmp_histdata_v69"
OUT=ROOT/"DataLake"/"raw"/"histdata"
PAIRS=["NSXUSD","USDCHF"]; YEARS=[2023,2024,2025]
t=time.time()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0
 print(f"[V69-DATA] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
# install lightweight downloader only if missing
try: import histdata
except Exception:
 subprocess.check_call([sys.executable,"-m","pip","install","git+https://github.com/StratCraftsAI/histdata.git"])
prog(1,10,"downloader available")
# Use CLI documented by project; download only authorized 2023-2025, never 2026.
cmd=["histdata","--pairs",*PAIRS,"--year-start","2023","--year-end","2025","--output",str(TMP)]
print("[V69-DATA] command:"," ".join(cmd),flush=True)
try:
 subprocess.check_call(cmd)
except Exception:
 # fallback: discover CLI help rather than guessing silently
 subprocess.call(["histdata","--help"])
 raise
prog(2,10,"download complete")
# Find produced parquet/csv/zip and normalize to canonical per-year parquet.
def read_any(p):
 if p.suffix.lower()==".parquet": return pd.read_parquet(p)
 if p.suffix.lower()==".csv":
  d=pd.read_csv(p,sep=None,engine="python",header=None)
  if d.shape[1]>=5:
   d=d.iloc[:,:6]; d.columns=["timestamp","open","high","low","close","volume"][:d.shape[1]]
  return d
 return None
receipt={"status":"COMPLETE","protected_2026_accessed":False,"files":[]}
for pi,pair in enumerate(PAIRS):
 files=[p for p in TMP.rglob("*") if p.is_file() and pair.lower() in p.name.lower() and p.suffix.lower() in [".parquet",".csv"]]
 if not files: raise RuntimeError(f"No normalized files found for {pair} under {TMP}")
 frames=[]
 for p in files:
  d=read_any(p)
  if d is None: continue
  dc=next((c for c in d.columns if str(c).lower() in ["timestamp","datetime","time","date"]),None)
  if dc is None: continue
  dt=pd.to_datetime(d[dc],errors="coerce")
  if dt.notna().any() and (dt.dt.year>=2026).any(): raise RuntimeError("2026 contamination")
  d=d.copy(); d["__dt"]=dt; frames.append(d)
 if not frames: raise RuntimeError(f"No parseable data for {pair}")
 D=pd.concat(frames,ignore_index=True)
 for yi,y in enumerate(YEARS):
  Y=D[D["__dt"].dt.year==y].copy()
  if Y.empty: raise RuntimeError(f"Missing {pair} {y}")
  Y=Y.drop(columns=["__dt"])
  # canonicalize datetime name if needed
  dc=next((c for c in Y.columns if str(c).lower() in ["timestamp","datetime","time","date"]),None)
  if dc!="datetime": Y=Y.rename(columns={dc:"datetime"})
  dest=OUT/pair/"M1"/f"{pair}_M1_{y}.parquet";dest.parent.mkdir(parents=True,exist_ok=True)
  Y.to_parquet(dest,index=False)
  h=hashlib.sha256(dest.read_bytes()).hexdigest()
  dt=pd.to_datetime(Y["datetime"],errors="coerce")
  receipt["files"].append({"market":pair,"year":y,"path":str(dest),"rows":len(Y),"min":str(dt.min()),"max":str(dt.max()),"sha256":h})
  prog(3+pi*3+yi,10,f"{pair} {y} rows={len(Y):,} sha={h[:12]}")
man=ROOT/"DataLake"/"manifests"/"oos_spot_2023_2025_v69_receipt.json";man.parent.mkdir(parents=True,exist_ok=True);man.write_text(json.dumps(receipt,indent=2))
prog(9,10,f"manifest {man}")
prog(10,10,"DONE; 2026 untouched")
print("\n=== V69 DATA RECEIPT ===");print(json.dumps(receipt,indent=2))
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "installer compile failed"}
py $Py
if($LASTEXITCODE -ne 0){throw "installer failed"}
