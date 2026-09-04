# Guardian Shared Intelligence V1 — live smoke result

Date: 2026-09-04
Status: **PASS / RESEARCH INFRASTRUCTURE ONLY**

## Evidence supplied from the real Windows lab

Three-minute full gate completed successfully with one health-fixed EIB collector and one shared market-state engine.

Observed summary:
- full gate: `PASS`;
- raw collector gate: `PASS`;
- 298 unique raw events;
- 0 duplicate event IDs;
- 0 future-availability violations;
- 36 generation samples / 36 unique generations;
- final BTCUSD quality: `OK`;
- final ETHUSD quality: `OK`;
- BTC/ETH core age roughly 4.25 s;
- shared state contained spot/perpetual prices, OI, funding, basis, rolling returns, OI changes and liquidation aggregates;
- no strategy BUY/SELL decision output was emitted.

Final generation observed: `1788507871038`.

## Important scientific observation from this same smoke

The smoke also exposed a semantic integrity issue that must be fixed **before any Guardian strategy consumes the shared features**:

- some `5m` and `15m` returns were identical because the engine selected the latest observation at-or-before the target window boundary even when that observation came from an older collection session;
- liquidation windows reported numeric zero / partial sums even when the collector had not necessarily covered the entire requested historical window continuously.

This is not lookahead and does not invalidate the collector/shared-service transport PASS. It is a **window-coverage semantics problem**: a nominal 5-minute feature must not silently use a much older anchor, and a liquidation sum may be reported as zero only when the liquidation channel was continuously observed over that whole window.

## Decision

Shared-service transport/atomic publication is validated enough to continue research, but Guardian read-only consumption remains blocked until a coverage-aware market-state candidate passes:

1. boundary-anchor freshness checks for price/OI changes;
2. explicit per-window coverage metadata;
3. liquidation sums set to `null` when websocket/health coverage is incomplete;
4. numeric zero retained only when the window is demonstrably covered and no liquidation occurred;
5. offline tests + a continuous live warm-up smoke.

No RSI, Momentum or D025 rule change is authorized by this result.
