# D021 — MICRO-REV M1 — preregistration V0

Status: `PREREGISTERED_CHEAP_FAIL / NOT A VALIDATED STRATEGY`

## Hypothesis

After an abnormal three-minute crypto price shock, an exhaustion candle followed by price and RSI confirmation has a positive short-horizon reversal expectancy after executable costs. Oversold/overbought RSI alone is not a signal. This is independent from D017 Momentum: it targets a short reversal after capitulation, not continuation.

## Economic and statistical rationale

The proposed mechanism is temporary price pressure and liquidity exhaustion after a rapid one-sided move, followed by confirmation that continuation has failed. The adverse prior is equally explicit: a retail liquidity taker may instead face informed-flow adverse selection, spread widening and slippage, which can erase or reverse the gross effect. This is why the first experiment measures executable quotes and stressed costs rather than optimizing an EA.

The design uses one primary horizon, sign-symmetric rules, fixed thresholds, non-overlapping events, equal symbol weighting and time-aware block bootstrap inference. Requiring agreement on both available markets limits a one-symbol discovery, while the sample and cost gates make the hypothesis cheaply falsifiable before additional trials.

## Locked sample and markets

- In-sample only: `2025-08-01 00:00:00` through `2026-06-27 23:59:59`.
- Locked OOS `2026-06-28` through `2026-08-28` must not be read or used.
- V0 markets: `BTCUSD_BT`, `ETHUSD_BT`.
- `SOLUSD` is excluded from V0 because no valid local imported history was found at preregistration time.
- M1 bars must be reconstructed from the existing bid/ask tick histories; histories must not be deleted or reimported.

## Locked event definition

Indicators use completed M1 bars: Wilder RSI(7), Wilder ATR(14), EMA(20) of close.

Long event:

1. `Close[t] - Close[t-3] <= -1.50 * ATR14[t]`.
2. `Close[t] <= EMA20[t] - 1.00 * ATR14[t]`.
3. `RSI7[t] <= 25`.
4. Lower wick of bar `t` is at least 40% of its full range and the close is at least 35% above its low.
5. Confirmation bar `t+1` closes above `Close[t]` and `RSI7[t+1] - RSI7[t] >= 3`.

Short events are the exact sign-symmetric counterpart, with `RSI7[t] >= 75`, an upper wick of at least 40%, close at least 35% below the high, a lower confirmation close and RSI decline of at least 3.

The event timestamp is the close of `t+1`. Overlapping events in the same direction and symbol are suppressed for ten minutes. Bars with missing ticks, zero ATR, or `spread / ATR14 > 0.10` are excluded by rule, not selected after results.

## Locked measurement

- Entry: first executable quote after the confirmation close; ask for long, bid for short.
- Exit horizons: +1, +3, +5 and +10 minutes. The sole primary horizon is +5 minutes; the others are descriptive secondary endpoints.
- Primary return: executable net return after observed bid/ask spread and configured broker commission.
- Cost stress: repeat with non-commission execution costs multiplied by 1.5.
- Barrier diagnostic: probability of reaching `+0.50 ATR` before `-0.50 ATR` within ten minutes, symmetrically by direction.
- Report MFE, MAE, event counts and results separately by symbol, direction and calendar quarter. No parameter ranking is allowed.

## Frozen cheap-fail gates

All gates must pass:

1. At least 100 non-overlapping events per symbol and at least 40 per direction; otherwise `FAIL_INSUFFICIENT_SAMPLE`.
2. Both symbols have positive mean net return at the primary +5 minute horizon.
3. The equally weighted two-symbol primary mean has a one-sided 95% stationary-block-bootstrap lower confidence bound above zero.
4. The primary mean remains positive under the 1.5x execution-cost stress.
5. The pooled barrier probability is above 0.50 with a one-sided 95% lower confidence bound above 0.50.

Failure of any gate rejects V0. No threshold may be changed within D021 after outcomes are opened. A materially different definition requires a new campaign and increments the trial ledger.

## Execution gate

Before running, the worker must persist: source file hashes, exact available date coverage, symbol specifications, commission assumptions, event-study code hash and confirmation that the OOS end is never requested. If any item is missing, execution fails closed.

No EA integration, optimization or long MT5 backtest is authorized by this preregistration. Only the cheap-fail event study may follow after the currently active MiMo job is harvested without duplication.
