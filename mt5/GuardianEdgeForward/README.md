# GuardianEdgeForward V100

Frozen forward-shadow implementation for corrected Guardian ranks 7 and 9.

## Frozen hypotheses

- Rank 7: price_USDJPY_zret_60m LO AND price_USDCHF_rv_60m HI -> LONG DXY.cash for 15m
- Rank 9: price_XAUUSD_rv_60m HI AND price_GBPUSD_ret_30m HI -> SHORT GBPUSD for 30m

## What the EA does

- Reproduces the frozen feature definitions on completed M5 bars.
- Evaluates causal state using PRIOR expanding mean/std statistics, then appends the current feature value.
- Samples rank 7 every 15 minutes and rank 9 every 30 minutes.
- Writes shadow signals only.
- Contains no live order-sending code.

## Hard 2026 protection

The EA has a hard activation floor at 2027-01-01 00:00. Before that time OnInit() returns INIT_FAILED before any feature calculation or signal logging.

Do not weaken this lock while 2026 remains the protected research holdout.

## Required state seed

The EA also refuses to initialize until the Common Files CSV below exists:

GuardianEdgeForward\state_seed_v100.csv

CSV format:

feature,n,sum,sumsq

Required feature rows:

- price_USDJPY_zret_60m
- price_USDCHF_rv_60m
- price_XAUUSD_rv_60m
- price_GBPUSD_ret_30m

The real seed must be generated only after the full 2026 holdout is intentionally released. It must represent the exact research/live lineage: 2010-2022 research foundation, validated FTMO continuation through 2026, then live continuation from 2027 onward.

The shipped template is intentionally unusable.

## Deployment stage

V100 is compile + audit + shadow package only. Do not copy or attach it to a trading account before the protected 2026 holdout is released.
