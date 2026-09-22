# Guardian Research — CURRENT PROJECT HANDOFF

**Canonical current state: 2026-09-22**

## V100 — frozen forward/shadow package

Operator receipt supplied from the completed run:

- run_id: GEF100-20260922-094644
- status: V100_FORWARD_SHADOW_PACKAGE_FROZEN
- source_v97e: GEF97E-20260922-085850
- source_v99: GEF99-20260922-092305
- frozen ranks: **7, 9**
- frozen panel SHA256: 0dd255ce02f1ac528ecc8b38293213d779d0647a79b2a9f065eee5ee550810f4
- MQL compile: **PASS — 0 errors, 0 warnings**
- activation_not_before: **2027-01-02 00:00**
- shadow_only: **true**
- real_seed_included: **false**
- order_sending_code_present: **false**
- 2026 market values accessed: **false**

Interpretation: V100 is the frozen execution/shadow package for an existing validated lineage. It is not the next discovery experiment. Do not alter ranks 7/9, thresholds, candidate identities or activation lock.

The repository also contains V100B parity-audit code. Do not assume V100B has been executed unless a local V100B receipt proves it.

## Next primary research — V101

V101 is preregistered as a genuinely new bounded interaction class:

**PRICE STATE A × PRICE STATE B × RATES/REAL-YIELD/BREAKEVEN STATE → target return**

Files:
- research/campaigns/GEF_V101_SPARSE_TRIPLE_RATES_2026_09_22.md
- scripts/gef_v101_sparse_triple_rates.py
- automation/Run-GuardianEdgeFactoryV101.ps1

Design:
- 2010-2012 discovery
- 2013 internal discovery holdout
- freeze
- 2014-2017 replication
- freeze
- 2018-2022 validation
- STOP

V101 may never read 2023-2025 or 2026.

## Important temporal nuance

The lineage that became V100 has already used 2023-2025 historically. Those years therefore cannot be described globally as untouched.

For V101, however, 2023-2025 are explicitly forbidden as selection/evaluation data. They are not reusable merely because another frozen lineage saw them.

2026 remains protected and unopened according to the V100 receipt.

## Why V101 is not a duplicate

V85 already scanned a large singleton + pair universe. Running the same search again would only add multiplicity.

V101 therefore:
- reuses the frozen V85 state/target infrastructure;
- selects atoms using only the original discovery windows;
- tests exactly three-condition interactions;
- requires two price states from different price families plus one causal rates state;
- reproduces selected 2010-2013 states exactly before replication;
- fails closed on any parity mismatch;
- freezes candidates before each later temporal window.

## Next action

Run:

powershell -ExecutionPolicy Bypass -File D:\MT5_Backtests\guardian-research\automation\Run-GuardianEdgeFactoryV101.ps1 -Root D:\MT5_Backtests

Then inspect the newest RUN_RECEIPT.json under:
D:\MT5_Backtests\Research\Autonomous\guardian_edge_factory_v101_sparse_triple_rates\GEF101-*

Do not open or score 2023-2025/2026 after V101 without a new explicit decision.