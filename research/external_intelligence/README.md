# Guardian External Intelligence Bus — Research V1

Status: `IMPLEMENTED / OFFLINE TESTED / LIVE SMOKE IN PROGRESS`. No live orders. No production dependency.

## Goal

Provide Guardian research with timestamped, replayable external market observations without giving any external API permission to trade and without making Guardian risk/protection depend on Internet availability.

V1 scope is intentionally small: BTC and ETH only.

## Current implementation

Provider V1: Bybit public market data, no API key.

Files:
- `collector_v1.py` — public collector/recorder;
- `smoke_v1.py` — timed live smoke + quality summary;
- `START_EIB_SMOKE_V1.cmd` — one-click Windows smoke launcher;
- `replay_v1.py` — strict availability-gated replay;
- `schema_v1.json` — canonical record schema;
- `manifest_v1.json` — provider/source limitations;
- `COLLECTOR_V1.md` — install/smoke/storage instructions;
- `tests/test_eib_v1.py` — offline normalization/replay tests.

Product/reproducibility documentation:
- `../../docs/GUARDIAN_PRODUCT_INSTALLATION_AND_DATA_LIFECYCLE.md` — machine bootstrap, Git clone/update, smoke launch, storage/retention policy, archive target, and future commercial-installer requirements.

Target observations implemented:
- spot last price;
- perpetual last price;
- open interest;
- funding rate;
- long/short liquidation events and explicit estimated liquidation notional;
- health/staleness.

## Canonical record

See `schema_v1.json`.

The key replay rule is based on **availability time**, not merely exchange/source event time:

`available_at_ms <= simulated_time_ms`

This avoids a subtle lookahead bug where an exchange event has an old source timestamp but was only received later by the collector.

## V1 data flow

`Bybit public -> read-only collector -> normalized daily JSONL -> health/staleness -> replay reader -> D025 research`

Guardian production is not part of this chain yet.

## Provider policy

- Prefer official public market-data endpoints/streams.
- Adapter/provider-specific logic must remain isolated from future strategy logic.
- No API key with trading permission.
- If a metric is not public/reliable from one source, mark the channel PARTIAL rather than fabricating/filling it.
- Preserve source venue because spot/perpetual prices and liquidation semantics are venue-specific.
- V1 is deliberately single-venue. Cross-venue aggregation comes only after V1 is proven.

## Liquidation limitation

Bybit `allLiquidation` reports size and bankruptcy price. V1 therefore records `liquidation_notional` as an estimate `size * bankruptcy_price` and labels the unit `USDT_est_bankruptcy_price`. It must never be represented as exchange-reported executed notional.

## Storage policy

Current research behavior:

- data are stored locally under `D:\MT5_Backtests\Research\ExternalIntelligence\` by default;
- one JSONL file per UTC day;
- no automatic deletion during D025 research.

Target lifecycle after smoke validation:

- current UTC day stays raw JSONL;
- closed days become verified `.jsonl.gz` archives;
- research retention remains manual/indefinite until the scientific value and disk rate are measured;
- future commercial retention will be configurable, with a provisional 90-day default and longer lab mode;
- raw deletion is allowed only after archive-integrity verification.

## Health policy

Each channel exposes one of:

- `OK` — current and parseable;
- `STALE` — last valid observation exceeds its metric-specific age limit;
- `PARTIAL` — provider is up but one or more expected metrics are unavailable/incomplete;
- `DOWN` — channel unavailable.

A stale/down Crypto+ input must disable only the feature that needs it. It must not disable Guardian Core, manual protection, risk or compliance.

## Validation status

Completed by ChatGPT:
- Python syntax compile: PASS;
- 4/4 offline unit tests: PASS;
- strict `available_at` replay gate: PASS.

Live smoke on the user's PC: started 2026-09-04, 35-minute run. Final summary still pending.

Still required after the run:
1. inspect smoke summary and actual disk rate;
2. reconnect/deduplication test;
3. health/staleness transitions;
4. replay against the real sample;
5. compact sample + manifest/stats committed to GitHub;
6. only then implement daily archive/retention automation.

Only after these gates: D025 LER observer/event study.

## Not allowed in V1

- live trading;
- changes to `production/guardian/`;
- opaque scoring/ML;
- threshold optimization;
- future-data joins;
- silent forward-fill of stale external data.
