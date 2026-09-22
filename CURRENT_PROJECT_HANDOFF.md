# Guardian Research — CURRENT PROJECT HANDOFF

**Canonical current state: 2026-09-22**

## V100 — frozen forward/shadow lineage

- run_id: GEF100-20260922-094644
- frozen ranks: 7, 9
- panel SHA256: 0dd255ce02f1ac528ecc8b38293213d779d0647a79b2a9f065eee5ee550810f4
- compile PASS
- shadow only
- activation not before 2027-01-02 00:00
- 2026 market values not accessed

Do not retune V100 or use ranks 7/9 to select new research.

## V101 — CLOSED

Completed:
- run_id: GEF101-20260922-142601
- engine: V101.2
- atomic shortlist: 3641
- attempted triples: 17417
- finite discovery triples: 187
- discovery frozen: 150
- replication survivors: 2
- validation survivors: **0**
- 2023-2025 accessed: false
- 2026 accessed: false

Decision: close sparse PRICE × PRICE × RATES interaction lineage. No rescue of the two replication survivors.

Canonical receipt:
research/results/GEF101_CLOSURE_2026_09_22.json

## V102 — ACTIVE NEXT TEST

Question: do standalone nominal-rate / real-yield / breakeven / yield-curve states carry reproducible predictive information without requiring a price-state interaction?

Protocol:
- 2010-2012 discovery
- 2013 internal confirmation
- freeze
- 2014-2017 replication
- robustness
- immutable freeze
- 2018-2022 validation
- STOP

No 2023-2025.
No 2026.

Files:
- research/campaigns/GEF_V102_STANDALONE_RATES_2026_09_22.md
- scripts/gef_v102_standalone_rates.py
- automation/Run-GuardianEdgeFactoryV102.ps1
- automation/Watch-GuardianEdgeFactoryV102.ps1

V102 deliberately reuses the canonical V83B/V85 rate state lineage and the V101.2 reconstruction semantics. V101 triple outcomes are not used to choose V102 candidates.

## Run

powershell -ExecutionPolicy Bypass -File D:\MT5_Backtests\guardian-research\automation\Run-GuardianEdgeFactoryV102.ps1 -Root D:\MT5_Backtests
