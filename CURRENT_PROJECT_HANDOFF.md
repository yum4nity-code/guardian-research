# Guardian Research — CURRENT PROJECT HANDOFF

**Canonical current state: 2026-09-22**

## V100
Frozen forward/shadow package. Ranks 7/9. 2026 protected.

## V101 — CLOSED
Sparse price × price × rates:
17,417 attempted -> 150 frozen -> 2 replicated -> 0 validated.

## V102/V103 — RATES CLOSED BEFORE OOS

V102 run GEF102-20260922-143744:
10,902 finite tests -> 200 frozen -> 34 replicated -> 27 robust -> 5 validated.

V103 run GEF103-20260922-145228:
- five candidates audited
- three unique signal families
- **0 final pre-OOS passes**
- 2023-2025 not accessed
- 2026 not accessed

Important interpretation:
- REAL 7Y d1 LO -> GBPUSD/AUDUSD/EURUSD signals were concentrated in a single validation month/year, so month-removal / leave-one-year-out / month bootstrap became undefined because no independent sample remained.
- NOM 1M -> USDJPY failed independent concentration/repeated-signal gates.
- NOM 3M d5 -> USDCHF failed trim-5% and daily-first stress.
- Therefore no lag diagnostic can rescue the lineage; rates standalone is closed before locked OOS.

Canonical closure:
research/results/GEF103_RATES_CLOSURE_2026_09_22.json

## V104 — ACTIVE NEXT FAMILY

Standalone CFTC Futures Only positioning.

Causal rule:
- report/as-of date parsed using V82D logic
- AVAILABLE_AT = next Monday 00:00 UTC after report date
- exact V83 market mappings
- exact V83 feature definitions
- 2010-2013 values anchored to canonical V83B
- exact V85 state parity required before replication

Protocol:
2010-2012 discovery -> 2013 confirmation -> freeze -> 2014-2017 replication -> robustness -> freeze -> 2018-2022 validation -> STOP.

No 2023-2025.
No 2026.

Run:
powershell -ExecutionPolicy Bypass -File D:\MT5_Backtests\guardian-research\automation\Run-GuardianEdgeFactoryV104.ps1 -Root D:\MT5_Backtests
