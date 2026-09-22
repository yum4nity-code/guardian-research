# GUARDIAN M5 Motion Topology Factory V1.1 — Tradability Infrastructure Amendment

Date: 2026-09-22
Status: FROZEN BEFORE ANY ALPHA TEST

## Why this amendment exists

The V1 cache integrity audit passed OHLC integrity, endpoint-target sanity and cross-feature support, but failed the tradability-session-shape audit.

The original rule required each 5-minute UTC minute-of-week slot to be present in >=95% of 2012-2014 source observations. That produced implausibly fragmented masks for UDXUSD, SPXUSD, NSXUSD and BCOUSD.

Examples from the V1 audit:
- SPXUSD: 28.58 h/week in 12 fragments;
- UDXUSD: 71.00 h/week in 13 fragments;
- NSXUSD: 84.25 h/week in 10 fragments.

This is treated as an infrastructure problem caused by combining fixed UTC slots with historical session/DST/source-coverage variation.

No alpha test, edge trial or feature/outcome association has yet been run.

## Replacement tradability rule

V1.1 uses observed historical continuity rather than a frozen UTC minute-of-week schedule.

For each market independently:
1. a 5-minute bar is source-present iff its M5 close is finite;
2. each transition from present -> absent is a close/gap boundary;
3. each transition from absent -> present is a reopen/recovery boundary;
4. remove the final 30 minutes of finite bars before every close/gap boundary;
5. remove the first 30 minutes of finite bars after every reopen/recovery boundary;
6. missing bars themselves are never tradable;
7. all target windows additionally require complete tradability throughout both the past lookback and forward target horizon;
8. pair/group observations require all involved markets tradable at the decision timestamp.

This intentionally treats unexplained source gaps conservatively as non-tradable boundaries.

## Why this is causally acceptable

The mask is an eligibility filter, not a predictor.
It uses only contemporaneous/historical source presence to decide whether a decision timestamp belongs to a continuous observed trading run.
For target eligibility, future continuity is used only to determine whether the target can be measured; it is never exposed as a predictive feature.

## Live FTMO mapping

Historical continuity is a research-quality proxy, not an assertion of current FTMO hours.
Before shadow/live use, frozen signals must be mapped to the current FTMO symbol-specific trading schedule and maintenance/holiday updates.

## Everything else remains frozen

Unchanged:
- universe;
- M5 frequency;
- endpoint-score definition;
- 15/30/60m lookbacks;
- 15/30/60m forward horizons;
- intra/inter-asset state primitives;
- economic graph;
- temporal firewall;
- M01-M12 phenomenon definitions;
- statistical gates.

Temporal firewall remains:
- warm-up: 2011
- discovery: 2012-2014
- replication: 2015-2017
- validation: 2018-2022
- locked OOS: 2023-2025
- protected: 2026

The first V1.1 builder still refuses all 2015+ outcomes.
