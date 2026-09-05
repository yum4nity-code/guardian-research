# D032-E1 — Bullish Doji Star H1 + RSI(14) M15 diagnostic

Date: 2026-09-05
Status: PREREGISTERED BEFORE RSI-CONDITIONED RESULTS ARE INSPECTED
Classification: POSTHOC_ENTRY_DIAGNOSTIC_RSI_RECORDED_NO_FILTER

## Purpose
Diagnose whether RSI(14) on M15 explains entry quality for the already confirmed D032 Bullish Doji Star H1 setup. The goal is to test the user's hypothesis that the Doji entry may be materially better when M15 is oversold, without choosing an RSI threshold in advance.

## Frozen entry
Unchanged from D032-C1:
- Bullish Doji Star H1, same TA-Lib-default numerical definition;
- 144-hour SMA downtrend with strict `MA[t-6] > ... > MA[t]`;
- executable LONG entry = first ASK after signal;
- `1R = 2 * sample stdev(previous 24 H1 returns)`.

## RSI measurement
- RSI period = 14.
- Timeframe = M15.
- Record the exact RSI value from the last fully closed M15 candle at the H1 signal boundary.
- The currently forming M15 candle must never be used.
- No RSI threshold is applied in this first diagnostic.

## Primary diagnostics
For every qualifying Doji event, record:
- exact RSI(14) M15 value;
- executable +24h return in bps and R;
- pre-24h MFE_R and MAE_R with timestamps;
- +24h win/loss status;
- feed-gap status.

## Discovery window
Use PRE2024 only for this first RSI relationship scan:
- signal start: 2018-07-01 00:00;
- last accepted signal: 2023-12-30 23:00.

POST2024 must not be used by v1.00. If the PRE2024 relationship is strong enough to justify a threshold, freeze exactly one threshold before a later POST2024 validation run.

## Cohort
Primary diagnostic cohort:
- BTC CFD
- ETH CFD
- DOGE/DOG CFD

Other symbols are unregistered and must not determine the threshold.

## Interpretation rule
The first scan may show descriptive RSI bands such as `<20`, `20-25`, `25-30`, `30-35`, `35-40`, `>=40`, but no band selected after inspection is considered validated.

A useful RSI relationship should improve entry quality, especially MAE of future winners, without collapsing signal frequency. If a threshold is chosen later, it must be preregistered before POST2024 validation.

## Output
Each run writes:
`FILE_COMMON\GuardianResearch\SETUP_SCANS\D032_E1_DojiStar_RSI14M15\<SYMBOL>\RUN_...\`

Files:
- `RSI_EVENTS.csv`
- `SUMMARY.csv`
- `RUN_INFO.csv`

No orders are sent and Guardian is OFF.
