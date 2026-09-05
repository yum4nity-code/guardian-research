# D033 — EURUSD M5 Double Top / Double Bottom, Ben Omrane & Van Oppens M2

Date: 2026-09-05
Status: PREREGISTERED BEFORE D033 CFD OUTCOMES ARE INSPECTED
Classification: CLOSE_REPLICATION_CFD_TRANSFER

## Source
Ben Omrane, W. & Van Oppens, H. (2006), *The performance analysis of chart patterns: Monte Carlo simulation and evidence from the euro/dollar foreign exchange market*, Empirical Economics 30(4), 947–971. DOI `10.1007/s00181-005-0007-8`.

The paper studies five-minute EUR/USD mid-quotes, uses a 36-observation rolling window, Gaussian Nadaraya-Watson smoothing, Silverman bandwidth reduced to 20%, and two extrema methods. D033 freezes the source **M2** arm before testing because M2 uses high prices for maxima and low prices for minima and produced materially more DT/DB detections in the paper than M1.

## Frozen source-like detection
- primary market: EURUSD only;
- 5-minute midpoint OHLC reconstructed from tester BID/ASK;
- rolling window length `l=36` M5 observations;
- Gaussian Nadaraya-Watson kernel;
- `h* = 0.2 * hopt`, with Silverman `hopt=(4/3)^(1/5)*sigma*l^(-1/5)` on the regular time grid;
- M2: smooth highs for maxima and lows for minima;
- derivative sign changes identify candidate extrema;
- project extrema to the original high/low curve using the source ±1-observation projection;
- enforce alternating extrema;
- Double Top = max/min/max; Double Bottom = min/max/min;
- source exact-equality equations are implemented with only one MT5 point of numerical quote-grid tolerance, not a tunable similarity band;
- `td`, `tf`, timing-symmetry and pre-trend conditions follow the source quantitative definitions;
- final journal pre-trend requirement used: prior move >= `2/3 * h` for both DT and DB.

## Frozen source trading rule
At pattern completion `tf`:
- DT => SHORT; DB => LONG;
- source decision levels are midpoint-based;
- take profit = `0.50*h` in the predicted direction;
- stop loss = `0.20*h` in the adverse direction;
- if neither is reached, close at `tf + (tf-td)`;
- source nominal reward:risk is therefore 2.5:1 before spread.

CFD execution transfer:
- LONG entry ASK / exit BID;
- SHORT entry BID / exit ASK;
- spread embedded;
- no Guardian and no live orders;
- historical commission and swap are not reconstructed in v1.00;
- exact old real ticks are unavailable, so first pass is M1 tester + `1 minute OHLC` and is not final live-execution proof.

## Frozen development window
Signals: `2024-01-01 00:00` through `2026-06-30 23:59`.
Run the tester with warm-up before the start and enough time after the end to resolve late trades. Pre-2024 history remains reserved for a later confirmation if D033 survives development.

## Passive feature lab — NOT filters
Every event records, without changing eligibility:
- RSI(14) synthetic from internally reconstructed M5 closes at M5/M15/H1 strides;
- ATR(14) M5;
- 15m / 1h / 4h / 24h returns;
- distance from M5 SMA20/SMA50/SMA200;
- 1h / 4h realized 5-minute volatility;
- 1h / 4h range;
- signal hour and day of week;
- pattern height, duration, symmetry, equal-extrema difference, pre-trend ratio;
- executable spread, MFE/MAE and final R.

No RSI/SMA/ATR/session threshold may be selected from this interval and called validated. Any feature-based adaptation must be frozen separately and tested on reserved data.

## Advancement gate
Evaluate **clean M2 DT+DB pooled EURUSD trades**. D033 advances only if all are true:
1. >=250 fully resolved clean trades;
2. mean executable result > `+0.15R/trade`;
3. median executable R > 0;
4. month-block bootstrap 95% lower bound of mean executable R > 0;
5. DT mean R > 0 and DB mean R > 0;
6. at least two of calendar 2024, 2025 and 2026 have positive mean R;
7. no single event contributes >10% of total positive pooled R.

A PASS only advances the exact frozen M2 rule to untouched/pre-2024 confirmation plus explicit cost stress. A FAIL closes this exact rule; do not retune equality tolerance, 36-bar window, TP/SL fractions, RSI, sessions or extrema rules on the same 2024-2026 interval.

## Scanner
`D033_EURUSD_M5_DoubleTopBottom_M2_FeatureLab_v1_00.mq5`
SHA-256 `4ad46396f14a71e2b1f30f63bd089cdf9d4a043568d80a068fb99199fc4d647c`
Static QA before delivery: braces/parens/brackets balanced; EVENTS header and row both 61 columns; SUMMARY rows 14 columns; direct header flush + runtime FileSize QA. ChatGPT has not MetaEditor-compiled it.