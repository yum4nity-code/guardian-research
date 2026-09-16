# R32 — R6B-347 causal regime autopsy — 2026-09-16

## Goal

Identify whether the historically weak R6B-347 long-breakout rule becomes an economically useful conditional edge inside a simple market regime that is observable before each trade.

## Frozen strategy

R6B-347 unchanged:
- XAUUSD LONG
- M5 lookback 96
- breakout buffer 0.10 ATR14
- UTC00_08
- fixed horizon 96 M5 bars
- one position at a time
- frozen E1 / STRESS costs

## Source

Reuse completed R30 yearly Dukascopy XAUUSD M1/M5 files from the pinned R15 source.

No 2026 access.

## Temporal split

- development / threshold selection: 2005-01-01 through 2017-12-31
- untouched validation: 2018-01-01 through 2025-12-31

2004 is excluded because it is a partial year.

No validation-period result may influence threshold selection.

## Causal feature library

Computed at the signal timestamp from data available no later than that signal close:
- 20 data-day return
- 60 data-day return
- 252 data-day return
- 20-day realized M5 volatility
- 60-day realized M5 volatility
- 20-day directional efficiency
- distance to prior 252-day high
- ATR14 / price
- breakout margin in ATR units

No outcome, future bar, trade PnL or later calendar-year information enters a feature.

## First-pass search

Univariate filters only.

For each feature:
- development quantiles 20/30/40/50/60/70/80%
- retain >= threshold or <= threshold
- at least 150 development trades
- at least 80 validation trades

Candidates are ranked on development E1 ending capital, with STRESS retained for inspection.

Only the development top 20 are then inspected on validation.

A validation survivor is reported when:
- validation E1 ending capital > 10,000
- validation STRESS ending capital > 10,000
- validation E1 expectancy_bps > 0

This is an exploratory causal regime scan, not final independent proof. Any survivor must be frozen and rerun in a later study without threshold changes.

## Prohibitions

- no multi-feature combinations in R32
- no R6 parameter changes
- no post-validation rescue threshold
- no R27 inclusion
- no 2026 access
- no live deployment
