# GuardianEdgeForward V100

Frozen forward-shadow implementation for corrected Guardian ranks 7 and 9.

## Frozen hypotheses

- Rank 7: price_USDJPY_zret_60m LO AND price_USDCHF_rv_60m HI -> LONG DXY.cash for 15m
- Rank 9: price_XAUUSD_rv_60m HI AND price_GBPUSD_ret_30m HI -> SHORT GBPUSD for 30m

## What the EA does

- Reproduces the frozen feature definitions on the exact 5-minute research grid, including the original missing-bar semantics: ret30 only needs its two endpoints, while rv60/zret60 use up to the last 12 5-minute returns with min_periods=6 and sample std.
- Evaluates causal state using PRIOR expanding mean/std statistics, then appends the current feature value with Welford n/mean/M2 updates for numerical stability.
- Samples rank 7 every 15 minutes and rank 9 every 30 minutes.
- Writes shadow signals only.
- Contains no live order-sending code.
- Persists causal running statistics after every processed M5 decision and replays any missed M5 decisions after a restart instead of silently skipping them.

## Hard 2026 protection

The EA has a hard activation floor at 2027-01-02 00:00 server time. Before that time OnInit() returns INIT_FAILED before any feature calculation or signal logging.

The one-day buffer is deliberate because the research clock and FTMO clock were shown to differ. The stricter gate is the seed requirement below: no real seed is shipped in V100.

Do not weaken either gate while 2026 remains the protected research holdout.

## Required state seed

The EA refuses to initialize until the Common Files CSV below exists:

GuardianEdgeForward\state_seed_v100.csv

CSV format:

feature,n,mean,m2,last_decision_time

Required feature rows:

- price_USDJPY_zret_60m
- price_USDCHF_rv_60m
- price_XAUUSD_rv_60m
- price_GBPUSD_ret_30m

All rows must carry the same audited last_decision_time.

The real seed must be generated only after the full 2026 holdout is intentionally released. It must represent the exact research/live lineage: 2010-2022 research foundation, validated FTMO continuation through 2026, then live continuation from 2027 onward.

The shipped template is intentionally unusable.

## Restart behavior

After first initialization, the EA writes:

GuardianEdgeForward\runtime_state_v100.csv

That file stores all four cumulative state statistics and the last processed M5 decision. On restart the EA resumes from it and sequentially catches up missing 5-minute decisions. Replayed signals are explicitly marked replayed=true and target_tick_fresh=false.

## Deployment stage

V100 is compile + audit + shadow package only. Do not copy or attach it to a trading account before the protected 2026 holdout is released.
