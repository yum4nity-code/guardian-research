# D046 — BTC 08:00 UTC Deribit expiry reversal screen V0

Date: 2026-09-07 Europe/Paris
Status: **PREREGISTERED / OUTCOMES UNOPENED**

## Scientific role

D046-A is a low-cost **unconditional screening experiment** motivated by the documented BTC option-expiry reversal around Deribit's 08:00 UTC daily option expiration.

It is intentionally **not** a replication of the high-open-interest paper result. The historical ATM option-OI series required for that replication is not available from Deribit's public current-state API. D046-A asks a narrower question first:

> Is the unconditional BTC price pattern around 08:00 UTC already strong enough, after executable FundedNext spread and frozen crypto commission, to justify acquiring/reconstructing historical Deribit ATM open interest?

A failure of D046-A rejects only the **unconditional** screen. It does **not** falsify the paper's high-OI mechanism. A pass only authorizes the separate OI-gated research step; it does not authorize Guardian trading.

## Prior evidence / mechanism

External research published in 2026 reports a BTC return reversal around Deribit option expiry, concentrated when at-the-money option open interest is elevated. Deribit BTC daily options expire at 08:00 UTC. The economic mechanism is event-time/options-market structure, making this family intentionally orthogonal to Guardian's rejected generic Momentum/RSI entry families and to the daily breakout benchmarks.

The repository already contains a read-only forward observer at `research/external_intelligence/deribit_expiry_observer_v1.py`, which captures current 0DTE ATM OI around 07:00 UTC for future prospective evidence. D046-A does not consume that observer and does not use future information.

## Frozen market and execution

- Symbol: `BTCUSD` only.
- Broker profile: FundedNext.
- Tester model: `0` / Every tick.
- Tester period: M1, but entry/exit use first executable tester tick at/after each frozen UTC boundary.
- No orders are sent; the EA is a virtual-event research harness.
- No indicator, trend filter, volatility filter, weekday filter or OI filter.
- No stop loss, take profit, break-even, trailing or partial close.
- No position overlap: PRE leg is closed before POST leg is opened.

### Leg A — pre-expiry short

1. On each eligible UTC day, enter virtual SHORT on the first executable tick at or after **07:00:00 UTC**.
2. Entry uses executable BID.
3. Close on first executable tick at or after **08:00:00 UTC** using executable ASK.

### Leg B — post-expiry long

1. On the same eligible UTC day, after Leg A is closed, enter virtual LONG on the first executable tick at or after **08:00:00 UTC**.
2. Entry uses executable ASK.
3. Close on first executable tick at or after **09:00:00 UTC** using executable BID.

For every boundary, the first executable tick must arrive within **300 seconds** of the target UTC time. Otherwise that leg/day is ineligible rather than filled optimistically.

A paired eligible day requires both PRE_SHORT and POST_LONG to be eligible.

## Frozen server-time to UTC conversion

MT5 Strategy Tester does not preserve a historical broker GMT offset; in testing `TimeGMT()` cannot be used to recover true UTC independently from simulated server time. Therefore D046 freezes the FundedNext server conversion explicitly.

For this experiment the server is interpreted as:

- GMT+2 outside the US-DST server season;
- GMT+3 during the US-DST server season.

Frozen +3 intervals:

- 2024-03-11 00:00 server through 2024-11-04 00:00 server;
- 2025-03-10 00:00 server through 2025-11-03 00:00 server;
- 2026-03-09 00:00 server through 2026-11-02 00:00 server.

To avoid any one-hour ambiguity around broker clock changes, all UTC events whose server dates fall on these transition pairs are excluded entirely:

- 2024-03-10 / 2024-03-11;
- 2024-11-03 / 2024-11-04;
- 2025-03-09 / 2025-03-10;
- 2025-11-02 / 2025-11-03;
- 2026-03-08 / 2026-03-09;
- 2026-11-01 / 2026-11-02.

