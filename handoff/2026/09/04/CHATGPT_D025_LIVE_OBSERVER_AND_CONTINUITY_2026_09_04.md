# Handoff — D025 live observer + continuity

Date: 2026-09-04
Author: ChatGPT
Status: LIVE RESEARCH RUNNING

## User-validated live evidence

D025 observer launched successfully in MT5 on a spare USDSEK chart.

Observed logs:
- `[D025][START] ... symbols=BTCUSD,ETHUSD | CORE_MT5_ONLY | VIRTUAL_TRADES_ONLY | NO_ORDER_FUNCTIONS`
- BTCUSD `H1_SWING_HIGH` SWEEP, depthATR ≈ 0.283
- ETHUSD `H1_SWING_HIGH` SWEEP, depthATR ≈ 0.109
- a host-chart timeframe change caused `STOP reason=3`, then normal re-init; `active_virtual_trades_lost_on_restart=0` at that moment.

No live order was created; D025 is research-only.

## Versioning correction

User clarified MT5 versioning convention. D025 source `research/ea/D025_LER_Observer_V0.mq5` now uses:

`#property version "1.00"`

Research label `V0` remains the experimental rules generation; MT5 build versions for this lineage use simple numeric versions `1.00`, `1.01`, `1.02`, etc.

## Shared Intelligence

Bybit + Binance Shared Intelligence runtime is installed as a Windows scheduled task and user-verified `Running`.
Guardian v11.17.x/"Guardian 17" reads fresh multi-venue data in observer/read-only mode with BTC and ETH both venues OK.

D025 V0 does not yet consume external data in its state transitions; this is deliberate to preserve Core-vs-Crypto+ attribution.

## Canonical resume point

A new root file now exists:

`CURRENT_PROJECT_HANDOFF.md`

It is the first file a fresh ChatGPT/Codex instance should read. It contains active versions, live components, scientific constraints and next safe actions.

README and AGENTS.md were updated so future agents are explicitly required to read and maintain it.

## Next safe action

Let D025 1.00 accumulate live events. Verify progression/failure paths through SWEEP -> CASCADE -> EXHAUSTION -> RECLAIM -> RETEST/ACCEPTANCE -> VALID_SIGNAL without changing locked thresholds from early outcomes. Then build the automated analyzer over the D025 event/trade/outcome CSVs.
