# GUARDIAN M5 Motion Topology — M04 2018-2022 Independent Validation Preregistration

Date: 2026-09-23
Status: FROZEN BEFORE 2018-2022 OUTCOMES

Parent discovery:
GEFM5D-20260923-052315

Parent replication:
GEFM5R-20260923-053206

Frozen replication survivor SHA256:
942eeda155a39446adecacba0171a04552d0c99fe86ac1cfb50fab30dce3b371

## Replication result

Six frozen M04 discovery survivors were tested exactly on 2015-2017.
Five survived:
1. EURUSD <- UDXUSD relation -1 L15/H15
2. GBPUSD <- UDXUSD relation -1 L15/H15
3. GBPUSD <- UDXUSD relation -1 L30/H30
4. AUDUSD <- UDXUSD relation -1 L15/H15
5. USDCHF <- UDXUSD relation +1 L15/H15

AUDUSD <- UDXUSD L30/H30 failed replication and is CLOSED.
It is not eligible for validation or rescue.

## Scientific interpretation

The five surviving variants are treated as correlated manifestations of one M04 family:
UDX/FX correlation break followed by recoupling before a movement endpoint.

They are not treated as five independent discoveries.

## Exact signal definition

Unchanged from discovery and replication:
- corr_short = rolling 12 M5 observations, min 8;
- corr_long = rolling 72 M5 observations, min 36;
- corr_break = corr_short - corr_long;
- corr_break_z = causal expanding z, min 250 prior observations, shift 1;
- prior 15m max(abs(corr_break_z)) >= 1.5;
- current abs(corr_break_z) < 1.0;
- current abs(corr_break_z) < abs(corr_break_z one bar ago);
- 30m event cooldown.

## Exact target

Frozen endpoint_score:
- L15/H15 for EURUSD, GBPUSD, AUDUSD, USDCHF;
- L30/H30 for GBPUSD L30.

No target or horizon substitution.

## Causal continuity and parity

Build features continuously from 2011 through 2022.
Do not reset expanding/rolling state at 2018.

Before any 2018-2022 scoring:
- reconstruct 2011-2017;
- require exact parity against the replication engine for corr_break and corr_break_z on all four FX pairs;
- if parity fails, stop before validation.

2023+ is forbidden.

## Validation statistical unit

Event episode:
first M04 event after 30m cooldown.

Inference clusters:
UTC calendar day.

## Minimum support

Each frozen variant must have:
- >=250 independent episodes over 2018-2022;
- >=150 distinct UTC days.

## Primary validation gate per variant

A variant VALIDATES only if all are true:
1. mean endpoint_score > 0;
2. one-sided cluster-robust p <= 0.05;
3. at least 4 of 5 calendar-year means are > 0;
4. leave-one-year-out minimum mean endpoint_score > 0;
5. trim-best-1%-of-episodes mean endpoint_score > 0;
6. trim-best-2%-of-episodes mean endpoint_score > 0.

No threshold rescue if any gate fails.

## Family-level interpretation

Because variants share UDX and overlapping FX structure:
- report all five;
- report the count validating;
- do not call them independent edges;
- no best-of-five selection is allowed.

The M04 family is considered independently validated only if at least 3 of the 5 frozen variants pass ALL variant gates.

This 3-of-5 rule is frozen now, before any 2018-2022 outcome access.

## Negative-control diagnostics

Diagnostics do not rescue a failed primary gate.

For each variant, report endpoint_score at:
- event timestamps shifted +60 minutes;
- event timestamps shifted -60 minutes.

These are specificity diagnostics only.
They do not replace or relax the primary validation gate.

## Execution

No TP/SL optimization.
No transaction-cost optimization.
No session subgroup optimization.
No live FTMO mapping.

Execution design is a later stage only if the signal family validates.

## Locked future

2023-2025 remains LOCKED OOS.
2026 remains PROTECTED.

If family validation passes:
stop and prepare a human-reviewed locked-OOS protocol before any 2023-2025 access.

If family validation fails:
close this M04 lineage with no rescue.
