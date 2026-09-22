# Guardian Research — CURRENT PROJECT HANDOFF

**Canonical current state: 2026-09-22**

## V100
Frozen forward/shadow package. Ranks 7/9. 2026 protected.

## V101 — CLOSED
GEF101-20260922-142601:
- 17,417 sparse triples attempted
- 150 frozen
- 2 replication survivors
- 0 validation survivors
Decision: closed, no rescue.

## V102 — VALIDATED PRE-OOS
GEF102-20260922-143744:
- 10,902 finite standalone-rate tests
- 200 discovery candidates frozen
- 34 replication survivors
- 27 robustness survivors
- 5 validation survivors
- final survivor SHA256: f6aa7d91488a5e52eeb1d5fa3c614dcff918ac3f1e4dd680ec3e3cac7060b865
- 2023-2025 not accessed
- 2026 not accessed

Five survivors:
1. NOM 1M level HI -> USDJPY 240m SHORT
2. REAL 7Y d1 LO -> GBPUSD 120m LONG
3. REAL 7Y d1 LO -> AUDUSD 120m LONG
4. REAL 7Y d1 LO -> EURUSD 120m LONG
5. NOM 3M d5 HI -> USDCHF 120m SHORT

The three REAL 7Y candidates share the same signal definition and count as one economic signal family for independence analysis.

## V103 — ACTIVE NEXT
Final <=2022 forensic of the exact five V102 survivors.

Tests include:
- tail concentration;
- remove best 10 events;
- remove best calendar month;
- leave-one-year-out;
- horizon non-overlap;
- one signal per day;
- one signal per contiguous state episode;
- z 0.9 / 1.1;
- +1d / +2d information delay;
- 1/2/3/5 bp cost diagnostics;
- month-block bootstrap;
- signal overlap and common-timestamp return correlations.

V103 does not optimize a portfolio and does not open 2023-2025 or 2026.

Run:
powershell -ExecutionPolicy Bypass -File D:\MT5_Backtests\guardian-research\automation\Run-GuardianEdgeFactoryV103.ps1 -Root D:\MT5_Backtests

Regardless of result, STOP after V103. A separate preregistered V104 plus human decision is required before any 2023-2025 access.
