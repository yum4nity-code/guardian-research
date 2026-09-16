# R28 Discovery Candidate v1.00 — Independent Cold Audit — 2026-09-16

## Verdict

**PASS_TO_PREFLIGHT**

This is a static/cold-review verdict only. It does not claim target-machine test
execution and does not authorize R28 discovery until exact-commit preflights pass.

## Reviewed candidate

- preregistration:
  - R28_XAU_COMPRESSION_DIRECTIONAL_DRIFT_PLAN_2026_09_16.md
- discovery engine:
  - xau_r28_discovery_v1_00.py
- R28 synthetic tests:
  - test_xau_r28_discovery_v1_00.py
- frozen conditioning state:
  - xau_edge_discovery_r21_r25_v1_03.r22_volatility_compression
- frozen contiguous forward-return function:
  - xau_edge_discovery_r21_r25_v1_01.forward_return
- sealed discovery builder:
  - build_xau_m5_discovery_slice_v1_02.py

Cold-review source state immediately before this audit document:
- main: 0ef27a753fe2a0236840f41f474b9174e7517734

## Scientific-contract review

PASS.

Primary state:
- bottom10 only

Primary horizons:
- 4b
- 8b

Frozen estimator:
- signed event forward return
- minus event-frequency-weighted same-UTC-clock unconditional signed forward
  return

Frozen inference:
- complete-estimator delete-one-UTC-day jackknife
- union of baseline and event days required
- baseline is re-estimated after deleting each day
- any undefined required replication makes SE/t unavailable

Discovery PASS requires:
- both means nonzero
- same sign at 4b and 8b
- abs(jackknife t) > 2.0 at 4b
- abs(jackknife t) > 2.0 at 8b

Only after discovery PASS may the common sign be frozen for confirmation.

## Conditioning-state identity review

PASS.

The R28 wrapper directly aliases:

xau_edge_discovery_r21_r25_v1_03.r22_volatility_compression

No new percentile, lookback, state threshold, hourly sampling rule or zero-stdev
behavior is implemented.

The wrapper discards bottom20 events from the R28 primary family.

## Signed-outcome review

PASS.

The exact existing contiguous-M5 forward-return function is reused.

R28 does not infer direction from:
- R27 persistence sign
- prior bar return
- session
- news
- breakout state
- volatility magnitude

Signed return is evaluated as a new outcome.

## Same-clock baseline review

PASS.

The signed baseline mirrors the R22 absolute baseline structure:
- one baseline observation for every eligible stage M5 bar
- keyed by UTC minute-of-day
- same forward horizon
- event-frequency weighting across clocks

The only intentional change from R22 is:
- signed forward return instead of absolute forward return

## Complete-jackknife review

PASS.

The implementation:
- removes each required UTC day's event observations
- removes the same day's baseline observations
- recalculates clock-specific baseline means
- recalculates the full event-minus-baseline estimator
- refuses SE/t if any required replication is undefined

Synthetic tests cover:
- known full estimator arithmetic
- valid complete replication set
- required-delete baseline failure
- fail-closed t-stat behavior

## Descriptive-output review

PASS.

Full-sample per-event directional_excess values and naive statistics are
descriptive only.

They are not used by the discovery gate.

## Stage sealing review

PASS.

R28 uses:
- build_xau_m5_discovery_slice_v1_02.py
- xau_edge_discovery_r21_r25_v1_03 discovery receipt validation
- xau_edge_discovery_r21_r25_v1_03 generated-M5 loader

The builder is discovery-only and must physically open only payloads through
2019-06-30.

R28 itself has no confirmation mode and no date CLI arguments.

Stage flags are fixed:
- confirmation_opened false
- pre_oos_2025_opened false
- protected_2026_opened false

## Output / rerun safety review

PASS.

Canonical output:
D:/MT5_Backtests/Research/Autonomous/r28_xau_discovery_v100/discovery.json

Canonical progress:
D:/MT5_Backtests/Research/Autonomous/r28_xau_discovery_v100/progress.json

- final output atomic
- completed result cannot be overwritten
- cleanup limited to R28 transient artifacts
- audit receipts/logs outside cleanup surface

## Test review

R28 synthetic tests cover:
- exact frozen R22 state-extractor identity
- exact forward-return identity
- bottom10-only filtering
- signed forward-return calculation
- same-clock signed estimator arithmetic
- complete delete-one-day fail-closed behavior
- positive-sign discovery PASS
- negative-sign discovery PASS
- opposite-sign horizon FAIL
- t=2.0 boundary FAIL
- unavailable-statistic FAIL
- descriptive signed-baseline attachment
- one-shot result refusal
- artifact path confinement

## Required exact-main-commit preflights

Before R28 discovery is enabled, all must PASS on the same main commit:

1. orchestrator control-plane tests
2. test_xau_r28_discovery_v1_00.py
3. full R21-R25 v1.03 regression suite
4. test_build_xau_m5_discovery_slice_v1_02.py

Only after those receipts exist may R28 discovery r1 be enabled.

## Still prohibited

- confirmation before discovery PASS and sign freeze
- bottom20 rescue
- alternate horizons
- directional conditioning
- PnL optimization
- 2025
- 2026+
- Guardian/live integration
