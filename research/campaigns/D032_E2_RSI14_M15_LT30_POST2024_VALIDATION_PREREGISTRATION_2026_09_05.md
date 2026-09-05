# D032-E2 — RSI(14) M15 <30 conditional validation on Bullish Doji Star H1

Date: 2026-09-05
Status: PREREGISTERED BEFORE POST2024 RSI VALUES ARE INSPECTED
Classification: POSTHOC_ADAPTATION_CONDITIONAL_FILTER_VALIDATION

## Purpose
Validate whether the standard oversold condition RSI(14) M15 <30 identifies a stronger subset of the already-confirmed D032 Bullish Doji Star H1 setup.

This is NOT a new confirmation of the underlying Doji entry. The 2024-2026 Doji +24h outcomes were seen during D032 discovery, but RSI(14) M15 values and the conditional RSI<30 subset have not yet been inspected for POST2024.

## Frozen setup
Unchanged from D032-C1/E1:
- Bullish Doji Star H1, same TA-Lib-default numerical definition;
- 144-hour SMA strict downtrend `MA[t-6] > ... > MA[t]`;
- executable LONG entry = first ASK after signal;
- 1R = 2 * sample stdev(previous 24 H1 returns);
- primary endpoint = executable +24h return;
- no Guardian, no orders, no TP/SL/trailing in this filter-validation scanner.

## Frozen RSI condition
- Indicator: RSI(14)
- Timeframe: M15
- Price: close
- Sample: last fully closed M15 candle at H1 signal boundary
- Freshness requirement: M15 bar open must equal `signal_end - 15 minutes`. If broker/session history makes the last available M15 bar older than this, the event is tagged stale and is NOT eligible for the RSI<30 primary subset.
- Threshold: **RSI < 30.0000** exactly.
- No alternate 20/25/35/40 threshold may replace the primary threshold after results are opened.

## Validation window
POST2024 conditional-filter validation:
- first signal: 2024-01-01 00:00
- last signal: 2026-06-25 23:00

The final signal leaves 24 hours of path inside the previously bounded D032 discovery horizon ending 2026-06-26.

## Cohorts
Primary core:
- BTCUSD
- ETHUSD
- DOGUSD / DOGE CFD

Secondary frozen transport diagnostics:
- LNKUSD / LINK CFD
- XRPUSD

Transport results do not alter the core primary verdict but are used to assess whether the RSI condition transfers beyond the core.

## Primary outputs
For every Doji event in the POST2024 window record:
- exact RSI14 M15
- M15 bar timestamp and freshness flag
- RSI<30 pass/fail
- executable +24h bps and R
- pre24 MFE_R / MAE_R and timestamps
- feed-gap flag

Summary must separately report all clean Doji events and the clean fresh-M15 RSI<30 subset.

## Primary advancement criteria
RSI<30 advances only as a high-conviction conditional sleeve if the frozen BTC/ETH/DOG core subset satisfies all of:
1. >= 8 clean fresh-M15 RSI<30 core events aggregate;
2. aggregate mean executable +24h > +0.15R/event;
3. aggregate median executable +24h bps > 0;
4. at least 2 of 3 core symbols with at least 2 eligible events have positive mean +24h bps;
5. pooled RSI<30 mean +24h R exceeds the contemporaneous unfiltered clean-core mean +24h R;
6. no single event contributes >60% of the total positive pooled +24h R.

MAE is a required diagnostic but not an advancement gate because PRE2024 data did not show that RSI<30 clearly improves entry excursion. If POST2024 also fails to improve winner MAE, RSI<30 must not be presented as solving the stop-distance problem even if return criteria pass.

## Interpretation lock
- PASS => RSI<30 may be retained as a sparse high-conviction sleeve candidate; still requires cost/swap/management work and cannot be called a high-frequency challenge engine.
- FAIL => discard RSI<30 as an entry filter; do not tune neighboring thresholds on this same POST2024 interval.

## Tester
M1 chart, `1 minute OHLC` because historical real ticks are unavailable for the old FundedNext interval.
