# P08 — Synthetic USD breadth vs UDX divergence

Date: 2026-09-22
Status: PRE-REGISTERED / NO COMPUTE YET

## Economic hypothesis
A divergence between UDX and a predeclared equal-weight synthetic USD breadth factor contains information about subsequent dollar/metals repricing.

## Predeclared variants
one 60m breadth-divergence object; targets UDX/XAU/XAG at 60m and 120m.

## Model
y_fwd = a + b*z_divergence + e at |z_divergence|>=1.5 with 240m cooldown. Primary coefficient: b.

## Control / incremental-information logic
synthetic USD = mean[-EURUSD,-GBPUSD,-AUDUSD,+USDJPY,+USDCHF,+USDCAD] using each pair's 60m return causally standardized before averaging; divergence=z_UDX60 - z_synthetic.

## Statistical unit
distinct breadth-divergence events, clustered by UTC day

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
