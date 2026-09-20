param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v10.py"
$code=@'
from pathlib import Path
import pandas as pd, numpy as np, json, time, hashlib
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests"); B=ROOT/"Research"/"Autonomous"; V3B=B/"guardian_edge_factory_v3"; CACHE=V3B/"cache5"; OUTB=B/"guardian_edge_factory_v10";OUTB.mkdir(parents=True,exist_ok=True)
D0=pd.Timestamp("2010-01-01");D1=pd.Timestamp("2013-12-31 23:59:59");H=60;P=.90;t0=time.time()
def st(o,s,i,n,m=""):
 e=time.time()-t0;eta=e/i*(n-i) if i else 0; print(f"[GEF10] {s:<14} {i}/{n} {100*i/n:6.2f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {m}",flush=True)
 (o/"STATUS.json").write_text(json.dumps({"stage":s,"done":i,"total":n,"pct":100*i/n,"elapsed_s":e,"eta_s":eta,"message":m},indent=2))
v=[]
for q in V3B.glob("GEF3-*"):
 r=q/"RUN_RECEIPT.json"
 if r.exists():
  j=json.loads(r.read_text())
  if j.get("status")=="COMPLETE" and not j.get("locked_oos_2023_2025_accessed") and not j.get("protected_2026_accessed"):v.append((q.stat().st_mtime,q))
