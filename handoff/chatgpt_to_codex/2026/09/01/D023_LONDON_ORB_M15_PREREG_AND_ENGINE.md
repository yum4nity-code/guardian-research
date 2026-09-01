# D023 — LONDON OPENING RANGE BREAKOUT M15 V0

STATUT: PREREGISTERED / ENGINE PREPARED / REAL-DATA EXECUTION NOT YET DONE

## Why this exists

D023 is a fourth strategy family, distinct from D017 Momentum, D021 MICRO-REV and D022 PAIR-REV. It tests classic opening-range continuation rather than general momentum or mean reversion.

External rationale only, not validation for our markets:
- Holmberg, Loennbark & Lundstroem, Finance Research Letters 2013, "Assessing the profitability of intraday opening range breakout strategies" found empirical evidence of intraday trending with an ORB rule in crude oil futures. DOI 10.1016/j.frl.2012.09.001.
- Bulkowski, "Opening Range Breakout", Swing and Day Trading, Wiley 2012, documents the classic opening-range breakout concept.

Forex has no single exchange opening auction, so V0 explicitly anchors the experiment to the London participation shift rather than pretending there is a universal FX open.

## Frozen V0 universe

Exactly four markets:
- EURUSD
- GBPUSD
- USDJPY
- XAUUSD

Timeframe: M15.
OOS starts 2026-06-28 00:00:00 UTC and must never be read. Inputs must be physically PRE-OOS only.

## Frozen London-session rule

All session clocks are Europe/London local time and therefore DST-aware.

For every London weekday and symbol:
1. Opening range = high/low of exactly four M15 bars from 08:00 inclusive to 09:00 exclusive.
2. Search for the first M15 close strictly above the opening-range high or strictly below the opening-range low from 09:00 inclusive to 11:00 exclusive.
3. Long after the first close above; short after the first close below.
4. Entry = next M15 bar open, executable side of observed spread.
5. Stop = opposite edge of the opening range.
6. No take-profit in V0. This deliberately tests continuation itself instead of selecting an arbitrary TP after results.
7. Exit = stop or final M15 close finishing by 16:00 London, whichever comes first.
8. Maximum one trade per symbol per London day. No reversal after first breakout.

No EMA, RSI, ATR filter, day-of-week filter, range-size filter, news filter or direction bias may be added to V0.

## Costs frozen before results

Input M15 files must contain spread in PRICE UNITS.

Commission schedule is based on FTMO's published 29 Sep 2025 structure:
- Forex: USD 2.50 per standard lot per side.
- Metals CFD: 0.0007% of volume per side.

The engine converts the round-trip commission into a price-move equivalent per symbol and includes observed spread. It also repeats the result with all realized execution costs multiplied by 1.5.

If spread is unavailable, the engine fails closed as COST_MODEL_INCOMPLETE rather than producing a validation.

## Frozen cheap-fail gates

All must pass for CANDIDATE:
- >= 60 trades on EACH of the 4 symbols.
- >= 300 trades aggregate.
- >= 3 of 4 symbols have positive net R sum.
- aggregate net PF >= 1.20.
- one-sided 95% moving-block-bootstrap lower bound of daily mean R > 0.
- aggregate PnL remains positive under 1.5x execution-cost stress.
- no single positive symbol contributes > 60% of total positive symbol contribution.

Failure of any gate => REJECT_V0. No parameter tuning inside D023 after outcomes are opened.

## Engine already implemented by ChatGPT

File:
`d023_london_orb_m15_eventstudy.py`

SHA256:
`3788e8963b1c3a3c4213e29cf6fa212e29437e10d3c900c9e34261f637946b27`

Expected local destination after user installs it:
`D:\MT5_Backtests\automation\d023_london_orb_m15_eventstudy.py`

Validation already done before handoff:
- Python syntax compile PASS.
- End-to-end synthetic M15 test PASS on all four markets, 440 synthetic trades, deterministic CANDIDATE output. This validates plumbing only, not edge.
- Explicit OOS contamination test PASS: a row at 2026-06-28 00:00 UTC makes the engine abort with OOS_GUARD_FAIL.
- DST handling uses Europe/London via zoneinfo.

Outputs:
- D023_trades.csv
- D023_summary.json

## ACTION_CODEX

Do not rewrite or tune D023.
When higher-priority D017/D021/D022 work permits and the engine is visible locally:
1. locate/export compatible M15 OHLC+spread data for EURUSD, GBPUSD, USDJPY, XAUUSD;
2. physically clip to timestamps strictly before 2026-06-28 00:00 UTC;
3. preserve provenance/hashes;
4. execute D023 once;
5. persist outputs and apply the emitted verdict exactly;
6. no OOS and no second parameter attempt.
