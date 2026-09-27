# GUARDIAN M5 Motion Topology — M09/M10 Motif Census Preregistration

Date: 2026-09-27  
Status: FROZEN BEFORE MOTIF CENSUS

## Purpose

Resume the original M5 Motion Topology Factory with the still-untested configuration-based families:
- M09 repeated state / motif;
- M10 recurrent sequence.

This stage is predictor-only. It freezes which recurring configurations exist often enough to deserve an outcome test. It does not test alpha and must not open endpoint target files.

## Temporal firewall

- warm-up: 2011;
- motif census: 2012-2014 only;
- 2015+ state files forbidden in this engine;
- 2015+ outcomes forbidden;
- 2023-2025 locked OOS untouched;
- 2026 protected.

## Frozen compact state

For each market and L in {15,30,60} minutes, encode:
1. established move direction: sign(ret_L);
2. move strength from causal expanding z(ret_L): weak <0.75, medium 0.75-1.5, strong >=1.5;
3. acceleration relative to established move: sign(sign(ret_L) * accel_5_vs_15);
4. shock flag: frozen shock_abs_ge_1p5;
5. full-universe breadth bucket: <0.40 / 0.40-0.60 / >0.60;
6. causal dispersion z bucket: <-0.75 / -0.75..0.75 / >0.75;
7. residual-extreme flag: any incident frozen economic-graph residual z with abs>=1.5;
8. correlation-break flag: any incident graph pair causal corr-break z with abs>=1.5.

No bit may be added, removed or threshold-changed after the census is seen without starting a new experiment.

## M09

Single compact state at t.

A state enters the frozen outcome-test dictionary only if it has >=100 independent 30-minute-cooldown episodes in 2012-2014.

## M10

Frozen sequences of the same state representation:
- length 2: t-5m -> t;
- length 3: t-10m -> t-5m -> t.

A sequence enters the frozen outcome-test dictionary only if it has >=100 independent 30-minute-cooldown episodes.

## Later outcome engine — not part of this run

After census review, a separate engine may test only frozen dictionary entries against matched endpoint_score L->L in 2012-2014.

Hard discovery eligibility will remain:
- >=200 independent episodes;
- >=120 UTC days;
- positive endpoint effect;
- cluster-robust one-sided test by UTC day;
- BH-FDR q<=0.05 separately for M09 and M10.

No rescue or motif editing after outcome association.

## Required outputs

- STATE_SUPPORT.csv
- M09_MOTIF_CENSUS_ALL.csv
- M10_SEQUENCE_CENSUS_ALL.csv
- FROZEN_M09_DICTIONARY.csv
- FROZEN_M10_DICTIONARY.csv
- MOTIF_DICTIONARY_FREEZE.json
- RUN_RECEIPT.json

The receipt must explicitly assert that outcome files were not accessed and 2015+/2023-2025/2026 remained unopened.
