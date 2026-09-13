# R13 BTC/ETH Failed-Breakout Rejection — Preregistration

Date: 2026-09-13
Status: frozen before execution

## Scientific question

After price sweeps strictly beyond a prior H1 channel but the completed decision bar closes back inside that channel, does the failed breakout predict short-horizon reversal strongly enough to survive realistic fixed costs and independent temporal gates?

This is a genuinely independent family from R8 relative-value mean reversion, R9 calendar/session seasonality, R10 multi-day trend, R11 cross-market lead-lag shock spillover, and R12 volatility-compression continuation. R12 is closed after clean scientific FAIL and is not retuned or rescued.

## Data and protection

Use only the existing pre-2026 BTCUSDT and ETHUSDT spot 5m files under `D:\MT5_Backtests\Research\Data\R7_LongHistory`:

- `BTCUSDT_spot_5m_2017_2025.csv` SHA256 `75d0d48dcfa7e649192d1eb2c96e89a591aa49bcfac11d394a1f84113264f6e8`
- `ETHUSDT_spot_5m_2017_2025.csv` SHA256 `21b170675eae6bd2e3d442391e2acb9392abdff443f517b5cb0ee1946a12aa13`

Protected 2026 is forbidden. Any row timestamped >= 2026-01-01 or any input filename containing `2026` must fail closed.

Construct H1 bars only when exactly 12 underlying M5 rows exist. Missing H1 hours fail closed.

## Frozen signal family

For each completed H1 decision bar, compute the prior channel using only completed bars before the decision bar.

Definitions are the Cartesian product:

- asset: BTCUSDT, ETHUSDT
- prior channel: 24, 72, 168 hours
- minimum sweep penetration as fraction of prior channel range: 0.00, 0.05
- minimum close re-entry depth as fraction of prior channel range: 0.00, 0.10
- hold: 3, 6, 12 hours

Total: 2 x 3 x 2 x 2 x 3 = 72 exact definitions.

For prior channel high `H`, low `L`, range `R=H-L`:

- upper failed breakout / short: decision high > H + penetration*R AND decision close <= H - reentry*R
- lower failed breakout / long: decision low < L - penetration*R AND decision close >= L + reentry*R

The sweep inequality is deliberately strict so `penetration=0` still requires an actual excursion beyond the prior channel rather than a mere touch. If both sides qualify on the same bar, reject the bar as ambiguous.

Entry is the next H1 open. Exit is the H1 open exactly `hold` hours later. One-position chronological replay applies per definition. Signals with missing required hourly timestamps, non-positive prior range, or exit crossing a calendar-year boundary are purged.

## Costs

Frozen round-trip costs applied directly to returns:

- E1: 10 bps
- STRESS: 20 bps

No sizing, Challenge Lab, leverage optimization, stop/TP optimization, or post-hoc filters are permitted.

## Chronology and gates

### Discovery: 2018-01-01 through 2022-12-31

A definition advances only if:

- n >= 75
- E1 mean > 0
- STRESS mean > 0
- at least 4 of 5 discovery years have positive E1 net sum
- two-sided normal-approximation p < 0.01 on E1

Freeze exact candidate IDs and their SHA256 before confirmation.

### Confirmation: 2023-01-01 through 2024-12-31

No rule changes. Apply BH-FDR 5% across discovery survivors. Advance only if:

- n >= 25
- E1 mean > 0
- STRESS mean > 0
- 2023 E1 net sum > 0
- 2024 E1 net sum > 0
- BH q <= 0.05

Freeze exact candidate IDs and SHA256 before opening 2025.

### Pre-OOS gate: 2025-01-01 through 2025-12-31

Advance only if:

- n >= 10
- E1 mean > 0
- STRESS mean > 0
- H1 2025 E1 net sum > 0
- H2 2025 E1 net sum > 0
- STRESS total remains positive after removing the single best trade
- best positive STRESS trade contributes <= 35% of total positive STRESS gains

2026 remains unopened regardless of outcome. A PASS here is pre-OOS evidence only.

## Mandatory preflight

Before the expensive run, deterministic cold tests must verify:

- exactly 72 unique stable definitions
- prior channel excludes decision bar
- strict beyond-channel sweep and re-entry inequalities are directional and symmetric
- ambiguous two-sided bars are rejected
- next-H1-open entry and fixed open-to-open exit
- one-position overlap semantics
- missing-hour fail closed
- cross-year exits purged
- exact input hashes and protected-2026 contract
- frozen costs and chronology

Any preflight failure blocks execution.
