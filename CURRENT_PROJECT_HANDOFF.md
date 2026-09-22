# Guardian Research — CURRENT PROJECT HANDOFF

**Canonical current state: 2026-09-22**

## Closed / frozen lineages
- V100 forward/shadow frozen; 2026 protected.
- Rates standalone closed after V103 forensic 0/5.
- CFTC standalone closed after V105 report-level forensic 0/7.
- ALFRED V107 closed operationally without alpha conclusion.
- Treasury V109 closed at discovery: 15,870 finite tests, 0 frozen after BH.

## V110 — VALIDATED PRE-OOS

Run: GEF110-20260922-162255
- 240 frozen calendar cells
- 10,265 finite discovery tests
- 76 discovery survivors
- 33 replication survivors
- 19 robustness survivors
- 8 validation survivors
- final SHA256: 3d89751fa6533b5f5290be3b9704480aea9455d4e3b069b10bb2728bd67a2bbc
- 2023-2025 not accessed
- 2026 not accessed

Eight survivors include obvious structural clusters:
- AUDUSD H21: 120m and 240m
- USDCHF H23: 120m and 240m
- USDCHF H22: 240m
- USDJPY H22 Thursday: 120m
- XAGUSD H11: 60m
- EURUSD H11: 120m

Do not treat all eight as independent edges.

## V111 — ACTIVE

Final pre-OOS forensic of exactly those eight V110 survivors.

2018-2022 only.

Tests:
- baseline candidate mean and matched-control effect
- net 1/2/3/5 bp
- trim best 1/2/5%
- remove best 10/20 events
- remove best calendar month
- leave-one-year-out
- timing shifts -10/-5/+5/+10 minutes around the frozen hour
- deterministic 2,000-draw month-block bootstrap
- event-set Jaccard
- common-timestamp return correlation
- structural family key = target_market + calendar cell

Pass requires:
baseline >0; control effect >0; net1 >0; trim5 >0; remove-best20 >0; remove-best-month >0; LOO >0; -5m >0; +5m >0; +10m >0; bootstrap q2.5 >0.

STOP after V111.
Do not open 2023-2025 automatically.
Do not open 2026.
