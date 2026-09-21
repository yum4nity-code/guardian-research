param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\gef_v81_cross_source_concordance.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,re,time,hashlib,math
ROOT=Path(r"D:\MT5_Backtests")
V80C=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v80c").glob("GEF80C-*"))[-1]
V79=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v79").glob("GEF79-*"))[-1]
X=pd.read_parquet(V80C/"CAUSAL_STATE_MATRIX_2010_2013_FULL.parquet")
Y=pd.read_parquet(V79/"FUTURE_TARGETS_2010_2013.parquet")
X.index=pd.to_datetime(X.index);Y=Y.reindex(X.index)
rid="GEF81-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");O=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v81"/rid;O.mkdir(parents=True,exist_ok=True);t=time.time()
def prog(i,n,msg,trials=0,surv=0):
 e=time.time()-t;eta=e/i*(n-i) if i else 0;print(f"[GEF81] {i}/{n} {100*i/n:.0f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | trials {trials:,} | provisional {surv:,} | {msg}",flush=True)
def fam(c):
 for p in ["cboe_vol","financial_conditions","fred","alfred","treasury_auctions","cfe"]:
  if c.startswith(p+"_"):return p
 return "price_state"
prog(1,12,f"load {len(X):,} rows x {X.shape[1]:,} features; cross-family concordance discovery only")
# Keep sufficiently covered, varying features. Remove raw px levels from mining; retain derived price states.
cols=[]
for c in X.columns:
 s=pd.to_numeric(X[c],errors="coerce")
 if s.notna().mean()>=.50 and s.nunique(dropna=True)>=10 and not c.endswith("_px"):cols.append(c)
# Limit redundancy by exact vector hash; already mostly deduped.
F=pd.DataFrame({"feature":cols,"family":[fam(c) for c in cols]})
F.to_csv(O/"ELIGIBLE_FEATURES.csv",index=False);prog(2,12,f"eligible features={len(cols)} families={F.family.value_counts().to_dict()}")
# Causal state encodings: expanding historical rank, shifted one row so threshold uses only prior/current history.
states={}
for c in cols:
 s=pd.to_numeric(X[c],errors="coerce")
 # expanding percentile approximation via rolling 1y ranks would be expensive; use expanding z with prior moments.
 mu=s.expanding(min_periods=500).mean().shift(1);sd=s.expanding(min_periods=500).std().shift(1)
 z=(s-mu)/sd.replace(0,np.nan)
 states[c]={"lo":z<=-1.0,"hi":z>=1.0}
prog(3,12,"causal state encodings built: z<=-1 / z>=+1 using prior expanding moments")
# Targets: reduce redundant horizons for discovery compute, still broad across all 13 markets.
targets=[c for c in Y.columns if any(c.endswith(f"_fwd_{h}h") for h in [1,5,15,30,60,120,240])]
# singleton baselines
base={};trials=0
for c in cols:
 for st,m in states[c].items():
  for y in targets:
   yy=pd.to_numeric(Y[y],errors="coerce");q=m & yy.notna()
   n=int(q.sum())
   if n>=100:
    a=yy[q].to_numpy();base[(c,st,y)]={"n":n,"mean":float(np.mean(a)),"hit":float(np.mean(a>0))};trials+=1
