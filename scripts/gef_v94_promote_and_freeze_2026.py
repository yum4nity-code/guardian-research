from pathlib import Path
import pandas as pd
import numpy as np
import json
import hashlib

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v94"
BASE.mkdir(parents=True,exist_ok=True)

ENGINE_VERSION="V94.0"
GENERIC_COST_BP=1.0

FINAL_2026_PROTOCOL={
    "window":"2026-01-01 through 2026-12-31 only; do not open before full-year data are intentionally released",
    "candidate_set":"all V93 economic_oos_pass hypotheses; no ranking-based cherry-pick",
    "signal_rule":"exact V92 feature states, target horizon and direction unchanged",
    "state_rule":"exact causal expanding z-score lineage already used by V85/V92/V93",
    "generic_cost_bp":1.0,
    "primary_candidate_readout":[
        "signal count",
        "gross mean bp",
        "net mean after hypothetical 1bp",
        "year total return",
        "max drawdown on non-overlapping signal sequence"
    ],
    "primary_survival_rule":[
        "at least 10 valid signals in 2026",
        "gross mean positive",
        "net mean after hypothetical 1bp positive"
    ],
    "statistics":"5-day cluster one-sided p and BH q across the frozen candidate set are diagnostic, not a guillotine",
    "no_retuning":True,
    "no_new_filter":True,
    "no_candidate_replacement":True,
    "no_2026_access_during_v94":True,
}

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def status(out,step,total,msg,**extra):
    payload={
        "engine_version":ENGINE_VERSION,
        "step":step,
        "steps":total,
        "percent":round(100*step/total,1),
        "timestamp_utc":pd.Timestamp.now("UTC").isoformat(),
        "message":msg,
        **extra,
    }
    write_json(out/"LIVE_STATUS.json",payload)
    tail=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(
        f"[GEF94] {step}/{total} {100*step/total:.0f}% | {msg}"
        +(f" | {tail}" if tail else ""),
        flush=True,
    )

# ---------- load latest completed V93 ----------
runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v93").glob("GEF93-*"))
runs=[
    p for p in runs
    if (p/"RUN_RECEIPT.json").exists()
    and (p/"LOCKED_OOS_2023_2025_SCORED.csv").exists()
]
if not runs:
    raise RuntimeError("No completed V93 scored run")
