# EIB V1 — post-smoke next gates

Date: 2026-09-04
Status: LIVE SMOKE PASS / REAL REPLAY PASS / RECONNECT PASS / HEALTH-SPAM FIX PENDING

## Live smoke evidence

The first real BTC/ETH smoke completed for ~35 minutes with gate PASS:
- 4210 unique events;
- 0 duplicate event IDs;
- 0 invalid JSON lines;
- 0 future-availability violations;
- no missing core channels;
- p50 source->receive lag 1 ms, p95 12 ms;
- 5 ETH liquidation events captured;
- raw file size 1.991 MB for the 35-minute window.

This validates basic live collection. Long-run retention remains a separate later concern.

## Real replay evidence

Real captured JSONL was replay-tested with the strict availability-time gate:

- `--until-ms 1788500321048` (1 ms before smoke start) -> `0` visible lines;
- `--until-ms 1788500331049` (~10 s after smoke start) -> `20` visible lines.

Verdict: **PASS**. The replay did not expose any observation before its recorded `available_at_ms` on this real sample. This is evidence for the anti-lookahead invariant on live-captured data, not only on offline unit tests.

## Manual network interruption / reconnect evidence

Three-minute smoke with a deliberate ~30-40 s Internet interruption:

- gate: `PASS`;
- 320 unique events;
- 0 duplicate event IDs;
- 0 invalid JSON lines;
- 0 future-availability violations;
- no missing core channels;
- quality transitions observed: `DOWN=2`, `PARTIAL=2`, `STALE=6`, `OK=310`;
- 31 observations were recovered for every core BTC/ETH market channel over the 3-minute run;
- final `health.json`: BTCUSD `OK`, ETHUSD `OK`, `ws_connected=true`;
- final reasons: fresh spot/perpetual data and liquidation websocket connected.

Verdict: **PASS** for interruption detection, stale/partial visibility, automatic recovery and resumed append behavior.

Caveat: no liquidation event occurred during this short reconnect window, so duplicate/replay behavior for a liquidation emitted exactly around reconnect remains a rare-case test to revisit later. Do not claim that specific edge case is proven by this run.

## Immediate next gates

1. ~~Real replay test on the captured JSONL using strict `available_at_ms` gating.~~ **PASS**
2. ~~Short manual network interruption/reconnect test.~~ **PASS**
3. ~~Verify collector resumes appending, does not truncate, and produces no duplicate event IDs in the observed run.~~ **PASS**
4. ~~Verify PARTIAL/STALE/DOWN transitions are observable during interruption and recovery returns to OK.~~ **PASS**
5. Fix health-record spam (current V1 writes health too frequently because age is part of the changing reason/signature).
6. Re-run a short smoke after the health fix and remeasure raw/gzip storage.
7. Prototype `market_state_v1` for the shared per-PC intelligence service.

## Shared intelligence prototype gate

The first shared-state prototype must remain neutral and strategy-agnostic. It may expose rolling facts such as OI deltas, liquidation sums/z-scores, spot/perp returns/dislocation, funding and quality/age. It must not emit BUY/SELL decisions.

Guardian Core protections, risk and prop-firm compliance must remain independent of this service.
