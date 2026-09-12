# R5 post-result cold audit — infrastructure repair r2

## Trigger

`R5-POST-RESULT-COLD-AUDIT-PREFLIGHT r1` terminated before market-data access with an assertion failure in the aligned M5/raw-M1 synthetic reference test.

## Root cause

The v1_00 replay converted timezone-aware pandas timestamps with `Series.astype('int64')` and then treated the resulting integers as nanoseconds. On the runtime pandas build the datetime storage resolution can be microseconds, so adding `tf_seconds * 1e9` produced an invalid entry target. This is an implementation/unit defect, not scientific evidence.

## Frozen scientific semantics

No scientific parameter changes. R2 must preserve exactly:
- first raw-M1 open at/after source-bar close as entry reference;
- first raw-M1 open at/after frozen source-row `t+h+1` timestamp as exit reference;
- same-year purge restricted to 2024/2025;
- exact R5 result SHA256 `81dd16fabf001025c4dc144035d538fa46fab2fc768ba237610e027af1c7d34e`;
- `EDGE_DRIFT_LIMIT = 0.005` ATR;
- `SELECTED_MISMATCH_LIMIT = 0.01`;
- reject-only interpretation;
- protected 2026 forbidden.

## Repair

Normalize timestamps explicitly to UTC nanoseconds via `DatetimeIndex(...).asi8` before search/mapping. Add a deterministic resolution-independence test comparing ns/us-backed synthetic frames. No market-data access is permitted in preflight r2.

If preflight r2 PASSes, rerun the same frozen post-result audit as immutable revision 2 using only the timestamp-unit repair. If it fails, do not infer anything about R5 alpha and do not open 2026.
