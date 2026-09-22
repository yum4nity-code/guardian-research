# P04 — Oil -> CAD transmission beyond the dollar

Date: 2026-09-22
Status: PRE-REGISTERED / NO COMPUTE YET

## Economic hypothesis
An oil shock predicts the component of USDCAD that is not explained by the broad USD factor.

## Predeclared variants
WTI and Brent 60m shock z; horizons 60/120/240m.

## Model
epsilon_fwd_USDCAD|UDX = a + b*z_oil60 + e, evaluated only at |z_oil60|>=1.5 events with 240m cooldown. Primary coefficient: b.

## Control / incremental-information logic
USDCAD target residualized against UDX using causal rolling beta.

## Statistical unit
distinct oil-shock events, clustered by UTC day

## Predeclared discovery-test count
6

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
