# Guardian Shared Intelligence V1 — implementation report

Date: 2026-09-04
Status: `IMPLEMENTED / UNIT TEST PENDING ON USER PC / LIVE SMOKE PENDING`

## Purpose

Avoid duplicate external data collection and duplicate rolling calculations when multiple Guardian instances or Strategy Tester workers run on the same machine.

Target architecture:

`Bybit public -> ONE collector -> raw EIB JSONL -> ONE market-state engine -> ONE atomic market_state_v1.json -> many Guardian consumers`

This layer is strategy-neutral and read-only. It cannot submit MT5 orders and has no trading API credentials.

## Raw EIB gates already passed

Real-PC evidence before this implementation:

- 35-minute BTC/ETH smoke: PASS;
- 4210 unique events;
- 0 duplicate event IDs;
- 0 invalid JSON lines;
- 0 future-availability violations;
- all core channels present;
- real replay anti-lookahead test: PASS;
- deliberate Internet interruption/reconnect: PASS with DOWN/PARTIAL/STALE transitions and final BTC/ETH OK + websocket connected;
- semantic health hotfix: 3/3 offline tests PASS and live smoke PASS, reducing aggregate health writes from 36/symbol to 4/symbol over 3 minutes.

## New implementation

Files:

- `research/external_intelligence/market_state_v1.py`
- `research/external_intelligence/market_state_schema_v1.json`
- `research/external_intelligence/shared_service_v1.py`
- `research/external_intelligence/smoke_shared_service_v1.py`
- `research/external_intelligence/tests/test_market_state_v1.py`
- `research/external_intelligence/START_SHARED_INTELLIGENCE_SMOKE_V1.cmd`
- `research/external_intelligence/START_SHARED_INTELLIGENCE_V1.cmd`

The shared service intentionally uses the validated `BybitCollectorHealthFixed` collector implementation rather than modifying the original validated collector in place.

## Shared facts V1

For BTCUSD and ETHUSD:

- spot last price;
- perpetual last price;
- open interest;
- funding rate;
- perp/spot basis %;
- spot returns: 1m / 5m / 15m / 1h;
- perpetual returns: 1m / 5m / 15m / 1h;
- perp-minus-spot return dislocation in percentage points;
- OI changes: 1m / 5m / 15m / 1h;
- long estimated liquidation notional sums: 1m / 5m / 15m / 1h;
- short estimated liquidation notional sums: 1m / 5m / 15m / 1h;
- net short-minus-long liquidation notional;
- quality/status, core age and latest availability time.

No BUY/SELL signal, strategy weight or opaque AI score is emitted.

## Missing-history behavior

If a requested window is not yet populated, the feature remains `null`.

Example: after only 3 minutes of runtime, 5m/15m/1h return and OI-change features may legitimately be null. They must not be silently forward-filled or fabricated.

Liquidation sums may legitimately be zero during a quiet window.

## Availability invariant

The engine accepts a raw observation only if:

`available_at_ms <= as_of_ms`

This same rule is used by the historical helper so future event timestamps cannot leak into a simulated state.

## Shared snapshot contract

Atomic file:

`D:\MT5_Backtests\Research\ExternalIntelligence\market_state_v1.json`

Key fields:

- `schema_version`;
- `engine`;
- monotonic `generation_id`;
- `computed_at_ms`;
- `health_snapshot_age_ms`;
- per-symbol quality/raw/derived facts.

Guardian consumers should cache the last `generation_id` and only reparse when it changes.

## Tests to run next

Offline/unit:

```powershell
cd D:\MT5_Backtests\guardian-research
git pull
cd .\research\external_intelligence
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_market_state_v1.py" -v
```

Live combined smoke:

```powershell
.\START_SHARED_INTELLIGENCE_SMOKE_V1.cmd
```

The smoke runs one collector plus one market-state engine for 3 minutes and requires:

- underlying EIB raw gate PASS;
- `generation_id` advances;
- BTC/ETH final quality OK;
- core spot/perp/OI/funding present and fresh;
- no derived future-availability violation;
- no strategy decision-like field in the shared snapshot.

## Gate after smoke

If PASS, the next step is **not** to change strategy behavior immediately.

Next implementation should be a read-only Guardian observer/consumer that:

1. reads `market_state_v1.json`;
2. checks schema/generation/age;
3. exposes diagnostics in logs/HUD only;
4. never blocks Guardian Core or changes RSI/Momentum/LER decisions yet.

Only after observer correctness do we run event studies comparing base strategies vs external-feature-enriched variants.
