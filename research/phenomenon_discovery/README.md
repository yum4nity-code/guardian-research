# Guardian Phenomenon Discovery Lab

Status: Phase A bootstrap prepared on 2026-09-08.

## Goal

Search for repeatable market-state phenomena before designing a trading strategy.

The lab deliberately reverses the usual workflow:

`market state -> future distribution shift -> robustness checks -> only then strategy`

It must not optimize P&L first or rescue a rejected Guardian strategy family.

## Phase A discovery window

Frozen bootstrap window:

- start: `2024-01-01 UTC`
- end: `2026-01-01 UTC` exclusive
- symbols: `BTCUSDT`, `ETHUSDT`
- exchange: Bybit USDT perpetual
- resolution: 5 minutes
- sources: public Bybit V5 kline + historical open-interest endpoints

**2026 is intentionally excluded from Phase A discovery.** Do not download or inspect 2026 data for rule generation. A later preregistered validation stage may use 2026 only after discovery rules and statistical gates are frozen.

## Phase A files

- `download_bybit_oi_price_v1_00.py` — downloads and aligns 5m price + OI; no interpolation/forward fill.
- `build_feature_matrix_v1_00.py` — causal closed-bar features plus explicitly named `future_*` labels.
- `check_dataset_v1_00.py` — row/gap/duplicate/basic missing-data integrity gate.
- `START_PHASE_A_DISCOVERY_V1.ps1` — one-command Windows launcher.

## Initial features

Closed-bar predictors include:

- RSI(14), Wilder;
- ATR(14), Wilder;
- ATR slope 1-bar absolute and percent;
- ATR slope 3-bar percent;
- price changes 5m / 15m / 1h;
- OI changes 5m / 15m / 1h;
- OI acceleration proxies;
- candle range / body normalized by ATR.

The first matrix also contains offline labels:

- future returns 5m / 15m / 30m / 1h;
- future MFE/MAE normalized by current ATR;
- first touch of +1 ATR or -1 ATR within 1h.

`future_*` fields are labels only and are forbidden as predictors.

## ATR-slope note

Phase A currently computes transparent Wilder ATR(14) slopes from historical closed 5m bars. Before any Guardian integration, the exact current live Guardian ATR-slope formula must be mirrored and conformance-tested against live Guardian output. The lab must not silently claim exact live equivalence until that check exists.

## Causality

Historical exchange endpoints do not reproduce the live sniffer's actual receive-time semantics. Therefore Phase A historical data are discovery data only.

The existing Bybit+Binance sniffer remains the stronger forward source because it records `available_at_ms` and preserves real gaps/staleness. Any candidate phenomenon must later survive an availability-gated forward test.

## Next step after Phase A data gate

Do not immediately optimize strategies. First produce a phenomenon atlas:

- unconditional future distributions;
- conditional distributions by coarse quantile bins of OI change / OI acceleration / ATR slope / RSI / price displacement;
- minimum event-count gates;
- stability across BTC and ETH;
- time-block stability;
- correction for multiple testing before promoting any candidate.
