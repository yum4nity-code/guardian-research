param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Base=Join-Path $Root "Research\Autonomous\guardian_edge_factory_v3"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v3_autopsy.py"

$code=@'
from pathlib import Path
import pandas as pd, numpy as np, json
from datetime import datetime, timezone

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v3"

runs=[]
for p in BASE.glob("GEF3-*"):
    r=p/"RUN_RECEIPT.json"
    if r.exists():
        try:
            j=json.loads(r.read_text())
            if j.get("status")=="COMPLETE" and not j.get("locked_oos_2023_2025_accessed") and not j.get("protected_2026_accessed"):
                runs.append((p.stat().st_mtime,p,j))
        except: pass
if not runs: raise SystemExit("No eligible COMPLETE V3 run")
_,RUN,REC=sorted(runs)[-1]

print(f"[AUTOPSY] run={RUN.name}",flush=True)
cross=pd.read_csv(RUN/"cross_market_replication_table.csv")
null=pd.read_csv(RUN/"cross_market_block_null.csv")
annual=pd.read_csv(RUN/"year_stability_summary.csv")

for c in ["ic_D","ic_R","ic_V","min_abs_ic","lag","h"]:
    if c in cross: cross[c]=pd.to_numeric(cross[c],errors="coerce")
null["abs_ic"]=pd.to_numeric(null.abs_ic,errors="coerce")
for c in ["median_ic","sign_consistency","worst_abs_ic","h"]:
    if c in annual: annual[c]=pd.to_numeric(annual[c],errors="coerce")

# Null thresholds. Controls were generated on top Discovery cross-market definitions.
nv=null.abs_ic.dropna()
nullstats={"n":len(nv),"mean":nv.mean(),"p95":nv.quantile(.95),"p99":nv.quantile(.99),"max":nv.max()}

# Conservative real signal metrics: weakest of D/R/V and shrinkage V/D.
same=cross[cross.same_sign_DRV.astype(str).str.lower()=="true"].copy()
same["shrink_V_vs_D"]=same.ic_V.abs()/same.ic_D.abs().replace(0,np.nan)
same["null_exceed_p"]=[(1+(nv>=abs(v)).sum())/(1+len(nv)) for v in same.min_abs_ic]
same["beats_null_max"]=same.min_abs_ic>nullstats["max"]

# semantic clustering: target/explainer/direction; neighboring lag/h are aliases, not separate edges
same["direction"]=np.sign(same.ic_D).astype(int)
clusters=(same.groupby(["target","explain","direction"])
 .agg(cells=("min_abs_ic","size"),best_min_abs_ic=("min_abs_ic","max"),
      median_min_abs_ic=("min_abs_ic","median"),best_null_p=("null_exceed_p","min"),
      median_shrink=("shrink_V_vs_D","median"),
      lags=("lag",lambda x:";".join(map(str,sorted(set(x.dropna().astype(int)))))),
      horizons=("h",lambda x:";".join(map(str,sorted(set(x.dropna().astype(int)))))))
 .reset_index().sort_values("best_min_abs_ic",ascending=False))

# representatives = best weakest-era IC per cluster
idx=same.groupby(["target","explain","direction"]).min_abs_ic.idxmax()
reps=same.loc[idx].sort_values("min_abs_ic",ascending=False).copy()

# Annual local stability.
if len(annual):
    annual["strong_annual_stability"]=(annual.sign_consistency>=0.75)&(annual.worst_abs_ic>0)
    annual=annual.sort_values(["sign_consistency","worst_abs_ic"],ascending=False)

# concentration diagnostics
conc_target=same.groupby("target").agg(cells=("min_abs_ic","size"),median_min_ic=("min_abs_ic","median"),best=("min_abs_ic","max")).sort_values("best",ascending=False)
conc_explain=same.groupby("explain").agg(cells=("min_abs_ic","size"),median_min_ic=("min_abs_ic","median"),best=("min_abs_ic","max")).sort_values("best",ascending=False)
conc_lag=same.groupby("lag").agg(cells=("min_abs_ic","size"),median_min_ic=("min_abs_ic","median"),best=("min_abs_ic","max")).sort_index()
conc_h=same.groupby("h").agg(cells=("min_abs_ic","size"),median_min_ic=("min_abs_ic","median"),best=("min_abs_ic","max")).sort_index()

same.sort_values("min_abs_ic",ascending=False).to_csv(RUN/"AUTOPSY_same_sign_cells.csv",index=False)
clusters.to_csv(RUN/"AUTOPSY_cross_market_clusters.csv",index=False)
reps.to_csv(RUN/"AUTOPSY_cross_market_representatives.csv",index=False)
annual.to_csv(RUN/"AUTOPSY_local_annual_stability.csv",index=False)
conc_target.to_csv(RUN/"AUTOPSY_concentration_target.csv")
conc_explain.to_csv(RUN/"AUTOPSY_concentration_explainer.csv")
conc_lag.to_csv(RUN/"AUTOPSY_concentration_lag.csv")
conc_h.to_csv(RUN/"AUTOPSY_concentration_horizon.csv")

top=reps.head(20)
summary={
 "run":RUN.name,
 "generated_utc":datetime.now(timezone.utc).isoformat(),
 "locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,
 "same_sign_cells":int(len(same)),
 "distinct_target_explainer_direction_clusters":int(len(clusters)),
 "representatives_beating_null_max":int(reps.beats_null_max.sum()),
 "null":{k:(int(v) if k=="n" else float(v)) for k,v in nullstats.items()},
 "local_annual_rows":int(len(annual)),
 "local_strong_annual_stability":int(annual.strong_annual_stability.sum()) if len(annual) else 0,
 "top_representatives":top[["target","explain","lag","h","ic_D","ic_R","ic_V","min_abs_ic","null_exceed_p","shrink_V_vs_D"]].to_dict("records"),
 "interpretation_rule":"Descriptive PRE-OOS autopsy only; no OOS promotion or tradability claim."
}
(RUN/"AUTOPSY_SUMMARY.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")

print("\n=== V3 AUTOPSY SUMMARY ===")
print(json.dumps(summary,indent=2))
print("\n=== TOP DISTINCT CROSS-MARKET PHENOMENA ===")
print(top[["target","explain","lag","h","ic_D","ic_R","ic_V","min_abs_ic","null_exceed_p"]].to_string(index=False))
print("\n=== CONCENTRATION BY TARGET ===")
print(conc_target.to_string())
print("\n=== CONCENTRATION BY EXPLAINER ===")
print(conc_explain.to_string())
print("\n=== LOCAL ANNUAL STABILITY TOP 20 ===")
print(annual.head(20).to_string(index=False))
'@

Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "Autopsy compile failed"}
Write-Host "=== V3 AUTOPSY ==="
py $Py
if($LASTEXITCODE -ne 0){throw "Autopsy failed"}
