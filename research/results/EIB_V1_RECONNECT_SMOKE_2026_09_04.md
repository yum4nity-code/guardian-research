# EIB V1 — reconnect smoke evidence

Date: 2026-09-04
Status: `RECONNECT SMOKE PASS / FINAL HEALTH SNAPSHOT TO CONFIRM`

## Test

A 3-minute live smoke was run on the user's Windows machine with a manual Internet interruption of roughly 30-40 seconds followed by reconnection.

Command used:

```powershell
.\.venv\Scripts\python.exe smoke_v1.py --minutes 3 --data-dir "D:\MT5_Backtests\Research\ExternalIntelligence"
```

## Observed result

- gate: `PASS`
- observed duration: `178.84 s`
- unique events: `320`
- duplicate event IDs: `0`
- future availability violations: `0`
- invalid JSON lines: `0`
- missing core channels: none
- quality transitions observed: `DOWN=2`, `PARTIAL=2`, `STALE=6`, `OK=310`
- BTC core rows: 31 each for spot last price, perp last price, OI, funding
- ETH core rows: 31 each for spot last price, perp last price, OI, funding
- health rows: 36 per symbol (known health-spam issue still present)
- no liquidation event happened during this short window, so liquidation-specific replay/deduplication across reconnect was not directly exercised by this run.

## Interpretation

The interruption was detected: non-OK health states (`PARTIAL`, `STALE`) were persisted during the outage. Core market rows resumed within the same process after connectivity returned, and the run completed with no duplicate event IDs, no malformed JSON, no missing core channel and no availability-time violation.

This is strong evidence that same-process network reconnect and append behavior work for the REST/core stream. It does not by itself prove cross-process restart deduplication, nor liquidation-event deduplication when a liquidation is replayed by the provider after reconnect.

## Remaining immediate gates

1. Read the final `health.json` snapshot after reconnection and confirm BTC/ETH are `OK` and websocket is connected.
2. Fix health-record spam: volatile age values must not make every 5-second health check look like a semantic state change.
3. Run a short post-fix smoke and verify health events are change-driven + heartbeat (~1/min), not every loop.
4. Then prototype `market_state_v1` shared intelligence state; no strategy rule changes yet.
