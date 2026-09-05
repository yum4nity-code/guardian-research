# D032-M1 — Bullish Doji Star H1 post-24h runner management

Date: 2026-09-05
Status: PREREGISTERED BEFORE >24H OUTCOMES ARE INSPECTED
Classification: MANAGEMENT_DEVELOPMENT_POST24_PREREGISTERED

## Purpose
Develop management for the already confirmed D032 Bullish Doji Star H1 entry without changing the entry definition. The confirmed +24h full-exit result remains the reference baseline. This experiment asks whether +24h should become a management switch rather than an unconditional exit.

This is not a new entry confirmation and not a Guardian/production test.

## Frozen entry
Unchanged from D032-C1:
- Bullish Doji Star H1 using the same TA-Lib-default numerical definition;
- 144-hour SMA downtrend with strict `MA[t-6] > ... > MA[t]`;
- executable LONG entry = first ASK after signal;
- `1R = 2 * sample stdev(previous 24 H1 returns)`.

Primary cohort remains BTC, ETH and DOGE/DOG CFDs only. Any other symbol is unregistered for the primary management verdict.

## Confirmed reference
Baseline management is the already confirmed rule:

`LONG -> no price target -> full exit at exact +24h BID`

Spread is embedded by ASK entry / BID exit. Explicit commission is configured separately in bps/side.

## Primary management candidate
Frozen before inspecting any >24h path:

1. At +24h compute net ex-swap PnL.
2. If net PnL <= 0: close the full position at +24h.
3. If net PnL > 0: convert the full position to a runner.
4. Runner has no TP.
5. Runner protection floor is net breakeven: executable entry ASK plus configured round-turn commission expressed as a price fraction.
6. Runner trailing distance is `1.0R` from the highest BID observed after +24h.
7. Effective stop is `max(net-BE floor, post-24h peak BID - 1.0R)`.
8. Primary runner timeout is +48h from the original signal.
9. If a market gap crosses the stop, record the actual first executable BID rather than pretending the stop filled at its requested level.

The primary comparison is paired against the +24h full-exit reference on the same events.

## Frozen diagnostics only
The scanner may also record, but these may not replace the primary rule after results are opened:
- +48h runner with 0.5R trailing distance;
- +48h runner with 1.5R trailing distance;
- +72h timeout with the same 1.0R trail;
- raw executable returns at 24/30/36/42/48/60/72h;
- pre-24h first-hit flags for -1.5R, -2.0R and -2.5R. These are diagnostic inputs for a later separately frozen hard-stop experiment; no pre-24h stop is imposed by D032-M1.

## Weekend / swap treatment
Weekend/feed gaps after +24h are retained and flagged because they are part of the operational runner problem. The scanner also records the broker's current raw swap mode, long-swap property and triple-swap day in RUN_INFO.

Exact historical swap is NOT claimed by the virtual scanner. Summary PnL is therefore `net ex-swap`. Swap must be stressed separately before production using the applicable FundedNext symbol specification/rates.

## Data windows
The >24h endpoint was not previously inspected. Two management-development epochs are frozen:
- PRE2024: signals 2018-07-01 through 2023-12-28 23:00, leaving a full 72h future path before 2024;
- POST2024: signals 2024-01-01 through 2026-06-23 23:00, leaving a full 72h path within the previously seen D032 discovery interval ending 2026-06-26.

These epochs may be reported separately and pooled for management development. They do not create a new independent entry confirmation.

## Tester limitation
FundedNext historical real ticks are unavailable for the old period. Recommended tester configuration is M1 + `1 minute OHLC`.

Therefore generated intraminute trailing-stop ordering is provisional. D032-M1 can reject an obviously bad management rule, but a positive trailing-stop result still requires later real-tick/live-forward confirmation before production.

## Primary advancement rule
The +24h-to-+48h 1R runner candidate advances to a separate validation stage only if, on the frozen BTC/ETH/DOG cohort:
- paired mean delta versus the +24h baseline is > 0;
- month-block bootstrap 95% lower bound of the paired delta is > 0;
- at least 2 of 3 core symbols have positive paired mean delta;
- no single core symbol contributes more than 60% of total positive incremental gain.

If these fail, retain the confirmed +24h reference and reject the runner candidate rather than tuning it on the same outcomes.

## Output contract
Each run writes to:

`FILE_COMMON\GuardianResearch\SETUP_SCANS\D032_M1_DojiStar_Post24_Runner\<SYMBOL>\RUN_...\`

Files:
- `MANAGEMENT_EVENTS.csv`
- `SUMMARY.csv`
- `RUN_INFO.csv`

No orders are sent and Guardian is OFF.
