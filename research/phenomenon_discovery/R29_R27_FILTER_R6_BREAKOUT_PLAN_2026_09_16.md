# R29 — R27 compression-state filter × R6 XAU breakouts — preregistration 2026-09-16

## Purpose

Test whether the statistically confirmed R27 low-volatility regime is useful as
a veto/filter for the existing frozen XAUUSD breakout candidates R6B-347 and
R6B-307.

This is an interaction/filter diagnostic. It does not change either R6 entry or
exit rule.

## Selection / independence disclosure

R6B-347 and R6B-307 were selected after observing their 2024 discovery and 2025
confirmation performance.

Therefore any R29 analysis on those same 2024-2025 canonical files is
post-selection and cannot be called independent validation.

A PASS in R29 means only:
- the interaction is strong enough to retain as a prospective filter candidate;
- a later forward/shadow A/B test is justified.

A PASS does NOT authorize adding the veto to Guardian production.

## Frozen R6 candidates

### R6B-347 — primary
- direction LONG
- lookback 96 M5 bars
- breakout buffer 0.10 ATR14
- signal session UTC 00:00-08:00
- fixed holding horizon 96 M5 bars
- canonical chronological one-position replay
- first raw-M1 open at/after signal-bar close
- frozen E1 and STRESS cost profiles

### R6B-307 — replication
- direction LONG
- lookback 96 M5 bars
- breakout buffer 0.00 ATR14
- signal session UTC 00:00-08:00
- fixed holding horizon 48 M5 bars
- same execution/cost semantics

No R6 parameter may change.

## Canonical data

Reuse exactly the R6 Phase I-B files:
- xauusd_m5_2024_2025_news_clean.csv
  SHA256 972ecaf6c3cadf7136363f396d7a29e7a6246646b575fad5c3e677036004b503
- xauusd_m1_2024_2025_raw.csv
  SHA256 f98a395961b27ca9dcb34cffa4ef8dd93720adb70292abf7bc96108667232445

Allowed years:
- 2024
- 2025

Any 2026+ row is a hard failure.

## R27-compatible active state

R27 itself used first qualifying event per UTC hour/state for statistical event
sampling.

A live filter needs a state at the exact R6 signal bar, so R29 preregisters a
new "R27-compatible active bottom10 state" without hourly thinning.

For every M5 bar:
1. compute close-to-close returns only across contiguous 300-second bars;
2. compute sample stdev of the previous 48 contiguous M5 returns;
3. current-bar return is excluded;
4. build the comparison distribution from the previous up to 20 available UTC
   data days in the same calendar-year slice;
5. current day is excluded;
6. nearest-rank 10th percentile exactly matches R22/R27;
7. active_bottom10 = stdev48 <= q10.

If the previous 48 returns are not contiguous or no prior-day distribution
exists, state is unavailable.

There is:
- no bottom20;
- no hourly first-event thinning;
- no session-specific percentile;
- no magnitude threshold;
- no news/weekday/direction conditioning.

The removal of hourly thinning is explicitly a new R29 filter mapping and is not
claimed as already validated by R27.

## Year isolation

R6 replay and R29 state construction are performed separately in:
- 2024
- 2025

No state history crosses the calendar-year boundary.

This preserves the existing R6 year-isolation semantics.

## Trade classification

Each exact canonical R6 executable trade is labeled from its original R6 signal
index as one of:
- ACTIVE_BOTTOM10
- NOT_BOTTOM10
- STATE_UNAVAILABLE

No trade is removed before classification.

Primary comparison excludes STATE_UNAVAILABLE from the bottom10-vs-nonbottom
difference, but all original strategy metrics and state-availability counts are
reported.

## Primary estimand

For each candidate and cost profile:

interaction_difference =
    mean net PnL per ACTIVE_BOTTOM10 trade
    - mean net PnL per NOT_BOTTOM10 trade

Negative values mean R27-compatible compression is associated with worse R6
trade quality and therefore supports a prospective veto.

Primary profile:
- E1

Stress replication:
- STRESS

## Bootstrap inference

For pooled 2024+2025 trades, perform a deterministic calendar-day block
bootstrap of interaction_difference.

- resample calendar days with replacement;
- retain all trades from each sampled day;
- 5,000 resamples;
- fixed seed 20260916 plus candidate-specific deterministic hash;
- a replicate lacking either stratum is invalid;
- require at least 4,750 valid replicates;
- report percentile 95% interval.

This bootstrap is descriptive interaction evidence, not independent validation.

## Frozen FILTER_LEAD gate

R29 returns FILTER_LEAD only if ALL conditions hold:

1. state availability >= 90% for R6B-347 in 2024 and 2025;
2. state availability >= 90% for R6B-307 in 2024 and 2025;
3. each candidate has at least 12 ACTIVE_BOTTOM10 trades pooled across 2024+2025;
4. R6B-347 E1 interaction_difference < 0 in 2024;
5. R6B-347 E1 interaction_difference < 0 in 2025;
6. R6B-347 pooled E1 interaction_difference < 0;
7. R6B-347 pooled E1 95% bootstrap upper bound < 0;
8. R6B-307 pooled E1 interaction_difference < 0;
9. R6B-307 pooled STRESS interaction_difference < 0;
10. R6B-347 pooled STRESS interaction_difference < 0.

If any condition fails:
- R29 closes as NO_FILTER_LEAD;
- no q20, lag, alternate lookback, alternate session or candidate substitution.

## Secondary outputs

Report for each candidate/year/pooled:
- original trade count;
- state-available count;
- active-bottom10 count/share;
- E1 and STRESS expectancy/PF/net/win rate by state;
- full original metrics;
- hypothetical veto-retained metrics excluding ACTIVE_BOTTOM10;
- net/expectancy/PF change from applying the hypothetical veto.

These are descriptive and cannot override the frozen gate.

## Interpretation

FILTER_LEAD:
- supports a future prospective shadow A/B test of R6 with vs without the veto;
- does not authorize production, protected-OOS reuse, or retuning.

NO_FILTER_LEAD:
- R27 remains a confirmed volatility-regime phenomenon;
- it is not useful under this frozen R6 filter mapping.

## Prohibitions

- no 2026 access
- no bottom20 rescue
- no threshold tuning
- no grace window before/after the signal
- no alternate state persistence window
- no R6 parameter changes
- no SL/TP changes
- no PnL optimization
- no Guardian/live modification
