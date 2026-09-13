# R11 BTC/ETH Lead-Lag Shock Spillover — Preregistration

Date: 2026-09-13
Status: frozen before execution

## Scientific rationale

R10 BTC/ETH multi-day time-series trend is CLOSED after a clean scientific FAIL at discovery (0/72 definitions); protected 2026 remained untouched. R11 is not a retune or rescue. It tests a different mechanism from R8 relative-value mean reversion, R9 calendar/session effects, and R10 own-asset multi-day trend: whether an unusually large completed move in one crypto asset transmits with delay to the other asset when the follower has not already made a comparable standardized move.

## Data and protection

Inputs are the existing immutable local files under `D:\MT5_Backtests\Research\Data\R7_LongHistory`:
- `BTCUSDT_spot_5m_2017_2025.csv`, SHA256 `75d0d48dcfa7e649192d1eb2c96e89a591aa49bcfac11d394a1f84113264f6e8`
- `ETHUSDT_spot_5m_2017_2025.csv`, SHA256 `21b170675eae6bd2e3d442391e2acb9392abdff443f517b5cb0ee1946a12aa13`

Rows at or after 2026-01-01 are forbidden and cause fail-closed execution. Inputs are independently converted to complete H1 bars, then inner-joined on timestamp. Any signal/lookback/holding path with a missing synchronized H1 bar is rejected. No 2026 file or row may be opened.

## Frozen chronology

- Discovery/development: 2018-01-01 through 2022-12-31.
- Independent confirmation: 2023-01-01 through 2024-12-31.
- Pre-OOS temporal gate: 2025-01-01 through 2025-12-31.
- Protected final OOS: 2026, forbidden in R11 v1 and not considered unless all pre-OOS gates pass and the owner explicitly approves a separately committed preregistration.

All definitions are enumerated before market-data evaluation. Discovery survivors are frozen before confirmation metrics are computed. Confirmation survivors are frozen before 2025 metrics are computed.

## Frozen signal and strategy family

For each synchronized completed H1 bar `t`, compute each asset's one-hour log return. Its volatility scale is the trailing 168-hour sample standard deviation using returns ending at `t-1` only (`rolling(168).std().shift(1)`). Thus the completed return at `t` cannot influence its own normalizer.

For leader lookback `L`, define `leader_z = log(close_t / close_{t-L}) / (sigma_leader_prior * sqrt(L))` and the analogous `follower_z` using the follower's own prior-only volatility scale. A shock is eligible when:
- `abs(leader_z) >= Z`, and
- `abs(follower_z) <= 0.5 * abs(leader_z)`.

The 0.5 lag-ratio is fixed once for the entire family and is not optimized. The follower is traded in the sign of the leader shock (continuation/spillover). The decision exists only after H1 bar `t` closes; entry is at the follower's next synchronized H1 open (`t+1h`); exit is at the synchronized H1 open after the frozen holding interval. One position at a time per definition, no pyramiding. Signals whose lookback, entry, or exit path is not hourly-contiguous, or whose decision/exit spans a calendar-year boundary, are rejected.

Exact grid (72 definitions):
- leader: BTCUSDT or ETHUSDT (the other asset is the follower)
- leader/follower shock lookback hours: 1, 3, 6
- absolute leader z threshold: 1.5, 2.0, 2.5
- follower holding hours: 1, 3, 6, 12

Candidate IDs are deterministic hashes of the complete serialized rule.

## Frozen costs

Follower-only round-trip portfolio costs per completed trade:
- E1: 10 bps (0.001)
- STRESS: 20 bps (0.002)

Costs are reject-only screens and are never optimized.

## Frozen gates

Discovery candidate must have at least 80 completed trades; positive E1 and STRESS mean net trade return; positive E1 net sum in at least 4 of the 5 full years 2018-2022; and aggregate two-sided normal-approximation p < 0.01 on E1 net trade returns.

Discovery survivor IDs are frozen and hashed before opening 2023-2024. Confirmation requires at least 30 trades; positive E1 and STRESS mean; positive E1 net sum separately in 2023 and 2024; and BH-FDR q <= 0.05 across all frozen discovery survivors.

Confirmation survivor IDs are frozen and hashed before opening 2025. The 2025 pre-OOS gate requires at least 15 trades; positive E1 and STRESS mean; positive E1 net sum separately in H1 and H2; positive STRESS net sum after removing the single best STRESS trade; and no single positive STRESS trade contributing more than 35% of total positive STRESS contribution.

A PASS means only that a frozen pre-OOS lead-lag candidate exists. It is not an EA and does not authorize live deployment or opening 2026.

## Mandatory deterministic preflight

Before market-data execution, tests must verify: exactly 72 deterministic definitions; prior-only volatility normalization; follower/leader lag-ratio gating; direction transfer; next-H1-open entry; fixed-horizon exit; one-position overlap semantics; missing-hour fail-closed behavior; year-boundary purge; exact E1/STRESS cost subtraction; immutable input hashes; and protected-2026 rejection.

## Post-result rule

If 0 candidates pass, close R11 without rescue or threshold retuning and move to a genuinely independent phenomenon family. If candidates pass, freeze exact definitions and preregister a separate reject-only robustness/red-team stage before any protected OOS consideration.
