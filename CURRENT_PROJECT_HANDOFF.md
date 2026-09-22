# Guardian Research — CURRENT PROJECT HANDOFF

**Canonical current state: 2026-09-22**

## V100
Frozen forward/shadow package. Ranks 7/9. 2026 protected.

## Closed before locked OOS
- rates standalone: V103 pre-OOS forensic 0/5
- CFTC standalone: V105 report-level pre-OOS forensic 0/7

2023-2025 was not spent on either lineage.

## V106 source audit — COMPLETE

Run GEF106-20260922-152746:
- 127 candidate source files audited
- zero edge trials
- financial_conditions: not ready, no causal release field
- treasury_auctions: not safely inspectable yet
- fomc_fed: not safely inspectable yet
- cfe_volume_oi: no causal release field
- cboe_vol: no causal release field under this audit
- **alfred_vintage: READY**
  - 53 candidate files
  - 39 safely inspected tables
  - coverage 2000-2022
  - 39 tables with causal vintage semantics

## V107.3 — ACTIVE

Standalone ALFRED first-vintage event-level research.

Canonical causal rule inherited from V80C:
- use first_vintage only as release provenance
- use first_value only as value
- AVAILABLE_AT = first_vintage + 1 calendar day
- never use last_vintage, last_value, was_revised, vintage_count or final revised values

Critical statistical rule:
**one observation per ALFRED release event**.
V107.2 uses one release per observation, NEG/POS states for d1/d3, prior-median-side states for level/z24, and a physical price firewall: <=2013 before discovery freeze, <=2017 after freeze, <=2022 only after pre-validation freeze.
Do not count every 5-minute bar while a released macro value remains carried forward.

Features per series:
- level
- d1
- d3
- z24
with causal release-space standardization.

Targets:
- local Guardian HistData markets
- 60 / 120 / 240 minute horizons

Temporal ladder:
2010-2013 discovery -> freeze -> 2014-2017 replication -> robustness -> freeze -> 2018-2022 validation -> STOP.

No 2023-2025.
No 2026.

Run:
powershell -ExecutionPolicy Bypass -File D:\MT5_Backtests\guardian-research\automation\Run-GuardianEdgeFactoryV107.ps1 -Root D:\MT5_Backtests


### V107.3 correction
Earlier V107.0-2 runs produced zero finite discovery tests.
V107.3 now audits all ALFRED pre-2023 tables, measures event support before reading returns, uses all-release symmetric directional scoring rather than sparse state buckets, and exits with a valid receipt instead of raising if support is insufficient.
