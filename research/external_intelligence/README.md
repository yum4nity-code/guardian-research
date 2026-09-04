# Guardian External Intelligence Bus — Research V1

Status: `LIVE SMOKE PASS / REAL REPLAY PASS / RECONNECT PASS / HEALTHFIX PASS / SHARED MARKET STATE IMPLEMENTED, LIVE SMOKE PENDING`.

No live orders. No Guardian risk/compliance dependency on Internet.

## Goal

Provide Guardian with timestamped, replayable external market observations and one shared strategy-neutral market-state service per PC. External data may enrich strategies later, but Guardian protection, risk and prop-firm compliance must continue independently if this service is stale/down.

V1 scope: BTC and ETH only, Bybit public market data, no API key.

## Validated raw EIB V1

The user's real-PC gates passed on 2026-09-04:

- ~35-minute live smoke: PASS;
- 4210 unique events, 0 duplicate IDs, 0 invalid JSON, 0 future-availability violations;
- all core spot/perp/OI/funding channels present;
- real replay: 0 records visible 1 ms before smoke start, 20 visible ~10 s after start;
- deliberate Internet interruption/reconnect: PASS, with DOWN/PARTIAL/STALE transitions and recovery to BTC/ETH OK + liquidation websocket connected;
- health-event spam hotfix: offline 3/3 tests PASS and live smoke PASS; aggregate health dropped from 36/symbol to 4/symbol over 3 minutes while core channels stayed complete.

The raw collector/replay layer is therefore sufficiently validated for the next research layer. Rare liquidation replay exactly across a reconnect remains a later edge-case test, not a blocker for the shared-state prototype.

## Current files

Raw EIB:
- `collector_v1.py` — original public collector/recorder;
- `collector_v1_healthfix.py` — validated semantic-health hotfix used by the shared service;
- `smoke_v1.py` — timed raw live smoke;
- `smoke_healthfix_v1.py` — healthfix smoke;
- `replay_v1.py` — strict availability-gated replay;
- `schema_v1.json` — canonical observation schema;
- `manifest_v1.json` — provider/source limitations;
- `tests/test_eib_v1.py` — normalization/replay tests;
- `tests/test_healthfix_v1.py` — semantic-health tests.

Shared Intelligence V1:
- `market_state_v1.py` — strategy-neutral rolling feature engine + atomic shared snapshot writer;
- `shared_service_v1.py` — one collector + one market-state engine per PC;
- `smoke_shared_service_v1.py` — 3-minute live gate for the combined service;
- `tests/test_market_state_v1.py` — availability/feature/atomic snapshot tests;
- `START_SHARED_INTELLIGENCE_SMOKE_V1.cmd` — one-click live smoke;
- `START_SHARED_INTELLIGENCE_V1.cmd` — continuous research service launcher.

Product/reproducibility docs:
- `../../docs/GUARDIAN_PRODUCT_INSTALLATION_AND_DATA_LIFECYCLE.md`;
- `../../docs/GUARDIAN_SHARED_INTELLIGENCE_SERVICE_ARCHITECTURE.md`.

## Raw observations

Implemented:
- spot last price;
- perpetual last price;
- open interest;
- funding rate;
- long/short liquidation events;
- estimated liquidation notional (`size * bankruptcy_price`, explicitly labelled estimate);
- health/staleness.

Replay invariant:

`available_at_ms <= simulated_time_ms`

Source timestamp alone is never sufficient for historical visibility.

## Shared market state V1

The first shared state deliberately contains neutral facts only. It does **not** output BUY/SELL or a strategy score.

For BTCUSD and ETHUSD it currently computes:
- current spot/perpetual price;
- current open interest;
- current funding;
- perp-vs-spot basis %;
- spot returns over 1m / 5m / 15m / 1h;
- perpetual returns over 1m / 5m / 15m / 1h;
- perpetual-minus-spot return dislocation in percentage points;
- open-interest changes over 1m / 5m / 15m / 1h;
- long/short estimated liquidation notional over 1m / 5m / 15m / 1h;
- net short-minus-long liquidation notional;
- quality/status, source age and latest availability time.

The live snapshot is written atomically to:

`D:\MT5_Backtests\Research\ExternalIntelligence\market_state_v1.json`

It includes a monotonic `generation_id`. Multiple Guardian instances should later read this one compact file instead of each fetching/recomputing external data independently.

If a historical window is not yet populated, the corresponding change/return remains `null`. V1 must not silently forward-fill missing history.

## Data flow

Live:

`Bybit public -> one collector -> raw JSONL -> one market-state engine -> market_state_v1.json -> many Guardian consumers`

Backtest target:

`immutable raw archive -> availability-gated replay -> deterministic derived feature stream -> many tester workers`

No live external service may be used as historical truth inside Strategy Tester.

## Provider / safety policy

- public read-only market data only;
- no trading credentials;
- shared service cannot submit MT5 orders;
- provider-specific logic stays isolated from strategy interpretation;
- stale/down external state disables only dependent enrichment features;
- Guardian Core/manual protection/risk/compliance remain independent;
- no opaque global AI score;
- no parameter tuning based on this first live smoke.

## Immediate next gate

Run:

```powershell
cd D:\MT5_Backtests\guardian-research
git pull
cd .\research\external_intelligence
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_market_state_v1.py" -v
.\START_SHARED_INTELLIGENCE_SMOKE_V1.cmd
```

Expected before any Guardian integration:
- market-state tests PASS;
- combined live smoke PASS;
- `generation_id` advances;
- BTC/ETH core state remains fresh/OK;
- no future-availability violation;
- underlying raw collector gate remains PASS.

Only after that do we add a **read-only Guardian consumer/observer**, initially with no strategy behavior change.

## Not allowed yet

- live strategy decisions from external state;
- changes to `production/guardian/`;
- opaque scoring/ML;
- threshold optimization;
- future-data joins;
- silent stale-data reuse;
- live LER orders.