No outcome-dependent change to the offset table is allowed.

## Frozen cost model

Spread is embedded through actual executable BID/ASK tester ticks.

FundedNext crypto commission is frozen at **4 bps per side**, therefore:

- normal round-turn commission per one-hour leg: 8 bps;
- 1.5x commission stress: 12 bps.

For each leg:

- SHORT gross bps = `(entry_bid - exit_ask) / entry_bid * 10000`;
- LONG gross bps = `(exit_bid - entry_ask) / entry_ask * 10000`;
- net bps = gross bps - 8;
- stress net bps = gross bps - 12.

There is deliberately no R-based score because D046-A has no artificial stop denominator.

## Frozen stages

### Smoke — December 2023

- Window: 2023-12-01 through 2023-12-31.
- Engineering only.
- No profitability interpretation.
- Must compile 0 errors / 0 warnings, emit INIT/READY/FINAL lifecycle, clean executable prices, deterministic CSVs, at least several complete paired days, and demonstrate UTC-boundary delays <=300 seconds for eligible legs.

### Development — 2024-01-01 through 2025-12-31

Primary scientific screening window.

Frozen pass gates:

1. paired eligible days >= **600**;
2. mean PRE_SHORT net bps > **0**;
3. mean POST_LONG net bps > **0**;
4. mean combined paired-day net bps > **0**;
5. combined paired-day Profit Factor >= **1.10**;
6. total combined net bps in 2024 > **0**;
7. total combined net bps in 2025 > **0**;
8. total combined net bps under 1.5x commission stress > **0**;
9. deterministic month-block bootstrap 95% lower bound of combined paired-day mean net bps > **0**;
10. integrity failures = 0.

Month-block bootstrap: 20,000 resamples, deterministic seed **460800**. The resampling unit is UTC calendar month; paired daily combined outcomes within a sampled month remain together.

Verdicts:

- count gate failure: `INCONCLUSIVE_COUNT`;
- all gates pass: `UNCONDITIONAL_EXPIRY_SCREEN_PASS`;
- otherwise: `REJECT_UNCONDITIONAL_SCREEN`.

A development pass does not imply the high-OI paper mechanism is confirmed. It only justifies exact historical OI acquisition/reconstruction and fresh validation.

### Confirmation — 2026-01-01 through 2026-06-30

Locked until development passes and state is explicitly advanced.

Frozen confirmation gates:

1. paired eligible days >= **150**;
2. PRE_SHORT mean net bps > 0;
3. POST_LONG mean net bps > 0;
4. combined paired-day mean net bps > 0;
5. combined paired-day PF >= **1.05**;
6. combined 1.5x commission-stress total > 0;
7. month-block bootstrap 95% lower bound of combined daily mean > 0;
8. integrity failures = 0.

Failure verdict: `UNCONFIRMED_UNCONDITIONAL_SCREEN`.
Pass verdict: `UNCONDITIONAL_EXPIRY_SCREEN_CONFIRMED`.

Even a confirmed unconditional screen is not production-ready: historical OI attribution, prop-firm trading-rule review, live-forward timing/fill evidence, portfolio overlap and risk sizing remain separate requirements.

## Anti-overfitting boundary

After D046-A results are seen:

- do not shift 07:00 / 08:00 / 09:00 times;
- do not optimize holding duration;
- do not add weekdays, volatility regimes or indicators;
- do not alter the cost model;
- do not retune the DST mapping;
- do not inspect multiple nearby windows and choose the best one under D046-A.

Any such follow-up is a new preregistered experiment on fresh evidence.

## Canonical implementation

- source: `research/strategies/d046/D046_BTC_DeribitExpiryReversal_M1_v1_00.mq5`
- manifest: `research/experiments/D046.json`
- scorer: `research/runner/d046_expiry_score.py`
- one-command workflow: `research/runner/d046_expiry_workflow.py`
- result transport: isolated `backtest-results` events; legacy AutoSync is never used.
