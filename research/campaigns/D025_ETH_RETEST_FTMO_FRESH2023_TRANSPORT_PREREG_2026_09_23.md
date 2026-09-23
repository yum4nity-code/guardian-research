# D025 ETH RETEST +2R — FTMO Fresh-2023 / Transport-2024-2025

Date: 2026-09-23
Status: FROZEN BEFORE FTMO 2023 OUTCOME

## Why this is next

The preserved D025 branch is:
- symbol: ETHUSD
- validation path: RETEST
- frozen D025 V0 entry state machine
- frozen structural stop = sweep/cascade/reclaim extreme + 0.10 H1 ATR buffer
- diagnostic fixed target = +2R

Existing non-fresh evidence:
- 2024 RETEST EV2 about +0.084R
- 2025 RETEST EV2 about +0.109R
- Jun-Jul 2026 RETEST EV2 about +0.588R
- pooled descriptive 704 trades, EV2 about +0.133R before full execution costs

The original FundedNext lineage has unresolved historical tick-volume/feed provenance. Therefore this test does not try to force population parity. It asks whether the exact frozen state machine produces a similar RETEST +2R effect on the intended FTMO feed.

## Stage / evidence labels

FTMO 2023:
- treated as the fresh temporal test for this frozen branch, provided usable historical data exist;
- this date was not part of the documented D025 2024-2026 branch-selection evidence.

FTMO 2024-2025:
- feed-transport / replication diagnostic only;
- not independent alpha confirmation because those years informed the branch.

2026:
- hard blocked.

## Frozen signal

Use unmodified D025 LER VirtualPath 1.03 state logic from:
research/ea/D025_LER_VirtualPath_1_03.mq5

No threshold changes:
- H1 ATR(14)
- eight objective level families
- fresh sweep >=0.10 ATR
- cascade range shock >=1.25
- directional body >=0.15 ATR
- relative tick volume >=1.25
- exhaustion progress <=0.25 cascade range
- activity >=0.70 cascade volume
- reclaim within 4 M15 bars
- RETEST within 0.15 ATR and close on reclaimed side
- structural stop +0.10 ATR beyond adverse extreme

Only validation_path == RETEST is evaluated for this branch.

## Endpoint

Fixed first-touch comparison:
- target = +2R
- stop = original structural -1R
- horizon telemetry = 48h
- same-M1 target/stop ambiguity is excluded
- unresolved 48h events are reported and excluded from the resolved first-touch EV, matching the historical D025 diagnostic convention

EV2 = mean(+2R target-first, -1R stop-first) over resolved non-ambiguous events.

## Tester

- exact currently connected FTMO terminal/account context
- ETHUSD alias resolved from that terminal
- 2023-01-01 through 2025-12-31
- M1 chart
- 1 minute OHLC model for the first stage

Reason: D025 decisions use closed M15/H1/H4 state plus M1 first-touch telemetry. A prior controlled D025 run found that switching Every Tick to real-ticks did not change the observed signal/path population on the old feed. If the FTMO result survives, exact real-tick BID/ASK execution is a later production-readiness stage.

## Fresh-2023 V2 label

For resolved RETEST events:
- NEGATIVE if EV2 <= 0
- SPARSE_POSITIVE if EV2 > 0 but resolved n < 50
- POSITIVE_CONFIRMED if resolved n >= 50, EV2 > 0 and month-block bootstrap q10 > 0
- POSITIVE_UNCERTAIN otherwise when EV2 > 0

2024-2025 is reported separately as transport evidence.

## Costs / execution

The VirtualPath engine uses ASK entry for LONG and BID entry for SHORT.
The fixed path result is not yet a complete historical commission/slippage/ask-side-short-stop simulation.

The harness logs historical signal-time spread/risk telemetry.
Report a conservative one-spread payoff stress for SHORT as a diagnostic only.
Do not call this production-ready without a later exact real-tick BID/ASK + commission audit.

## Firewalls

- 2026: BLOCKED
- no path change
- no target sweep
- no threshold tuning
- no side selection after seeing outcome
- no alternate market rescue
