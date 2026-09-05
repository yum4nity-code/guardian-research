# D030 — H4 FX ENGULFING REPLICATION GATE

Date: 2026-09-05
Status: RESERVE CANDIDATE / NOT PREREGISTERED FOR EXECUTION / METHODOLOGY GATE

## Published basis

Ahmed S. Alanazi (2020), *The European Journal of Finance*, "The bullish and the bearish engulfing patterns: beating the forex market or being beaten?"
DOI: 10.1080/1351847X.2020.1748679

Publisher abstract reports:
- 112,792 in-sample daily candles;
- 148,992 out-of-sample four-hour candles;
- more than three million spot quote observations;
- 24 FX pairs, 2000-2018;
- significant profitability particularly for the seven majors;
- material importance of transaction costs.

## Why it is a high-interest reserve

This is unusually relevant to Guardian because the evidence is:
- directly in spot FX;
- explicitly tested on H4 data out of sample;
- based on a simple visual setup family rather than a large indicator stack;
- high enough timeframe to suppress much M1/M5 noise, but potentially frequent enough across several majors to be useful.

## Hard blocker

The accessible publisher abstract is not sufficient to reconstruct every trading semantic exactly. Before D030 becomes an executable preregistration, recover/verify from the actual paper at minimum:
1. exact bullish engulfing definition;
2. exact bearish engulfing definition;
3. whether a preceding trend is required and, if so, its objective definition;
4. gap/open requirements in 24-hour FX;
5. exact H4 candle timezone/alignment used in the OOS sample;
6. entry timing and executable bid/ask convention;
7. stop-loss definition;
8. take-profit/exit/time-stop definition;
9. treatment of overlapping/repeated patterns;
10. spread/transaction-cost assumptions;
11. exact seven-major universe and whether results are pooled or pair-specific.

## Anti-hallucination rule

Do NOT fill missing methodology with generic candlestick lore, broker blogs, TradingView conventions, or our own preferred R multiple and then call it an Alanazi replication.

A separate "engulfing-inspired" V0 could be created later, but it must be labelled as an adaptation and its rules frozen independently before any outcomes are read.

## Decision

D030 stays behind D023/D022/D027/D028 today. If the full methodology is recovered faithfully, it becomes a strong candidate for the next research batch and may be preferable to adding another indicator-based strategy.
