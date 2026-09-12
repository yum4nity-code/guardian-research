# R9 BTC/ETH Calendar-Session Seasonality — Preregistration

Date: 2026-09-13
Status: frozen before execution

## Rationale
R8 BTC/ETH relative-value mean reversion is scientifically CLOSED after 0/54 discovery survivors. R9 is not a retune or rescue. It tests a genuinely independent information source: recurring UTC calendar/session effects in BTC and ETH, with no market-state feature, z-score, tail threshold, or pair-spread input.

## Data and protection
Use only existing local pre-OOS files under `D:\MT5_Backtests\Research\Data\R7_LongHistory`:
- `BTCUSDT_spot_5m_2017_2025.csv`
- `ETHUSDT_spot_5m_2017_2025.csv`

Any filename or row at/after 2026-01-01 causes fail-closed execution. Resample to complete H1 bars only (12 constituent 5m bars).

## Chronology
- Discovery: 2018-01-01 through 2022-12-31.
- Independent confirmation: 2023-01-01 through 2024-12-31.
- Pre-OOS temporal gate: 2025-01-01 through 2025-12-31.
- Protected final OOS: 2026; forbidden in R9 v1.

The full discovery survivor set is frozen before any confirmation metric is computed. Confirmation survivors are frozen before any 2025 metric is computed.

## Frozen family
At an H1 bar open, if UTC weekday and hour match a frozen rule, enter immediately at that open and exit at the exact H1 open after the frozen hold interval. Calendar information is known before entry; no future market value is used.

Grid: 672 exact definitions.
- asset: BTCUSDT, ETHUSDT
- UTC weekday: Monday..Sunday (0..6)
- UTC entry hour: 0, 4, 8, 12, 16, 20
- hold hours: 4, 8, 12, 24
- direction: long, short

A trade is rejected if the exact exit H1 bar is missing, if any intervening H1 bar is missing, or if entry/exit cross a calendar-year boundary. No pyramiding is possible for a single rule because each definition triggers once per week and max hold is 24h.

Gross return is direction times open-to-open simple return.

## Frozen reject-only costs
- E1: 10 bps round trip per trade (0.001)
- STRESS: 20 bps round trip per trade (0.002)

## Gates
Discovery requires at least 180 trades; positive E1 and STRESS mean; positive E1 net sum in at least 4 of 5 years 2018-2022; aggregate two-sided normal-approx p < 0.01 on E1 trade returns.

Discovery survivors are frozen before 2023-2024. Confirmation requires at least 80 trades; positive E1 and STRESS mean; positive E1 net sum separately in 2023 and 2024; BH-FDR q <= 0.05 across the frozen discovery survivor set.

Confirmation survivors are frozen before 2025. The 2025 gate requires at least 40 trades; positive E1 and STRESS mean; positive E1 net sum in H1 and H2 separately; positive STRESS net sum after removing the single best trade; and no single positive STRESS trade contributing more than 35% of total positive STRESS contribution.

PASS means only that a pre-OOS calendar/session candidate exists. It is not an EA and does not authorize live deployment or protected 2026 access.

## Mandatory preflight
Before market-data execution, deterministic tests must verify: protected-row rejection; complete-H1 resampling; exact UTC weekday/hour triggering; long/short PnL sign; cost subtraction; exact-exit and missing-hour fail-closed behavior; year-boundary purge; chronology separation; and candidate-count determinism (672).

## Post-result
If 0 candidates pass, close R9 without rescue and move to a genuinely independent mechanism/representation. If candidates pass, freeze exact definitions and run a separate reject-only robustness/red-team stage before protected OOS consideration.