# D032 — CRYPTO H1 REVERSAL TRIO

Date: 2026-09-05
Status: PREREGISTERED / CODE PREPARED / NOT YET RUN
Classification: CLOSE_REPLICATION_CFD_TRANSFER

## Purpose

D032 is a setup-first entry-edge diagnostic, not a production strategy and not a Guardian integration test. It tests whether three candlestick reversal patterns with recent large-sample crypto evidence retain measurable predictive/excursion edge on the target MT5 CFD feed.

Primary source: Moser & Brauneis (2026), International Review of Economics & Finance 108, article 105158, DOI 10.1016/j.iref.2026.105158.

The source studies hourly OHLC data from 07/2018 to 01/2022 across nearly 400 cryptocurrencies, roughly 2,000 trading pairs and 36 exchanges, using TA-Lib pattern recognition, explicit prior-trend requirements, fixed holding horizons through 24h, data-snooping controls and robustness checks.

## Frozen symbols for first CFD campaign

- BTC CFD on the target prop/broker feed
- ETH CFD on the target prop/broker feed
- DOGE CFD on the target prop/broker feed

No symbol substitution after results are opened.

## Frozen selected patterns

1. `DOJI_STAR_BULLISH` — TA-Lib CDLDOJISTAR bullish output, accepted only with a qualifying prior downtrend.
2. `INVERTED_HAMMER_BULLISH` — TA-Lib CDLINVERTEDHAMMER, accepted only with a qualifying prior downtrend.
3. `HANGING_MAN_BEARISH` — TA-Lib CDLHANGINGMAN, accepted only with a qualifying prior uptrend.

TA-Lib default candle settings are reimplemented numerically in MQL5. Do not replace them with visual heuristics or optimized thresholds after seeing results.

## Frozen trend interpretation

The paper states that it uses a moving average over the past six days on hourly closes and requires `MA[t-6] ... MA[t]` to be strictly monotonic. D032 freezes the following explicit interpretation before first run:

- moving-average window = 6 x 24 = 144 H1 observations;
- uptrend if the seven consecutive hourly MA values `MA[t-6] < ... < MA[t]` are strictly increasing;
- downtrend if `MA[t-6] > ... > MA[t]` are strictly decreasing.

This is logged as a methodology interpretation, not silently claimed as an exact source-code reproduction. Any later alternative interpretation is a new experiment, not a correction chosen after outcome inspection.

## Source-return replication layer

Signal timestamp = end of the H1 candle completing the pattern.

Directional source-close return is recorded at exactly these horizons:

`1, 2, 3, 6, 9, 12, 15, 18, 24 hours`.

No best-horizon selection is permitted after outcomes are opened. The whole response curve is diagnostic evidence.

## Source stop / R definition

At signal time, calculate the sample standard deviation of the previous 24 hourly returns.

`1R = 2 x sigma_24h` as a fractional price move.

The source robustness experiment defines stop breach when price moves more than 2 standard deviations against the predicted direction. D032 records this threshold and uses it as the source-defined R for path diagnostics.

Additional diagnostics are allowed because they do not alter the source signal:

- MFE_R and MAE_R during the first 24h;
- touch of 0.5R, 1R, 1.5R, 2R, 2.5R and 3R;
- touch timestamps for pattern events;
- whether -1R was breached and when.

All R diagnostics are capped at the source-valid 24h window. A level reached after 24h does not count.

## CFD executable layer

Because the user trades CFDs, every source-close result is paired with an executable MT5 result:

- source layer uses H1 close-to-close prices;
- executable entry uses the first tester bid/ask available after the signal;
- executable future return uses the executable opposite side at each exact horizon;
- spread is therefore embedded in executable returns;
- commission is stored separately as an input in bps/side and must be included in final analysis if non-zero.

Any source edge that disappears on the CFD executable layer is not considered transferable.

## Matched control pool

D032 creates a deterministic control pool from hours that satisfy the same qualifying prior trend but contain none of the selected trio patterns.

- downtrend controls are evaluated in the bullish/long reversal direction;
- uptrend controls are evaluated in the bearish/short reversal direction;
- controls use the same sigma/R calculation and same source/executable horizon returns.

Purpose: measure incremental setup information relative to what the same market/trend context would have done without the pattern.

The control pool is for matched offline analysis. Do not optimize a control-selection rule after seeing pattern results.

## Feed gaps / CFD closures

D032 flags H1 discontinuities and missing exact horizons. Missing broker prices are not silently interpolated. Pattern events and control rows with feed gaps remain identifiable in output for sensitivity analysis.

## Output contract

Each Strategy Tester run creates its own recognizable folder under:

`FILE_COMMON\GuardianResearch\SETUP_SCANS\D032_CRYPTO_H1_ReversalTrio\<SYMBOL>\<RUN_TAG>\`

Files:

- `PATTERN_EVENTS.csv`
- `CONTROL_POOL.csv`
- `SUMMARY.csv`
- `RUN_INFO.csv`

No orders are sent. Guardian is OFF for this cheap entry-viability phase.

## Mandatory analysis before any strategy design

Per symbol, pattern, year/subperiod and aggregate:

- occurrence count;
- source returns at all nine source horizons;
- executable CFD returns at all nine horizons;
- commission-adjusted results when commission is supplied;
- MFE_R / MAE_R;
- 0.5R through 3R touch frequencies;
- -1R stop-breach frequency;
- time to R levels for pattern events;
- trend-matched control differential;
- feed-gap sensitivity;
- BTC vs ETH vs DOGE transport consistency;
- concentration by time period / few events.

## Scientific boundary

D032 does NOT select a production TP, trailing rule or Guardian risk model. A promising horizon or R level discovered here is a discovery result only. A management rule must be frozen in a new experiment and validated on untouched/future data before Guardian integration.

Guardian/FTMO drawdown testing is deliberately deferred until an entry setup demonstrates enough standalone edge to justify the expensive full-chassis campaign.
