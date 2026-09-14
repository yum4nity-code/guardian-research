# R21-R25 XAUUSD phenomenon batch — preregistration 2026-09-14

Purpose: continue XAUUSD phenomenon discovery using the existing Dukascopy M1 master cache / derived M5 data while the FTMO live quote observer independently measures execution costs for R18.

## Data doctrine

- Historical discovery data are Dukascopy XAUUSD OHLC, not true historical tick-by-tick quotes.
- Use the frozen independent stage boundaries already used in R16-R20:
  - discovery: through 2019-06-30
  - confirmation: 2019-07-01 through 2024-12-31
  - pre-OOS: 2025 only after a phenomenon survives confirmation and economic review
  - protected: 2026+, hard sealed for historical-performance testing
- No parameter rescue after results are viewed.
- No P&L optimisation during phenomenon discovery.
- M1 may be used where event timing needs finer granularity; M5 may be used where the phenomenon is naturally bar-based.

## R21 — COMEX 15-minute unconditional drift

Reason: R17 discovery showed an exploratory unconditional post-COMEX 15-minute drift while the preregistered pre-open-conditioned continuation/reversal hypothesis failed. R17 confirmation was not opened, so this is frozen as a separate relabelled phenomenon before independent confirmation.

Frozen definition:
- anchor: 08:20 America/New_York, DST-aware
- response: raw XAUUSD return from the 08:20 M5 close anchor to 15 minutes later, using the same causal M5 convention as R17
- primary metric: post_15m mean > 0
- confirmation requirement: positive mean and day-clustered t > +2.0
- yearly stability reported descriptively; no malformed fixed-year-count rule
- 30/60/120 minute post-open returns are descriptive only and may not replace a failed 15-minute primary metric
- no direction, weekday, news, volatility or session sub-filtering

## R22 — volatility compression -> expansion

Hypothesis: unusually low recent realised intraday range/volatility precedes larger subsequent absolute movement.

Frozen M5 definition:
- trailing window: 48 contiguous M5 bars
- compression statistic: realised close-to-close return standard deviation over the prior 48 bars
- normalisation: compare prior-48 stdev with the trailing 20 trading-day distribution of the same statistic available strictly before the event
- preregistered compression states: bottom 10% and bottom 20% percentile; bottom 10% is primary, bottom 20% secondary
- event sampling: first qualifying event per UTC hour to reduce mechanical overlap
- responses: absolute forward close-to-close return over 1/2/4/8/16 bars
- primary horizons: 4b and 8b
- primary comparison: compressed-event absolute forward return minus unconditional same-clock baseline from the same discovery stage
- confirmation requires positive effect for both 4b and 8b with day-clustered t > +2.0
- no post-result percentile/horizon/session tuning

## R23 — Asia/overnight move -> New York continuation or reversal

Hypothesis: the completed Asia/European pre-NY move contains information about the first two hours after COMEX open.

Frozen definition:
- timezone: America/New_York for event anchor, Europe/London only where needed for DST-safe session construction
- pre-NY reference move: return from 00:00 UTC to 08:20 New York local opening anchor
- direction = sign of that pre-NY return
- responses after 08:20 NY: 15/30/60/120 minutes
- signed continuation = direction * post return
- signed reversal = -direction * post return
- primary horizons: 30m and 60m
- discovery compares continuation and reversal symmetrically; whichever sign is stronger may be frozen only before confirmation is opened
- no magnitude buckets or weekday/session filters in the current batch

## R24 — COMEX opening-range breakout

Hypothesis: a break of the first 15-minute COMEX opening range carries directional information beyond the breakout bar.

Frozen definition:
- opening range: 08:20 through 08:35 America/New_York using M5 bars
- first subsequent M5 close outside the completed range, searched through 10:00 NY
- one event per NY trading day
- direction = +1 above opening-range high, -1 below opening-range low
- responses: signed forward return 1/2/4/8/16 bars from breakout close
- primary horizons: 2b and 4b
- breakout continuation is the primary sign; inverse/reversal statistic is reported symmetrically but cannot be relabelled as success after confirmation without a new preregistration
- no breakout-distance threshold optimisation

## R25 — NY-open gap toward previous daily close

Hypothesis: distance between the 08:20 NY anchor price and the previous UTC trading-day close contains gap-fill / continuation information.

Frozen definition:
- previous close: final contiguous M5 close of the previous UTC trading day
- current anchor: 08:20 America/New_York M5 anchor close
- gap direction = sign(anchor / previous_close - 1)
- gap-fill statistic: signed movement toward previous close after anchor
- gap-continuation statistic: signed movement away from previous close
- responses: 15/30/60/120 minutes
- primary horizons: 30m and 60m
- all non-zero gaps included; no gap-size threshold in v1.00
- report crossing/fill probability descriptively, but primary test is signed return toward/away from previous close

## Multiplicity and promotion rule

This is a five-phenomenon batch. Discovery is a screening stage, not proof. For each research item:
- raw event count, day count, naive t, day-clustered t, yearly sign stability, and effect magnitude must be reported
- a discovery survivor must have a frozen primary metric/sign before confirmation is opened
- confirmation must use unchanged definitions
- economic gate comes after statistical confirmation, not before
- a fail is not rescued by changing thresholds, sessions, horizons, or labels after seeing confirmation

## R18 separation

R18 remains unchanged. The FTMO live logger is only an execution-cost measurement stream. R21-R25 do not use those live ticks for historical return discovery and do not alter R18's frozen parameters.
