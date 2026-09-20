param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v28_component_attribution.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests");RAW=ROOT/"DataLake"/"raw"/"histdata";OUT=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v28";OUT.mkdir(parents=True,exist_ok=True)
THR=.008340;H=240;DIR=-1;started=time.time();rid="GEF28-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");O=OUT/rid;O.mkdir()
def prog(i,n,msg):
 e=time.time()-started;eta=e/i*(n-i) if i else 0;print(f"[GEF28] {i}/{n} {100*i/n:.1f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {msg}",flush=True)
def load(m):
 z=[]
 for y in range(2010,2023):
  p=RAW/m/"M1"/f"{m}_M1_{y}.parquet"
  if p.exists():
   d=pd.read_parquet(p);tc=next(c for c in d if c.lower() in ("datetime","time","timestamp"));d.index=pd.to_datetime(d[tc]);z.append(d[["close"]].sort_index().resample("5min",label="right",closed="left").last().dropna())
 return pd.concat(z).sort_index()
prog(1,7,"load 2010-2022 only");A=load("XAGUSD");B=load("XAUUSD");idx=A.index.intersection(B.index);a=A.close.reindex(idx);b=B.close.reindex(idx)
ra=np.log(a/a.shift(6));rb=np.log(b/b.shift(6));div=ra-rb
def target(sig):
 en=a.reindex(sig.index);ex=a.reindex(sig.index+pd.Timedelta(minutes=H));en.index=sig.index;ex.index=sig.index;return (sig*np.log(ex/en)*1e4).dropna()
def stats(name,sig):
 p=target(sig);yrs=p.groupby(p.index.year).mean();return {"test":name,"n":len(p),"gross_bp":float(p.mean()),"hit":float((p>0).mean()),"posyears":float((yrs>0).mean())}
# Baseline exact frozen rule
base_sel=div[div.abs()>=THR];base_sig=DIR*np.sign(base_sel)
rows=[stats("FROZEN_DIVERGENCE",base_sig)]
prog(2,7,"component attribution at identical event timestamps")
# On the SAME frozen event timestamps: ask whether direction is really supplied by XAG past, XAU past, or divergence.
ev=base_sel.index
rows+= [stats("SAME_EVENTS_XAG_MEANREV",-np.sign(ra.reindex(ev)).dropna()),
        stats("SAME_EVENTS_XAU_MEANREV",-np.sign(rb.reindex(ev)).dropna()),
        stats("SAME_EVENTS_XAG_MOMENTUM",np.sign(ra.reindex(ev)).dropna()),
        stats("SAME_EVENTS_XAU_MOMENTUM",np.sign(rb.reindex(ev)).dropna())]
prog(3,7,"standalone component tails with frozen event count")
# No threshold tuning: choose top-N absolute observations where N equals baseline count, separately per component, diagnostic only.
N=len(base_sel)
for name,x in [("XAG",ra),("XAU",rb)]:
 q=x.dropna();sel=q.loc[q.abs().nlargest(min(N,len(q))).index].sort_index()
 rows.append(stats(f"STANDALONE_{name}_TOPN_MEANREV",-np.sign(sel)))
 rows.append(stats(f"STANDALONE_{name}_TOPN_MOMENTUM",np.sign(sel)))
prog(4,7,"conditional sign quadrants")
quad=[]
tmp=pd.DataFrame({"ra":ra,"rb":rb,"div":div}).reindex(ev).dropna()
for qa,qb in [(1,1),(1,-1),(-1,1),(-1,-1)]:
 z=tmp[(np.sign(tmp.ra)==qa)&(np.sign(tmp.rb)==qb)]
 sig=DIR*np.sign(z["div"]);s=stats(f"XAG{qa:+d}_XAU{qb:+d}",sig);quad.append(s)
pd.DataFrame(quad).to_csv(O/"SIGN_QUADRANTS.csv",index=False)
prog(5,7,"strict past-XAU incremental controls")
# Compare frozen divergence to variants using only stale XAU. No future data.
stale=[]
for bars in [1,2,3,6,12]:
 bs=b.shift(bars);rbs=np.log(bs/bs.shift(6));ds=ra-rbs;sel=ds[ds.abs()>=THR];stale.append(stats(f"DIVERGENCE_XAU_STALE_{bars*5}m",DIR*np.sign(sel)))
pd.DataFrame(stale).to_csv(O/"STALE_XAU_CONTROLS.csv",index=False)
prog(6,7,"write attribution diagnostics")
R=pd.DataFrame(rows);R.to_csv(O/"COMPONENT_ATTRIBUTION.csv",index=False)
base=float(R.loc[R.test=="FROZEN_DIVERGENCE","gross_bp"].iloc[0]);xag=float(R.loc[R.test=="SAME_EVENTS_XAG_MEANREV","gross_bp"].iloc[0]);xau=float(R.loc[R.test=="SAME_EVENTS_XAU_MEANREV","gross_bp"].iloc[0])
# Diagnostic criterion: divergence should materially outperform both same-event single-market directions.
incremental=bool(base>0 and base>xag+1 and base>xau+1)
summary={"candidate":"XAGUSD<-XAUUSD divret_6b H240 P99 direction -1","period":"2010-2022 only","baseline_bp":base,"same_event_xag_meanrev_bp":xag,"same_event_xau_meanrev_bp":xau,"incremental_divergence_pass":incremental,"note":"Standalone TOP-N component tests are diagnostics only and do not redefine the frozen candidate. No future-driver information used.","locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False}
(O/"ATTRIBUTION_SUMMARY.json").write_text(json.dumps(summary,indent=2));receipt={"run_id":rid,"status":"COMPLETE","data_period":"2010-2022 only","locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"incremental_divergence_pass":incremental,"instruction":"STOP FOR HUMAN REVIEW. No automatic OOS access.","errors":[]};(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(7,7,"STOP - OOS untouched");print("\n=== V28 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== ATTRIBUTION SUMMARY ===");print(json.dumps(summary,indent=2));print("\n=== COMPONENTS ===");print(R.to_string(index=False));print("\n=== QUADRANTS ===");print(pd.DataFrame(quad).to_string(index=False));print("\n=== STALE XAU ===");print(pd.DataFrame(stale).to_string(index=False));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V28 compile failed"}
Write-Host "=== GEF V28 - XAU/XAG COMPONENT ATTRIBUTION ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V28 failed"}
