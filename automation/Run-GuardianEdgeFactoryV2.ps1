param(
  [string]$Root = "D:\MT5_Backtests"
)
$ErrorActionPreference = "Stop"
$Base = Join-Path $Root "Research\Autonomous\guardian_edge_factory_v1"
$Runs = Join-Path $Base "runs"
$Tools = Join-Path $Root "DataLake\tools"
$Py = Join-Path $Tools "guardian_edge_factory_v2.py"

if (!(Test-Path $Runs)) { throw "V1 runs directory missing: $Runs" }

$pycode = @'
from pathlib import Path
import pandas as pd, numpy as np, json, time, hashlib, sys, math
from datetime import datetime, timezone

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v1"
RUNS=BASE/"runs"
OUTBASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v2"
OUTBASE.mkdir(parents=True,exist_ok=True)

# Never enumerate research datasets globally. V2 reads only a completed PRE-2023 V1 run.
cands=[]
for p in RUNS.glob("GEF1-*"):
    rec=p/"RUN_RECEIPT.json"
    if rec.exists():
        try:
            j=json.loads(rec.read_text(encoding="utf-8"))
            if j.get("status")=="COMPLETE" and j.get("research_max")=="2022-12-31" and not j.get("locked_oos_2023_2025_accessed") and not j.get("protected_2026_accessed"):
                cands.append((p.stat().st_mtime,p,j))
        except Exception: pass
if not cands: raise SystemExit("No eligible COMPLETE V1 run")
_,V1,V1REC=sorted(cands)[-1]

run_id="GEF2-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
OUT=OUTBASE/run_id; OUT.mkdir(parents=True)
t0=time.time(); ledger=[]; errors=[]

def progress(stage,i,n,extra=""):
    elapsed=time.time()-t0
    pct=100*i/max(n,1)
    eta=(elapsed/i*(n-i)) if i else float("nan")
    es=f"{int(elapsed//3600):02d}:{int(elapsed%3600//60):02d}:{int(elapsed%60):02d}"
    et="--:--:--" if not np.isfinite(eta) else f"{int(eta//3600):02d}:{int(eta%3600//60):02d}:{int(eta%60):02d}"
    print(f"[GEF2] {stage:<24} {i:>5}/{n:<5} {pct:6.2f}% | elapsed {es} | ETA {et} | {extra}",flush=True)

def bh_fdr(p):
    p=np.asarray(p,float); n=len(p)
    order=np.argsort(p); ranked=p[order]
    q=ranked*n/np.arange(1,n+1)
    q=np.minimum.accumulate(q[::-1])[::-1]
    out=np.empty(n); out[order]=np.minimum(q,1.0)
    return out

def fisher_z_p(r,n):
    # Large-sample two-sided normal approximation for Spearman screening.
    r=np.clip(np.asarray(r,float),-0.999999,0.999999)
    n=np.asarray(n,float)
    z=np.arctanh(r)*np.sqrt(np.maximum(n-3,1))
    # erfc unavailable vectorized in stdlib: normal survival approximation
    x=np.abs(z)
    # Abramowitz-Stegun normal CDF approximation
    t=1/(1+0.2316419*x)
    poly=t*(0.319381530+t*(-0.356563782+t*(1.781477937+t*(-1.821255978+t*1.330274429))))
    sf=(1/np.sqrt(2*np.pi))*np.exp(-0.5*x*x)*poly
    return np.minimum(1.0,2*sf)

progress("LOAD V1",0,1,str(V1))
trials=pd.read_parquet(V1/"all_univariate_trials.parquet")
surv=pd.read_csv(V1/"microedge_screen_survivors.csv")
null=pd.read_csv(V1/"negative_controls.csv")
progress("LOAD V1",1,1,f"{len(trials)} rows; {len(surv)} survivors; {len(null)} nulls")

# 1) Repair/audit negative controls
required={"symbol","feature","control","n","abs_ic"}
missing=required-set(null.columns)
if missing: raise SystemExit(f"negative_controls schema missing: {sorted(missing)}")
null["abs_ic"]=pd.to_numeric(null["abs_ic"],errors="coerce")
null_clean=null.dropna(subset=["abs_ic"])
null_summary={
 "n":int(len(null_clean)),
 "mean_abs_ic":float(null_clean.abs_ic.mean()),
 "median_abs_ic":float(null_clean.abs_ic.median()),
 "p95_abs_ic":float(null_clean.abs_ic.quantile(.95)),
 "p99_abs_ic":float(null_clean.abs_ic.quantile(.99)),
 "max_abs_ic":float(null_clean.abs_ic.max())
}
(OUT/"negative_control_summary.json").write_text(json.dumps(null_summary,indent=2),encoding="utf-8")
progress("NULL AUDIT",1,1,json.dumps(null_summary))

# 2) Multiplicity audit over all V1 real trials
x=trials.copy()
for c in ["ic","effect","n"]: x[c]=pd.to_numeric(x[c],errors="coerce")
x=x.dropna(subset=["ic","n"])
x["p_approx"]=fisher_z_p(x.ic.values,x.n.values)
# FDR separately by split + target horizon to avoid mixing unlike families.
x["q_bh"]=np.nan
groups=list(x.groupby(["split","h"],sort=False))
for gi,((sp,h),idx) in enumerate(groups,1):
    x.loc[idx.index,"q_bh"]=bh_fdr(idx.p_approx.values)
    progress("FDR",gi,len(groups),f"{sp} h={h}")
