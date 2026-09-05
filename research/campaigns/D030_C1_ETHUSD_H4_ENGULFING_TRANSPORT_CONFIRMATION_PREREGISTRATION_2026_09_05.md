# D030-C1 — ETHUSD H4 Alanazi Engulfing transport confirmation

Date: 2026-09-05
Status: PREREGISTERED BEFORE PRE2024 ETH D030 OUTCOMES ARE INSPECTED
Classification: POSTHOC_SYMBOL_SELECTION / CFD_TRANSPORT_CONFIRMATION

## Why this exists
The frozen D030 seven-major FX replication failed on FundedNext CFDs. User-added ETHUSD was a non-primary adaptation/transport diagnostic and produced the only result above the project's nominal +0.15R threshold with a positive month-block bootstrap lower bound on 2024-2026.

Because ETH was selected after seeing that result, it is discovery only. This experiment freezes a separate untouched historical confirmation window before any D030 ETH outcomes from that window are opened.

## Frozen signal and management
Exactly the same D030 v1.01 rules; no tuning:
- H4 midpoint-quote candles reconstructed from tester BID/ASK;
- Alanazi full-wick bullish/bearish engulfing definition;
- no trend filter;
- entry at first executable price of next H4 candle (ASK long / BID short);
- stop exactly 5 pips beyond engulfing-candle midpoint low/high;
- target exactly 1:1 from executable entry to stop;
- spread embedded via BID/ASK;
- no Guardian, no live orders;
- no RSI, no direction filtering, no alternate RR.

## Primary market
ETHUSD only.

BTC/XAU/DOG/LNK/XRP are not part of this confirmation gate.

## Untouched confirmation window
Signals from **2019-01-01 00:00 through 2023-12-31 23:59**.

This interval is earlier than the D030 2024-2026 discovery sample and follows the main 2015-2018 out-of-sample interval discussed in the source paper. Tester may start earlier and end later only to construct H4 context and resolve late trades; eligibility is by signal timestamp.

## Primary endpoint
Executable realized R after embedded spread, before historical swap because exact historical FundedNext swap series is unavailable in the scanner.

## Frozen confirmation gate
ETH transport confirmation passes only if all are true:
1. >=250 completed eligible trades;
2. mean executable R > +0.15R/trade;
3. month-block bootstrap 95% lower bound of mean executable R >0;
4. both LONG and SHORT subsets have mean executable R >0;
5. both temporal halves 2019-2021 and 2022-2023 have mean executable R >0;
6. no single event contributes >10% of total positive executable R.

Failure means reject ETH H4 engulfing as a confirmed transport edge; do not tune trend, RR, direction, candle size, or sessions on the same confirmation interval.

## Cost / swap lock
A PASS on the primary gate is still not production approval.

The 2024-2026 discovery run embeds spread but excludes historical swap. Current run-time ETHUSD symbol properties reported points-based long and short swap of -385 with triple rollover day 5. Therefore after primary confirmation, the exact same event rows must undergo a separately documented adverse rollover stress using frozen assumptions. If reasonable swap stress drops expected net result below +0.15R/trade, the setup does not meet the project's production edge target even if its pre-swap entry signal confirms.

No cost assumption may be relaxed after seeing the pre2024 outcomes.

## Tester
Use the existing `D030_FX_Engulfing_H4_Alanazi_CloseReplication_v1_01.mq5`, M1 chart, `1 minute OHLC`, no input changes. Historical real ticks are unavailable on the old FundedNext interval, so this remains bar/tick-model confirmation rather than final live-execution proof.
