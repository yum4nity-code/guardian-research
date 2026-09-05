# D032-C1 — Bullish Doji Star H1 — LINK transport result

Date: 2026-09-05
Status: TRANSPORT FAIL / DOES NOT ALTER CORE BTC-ETH-DOG CONFIRMATION
Experiment: `D032_C1_CONFIRM_DojiStar_H1`
Feed: FundedNext LNKUSD CFD
Tester: M1, generated 1-minute OHLC for historical period
Frozen confirmation window: 2018-07-01 through 2023-12-30 23:00 server time; actual LNK history/run begins 2021-09-24.

## Result

- accepted Doji signals: 32
- clean +24h events: 28
- feed-gap/incomplete events: 4
- mean executable +24h return: -118.675 bps (-1.1868%)
- median executable +24h return: about -116.72 bps
- win rate: 39.29%
- mean +24h return in source-defined risk: -0.690R/event
- secondary -1R/+3R/24h management mean: -0.192R/event
- management outcomes: 21 stop-first, 5 target-first, 2 timeout

Same-downtrend/no-Doji clean controls: n=5,048; mean executable +24h return about +14.35 bps. Doji minus broad same-trend control differential is therefore about -133.03 bps.

Year breakdown of clean Doji events:
- 2021: n=6, mean about +1.83 bps
- 2022: n=17, mean about -118.80 bps
- 2023: n=5, mean about -262.87 bps

The response curve deteriorates after the first hour and remains negative through +24h; this is not a case where only the frozen 24h endpoint misses an earlier strong edge.

## Interpretation

LINK materially fails transport on the untouched pre-2024 FundedNext CFD sample. This is notable because the 2024-2026 discovery-side LINK sample had looked positive. The sign reversal is evidence against treating Bullish Doji Star as a universal crypto rule. It does NOT invalidate the preregistered core BTC/ETH/DOG confirmation, because LINK was transport-only by design.

Do not tune LINK-specific thresholds or exclude bad years post hoc. Retain LINK as a transport failure and complete XRP transport separately.