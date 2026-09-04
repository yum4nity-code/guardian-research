# D025 LER V0 — locked observer rules

Date: 2026-09-04
Status: LOCKED BEFORE RESULTS / RESEARCH ONLY / NO LIVE ORDERS

This file freezes the first mechanical observer rules before any D025 outcome is inspected. V0 is intentionally simple and interpretable. Any later change must create a new version; this file is not edited to improve historical results.

## Scope

Symbols: BTCUSD, ETHUSD.

Timeframes:
- H4 context/structure only.
- H1 structure, objective levels, ATR(14).
- M15 event state machine.
- M1 only for post-signal MFE/MAE tracking.

No BUY/SELL/position modification function is permitted.

## Objective levels

Eight level families are observed per symbol:
1. Previous Day High (PDH)
2. Previous Day Low (PDL)
3. Previous Week High (PWH)
4. Previous Week Low (PWL)
5. Latest confirmed H1 swing high
6. Latest confirmed H1 swing low
7. Latest confirmed H4 swing high
8. Latest confirmed H4 swing low

A confirmed swing is a 2-left / 2-right pivot on CLOSED bars. The pivot must therefore already be mechanically confirmed before the event. Round numbers are excluded from V0.

Low levels are observed for LONG reclaim events. High levels are observed for SHORT reclaim events.

## Fixed thresholds

All thresholds below are frozen for V0:

- Watch distance: 0.50 x H1 ATR(14).
- Minimum sweep depth: 0.10 x H1 ATR(14).
- Structural stop buffer after a valid signal: 0.10 x H1 ATR(14) beyond the sweep extreme.
- Cascade range shock: current M15 range >= 1.25 x mean range of the preceding 20 CLOSED M15 bars.
- Cascade directional body: directional M15 body >= 0.15 x H1 ATR(14).
- Cascade relative tick volume: current M15 tick volume >= 1.25 x mean tick volume of preceding 20 CLOSED M15 bars.
- Exhaustion maximum new outward progress: <= 0.25 x cascade-bar range.
- Exhaustion activity floor: tick volume >= 0.70 x cascade-bar tick volume.
- Retest proximity: within 0.15 x H1 ATR(14) of the swept level while closing back on the reclaimed side.
- Cooldown after VALID_SIGNAL or failed sequence: 4 hours for that level family.

## Fresh-sweep rule

A sweep must be a fresh crossing from the pre-event side:
- LONG reclaim candidate: previous CLOSED M15 close >= level, then a CLOSED M15 low <= level - 0.10 ATR.
- SHORT reclaim candidate: previous CLOSED M15 close <= level, then a CLOSED M15 high >= level + 0.10 ATR.

This prevents a continuing trend that has already lived beyond the level from being repeatedly labelled as a new sweep.

## State machine

`IDLE -> LEVEL_WATCH -> SWEEP -> CASCADE -> EXHAUSTION -> RECLAIM -> RETEST/ACCEPTANCE -> VALID_SIGNAL`

LEVEL_WATCH is telemetry only. A valid sequence may begin directly with SWEEP if the market crosses the level between timer evaluations.

### SWEEP -> CASCADE

Cascade may be satisfied on the sweep bar itself. Otherwise it must appear within the next 2 CLOSED M15 bars.

Directional requirements:
- LONG candidate: cascade bar body is bearish.
- SHORT candidate: cascade bar body is bullish.

The fixed range-shock, body and relative-volume thresholds must all be satisfied.

### CASCADE -> EXHAUSTION

Exhaustion must appear within the next 3 CLOSED M15 bars.

For each candidate bar calculate additional progress beyond the most adverse extreme already observed since cascade. Exhaustion is marked when:
- additional outward progress <= 0.25 x cascade range; and
- tick volume remains >= 0.70 x cascade tick volume.

No external Binance/Bybit metric is allowed to trigger this state in V0.

### EXHAUSTION -> RECLAIM

Reclaim must occur within the next 4 CLOSED M15 bars:
- LONG candidate: M15 close > swept level.
- SHORT candidate: M15 close < swept level.

### RECLAIM -> RETEST / ACCEPTANCE

Within the next 4 CLOSED M15 bars, either:

A. Retest path
- LONG: low comes within 0.15 ATR above/below the level and the bar closes > level.
- SHORT: high comes within 0.15 ATR above/below the level and the bar closes < level.

or

B. Acceptance path
- two consecutive CLOSED M15 bars close on the reclaimed side of the level.

Either path creates VALID_SIGNAL.

## Virtual entry and risk unit

At VALID_SIGNAL:
- virtual entry = close of the validating M15 bar;
- LONG virtual SL = most adverse sweep/cascade/reclaim extreme - 0.10 x H1 ATR;
- SHORT virtual SL = most adverse sweep/cascade/reclaim extreme + 0.10 x H1 ATR;
- 1R = absolute(entry - virtual SL).

If 1R is non-positive or less than 5 symbol points, the observation is rejected as invalid data and no virtual trade is created.

There is no TP and no time-stop in V0.

## Post-signal measurement

Using CLOSED M1 bars after VALID_SIGNAL, record:
- MFE in R;
- MAE in R;
- first time to +1R, +2R, +3R, +4R, +5R;
- first time virtual SL is touched;
- snapshots at 1h, 4h, 8h, 24h and 48h.

The final V0 observation horizon is 48h. Touch ordering inside the same M1 candle is treated as ambiguous if both SL and a new positive-R threshold are first crossed in that candle; the event must be flagged rather than resolved optimistically.

## Logging

The observer must append immutable CSV records containing at least:
- session id;
- event id;
- UTC timestamp;
- symbol;
- level family and frozen level price;
- side;
- state transition;
- H1 ATR;
- sweep depth ATR;
- range shock;
- normalized directional body;
- relative tick volume;
- time outside level;
- time to reclaim;
- retest/acceptance path;
- entry / virtual SL / risk;
- MFE/MAE and R-hit timing data.

## External intelligence

Binance/Bybit Shared Intelligence continues collecting independently, but it DOES NOT influence the D025 V0 state machine.

Crypto+ data will be joined later by timestamp using the anti-lookahead rule `available_at <= event_time`. This preserves a clean comparison between D025 Core and enriched variants.

## Failure policy

- Missing H1 ATR or insufficient bar history: skip evaluation; log a throttled REVIEW message.
- MT5 restart may interrupt an in-flight sequence. Such sequences are not reconstructed in V0 and must be marked incomplete if detected by downstream analysis.
- Guardian production remains untouched.

## Scientific lock

The thresholds in this document are not claims that they are optimal. They are deliberately broad, mechanically justified starting values. D025 V0 is a falsification/event-study instrument, not a production strategy.
