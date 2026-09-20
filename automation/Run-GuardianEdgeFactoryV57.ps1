param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v57_cftc_replication.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib,re,zipfile,tempfile,os
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";SRC=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v56c"/"GEF56C-20260920-183439";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v57";OUT.mkdir(parents=True,exist_ok=True)
EXPECTED="8b6d5e538b9ef1f85699214d4c107a7575135814ebcf6cbed8b29e6b4d68818c"
t=time.time();rid="GEF57-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF57] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
fp=SRC/"V57_FROZEN_INPUT.csv";sha=hashlib.sha256(fp.read_bytes()).hexdigest()
if sha!=EXPECTED:raise RuntimeError("V57 frozen input SHA mismatch")
F=pd.read_csv(fp);prog(1,10,f"verified frozen input sha={sha[:12]} lineages={len(F)}")
# Parse ONLY CFTC Excel archives 2014-2017.
files=sorted((DL/"raw"/"cftc"/"futures_only_reports").glob("*excel*.zip"));use=[p for p in files if any(str(y) in p.name for y in range(2014,2018))]
rows=[];errors=[]
for p in use:
 try:
  with zipfile.ZipFile(p) as z:
   for m in [x for x in z.namelist() if x.lower().endswith((".xls",".xlsx"))]:
    with tempfile.NamedTemporaryFile(suffix=Path(m).suffix,delete=False) as tf:tf.write(z.read(m));tmp=tf.name
    try:d=pd.read_excel(tmp);d=d.copy();rows.append(d)
    finally:
     try:os.unlink(tmp)
     except:pass
 except Exception as e:errors.append({"archive":str(p),"error":repr(e)})
if not rows:raise RuntimeError("No 2014-2017 CFTC Excel rows")
C=pd.concat(rows,ignore_index=True,sort=False)
def col(name):
 z=[c for c in C.columns if str(c).lower()==name.lower()]
 if not z:raise RuntimeError("Missing "+name)
 return z[0]
dc=col("As_of_Date_In_Form_YYMMDD");mc=col("Market_and_Exchange_Names");oi=col("Open_Interest_All");nl=col("NonComm_Positions_Long_All");ns=col("NonComm_Positions_Short_All");cl=col("Comm_Positions_Long_All");cs=col("Comm_Positions_Short_All")
def yymmdd(v):
 try:
  s=str(int(float(v))).zfill(6);yy=int(s[:2]);return pd.Timestamp(2000+yy if yy<70 else 1900+yy,int(s[2:4]),int(s[4:6]))
 except:return pd.NaT
C["REPORT_DATE"]=C[dc].map(yymmdd)
for c in [oi,nl,ns,cl,cs]:C[c]=pd.to_numeric(C[c],errors="coerce")
C=C[C.REPORT_DATE.notna()&C[mc].notna()&(C[oi]>0)].copy()
C["noncomm_net_pct_oi"]=(C[nl]-C[ns])/C[oi];C["commercial_net_pct_oi"]=(C[cl]-C[cs])/C[oi]
wd=C.REPORT_DATE.dt.weekday;days=(7-wd)%7;days=days.where(days>0,7);C["AVAILABLE_AT"]=(C.REPORT_DATE+pd.to_timedelta(days,unit="D")).dt.normalize()
prog(2,10,f"CFTC replication rows={len(C)} archives={len(use)}")
def spot_daily(sym):
 cand=list(DL.rglob(f"*{sym}*.parquet"));frames=[]
 for q in cand:
  yrs=[int(x) for x in re.findall(r"20\d{2}",q.name)]
  if yrs and not any(2014<=y<=2017 for y in yrs):continue
  try:
   d=pd.read_parquet(q);dc2=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None);pc=next((c for c in d.columns if str(c).lower() in ["close","bidclose","price"]),None)
   if dc2 is None and isinstance(d.index,pd.DatetimeIndex):d=d.reset_index();dc2=d.columns[0]
   if dc2 is None or pc is None:continue
   x=pd.DataFrame({"dt":pd.to_datetime(d[dc2],errors="coerce"),"px":pd.to_numeric(d[pc],errors="coerce")}).dropna();x=x[(x.dt.dt.year>=2014)&(x.dt.dt.year<=2017)]
   if len(x):frames.append(x)
  except:pass
 if not frames:raise RuntimeError("No 2014-2017 spot parquet for "+sym)
 x=pd.concat(frames).sort_values("dt").drop_duplicates("dt");return x.set_index("dt").px.resample("1D").last().dropna()
results=[]
for i,r in F.iterrows():
 sym=r.market;cc=C[C[mc]==r.cftc_market].sort_values("AVAILABLE_AT").copy();base=r.feature
 cc[base+"_pct"]=cc[base].rolling(156,min_periods=52).rank(pct=True)
 s=spot_daily(sym);df=pd.DataFrame({"px":s}).reset_index();df.columns=["dt","px"];df["dt"]=pd.to_datetime(df.dt);df=df.sort_values("dt")
 df=pd.merge_asof(df,cc[["AVAILABLE_AT",base+"_pct"]].sort_values("AVAILABLE_AT"),left_on="dt",right_on="AVAILABLE_AT",direction="backward")
 h=int(r.h);df["ret"]=df.px.shift(-h)/df.px-1
 mask=df[base+"_pct"]>=float(r.q) if r.tail=="hi" else df[base+"_pct"]<=float(r.q)
 x=(df.loc[mask,"ret"]*int(r.trade_side)).dropna();dates=df.loc[x.index,"dt"]
 years=x.groupby(dates.dt.year.to_numpy()).mean()
 # Frozen replication gate, same for all lineages.
 passed=bool(len(x)>=40 and x.mean()*10000>0 and (x>0).mean()>=.52 and ((years>0).mean()>=.50 if len(years) else False))
 results.append({"key":r.key,"lineage_family":r.lineage_family,"market":sym,"n":len(x),"gross_bp":x.mean()*10000 if len(x) else np.nan,"hit":(x>0).mean() if len(x) else np.nan,"positive_year_fraction":(years>0).mean() if len(years) else np.nan,"pass":passed})
 prog(3+i,10,f"{sym} {i+1}/{len(F)} n={len(x)} gross={x.mean()*10000:.2f}bp pass={passed}")
R=pd.DataFrame(results);R.to_csv(O/"REPLICATION_RESULTS.csv",index=False);S=R[R["pass"]].copy();S.to_csv(O/"V58_SURVIVORS.csv",index=False)
ssha=hashlib.sha256((O/"V58_SURVIVORS.csv").read_bytes()).hexdigest()
receipt={"run_id":rid,"status":"COMPLETE_CFTC_FROZEN_REPLICATION","period":"2014-2017 only","frozen_input_sha256":sha,"tested_lineages":len(R),"survivors":len(S),"survivor_sha256":ssha,"gate":"n>=40, gross_bp>0, hit>=0.52, positive_year_fraction>=0.50","validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"retuning":False,"errors":errors}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(9,10,f"replication survivors={len(S)} sha={ssha[:12]}");prog(10,10,"STOP before validation")
print("\n=== V57 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== REPLICATION RESULTS ===");print(R.to_string(index=False));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V57 compile failed"}
Write-Host "=== GEF V57 - CFTC FROZEN REPLICATION 2014-2017 ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V57 failed"}
