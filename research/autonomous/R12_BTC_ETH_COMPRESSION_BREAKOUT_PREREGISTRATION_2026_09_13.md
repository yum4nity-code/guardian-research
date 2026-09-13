# R12 BTC/ETH Volatility-Compression Breakout — Preregistration

Date: 2026-09-13
Status: FROZEN BEFORE EXECUTION

## Rationale

R8 relative-value mean reversion, R9 calendar/session seasonality, R10 multi-day time-series trend and R11 cross-market lead-lag spillover are closed scientific failures under their frozen hypotheses. R12 is a genuinely independent mechanism family: volatility compression followed by a causal price-channel breakout. It is not a parameter rescue of any closed family.

## Inputs and protected-data boundary

Use only these existing local files under `D:\MT5_Backtests\Research\Data\R7_LongHistory`:

- `BTCUSDT_spot_5m_2017_2025.csv`, SHA256 `75d0d48dcfa7e649192d1eb2c96e89a591aa49bcfac11d394a1f84113264f6e8`
- `ETHUSDT_spot_5m_2017_2025.csv`, SHA256 `21b170675eae6bd2e3d442391e2acb9392abdff443f517b5cb0ee1946a12aa13`

Any row at or after 2026-01-01 UTC is forbidden and must fail closed. Protected 2026 must not be opened or inspected.

## Bar construction

Resample to UTC H1 bars from complete groups of exactly twelve 5-minute bars. Any H1 hour lacking exactly 12 source bars is absent. Signal evaluation and replay must fail closed across missing H1 hours.

## Frozen family

Exactly 72 deterministic definitions:

- asset: BTCUSDT, ETHUSDT;
- compression window: 24h, 72h;
- prior price-channel window: 24h, 72h;
- volatility-ratio threshold: 0.50, 0.70, 0.90;
- holding period: 6h, 12h, 24h.

For decision bar `t`, using only information available after that H1 bar closes:

1. Compute hourly log returns.
2. `recent_vol` = sample standard deviation of the `compression_window` hourly returns immediately preceding decision bar `t`; the return of decision bar `t` itself is excluded.
3. `baseline_vol` = sample standard deviation of the 168 hourly returns immediately preceding the recent-vol window; no overlap with recent-vol returns.
4. Require `baseline_vol > 0` and `recent_vol / baseline_vol <= frozen threshold`.
5. Build the channel from the highs/lows of the `channel_window` complete H1 bars immediately preceding `t`, excluding `t`.
6. If completed decision-bar close is strictly above prior channel high, direction = long. If strictly below prior channel low, direction = short. Otherwise no signal.
7. Enter at the next H1 open (`t+1h`). Exit at the H1 open `hold_hours` later.

No future bar contributes to compression, baseline, channel or direction. No overlapping positions within a definition; chronological one-position replay is mandatory. Any trade whose required history, entry, holding path or exit crosses a missing H1 hour fails closed. Trades crossing a calendar-year boundary are purged.

## Costs

Fixed round-trip return deductions:

- E1: 10 bps (`0.001`)
- STRESS: 20 bps (`0.002`)

No sizing, leverage or Challenge Lab may rescue alpha.

## Chronology and frozen gates

### Discovery: 2018-01-01 through 2022-12-31

A definition survives discovery only if all are true:

- at least 75 trades;
- E1 mean return > 0;
- STRESS mean return > 0;
- at least 4 of 5 calendar years have positive E1 net sum;
- two-sided normal-approximation p-value on E1 mean < 0.01.

Freeze exact surviving candidate IDs before any 2023-2024 confirmation calculation.

### Independent confirmation: 2023-01-01 through 2024-12-31

Across the frozen discovery survivors, apply Benjamini-Hochberg FDR 5% to E1 mean-return p-values. A candidate survives only if:

- at least 25 trades;
- E1 mean > 0 and STRESS mean > 0;
- 2023 E1 net sum > 0;
- 2024 E1 net sum > 0;
- BH q <= 0.05.

Freeze exact surviving candidate IDs before any 2025 computation.

### Pre-OOS temporal gate: 2025 only

A frozen confirmation survivor passes only if:

- at least 10 trades;
- E1 mean > 0 and STRESS mean > 0;
- Jan-Jun E1 net sum > 0;
- Jul-Dec E1 net sum > 0;
- STRESS net sum remains > 0 after deleting the single best STRESS trade;
- the largest positive STRESS trade is no more than 35% of total positive STRESS returns.

R12 scientific PASS requires at least one pre-OOS survivor. Otherwise R12 is closed as scientific FAIL without rescue.

## Mandatory preflight

Before the expensive run, deterministic tests must verify:

- exactly 72 unique definitions and stable candidate IDs;
- exact input hashes and protected-2026 rejection in the engine contract;
- complete-H1 construction only;
- compression and baseline windows exclude the decision-bar return and do not overlap;
- channel excludes the decision bar;
- causal next-H1-open entry and exact open-to-open exit;
- one-position replay;
- missing-hour fail-closed behavior;
- year-boundary exit purge;
- frozen costs and protected cutoff.

The preflight must PASS before execution.

## Promotion boundary

A R12 PASS is pre-OOS evidence only. It does not authorize protected 2026, EA promotion or live trading. Protected 2026 remains forbidden absent the owner's explicit approval and a separately committed final-OOS preregistration/job.
