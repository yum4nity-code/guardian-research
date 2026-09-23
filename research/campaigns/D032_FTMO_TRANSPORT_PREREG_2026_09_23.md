# D032 Bullish Doji Star H1 — FTMO Feed/Execution Transport

Date: 2026-09-23
Status: FROZEN BEFORE FTMO TRANSPORT OUTCOME

## What is already confirmed

D032-C1 confirmed the Bullish Doji Star H1 entry on an independent pre-2024 CFD sample:
- BTC/ETH/DOG core n=79
- mean executable +24h = +133.52 bp/event
- median = +93.43 bp
- win rate = 64.56%
- mean = +0.588R/event
- month-block bootstrap 95% lower bound ~+10.1 bp
- 3/3 core symbols positive
- Doji minus same-trend control differential +101.38 bp

The pattern/trend definition is frozen and must not be retuned.

## Purpose of this run

Test transport to the FTMO market feed and executable BID/ASK outcome.
This is not a new alpha search.

## Frozen signal

Bullish Doji Star H1:
- previous H1 candle bearish;
- previous real body is long versus the prior 10 real bodies using TA-Lib default BodyLong semantics;
- current H1 candle is a doji: real body <= 10% of the average prior-10 high-low ranges;
- current real body gaps below the previous real body;
- SMA(144) is strictly falling across seven consecutive H1 values: MA[t-6] > ... > MA[t].

Signal time = end of the H1 pattern candle.

If Python TA-Lib is available, the reconstructed numerical signal must match positive CDLDOJISTAR occurrences under the same trend filter; any material mismatch aborts the run.

## Core FTMO symbols

Try:
- BTCUSD
- ETHUSD
- DOGUSD / DOGEUSD aliases if present

Unavailable symbols are reported, never substituted by unrelated markets.

## Windows

Use FTMO history only through 2025-12-31:
- PRE2024 transport view: signals whose +24h endpoint remains before 2024-01-01
- 2024-2025 transport view: signals whose +24h endpoint remains before 2026-01-01
- pooled view also reported

2026 raw data is hard-blocked.

## Execution

For every frozen FTMO-feed signal:
- LONG entry = first available ASK at/after H1 signal close;
- exit = first available BID at/after exactly +24h;
- historical tick is preferred;
- M1 open + recorded spread is fallback only if tick history is absent.

Report:
- event count;
- executable coverage;
- mean/median/win rate in bp;
- source-risk-normalized R using 1R = 2 * stdev(previous 24 H1 returns);
- symbol/year breakdown;
- trim-best 1/2/5%;
- extra-cost grid after observed BID/ASK;
- current FTMO symbol metadata separately.

## Interpretation

This run answers whether the already-confirmed D032 entry mechanism transports to FTMO.
It does not validate the rejected -1R/+3R management and does not authorize a new stop/TP.
The canonical reference remains immediate LONG entry and exact +24h exit.

No retuning, neighboring candlestick thresholds, RSI filters, reclaim entry, or alternate horizon is allowed.

2026 remains blocked.
