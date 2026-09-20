param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v58_cftc_prevalidation.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib,re,zipfile,tempfile,os
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";SRC=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v57"/"GEF57-20260920-183544";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v58";OUT.mkdir(parents=True,exist_ok=True)
EXPECTED="ae41a85c8829e9f4c70b7fe05cbb2f65a3ff520b9d792ffbc61fc6b9749ab142"
t=time.time();rid="GEF58-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF58] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
fp=SRC/"V58_SURVIVORS.csv";sha=hashlib.sha256(fp.read_bytes()).hexdigest()
if sha!=EXPECTED:raise RuntimeError("V57 survivor SHA mismatch")
S=pd.read_csv(fp);prog(1,10,f"verified V57 survivors sha={sha[:12]} n={len(S)}")
# Recover frozen specifications only; no 2018+ data.
F=pd.read_csv(ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v56c"/"GEF56C-20260920-183439"/"V57_FROZEN_INPUT.csv")
S=S.merge(F[["key","cftc_market","feature","tail","q","h","trade_side"]],on="key",how="left",validate="one_to_one")
# Parse 2014-2017 CFTC only.
files=sorted((DL/"raw"/"cftc"/"futures_only_reports").glob("*excel*.zip"));use=[p for p in files if any(str(y) in p.name for y in range(2014,2018))]
rows=[]
for j,p in enumerate(use,1):
 with zipfile.ZipFile(p) as z:
  for m in [x for x in z.namelist() if x.lower().endswith((".xls",".xlsx"))]:
   with tempfile.NamedTemporaryFile(suffix=Path(m).suffix,delete=False) as tf:tf.write(z.read(m));tmp=tf.name
   try:rows.append(pd.read_excel(tmp))
   finally:
    try:os.unlink(tmp)
    except:pass
 print(f"[GEF58] CFTC archive {j}/{len(use)}",flush=True)
C=pd.concat(rows,ignore_index=True,sort=False)
def col(n):
 z=[c for c in C.columns if str(c).lower()==n.lower()]
 if not z:raise RuntimeError("Missing "+n)
 return z[0]
dc=col("As_of_Date_In_Form_YYMMDD");mc=col("Market_and_Exchange_Names");oi=col("Open_Interest_All");nl=col("NonComm_Positions_Long_All");ns=col("NonComm_Positions_Short_All");cl=col("Comm_Positions_Long_All");cs=col("Comm_Positions_Short_All")
def ymd(v):
 try:s=str(int(float(v))).zfill(6);yy=int(s[:2]);return pd.Timestamp(2000+yy if yy<70 else 1900+yy,int(s[2:4]),int(s[4:6]))
 except:return pd.NaT
C["REPORT_DATE"]=C[dc].map(ymd)
for c in [oi,nl,ns,cl,cs]:C[c]=pd.to_numeric(C[c],errors="coerce")
C=C[C.REPORT_DATE.notna()&C[mc].notna()&(C[oi]>0)].copy();C["noncomm_net_pct_oi"]=(C[nl]-C[ns])/C[oi];C["commercial_net_pct_oi"]=(C[cl]-C[cs])/C[oi]
wd=C.REPORT_DATE.dt.weekday;days=(7-wd)%7;days=days.where(days>0,7);C["AVAILABLE_AT"]=(C.REPORT_DATE+pd.to_timedelta(days,unit="D")).dt.normalize()
prog(2,10,f"CFTC 2014-17 ready rows={len(C)}")
def spot(sym):
 fs=[];cand=list(DL.rglob(f"*{sym}*.parquet"))
 for q in cand:
  ys=[int(x) for x in re.findall(r"20\d{2}",q.name)]
  if ys and not any(2014<=y<=2017 for y in ys):continue
  try:
   d=pd.read_parquet(q);dc2=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None);pc=next((c for c in d.columns if str(c).lower() in ["close","bidclose","price"]),None)
   if dc2 is None and isinstance(d.index,pd.DatetimeIndex):d=d.reset_index();dc2=d.columns[0]
   if dc2 is None or pc is None:continue
   x=pd.DataFrame({"dt":pd.to_datetime(d[dc2],errors="coerce"),"px":pd.to_numeric(d[pc],errors="coerce")}).dropna();x=x[(x.dt.dt.year>=2014)&(x.dt.dt.year<=2017)]
   if len(x):fs.append(x)
  except:pass
 if not fs:raise RuntimeError("No spot "+sym)
 x=pd.concat(fs).sort_values("dt").drop_duplicates("dt");return x.set_index("dt").px.resample("1D").last().dropna()
