# Guardian External Intelligence Bus — Research V1

Status: research only. No live orders. No production dependency.

## Goal

Provide Guardian research with timestamped, replayable external market observations without giving any external API permission to trade and without making Guardian risk/protection depend on Internet availability.

V1 scope is intentionally small: BTC and ETH only.

## Target observations

- spot last price;
- perpetual last price;
- open interest;
- funding rate;
- long/short liquidation events or normalized liquidation notional when a public source exposes them.

## Canonical record

See `schema_v1.json`.

The key replay rule is based on **availability time**, not merely exchange/source event time:

`available_at_ms <= simulated_time_ms`

This avoids a subtle lookahead bug where an exchange event has an old source timestamp but was only received later by the collector.

## V1 data flow

`Public exchange/provider -> read-only collector -> normalized JSONL/Parquet -> health/staleness -> replay reader -> D025 research`

Guardian production is not part of this chain yet.

## Provider policy

- Prefer official public market-data endpoints/streams.
- Adapter layer must isolate provider-specific field names and reconnect behavior.
- No API key with trading permission.
- If a metric is not public/reliable from one source, mark the channel PARTIAL rather than fabricating/filling it.
- Preserve source venue because spot/perpetual prices and liquidation semantics are venue-specific.

## Health policy

Each channel exposes one of:

- `OK` — current and parseable;
- `STALE` — last valid observation exceeds its metric-specific age limit;
- `PARTIAL` — provider is up but one or more expected metrics are unavailable/incomplete;
- `DOWN` — channel unavailable.

A stale/down Crypto+ input must disable only the feature that needs it. It must not disable Guardian Core, manual protection, risk or compliance.

## Incremental gates

1. Schema and recorder.
2. 30+ minute BTC/ETH smoke collection.
3. Reconnect/deduplication test.
4. Replay reader with strict `available_at` gate.
5. Small sample + manifest + source limitations committed to GitHub.
6. Only then: D025 LER observer/event study.

## Not allowed in V1

- live trading;
- changes to `production/guardian/`;
- opaque scoring/ML;
- threshold optimization;
- future-data joins;
- silent forward-fill of stale external data.
