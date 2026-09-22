# P12 — CFTC crowding x own-price shock

Date: 2026-09-22
Status: PRE-REGISTERED / NO COMPUTE YET

## Economic hypothesis
The continuation/reversal of a large own-market price shock depends on noncommercial futures crowding.

## Predeclared variants
11 mapped CFTC markets × horizons 60/120/240m; fixed noncomm_net_pct_oi_z52 and own-price 60m causal shock z.

## Model
r_fwd = a + b*z_crowding + c*z_price_shock + d*(z_crowding*z_price_shock) + e. Evaluate only |z_price_shock|>=1.5 events with 240m cooldown. Primary coefficient: d.

## Control / incremental-information logic
both parent terms included; no carried 5m row counts as an independent positioning observation.

## Statistical unit
distinct price-shock events; inference clustered by CFTC state/report instance

## Predeclared discovery-test count
33

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
