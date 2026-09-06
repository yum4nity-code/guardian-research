# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-06 Europe/Paris
Status: **ACTIVE / D023 P0 / V1.08 HARNESS STATIC-AUDITED / AUTOSYNC V1.02 STATIC-AUDITED / LOCAL RECOVERY+COMPILE+SMOKE PENDING / FULL 2023 BLOCKED**

## Canonical entrypoint

Read first:

1. `START_HERE_NEXT_AI.md`
2. `GUARDIAN_MASTER_MANDATE.md`
3. `handoff/guardian_next_ai/2026/09/06/GUARDIAN_PROJECT_RESTART_HANDOFF_2026_09_06.md`
4. `CURRENT_QUEUE.json`

The Sep-6 restart handoff supersedes older execution-order text in historical handoffs.

## Current P0 — D023 USDJPY London ORB

D023 is the current primary research candidate.

FundedNext/DST-aware inspected 2024-2026 conformance remains:

- n = 482;
- mean net about +0.0915R/trade;
- cumulative about +44.10R;
- net PF about 1.176;
- positive 2024, 2025 and 2026 H1, but weakening through time.

This is **CANDIDATE evidence, not validation**.

Frozen strategy semantics remain unchanged:

- USDJPY M15;
- London OR 08:00-09:00, exactly four M15 bars;
- first strict M15 close outside OR from 09:00 inclusive to 11:00 exclusive;
- enter next M15 open on executable spread side;
- stop opposite OR edge;
- maximum one trade/day;
- exit at stop or close of the M15 bar finishing 16:00 London;
- no EMA/RSI/ATR/day/news/direction rescue filters.

Do not remove SHORT because LONG looked stronger on inspected data.

## Untouched 2023 confirmation gates — frozen

All are required for CONFIRM:

- n >= 150;
- mean net R > 0;
- net PF >= 1.10;
- 5-day moving-block bootstrap lower 5% bound of zero-filled weekday daily mean net R > 0;
- total/mean result remains positive under 1.5x commission.

Do not alter these after seeing 2023.

## Active D023 harness — v1.08

Source:

`research/strategies/d023/D023_USDJPY_LondonORB_M15_v1_08_FUNDEDNEXT_2023_HARNESSFIX_20260906.mq5`

SHA256:

`10e86306d87b6d5f1c507ae724c629c972be0f53c3e586f2fd700691fadc1de4`

Source commit:

`b0fb0bc6b557aea5c58cd56a041856a3a0bccd7b`

Static audit:

`research/results/D023_V108_2023_HARNESS_STATIC_AUDIT_2026_09_06.md`

### Provenance resolved

The exact historical local v1.07 source was recovered from the user's ChatGPT Library. SHA256:

`34ce816eef241c662d6b9fa3be3caea62bc67a25d034bf6cb86e9c67903fff01`

This exactly matches the SHA recorded in the restart handoff. Its broken path literal and stale v1.06 log labels are confirmed defects in the actual warned-about v1.07.

v1.08 changes harness/observability only. Static comparison against exact v1.07 found the calendar/DST/cost/state section, `WriteTrade`, and complete `OnTick` strategy path byte-identical.

v1.08 is **not yet real-MetaEditor compile validated**.

## D023 output recovery / GitHub AutoSync — current P0 engineering path

At takeover, GitHub branch `backtest-results` existed but was still at commit:

`4d4a300c00d882dc66a497689284b0cc2827e165` — `Document automated backtest results branch` — 2026-09-04.

`backtests/inbox/LATEST.json` did not exist. Therefore no D023 AutoSync output was recoverable from GitHub at takeover time.

The generic watcher v1.01 was statically audited and found insufficient for D023 P0:

- a Git/push exception can terminate the watcher;
- D023 STATS contains exact local output paths, including normal `C:\Users\...` paths;
- v1.01 can reject STATS in the per-file PUBLICSAFE filter but later re-add that same STATS through a TRADES-triggered companion group without rerunning the safety check.

New P0 watcher:

`automation/Guardian_Backtest_CSV_AutoSync_v1_02_D023_RESILIENT_PUBLICSAFE.ps1`

Source commit:

`2021c4f57c83e4990e443596c19ed02b90ad1ffd`

Static audit:

`research/results/D023_AUTOSYNC_V102_STATIC_AUDIT_2026_09_06.md`

Local-action handoff:

`handoff/chatgpt_to_codex/2026/09/06/D023_AUTOSYNC_V102_INSTALL_RECOVER_AND_SMOKE_REQUEST_2026_09_06.md`

