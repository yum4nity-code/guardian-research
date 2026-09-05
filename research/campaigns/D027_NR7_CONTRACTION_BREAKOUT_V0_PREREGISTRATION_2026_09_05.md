# D027 — NR7 CONTRACTION BREAKOUT V0

Date: 2026-09-05
Status: PREREGISTERED / NOT YET RUN

## Why this family

This is a deliberately simple volatility-contraction -> expansion strategy derived from Toby Crabel's Narrow Range / Opening Range Breakout framework. It is not an RSI, ADX, EMA or generic Momentum variant.

Primary historical basis:
- Toby Crabel, *Day Trading with Short Term Price Patterns and Opening Range Breakout* (1990): NR4/NR7 contraction patterns and breakout logic.
- Toby Crabel, *Opening Range Breakout — A Century of Evidence* (2026 working draft): long-horizon ORB/contraction-expansion evidence across many futures markets.

This is a research basis, not proof that the transfer to FundedNext/FTMO FX/CFD data is profitable.

## Frozen V0 universe

Exactly four markets:
- EURUSD
- GBPUSD
- USDJPY
- XAUUSD

Input timeframe: M15, aggregated internally to Europe/London trading days.
Research period: 2024-01-01 through 2025-12-31 for the first manual MT5 campaign when possible. If a pre-OOS research dataset is used instead, timestamps >= 2026-06-28 00:00 UTC remain locked out.

## Frozen day definition

A trading day is a Europe/London calendar weekday from 00:00 inclusive to 24:00 exclusive, DST-aware. Weekend/non-trading gaps are skipped.

For each complete day D:
- daily range = high(D) - low(D);
- D is NR7 if its range is strictly the smallest of the seven most recent complete trading-day ranges including D;
- ties do NOT qualify.

Only information available by the end of D may be used to prepare D+1.

## Frozen trade rule on D+1

Only if D was NR7:
1. Reference high/low = full NR7 day D high/low.
2. From 07:00 inclusive to 16:00 exclusive London time on D+1, find the first M15 CLOSE strictly above the reference high or strictly below the reference low.
3. Long after the first close above; short after the first close below.
4. Entry = next M15 bar open, executable side when bid/ask history is available.
5. Initial stop = opposite edge of the NR7 reference range.
6. Exit = stop or final M15 close finishing by 16:00 London, whichever occurs first.
7. Maximum one trade per symbol per qualifying D+1. No reversal after the first breakout.

No ATR, RSI, EMA, ADX, day-of-week selector, news filter, direction bias, minimum/maximum range filter, volume filter or Guardian filter in V0.

## Mandatory diagnostics

Per symbol, per year, and aggregate:
- qualifying NR7 days;
- triggered trades;
- long/short counts;
- net R before and after execution costs;
- win rate;
- PF;
- median and mean R;
- MFE/MAE in R;
- stop rate;
- time-exit rate;
- monthly PnL concentration;
- 1.5x execution-cost stress;
- block-bootstrap confidence interval for mean daily strategy R.

## Frozen cheap-fail gates

V0 may become CANDIDATE only if all hold:
- >= 40 triggered trades on EACH symbol and >= 200 aggregate;
- >= 3 of 4 symbols positive net R;
- aggregate net PF >= 1.20;
- aggregate mean net R >= +0.10R/trade as a minimum research continuation gate;
- user's stronger production preference remains approximately >= +0.15R/trade, ideally +0.20R+;
- one-sided 95% moving-block-bootstrap lower bound of daily mean R > 0;
- aggregate PnL remains positive with execution costs x1.5;
- no single positive symbol contributes > 60% of total positive symbol contribution;
- no year is catastrophically dependent on the other year.

Failure => REJECT_V0. No threshold/window tuning after outcomes are opened.

## Scientific boundary

D027 tests contraction-expansion. It is related to ORB conceptually but is not D023: D023 breaks the same morning's 08:00-09:00 opening range every day; D027 trades only after a prior full-day NR7 contraction and breaks that prior contraction range.

If D027 and D023 both work, correlation/overlap is measured later before portfolio combination.
