# Batch A first-run infrastructure failure — P12 CFTC dedup interaction

Date: 2026-09-22

## Observed failure

The first Batch-A run stopped during variant materialization at P12:

Missing frozen CFTC feature:
cftc_XAUUSD_noncomm_net_pct_oi_z52

The run had already loaded only the frozen 2010-2013 V83B layers and had built rate/beta/residual/breadth objects.

## Scientific status

- zero Batch-A discovery regression was executed;
- zero p-value was produced;
- zero candidate was selected;
- 2014+ market returns were not accessed;
- 2023-2025 were not accessed;
- 2026 was not accessed.

This is infrastructure/schema failure only.

## Root cause

V83 creates the intended CFTC transforms from the canonical V82D source:

- commercial_net_pct_oi level/d1w/d4w/z52
- noncomm_net_pct_oi level/d1w/d4w/z52

Then V83 applies dedup_vectors() to the entire slow-state matrix.

Therefore an economically intended CFTC column can be absent from the final V83/V83B slow parquet if its full carried vector is deduplicated, despite the underlying canonical causal CFTC source remaining available.

## V1.1 correction

P12 now reconstructs the exact V83 noncommercial z52 transform directly from:

D:\MT5_Backtests\DataLake\normalized\cftc_pre2023\CFTC_FUTURES_ONLY_2009_2013_CAUSAL_V82D.parquet

Exact transform:
- group by exact frozen market mapping;
- sort by report_date;
- s = noncomm_net_pct_oi;
- rolling mean/std = 52 reports, min_periods=26;
- z52 = (s - rolling_mean) / rolling_std;
- visible only from the source AVAILABLE_AT using backward as-of join.

No scientific parameter changes:
- same P12 markets;
- same noncommercial positioning variable;
- same z52 transform;
- same price-shock object;
- same |z|>=1.5 event threshold;
- same 240m cooldown;
- same horizons;
- same regression;
- same clustering by CFTC report instance;
- same discovery/holdout gates.
