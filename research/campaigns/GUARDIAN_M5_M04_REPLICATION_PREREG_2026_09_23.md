# GUARDIAN M5 Motion Topology — M04 2015-2017 Replication Preregistration

Date: 2026-09-23
Status: FROZEN BEFORE REPLICATION OUTCOMES

Parent discovery run:
GEFM5D-20260923-052315

Parent frozen survivor SHA256:
ba4323dabdb2e43c2a86d1ff6be53297a41847e00017f2098f328998ba195bb6

## Discovery result

291 preregistered variants were materialized.
262 passed support validity.
6 BH discoveries survived, all in M04 correlation break + recoupling.

No 2015+ outcomes were accessed by discovery.

## Frozen survivors

1. EURUSD <- UDXUSD, relation -1, L15 -> H15
2. GBPUSD <- UDXUSD, relation -1, L15 -> H15
3. GBPUSD <- UDXUSD, relation -1, L30 -> H30
4. AUDUSD <- UDXUSD, relation -1, L15 -> H15
5. AUDUSD <- UDXUSD, relation -1, L30 -> H30
6. USDCHF <- UDXUSD, relation +1, L15 -> H15

No other M01-M08 variant is eligible for replication.

## Exact M04 event definition

For the frozen economic pair:
- corr_short = rolling 12 M5 observations, minimum 8;
- corr_long = rolling 72 M5 observations, minimum 36;
- corr_break = corr_short - corr_long;
- corr_break_z = causal expanding z-score of corr_break with minimum 250 prior observations and shift 1 bar;
- within the prior 15 minutes, max(abs(corr_break_z)) >= 1.5;
- current abs(corr_break_z) < 1.0;
- current abs(corr_break_z) < abs(corr_break_z one M5 bar ago).

The M04 event mask is identical across L15/L30 for a given pair.
L only selects the frozen endpoint target.

## Replication target

Use exactly:
endpoint_score_Lm_Lm

Frozen scale mapping:
- L15 -> H15
- L30 -> H30

Positive endpoint score means normalized reversal excursion exceeds normalized continuation excursion.

## Causal continuity

Replication feature construction MUST continue from 2011 history.
Do not reset rolling correlations or expanding z-scores at 2015.

The replication cache may read market data only through 2017-12-31.
2018+ is forbidden.

A parity check against the frozen discovery V1.1 cache is mandatory for the pre-2015 corr_break object before any 2015-2017 scoring.

## Event/statistical unit

- event cooldown: 30 minutes, unchanged;
- first event after cooldown only;
- cluster inference by UTC calendar day.

## Replication gates

For each of the six frozen variants:
- >=100 independent event episodes;
- >=60 distinct UTC days;
- mean endpoint_score > 0;
- same direction as discovery;
- one-sided cluster-robust p <= 0.05.

No BH/FDR retest is added at replication because the replication rule was frozen prospectively in the parent M5 Motion Topology V1 design before discovery.

Report all six outcomes together and explicitly note their shared UDX/FX dependence.

## No rescue

Forbidden after replication output:
- alternate correlation windows;
- alternate z thresholds;
- alternate recoupling threshold;
- alternate cooldown;
- alternate L/H;
- pair substitutions;
- sign changes;
- subgroup/session filtering;
- dropping a failed year;
- using 2018+ to rescue.

## Next stage

If one or more variants pass:
freeze exact survivors and preregister 2018-2022 validation before opening it.

If none pass:
close this M04 discovery lineage.

2018-2022 remains unopened by this replication engine.
2023-2025 remains locked.
2026 remains protected.
