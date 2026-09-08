# Phenomenon Discovery Lab — Phase A data gate

Date: 2026-09-08
Status: PASS

## Frozen discovery dataset

Window: 2024-01-01 00:00 UTC through 2025-12-31 23:55 UTC
Resolution: 5 minutes
Exchange/source: Bybit linear perpetual historical kline + open interest
Symbols: BTCUSDT, ETHUSDT
2026: intentionally withheld / not downloaded by the Phase A launcher

## Integrity result

BTCUSDT historical aligned rows: 210,528
ETHUSDT historical aligned rows: 210,528
BTCUSDT feature rows after Wilder warmup: 210,514
ETHUSDT feature rows after Wilder warmup: 210,514

For both historical inputs and both feature matrices:
- duplicate timestamps: 0
- non-5m gaps: 0
- largest interval: 300,000 ms
- blank open interest: 0
- open-interest alignment coverage: 100.00%

Historical first timestamp: 2024-01-01T00:00:00+00:00
Historical last timestamp: 2025-12-31T23:55:00+00:00
Feature first timestamp after ATR/RSI warmup: 2024-01-01T01:10:00+00:00

## Decision

Phase A data gate passes. The dataset is sufficiently complete to proceed to coarse phenomenon discovery.

The next canonical stage is Phase B: an interpretable quintile atlas using 2024 as discovery and 2025 as internal confirmation across BTC and ETH. It is not a trading-strategy optimizer and does not authorize PnL/risk conclusions.

2026 remains untouched for later protected validation after the phenomenon definition and statistical gates are frozen.
