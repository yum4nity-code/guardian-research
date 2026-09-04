# D025 / Guardian EIB V1 — live smoke 2026-09-04

Status: `LIVE SMOKE PASS / VALIDATION PARTIAL`  
Source: user-run Windows smoke on the research collector.  
No live trading, no Guardian production mutation.

## Run

- Start UTC: `2026-09-04T05:38:41.049000+00:00`
- Stop UTC: `2026-09-04T06:13:41.069000+00:00`
- Observed duration: `2099.53 s` (~35 min)
- Output directory: `D:\MT5_Backtests\Research\ExternalIntelligence`
- Gate returned by `smoke_v1.py`: `PASS`

## Exact smoke summary supplied by user

- Unique events: `4210`
- Duplicate event IDs: `0`
- Invalid JSON lines: `0`
- Future availability violations: `0`
- Missing core channels: `[]`
- Quality counts: `OK=4208`, `DOWN=2`
- Source->receive lag p50: `1 ms`
- Source->receive lag p95: `12 ms`

Per-channel counts:

- BTCUSD aggregate health: `420`
- BTCUSD perpetual funding_rate: `420`
- BTCUSD perpetual last_price: `420`
- BTCUSD perpetual open_interest: `420`
- BTCUSD spot last_price: `420`
- ETHUSD aggregate health: `420`
- ETHUSD perpetual funding_rate: `420`
- ETHUSD perpetual last_price: `420`
- ETHUSD perpetual open_interest: `420`
- ETHUSD spot last_price: `420`
- ETHUSD liquidation_qty: `5`
- ETHUSD liquidation_notional: `5`
- BTC liquidation events during this window: `0` (not a failure; a quiet window can legitimately contain none)

## What this proves

1. The public Bybit REST path continuously supplied both BTC and ETH spot/perpetual price, open interest and funding for the full 35-minute window.
2. The liquidation WebSocket delivered real ETH liquidation events.
3. Recorder deduplication produced zero duplicate event IDs in this run.
4. JSONL remained parseable in the smoke summary.
5. The smoke detected no observation exposed with `available_at_ms` after the smoke time boundary; no observed lookahead violation.
6. The measured source/receive timing is low in this environment. This metric is based on exchange/source timestamps versus local receive timestamps and must not be mislabeled as a full network round-trip latency measurement.

## Important instrumentation observation

The run contains `420` aggregate `health` records per symbol, i.e. effectively one every 5 seconds. The code comment intended to persist health **on status change and at least once per minute**, while still updating `health.json` frequently.

Likely cause: the persisted health signature currently includes a textual reason containing continuously changing age values (`...ok:<age>ms...`), so the signature changes every health loop even when health status remains `OK`.

Impact: no correctness failure for market observations, but avoidable JSONL growth/noise. Fix before long-duration collection: keep `health.json` frequent, but make the historical health-event signature depend on stable state (status/connectivity/error class), not the continuously changing age string.

The two initial `DOWN` observations are consistent with startup before all REST/WS channels have produced their first valid sample, but this is an inference from the summary only. Confirm from `health.json`/early JSONL before classifying them definitively.

## Gates still NOT proven by this smoke

- deliberate network cut and automatic reconnect;
- deduplication specifically across reconnect/restart;
- STALE/PARTIAL/DOWN transitions during an induced outage;
- replay against the real produced JSONL with strict `available_at_ms <= simulated_time_ms` boundary checks;
- append-after-restart / no truncation on the user's PC;
- actual disk footprint and compression ratio;
- long-duration stability (hours/days).

Therefore `PASS` means the **35-minute continuous live smoke passed**, not that the full EIB V1 production-readiness gate is complete.

## Next small steps

1. Measure actual JSONL byte size from this 35-minute run and estimate daily/monthly storage from evidence rather than assumption.
2. Fix historical health-event spam while preserving frequent atomic `health.json` updates.
3. Run real-sample replay checks.
4. Run one controlled short network interruption/reconnect test and verify no duplicate liquidation IDs, no invented forward-fill and correct health transitions.
5. Only after those gates: start the shared feature/state service that computes neutral market features once per machine for RSI, Momentum and D025 LER consumers.

## Provider semantics check

Bybit official `allLiquidation` documentation states that field `S` is the **position side**; `Buy` means a long position was liquidated. This matches V1 normalization. The provider reports executed size and bankruptcy price; V1 liquidation notional remains explicitly an estimate `size * bankruptcy_price`, not an exchange-reported executed notional.
