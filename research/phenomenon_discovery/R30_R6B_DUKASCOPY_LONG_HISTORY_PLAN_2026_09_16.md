# R30 — R6B Dukascopy 2004-2025 capital characterization — 2026-09-16

## Question

If EUR 10,000 had been allocated to the frozen R6B breakout rules at 1x
notional exposure, how much capital would remain/grow over the longest pinned
XAUUSD history currently available?

This is a retrospective economic characterization, not an independent OOS
claim.

## Frozen candidates

R6B-347:
- XAUUSD LONG
- M5 lookback 96 bars
- breakout close > prior 96-bar high + 0.10 ATR14
- UTC signal session 00:00 <= hour < 08:00
- fixed horizon 96 source M5 bars

R6B-307:
- XAUUSD LONG
- M5 lookback 96 bars
- breakout close > prior 96-bar high
- UTC signal session 00:00 <= hour < 08:00
- fixed horizon 48 source M5 bars

No parameter search is permitted in R30.

## Market source

Pinned R15 Dukascopy XAUUSD BID M1 master index:
d77fb76e5b5ee0600a488c331084e70972a8800a33ae59a957c1044dc39ef566

Window:
- first available source day 2004-11-08
- last source day 2025-12-31
- 2026+ not opened

R30 builds raw yearly M1 and exact complete-bucket M5.

No historical news mask is invented. Therefore this is a raw-market
long-history version of the frozen R6B rules, not an exact reproduction of the
2024-2025 FundedNext news-clean signal feed.

## Execution

Each calendar year is replayed independently, matching the original R6
year-isolation style.

- signal after M5 close
- entry at first raw M1 open at/after signal-bar close
- exit at first raw M1 open at frozen M5 horizon boundary
- one position at a time per candidate
- exit processed before an equal-timestamp new signal

Cost profiles:
- E1 unchanged
- STRESS unchanged

## Capital model

Initial capital:
EUR 10,000 equivalent account units

Exposure:
1x notional on every accepted trade

Trade return:
net PnL per one XAU / entry XAU price

Compounding:
equity_next = equity * (1 + trade_return)

No leverage search.
No position-size optimization.
No reinvestment cap.

## Required outputs

For R6B-347 and R6B-307, under E1 and STRESS:
- ending capital from 10,000
- total return
- CAGR
- trade-close max drawdown
- total trades
- PF / expectancy / win rate
- yearly capital start/end
- yearly return
- yearly trade-close max drawdown
- profitable full years 2005-2025
- capital curve

## Interpretation

The result answers economic persistence across history.

It does not imply:
- future returns will match history;
- the Dukascopy BID feed is identical to a retail broker/CFD execution feed;
- intratrade mark-to-market drawdown equals the reported trade-close drawdown;
- any particular leverage level is safe.

## Protection

- no 2026 access
- no R6 retuning
- no R27 filter
- no news-filter invention
- no live deployment action
