# Guardian v11.16.14 counter-audit — 2026-09-02

## Verdict
The catastrophic BTC/GBPUSD runs are NOT explainable by the BUY1 SL change from 0.15 ATR to 0.50 ATR.

Static diff v11.16.13 -> v11.16.14: 1 file, 10 insertions / 9 deletions. Functional strategy changes are limited to:
- add `InpRSIBuy1SLBufferATR = 0.50`;
- use it for auto BUY1 structural stop;
- use it for manual M-BUY1 adopted stop;
- keep BUY2/common-stop structural buffer on existing `InpRSISLBufferATR = 0.15`;
- parameter validation + version/HUD labels.

No RSI TP1/TP2 logic was removed or changed. RSI TP1 remains RSI >= 50, partial close 40%, BE NET + trailing; TP2 remains RSI >= 70.

## Proof the bad run was not RSI-only
- RSI entry executor has only `g_trade.Buy(...)`.
- The only automatic path capable of `g_trade.Sell(...)` is `ExecuteTrade(...)`, i.e. Momentum.
- Bad BTC screenshot: 4,170 trades = 2,030 longs + 2,140 shorts. Therefore Momentum was active in that test.
- Raw BTC tail includes new SELL entries at 23:30 and 23:53. 23:53 is not a normal M5 boundary, suggesting Momentum was also running with an effective M1 setup cadence (likely `InpAutoSetupTimeframe=false` or an M1 setup-TF input).
- Raw EURUSD tail likewise contains SELL entries on arbitrary minutes (18:54, 18:58, 19:14, 19:17, etc.), incompatible with an RSI-only build and inconsistent with the default M15 Momentum cadence.

## Wider-SL implementation audit
The intended wider-SL experiment itself is implemented correctly:
- BUY1/M-BUY1 stop: episode low - 0.50 ATR.
- BUY2 structural stop: unchanged at episode2 low - 0.15 ATR, and BUY2 is forbidden from loosening the BUY1 common stop.
- `CalculateDynamicLot()` computes lot size from stop distance and fixed dollar risk. Increasing stop distance therefore reduces lots automatically; it does not increase planned dollar risk.

0.50 ATR is NOT claimed to be optimal. It is a research point selected for A/B testing against the 0.15 ATR baseline.

## Remediation
Created v11.16.15 `RSI_ONLY_WIDER_SL_AUDITED` as a dedicated research build:
- Momentum default OFF;
- Momentum entry path HARD-DISABLED at runtime even if an old `.set`/cached input sets the switch ON;
- defense-in-depth block inside `ExecuteTrade()`;
- RSI BUY1 buffer remains 0.50 ATR; BUY2 remains 0.15 ATR;
- existing Momentum positions would still be managed, but no new Momentum entry can be created by this research build.

Expected sanity check for an RSI-only backtest: Short Trades must be exactly 0.
