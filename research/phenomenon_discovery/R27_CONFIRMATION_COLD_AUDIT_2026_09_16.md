# R27 Confirmation Candidate v1.00 — Independent Cold Audit — 2026-09-16

## Verdict

**PASS_TO_PREFLIGHT**

Static/cold-review verdict only. Real R27 confirmation remains prohibited until
all exact-main-commit preflights pass.

## Reviewed candidate

- preregistration:
  - R27_XAU_COMPRESSION_PERSISTENCE_PLAN_2026_09_16.md
- confirmation engine:
  - xau_r27_confirmation_v1_00.py
- R27 synthetic tests:
  - test_xau_r27_confirmation_v1_00.py
- reused R22 implementation/regression:
  - xau_edge_discovery_r21_r25_v1_03.py
  - test_xau_edge_discovery_r21_r25_v1_03.py
- reused sealed confirmation builder:
  - build_xau_m5_r21_confirmation_slice_v1_00.py
  - test_build_xau_m5_r21_confirmation_slice_v1_00.py
- reused R15/stage admission:
  - xau_r21_confirmation_v1_00.py

Cold-review source state immediately before this audit document:
- main: 3c7d29611baf7a5e1d47c11616f582bdccb204cd

## Scientific contract review

PASS.

R27 is a new research identifier. R22 expansion remains a failed hypothesis.

Frozen primary state:
- bottom10 only

Frozen primary horizons:
- 4b
- 8b

Frozen persistence effect:
- persistence_h = -excess_abs_h
- equivalently baseline absolute movement minus compressed-event absolute movement

Frozen joint gate:
- persistence_4b mean > 0
- persistence_4b complete-estimator delete-one-day jackknife t > +2.0
- persistence_8b mean > 0
- persistence_8b complete-estimator delete-one-day jackknife t > +2.0

All conditions required.

Bottom20 and 1b/2b/16b are descriptive only and cannot rescue a failed primary.

## Frozen R22 component identity review

PASS.

The R27 engine aliases directly:
- xau_edge_discovery_r21_r25_v1_03.r22_volatility_compression
- xau_edge_discovery_r21_r25_v1_03.r22_complete_estimator_day_jackknife

No R27-specific rewrite of:
- prior-48 volatility statistic
- 20 prior trading-day normalization
- bottom10 threshold
- hourly first-event sampling
- same-clock baseline
- complete-estimator delete-one-day jackknife

exists.

## Baseline / inference review

PASS.

The exact R22 same-clock baseline is retained.

The jackknife:
- re-estimates the complete event-minus-baseline estimator for every required
  delete-one-UTC-day replication
- requires every baseline/event day replication
- returns SE/t unavailable if any required replication is undefined

R27 sign-inverts only:
- full estimator mean
- resulting t-statistic

The cluster/jackknife SE, replicate counts, method and failure reason are preserved.

## Descriptive-statistics cold-review correction

During cold review, the first R27 draft attempted to derive the sign-inverted
naive positive fraction as 1 - original_positive_fraction. That is incorrect if
exact zero observations exist.

This did not affect the primary complete-jackknife gate, but the descriptive
implementation was corrected before this audit verdict.

The final code now computes naive persistence statistics directly on:
- -excess_abs_4b
- -excess_abs_8b

A synthetic test explicitly includes a zero observation and verifies the exact
positive fraction.

## Stage / provenance review

PASS.

R27 reuses the already-audited confirmation infrastructure:
- canonical R15 path only
- pinned R15 SHA256
- persisted R15 attestation checks
- private snapshot of verified index bytes
- exact confirmation builder
- exact first date 2019-07-01
- exact last date 2024-12-31
- exactly 1,437 source days
- generated M5 absolute 300-second grid
- 2025 payload bytes unopened
- 2026+ hard sealed

## Independence disclosure review

PASS WITH DISCLOSED LIMITATION.

2019-07-01 through 2024-12-31 payload bytes were previously opened by R21 and R26.
Neither run computed R22/R27 confirmation events/statistics.

R27 outcomes therefore remain unseen before preregistration, while the period is
not virgin-byte data.

2025 remains unopened and is not used as a replacement confirmation set.

## Compute-surface review

PASS.

R27 intentionally does not call the full R22 summary across ten state/horizon
jackknifes.

It computes:
- exact R22 events
- bottom10 complete-estimator jackknife at 4b
- bottom10 complete-estimator jackknife at 8b

This reduces compute without changing the frozen primary estimator.

Progress phases:
- build_m5
- load_m5
- extract_R27_events
- jackknife_4b
- jackknife_8b
- serialize
- complete

## Output / rerun safety review

PASS.

Canonical output:
D:/MT5_Backtests/Research/Autonomous/r27_xau_confirmation_v100/confirmation.json

Canonical progress:
D:/MT5_Backtests/Research/Autonomous/r27_xau_confirmation_v100/progress.json

- final output is atomic
- existing final output causes hard refusal
- cleanup removes only R27 transient files/directories
- receipts/logs remain outside cleanup

## Required exact-commit preflights

Before real R27 confirmation is enabled, all must PASS on the same main commit:

1. orchestrator control-plane tests
2. R27 synthetic confirmation tests
3. full R21-R25 v1.03 regression suite, covering R22 complete jackknife
4. sealed confirmation-builder tests

Only after these receipts exist may R27 confirmation r1 be enabled.

## Still prohibited

- bottom20 rescue
- 1b/2b/16b rescue
- percentile/state/session tuning
- PnL optimization
- 2025 inspection
- 2026+ inspection
- Guardian/live integration
