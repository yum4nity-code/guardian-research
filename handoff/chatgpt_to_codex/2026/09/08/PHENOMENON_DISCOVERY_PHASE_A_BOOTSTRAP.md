# Phenomenon Discovery Lab — Phase A bootstrap

This note supplements the current queue. It does not revive D053/D054 or any other rejected alpha family.

Prepared by ChatGPT on 2026-09-08 because the user wants a fundamentally different research mode after repeated strategy-family failures.

## Current task

Run/validate the phenomenon-first data bootstrap before inventing another strategy.

Canonical files:

- `research/phenomenon_discovery/README.md`
- `research/phenomenon_discovery/download_bybit_oi_price_v1_00.py`
- `research/phenomenon_discovery/build_feature_matrix_v1_00.py`
- `research/phenomenon_discovery/check_dataset_v1_00.py`
- `research/phenomenon_discovery/START_PHASE_A_DISCOVERY_V1.ps1`

Frozen Phase A discovery window:

- BTCUSDT + ETHUSDT
- Bybit linear perpetual
- 5m
- 2024-01-01 <= t < 2026-01-01
- 2026 must remain withheld from discovery until candidate phenomena and validation rules are preregistered.

Do not convert this immediately into a trading strategy. Next research object after the data gate is a phenomenon atlas of conditional future distributions with coarse bins, cross-symbol/time-block stability, event-count gates and multiple-testing correction.

Historical Bybit API data are discovery-only. Existing live Bybit+Binance sniffer with `available_at_ms` is the later forward evidence source.