x.to_parquet(OUT/"v1_trials_with_fdr.parquet",index=False)

# 3) Collapse aliases into phenomenon families. This is deliberately conservative.
def family(f):
    f=str(f)
    if f.startswith("z_"): return "location_z"
    if f.startswith("ret_"): return "momentum_return"
    if f.startswith("rv_"): return "realized_vol"
    if f.startswith("rangepos_"): return "range_position"
    return f.split("_")[0]
surv["family"]=surv.feature.map(family)
for c in ["ic_D","ic_R","ic_V","min_abs_ic","h"]: 
    if c in surv: surv[c]=pd.to_numeric(surv[c],errors="coerce")
surv["phenomenon_key"]=surv["symbol"].astype(str)+"|"+surv["family"].astype(str)+"|h"+surv["h"].astype("Int64").astype(str)

# Empirical null exceedance: compare min_abs_ic to global control abs IC.
nullvals=np.sort(null_clean.abs_ic.to_numpy())
def null_tail(v):
    if len(nullvals)==0 or pd.isna(v): return np.nan
    return float((1 + np.sum(nullvals>=abs(v)))/(1+len(nullvals)))
surv["null_empirical_p"]=surv.min_abs_ic.map(null_tail)
surv["null_q_bh"]=bh_fdr(surv.null_empirical_p.fillna(1).values)

# One representative per correlated semantic family/symbol/horizon.
rep=(surv.sort_values(["min_abs_ic"],ascending=False)
          .drop_duplicates(["symbol","family","h"])
          .copy())
rep["robust_pre_oos_screen"]=(rep["same_sign_DRV"].astype(str).str.lower()=="true") & (rep["null_q_bh"]<=0.05)
rep.to_csv(OUT/"phenomenon_representatives.csv",index=False)
surv.to_csv(OUT/"survivors_audited.csv",index=False)
progress("ALIAS COLLAPSE",len(rep),len(rep),f"{rep.robust_pre_oos_screen.sum()} pass empirical-null/FDR screen")

# 4) Produce a bounded shortlist; this is NOT an OOS promotion.
short=rep[rep.robust_pre_oos_screen].sort_values(["min_abs_ic"],ascending=False).head(100)
short.to_csv(OUT/"PRE_OOS_SHORTLIST_NOT_PROMOTED.csv",index=False)

# 5) Dependency map showing how many V1 cells each representative family subsumes.
dep=(surv.groupby(["symbol","family","h"],dropna=False)
       .agg(alias_cells=("feature","size"),best_min_abs_ic=("min_abs_ic","max"),
            features=("feature",lambda s:";".join(sorted(set(map(str,s))))))
       .reset_index())
dep.to_csv(OUT/"dependency_clusters.csv",index=False)

# 6) Trial ledger includes V1 inherited trials + V2 decisions.
for _,r in rep.iterrows():
    ledger.append({"stage":"V2_ALIAS_NULL_FDR","symbol":r.symbol,"family":r.family,"h":int(r.h),
                   "decision":"SCREEN_PASS" if bool(r.robust_pre_oos_screen) else "SCREEN_REJECT",
                   "null_empirical_p":float(r.null_empirical_p),"null_q_bh":float(r.null_q_bh),
                   "min_abs_ic":float(r.min_abs_ic)})
pd.DataFrame(ledger).to_csv(OUT/"V2_TRIAL_LEDGER.csv",index=False)

receipt={
 "run_id":run_id,"status":"COMPLETE","source_v1_run":V1.name,
 "created_utc":datetime.now(timezone.utc).isoformat(),
 "research_max":"2022-12-31",
 "locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,
 "v1_trial_count":int(V1REC.get("trial_count",0)),
 "v2_decision_count":len(ledger),
 "negative_control_summary":null_summary,
 "survivor_cells_input":int(len(surv)),
 "phenomenon_representatives":int(len(rep)),
 "pre_oos_shortlist_count":int(len(short)),
 "errors":errors,
 "scientific_warning":"V2 shortlist is a PRE-OOS screening artifact, not proof of tradable edge and not authorization to open locked OOS.",
 "next_gate":"Year-by-year stability, cost/delay stress, bootstrap/block-null, then cross-market incremental-information factory. 2023-2025 remains locked."
}
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
progress("COMPLETE",1,1,f"shortlist={len(short)}")
print("\n=== GEF V2 RECEIPT ===",flush=True)
print(json.dumps(receipt,indent=2),flush=True)
print("RUN:",OUT,flush=True)
'@

Set-Content -Path $Py -Value $pycode -Encoding UTF8
py -m py_compile $Py
if ($LASTEXITCODE -ne 0) { throw "V2 Python compile failed" }

Write-Host "=== GUARDIAN EDGE FACTORY V2 ==="
Write-Host "Python:" $Py
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if ($LASTEXITCODE -ne 0) { throw "V2 run failed" }
