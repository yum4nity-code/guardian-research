param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v62_cftc_locked_oos.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib,re,zipfile,tempfile,os
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");DL=ROOT/"DataLake";SRC=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v61";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v62";OUT.mkdir(parents=True,exist_ok=True)
EXPECTED="41d36d378fa85a1ef44a4dcda41c9adccae0e0f3d122c935168aa5451fd339c0"
runs=sorted(SRC.glob("GEF61-*")); assert runs,"No V61 run"; V61=runs[-1]; fp=V61/"OOS_ELIGIBLE_CANDIDATES.csv"
if hashlib.sha256(fp.read_bytes()).hexdigest()!=EXPECTED:raise RuntimeError("V61 eligible SHA mismatch")
F=pd.read_csv(fp);
# Rehydrate immutable candidate specifications because V61 forensic output only carries metrics.
SPEC=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v59"/"GEF59-20260920-184355"/"V60_IMMUTABLE_CANDIDATES.csv"
SPECS=pd.read_csv(SPEC)
F=F.merge(SPECS[["key","cftc_market","feature","tail","q","h","trade_side"]],on="key",how="left",validate="one_to_one")
if F[["cftc_market","feature","tail","q","h","trade_side"]].isna().any().any():raise RuntimeError("Incomplete candidate spec rehydration")
t=time.time();rid="GEF62-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF62] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
prog(1,8,f"LOCKED OOS authorization input verified sha={EXPECTED[:12]} candidates={len(F)}")
# Predeclare final OOS gate BEFORE reading OOS.
gate={"window":"2023-2025","candidate_sha256":EXPECTED,"requirements":{"n_min":20,"gross_bp_gt":0,"hit_rate_min":0.50,"positive_year_fraction_min":2/3,"trim_best_1pct_bp_gt":0,"remove_best_3_days_bp_gt":0,"true_nonoverlap_bp_gt":0},"no_retuning":True,"protected_2026":"DO_NOT_OPEN"}
(O/"OOS_GATE_PREDECLARED.json").write_text(json.dumps(gate,indent=2));gsha=hashlib.sha256((O/"OOS_GATE_PREDECLARED.json").read_bytes()).hexdigest();prog(2,8,f"OOS gate frozen sha={gsha[:12]}")
# Preflight file discovery only; no OOS returns are computed here.
for sym in F["market"].tolist():
 cands=list(DL.rglob(f"*{sym}*.parquet"))
 print(f"[GEF62] preflight {sym}: parquet_candidates={len(cands)}",flush=True)
# CFTC feature history 2020-2025; targets strictly 2023-2025. Never read 2026.
files=sorted((DL/"raw"/"cftc"/"futures_only_reports").glob("*excel*.zip"));use=[p for p in files if any(str(y) in p.name for y in range(2020,2026)) and "2026" not in p.name]
rows=[]
for j,p in enumerate(use,1):
 with zipfile.ZipFile(p) as z:
  for m in [x for x in z.namelist() if x.lower().endswith((".xls",".xlsx"))]:
   with tempfile.NamedTemporaryFile(suffix=Path(m).suffix,delete=False) as tf:tf.write(z.read(m));tmp=tf.name
   try:rows.append(pd.read_excel(tmp))
   finally:
    try:os.unlink(tmp)
    except:pass
 print(f"[GEF62] CFTC archive {j}/{len(use)}",flush=True)
if not rows:raise RuntimeError("No <=2025 CFTC files available for OOS")
C=pd.concat(rows,ignore_index=True,sort=False).copy()
def col(n):
 z=[c for c in C.columns if str(c).lower()==n.lower()]
 if not z:raise RuntimeError("Missing "+n)
 return z[0]
dc=col("As_of_Date_In_Form_YYMMDD");mc=col("Market_and_Exchange_Names");oi=col("Open_Interest_All");cl=col("Comm_Positions_Long_All");cs=col("Comm_Positions_Short_All")
def ymd(v):
 try:s=str(int(float(v))).zfill(6);yy=int(s[:2]);return pd.Timestamp(2000+yy if yy<70 else 1900+yy,int(s[2:4]),int(s[4:6]))
 except:return pd.NaT
