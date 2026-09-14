# XAUUSD Edge Discovery Program — R16 to R20

Status: preregistered research batch after final R15 v1.01 scientific FAIL.

## Why this batch exists

R15 replicated the historical GLD→XAUUSD relation but failed independent 2019H2–2024 confirmation. We therefore do **not** optimize R15 parameters. The next work searches distinct, falsifiable XAUUSD phenomena.

## Frozen research doctrine

1. Phenomenon first, strategy second.
2. No parameter torture and no large P&L-first grid search.
3. Every hypothesis must be directionally declared before inspection.
4. Causal features only: information available at or before event time.
5. Discovery/replication → independent multi-year confirmation → economic/cost gate → pre-OOS 2025.
6. Protected 2026 remains sealed until a candidate has passed every prior gate and a separate validation plan is frozen.
7. A FAIL may inform the next experiment, but must never be tuned until it becomes a PASS.
8. Report nulls and sign reversals, not only survivors.

## Batch

### R16 — Asian range → London
Primary question: after the Asian range is frozen, does a London breach predict continuation or a false-break reversal?

Predeclared measurements:
- Asian high/low and range;
- first London close outside the Asian range;
- breakout direction and normalized displacement;
- re-entry into the Asian range within a fixed number of bars;
- forward direction-adjusted returns.

Competing hypotheses are evaluated on the same events:
- H16A: breakout continuation;
- H16B: false-break/re-entry reversal.

### R17 — COMEX / New York opening impulse
Question: does the pre-open impulse predict post-open continuation or reversal?

Predeclared windows:
- pre-open: 5, 15, 30 minutes;
- post-open: 15, 30, 60, 120 minutes.

Report raw and direction-adjusted post-open returns. Volatility stratification is descriptive at discovery stage, not an optimization grid.

### R18 — Volatility shock
Question: after an unusually large M5 bar relative to trailing realized volatility, does XAUUSD continue or mean-revert?

Frozen event score:
`abs(current return) / trailing return standard deviation`

Forward horizons:
1, 2, 4, 8, 16 bars.

Thresholds are a small preregistered set, not an unconstrained search.

### R19 — Previous-day high / low
Question: near PDH/PDL during London or New York, is the dominant phenomenon breakout continuation or rejection?

Use prior trading-day levels only. Never use current-day high/low as a substitute.
Distances are reported both in dollars and normalized by trailing ATR-like true range.

### R20 — Round-number interaction
Question: when XAUUSD approaches or crosses round-number levels, is subsequent movement continuation or rejection?

Frozen level increments:
- $10
- $25
- $50
- $100

Report approach/touch/cross state, nearest level, signed distance, session, and forward returns.

## Data policy

The batch consumes the existing same-terminal XAUUSD research CSV format:
`symbol,timeframe,server_time,server_epoch,open,high,low,close,...`

The runner hard-rejects any 2026 row. By default it also excludes 2025. `--stage preoos` is the only mode allowed to admit 2025, and still rejects 2026.

Research code does not unlock protected 2026.

## Interpretation

The first pass asks only whether a reproducible distribution shift exists and is large enough to justify deeper work. It is not an EA backtest and does not optimize entries, stops, targets, sizing, or P&L.
