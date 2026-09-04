# EIB V1 — post-smoke next gates

Date: 2026-09-04
Status: LIVE SMOKE PASS / REAL REPLAY PASS / RECONNECT PENDING

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

This validates basic live collection. It does **not** yet validate reconnect behavior or long-run retention.

## Real replay evidence

Real captured JSONL was replay-tested with the strict availability-time gate:

- `--until-ms 1788500321048` (1 ms before smoke start) -> `0` visible lines;
- `--until-ms 1788500331049` (~10 s after smoke start) -> `20` visible lines.

Verdict: **PASS**. The replay did not expose any observation before its recorded `available_at_ms` on this real sample. This is evidence for the anti-lookahead invariant on live-captured data, not only on offline unit tests.

## Immediate next gates

1. ~~Real replay test on the captured JSONL using strict `available_at_ms` gating.~~ **PASS**
2. Short manual network interruption/reconnect test.
3. Verify collector resumes appending, does not truncate, and produces no duplicate event IDs.
4. Verify PARTIAL/STALE/DOWN transitions are observable during interruption and recovery returns to OK.
5. Fix health-record spam (current V1 writes health too frequently because age is part of the changing reason/signature).
6. Re-run a short smoke after the health fix and remeasure raw/gzip storage.
7. Only then prototype `market_state_v1` for the shared per-PC intelligence service.

## Shared intelligence prototype gate

The first shared-state prototype must remain neutral and strategy-agnostic. It may expose rolling facts such as OI deltas, liquidation sums/z-scores, spot/perp returns/dislocation, funding and quality/age. It must not emit BUY/SELL decisions.

Guardian Core protections, risk and prop-firm compliance must remain independent of this service.
