# D029 — TSMOM 12M/1M full 8-market primary verdict

Date: 2026-09-05
Status: **REJECTED**
Classification: `CLOSE_REPLICATION_CFD_TRANSFER`

## Frozen source-like rule
Moskowitz/Ooi/Pedersen-style monthly time-series momentum transfer:
- sign of prior 12 completed calendar-month CFD return;
- LONG if positive / SHORT if negative;
- hold one calendar month;
- executable BID/ASK entry and exit, spread embedded;
- EWMA ex-ante volatility with `delta=60/61`, annualization 261;
- source-like scaling `0.40 / exante_vol`;
- no stop/TP/trailing/filter;
- historical swap and commission not reconstructed.

Frozen development interval: 2018-01-01 through 2023-12-31.
Primary universe: EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD, XAUUSD.

## Data note
Seven FX majors have 72 resolved monthly events each. XAUUSD history on the supplied FundedNext feed begins only in 2021 for this scanner, therefore XAU contributes 36 resolved monthly events rather than 72. Total pooled primary sample = 540 events.

## Per-market results
| Market | n | Mean executable bps | Mean source-scaled return %/month |
|---|---:|---:|---:|
| EURUSD | 72 | +0.55 | +0.501 |
| GBPUSD | 72 | +5.07 | +0.604 |
| USDJPY | 72 | +18.22 | +0.826 |
| USDCHF | 72 | -14.92 | -0.760 |
| USDCAD | 72 | -16.57 | -0.643 |
| AUDUSD | 72 | +4.93 | +0.550 |
| NZDUSD | 72 | -1.96 | +0.149 |
| XAUUSD | 36 | -94.58 | -2.341 |

Exactly 5/8 primary markets have positive mean source-scaled return.

## Pooled results
- resolved primary events: **540**;
- pooled mean executable directional return: **-6.93 bps/event**;
- pooled mean source-scaled return: **+0.0075%/month/event** (essentially flat);
- equal-month portfolio mean source-scaled return: about **+0.0267%/month**;
- equal-month annualized Sharpe: about **0.012**;
- month-block bootstrap 95% interval for pooled/equal-month source-scaled mean: approximately **[-1.7%, +1.75%] per month**, decisively crossing zero.

Temporal split:
- 2018-2020 pooled source-scaled mean: **+0.315%/month/event**;
- 2021-2023 pooled source-scaled mean: **-0.262%/month/event**.

Positive net source-scaled contribution concentration among profitable markets:
- USDJPY ~31.4% of total positive net contribution;
- GBPUSD ~23.0%;
- AUDUSD ~20.9%;
- EURUSD ~19.0%;
- NZDUSD ~5.7%.
No single positive market exceeds the frozen 35% concentration cap.

## Frozen gate
1. >=400 resolved pooled events: **PASS** (540)
2. pooled mean executable directional return >0: **FAIL** (-6.93 bps)
3. pooled mean source-vol-scaled monthly return >0: **PASS**, but economically negligible (+0.0075%)
4. month-block bootstrap 95% lower bound >0: **FAIL**
5. at least 5/8 primary markets positive mean source-scaled return: **PASS** (5/8)
6. both 2018-2020 and 2021-2023 pooled means positive: **FAIL** (2021-2023 negative)
7. no single market >35% of positive pooled source-scaled contribution: **PASS**

Final gate: **4/7 PASS, 3/7 FAIL -> REJECT**.

## Interpretation
The source-like 12M/1M TSMOM transfer does not show a stable enough edge on this FundedNext CFD universe. Adding the two previously missing primary markets materially weakens the partial six-market result: USDCAD is negative and XAUUSD is strongly negative on its available 2021-2023 history. The pooled executable return is negative, the bootstrap crosses zero widely, and the later temporal half is negative.

Per preregistration, do not rescue D029 on the same 2018-2023 sample by mining RSI, ATR, SMA, return, session, direction, or alternate lookback/holding thresholds. The diagnostic feature lab may only generate separately preregistered hypotheses for reserved/future data; v1.00 H4 feature fields are additionally contaminated on some older-feed segments and must not be used for inference.

BTC/ETH secondary adaptation diagnostics remain discovery clues only and are not part of this primary verdict.
