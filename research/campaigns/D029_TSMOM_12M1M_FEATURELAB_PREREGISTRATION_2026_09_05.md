# D029 — Moskowitz/Ooi/Pedersen 12M/1M TSMOM CFD transfer + feature lab

Date: 2026-09-05
Status: PREREGISTERED BEFORE D029 CFD OUTCOMES ARE INSPECTED
Classification: CLOSE_REPLICATION_CFD_TRANSFER

## Source
Moskowitz, Ooi & Pedersen (2012), *Journal of Financial Economics* 104, 228–250, DOI `10.1016/j.jfineco.2011.11.003`.

The source 12-month TSMOM factor goes LONG when the instrument's own prior 12-month excess return is positive and SHORT when negative, holds for one month, and scales position size inversely to ex-ante volatility. The source volatility model is EWMA of lagged squared daily returns with decay chosen so the center of mass is 60 days; the benchmark factor uses a 40% annualized volatility target per instrument.

## CFD transfer differences
This scanner uses FundedNext CFD price returns rather than futures/forward excess-return series. Signal direction is based on closed MT5 monthly BID bars. Entry and exit are executable ASK/BID so spread is embedded. Historical swap and commission are not reconstructed in the first pass.

## Frozen development window
Signals from 2018-01-01 through 2023-12-31. 2024-2026 stays reserved for a later validation if the transfer is interesting.

## Frozen source-like rule
- monthly signal only;
- prior 12 completed calendar-month CFD return;
- LONG if >0, SHORT if <0;
- entry = first executable quote of new calendar month;
- exit = first executable quote of following calendar month;
- no stop, TP, trailing, RSI filter, session filter or trend filter;
- ex-ante annualized volatility = EWMA lagged daily return variance with `delta=60/61`, annualization 261;
- source-like position multiplier = `0.40 / exante_vol`.

## Primary source-like CFD universe
Recommended primary runs:
- EURUSD
- GBPUSD
- USDJPY
- USDCHF
- USDCAD
- AUDUSD
- NZDUSD
- XAUUSD

Crypto may be run as secondary adaptation diagnostics only:
- BTCUSD
- ETHUSD
- DOGUSD
- any additional liquid CFD supplied by the user.

## Diagnostic feature lab — NOT SIGNAL FILTERS
Every monthly event also records, without changing trade eligibility:
- RSI(14) D1 and H4;
- ATR(14) D1/H4 normalized by price;
- 5/20/60/120/252-day returns;
- 20d/60d realized annualized volatility;
- distance from D1 SMA20/SMA50/SMA200;
- 20-day close z-score;
- position within the trailing 252-day close range;
- previous-month range percentage;
- executable MFE/MAE during the one-month holding period.

These fields are descriptive only. No threshold may be selected from 2018-2023 and called validated. Any feature-based adaptation that looks interesting must be frozen separately and tested on reserved 2024-2026 data.

## Advancement gate for the source-like transfer
Because the source has no natural stop, do NOT invent R for D029. Advance the source-like transfer to a separate validation stage only if the primary CFD universe satisfies all of:
1. at least 400 fully resolved pooled monthly events;
2. pooled mean executable directional return after embedded spread >0;
3. pooled mean source-vol-scaled monthly return >0;
4. month-block bootstrap 95% lower bound of source-vol-scaled return >0;
5. at least 5 of 8 primary markets have positive mean source-vol-scaled return;
6. both 2018-2020 and 2021-2023 pooled means are positive;
7. no single market contributes >35% of total positive pooled source-vol-scaled return.

A PASS is only evidence that the published TSMOM family transfers to the CFD feed. Prop-firm relevance still requires a separately frozen stop/risk study, cost/swap stress and enough practical frequency. A FAIL means do not rescue 12M/1M with same-sample RSI/SMA/ATR threshold mining.

## Tester
Use `D029_TSMOM_12M1M_FeatureLab_v1_00.mq5` on M1 with `1 minute OHLC` for old FundedNext history. Tester should start early enough to provide at least 12 months of monthly history and EWMA warmup; a 2017 start is recommended when available, while signal eligibility remains hard-locked to 2018-2023.
