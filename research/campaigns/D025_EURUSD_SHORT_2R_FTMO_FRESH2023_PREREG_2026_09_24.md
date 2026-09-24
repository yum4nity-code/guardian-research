# D025-EURUSD-SHORT-2R — FTMO Fresh-2023 Confirmation

Date: 2026-09-24
Status: FROZEN BEFORE FRESH-2023 OUTCOME ACCESS
Parent: D025 Liquidity Exhaustion Reclaim / VirtualPath 1.03

## Objective

Find a tradable edge, not a monitoring exercise.

This test evaluates the strongest preserved low-cost D025 branch:
- market: EURUSD
- side: SHORT only
- entry family: frozen D025 LER V0 entry state machine
- validation path: BOTH RETEST and ACCEPTANCE; path split is diagnostic only
- stop: original structural -1R
- target: +2R
- maximum observation: 48h

The branch definition comes from the already-seen 2024-2025 evidence. Therefore:
- 2023 is the fresh temporal test;
- 2024-2025 are feed-transport / replication only;
- 2026 is blocked.

No threshold, level family, path, session, target, stop or hold-period optimization is allowed.

## Frozen source implementation

Use unchanged `research/ea/D025_LER_VirtualPath_1_03.mq5` signal/state logic.

Permitted harness-only changes:
- dedicated output paths;
- disable verbose logging;
- drive closed-bar processing from OnTick in Strategy Tester;
- record contemporaneous BID/ASK spread at entry;
- write completion marker.

These do not alter signal selection.

## Main outcome

For every EURUSD SHORT signal:
- +2R first before structural -1R => +2R
- structural -1R first => -1R
- same-M1 target/stop ambiguity => exclude from resolved sample
- unresolved by 48h => unresolved, excluded from first-touch EV

Primary fresh-2023 evidence:
- resolved N
- +2R hit rate
- EV in R
- month-block bootstrap q10 and P(EV<=0)

## Cost/economic diagnostic

The virtual path uses Bid OHLC and is not exact Ask-side short execution.

Predeclared conservative diagnostic:
- entry spread R = contemporaneous (Ask-Bid) / structural risk
- FTMO Forex commission R = USD 5 round trip / (100,000 * structural risk price)
- stressed payoff R = first-touch payoff R - entry_spread_R - commission_R

This is a screening cost model, not exact tick execution.

If fresh-2023 raw EV <= 0: close branch.
If raw EV > 0 but stressed EV <= 0: preserve signal clue only; no exact-tick follow-up.
If fresh-2023 raw EV > 0 AND stressed EV > 0:
- POSITIVE_UNCERTAIN if month-cluster q10 stressed <= 0
- POSITIVE_CONFIRMED if month-cluster q10 stressed > 0
- then exact real-tick Ask-side follow-up is permitted, still without retuning.

## Firewalls

- 2026: BLOCKED
- LONG side: diagnostic only if emitted; not candidate
- path filtering: BLOCKED
- level-family filtering: BLOCKED
- session/news filtering: BLOCKED
- target/stop changes: BLOCKED
- retuning: BLOCKED
- live deployment: BLOCKED
