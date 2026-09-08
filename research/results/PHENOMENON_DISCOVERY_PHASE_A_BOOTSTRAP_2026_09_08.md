# Guardian Phenomenon Discovery Lab — Phase A Bootstrap

Date: 2026-09-08
Status: PREPARED / USER-RUN DATA GATE PENDING

## Decision

Do not create another named strategy family yet. Start a phenomenon-first research line using existing external-intelligence concepts and historical public exchange data.

## Frozen Phase A scope

- discovery only, no trading;
- BTCUSDT + ETHUSDT;
- Bybit USDT perpetual;
- 5-minute kline + historical open interest;
- discovery window: 2024-01-01 UTC through 2025-12-31 UTC (`--end 2026-01-01`, exclusive);
- 2026 intentionally withheld from discovery;
- existing live Bybit+Binance sniffer remains future availability-gated validation evidence.

## Implemented bootstrap

- `research/phenomenon_discovery/download_bybit_oi_price_v1_00.py`
- `research/phenomenon_discovery/build_feature_matrix_v1_00.py`
- `research/phenomenon_discovery/check_dataset_v1_00.py`
- `research/phenomenon_discovery/START_PHASE_A_DISCOVERY_V1.ps1`
- `research/phenomenon_discovery/README.md`

## Scientific constraints

- no P&L optimization in Phase A;
- no BUY/SELL rule generation before the phenomenon atlas;
- no interpolation or silent forward fill of missing OI;
- future columns are labels only;
- current bootstrap ATR slope is a transparent Wilder ATR(14) historical slope, not yet claimed to be byte/semantic-equivalent to the current live Guardian ATR-slope implementation;
- exact live ATR-slope conformance must be added before Guardian strategy integration;
- historical Bybit API data are discovery evidence, not a substitute for live `available_at_ms` semantics.

## Next gate

User runs the Phase A launcher on the research PC and returns console output / integrity report. Only after the data gate passes do we build the phenomenon atlas and multiple-testing controls.
