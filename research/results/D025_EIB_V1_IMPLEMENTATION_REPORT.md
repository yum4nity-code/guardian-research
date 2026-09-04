# D025 — External Intelligence Bus V1 — implementation report

Date: 2026-09-04
Status: `IMPLEMENTED / OFFLINE TESTED / LIVE SMOKE PENDING`

## Scope implemented

Provider V1: Bybit public market data, no API key.

Canonical instruments:
- BTCUSD -> BTCUSDT
- ETHUSD -> ETHUSDT

Recorded observations:
- spot last price;
- USDT perpetual last price;
- perpetual open interest;
- perpetual funding rate;
- liquidation quantity with long/short side;
- liquidation notional estimate (`size * bankruptcy_price`);
- provider/channel health.

## Files

- `research/external_intelligence/collector_v1.py`
- `research/external_intelligence/replay_v1.py`
- `research/external_intelligence/schema_v1.json`
- `research/external_intelligence/manifest_v1.json`
- `research/external_intelligence/requirements.txt`
- `research/external_intelligence/COLLECTOR_V1.md`
- `research/external_intelligence/tests/test_eib_v1.py`

## Hashes

- collector SHA256: `761329daa74cdb31dd80f136b0f37e1df759956e13e6ea0b3bc3c7bd6c73874e`
- replay SHA256: `4a8b1ef7a80bbf2a898b996f5b86b38475ec88695a673591f49f3a158bb2b034`
- tests SHA256: `d1f65cb2b08f73a6e6b06c5cc131372520e4534984102dd58bd237d501083948`
- manifest SHA256: `b99e3af8f60ce0aadfeff79436e6220ff9f0d03becb42992fad59f719bd7f7eb`

## Offline validation performed by ChatGPT

Executed in a Python environment with aiohttp 3.13.3:

- `python -m py_compile collector_v1.py replay_v1.py` -> PASS
- `python -m unittest discover -s tests -v` -> 4/4 PASS

Tests cover:
- spot ticker normalization;
- perpetual price/OI/funding normalization;
- Bybit liquidation side semantics and notional estimate;
- replay lookahead gate using `available_at_ms`, not source event time.

## Replay invariant

A record is invisible to a simulated strategy until:

`available_at_ms <= simulated_time_ms`

`available_at_ms` is the local receive timestamp, not the exchange event timestamp. This prevents an old exchange timestamp from leaking information that actually arrived later.

## Public provider evidence

Bybit official docs:
- ticker REST, spot + linear: https://bybit-exchange.github.io/docs/v5/market/tickers
- public websocket connection: https://bybit-exchange.github.io/docs/v5/ws/connect
- all liquidations: https://bybit-exchange.github.io/docs/v5/websocket/public/all-liquidation

Important liquidation semantic: in `allLiquidation`, `S=Buy` means a long position was liquidated; `S=Sell` means a short position was liquidated. The feed reports size and bankruptcy price. Therefore V1 notional is an estimate and is labeled as such.

## Remaining live gate

Not yet proven in ChatGPT's execution environment because external network collection is not available there. Codex must run the implementation on the user's PC for 30+ minutes and record:
- per-metric counts;
- source->receive latency distribution;
- duplicate event-id rate;
- reconnect behavior;
- health/staleness transitions;
- JSONL size/growth;
- replay test against the real sample.

No D025 signal engine or Guardian production integration is authorized before this live data gate passes.
