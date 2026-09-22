# P01 — Real-yield + USD pressure on gold

Date: 2026-09-22
Status: PRE-REGISTERED / NO COMPUTE YET

## Economic hypothesis
Changes in US real yields alter the effect of a contemporaneous USD move on future gold returns after removing the common USD component from gold.

## Predeclared variants
REAL 5Y, 10Y, 30Y daily d1 × current UDX 60m causal z; horizons 60/120/240m.

## Model
epsilon_fwd_XAU|UDX = a + b*z_real_d1 + c*z_UDX60 + d*(z_real_d1*z_UDX60) + e. Primary coefficient: d.

## Control / incremental-information logic
USD component removed from the target through rolling beta; parents remain in the regression.

## Statistical unit
top-of-hour non-overlapping decisions, clustered by UTC day

## Predeclared discovery-test count
9

## Common gates
This lineage inherits **GEF_BATCH_A_COMMON_PROTOCOL_2026_09_22.md** without modification.

Discovery:
2010-2012.

Temporal holdout:
2013.

2014+:
forbidden in the discovery engine.

2023-2025:
not available for design/selection of this new lineage.

2026:
forbidden.

No threshold, lookback, sign, market, horizon or parent-control substitution may be introduced after seeing results without creating a new lineage.
