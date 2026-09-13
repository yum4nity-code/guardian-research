# R14 Bitcoin hourly negative-shock overreaction — literature replication preregistration

Date: 2026-09-13
Status: FROZEN BEFORE EXECUTION
Family: literature-first replication
Protected final OOS: 2026 forbidden until canonical protected-OOS conditions are met

## External published hypothesis

R14 replicates the simplest filter-size event-study branch from:

José Luis Miralles-Quirós and María Mar Miralles-Quirós (2022), “Intraday Bitcoin price shocks: when bad news is good news”, Journal of Applied Economics 25(1), 1294–1313. DOI: 10.1080/15140326.2022.2151253.

The paper uses Kraken hourly Bitcoin closes from 2016-03-01 through 2021-06-30. A negative shock occurs when the hourly log return is below one of six fixed thresholds: -0.5%, -1.0%, -1.5%, -2.5%, -3.5%, -5.0%. It reports positive post-shock average cumulative log returns at each of eight horizons: 1, 2, 3, 4, 5, 6, 12 and 24 hours. The paper interprets this as overreaction/reversal after negative shocks.

R14 does not invent a new threshold grid. The 6 x 8 = 48 negative-shock cells come directly from the published table.

## Data and closest-feasible replication

Guardian local source:
`BTCUSDT_spot_5m_2017_2025.csv`

Expected SHA256:
`75d0d48dcfa7e649192d1eb2c96e89a591aa49bcfac11d394a1f84113264f6e8`

The local source is Binance BTCUSDT rather than the paper's Kraken BTC series and does not cover the paper's full 2016 start. R14 is therefore a near-replication, not a claim of byte-for-byte reproduction.

Construct H1 bars only when exactly 12 underlying M5 closes exist in the hour. Reject duplicate timestamps, unexpected source hashes, filenames containing `2026`, and any row at or after 2026-01-01 UTC.

Closest-feasible replication window:
- start: 2017-08-17 00:00 UTC
- end exclusive: 2021-07-01 00:00 UTC

Independent later confirmation:
- 2021-07-01 through 2024-12-31 inclusive
- implemented as end-exclusive 2025-01-01

Pre-OOS:
- 2025-01-01 through 2025-12-31

Protected final OOS:
- 2026; unopened by R14.

## Published-event semantics

For completed H1 bar t:
`r_t = ln(close_t / close_{t-1})`

A negative shock for threshold f occurs only when:
`r_t < -f`

Strict inequality is required.

For published horizon h, the paper-style event return is:
`ACR_event = ln(close_{t+h} / close_t)`

The full hourly path from event close through horizon close must be continuous. An event whose horizon exits the current stage window is rejected. Event-study observations may overlap, matching the paper-style event-study design.

No transaction cost or one-position filter is applied during paper replication or independent phenomenon confirmation.

## Stage 1 — published-effect near-replication

Test all 48 published negative-shock cells on the closest-feasible replication window.

For every cell persist:
- event count n;
- mean cumulative log return;
- standard deviation;
- paper-style t statistic;
- two-sided p-value approximation;
- BH-FDR q-value across all 48 cells.

A published cell becomes a frozen replication candidate only if:
- n >= 30;
- mean cumulative log return > 0;
- BH q <= 0.05.

The direction is fixed by the paper: positive post-negative-shock return. No opposite-direction rescue is allowed.

Freeze candidate IDs and SHA before inspecting independent confirmation.

## Stage 2 — independent later confirmation

Evaluate only frozen Stage-1 candidates on 2021-07-01 through 2024-12-31.

Pass only if:
- n >= 30;
- mean cumulative log return > 0;
- at least 2 of the 3 full calendar years 2022, 2023 and 2024 have positive cumulative event return;
- BH q <= 0.05 across the frozen replication candidates.

2021-H2 is retained diagnostically but is not one of the three full-year stability votes.

Freeze confirmation IDs/SHA before economic translation.

## Stage 3 — executable/economic translation

Paper replication is not itself an executable strategy test.

For each independently confirmed cell:
- signal becomes known only after the shock H1 bar has completed;
- enter LONG at the next H1 open;
- exit at the H1 open exactly h hours after entry;
- require a continuous H1 path;
- enforce one-position chronological replay for that candidate;
- no cross-stage-window exit is allowed.

Round-trip costs:
- E1 = 0.001
- STRESS = 0.002

Pass only if mean E1 return > 0 and mean STRESS return > 0 on the frozen 2021-2024 confirmation period.

Freeze economic IDs/SHA before opening 2025.

## Stage 4 — 2025 pre-OOS

Exact candidate and economic assumptions remain frozen.

Pass only if:
- n >= 10;
- E1 mean > 0;
- STRESS mean > 0;
- H1-2025 E1 net sum > 0;
- H2-2025 E1 net sum > 0;
- STRESS net sum after removing the single best STRESS trade > 0;
- largest positive STRESS trade / total positive STRESS PnL <= 0.35.

## Mandatory funnel and diagnostics

Persist:
`tested -> replication_enough_n -> replication_positive -> replication_fdr -> replication_pass -> confirmation_enough_n -> confirmation_positive -> confirmation_stability -> confirmation_fdr -> confirmation_pass -> economic_pass -> preoos_survivors`

Persist a compact 48-row replication ledger with threshold, horizon, n, mean, t-stat, p, q and pass flags.

## No-rescue rules

- No threshold or horizon may be added after seeing R14 results.
- No positive-shock branch may be substituted to rescue a failed negative-shock replication.
- No cost/sizing filter may rescue a failed published effect.
- No use of 2025 to choose among replication candidates.
- No use of 2026 at any R14 stage.
- A failure to reproduce the published effect must trigger implementation/data-source audit before scientific interpretation, because this is an external benchmark of Guardian as well as an alpha test.
