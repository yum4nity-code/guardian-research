# D026 Price Exhaustion Reclaim V0 — locked rules

Date: 2026-09-04
Status: LOCKED BEFORE ANY D026 RESULT / RESEARCH ONLY / NO LIVE ORDERS

## Purpose

D026 is a NEW strategy research branch, not a repair or retuning of D025.

The aim is to test whether the structural idea behind liquidity-exhaustion/reclaim can produce a large, repeatable edge using **price/time/ATR only**, with no broker tick-volume dependency and no Binance/Bybit dependency in the baseline.

These rules are frozen before any D026 backtest outcome is inspected. If they fail, V0 fails. Historical results must not be used to edit this file.

## Initial scope

Primary research symbols:
- BTCUSD
- ETHUSD

Timeframes:
- H4: confirmed structural levels only.
- H1: confirmed structural levels + ATR(14).
- M15: full event state machine.
- M1: post-signal path measurement only.

No real trading functions are permitted in the V0 diagnostic EA.

## Objective levels

Same objective level families as D025 so the new experiment changes the impulse/exhaustion definition rather than the market map:

1. Previous Day High (PDH)
2. Previous Day Low (PDL)
3. Previous Week High (PWH)
4. Previous Week Low (PWL)
5. Latest confirmed H1 swing high
6. Latest confirmed H1 swing low
7. Latest confirmed H4 swing high
8. Latest confirmed H4 swing low

Confirmed swing = 2-left / 2-right pivot on CLOSED bars.

Low levels are observed for LONG reclaim candidates; high levels for SHORT candidates.

Round numbers remain excluded from V0.

## Fixed V0 thresholds

All values below are frozen before results:

### Level / sweep
- Watch distance: `0.50 x H1 ATR(14)`.
- Minimum fresh sweep depth: `0.10 x H1 ATR(14)`.
- Structural stop buffer: `0.10 x H1 ATR(14)` beyond the most adverse sequence extreme.

### Price-only displacement (replaces D025 CASCADE volume requirement)
A valid displacement bar must satisfy ALL of:

1. **Range shock**: M15 high-low >= `1.25 x` mean range of the preceding 20 CLOSED M15 bars.
2. **Directional body**: body in the sweep direction >= `0.20 x H1 ATR(14)`.
3. **Body efficiency**: absolute body / M15 range >= `0.55`.
4. **Close location**:
   - LONG reclaim candidate (bearish displacement): close is in the bottom `30%` of the M15 range.
   - SHORT reclaim candidate (bullish displacement): close is in the top `30%` of the M15 range.

No tick volume, real volume, OI, funding or liquidation metric is allowed in this state.

### Price-only exhaustion
Exhaustion must appear within the next 3 CLOSED M15 bars after displacement. A candidate exhaustion bar must satisfy BOTH:

1. additional outward progress beyond the most adverse extreme observed since displacement <= `0.20 x displacement-bar range`;
2. current M15 range <= `0.80 x displacement-bar range`.

This definition tests loss of price progress plus range contraction. It deliberately does not use volume.

### Reclaim / validation
- Reclaim deadline: within next 4 CLOSED M15 bars after exhaustion.
- LONG reclaim: M15 close > swept level.
- SHORT reclaim: M15 close < swept level.
- Retest proximity: `0.15 x H1 ATR(14)` around swept level while closing on reclaimed side.
- Acceptance alternative: two consecutive CLOSED M15 closes on reclaimed side.
- Validation deadline after reclaim: next 4 CLOSED M15 bars.
- Level-family cooldown after valid or failed sequence: 4 hours.

## Fresh-sweep rule

A sequence starts only from a fresh crossing:

LONG candidate:
- prior CLOSED M15 close >= level;
- new CLOSED M15 low <= level - `0.10 ATR`.

SHORT candidate:
- prior CLOSED M15 close <= level;
- new CLOSED M15 high >= level + `0.10 ATR`.

