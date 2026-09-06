# D023 USDJPY London ORB — FundedNext conformance control — 2026-09-06

## Context
D017 Momentum managed attribution is now closed as a current alpha candidate across BTC, ETH, EURUSD, GBPUSD, USDJPY, XAUUSD and USDCAD. The next independent sleeve is D023 London ORB USDJPY.

Historical D023 discovery/watchlist evidence: USDJPY n=489, gross mean +0.1499R, approximate FTMO-commission-adjusted mean +0.1179R, positive gross mean in 2024/2025/2026. Broad 4-market V0 remained rejected; USDJPY is only a separately confirmable branch.

## Frozen entry/exit rule
- M15.
- Europe/London local clock.
- Opening range = exactly 08:00, 08:15, 08:30, 08:45 London bars.
- First M15 close strictly outside the range from 09:00 inclusive to 11:00 exclusive.
- Entry = next M15 bar open at executable observed-spread side.
- Stop = opposite opening-range edge.
- Exit = stop or close of 15:45-16:00 London bar.
- One trade per London weekday.
- No EMA/RSI/ATR/news/day/range-size filters.

## Conformance finding
The old D023 MT5 diagnostic v1.02 used a fixed `server minus London = 2h` conversion. That is not exact around DST mismatch weeks.

FundedNext official documentation states server time is GMT+2 in standard time and GMT+3 in daylight-saving time. FundedNext's official 2025 DST notice explicitly says the change follows the beginning of **US Daylight Saving Time** (server moved to GMT+3 for Monday 2025-03-10). Therefore the new control uses US DST dates for FundedNext server offset and UK DST dates for Europe/London.

## FundedNext commission
Current FundedNext CFD general rules state commission is charged **per side**, fixed by model:
- Stellar 1-Step / 2-Step: USD 5 per Forex lot per side.
- Stellar Lite: USD 7 per Forex lot per side.
- Stellar Instant: USD 7 per Forex lot per side in general rules.

The standalone virtual diagnostic does not inherit Guardian's prop-firm adapter, so it now exposes the FundedNext commission model explicitly.

## Prepared diagnostic
Local/user artifact:
`D023_USDJPY_LondonORB_M15_v1_04_FUNDEDNEXT_20260906.mq5`

SHA256:
`d42aea373b55334e6e614f7405c532b7a6be1d074623aa649153176f98e373a1`

Static delimiter check: balanced. MetaEditor compile not yet claimed.

Default input:
`FN_STELLAR_1STEP_2STEP` = USD 5/lot/side.

CSV:
`D023_USDJPY_ORB_V104_FUNDEDNEXT_CONFORMANCE.csv`

## Required next action
1. User compiles v1.04 in MetaEditor. Require 0 errors / 0 warnings before calling it compile-valid.
2. Run USDJPY M15, Every tick, 2024-01-02 through 2026-06-26 on the FundedNext tester/account feed, with the correct FundedNext model selected.
3. Analyze conformance result against the old v1.02 watchlist result. Do not tune anything.
4. Only if the corrected-clock/corrected-cost signal remains credible, open the reserved 2023 USDJPY confirmation window under a separately frozen gate.
5. Manager/trail experiments are downstream and must not contaminate the entry confirmation.
