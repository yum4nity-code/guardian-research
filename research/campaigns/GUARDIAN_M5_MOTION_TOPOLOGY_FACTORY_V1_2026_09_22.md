# GUARDIAN M5 MOTION TOPOLOGY FACTORY V1

Date: 2026-09-22
Status: DESIGN FROZEN BEFORE COMPUTE

## Objective

Find reproducible structures that precede the END of an M5 movement:
- local/high-low exhaustion;
- reversal;
- failure to extend;
- simultaneous turning across assets;
- leader/follower sequences;
- recurring inter-asset and intra-asset motifs.

This is not a generic indicator scan.

Primary question:
> What repeatable M5 state of one or several markets tends to occur just before an established move stops or reverses?

## Universe

Core price universe:
XAUUSD, XAGUSD, UDXUSD, EURUSD, GBPUSD, USDJPY, AUDUSD, USDCHF, USDCAD, SPXUSD, NSXUSD, WTIUSD, BCOUSD.

Primary frequency:
M5.

Derived horizons:
5m, 10m, 15m, 30m, 60m.

## Tradability mask

Do not learn from market-close/reopen artifacts.

For each instrument and each pair/group:
1. infer recurring minute-of-week tradability from historical source availability using discovery years only;
2. retain only recurring slots with >=95% source availability;
3. add a 30-minute exclusion buffer before and after recurring closures/reopens;
4. pair/group observations require all involved markets tradable;
5. exceptional data holes are missing data, never signals.

The historical mask is a research eligibility filter, not a predictor.

Before live/shadow deployment, map the frozen research windows to current FTMO symbol trading hours and Trading Updates.

## Outcome: movement-end topology

Avoid arbitrary 'perfect top/bottom' labels as the only target.

At every M5 decision time t and lookback L in {15m,30m,60m}:

past_move(t,L) = close_t / close_(t-L) - 1
d = sign(past_move)

For forward horizon H in {15m,30m,60m}:

continuation_excursion = max over 0<k<=H of d * return(t -> t+k)
reversal_excursion = max over 0<k<=H of -d * return(t -> t+k)

endpoint_score = reversal_excursion - continuation_excursion

Normalize excursions by causal prior M5 realized volatility.

Interpretation:
- strongly positive endpoint_score = movement ended / reversed;
- strongly negative = movement continued;
- near zero = ambiguous.

Secondary labels:
- TOP candidate when d>0 and endpoint_score>0;
- BOTTOM candidate when d<0 and endpoint_score>0.

Predictors are strictly t-or-earlier. Future path is used only for the target.

## State primitives

### Intra-asset
Per market, causally measured:
- returns 5/10/15/30/60m;
- acceleration/deceleration: r5 vs r15/r30;
- realized vol 15/30/60m;
- range expansion/compression;
- distance to rolling 30/60m high and low;
- path efficiency / straightness;
- consecutive same-direction bars;
- wick/body proxies if OHLC is available from raw M1 aggregation;
- failure-to-extend after a shock;
- shock z-score;
- distance from causal rolling beta residual extrema.

### Inter-asset
- same-time return sign agreement;
- standardized breadth;
- shock breadth;
- dispersion;
- economically directed rolling-beta residuals;
- short-vs-long rolling correlation break;
- leader/follower lagged returns at 5/10/15m;
- pair spread / residual crossing zero;
- simultaneous residual extremes;
- one asset turns while a linked asset continues;
- common turning clusters.

## Frozen economic / structural relations

Do not Cartesian-mine every possible pair first.

Primary graph:
- XAU <-> XAG
- XAU <-> UDX
- XAG <-> UDX
- USDCAD <-> WTI
- USDCAD <-> BCO
- WTI <-> BCO
- NSX <-> SPX
- UDX <-> EURUSD
- UDX <-> GBPUSD
- UDX <-> AUDUSD
- UDX <-> USDJPY
- UDX <-> USDCHF
- UDX <-> USDCAD

Cross-market breadth can use the full 13-market state.

## Phenomenon families

M01 SYNCHRONIZED EXHAUSTION
Several linked markets experience a same-direction standardized shock, then breadth/acceleration decays. Test whether endpoint probability rises.

M02 LEADER STALL / FOLLOWER EXTENSION
Leader stops extending while follower remains stretched. Test follower endpoint and convergence.

M03 RESIDUAL EXTREME + RECROSS
Rolling-beta residual reaches an extreme, then crosses toward zero. Test movement end vs continuation.

