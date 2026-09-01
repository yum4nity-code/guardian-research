# D017 / v11.16 — PRE-OOS GENERALIZATION CAMPAIGN

STATUT: ACTION_REQUISE

CONSTAT
The user has downloaded approximately one year of tick data under `D:\MT5_Backtests\incoming\` for these additional markets: `AUDUSD`, `EURJPY`, `NZDUSD`, `USDCAD`, `USDCHF`, `XAUUSD`.

The user explicitly authorizes launching a frozen v11.16 generalization campaign now, using available MT5 workers if possible.

OBJECTIVE
Test whether the already-frozen v11.16 Momentum implementation generalizes beyond EURUSD/GBPUSD without changing the strategy. This is a robustness/generalization screen, not an optimization campaign.

EXECUTION AUTHORIZATION
- May launch now in parallel with the active MiMo work **only if MT5 workers are actually idle/available and launch does not duplicate or preempt an existing MT5 job**.
- Preserve the active MiMo job; do not stop/restart MiMo merely to start these tests.
- Inspect real worker/process state before launch.
- Use the worker farm / existing centralized worker orchestration, not ad-hoc duplicate terminals.
- If fewer than six workers are safely available, queue remaining symbols and run as workers free up.

FROZEN EXPERT / SEMANTICS
Use `candidates/for_guardian/Guardian_D017_PropFirmAuto_v11_16_MOMENTUM_PROD.mq5` (or the verified local equivalent matching the accepted v11.16 candidate).

Do not tune or alter strategy semantics. In particular preserve:
- Momentum only;
- Breakout/Pullback/Sweep disabled;
- strategy time-stop OFF;
- classic setup TF M15;
- classic macro/context H1;
- classic session filter 07:00–17:00 UTC;
- existing v11.16 risk, SL, TP1/BE/trailing, ranking, spread, quality, news/prop safety semantics;
- one frozen run per symbol for this first screen.

MARKETS
1. AUDUSD
2. EURJPY
3. NZDUSD
4. USDCAD
5. USDCHF
6. XAUUSD

DATA / PERIOD
- First verify tick files/import/custom-symbol coverage and record provenance for each market.
- Preferred common in-sample period: `2025-08-28` through `2026-06-28`, matching the historical D017 pre-OOS end.
- If one or more new tick sets do not reach 2025-08-28, choose the earliest common date actually covered by all six symbols and freeze that date for the whole six-market campaign before any result is read.
- Hard end date for this campaign: `2026-06-28`.
- **DO NOT OPEN OR USE THE LOCKED OOS WINDOW 2026-06-28 -> 2026-08-28.** No peeking, aggregate inspection, parameter adjustment or result-based use of that period during this stage.
- Prefer real ticks / imported tick data, not synthetic OHLC shortcuts.

PRE-REGISTRATION BEFORE FIRST RUN
Before launching the first symbol, persist a tiny campaign manifest containing:
- exact source/hash or verified executable identity;
- exact symbol/custom-symbol mapping;
- fixed start/end dates;
- modeling mode;
- account size / cost model;
- unchanged v11.16 inputs/invariants;
- the six-symbol list;
- explicit statement `NO_TUNING / ONE_RUN_PER_SYMBOL / OOS_LOCKED`;
- simple pass/fail or candidate-screen criteria chosen BEFORE reading any of these six results. Do not lower criteria after results.

RESULTS TO HARVEST FOR EACH SYMBOL
At minimum persist:
- net profit;
- Profit Factor;
- max equity drawdown % and $;
- trade count;
- win rate;
- expected payoff;
- Sharpe if MT5 report provides it;
- monthly P&L distribution;
- data quality / tick count / bar count;
- gross profit vs estimated/actual costs where available;
- any execution/profiling anomaly.

PORTFOLIO STEP AFTER ALL SIX RUNS
Do not simply keep every profitable symbol. After all six frozen runs:
- compare return/P&L correlation where trade/equity series are available;
- identify overlapping USD exposure and simultaneous drawdowns/trades;
- treat AUDUSD/NZDUSD/USDCHF as potentially correlated USD bets rather than independent edges;
- evaluate EURJPY and XAUUSD separately for diversification contribution;
- explicitly compare USDCAD against its previously weak/marginal evidence rather than tuning it to improve.

OOS GATE
Do not run the locked OOS automatically. First publish the six-market in-sample results and portfolio/correlation screen, then freeze which symbols (if any) qualify for OOS and the criteria used. Only after that may a separate OOS action be authorized under the existing research protocol.

INTERACTION WITH OTHER QUEUE ITEMS
- This campaign does NOT supersede the active MiMo job.
- It does NOT supersede `D017-V11-16-EXACT-FEED-CONTROL`; that remains a separate technical non-regression control.
- It does NOT replace D021 MICRO-REV; D021 remains an independent strategy-research lane.
- This campaign is permitted to use idle MT5 workers now because it is a frozen, no-tuning, pre-OOS generalization test.

ACTION_CODEX
1. Reconcile worker/process state and incoming tick data.
2. Pre-register the campaign manifest before reading results.
3. Launch as many of the six frozen v11.16 runs in parallel as safely available workers permit.
4. Queue the rest without duplicates.
5. Harvest results atomically and update checkpoint/queue.
6. Report concise status: workers used, symbols running/completed, progress, failures, and any data/import blocker.

NE_PAS_FAIRE
- no parameter optimization;
- no symbol-specific tuning;
- no selecting a different timeframe per symbol;
- no opening OOS;
- no relaunching duplicate workers/tests;
- no modifying production Guardian from this campaign;
- no stopping MiMo just to free attention for this campaign.