from pathlib import Path
import pandas as pd
import json

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v87"

runs=sorted(BASE.glob("GEF87-*"))
runs=[p for p in runs if (p/"RUN_RECEIPT.json").exists() and (p/"TRAIN_PLUS_2013_EDGE_AUDIT.csv").exists()]
if not runs:
    raise RuntimeError("No completed V87 output found")

run=runs[-1]
receipt=json.loads((run/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
audit=pd.read_csv(run/"TRAIN_PLUS_2013_EDGE_AUDIT.csv")

top=audit.sort_values(
    ["bh_q_primary","holdout_p_primary_one","mean_bp_2013"],
    ascending=[True,True,False],
    kind="mergesort"
)

show_cols=[
    "panel_rank","raw_rank","family_i","state_i","family_j","state_j",
    "target","direction",
    "n_train","mean_bp_train","positive_years","worst_year_mean_bp",
    "trim_top5_mean_bp_train","net_1p0bp_mean_bp_train",
    "n_2013","mean_bp_2013","win_rate_pct_2013",
    "holdout_p_primary_one","bh_q_primary","holm_p_primary",
    "net_1p0bp_mean_bp_2013","net_2p0bp_mean_bp_2013",
    "gross_sum_pct_2013","max_drawdown_pct_2013"
]

econ=audit.sort_values(
    ["mean_bp_2013","holdout_p_primary_one"],
    ascending=[False,True],
    kind="mergesort"
)

econ_cols=[
    "panel_rank","family_i","family_j","target","direction",
    "n_2013","mean_bp_2013","win_rate_pct_2013",
    "gross_sum_pct_2013","net_1p0bp_sum_pct_2013",
    "net_2p0bp_sum_pct_2013","holdout_p_primary_one","bh_q_primary"
]

missing=[c for c in show_cols+econ_cols if c not in audit.columns]
if missing:
    raise RuntimeError("Missing expected V87 columns: "+", ".join(sorted(set(missing))))

print("\n=== V87 RECEIPT ===")
print(json.dumps(receipt,indent=2))
print("\n=== TOP 30 BY 2013 CONFIRMATION ===")
print(top[show_cols].head(30).to_string(index=False))
print("\n=== BEST 20 ECONOMICALLY IN 2013 (GROSS MEAN BP) ===")
print(econ[econ_cols].head(20).to_string(index=False))
print("\nRUN:",run)
