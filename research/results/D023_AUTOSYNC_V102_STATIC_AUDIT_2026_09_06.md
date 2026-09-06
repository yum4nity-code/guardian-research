# D023 AutoSync v1.02 static audit — 2026-09-06

Status: **STATIC-AUDITED / LOCAL POWERSHELL SMOKE PENDING**

Source:

`automation/Guardian_Backtest_CSV_AutoSync_v1_02_D023_RESILIENT_PUBLICSAFE.ps1`

Source commit:

`2021c4f57c83e4990e443596c19ed02b90ad1ffd`

## Why v1.02 exists

The generic v1.01 watcher was not reliable enough for the D023 P0 handoff.

Observed repository state before v1.02:

- branch `backtest-results` existed;
- its head was still `4d4a300c00d882dc66a497689284b0cc2827e165` from 2026-09-04;
- `backtests/inbox/LATEST.json` did not exist;
- therefore no AutoSync publication was recoverable from GitHub at takeover time.

Static audit of v1.01 also found two concrete failure classes:

1. **liveness failure** — a Git/push exception escapes to the outer catch and terminates the watcher instead of keeping it alive for later retry;
2. **PUBLICSAFE grouping inconsistency** — D023 STATS intentionally contains exact local output paths. A STATS file can be rejected by the per-file `C:\Users\...` safety filter, while a TRADES-triggered group can subsequently add that same STATS companion without rerunning the safety check.

This means v1.01 can behave inconsistently and can potentially upload a local Windows user path despite the PUBLICSAFE label.

## v1.02 scope

v1.02 is intentionally narrow. It is the P0 D023 path, not a claim that the generic AutoSync problem is solved for every future research format.

It watches only the exact v1.08 output pair in MT5 `FILE_COMMON`:

- `D023_V108_USDJPY_2023_STATS.csv`
- `D023_V108_USDJPY_2023_TRADES.csv`

It does not run any backtest and does not modify D023 strategy semantics.

## Validation gates before upload

A pair is publishable only when:

- both exact files exist;
- the pair has remained unchanged for the stability window;
- STATS contains ordered `INIT -> READY -> FINAL`;
- `source_name` is the exact v1.08 harness source;
- `source_version == 1.08`;
- symbol contains USDJPY;
- timeframe is `PERIOD_M15`;
- `trades_closed == csv_trade_rows`;
- physical TRADES data-row count equals `trades_closed`;
- source hashes are unchanged across validation.

## Public-safe handling

The original local STATS source hash is recorded in `sync_manifest.json`.

Before GitHub publication, Windows user-profile path segments matching `C:\Users\<name>\...` are redacted to `C:\Users\<REDACTED>\...` in the published STATS snapshot. The manifest records both source SHA256 and published SHA256 and marks the STATS snapshot `sanitized=true`.

TRADES is copied without transformation but is still checked for blocked sensitive patterns.

## Retry / crash behavior

- Git operations retry with bounded exponential backoff.
- A per-cycle failure is logged and the watcher remains alive.
- The publication path is deterministic from source hashes + source last-write timestamps.
- A local pending transaction is committed/reconciled before the next publication.
- If push succeeds but local state persistence does not, the deterministic manifest path prevents a duplicate run folder on restart.
- A health JSON is maintained at `D:\MT5_Backtests\guardian-d023-csv-sync-v102-health.json`.

## Remaining required local validation

This ChatGPT environment does not contain Windows PowerShell/MetaTrader and therefore has **not** runtime-executed this script.

Before relying on it for the full 2023 gate, Codex/local must:

1. pull main;
2. run the v1.02 script with `-Once` against any existing finalized v1.08 pair if present;
3. otherwise install it and execute only the already-preregistered short D023 smoke flow;
4. verify the local health/log files;
5. verify that `backtest-results/backtests/inbox/LATEST.json` appears;
6. inspect the uploaded manifest and both CSVs;
7. verify that no unredacted `C:\Users\<name>` path is present on GitHub;
8. verify source hashes in the manifest against the local originals;
9. verify D023 counters and several ORB/DST sessions directly.

**Do not run full 2023 merely to test AutoSync.** The existing short smoke gate remains the required engineering proof before the untouched full confirmation.
