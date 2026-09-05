# D030 — Alanazi (2020) bullish/bearish engulfing H4 CFD close replication

Date: 2026-09-05
Status: PREREGISTERED BEFORE TARGET-CFD RESULTS ARE INSPECTED
Classification: `CLOSE_REPLICATION_CFD_TRANSFER`

## Primary source
Ahmed S. Alanazi (2020), “The bullish and the bearish engulfing patterns: beating the forex market or being beaten?”, *The European Journal of Finance* 26(15), 1484–1505. DOI: `10.1080/1351847X.2020.1748679`.

The full article methodology was recovered before this campaign was run. The published paper used daily candles in-sample and a completely different H4 sample as its out-of-sample robustness test. The H4 source OOS period was 2015–2018 on 24 FX pairs; the seven majors produced 3,047 trades, with 1,527 winners and 1,514 losers, and positive aggregate adjusted returns after spread and rollover.

## Why classification is CLOSE rather than EXACT
The trading rule itself is now recoverable exactly, but our target transfer is not the original FXCM spot dataset:
- target feed is FundedNext CFD;
- historical real ticks are unavailable for the old FundedNext interval, so tester execution uses M1 + `1 minute OHLC`;
- the paper detects patterns on H4 midpoint quote OHLC constructed from separate ask/bid OHLC. The scanner reconstructs H4 bid/ask OHLC from tester BID/ASK ticks and then uses their midpoint, which is a close approximation but not the original FXCM observations;
- exact historical rollover/interest-rate differentials are not reconstructed in the first pass.

No result from this campaign may therefore be called an exact reproduction of the paper.

## Frozen source pattern definition
Two consecutive H4 candles: Previous Candle (PC) and Current Candle (CC).

Bullish engulfing, Alanazi Eq. 5:
- `CC close > CC open`;
- `PC close < PC open`;
- `CC high > PC high`;
- `CC low < PC low`;
- `CC close > PC open`.

Bearish engulfing, Alanazi Eq. 6, exact mirror:
- `CC close < CC open`;
- `PC close > PC open`;
- `CC high > PC high`;
- `CC low < PC low`;
- `CC close < PC open`.

Important: this is a **full-candle/wick engulf**, not merely a real-body engulf. The paper explicitly allows formations with or without an opening gap. It also deliberately uses **no trend filter**, taking every engulfing occurrence as a reversal to avoid subjective trend identification.

## Frozen source execution
- Bullish: enter LONG at the next new H4 candle opening ASK.
- Bearish: enter SHORT at the next new H4 candle opening BID.
- Bullish stop: 5 pips below the CC low.
- Bearish stop: 5 pips above the CC high.
- Target: exactly 1:1 reward/risk, equal to the entry-to-stop distance.
- Spread: embedded through executable ASK/BID entry and opposite-side exit.
- No TP/SL optimisation, no trailing, no time stop, no trend filter, no RSI, no Guardian.
- Multiple events may overlap, matching event-study treatment rather than imposing portfolio constraints at this stage.

## Target CFD universe
Frozen primary universe = the same seven USD majors emphasized by the source:
- EURUSD
- GBPUSD
- USDJPY
- USDCHF
- USDCAD
- AUDUSD
- NZDUSD

No post-result pair selection can turn a failed pooled campaign into a validated strategy. Pair-level anomalies may only seed a new preregistered experiment.

## Target evaluation window
Primary target-CFD analysis window: signals from `2024-01-01 00:00` through `2026-08-31 23:59` server time.

Tester may run several days beyond 2026-08-31 so late-August trades can resolve; event-level analysis will enforce the frozen signal cutoff.

## Primary metrics
For each event preserve:
- source pattern direction and midpoint OHLC;
- executable entry, stop, target and spread;
- source-risk distance in pips;
- first stop/target outcome;
- binary source outcome (+1R / -1R);
- actual executable realized R and pips, including gap/slippage effects in the tester path;
- MFE_R, MAE_R, duration and feed-gap diagnostics.

Two distinct economic views must be reported:
1. **Risk-normalized expectancy** — relevant to Guardian/prop-firm sizing.
2. **Fixed-size pip expectancy** — closer to the paper’s fixed mini-lot economic design.

Do not confuse a positive fixed-lot pip result with a production-worthy risk-normalized edge.

## Advancement gate
D030 advances beyond this first CFD replication only if the seven-major primary pool satisfies all of:
1. at least 300 resolved clean trades;
2. pooled mean executable risk-normalized result `> +0.15R/trade` after embedded spread;
3. month-block bootstrap 95% lower bound of mean executable R `> 0`;
4. at least 4 of 7 majors have positive mean executable R;
5. pooled fixed-size pip result after embedded spread `> 0`;
6. no single pair contributes more than 40% of total positive pooled executable R.

The +0.15R threshold is the project’s pre-production economic standard, not a claim made by the source paper.

## Costs
Spread is embedded natively. Exact historical swap/rollover is not in the first-pass summary. If and only if D030 passes the pre-swap gate, historical/current rollover stress is mandatory before any Guardian integration.

## Interpretation lock
- **PASS**: retain exact frozen source rule for a separate robustness/cost stage; no same-sample threshold or stop/target optimisation.
- **FAIL on R but source-like pips positive**: academically interesting replication/transport, but reject as a Guardian/prop-challenge engine in this form.
- **FAIL broadly**: reject the target-CFD transfer; do not rescue by adding trend/RSI or changing 5-pip buffer/1:1 on the same outcomes.

## Tester
Use chart timeframe M1 with model `1 minute OHLC`. Scanner internally builds H4 quote bars and sends no orders.