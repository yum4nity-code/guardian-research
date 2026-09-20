param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v60_cftc_validation.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib,re,zipfile,tempfile,os
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";SRC=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v59"/"GEF59-20260920-184355";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v60";OUT.mkdir(parents=True,exist_ok=True)
EXP_C="70e6ca8fccd1228888d4e2f71421ba974cf2690e580bc21b677cedf575229ade";EXP_G="6c55a7d34a4c6b9b78bf948659e9d9f25626af211a75fb70b900e17efb678618"
t=time.time();rid="GEF60-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF60] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
cf=SRC/"V60_IMMUTABLE_CANDIDATES.csv";gf=SRC/"V60_VALIDATION_GATE.json"
if hashlib.sha256(cf.read_bytes()).hexdigest()!=EXP_C or hashlib.sha256(gf.read_bytes()).hexdigest()!=EXP_G:raise RuntimeError("V59 freeze/gate SHA mismatch")
F=pd.read_csv(cf);gate=json.loads(gf.read_text());prog(1,8,f"freeze+gate verified candidates={len(F)}")
# 2018-2022 only
files=sorted((DL/"raw"/"cftc"/"futures_only_reports").glob("*excel*.zip"));use=[p for p in files if any(str(y) in p.name for y in range(2018,2023))]
rows=[]
for j,p in enumerate(use,1):
 with zipfile.ZipFile(p) as z:
  for m in [x for x in z.namelist() if x.lower().endswith((".xls",".xlsx"))]:
   with tempfile.NamedTemporaryFile(suffix=Path(m).suffix,delete=False) as tf:tf.write(z.read(m));tmp=tf.name
   try:rows.append(pd.read_excel(tmp))
   finally:
    try:os.unlink(tmp)
    except:pass
 print(f"[GEF60] CFTC archive {j}/{len(use)}",flush=True)
C=pd.concat(rows,ignore_index=True,sort=False).copy()
def col(n):
 z=[c for c in C.columns if str(c).lower()==n.lower()]
 if not z:raise RuntimeError("Missing "+n)
 return z[0]
dc=col("As_of_Date_In_Form_YYMMDD");mc=col("Market_and_Exchange_Names");oi=col("Open_Interest_All");cl=col("Comm_Positions_Long_All");cs=col("Comm_Positions_Short_All")
def ymd(v):
 try:s=str(int(float(v))).zfill(6);yy=int(s[:2]);return pd.Timestamp(2000+yy if yy<70 else 1900+yy,int(s[2:4]),int(s[4:6]))
 except:return pd.NaT
C["REPORT_DATE"]=C[dc].map(ymd);C[oi]=pd.to_numeric(C[oi],errors="coerce");C[cl]=pd.to_numeric(C[cl],errors="coerce");C[cs]=pd.to_numeric(C[cs],errors="coerce")
C=C[C.REPORT_DATE.notna()&C[mc].notna()&(C[oi]>0)].copy();C["commercial_net_pct_oi"]=(C[cl]-C[cs])/C[oi]
wd=C.REPORT_DATE.dt.weekday;days=(7-wd)%7;days=days.where(days>0,7);C["AVAILABLE_AT"]=(C.REPORT_DATE+pd.to_timedelta(days,unit="D")).dt.normalize();prog(2,8,f"CFTC validation rows={len(C)}")
def spot(sym):
 fs=[]
 for q in DL.rglob(f"*{sym}*.parquet"):
  ys=[int(x) for x in re.findall(r"20\d{2}",q.name)]
  if ys and not any(2018<=y<=2022 for y in ys):continue
  try:
   d=pd.read_parquet(q);dc2=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None);pc=next((c for c in d.columns if str(c).lower() in ["close","bidclose","price"]),None)
   if dc2 is None and isinstance(d.index,pd.DatetimeIndex):d=d.reset_index();dc2=d.columns[0]
   if dc2 is None or pc is None:continue
   x=pd.DataFrame({"dt":pd.to_datetime(d[dc2],errors="coerce"),"px":pd.to_numeric(d[pc],errors="coerce")}).dropna();x=x[(x.dt.dt.year>=2018)&(x.dt.dt.year<=2022)]
   if len(x):fs.append(x)
  except:pass
 if not fs:raise RuntimeError("No validation spot "+sym)
 x=pd.concat(fs).sort_values("dt").drop_duplicates("dt");return x.set_index("dt").px.resample("1D").last().dropna()