V93=runs[-1]
r93=json.loads((V93/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r93.get("status") not in {
    "COMPLETE_V93_LOCKED_OOS_2023_2025",
    "COMPLETE_PARTIAL_V93_LOCKED_OOS_2023_2025",
}:
    raise RuntimeError(f"Latest V93 status not promotable: {r93.get('status')}")
if not r93.get("2023_2025_strategy_outcomes_accessed"):
    raise RuntimeError("V93 receipt says OOS outcomes were not accessed")
if r93.get("protected_2026_accessed"):
    raise RuntimeError("2026 protection already violated upstream")

V92=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v92"/r93["source_v92"]
r92=json.loads((V92/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
panel_path=V92/"FROZEN_CLEAN_OOS_PANEL.csv"
dev_path=V92/"V92_CLEAN_DEVELOPMENT_ALL.csv"
if not panel_path.exists() or not dev_path.exists():
    raise RuntimeError("Required V92 artifacts missing")
panel=pd.read_csv(panel_path)
dev=pd.read_csv(dev_path)
scored=pd.read_csv(V93/"LOCKED_OOS_2023_2025_SCORED.csv")

RID="GEF94-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID
OUT.mkdir(parents=True,exist_ok=False)
status(
    OUT,1,8,
    "V93/V92 lineage loaded; 2026 remains unopened",
    source_v93=V93.name,
    scored=len(scored),
    unscored=int(r93.get("unscored_data_unavailable",0)),
)

# ---------- exact promotion rule: ALL predeclared V93 economic passes ----------
passes=scored[scored["economic_oos_pass"].astype(bool)].copy()
if passes.empty:
    raise RuntimeError("V93 produced no economic OOS pass; nothing to promote")

# Never use current rank ordering to choose a subset.
pass_ranks=sorted(passes["development_rank"].astype(int).tolist())
promoted=panel[panel["development_rank"].astype(int).isin(pass_ranks)].copy()
if len(promoted)!=len(pass_ranks):
    raise RuntimeError("Promoted V93 pass does not map one-to-one to V92 frozen panel")

promoted=promoted.merge(
    passes[[
        "development_rank","n","mean_bp","net_1bp_mean_bp","median_bp",
        "win_rate_pct","sum_pct","max_drawdown_pct","cluster_p_one",
        "bh_q_panel","positive_net1bp_years","coverage_years_ge3signals",
        "y2023_n","y2023_mean_bp","y2023_net1bp_mean_bp",
        "y2024_n","y2024_mean_bp","y2024_net1bp_mean_bp",
        "y2025_n","y2025_mean_bp","y2025_net1bp_mean_bp",
    ]],
    on="development_rank",
    how="left",
    validate="one_to_one",
    suffixes=("","_v93"),
)

promoted=promoted.merge(
    dev[[
        "development_rank",
        "y2014_n","y2014_mean_bp",
        "y2015_n","y2015_mean_bp",
        "y2016_n","y2016_mean_bp",
        "y2017_n","y2017_mean_bp",
        "y2018_n","y2018_mean_bp",
        "y2019_n","y2019_mean_bp",
        "y2020_n","y2020_mean_bp",
        "y2021_n","y2021_mean_bp",
        "y2022_n","y2022_mean_bp",
        "hold2013_n","hold2013_mean_bp",
        "train_n","train_mean_bp",
        "e2_2014_2017_n","e2_2014_2017_mean_bp",
        "e3_2018_2022_n","e3_2018_2022_mean_bp",
        "full_2010_2022_n","full_2010_2022_mean_bp",
        "full_2010_2022_net1bp_mean_bp",
    ]],
    on="development_rank",
    how="left",
    validate="one_to_one",
    suffixes=("","_dev"),
)
status(
    OUT,2,8,
    "all V93 economic passes promoted; no cherry-pick",
    promoted=len(promoted),
    development_ranks=pass_ranks,
)

# ---------- evidence ledger 2013-2025, descriptive only ----------
ledger_rows=[]
for r in promoted.itertuples(index=False):
    yearly=[]
    for year in range(2014,2026):
        n=int(getattr(r,f"y{year}_n"))
        mean=float(getattr(r,f"y{year}_mean_bp"))
        yearly.append((year,n,mean))

    years_with_data=sum(n>0 for _,n,_ in yearly)
    pos_gross=sum(n>0 and np.isfinite(m) and m>0 for _,n,m in yearly)
    pos_net1=sum(n>0 and np.isfinite(m) and m>GENERIC_COST_BP for _,n,m in yearly)
    weighted_n=sum(n for _,n,_ in yearly)
    weighted_sum_bp=sum(n*m for _,n,m in yearly if n>0 and np.isfinite(m))
    mean_2014_2025=weighted_sum_bp/weighted_n if weighted_n else np.nan

    oos_break_even=float(r.mean_bp)
    oos_net2=float(r.mean_bp)-2.0
    oos_net3=float(r.mean_bp)-3.0
    oos_net5=float(r.mean_bp)-5.0

    ledger_rows.append({
        "development_rank":int(r.development_rank),
        "trial_index":int(r.trial_index),
        "feature_i":r.feature_i,
        "state_i":r.state_i,
        "feature_j":r.feature_j,
        "state_j":r.state_j,
        "target":r.target,
        "direction":r.direction,
        "train_n":int(r.train_n),
        "train_mean_bp":float(r.train_mean_bp),
        "hold2013_n":int(r.hold2013_n),
        "hold2013_mean_bp":float(r.hold2013_mean_bp),
        "e2_2014_2017_n":int(r.e2_2014_2017_n),
        "e2_2014_2017_mean_bp":float(r.e2_2014_2017_mean_bp),
        "e3_2018_2022_n":int(r.e3_2018_2022_n),
        "e3_2018_2022_mean_bp":float(r.e3_2018_2022_mean_bp),
        "oos_2023_2025_n":int(r.n),
        "oos_2023_2025_mean_bp":float(r.mean_bp),
        "oos_2023_2025_net1bp_mean_bp":float(r.net_1bp_mean_bp),
        "oos_2023_2025_break_even_cost_bp":oos_break_even,
        "oos_2023_2025_net2bp_mean_bp":oos_net2,
        "oos_2023_2025_net3bp_mean_bp":oos_net3,
        "oos_2023_2025_net5bp_mean_bp":oos_net5,
        "oos_2023_2025_cluster_p_one":float(r.cluster_p_one),
        "oos_2023_2025_bh_q":float(r.bh_q_panel),
        "oos_positive_net1bp_years":int(r.positive_net1bp_years),
        "years_2014_2025_with_data":int(years_with_data),
        "positive_gross_years_2014_2025":int(pos_gross),
        "positive_net1bp_years_2014_2025":int(pos_net1),
        "weighted_mean_bp_2014_2025":float(mean_2014_2025),
        "y2023_n":int(r.y2023_n),"y2023_mean_bp":float(r.y2023_mean_bp),
        "y2024_n":int(r.y2024_n),"y2024_mean_bp":float(r.y2024_mean_bp),
        "y2025_n":int(r.y2025_n),"y2025_mean_bp":float(r.y2025_mean_bp),
    })

ledger=pd.DataFrame(ledger_rows).sort_values("development_rank").reset_index(drop=True)
ledger.to_csv(OUT/"PROMOTED_EVIDENCE_LEDGER.csv",index=False)
status(
    OUT,3,8,
    "2013-2025 evidence ledger built; diagnostics do not alter candidate set",
    promoted=len(ledger),
)

# ---------- explicit evidence labels, no hidden winner selection ----------
labels=[]
for r in ledger.itertuples(index=False):
    labels.append({
        "development_rank":int(r.development_rank),
        "label":"PROMOTED_V93_ECONOMIC_PASS",
        "notes":[
            "passed the V93 economic OOS rule that was frozen before scoring",
            "2026 has not been accessed",
            "cost figures above 1bp are robustness diagnostics only",
            "BH q is diagnostic and is not used to exclude another promoted candidate",
        ],
    })
write_json(OUT/"PROMOTION_LABELS.json",labels)

# ---------- freeze exact 3-candidate 2026 holdout before any 2026 access ----------
freeze_cols=[
    "development_rank","trial_index",
    "feature_i","state_i","feature_j","state_j","target","direction",
]
freeze_panel=promoted[freeze_cols].sort_values("development_rank").reset_index(drop=True)
freeze_panel.to_csv(OUT/"FROZEN_2026_FORWARD_PANEL.csv",index=False)
panel_sha=sha256(OUT/"FROZEN_2026_FORWARD_PANEL.csv")

freeze={
    "run_id":RID,
    "status":"V94_2026_FORWARD_PANEL_FROZEN_BEFORE_2026_ACCESS",
    "source_v93":V93.name,
    "source_v92":V92.name,
    "selection_rule":"all and only V93 economic_oos_pass hypotheses",
    "frozen_candidates":len(freeze_panel),
    "development_ranks":pass_ranks,
    "panel_sha256":panel_sha,
    "protocol":FINAL_2026_PROTOCOL,
    "important_inference_note":"V93 panelwide inference is incomplete because six WTI-dependent hypotheses were unscored; this freeze makes no claim about those six.",
    "2026_values_accessed":False,
}
write_json(OUT/"FINAL_2026_FORWARD_FREEZE.json",freeze)
status(
    OUT,4,8,
    "three-candidate 2026 forward panel physically frozen",
    candidates=len(freeze_panel),
    panel_sha256=panel_sha[:16],
)

# ---------- no 2026 file checks: even presence is intentionally deferred ----------
status(OUT,5,8,"2026 file system/data presence intentionally not inspected")

summary=[]
for r in ledger.itertuples(index=False):
    summary.append({
        "development_rank":int(r.development_rank),
        "hypothesis":f"{r.feature_i} {r.state_i} AND {r.feature_j} {r.state_j} -> {r.direction} {r.target}",
        "oos_2023_2025_n":int(r.oos_2023_2025_n),
        "oos_2023_2025_mean_bp":float(r.oos_2023_2025_mean_bp),
        "oos_2023_2025_net1bp_mean_bp":float(r.oos_2023_2025_net1bp_mean_bp),
        "oos_2023_2025_bh_q":float(r.oos_2023_2025_bh_q),
        "oos_positive_net1bp_years":int(r.oos_positive_net1bp_years),
        "positive_net1bp_years_2014_2025":int(r.positive_net1bp_years_2014_2025),
        "break_even_cost_bp_2023_2025":float(r.oos_2023_2025_break_even_cost_bp),
    })
write_json(OUT/"PROMOTED_SUMMARY.json",summary)
status(OUT,6,8,"promotion summary written")

receipt={
    "run_id":RID,
    "status":"COMPLETE_V94_PROMOTION_AND_2026_FREEZE",
    "engine_version":ENGINE_VERSION,
    "source_v93":V93.name,
    "source_v92":V92.name,
    "v93_frozen_hypotheses":int(r93["frozen_hypotheses"]),
    "v93_scored_hypotheses":int(r93["scored_hypotheses"]),
    "v93_unscored_data_unavailable":int(r93["unscored_data_unavailable"]),
    "promoted_candidates":len(freeze_panel),
    "promoted_development_ranks":pass_ranks,
    "frozen_2026_panel_sha256":panel_sha,
    "panelwide_inference_complete":False if int(r93["unscored_data_unavailable"])>0 else True,
    "2026_values_accessed":False,
    "next":"DO_NOT_OPEN_2026_YET; EXECUTION_AND_DATA-ARTIFACT_AUDIT_ON_FROZEN_3_USING_2010_2025_ONLY",
}
write_json(OUT/"RUN_RECEIPT.json",receipt)
status(OUT,7,8,"receipt written",promoted=len(freeze_panel))
status(OUT,8,8,"DONE; 2026 remains fully protected")

print("\n=== V94 RECEIPT ===")
print(json.dumps(receipt,indent=2))
print("\n=== V94 PROMOTED 3 ===")
show=[
    "development_rank","feature_i","state_i","feature_j","state_j","target","direction",
    "oos_2023_2025_n","oos_2023_2025_mean_bp","oos_2023_2025_net1bp_mean_bp",
    "oos_2023_2025_cluster_p_one","oos_2023_2025_bh_q",
    "oos_positive_net1bp_years","positive_net1bp_years_2014_2025",
    "oos_2023_2025_break_even_cost_bp",
]
print(ledger[show].to_string(index=False))
print("\nRUN:",OUT)