prog(4,12,"singleton baselines complete",trials,0)
# Cross-family pair scan. Candidate feature states must each have support; pairs need >=80 hourly observations.
pairs=[];cand=[c for c in cols if any(states[c][s].sum()>=150 for s in ["lo","hi"])]
totalpairs=sum(1 for i,a in enumerate(cand) for b in cand[i+1:] if fam(a)!=fam(b))
done=0;lastpct=-1
for i,a in enumerate(cand):
 for b in cand[i+1:]:
  if fam(a)==fam(b):continue
  done+=1
  for sa in ["lo","hi"]:
   ma=states[a][sa]
   for sb in ["lo","hi"]:
    mask=ma & states[b][sb]
    if mask.sum()<80:continue
    for y in targets:
     yy=pd.to_numeric(Y[y],errors="coerce");q=mask & yy.notna();n=int(q.sum())
     if n<80:continue
     arr=yy[q].to_numpy();mean=float(np.mean(arr));hit=float(np.mean(arr>0));trials+=1
     ba=base.get((a,sa,y));bb=base.get((b,sb,y))
     if not ba or not bb:continue
     # interaction must exceed both singleton absolute means by >=25%, and basic economic screen >=2bp.
     bp=mean*1e4;inc=abs(mean)/max(abs(ba["mean"]),abs(bb["mean"]),1e-12)
     if abs(bp)>=2.0 and inc>=1.25 and max(hit,1-hit)>=.57:
      pairs.append({"a":a,"a_state":sa,"a_family":fam(a),"b":b,"b_state":sb,"b_family":fam(b),"target":y,"n":n,"mean_bp":bp,"hit_long":hit,"direction":1 if mean>0 else -1,"increment_ratio":inc,"a_mean_bp":ba["mean"]*1e4,"b_mean_bp":bb["mean"]*1e4})
  pct=int(done*100/max(totalpairs,1))
  if pct//10>lastpct//10:
   lastpct=pct;prog(5+min(3,pct//25),12,f"pair scan {done:,}/{totalpairs:,}",trials,len(pairs))
P=pd.DataFrame(pairs)
if len(P):P=P.sort_values(["increment_ratio","n"],ascending=[False,False])
P.to_csv(O/"PAIR_SCREEN_SURVIVORS_RAW.csv",index=False)
prog(9,12,f"raw pair screen survivors={len(P):,}",trials,len(P))
# Robust temporal screen by discovery year + non-overlap approximation based target horizon.
rob=[]
for _,r in P.head(5000).iterrows():
 mask=states[r.a][r.a_state] & states[r.b][r.b_state];yy=pd.to_numeric(Y[r.target],errors="coerce")
 direction=int(r.direction);yearstats=[];okyears=0
 for yr in range(2010,2014):
  q=mask & (X.index.year==yr) & yy.notna();a=(yy[q]*direction).to_numpy()
  mbp=float(np.mean(a)*1e4) if len(a) else np.nan
  yearstats.append(mbp)
  if len(a)>=15 and mbp>0:okyears+=1
 if okyears>=3 and np.nanmin(yearstats)>-2:
  z=r.to_dict();z["positive_years"]=okyears;z["year_means_bp"]=json.dumps(yearstats);rob.append(z)
R=pd.DataFrame(rob)
if len(R):R=R.sort_values(["positive_years","increment_ratio","n"],ascending=False)
R.to_csv(O/"PAIR_TEMPORAL_SURVIVORS.csv",index=False);prog(10,12,f"temporal survivors={len(R):,}",trials,len(R))
# Freeze top structurally diverse candidates, max 40, no repeated exact feature pair+target market overload.
frozen=[];seen=set()
for _,r in R.iterrows():
 key=(r.a_family,r.b_family,re.sub(r"_fwd_.*","",r.target))
 if key in seen:continue
 seen.add(key);frozen.append(r.to_dict())
 if len(frozen)>=40:break
pd.DataFrame(frozen).to_csv(O/"FROZEN_PAIR_CANDIDATES.csv",index=False)
ledger={"singleton_trials":sum(len(targets)*2 for _ in cols),"total_evaluated_trials":trials,"cross_family_feature_pairs":totalpairs,"raw_survivors":len(P),"temporal_survivors":len(R),"frozen":len(frozen),"note":"screening only; multiplicity correction/permutation and 2014-17 replication required before any edge claim"}
(O/"TRIAL_LEDGER.json").write_text(json.dumps(ledger,indent=2));prog(11,12,f"frozen diverse candidates={len(frozen)}",trials,len(frozen))
receipt={"run_id":rid,"status":"COMPLETE_CROSS_SOURCE_CONCORDANCE_DISCOVERY","features_tested":len(cols),"targets_tested":len(targets),"trials":trials,"raw_pair_survivors":len(P),"temporal_survivors":len(R),"frozen_candidates":len(frozen),"edge_claim":False,"2014_plus_accessed":False,"2023_plus_accessed":False,"protected_2026_accessed":False,"next":"V82_SELECTION_CORRECTION_AND_FROZEN_REPLICATION_PREP"}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2));prog(12,12,"DONE",trials,len(frozen))
print("\n=== V81 RECEIPT ===");print(json.dumps(receipt,indent=2));print("\n=== TOP FROZEN PAIRS ===");print(pd.DataFrame(frozen).head(20).to_string(index=False) if frozen else "NONE");print("\n=== TRIAL LEDGER ===");print(json.dumps(ledger,indent=2));print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V81 compile failed"}
Write-Host "=== GEF V81 - CROSS-SOURCE CONCORDANCE DISCOVERY ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V81 failed"}