V3=sorted(v)[-1][1];rid="GEF10-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S");OUT=OUTB/rid;OUT.mkdir()
annual=pd.read_csv(V3/"AUTOPSY_local_annual_stability.csv"); z=pd.read_parquet(CACHE/"GBPUSD_2010_2022.parquet").sort_index();z.index=pd.to_datetime(z.index);dm=(z.index>=D0)&(z.index<=D1)
def back(c,m):q=c.copy();q.index=q.index+pd.Timedelta(minutes=m);return q.reindex(c.index)
def fwd(c,m):q=c.copy();q.index=q.index-pd.Timedelta(minutes=m);return q.reindex(c.index)
def feat(name):
 c=z.close;k=int(name.split("_")[-1]);mp=max(3,k//20)
 if name.startswith("ret_"):return np.log(c/back(c,k))
 if name.startswith("z_"):
  a=c.rolling(f"{k}min",min_periods=mp);return (c-a.mean())/a.std().replace(0,np.nan)
 if name.startswith("rangepos_"):
  a=c.rolling(f"{k}min",min_periods=mp);lo=a.min();hi=a.max();return (c-lo)/(hi-lo).replace(0,np.nan)
def ecdf(x):
 a=np.sort(x[dm].dropna());v=x.to_numpy(float);o=np.full(len(v),np.nan);ok=np.isfinite(v);o[ok]=np.searchsorted(a,v[ok],side="right")/len(a)-.5;return pd.Series(o,index=x.index)
y=np.log(fwd(z.close,H)/z.close); comps={}
for _,r in annual[annual.symbol=="GBPUSD"].head(3).iterrows():
 x=feat(r.feature);sg=1 if x[dm].corr(y[dm],method="spearman")>0 else -1;comps[str(r.feature)]=sg*ecdf(x)
score=pd.concat(comps,axis=1).mean(axis=1);thr=float(score[dm].abs().quantile(P))
def trades(delay=0):
 s=score[score.abs()>=thr].dropna();et=s.index+pd.Timedelta(minutes=delay);p0=z.close.reindex(et);p1=z.close.reindex(et+pd.Timedelta(minutes=H));a=[];nxt=pd.Timestamp.min
 for t,sg,x0,x1 in zip(et,s.to_numpy(),p0.to_numpy(),p1.to_numpy()):
  if t<nxt or not np.isfinite(sg*x0*x1) or x0<=0 or x1<=0:continue
  a.append((t,np.sign(sg)*np.log(x1/x0)*10000,np.sign(sg),x0,x1));nxt=t+pd.Timedelta(minutes=H)
 return pd.DataFrame(a,columns=["time","gross_bp","side","entry","exit"])
st(OUT,"BUILD",1,1,f"components={list(comps)} threshold={thr:.6f}")
T=trades(0);T15=trades(15)
# data quality around top winners: minute availability, jumps, neighboring returns
audit=[]
tops=T.nlargest(100,"gross_bp")
for i,(_,r) in enumerate(tops.iterrows(),1):
 t=r.time;win=z.close.loc[(z.index>=t-pd.Timedelta(minutes=5))&(z.index<=t+pd.Timedelta(minutes=65))]
 dif=win.index.to_series().diff().dt.total_seconds().div(60)
 rr=np.log(win/win.shift(1))*10000
 audit.append({"time":t,"gross_bp":r.gross_bp,"side":r.side,"entry":r.entry,"exit":r.exit,"points_window":len(win),"max_gap_min":dif.max(),"max_abs_1m_bp":rr.abs().max(),"entry_hour":t.hour,"year":t.year})
 if i%10==0:st(OUT,"WINNER AUDIT",i,100,str(t))
A=pd.DataFrame(audit);A.to_csv(OUT/"top100_data_quality.csv",index=False)
# hour/session/year and cost surfaces. Costs are scenarios, not claims about broker.
diag=[]
for delay,tr in [(0,T),(15,T15)]:
 tr=tr.copy();tr["year"]=tr.time.dt.year;tr["hour"]=tr.time.dt.hour
 for kind,key,g in [("ALL","all",tr)]+[("YEAR",str(k),g) for k,g in tr.groupby("year")]+[("HOUR",str(k),g) for k,g in tr.groupby("hour")]:
  diag.append({"delay":delay,"kind":kind,"key":key,"n":len(g),"gross_bp":g.gross_bp.mean(),"hit":(g.gross_bp>0).mean(),"side_long_fraction":(g.side>0).mean()})
pd.DataFrame(diag).to_csv(OUT/"diagnostics.csv",index=False)
costs=[]
for delay,tr in [(0,T),(15,T15)]:
 for c in [0,.05,.10,.15,.20,.25,.30,.35,.40,.50,.75,1.0]:
  net=tr.gross_bp-c;ym=pd.DataFrame({"year":tr.time.dt.year,"net":net}).groupby("year").net.mean()
  costs.append({"delay":delay,"allin_cost_bp":c,"net_bp_trade":net.mean(),"positive_year_fraction":(ym>0).mean(),"annual_net_bp":net.sum()/13})
C=pd.DataFrame(costs);C.to_csv(OUT/"cost_surface_scenarios.csv",index=False)
# Freeze candidate definition, not OOS outcome. Include source hashes.
src=str(V3/"AUTOPSY_local_annual_stability.csv");hsh=hashlib.sha256(Path(src).read_bytes()).hexdigest()
rule={"rule_id":"GBP60_LOCAL_P90_PREOOS_V1","status":"FROZEN_PENDING_HUMAN_OOS_APPROVAL","market":"GBPUSD","direction_at_selected_tail":"SHORT_ONLY_OBSERVED_PREOOS","horizon_minutes":60,
"components":list(comps),"component_construction":"top 3 V3 GBPUSD local annual-stability rows; each signed by Discovery-only Spearman; Discovery-only ECDF; equal-weight mean",
"threshold_rule":"abs(composite) >= Discovery 2010-2013 90th percentile","threshold_value":thr,"entry_delay_primary_minutes":0,"delay_stress_minutes":15,
"discovery":"2010-2013","replication":"2014-2017","validation":"2018-2022","locked_oos":"2023-2025","protected":"2026",
"selection_rationale":"P90 lies inside broad P80-P95 plateau and was chosen before locked OOS; not the ex-post maximum.","source_v3":V3.name,"annual_file_sha256":hsh,
"mutation_policy":"No feature, sign, threshold, horizon, direction, delay or filter may be changed after OOS is opened. Any change creates a new research lineage and cannot reuse the same OOS as clean confirmation."}
(OUT/"FROZEN_RULE.json").write_text(json.dumps(rule,indent=2))
receipt={"run_id":rid,"status":"COMPLETE","research_max":"2022-12-31","locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,"errors":[],"rule_frozen":rule["rule_id"],
"note":"All-in cost grid is hypothetical stress, not broker-specific historical cost data. Top-winner audit checks source continuity/jumps but does not prove historical fillability.",
"next_gate":"Human review of data-quality audit and cost budget. If accepted, explicit human approval is required before opening locked OOS 2023-2025."}
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));st(OUT,"COMPLETE",1,1,"candidate frozen; OOS untouched")
print("\n=== V10 FROZEN RULE ===");print(json.dumps(rule,indent=2))
print("\n=== V10 TOP-WINNER DATA QUALITY ===");print(A[["time","gross_bp","points_window","max_gap_min","max_abs_1m_bp"]].head(25).to_string(index=False))
print("\n=== V10 COST SURFACE ===");print(C.to_string(index=False))
print("\n=== V10 ALL/YEAR DIAGNOSTICS ===");print(pd.DataFrame(diag)[pd.DataFrame(diag).kind.isin(["ALL","YEAR"])].to_string(index=False))
print("\n=== V10 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\nRUN:",OUT)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V10 compile failed"}
Write-Host "=== GUARDIAN EDGE FACTORY V10 — FINAL PRE-OOS AUDIT ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V10 run failed"}
