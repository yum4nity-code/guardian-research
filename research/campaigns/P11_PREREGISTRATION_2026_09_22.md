# P11 — XAU-XAG relative-value dislocation

Date: 2026-09-22
Status: PRE-REGISTERED / NO COMPUTE YET

## Economic hypothesis
An extreme XAU move relative to its causal beta on XAG predicts future convergence or continuation of the precious-metals spread.

## Predeclared variants
one XAU|XAG 60m residual-z object; horizons 60/120/240m.

## Model
epsilon_fwd_XAU|XAG = a + b*z_residual60 + e at |z_residual60|>=1.5 with 240m cooldown. Primary coefficient: b.

## Control / incremental-information logic
XAU forward return residualized against XAG with causal rolling beta. Inverse spread is not separately tested.

## Statistical unit
distinct residual-dislocation events, clustered by UTC day

## Predeclared discovery-test count
3

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