This prevents repeatedly labelling a market already living beyond the level as a new sweep.

## State machine

`IDLE -> LEVEL_WATCH -> SWEEP -> DISPLACEMENT -> EXHAUSTION -> RECLAIM -> RETEST/ACCEPTANCE -> VALID_SIGNAL`

### SWEEP -> DISPLACEMENT

The displacement bar may be the sweep bar itself. Otherwise it must occur within the next 2 CLOSED M15 bars.

Direction:
- LONG reclaim candidate: displacement bar bearish.
- SHORT reclaim candidate: displacement bar bullish.

All four frozen price-only displacement conditions must pass.

### DISPLACEMENT -> EXHAUSTION

Within next 3 CLOSED M15 bars, track the most adverse extreme and the extra outward progress. Exhaustion is confirmed on the first bar meeting both frozen price-only exhaustion conditions.

### EXHAUSTION -> RECLAIM

Within next 4 CLOSED M15 bars:
- LONG: close > swept level.
- SHORT: close < swept level.

### RECLAIM -> VALID_SIGNAL

Within next 4 CLOSED M15 bars either:

A. RETEST
- LONG: bar trades within `0.15 ATR` of level and closes > level.
- SHORT: bar trades within `0.15 ATR` of level and closes < level.

or

B. ACCEPTANCE
- two consecutive CLOSED M15 bars close on reclaimed side.

First valid path creates the signal.

## Virtual entry / risk

At VALID_SIGNAL:
- virtual entry = validating CLOSED M15 close;
- LONG SL = worst sequence low - `0.10 x H1 ATR`;
- SHORT SL = worst sequence high + `0.10 x H1 ATR`;
- `1R = abs(entry - SL)`.

Reject observation if risk <= 0 or < 5 symbol points.

No TP is part of the entry definition. No live order is sent.

## Post-signal diagnostic

Using CLOSED M1 bars for 48 hours, record:
- MFE / MAE in R;
- first +0.5R;
- first +1R / +2R / +3R / +4R / +5R;
- first structural-SL touch;
- first return to entry after +1R;
- same-M1 ambiguity for target/SL and target/BE ordering;
- 1h / 4h / 8h / 24h / 48h snapshots.

Same-M1 ordering must never be resolved optimistically.

## Mandatory event telemetry

For every transition, log at least:
- session/event id and timestamp;
- symbol / side / level family / level;
- H1 ATR;
- sweep depth ATR;
- displacement range ratio vs preceding-20 mean;
- directional body in H1 ATR;
- body/range efficiency;
- close-location fraction;
- displacement range;
- exhaustion extra-progress/displacement-range;
- exhaustion range/displacement-range;
- reclaim delay;
- path RETEST/ACCEPTANCE;
- entry / SL / risk.

## Explicit exclusions

D026 V0 must NOT use:
- tick volume;
- broker real volume;
- Binance/Bybit data;
- OI/funding/liquidations;
- RSI/EMA/MACD or other indicator gating;
- session filters;
- long/short asymmetry;
- symbol-specific thresholds;
- post-hoc year/regime switches.

Those can only be separate future hypotheses after V0 is judged.

## Evaluation standard

V0 is not accepted because it is merely positive.

Primary evaluation after clean BTC/ETH 2024-2025 runs:
- signal population and data integrity first;
- overall + side + path + year stability;
- fixed first-touch EV at +1R/+2R/+3R;
- partial/BE path only as a small predeclared management family;
- require a materially large pre-cost advantage, preferably >= ~+0.15R/trade and ideally ~+0.20R+ on a branch that repeats across years;
- then apply realistic spread, commissions and slippage plus cost stress before any production consideration.

No broad optimizer or threshold sweep is authorized for V0.

## Scientific lock

The thresholds above are not claimed optimal. They are deliberately simple structural starting values chosen before observing D026 results. Any revision after results must become D026 V1 or a separately named hypothesis and must not overwrite this lock.