out=[]
for i,r in F.iterrows():
 cc=C[C[mc]==r.cftc_market].sort_values("AVAILABLE_AT").copy();base=r.feature
 # Warm-up from 2018-only CFTC is intentionally NOT allowed: rolling percentile needs prior history.
 # Load 2015-2022 same contract solely for feature history; target returns remain strictly 2018-2022.
 histfiles=[p for p in files if any(str(y) in p.name for y in range(2015,2023))]
 hr=[]
 for p in histfiles:
  with zipfile.ZipFile(p) as z:
   for m in [x for x in z.namelist() if x.lower().endswith((".xls",".xlsx"))]:
    with tempfile.NamedTemporaryFile(suffix=Path(m).suffix,delete=False) as tf:tf.write(z.read(m));tmp=tf.name
    try:hr.append(pd.read_excel(tmp))
    finally:
     try:os.unlink(tmp)
     except:pass
 H=pd.concat(hr,ignore_index=True,sort=False);hd=[c for c in H.columns if str(c).lower()=="as_of_date_in_form_yymmdd"][0];hm=[c for c in H.columns if str(c).lower()=="market_and_exchange_names"][0];hoi=[c for c in H.columns if str(c).lower()=="open_interest_all"][0];hcl=[c for c in H.columns if str(c).lower()=="comm_positions_long_all"][0];hcs=[c for c in H.columns if str(c).lower()=="comm_positions_short_all"][0]
 H["REPORT_DATE"]=H[hd].map(ymd)
 for z in [hoi,hcl,hcs]:H[z]=pd.to_numeric(H[z],errors="coerce")
 H=H[(H[hm]==r.cftc_market)&H.REPORT_DATE.notna()&(H[hoi]>0)].copy();H[base]=(H[hcl]-H[hcs])/H[hoi];w=H.REPORT_DATE.dt.weekday;dd=(7-w)%7;dd=dd.where(dd>0,7);H["AVAILABLE_AT"]=(H.REPORT_DATE+pd.to_timedelta(dd,unit="D")).dt.normalize();H=H.sort_values("AVAILABLE_AT");H["pct"]=H[base].rolling(156,min_periods=52).rank(pct=True);H=H[(H.AVAILABLE_AT.dt.year>=2018)&(H.AVAILABLE_AT.dt.year<=2022)]
 s=spot(r.market);d=pd.DataFrame({"px":s}).reset_index();d.columns=["dt","px"];d=pd.merge_asof(d.sort_values("dt"),H[["AVAILABLE_AT","pct"]],left_on="dt",right_on="AVAILABLE_AT",direction="backward");h=int(r.h);d["ret"]=d.px.shift(-h)/d.px-1
 mask=d.pct>=float(r.q) if r.tail=="hi" else d.pct<=float(r.q);x=(d.loc[mask,"ret"]*int(r.trade_side)).dropna();dates=d.loc[x.index,"dt"];tmp=pd.DataFrame({"x":x.values,"dt":dates.values})
 yrs=tmp.assign(year=pd.to_datetime(tmp.dt).dt.year).groupby("year").x.mean();sx=x.sort_values(ascending=False);trim=sx.iloc[int(np.ceil(len(sx)*.01)):] if len(sx) else sx;day=tmp.groupby("dt").x.sum().sort_values(ascending=False);rm5=tmp[~tmp.dt.isin(day.head(5).index)].x
 keep=[];last=None
 for _,z in tmp.sort_values("dt").iterrows():
  zdt=pd.Timestamp(z["dt"]);zx=float(z["x"])
  if last is None or zdt>=last+pd.Timedelta(days=h):keep.append(zx);last=zdt
 non=pd.Series(keep,dtype=float)
 vals={"n":len(x),"gross_bp":x.mean()*10000 if len(x) else np.nan,"hit":(x>0).mean() if len(x) else np.nan,"positive_year_fraction":(yrs>0).mean() if len(yrs) else 0,"trim1_bp":trim.mean()*10000 if len(trim) else np.nan,"remove_best5days_bp":rm5.mean()*10000 if len(rm5) else np.nan,"true_nonoverlap_bp":non.mean()*10000 if len(non) else np.nan,"nonoverlap_n":len(non)}
 req=gate["requirements"];passed=bool(vals["n"]>=req["n_min"] and vals["gross_bp"]>0 and vals["hit"]>=req["hit_rate_min"] and vals["positive_year_fraction"]>=req["positive_year_fraction_min"] and vals["trim1_bp"]>0 and vals["remove_best5days_bp"]>0 and vals["true_nonoverlap_bp"]>0)
 out.append({"key":r.key,"market":r.market,**vals,"pass":passed});prog(3+i,8,f"{r.market} n={len(x)} gross={vals['gross_bp']:.2f}bp pass={passed}")
R=pd.DataFrame(out);R.to_csv(O/"VALIDATION_RESULTS.csv",index=False);P=R[R["pass"]];P.to_csv(O/"PREOOS_SURVIVORS.csv",index=False);psha=hashlib.sha256((O/"PREOOS_SURVIVORS.csv").read_bytes()).hexdigest()
receipt={"run_id":rid,"status":"COMPLETE_CFTC_INDEPENDENT_VALIDATION","period":"2018-2022 only","candidate_sha256":EXP_C,"gate_sha256":EXP_G,"tested":len(R),"passed":len(P),"preoos_survivor_sha256":psha,"locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"retuning":False}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(7,8,f"validation complete passed={len(P)}");prog(8,8,"HARD STOP before 2023-2025 OOS")
print("\n=== V60 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== VALIDATION RESULTS ===");print(R.to_string(index=False));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V60 compile failed"}
Write-Host "=== GEF V60 - CFTC INDEPENDENT VALIDATION 2018-2022 ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V60 failed"}
