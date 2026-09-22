# GEF V101.2 canonical-rates anchor patch — 2026-09-22

## Failure observed

V101.1 correctly passed discovery and froze the candidate set, but the 2010-2013 reconstruction parity gate failed for selected `rates_yields_*` states.

This is an infrastructure/provenance failure. No replication score was accepted and the engine stopped before validation.

## Root cause

V85 did not consume rates rebuilt ad hoc from the raw Treasury XML. It consumed the repaired **V83B slow causal matrix**.

V101.1 rebuilt the same conceptual Treasury features from source XML. Small provenance/normalization differences were therefore sufficient to produce state-mask mismatches, despite the temporal logic being causal.

## V101.2 correction

For each selected `rates_yields_*` feature:

1. rebuild the rates series causally through the requested replication/validation end date;
2. require the reconstructed hourly grid prefix to exactly match the canonical V83B index;
3. replace the 2010-2013 prefix with the exact feature values stored in the canonical repaired V83B matrix;
4. use reconstructed values only after the V83B history ends;
5. compute expanding shifted states across the stitched series;
6. still require exact V85 state-mask parity before any replication score is accepted.

This is not retuning. Candidate identities, thresholds, directions, targets, FDR rule, temporal windows and validation gates are unchanged.

2023-2025 and 2026 remain forbidden.