def metrics(x,dates):
 if len(x)==0:return {"n":0,"bp":np.nan,"hit":np.nan}
 return {"n":len(x),"bp":x.mean()*10000,"hit":(x>0).mean()}
out=[]
for i,r in S.iterrows():
 cc=C[C[mc]==r.cftc_market].sort_values("AVAILABLE_AT").copy();base=r.feature;cc["pct"]=cc[base].rolling(156,min_periods=52).rank(pct=True)
 ss=spot(r.market);d=pd.DataFrame({"px":ss}).reset_index();d.columns=["dt","px"];d=pd.merge_asof(d.sort_values("dt"),cc[["AVAILABLE_AT","pct"]].sort_values("AVAILABLE_AT"),left_on="dt",right_on="AVAILABLE_AT",direction="backward")
 h=int(r.h);d["ret"]=d.px.shift(-h)/d.px-1
 mask=d.pct>=float(r.q) if r.tail=="hi" else d.pct<=float(r.q);x=(d.loc[mask,"ret"]*int(r.trade_side)).dropna();dates=d.loc[x.index,"dt"]
 base_m=metrics(x,dates)
 sx=x.sort_values(ascending=False);trim1=sx.iloc[int(np.ceil(len(sx)*.01)):] if len(sx) else sx;trim2=sx.iloc[int(np.ceil(len(sx)*.02)):] if len(sx) else sx
 tmp=pd.DataFrame({"x":x.values,"dt":dates.values});day=tmp.groupby("dt").x.sum().sort_values(ascending=False)
 rm5=tmp[~tmp.dt.isin(day.head(5).index)].x
 # true greedy non-overlap by entry date
 ordx=tmp.sort_values("dt");keep=[];last=None
 for _,z in ordx.iterrows():
  if last is None or z.dt>=last+pd.Timedelta(days=h):keep.append(z.x);last=z.dt
 non=pd.Series(keep,dtype=float)
 # threshold neighbours on same replication window, diagnostic only
 neigh={}
 for q in sorted(set([max(.05,float(r.q)-.025),float(r.q),min(.95,float(r.q)+.025)])):
  mm=d.pct>=q if r.tail=="hi" else d.pct<=q;xx=(d.loc[mm,"ret"]*int(r.trade_side)).dropna();neigh[str(q)]=xx.mean()*10000 if len(xx) else None
 passed=bool(base_m["bp"]>0 and trim1.mean()*10000>0 and trim2.mean()*10000>0 and (rm5.mean()*10000 if len(rm5) else -1)>0 and (non.mean()*10000 if len(non) else -1)>0 and sum(v is not None and v>0 for v in neigh.values())>=2)
 out.append({"key":r.key,"market":r.market,"n":len(x),"baseline_bp":base_m["bp"],"trim1_bp":trim1.mean()*10000,"trim2_bp":trim2.mean()*10000,"remove_best5days_bp":rm5.mean()*10000 if len(rm5) else np.nan,"nonoverlap_bp":non.mean()*10000 if len(non) else np.nan,"nonoverlap_n":len(non),"neighbor_bp":json.dumps(neigh),"pass":passed})
 prog(3+i,10,f"{r.market} robust={passed}")
R=pd.DataFrame(out);R.to_csv(O/"ROBUSTNESS_RESULTS.csv",index=False);P=R[R["pass"]].copy();P.to_csv(O/"V59_SURVIVORS.csv",index=False);psha=hashlib.sha256((O/"V59_SURVIVORS.csv").read_bytes()).hexdigest()
receipt={"run_id":rid,"status":"COMPLETE_CFTC_PREVALIDATION_ROBUSTNESS","period":"2014-2017 only","source_survivor_sha256":sha,"tested":len(R),"passed":len(P),"v59_survivor_sha256":psha,"validation_2018_2022_accessed":False,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"retuning":False}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(9,10,f"passed={len(P)} sha={psha[:12]}");prog(10,10,"STOP before validation")
print("\n=== V58 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== ROBUSTNESS RESULTS ===");print(R.to_string(index=False));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V58 compile failed"}
Write-Host "=== GEF V58 - CFTC PRE-VALIDATION ROBUSTNESS ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V58 failed"}