M04 CORRELATION BREAK + RECOUPLING
Short correlation departs from long correlation and begins to normalize. Test endpoints in pair members.

M05 BREADTH DIVERGENCE
A market extends while its economic peer/breadth factor stops confirming. Test endpoint score.

M06 TURN CLUSTER
Two or more linked assets produce endpoint-like precursor states inside the same 5/10m window. Test whether a third/target market turns.

M07 LEAD-LAG TURN SEQUENCE
Asset A changes sign/decelerates 5-15m before B. Test repeated directed chains, with lag and direction frozen per graph edge.

M08 VOLATILITY EXHAUSTION
Large normalized move + volatility burst + failure to extend. Intra-asset family.

M09 REPEATED STATE / MOTIF
Represent each M5 bar with a compact frozen state vector:
- own move direction/strength;
- acceleration sign;
- shock flag;
- linked-market breadth sign;
- dispersion bucket;
- residual-extreme flag;
- correlation-break flag.

Search recurring states only in the motif-discovery partition. Require a minimum occurrence count before outcome evaluation.

M10 RECURRENT SEQUENCE
Length-2 and length-3 transitions between compact states over 5-15m. Test whether the same sequence repeatedly precedes endpoints.

M11 CROSSING TOPOLOGY
Price/residual/breadth objects cross frozen causal reference levels (zero, rolling mean, residual zero) in combinations. Test endpoint association.

M12 ASYMMETRIC TOP VS BOTTOM
Test whether the same topology behaves differently after upward vs downward established moves. This is a predeclared interaction, not two separately optimized systems.

## Repetition / motif controls

No arbitrary rule explosion.

For M09-M10:
- motif dictionary is learned only in the motif-discovery partition;
- minimum 100 occurrences before any outcome test;
- identical motif representation is frozen before temporal replication;
- no adding/removing state bits after seeing outcome;
- BH-FDR inside motif family;
- report total motifs considered, not only survivors.

## Temporal firewall

Because earlier Guardian lineages have already accessed parts of pre-2023 history, this is a NEW lineage with a fresh internal split.

Warm-up: 2011
Motif / structure discovery: 2012-2014
Temporal replication: 2015-2017
Independent validation: 2018-2022
Locked OOS: 2023-2025
Protected: 2026

The first engine must stop at 2014.
No 2015+ price outcomes are opened before structures/parameters are frozen.

## Statistical unit

Do not count overlapping M5 bars as independent.

Depending on family:
- endpoint episodes separated by >=30m cooldown;
- motif episode = first occurrence after >=30m cooldown;
- cluster robust inference by UTC day;
- lead-lag sequence episode separated by >=30m;
- simultaneous turn cluster counted once per cluster.

Report both raw rows and effective independent episodes.

## First-pass gates

These are research gates, not profitability claims.

Discovery:
- >=200 independent episodes for event/motif families;
- >=120 distinct UTC days;
- BH-FDR q<=0.05 inside family;
- coefficient/effect sign frozen.

Replication 2015-2017:
- >=100 independent episodes;
- >=60 distinct days;
- same effect direction;
- one-sided p<=0.05;
- no threshold rescue.

Validation 2018-2022:
- exact frozen object;
- year-by-year effect table;
- concentration/tail checks;
- execution-aware net effect;
- negative controls / time-shift placebo.

Only after these may 2023-2025 be considered for locked OOS.

## Execution relevance

Primary outcomes should be expressible as:
- probability that current move is ending;
- expected normalized reversal excursion vs continuation excursion;
- expected time-to-turn;
- target market / direction / horizon.

Do not optimize TP/SL in the signal-discovery engine.

Execution layer comes later.

## Immediate build order

1. M5 OHLC/close causal cache + recurring tradability mask.
2. Endpoint-score target cache.
3. State-primitives cache.
4. Frozen economic graph.
5. M01-M08 deterministic tests.
6. M09-M10 motif census and freeze.
7. M11-M12 interaction tests.
8. Close/freeze discovery.
9. Only then open 2015-2017 replication.

## Relationship to existing Guardian work

This campaign directly advances previously underexplored:
- Edge family 5 cross-asset lead/lag;
- family 6 relative value/spreads;
- family 21 correlation/dispersion;
- family 22 cross-sectional relative strength;
- existing P09 consensus/disagreement and P10 correlation-break concepts.

Batch B macro P02/P03/P05/P07/P09/P10/P13/P14 is PARKED, not discarded.
P09/P10 concepts are absorbed here in M5 execution-oriented form.
