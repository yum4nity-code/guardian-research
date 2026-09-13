# R10 BTC/ETH Multi-Day Time-Series Trend — Preregistration

Date: 2026-09-13
Status: FROZEN BEFORE EXECUTION

## Scientific question

Can a simple, low-turnover, causal multi-day time-series momentum rule on BTCUSDT and ETHUSDT survive long-history discovery, independent confirmation, 2025 pre-OOS and realistic round-trip cost stress without using protected 2026?

R10 is a genuinely independent family from R8 relative-value mean reversion and R9 UTC calendar/session seasonality. It does not use pair spreads, z-scores, weekday/session conditioning, or any R8/R9 selected thresholds. It is also evaluated on crypto rather than the XAU R6 family.

## Data and protection

Inputs are the existing immutable pre-2026 files:
- `BTCUSDT_spot_5m_2017_2025.csv`, expected SHA256 `75d0d48dcfa7e649192d1eb2c96e89a591aa49bcfac11d394a1f84113264f6e8`
- `ETHUSDT_spot_5m_2017_2025.csv`, expected SHA256 `21b170675eae6bd2e3d442391e2acb9392abdff443f517b5cb0ee1946a12aa13`

The engine must reject any input row timestamped `>= 2026-01-01T00:00:00Z` and any filename containing `2026`.

Complete H1 bars require exactly 12 underlying 5-minute bars. No forward-fill is permitted.

## Frozen chronology

- Warm-up/history availability begins in 2017.
- Discovery: 2018-01-01 through 2022-12-31.
- Independent confirmation: 2023-01-01 through 2024-12-31.
- Pre-OOS temporal gate: 2025-01-01 through 2025-12-31.
- Protected final OOS: 2026, FORBIDDEN in R10.

The complete discovery survivor set must be frozen before confirmation metrics are computed. The complete confirmation survivor set must be frozen before 2025 metrics are computed.

## Frozen signal family

Assets: BTCUSDT, ETHUSDT.

Decision frequency: one decision opportunity per UTC day, at the close of the H1 bar timestamped 00:00 UTC. Signal information uses only data available by that H1 close.

Lookback hours: `[24, 72, 168, 336]`.
Absolute momentum thresholds: `[0.01, 0.02, 0.04]` as decimal returns.
Holding periods: `[24, 72, 168]` hours.

For each asset/lookback/threshold/holding combination:
- compute momentum = `close_t / close_(t-lookback) - 1`;
- if momentum >= threshold, signal LONG;
- if momentum <= -threshold, signal SHORT;
- otherwise no trade.

There are exactly `2 * 4 * 3 * 3 = 72` frozen definitions.

## Causal execution and overlap semantics

For a signal generated from the completed H1 bar at time `t`, entry is the OPEN of the immediately following complete H1 bar at `t+1h`. Exit is the OPEN exactly `hold_hours` after entry.

A candidate uses one-position chronological replay. While a position is open, later signals for that candidate are ignored. A trade is rejected if any required H1 timestamp from decision through exit is missing, if entry/exit cannot be resolved exactly, or if decision and exit do not remain within the same evaluation year. Thus no return may cross discovery/confirmation/pre-OOS year boundaries.

Gross return is direction-adjusted simple return from entry open to exit open.

Costs are frozen round-trip deductions:
- E1: 0.0010 (10 bps)
- STRESS: 0.0020 (20 bps)

No sizing, leverage, stop-loss, take-profit or Challenge Lab is part of this test.

## Discovery gates — 2018-2022

A definition advances only if all are true:
- at least 80 completed trades;
- aggregate E1 mean > 0;
- aggregate STRESS mean > 0;
- at least 4 of 5 calendar years have positive E1 net sum;
- two-sided normal-approximation p-value of E1 trade returns < 0.01.

All advancing candidate IDs are sorted and hashed before any 2023-2024 confirmation metrics are computed.

## Confirmation gates — 2023-2024

Benjamini-Hochberg FDR is applied at 5% across all discovery survivors using their aggregate 2023-2024 E1 p-values.

A candidate advances only if all are true:
- at least 30 completed trades;
- aggregate E1 mean > 0;
- aggregate STRESS mean > 0;
- 2023 E1 net sum > 0;
- 2024 E1 net sum > 0;
- BH q-value <= 0.05.

The complete advancing ID set is sorted and hashed before any 2025 metric is computed.

## Pre-OOS gate — 2025

A candidate survives R10 only if all are true:
- at least 15 completed trades;
- aggregate E1 mean > 0;
- aggregate STRESS mean > 0;
- H1 2025 E1 net sum > 0;
- H2 2025 E1 net sum > 0;
- STRESS net sum remains > 0 after removing the single best STRESS trade;
- best positive STRESS trade contributes no more than 35% of total positive STRESS PnL.

## Interpretation

R10 PASS means only that one or more frozen rules survived all pre-2026 gates. It is not an EA and does not authorize production/live trading. Any surviving rules must be frozen and handled under the mandate before final protected OOS or later execution-fidelity work.

R10 FAIL closes this exact multi-day trend family/search space without same-sample rescue. The next campaign must be a genuinely independent mechanism/representation/market family.