C["REPORT_DATE"]=C[dc].map(ymd)
for c in [oi,cl,cs]:C[c]=pd.to_numeric(C[c],errors="coerce")
C=C[C.REPORT_DATE.notna()&C[mc].notna()&(C[oi]>0)].copy();C["commercial_net_pct_oi"]=(C[cl]-C[cs])/C[oi]
wd=C.REPORT_DATE.dt.weekday;days=(7-wd)%7;days=days.where(days>0,7);C["AVAILABLE_AT"]=(C.REPORT_DATE+pd.to_timedelta(days,unit="D")).dt.normalize()
if (C.AVAILABLE_AT.dt.year>=2026).any():raise RuntimeError("2026 contamination")
prog(3,8,f"CFTC <=2025 loaded rows={len(C)}")
def spot(sym):
 fs=[];scanned=0;usable=[]
 candidates=list(DL.rglob(f"*{sym}*.parquet"))
 print(f"[GEF62] spot discovery {sym}: candidates={len(candidates)}",flush=True)
 for q in candidates:
  scanned+=1
  try:
   d=pd.read_parquet(q)
   dc2=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
   pc=next((c for c in d.columns if str(c).lower() in ["close","bidclose","price"]),None)
   if dc2 is None and isinstance(d.index,pd.DatetimeIndex):
    d=d.reset_index();dc2=d.columns[0]
   if dc2 is None or pc is None:continue
   dt=pd.to_datetime(d[dc2],errors="coerce")
   if dt.notna().sum()==0:continue
   if int(dt.dt.year.min())>=2026:continue
   x=pd.DataFrame({"dt":dt,"px":pd.to_numeric(d[pc],errors="coerce")}).dropna()
   x=x[(x.dt.dt.year>=2023)&(x.dt.dt.year<=2025)]
   if len(x):
    fs.append(x);usable.append(str(q))
  except Exception:
   continue
 if not fs:
  raise RuntimeError(f"No 2023-2025 spot parquet for {sym}; scanned={scanned}; candidates={candidates[:20]}")
 print(f"[GEF62] spot {sym}: usable_files={len(usable)} rows={sum(len(x) for x in fs)}",flush=True)
 x=pd.concat(fs).sort_values("dt").drop_duplicates("dt")
 return x.set_index("dt").px.resample("1D").last().dropna()

out=[]
for i,r in F.iterrows():
 H=C[C[mc]==r.cftc_market].sort_values("AVAILABLE_AT").copy();base=r.feature;H["pct"]=H[base].rolling(156,min_periods=52).rank(pct=True);H=H[(H.AVAILABLE_AT.dt.year>=2023)&(H.AVAILABLE_AT.dt.year<=2025)]
 s=spot(r.market);d=pd.DataFrame({"px":s}).reset_index();d.columns=["dt","px"];d=pd.merge_asof(d.sort_values("dt"),H[["AVAILABLE_AT","pct"]],left_on="dt",right_on="AVAILABLE_AT",direction="backward");h=int(r.h);d["ret"]=d.px.shift(-h)/d.px-1
 mask=d.pct>=float(r.q) if r.tail=="hi" else d.pct<=float(r.q);x=(d.loc[mask,"ret"]*int(r.trade_side)).dropna();dates=d.loc[x.index,"dt"];tmp=pd.DataFrame({"x":x.values,"dt":dates.values})
 yrs=tmp.assign(year=pd.to_datetime(tmp.dt).dt.year).groupby("year").x.mean();sx=x.sort_values(ascending=False);trim=sx.iloc[int(np.ceil(len(sx)*.01)):] if len(sx) else sx;day=tmp.groupby("dt").x.sum().sort_values(ascending=False);rm=tmp[~tmp.dt.isin(day.head(3).index)].x
 keep=[];last=None
 for _,z in tmp.sort_values("dt").iterrows():
  zdt=pd.Timestamp(z["dt"]);zx=float(z["x"])
  if last is None or zdt>=last+pd.Timedelta(days=h):keep.append(zx);last=zdt
 non=pd.Series(keep,dtype=float)
 vals={"n":len(x),"gross_bp":x.mean()*10000 if len(x) else np.nan,"hit":(x>0).mean() if len(x) else np.nan,"positive_year_fraction":(yrs>0).mean() if len(yrs) else 0,"trim1_bp":trim.mean()*10000 if len(trim) else np.nan,"remove_best3days_bp":rm.mean()*10000 if len(rm) else np.nan,"true_nonoverlap_bp":non.mean()*10000 if len(non) else np.nan,"nonoverlap_n":len(non)}
 q=gate["requirements"];passed=bool(vals["n"]>=q["n_min"] and vals["gross_bp"]>0 and vals["hit"]>=q["hit_rate_min"] and vals["positive_year_fraction"]>=q["positive_year_fraction_min"] and vals["trim1_bp"]>0 and vals["remove_best3days_bp"]>0 and vals["true_nonoverlap_bp"]>0)
 out.append({"key":r.key,"market":r.market,**vals,"OOS_PASS":passed});prog(4+i,8,f"{r.market} OOS n={len(x)} gross={vals['gross_bp']:.2f}bp pass={passed}")
R=pd.DataFrame(out);R.to_csv(O/"LOCKED_OOS_RESULTS.csv",index=False)
receipt={"run_id":rid,"status":"COMPLETE_LOCKED_OOS_2023_2025","eligible_sha256":EXPECTED,"oos_gate_sha256":gsha,"tested":len(R),"passed":int(R.OOS_PASS.sum()),"protected_2026_accessed":False,"retuning":False,"post_oos_action":"STOP_FOR_INTERPRETATION_AND_EXECUTION_DESIGN"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(7,8,f"OOS complete passed={receipt['passed']}/{len(R)}");prog(8,8,"HARD STOP; 2026 UNTOUCHED")
print()
print("=== V62 RECEIPT ===")
print(json.dumps(receipt,indent=2))
print()
print("=== LOCKED OOS RESULTS ===")
print(R.to_string(index=False))
print()
print("RUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V62 compile failed"}
Write-Host "=== GEF V62 - LOCKED OOS 2023-2025 ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V62 failed"}
