# EIB V1 — Binance + Multi-Venue Candidate — 2026-09-04

Status: **IMPLEMENTED / OFFLINE+LIVE GATES PENDING**

## Purpose

Add Binance public market data beside the already validated Bybit EIB without mixing venues inside the same raw time series.

This candidate remains research-only and cannot create trading decisions.

## Added files

- `research/external_intelligence/binance_collector_v1.py`
- `research/external_intelligence/market_state_multivenue_v1.py`
- `research/external_intelligence/smoke_binance_multivenue_v1.py`
- `research/external_intelligence/tests/test_binance_collector_v1.py`
- `research/external_intelligence/tests/test_market_state_multivenue_v1.py`
- `research/external_intelligence/START_BINANCE_MULTIVENUE_GATE_V1.cmd`

## Binance public inputs

BTCUSDT and ETHUSDT only in V1.

REST:
- Spot price: `/api/v3/ticker/price`
- USDⓈ-M perp price: `/fapi/v2/ticker/price`
- Open interest: `/fapi/v1/openInterest`
- Latest funding: `/fapi/v1/premiumIndex`

WebSocket:
- `{symbol}@forceOrder` via the USDⓈ-M public market stream.

No API key. No account endpoint. No order endpoint.

## Critical normalization decisions

### Venue separation

Binance records are written to `binance_eib_v1_YYYYMMDD.jsonl`; validated Bybit records remain in `bybit_eib_v1_YYYYMMDD.jsonl`.

The multi-venue state engine owns one coverage-aware engine per venue. A Binance observation is never inserted into a Bybit price/OI/funding series and vice versa.

### Availability time

`available_at_ms = received_ts_ms`, preserving the anti-lookahead invariant.

Binance spot `/api/v3/ticker/price` does not provide an exchange timestamp. For that endpoint only, `source_ts_ms` is explicitly set to `received_ts_ms` and the limitation is written into the record quality reason.

### Liquidation semantics

Binance `forceOrder` publishes a snapshot feed: at most the latest force order for a symbol in each 1000 ms window. It is therefore **not exhaustive liquidation volume**.

For USDⓈ-M force orders:
- forced `SELL` closes a long -> normalized side `long`
- forced `BUY` closes a short -> normalized side `short`

Observed notional uses accumulated/original quantity and average/order price where available. It is labelled `USDT_observed_forceOrder_snapshot`.

Because Binance and Bybit liquidation feeds do not have identical sampling/notional semantics, the cross-venue engine deliberately does **not** publish a fake `total_liquidations` number. It publishes per-venue observed values plus the number of venues showing long/short liquidation activity.

## Cross-venue facts exposed

Per BTC/ETH:
- Binance-vs-Bybit spot price spread
- Binance-vs-Bybit perp price spread
- funding by venue + spread
- basis by venue + spread
- mean spot/perp/dislocation returns when both venues have valid coverage
- mean OI percentage change + dispersion + direction agreement
- venue-specific observed liquidation notional
- count of venues with long liquidation activity
- count of venues with short liquidation activity
- final quality status for each venue

No score, regime label, BUY, SELL, strategy filter, or risk action is emitted.

## Gate

Before running the gate, stop the existing shared runtime so there is exactly one Bybit writer.

```powershell
cd D:\MT5_Backtests\guardian-research
git pull
cd .\research\external_intelligence
.\START_BINANCE_MULTIVENUE_GATE_V1.cmd
```

The launcher runs offline normalization/separation tests and then a 3-minute real Bybit+Binance smoke.

Acceptance requires:
- all BTC/ETH core channels from both venues
- final BYBIT and BINANCE status `OK`
- no duplicate event IDs in the smoke window
- no availability-before-receive violation
- venue-separated raw prices
- cross-venue price/funding facts populated
- cross-venue 1m OI feature covered
- 1m liquidation observation coverage valid on both venues
- explicit liquidation sampling caveat retained
- `NO_STRATEGY_DECISION_OUTPUT`

Expected terminal line:

`[Guardian] FULL GATE BINANCE MULTI-VENUE V1: PASS.`

## Production status

**NOT integrated into Guardian live decision logic.**

Guardian v11.17.05 remains a read-only observer of the validated single-venue shared CSV until this multi-venue candidate passes its gates and a separate bridge/consumer audit is completed.
