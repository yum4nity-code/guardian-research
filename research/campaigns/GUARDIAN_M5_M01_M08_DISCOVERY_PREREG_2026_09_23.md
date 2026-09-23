# GUARDIAN M5 Motion Topology — M01-M08 Discovery Preregistration

Date: 2026-09-23
Status: FROZEN BEFORE OUTCOME ASSOCIATION

Parent cache:
M5 Motion Topology V1.1
Expected source run: GEFM5T-20260923-050308 or later V1.1-equivalent cache.

## Temporal firewall

Warm-up states: 2011
Discovery outcomes: 2012-01-01 through 2014-12-31
First discovery engine MUST NOT read any 2015+ outcome or market-state file.

Replication, if and only if discovery survivors exist:
2015-2017.

Validation, if replication survives:
2018-2022.

Locked OOS:
2023-2025.

Protected:
2026.

## Common target

Use only matched movement/forward scales:
- L15 -> H15
- L30 -> H30
- L60 -> H60

Primary outcome:
endpoint_score_Lm_Hm from the frozen V1.1 target cache.

Positive score means normalized reversal excursion exceeded normalized continuation excursion.

No TP/SL optimization is allowed in this engine.

## Common causal transforms

For each market and scale L:
move_z_L = causal expanding z of ret_Lm, min 250 prior observations, shifted 1 bar.

rv30_z = causal expanding z of rv_30m, min 250 prior observations, shifted 1 bar.

For pair objects:
residual z and correlation-break objects use the frozen causal cross-state cache.

If a family requires a z-score of a cached pair object:
causal expanding z, min 250 prior observations, shifted 1 bar.

## Event episodes

Raw event masks are evaluated only where the frozen endpoint target is finite.

First event after a 30-minute cooldown is retained.
No overlapping repeated M5 bars are counted as separate episodes.

Cluster for inference:
UTC calendar day.

Minimum discovery evidence:
- >=200 independent event episodes
- >=120 distinct UTC days

## Statistical test

For each predeclared variant:
- one-sample cluster-robust intercept test on endpoint_score at event episodes;
- directional alternative is positive endpoint_score only;
- if estimated mean <=0, one-sided p = 1;
- report N, days, mean, median and positive-score fraction.

Multiple testing:
BH-FDR q<=0.05 separately inside each M-family.

Only BH survivors are frozen for 2015-2017 replication.

No rescue:
no threshold, scale, pair, direction, cooldown or gate may be changed after seeing discovery output.

## Frozen directed economic graph

Each edge is target <- peer, with relation sign converting peer direction into target-equivalent direction.

1. XAUUSD <- XAGUSD, +1
2. XAUUSD <- UDXUSD, -1
3. XAGUSD <- UDXUSD, -1
4. USDCAD <- WTIUSD, -1
5. USDCAD <- BCOUSD, -1
6. WTIUSD <- BCOUSD, +1
7. NSXUSD <- SPXUSD, +1
8. EURUSD <- UDXUSD, -1
9. GBPUSD <- UDXUSD, -1
10. AUDUSD <- UDXUSD, -1
11. USDJPY <- UDXUSD, +1
12. USDCHF <- UDXUSD, +1
13. USDCAD <- UDXUSD, +1

## M01 — Synchronized exhaustion

For each directed edge and matched scale:
- abs(target move_z_L) >= 1.5
- abs(peer move_z_L) >= 1.0
- sign(target move_z_L) == sign(relation * peer move_z_L)
- target acceleration decelerates against established direction:
  sign(target ret_L) * target accel_5_vs_15 < 0
- peer does the same after relation adjustment:
  sign(target ret_L) * relation * peer accel_5_vs_15 < 0

Variants: 13 edges x 3 scales = 39.

## M02 — Leader stall / follower extension

For each directed edge:
- target is follower, peer is leader
- abs(target move_z_L) >= 1.5
- abs(peer move_z_L) >= 1.0
- target and relation-adjusted peer established moves have same sign
- target still extends:
  sign(target ret_5m) == sign(target ret_L)
- leader has stalled/turned:
  sign(relation * peer ret_5m) != sign(target ret_L)

Variants: 39.

## M03 — Residual extreme + recross

For each directed edge:
- use target-on-relation-adjusted-peer causal rolling-beta residual;
- within prior 15m, max abs(residual_z) >= 1.5;
- current abs(residual_z) < 1.0;
- current abs(residual_z) < abs(residual_z one bar ago).

This is a return toward equilibrium after a recent residual extreme.

Variants: 39.

## M04 — Correlation break + recoupling

For each directed edge:
- use cached short-minus-long correlation break for the unordered economic pair;
- causal z of correlation break;
- within prior 15m, max abs(corr_break_z) >= 1.5;
- current abs(corr_break_z) < 1.0;
- current abs(corr_break_z) < abs(corr_break_z one bar ago).

Variants: 39.

## M05 — Breadth divergence

For each of the 13 target markets:
- abs(target move_z_L) >= 1.5;
- if target move is positive, full-market positive breadth < 0.50;
- if target move is negative, full-market positive breadth > 0.50.

The market is stretched while the broader cross-market sign breadth fails to confirm.

Variants: 13 markets x 3 scales = 39.

## M06 — Turn cluster

Targets:
XAUUSD, XAGUSD, UDXUSD, USDCAD, WTIUSD, BCOUSD.

For each target:
- abs(target move_z_L) >= 1.0;
- define target turn precursor as sign(ret_5m) != sign(ret_15m);
- for each frozen graph neighbor, relation-adjust peer direction to target direction;
- a peer precursor is active if, within current or previous 5m bar:
  abs(peer move_z_L) >= 1.0,
  aligned established direction equals target established direction,
  and peer sign(ret_5m) != sign(peer ret_15m);
- event requires at least 2 distinct precursor markets across target + eligible neighbors inside the 10m window.

Variants: 6 targets x 3 scales = 18.

## M07 — Lead-lag turn sequence

For each directed edge:
- abs(target move_z_L) >= 1.0;
- target is still extending:
  sign(target ret_5m) == sign(target ret_L);
- relation-adjusted peer established direction matches target;
- peer generated a turn precursor at least once in t-15m, t-10m or t-5m:
  sign(peer ret_5m) != sign(peer ret_15m);
- target itself has not yet generated the same precursor at t.

One event covers the full 5-15m lead window; lag is not optimized separately.

Variants: 39.

## M08 — Volatility exhaustion

For each of 13 markets:
- abs(move_z_L) >= 1.5;
- rv30_z >= 1.0;
- frozen failure_extend_after_shock == 1.

Variants: 39.

## Total discovery family slots

M01 39
M02 39
M03 39
M04 39
M05 39
M06 18
M07 39
M08 39

TOTAL = 291 predeclared variants.

## Outputs required

DISCOVERY_ALL.csv
FAMILY_SUMMARY.csv
FROZEN_DISCOVERY_SURVIVORS.csv
DISCOVERY_FREEZE_RECEIPT.json
RUNTIME_PROVENANCE.json
RUN_RECEIPT.json

Receipt must assert:
- expected variants = 291
- 2015+ outcomes accessed = false
- 2018+ accessed = false
- 2023-2025 accessed = false
- 2026 accessed = false
