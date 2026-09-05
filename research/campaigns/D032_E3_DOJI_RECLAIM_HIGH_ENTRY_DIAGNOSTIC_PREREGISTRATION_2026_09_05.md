# D032-E3 — Bullish Doji Star H1 reclaim-high delayed-entry diagnostic

Date: 2026-09-05
Status: PREREGISTERED BEFORE RECLAIM-HIGH RESULTS ARE INSPECTED
Classification: POSTHOC_ENTRY_TIMING_DEVELOPMENT

## Purpose
The D032 Bullish Doji Star H1 entry has confirmed directional information at +24h on BTC/ETH/DOG, but immediate entry often experiences deep adverse excursion. D032-E3 tests whether waiting for a simple price-confirmation trigger improves entry quality without changing the underlying signal.

This is entry-timing development, not independent validation: historical post-signal path data have already been inspected in earlier D032 work.

## Frozen signal
Unchanged from D032-C1:
- Bullish Doji Star H1 using the same TA-Lib-default numerical definition;
- strict 144-hour SMA downtrend `MA[t-6] > ... > MA[t]`;
- `1R = 2 * sample stdev(previous 24 H1 returns)`;
- primary core = BTCUSD, ETHUSD, DOGUSD.

Transport symbols may be run for diagnostics only and do not alter the primary core verdict.

## Immediate baseline
For every accepted Doji:
- baseline entry = first executable ASK after the H1 signal closes;
- no SL, TP or trailing;
- reference exit = exact BID at original signal_end +24h.

## Frozen delayed-entry candidate
Primary candidate is **reclaim of the closed Doji H1 high**:
1. trigger level = high of the closed Doji H1 candle;
2. confirmation occurs on the first observed tick with `BID >= doji_high`;
3. fill is the contemporaneous ASK, never a synthetic fill at the trigger price;
4. trigger must occur within **6 hours** after signal_end;
5. if no trigger occurs inside 6h, the candidate takes no trade;
6. no SL, TP or trailing in this diagnostic;
7. candidate exit remains the exact BID at the **original signal_end +24h**, not 24h after the delayed fill.

The 6h confirmation window is frozen before results and is one of the source diagnostic horizons already used by D032; neighboring windows are not to replace it after results are opened.

## Why anchor exit to original +24h
The confirmed edge is tied to the source +24h signal horizon. Anchoring both baseline and delayed entry to the same endpoint isolates entry timing from a simultaneous change in holding period.

## Required diagnostics
Per event export:
- Doji OHLC and reclaim level;
- baseline fill/spread;
- whether reclaim triggered, trigger time, delay in minutes, executable ASK fill;
- baseline MFE_R/MAE_R and timestamps through +24h;
- reclaim-entry MFE_R/MAE_R and timestamps from trigger through +24h;
- exact +24h BID;
- baseline +24h bps/R;
- reclaim +24h bps/R;
- paired reclaim-minus-baseline delta bps/R;
- feed-gap flag;
- PRE2024 / POST2024 epoch label.

## Development window
Signals from 2018-07-01 through 2026-06-25 23:00 may be used for this development diagnostic. PRE2024 and POST2024 must be reported separately as robustness views as well as pooled.

Data after the bounded D032 window remain reserved for later forward/independent checking if the candidate survives development.

## Advancement gate
The 6h reclaim-high candidate advances to a separately frozen validation stage only if the BTC/ETH/DOG core satisfies all of:
1. at least 40 clean reclaim-triggered trades pooled;
2. pooled mean reclaim +24h > +0.15R/trade;
3. pooled median reclaim +24h bps > 0;
4. at least 2 of 3 core symbols have positive mean reclaim +24h R;
5. on paired reclaim-triggered events, median reclaim MAE_R is at least **0.25R less adverse** than the immediate-entry baseline median MAE_R;
6. no single event contributes more than 60% of total positive pooled reclaim +24h R.

The delayed entry is allowed to have lower raw +24h return than the immediate baseline if it materially improves adverse excursion, because the purpose is to make realistic stop-based risk sizing possible. However it must still clear the +0.15R mean gate above.

## Interpretation lock
- PASS => freeze the exact 6h reclaim-high rule and validate on untouched/future data before combining it with any SL/runner management.
- FAIL => reject reclaim-high as the entry-timing fix. Do not retune the same sample to 1h/3h/12h or to neighboring trigger levels.

## Tester
M1 chart, `1 minute OHLC` on the current FundedNext historical feed. Historical real ticks are unavailable for the older period, so any intraminute trigger result remains provisional and later real-tick/forward checking is required before production.
