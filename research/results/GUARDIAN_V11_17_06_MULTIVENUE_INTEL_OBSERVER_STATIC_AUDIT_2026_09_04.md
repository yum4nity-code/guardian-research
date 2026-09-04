# Guardian v11.17.06 — Multi-Venue Intelligence Observer — Static Audit

Date: 2026-09-04  
Status: **STATIC AUDIT PASS / USER COMPILATION REQUIRED**

## Provenance

- Base: `Guardian_D017_PropFirmAuto_v11_17_05_SHARED_INTEL_OBSERVER_CANDIDATE.mq5`
- Base SHA256: `2d790a633a615cdf8b40e3b2c90142685958e0031e75854821c470e118fdad9a`
- Candidate: `Guardian_D017_PropFirmAuto_v11_17_06_MULTIVENUE_INTEL_OBSERVER_CANDIDATE.mq5`
- Candidate SHA256: `71819213b69bc26a59e115e649168818a1d6ede33e346498db61c84034583123`

The v11.17.05 base SHA matches the previously delivered observer candidate.

## Scope

v11.17.06 changes only Shared Intelligence observer plumbing/telemetry so Guardian can consume:

`GuardianSharedIntelligence\market_state_multivenue_v1.csv`

Bridge schema: **2**, **61 CSV fields**, BTCUSD + ETHUSD rows.

Observed facts include Bybit/Binance status and age, spot/perp prices and cross-venue spreads, funding and basis by venue, cross-venue OI mean/dispersion/direction agreement, mean spot/perp/dislocation returns, venue-specific observed liquidations + active-venue counts, and venue-specific 1m/5m coverage.

## Trading isolation

No trading authority was added.

Static inspection confirms Shared Intelligence remains limited to its observer implementation, HUD/log lifecycle and refresh calls. No RSI, Momentum, manual-management, sizing, stop-loss, take-profit, drawdown or prop-firm decision condition references the Shared Intelligence state. Strategy Tester still rejects live FILE_COMMON intelligence. Missing/stale external data can only affect observer telemetry and cannot veto or authorize a trade.

## Parser/schema checks

- `SHARED_INTEL_FIELD_COUNT = 61`
- bridge schema must equal `2`
- both rows must share one positive `generation_id` and `computed_at_ms`
- symbols must resolve exactly to BTCUSD + ETHUSD in either order
- header sentinel checks cover schema/generation/time/symbol, Bybit/Binance status, `oi_mean_1m`, and final Binance liquidation coverage field
- blank optional values stay unavailable/`NA`, including expected 5m values during early runtime coverage

## Structural checks

- literal brace count: 960 opening / 960 closing
- candidate version: `11.1706`
- multi-venue FILE_COMMON path set correctly
- no modification to strategy defaults or inherited v11.17.04 manual-protection behavior

## Pre-integration runtime evidence

The shared multi-venue runtime gate passed with 61 state publishes, 61 bridge publishes, 61 distinct generations, zero review errors, zero failures, and BTC/ETH both-core true at observed checkpoints.

## Remaining gate

MetaEditor compilation is **not claimed**. User must compile v11.17.06 and run a live observer smoke proving Guardian itself reads advancing schema-2 generations with Bybit+Binance statuses.
