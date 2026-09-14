# R16-R20 Discovery Freeze — 2026-09-14

## Scope

This document freezes the discovery-stage interpretation and confirmation gates for XAUUSD R16-R20 before any confirmation data (2019-07-01 through 2024-12-31) are opened.

Discovery window:
- start: 2004-11-08
- end: 2019-06-30

Protected:
- 2025 pre-OOS remains unopened
- 2026+ remains hard sealed

All conclusions below are based only on the discovery JSON and the clustered-by-day audit.

## Discovery outcomes

### R16 — Asian range / London breakout + re-entry

Original continuation metrics are weak:
- best continuation horizon: 8 bars, naive/clustered t = +1.82

The planned false-break reversal hypothesis fails. Reversal metrics after confirmed re-entry are significantly negative:
- 1 bar: mean -7.73e-05, t = -4.00
- 2 bars: mean -1.064e-04, t = -4.07
- 4 bars: mean -1.516e-04, t = -4.38
- 8 bars: mean -1.688e-04, t = -3.50

Interpretation frozen before confirmation:
- After a London breakout of the Asian range followed by a confirmed close back inside the range within 3 M5 bars, XAUUSD historically tends to move again in the original breakout direction rather than continue reversing.
- This is a discovery-side inversion of the original false-break hypothesis. It may be tested in confirmation only as an explicitly relabelled phenomenon; no parameter changes are allowed.

Frozen confirmation metrics for R16:
- primary: negative `reversal_4b` (equivalently original-breakout-direction continuation from confirmed re-entry)
- secondary: negative `reversal_2b`
- sign must remain negative for both
- no threshold, re-entry window, range definition, session window, or horizon may be altered

### R17 — COMEX open

No convincing pre-open-direction continuation or reversal phenomenon:
- all continuation/reversal |t| <= 1.13

A raw unconditional post-open drift appears at 15m:
- post_15m mean +1.1117e-04
- t = +2.88
- positive years 12 / 16

Frozen interpretation:
- The preregistered lead/lag hypothesis based on pre-15m direction fails discovery.
- The unconditional +15m post-open drift is exploratory and was not the core preregistered directional hypothesis.

Decision:
- R17 is NOT promoted as a primary confirmation survivor.
- The raw post_15m drift may be reported descriptively in confirmation but cannot be treated as a promoted edge candidate without a separate preregistered study.

### R18 — Volatility shock mean reversion

Strongest discovery result.

After an M5 shock >= 2.0 trailing standard deviations, returns mean-revert:
- reversal_1b: mean +6.096e-05, day-clustered t = +13.66
- reversal_2b: mean +6.343e-05, day-clustered t = +11.01
- reversal_4b: mean +5.560e-05, day-clustered t = +7.53
- reversal_8b: mean +5.613e-05, day-clustered t = +5.67
- reversal_16b: mean +6.619e-05, day-clustered t = +4.92

Year signs:
- 1b: 12 positive / 4 negative
- 2b: 13 positive / 3 negative

Frozen confirmation hypothesis:
- XAUUSD exhibits short-horizon mean reversion after unusually large M5 returns.

Frozen primary confirmation metrics:
1. reversal_1b
2. reversal_2b

Frozen confirmation gate:
- both means > 0
- both day-clustered t > +2.0
- at least 4 of the 5 confirmation calendar years with positive mean for each primary metric

Secondary descriptive horizons:
- reversal_4b
- reversal_8b
- reversal_16b

No shock threshold, lookback, horizon, event definition, overlap handling, or sign convention may be changed before confirmation.

### R19 — Previous-day high/low proximity

Breakout-direction returns are positive:
- breakout_1b mean +7.545e-05, day-clustered t = +3.44
- breakout_2b mean +6.624e-05, day-clustered t = +2.22
- breakout_4b mean +1.335e-04, day-clustered t = +3.44
- breakout_8b mean +1.295e-04, day-clustered t = +2.67
- breakout_16b mean +1.409e-04, day-clustered t = +2.16

Year signs:
- 1b: 13 positive / 3 negative
- 2b: 12 positive / 4 negative

Frozen confirmation hypothesis:
- When XAUUSD first approaches/touches the previous UTC trading day's high or low during the frozen London/NY sessions, subsequent returns are biased through/beyond that level rather than rejecting.

Frozen primary confirmation metrics:
1. breakout_1b
2. breakout_4b

Frozen confirmation gate:
- both means > 0
- both day-clustered t > +2.0
- at least 4 of the 5 confirmation calendar years with positive mean for each primary metric

Secondary descriptive:
- breakout_2b
- breakout_8b
- breakout_16b

No proximity ATR fraction, ATR length, session definition, PDH/PDL definition, horizon, or first-event logic may be changed before confirmation.

### R20 — Round numbers

Naive t-statistics near 2 do not survive day clustering:
- continuation_1b clustered t = +1.65
- continuation_8b clustered t = +1.53
- continuation_16b clustered t = +1.44

Decision:
- FAIL discovery
- do not promote to confirmation
- no parameter rescue

## Frozen survivor set

Primary confirmation survivors:
1. R18 volatility-shock mean reversion
2. R19 previous-day high/low breakout bias

Conditional / relabelled phenomenon:
3. R16 post-reentry move in original breakout direction, using frozen existing event definition only

Not promoted:
- R17 preregistered COMEX lead/lag hypothesis
- R20 round-number hypothesis

## Confirmation doctrine

Confirmation window is frozen:
- 2019-07-01 through 2024-12-31

Before confirmation:
- no parameter changes
- no threshold searches
- no new horizons
- no session tweaks
- no event-filter optimization
- no P&L optimization
- no 2025 inspection
- no 2026 inspection

Confirmation must be run with the same v1.00 event extractor and clustered audit methodology.

Failure in confirmation ends that phenomenon in this branch of research. A failed candidate may inspire a new separately preregistered study, but may not be rescued by modifying the frozen study.
