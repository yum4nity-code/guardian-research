# GUARDIAN M5 Motion Topology — M04 Locked OOS 2023-2025 Preregistration

Date: 2026-09-23
Status: FROZEN BEFORE 2023-2025 OUTCOME ACCESS

Human gate:
Approved by owner after 2018-2022 validation.

Parent discovery:
GEFM5D-20260923-052315

Parent replication:
GEFM5R-20260923-053206

Parent validation:
GEFM5V-20260923-055623

## Frozen locked-OOS candidates

Exactly two variants are eligible:

1. EURUSD <- UDXUSD, relation -1, L15/H15
2. AUDUSD <- UDXUSD, relation -1, L15/H15

All other M01-M08 / M04 variants remain closed.

## Signal definition

Unchanged:
- corr_short = rolling 12 M5 observations, min 8;
- corr_long = rolling 72 M5 observations, min 36;
- corr_break = corr_short - corr_long;
- corr_break_z = causal expanding z with min 250 prior observations and shift 1;
- within prior 15m, max(abs(corr_break_z)) >= 1.5;
- current abs(corr_break_z) < 1.0;
- current abs(corr_break_z) < abs(corr_break_z one bar ago);
- 30m cooldown.

## Target

endpoint_score_15m_15m only.

No horizon substitution.

## Causal continuity

Construct state continuously from 2011 through 2025.
Do not reset expanding/rolling state at 2023.

Before scoring 2023-2025:
- reconstruct through 2022;
- require parity against the frozen pre-2018 reference and published 2018-2022 validation aggregates.

2026 is forbidden.

## Locked OOS hard gates per variant

- >=100 independent event episodes;
- >=60 distinct UTC days;
- mean endpoint_score > 0;
- one-sided cluster-robust p <= 0.05.

No new multiplicity correction is introduced at locked OOS because only the two frozen, independently validated candidates are being tested.

## Mandatory diagnostics only

Report, but do not use as mechanical pass/fail:
- 2023 / 2024 / 2025 means separately;
- leave-one-year-out means;
- trim-best 1% and 2%;
- +/-60m placebo shifts.

## No rescue

Forbidden:
- threshold changes;
- correlation-window changes;
- alternate horizons;
- alternate cooldown;
- session filtering;
- dropping a year;
- pair substitutions;
- direction changes;
- TP/SL optimization;
- execution-cost optimization.

## Interpretation

Evaluate EURUSD L15 and AUDUSD L15 separately.
Do not select a "winner" after seeing OOS.
If one passes and one fails, preserve both outcomes exactly.

2026 remains protected and unopened.
