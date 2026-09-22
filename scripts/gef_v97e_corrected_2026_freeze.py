from pathlib import Path
import pandas as pd
import json
import hashlib

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v97e_corrected_2026_freeze"
BASE.mkdir(parents=True,exist_ok=True)
ENGINE_VERSION="V97E.0"

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
        "step":step,"steps":total,
        "percent":round(100*step/total,1),
        "timestamp_utc":pd.Timestamp.now("UTC").isoformat(),
        "message":msg,**extra,
    }
    write_json(out/"LIVE_STATUS.json",payload)
    tail=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF97E] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

# Latest completed V97D.
runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v97d_full_v93_repair").glob("GEF97D-*"))
runs=[
    p for p in runs
    if (p/"RUN_RECEIPT.json").exists()
    and (p/"CORRECTED_FULL_V93_SCORED_PANEL.csv").exists()
    and json.loads((p/"RUN_RECEIPT.json").read_text(encoding="utf-8")).get("status")=="COMPLETE_V97D_FULL_V93_SCORED_PANEL_REPAIR"
]
if not runs:
    raise RuntimeError("No completed V97D full-panel repair")
V97D=runs[-1]
r97d=json.loads((V97D/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r97d.get("2026_accessed"):
    raise RuntimeError("V97D reports 2026 access")
R=pd.read_csv(V97D/"CORRECTED_FULL_V93_SCORED_PANEL.csv")

RID="GEF97E-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID
OUT.mkdir(parents=True,exist_ok=False)
status(
    OUT,1,7,
    "corrected V97D scored panel loaded; 2026 remains unopened",
    source_v97d=V97D.name,
    scored=len(R),
    unscored=len(r97d.get("unscored_original_ranks",[])),
)

required=[
    "development_rank","trial_index","feature_i","state_i",
    "feature_j","state_j","target","direction",
    "n","mean_bp","net_1bp_mean_bp","cluster_p_one","bh_q_panel",
    "positive_net1bp_years","economic_oos_pass",
]
missing=[c for c in required if c not in R.columns]
if missing:
    raise RuntimeError(f"V97D corrected panel schema missing {missing}")
if R["development_rank"].duplicated().any():
    raise RuntimeError("V97D corrected panel duplicate ranks")

passes=R[R["economic_oos_pass"].astype(bool)].copy()
if passes.empty:
    raise RuntimeError("Corrected V97D panel has no economic OOS pass")

pass_ranks=sorted(passes["development_rank"].astype(int).tolist())
expected=sorted(int(x) for x in r97d.get("corrected_economic_pass_ranks",[]))
if pass_ranks!=expected:
    raise RuntimeError(f"V97D receipt/panel pass mismatch: panel={pass_ranks} receipt={expected}")

status(
    OUT,2,7,
    "corrected promotion set resolved from exact pre-existing economic rule",
    corrected_pass_ranks=pass_ranks,
)

identity_cols=[
    "development_rank","trial_index","feature_i","state_i",
    "feature_j","state_j","target","direction",
]
freeze_panel=passes[identity_cols].sort_values("development_rank").reset_index(drop=True)
freeze_path=OUT/"CORRECTED_2026_FORWARD_PANEL.csv"
freeze_panel.to_csv(freeze_path,index=False)
panel_sha=sha256(freeze_path)

summary_cols=[
    "development_rank","feature_i","state_i","feature_j","state_j","target","direction",
    "n","mean_bp","net_1bp_mean_bp","positive_net1bp_years",
    "cluster_p_one","bh_q_panel",
    "y2023_n","y2023_mean_bp","y2024_n","y2024_mean_bp","y2025_n","y2025_mean_bp",
]
summary=passes[summary_cols].sort_values("development_rank").reset_index(drop=True)
summary.to_csv(OUT/"CORRECTED_PROMOTED_EVIDENCE.csv",index=False)

status(
    OUT,3,7,
    "corrected 2026 forward panel physically frozen",
    candidates=len(freeze_panel),
    sha256=panel_sha[:16],
)

freeze={
    "run_id":RID,
    "status":"V97E_CORRECTED_2026_FORWARD_PANEL_FROZEN",
    "source_v97d":V97D.name,
    "selection_rule":"all and only corrected V97D economic_oos_pass hypotheses among the original V93 scored hypotheses",
    "frozen_candidates":len(freeze_panel),
    "development_ranks":pass_ranks,
    "panel_sha256":panel_sha,
    "supersedes_v94_promotion_set":True,
    "superseded_reason":"V97A/V97B proved a USDCHF 2023-2025 timestamp anomaly; V97D repaired the full original V93 scored panel without outcome-based retuning",
    "panelwide_inference_complete":bool(r97d.get("panelwide_inference_complete",False)),
    "unscored_original_ranks":r97d.get("unscored_original_ranks",[]),
    "important_limitation":"six original V92 hypotheses remain unscored because their required WTI 2024-2025 source files were unavailable; this freeze makes no claim about those six",
    "2026_values_accessed":False,
    "protocol":{
        "candidate_set":"exact corrected ranks frozen here; no additions/removals based on later diagnostics",
        "2026_window":"protected; do not open before intentional final release",
        "minimum_2026_signals":10,
        "gross_mean_positive":True,
        "net_after_hypothetical_1bp_positive":True,
        "diagnostic_statistics":"cluster p/BH diagnostic only",
        "no_retuning":True,
        "no_new_filter":True,
        "no_candidate_replacement":True,
    },
}
write_json(OUT/"CORRECTED_2026_FORWARD_FREEZE.json",freeze)
status(OUT,4,7,"freeze metadata written; old V94 left untouched but superseded")

# Explicit supersession ledger so downstream scripts cannot silently use ranks 3/5.
supersession={
    "old_v94_run":None,
    "old_promoted_ranks":[3,5,9],
    "corrected_promoted_ranks":pass_ranks,
    "removed_after_data_repair":[3,5],
    "newly_promoted_after_data_repair":[7],
    "unchanged_promoted":[9],
    "reason":"USDCHF 2023-2025 timestamp semantics repair",
    "retuning":False,
    "2026_accessed":False,
}
# Resolve old V94 from V97D's source_v93 lineage if available from latest completed V94.
v94_runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v94").glob("GEF94-*"))
v94_runs=[p for p in v94_runs if (p/"RUN_RECEIPT.json").exists()]
if v94_runs:
    supersession["old_v94_run"]=v94_runs[-1].name
write_json(OUT/"SUPERSESSION_LEDGER.json",supersession)
status(OUT,5,7,"supersession ledger written",old=[3,5,9],corrected=pass_ranks)

receipt={
    "run_id":RID,
    "status":"COMPLETE_V97E_CORRECTED_2026_FREEZE",
    "engine_version":ENGINE_VERSION,
    "source_v97d":V97D.name,
    "corrected_promoted_ranks":pass_ranks,
    "frozen_candidates":len(freeze_panel),
    "frozen_panel_sha256":panel_sha,
    "panelwide_inference_complete":bool(r97d.get("panelwide_inference_complete",False)),
    "unscored_original_ranks":r97d.get("unscored_original_ranks",[]),
    "candidate_set_changed_by_script":False,
    "thresholds_retuned":False,
    "2026_values_accessed":False,
    "next":"AUDIT_FROZEN_CORRECTED_RANKS_7_AND_9_ON_PRE2026_EXECUTION_AND_FTMO_FEED_ONLY; KEEP_2026_CLOSED",
}
write_json(OUT/"RUN_RECEIPT.json",receipt)
status(OUT,6,7,"receipt written")
status(OUT,7,7,"DONE; corrected panel frozen, 2026 untouched")

print("\n=== V97E RECEIPT ===")
print(json.dumps(receipt,indent=2))
print("\n=== V97E CORRECTED PROMOTED EVIDENCE ===")
print(summary.to_string(index=False))
print("\nRUN:",OUT)
