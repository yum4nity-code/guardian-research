# R8 BTC/ETH Relative-Value Mean-Reversion — Preregistration

Date: 2026-09-12
Status: frozen before execution

## Scientific rationale

R7 single-market BTC/ETH feature-tail directional rules are CLOSED after pre-OOS economic robustness failed 0/8 under frozen 10/20 bps costs. R8 is not a retune or rescue. It tests a genuinely different mechanism: temporary relative-value dislocation between BTC and ETH with a market-neutral two-leg position.

## Data and protection

Inputs are the existing local files under `D:\MT5_Backtests\Research\Data\R7_LongHistory`:
- `BTCUSDT_spot_5m_2017_2025.csv`
- `ETHUSDT_spot_5m_2017_2025.csv`

Rows at or after 2026-01-01 are forbidden and cause fail-closed execution. Inputs are synchronized and resampled to complete H1 bars only. No 2026 file or row may be opened.

## Frozen chronology

- Discovery/development: 2018-01-01 through 2022-12-31.
- Independent confirmation: 2023-01-01 through 2024-12-31.
- Pre-OOS temporal gate: 2025-01-01 through 2025-12-31.
- Protected final OOS: 2026, forbidden in R8 v1 and not considered unless all pre-OOS gates pass.

All candidate definitions are enumerated and evaluated on discovery first. The survivor set is frozen before confirmation metrics are computed. Confirmation survivors are frozen before 2025 metrics are computed.

## Frozen strategy family

On synchronized H1 closes define `spread = log(BTC close) - log(ETH close)`. For each rolling lookback L, compute prior-bar-only mean and standard deviation (`shift(1)`), then z-score the current completed bar against those prior values.

Grid (54 exact definitions):
- lookback hours: 72, 168, 336
- entry absolute z: 1.5, 2.0, 2.5
- exit absolute z: 0.0, 0.5
- maximum hold hours: 24, 48, 96

Signal/entry is causal: a threshold crossing is known only after H1 bar close; both legs enter at the next synchronized H1 open. If spread is high, short BTC / long ETH. If spread is low, long BTC / short ETH. Exit occurs at the first subsequent H1 open after the completed prior bar has reverted inside the frozen exit threshold, or at max hold, whichever comes first. One pair position at a time. No pyramiding. Entries/exits crossing a calendar-year boundary are rejected for stage metrics.

Pair gross return is equal-notional: `0.5 * BTC_leg_return + 0.5 * ETH_leg_return` using open-to-open simple returns with opposite leg directions.

## Frozen costs

Costs are applied to portfolio notional per complete pair trade:
- E1: 10 bps round trip total portfolio cost (0.001)
- STRESS: 20 bps round trip total portfolio cost (0.002)

These are reject-only screens, not parameters to optimize.

## Gates

Discovery candidate must have at least 80 completed trades, positive E1 and STRESS net mean trade return, positive E1 net sum in at least 4 of the 5 full years 2018-2022, and aggregate one-sample two-sided normal-approx p < 0.01 on E1 net trade returns.

Discovery survivors are frozen before opening 2023-2024. Confirmation requires at least 30 trades, positive E1 and STRESS net mean, positive E1 net sum separately in 2023 and 2024, and BH-FDR q <= 0.05 across frozen discovery survivors.

Confirmation survivors are frozen before opening 2025. The 2025 pre-OOS gate requires at least 15 trades; positive E1 and STRESS net mean; positive E1 net sum in H1 and H2 separately; positive STRESS net sum after removing the single best trade; and no single STRESS trade contributing more than 35% of positive gross contribution when aggregate STRESS net is positive.

A PASS means only a frozen pre-OOS relative-value candidate exists. It is not an EA and does not authorize live deployment.

## Mandatory preflight

Before market-data execution, deterministic tests must verify: prior-bar-only z-score construction; next-open entry; exit timing; one-position semantics; symmetric two-leg PnL signs; cost subtraction; missing-hour fail-closed behavior; calendar-year boundary purge; and rejection of any 2026 row.

## Post-result rule

If 0 candidates pass, close R8 without rescue and move to a genuinely independent family. If candidates pass, freeze exact definitions and run a separate reject-only robustness/red-team stage before any protected OOS consideration.