# D023 AutoSync v1.02 — install, recover existing outputs, then smoke only if needed

Priority: **P0 / local Codex action**

Do not run any already completed long backtest again.

## First objective: recover before rerunning anything

Pull `main` and inspect these exact local files first:

- `%APPDATA%\MetaQuotes\Terminal\Common\Files\D023_V108_USDJPY_2023_STATS.csv`
- `%APPDATA%\MetaQuotes\Terminal\Common\Files\D023_V108_USDJPY_2023_TRADES.csv`

Also inspect:

- `D:\MT5_Backtests\logs\guardian-backtest-csv-sync.log`
- `D:\MT5_Backtests\guardian-backtest-csv-sync-state.json`
- any existing `D:\MT5_Backtests\guardian-backtest-autosync-results`

If a finalized v1.08 pair already exists, **do not rerun the smoke just to recreate it**. Validate and publish that pair first.

## New P0 sync source

`automation/Guardian_Backtest_CSV_AutoSync_v1_02_D023_RESILIENT_PUBLICSAFE.ps1`

Read:

`research/results/D023_AUTOSYNC_V102_STATIC_AUDIT_2026_09_06.md`

v1.02 is deliberately D023-only. It validates the pair, redacts local Windows username paths before GitHub, records source and published hashes, uses deterministic run identity, retries Git failures without killing the watcher and emits a health JSON.

## Recovery sequence

1. `git pull` the Guardian repo.
2. Verify the v1.02 file exists.
3. If finalized D023 v1.08 STATS/TRADES already exist, run v1.02 with `-Once`.
4. Inspect:
   - `D:\MT5_Backtests\guardian-d023-csv-sync-v102-health.json`
   - `D:\MT5_Backtests\logs\guardian-d023-csv-sync-v102.log`
5. Verify branch `backtest-results` now contains:
   - `backtests/inbox/LATEST.json`
   - one deterministic D023 run directory
   - both CSVs
   - `sync_manifest.json`
6. Verify manifest source SHA256 against the local originals.
7. Verify GitHub STATS contains no unredacted `C:\Users\<name>` path.
8. Return the branch commit SHA and the exact run path to ChatGPT.

## If no valid finalized v1.08 pair exists

Then install v1.02 and continue the already-authorized v1.08 engineering gate only:

1. real FundedNext MetaEditor compile;
2. require 0 errors / 0 warnings;
3. USDJPY M15 Every tick smoke only, `2023-03-13` through `2023-03-31`;
4. inspect local STATS/TRADES directly;
5. require `INIT -> READY -> FINAL` and `csv_trade_rows == trades_closed`;
6. manually verify at least three ORB sessions and DST behavior across 2023-03-26;
7. confirm v1.02 pushed the same validated pair to `backtest-results`;
8. return compile evidence, local hashes, GitHub run path and validation notes.

## Hard block

**Do not run the full 2023 confirmation until compile 0/0 + smoke + direct CSV/manual DST validation are all PASS.**

Do not tune D023, remove SHORT, add filters, change manager logic or change the frozen 2023 gates.
