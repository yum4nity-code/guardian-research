# P06 — Nasdaq-vs-SPX duration divergence conditioned by real rates

Date: 2026-09-22
Status: PRE-REGISTERED / NO COMPUTE YET

## Economic hypothesis
The future resolution of Nasdaq-vs-SPX relative-value divergence depends on the prevailing real-yield shock.

## Predeclared variants
REAL 5Y, 10Y, 30Y daily d1 × current NSX|SPX residual z; horizons 60/120/240m.

## Model
epsilon_fwd_NSX|SPX = a + b*z_divergence + c*z_real_d1 + d*(z_divergence*z_real_d1) + e. Primary coefficient: d.

## Control / incremental-information logic
NSX forward return residualized against SPX with causal rolling beta; both parent predictors included.

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
