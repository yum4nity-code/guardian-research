# GUARDIAN M5 Motion Topology — M09/M10 Outcome Discovery Preregistration

Date: 2026-09-27  
Status: FROZEN BEFORE OUTCOME ASSOCIATION

## Parent predictor-only census

Exact run:
`GEFM5MC-20260927-100900`

Frozen dictionaries:
- M09: 6,393 motifs
- SHA256: `f4b16ed02534ada03aee9acbbcfb42c9450524c54cd17065a281aacb5b3d0e80`
- M10: 14,662 sequences
- SHA256: `5df682a7a81d02ca9e72439e8e86434ccdf6579c0f16958316853c38729e1893`

These objects were selected only by predictor frequency. No outcome file had been opened when they were frozen.

## Objective

Test whether the already-frozen recurring market configurations are associated with the end/reversal of an established M5 move.

No motif, state bit, sequence, threshold, market or scale may be added after outcome association begins.

## Temporal firewall

- causal warm-up states: 2011;
- discovery outcomes: 2012-2014 only;
- 2015+ state/outcomes forbidden in this engine;
- 2023-2025 locked OOS untouched;
- 2026 protected.

## Target

Matched scales only:
- L15 -> H15;
- L30 -> H30;
- L60 -> H60.

Outcome:
`endpoint_score_Lm_Lm` from the frozen Motion Topology V1.1 cache.

Positive endpoint score means normalized reversal excursion exceeded normalized continuation excursion.

## Episode construction

For each frozen motif/sequence:
1. require the matched endpoint target to be finite;
2. take the first occurrence after a 30-minute cooldown;
3. cluster inference by UTC calendar day.

Hard validity:
- >=200 independent episodes;
- >=120 distinct UTC days.

## Statistical test

Per frozen object:
- mean endpoint score;
- cluster-robust intercept standard error by UTC day;
- one-sided test for mean > 0;
- if mean <= 0, p_one = 1.

Multiple testing:
- BH-FDR across all valid M09 tests;
- BH-FDR separately across all valid M10 tests;
- q <= 0.05 required.

A discovery survivor must therefore satisfy:
- validity support gates;
- mean > 0;
- BH q <= 0.05.

## Diagnostics only

Also report, but do not use as discovery pass/fail gates:
- median endpoint;
- positive-score fraction;
- mean after removing best 1% of episodes;
- mean after removing best 2% of episodes;
- 2012 / 2013 / 2014 means.

These diagnostics may inform the preregistered replication design, but may not be used to rescue or alter discovery survivors.

## No rescue

After this engine opens 2012-2014 outcomes:
- do not modify the motif dictionary;
- do not alter state thresholds;
- do not substitute scales;
- do not change sequence length;
- do not add market filters;
- do not inspect 2015+ to choose a repair.

If survivors exist, freeze them exactly and build a separate 2015-2017 replication engine.

## Required outputs

- DISCOVERY_ALL.csv
- FAMILY_SUMMARY.csv
- FROZEN_DISCOVERY_SURVIVORS.csv
- DISCOVERY_FREEZE_RECEIPT.json
- RUNTIME_PROVENANCE.json
- RUN_RECEIPT.json

The receipt must explicitly state that 2015+, 2023-2025 and 2026 were not accessed.
