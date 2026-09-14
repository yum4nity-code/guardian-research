# R18 FTMO Execution Cost Capture Protocol v1.00

Purpose: obtain the missing independent execution-cost evidence for R18 without opening 2025/2026 historical OOS and without changing the phenomenon.

## What must be measured

On the user's FTMO MetaTrader 5 environment for XAUUSD:

1. Bid and Ask on every tick.
2. M5 bar OHLC and close time.
3. R18 shock score using the frozen definition: current close-to-close return divided by sample stdev of the previous 48 contiguous M5 returns; event if absolute score >= 2.0.
4. At each R18 event, capture the first executable quote after the shock bar closes / next M5 begins.
5. Record spread in both price units and basis points at that quote.
6. Record direction-specific executable entry price: Ask for contrarian long after a negative shock; Bid for contrarian short after a positive shock.
7. For the frozen 1b, 2b, 4b, 8b and 16b exits, record direction-specific executable exit quote: Bid to close long; Ask to close short.
8. Compute realized quote-to-quote round-trip spread cost in basis points for each frozen horizon.
9. If an actual micro-size market-order probe is later explicitly authorized, separately record requested price, fill price, execution latency and signed slippage. Do not place trades as part of this measurement protocol unless explicitly authorized.

## No tuning

Do not change:
- M5 timeframe
- 48-return lookback
- 2.0 shock threshold
- contrarian direction
- frozen horizons

Do not filter by session, direction, shock magnitude, news, spread, weekday or volatility after observing results.

## Decision rule

Compare the independently observed all-in execution cost distribution with the already frozen non-overlap break-even budgets. Commission is included separately using the applicable FTMO Metals CFD rate.

R18 can advance only if a realistic, independently justified execution-cost assumption leaves positive expected net value. The result must be reported for both primary horizons 1b and 2b. Secondary horizons remain descriptive and cannot replace a failed primary gate post hoc.

## OOS protection

This is prospective execution-cost measurement, not a return-performance OOS test. It must not inspect the protected historical 2025 pre-OOS returns or protected 2026 historical performance sample.
