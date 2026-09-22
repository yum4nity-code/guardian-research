# GEF V111 — Final pre-OOS forensic for V110 UTC calendar survivors

Status: PRE-REGISTERED / READY TO RUN
Date: 2026-09-22

## Frozen source

Exact V110 run:
- run_id: GEF110-20260922-162255
- final survivor SHA256: 3d89751fa6533b5f5290be3b9704480aea9455d4e3b069b10bb2728bd67a2bbc
- 8 validation survivors
- 2023-2025 not accessed
- 2026 not accessed

V111 audits exactly those 8 rows. No new calendar cell, market, horizon, orientation, threshold or candidate substitution is allowed.

## Window

Primary forensic window: 2018-2022 only.

Earlier data may be read only for exact source verification.
Forbidden:
- 2023-2025
- 2026+

## Candidate-level diagnostics

For each frozen V110 survivor:

Baseline:
- N
- directional trade mean
- matched-control effect
- median
- win rate

Costs:
- net after 1, 2, 3 and 5 bp

Tail/concentration:
- trim best 1%, 2%, 5%
- remove best 10 events
- remove best 20 events
- remove best calendar month by total directional contribution
- leave-one-year-out minimum

Timing stability:
- entry -10 minutes
- entry -5 minutes
- exact top-of-hour
- entry +5 minutes
- entry +10 minutes

The same frozen calendar classification uses the original top-of-hour anchor. Timing shifts change only the trade entry/exit, not which calendar event belongs to the candidate.

Bootstrap:
- deterministic calendar-month block bootstrap
- 2,000 draws
- candidate trade mean
- seed 111 + candidate index

## Dependency audit

Across the 8 frozen survivors:
- exact event-set Jaccard on original candidate timestamps
- common-timestamp directional-return correlation
- structural family key = target market + calendar cell
- same market/cell with multiple horizons is one structural information family
- overlapping horizons are not counted as independent edges

No portfolio weighting or optimization.

## Final pre-OOS gate

Candidate passes only if all are true:

- baseline trade mean > 0
- matched-control effect > 0
- net 1 bp > 0
- trim best 5% > 0
- remove best 20 events > 0
- remove best month > 0
- leave-one-year-out minimum > 0
- -5 minute entry mean > 0
- +5 minute entry mean > 0
- +10 minute entry mean > 0
- month-block bootstrap 2.5% lower bound > 0

The -10 minute shift and 2/3/5 bp cost results are diagnostics, not mandatory gates.

No gate relaxation after results.

## Stop

Regardless of outcome, STOP after V111.

Do not open 2023-2025 automatically.
Do not open 2026.

If at least one unique structural information family passes, the next step is a separately preregistered locked-OOS protocol plus human review.