v1.02 is intentionally D023-only for the P0 recovery path. It:

- watches the exact v1.08 STATS/TRADES pair in MT5 `FILE_COMMON`;
- first tries to recover already-existing finalized outputs before any rerun;
- requires ordered `INIT -> READY -> FINAL`;
- requires exact v1.08 source/version, USDJPY, PERIOD_M15;
- requires `trades_closed == csv_trade_rows == physical TRADES rows`;
- verifies source hashes are stable across validation;
- redacts local Windows username paths from the GitHub STATS snapshot;
- records source and published SHA256 values in `sync_manifest.json`;
- uses deterministic run identity to avoid duplicate run folders after crash/restart;
- retries Git failures and keeps the watcher alive across per-cycle errors;
- writes local health status to `D:\MT5_Backtests\guardian-d023-csv-sync-v102-health.json`.

Important: v1.02 is **static-audited only** in ChatGPT because this environment has no Windows PowerShell/MT5 runtime. Local runtime proof is still required.

## Next safe action — mandatory

Codex/local must do this in order:

1. sync repo;
2. inspect whether finalized local v1.08 STATS/TRADES already exist in `%APPDATA%\MetaQuotes\Terminal\Common\Files`;
3. if they exist, run AutoSync v1.02 `-Once`, validate/publish them, and **do not rerun the smoke merely to recreate output**;
4. if they do not exist, verify v1.08 SHA256 exactly;
5. real compile in the relevant FundedNext MetaEditor;
6. require **0 errors / 0 warnings**;
7. run only USDJPY M15 Every tick smoke `2023-03-13` through `2023-03-31`;
8. directly inspect local `D023_V108_USDJPY_2023_STATS.csv` and `D023_V108_USDJPY_2023_TRADES.csv`;
9. require STATS `INIT -> READY -> FINAL`, nonzero counters as expected and `csv_trade_rows == trades_closed`;
10. manually verify at least three ORB sessions;
11. verify DST behavior on both sides of the 2023-03-26 UK transition;
12. verify the same validated pair is present under `backtest-results/backtests/inbox/...` with a manifest and no unredacted Windows username path;
13. return compile evidence + local hashes + GitHub run path + smoke outputs for audit.

Expected smoke clock behavior:

- weekdays 2023-03-13 through 2023-03-24: FundedNext UTC+3, London UTC+0, server-London = 3h;
- from Monday 2023-03-27: FundedNext UTC+3, London UTC+1, server-London = 2h.

Inherited output convention: a `TIME_1600` exit uses the close price of the 15:45-16:00 London bar, but CSV `exit_time_*` records that M15 bar's opening timestamp (15:45). Do not misread this as an economic 15:45 exit.

### Hard block

**Do NOT run full `2023-01-02` through `2023-12-29` yet.**

If compile or smoke fails, create a new uniquely named harness version and change harness/observability only. Do not touch ORB semantics.

Only after compile 0/0 + smoke PASS + direct CSV/manual clock validation + AutoSync publication proof may the untouched full 2023 confirmation be run exactly once.

## D17 Momentum

D17 Momentum is closed as a current alpha candidate after broad attribution across BTCUSD, ETHUSD, EURUSD, GBPUSD, USDJPY, XAUUSD and USDCAD.

Preserve D17 only for source lineage and Manager Evidence Ledger. Do not restart a rescue campaign or tune inspected D17 samples.

Manager evidence remains useful, but a dedicated Manager Lab should wait for similar management weakness on an independent confirmed strategy family.

## Guardian Core

Guardian Core v12.01 is the stable compile-validated pure infrastructure baseline.

Canonical note:

`production/guardian/GUARDIAN_CORE_V12_01_COMPILE_VALIDATED_2026_09_06.md`

Keep Core stable during strategy research. Strategies integrate through the registry/API; do not turn Core back into the research laboratory.

## FundedNext runtime issue

FundedNext request/retry hyperactivity is a separate runtime/compliance problem.

FundedNext AUTO remains OFF until request budgeting, deduplication, retry/backoff behavior and safety are bounded and verified. Do not mix this runtime issue into D023 alpha conclusions.

## Communication / persistence

After every material milestone:

- update `CURRENT_QUEUE.json`;
- update this handoff;
- update `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md` for the Europe/Paris workday;
- persist local-action requests through the ChatGPT/Codex handoff + inbox mechanism when needed.

For D023 run results report concisely:

**VERDICT — N — expectancy — PF — stability/cost issue — next action**
