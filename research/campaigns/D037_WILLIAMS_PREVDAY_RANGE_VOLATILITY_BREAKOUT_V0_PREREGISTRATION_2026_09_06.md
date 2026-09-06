# D037 — Williams-inspired Previous-Day Range Volatility Breakout V0

Date preregistered: 2026-09-06
Status: FROZEN BEFORE RESULT INSPECTION

## Research question

Can a simple previous-day-range volatility expansion rule produce a positive, broad, cost-robust intraday edge across the Guardian/FundedNext six-market universe without indicator filters or post-hoc tuning?

This is a Williams-inspired volatility-breakout adaptation, not a claim of verbatim reproduction of every historical Larry Williams rule. The documented core idea is preserved: measure the previous completed day's range and project breakout levels from the current day's open.

## Frozen universe

Exactly six symbols, one symbol per Strategy Tester run:
- BTCUSD
- ETHUSD
- EURUSD
- GBPUSD
- USDJPY
- XAUUSD

Execution timeframe: M15.
Reference timeframe: broker D1 bars.
Account currency must be USD.

## Frozen daily setup

For broker day D:
- `prev_range = High(D-1) - Low(D-1)` using the immediately preceding complete broker D1 bar.
- `day_open = Open(D)`.
- LONG trigger = `day_open + 0.50 * prev_range`.
- SHORT trigger = `day_open - 0.50 * prev_range`.

The 0.50 multiplier is frozen before testing and is not a parameter-search seed.

## Entry

- First valid threshold touched during broker day D wins.
- LONG uses executable ask-side price.
- SHORT uses executable bid-side price.
- If the market gaps beyond a threshold, fill at the worse executable observed price, not the theoretical threshold.
- Maximum one D037 trade per symbol per broker day.
- No reversal on the same day.
- If both thresholds become eligible within the same M15 bar and tick ordering cannot be reconstructed, mark the day ambiguous and do not score a trade. Do not choose the favorable side.

## Initial stop

- LONG stop = `entry - 0.50 * prev_range`.
- SHORT stop = `entry + 0.50 * prev_range`.
- No trailing stop.
- No break-even move.
- No take-profit.

This makes the initial stop distance use the same frozen volatility unit as the breakout threshold.

## Exit

Whichever occurs first:
1. initial stop, with gap-through filled at the worse executable price; or
2. end-of-broker-day exit at the final executable M15 close of day D.

No overnight carry into the next broker day.

## Filters explicitly forbidden

No RSI, EMA, ADX, ATR filter, day-of-week filter, news filter, direction bias, regime classifier, discretionary filter, symbol-specific multiplier, symbol-specific stop, or post-result rescue rule.

## Cost model

Same FundedNext cost semantics frozen for D036:
- Forex: USD 5 per lot per side.
- Metals: 0.0016% × lot × contract size × side execution price, per side.
- Crypto: 0.04% × lot × contract size × side execution price, per side.
- Spread from tester/executable-side prices.
- Money P/L and initial-stop money risk expressed as one-lot USD equivalents.
- Emit baseline net R and commission ×1.5 stress net R per trade.

## Mandatory integrity rules

A trade row is invalid and the run must end `FINAL_INVALID_*` if any of the following occurs:
- entry <= 0
- stop <= 0
- exit <= 0
- non-finite price or P/L
- initial risk <= 0
- opened != closed
- closed != CSV rows
- any fallback would convert an invalid market price into a valid P/L row

Any fallback calculation may be used only after all market prices have independently passed validity checks.

## Smoke stage

Dates: 2025-03-03 through 2025-03-31.
Representative cost classes:
- USDJPY
- XAUUSD
- BTCUSD

Stage name: `D037_SMOKE_MAR2025`.

Smoke is technical only. No alpha verdict from smoke P/L.

Required smoke pass:
- compile 0 errors / 0 warnings
- lifecycle clean
- positive valid prices only
- opened = closed = rows
- no invalid-risk or invalid-price event
- deterministic STATS/TRADES output

## Development stage

Dates: 2024-01-02 through 2025-12-31.
Stage name: `D037_DEV_2024_2025`.

All gates must pass:
- aggregate n >= 800
- each symbol n >= 80
- aggregate mean net R >= +0.05 R/trade
- aggregate PF >= 1.10
- at least 4 of 6 symbols positive total net R
- aggregate 2024 positive AND aggregate 2025 positive
- aggregate total remains positive at commission ×1.5
- no one symbol contributes more than 60% of positive-symbol net-R contribution
- zero invalid-price/PnL-integrity events

Any failed gate => `REJECT_V0`. No rescue tuning on the opened development sample.

## Untouched confirmation

Hard locked unless every development gate passes.

Dates: 2026-01-02 through 2026-06-30.
Stage name: `D037_CONFIRM_2026_H1`.

All confirmation gates must pass:
- aggregate n >= 180
- mean net R > 0
- PF >= 1.08
- at least 3 of 6 symbols positive
- aggregate positive at commission ×1.5
- zero integrity events

Failure => UNCONFIRMED. No parameter rescue.

## Decision discipline

The six-market development sample must be evaluated exactly as frozen here. Results may inform future independent hypotheses, but D037 V0 itself is either accepted for untouched confirmation or rejected. No K tuning, no symbol deletion, no direction deletion, no day-of-week rescue, and no exit rewrite after seeing 2024-2025 outcomes.
