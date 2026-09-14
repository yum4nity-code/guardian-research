# XAUUSD Edge Discovery Program — R16 to R20

Status: preregistered research batch after final R15 v1.01 scientific FAIL.

## Why this batch exists

R15 replicated the historical GLD→XAUUSD relation but failed independent 2019H2–2024 confirmation. We therefore do **not** optimize R15 parameters. The next work searches distinct, falsifiable XAUUSD phenomena.

## Frozen research doctrine

1. Phenomenon first, strategy second.
2. No parameter torture and no large P&L-first grid search.
3. Every hypothesis is directionally declared before inspection.
4. Causal features only: information available at or before event time.
5. Discovery/replication → independent multi-year confirmation → economic/cost gate → pre-OOS 2025.
6. Protected 2026 remains sealed until a candidate has passed every prior gate and a separate validation plan is frozen.
7. A FAIL may inform the next experiment, but must never be tuned until it becomes a PASS.
8. Report nulls and sign reversals, not only survivors.

## Frozen stage boundaries

To preserve the independent boundary already used by Guardian/R15:

- `discovery`: all eligible history strictly before **2019-07-01**;
- `confirmation`: **2019-07-01 through 2024-12-31**;
- `preoos`: **2025-01-01 through 2025-12-31** only;
- **2026 is hard rejected in every mode**.

The code must not silently combine discovery and confirmation samples.

## Batch

### R16 — Asian range → London
Primary question: after the Asian range is frozen, does a London breach predict continuation or a false-break reversal?

Frozen clocks are DST-aware local-market clocks:
- Asian range: 00:00–07:00 `Europe/London`;
- London event window: 08:00–12:00 `Europe/London`;
- first M5 close outside the Asian range is the breakout event;
- false break requires a confirmed close back inside the range within 3 M5 bars.

Competing hypotheses:
- H16A: breakout continuation, returns anchored at the breakout close;
- H16B: false-break reversal, returns anchored **after the re-entry confirmation close**. This avoids conditioning on future re-entry while measuring from the earlier breakout bar.

### R17 — COMEX / New York opening impulse
Question: does the pre-open impulse predict post-open continuation or reversal?

Frozen event clock: 08:20 `America/New_York` (DST-aware).
Pre-open windows: 5, 15, 30 minutes.
Post-open windows: 15, 30, 60, 120 minutes.

### R18 — Volatility shock
Question: after an unusually large M5 bar relative to trailing realized volatility, does XAUUSD continue or mean-revert?

Frozen event score:
`abs(current return) / stdev(previous 48 contiguous M5 returns)`

Frozen descriptive thresholds: 2.0, 2.5, 3.0.
Forward horizons: 1, 2, 4, 8, 16 M5 bars.

### R19 — Previous-day high / low
Question: near PDH/PDL during London or New York, is the dominant phenomenon breakout continuation or rejection?

Use prior UTC trading-day levels only; never current-day high/low. Proximity is frozen at 0.20 of trailing 14-bar true range, while exact touches are always retained.

### R20 — Round-number interaction
Question: when XAUUSD approaches or crosses round-number levels, is subsequent movement continuation or rejection?

Frozen increments: $10, $25, $50, $100.
Frozen proximity: 10% of the relevant increment, or an exact intrabar touch.
Report approach/touch/cross state, nearest level, signed distance, session and forward returns.

## Data policy

R15 left a quality-controlled Dukascopy XAUUSD M1 master cache locally under the Guardian data root. That cache is the preferred historical source. It is **not stored in this Git repository**, so this repository does not pretend to parse or open opaque cache files without the local R15 data contract.

R16–R20 consumes a deterministic M5 research CSV with:
`symbol,timeframe,server_time,server_epoch,open,high,low,close,...`

When the local R15 M1 master cache is used, M5 must be derived deterministically from five contiguous M1 bars: first open, max high, min low, last close. Incomplete/non-contiguous five-minute buckets are dropped, never filled.

The runner validates strict timestamp monotonicity, rejects gaps for forward-return calculations, applies the frozen stage boundaries above, and hard-rejects any 2026 row before analysis.

## Interpretation

The first pass asks only whether a reproducible distribution shift exists and is large enough to justify deeper work. It is not an EA backtest and does not optimize entries, stops, targets, sizing or P&L.
