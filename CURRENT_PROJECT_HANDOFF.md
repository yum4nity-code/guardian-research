# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-04 13:38 Europe/Paris
Status: ACTIVE / LIVE RESEARCH RUNNING / D025 V3 PORTABLE SERVER MATCH FIXED

This file is the canonical fast-resume entry point for a fresh ChatGPT/Codex instance. It must stay current enough that the project can be resumed without relying on conversation history.

## 1. Current live Guardian

- User-local name: **Guardian 17**.
- Lineage: Guardian v11.17.x; current documented integration is the multi-venue Shared Intelligence observer branch (v11.17.06 candidate lineage).
- Guardian is compiled and installed on FTMO Demo.
- Shared Intelligence is strictly observational/read-only and has **NO TRADING EFFECT**.
- Live MT5 evidence on 2026-09-04 showed:
  - `[SHAREDINTEL][MV][OBSERVER] ready=YES`
  - BTC Bybit/Binance = `OK/OK`, `both=YES`
  - ETH Bybit/Binance = `OK/OK`, `both=YES`
  - fresh generation ids advancing
  - sub-second source ages in observed samples
- Guardian production risk/compliance/RSI/Momentum must remain independent from external-intelligence availability.

## 2. Shared Intelligence runtime

Architecture:

`Bybit collector + Binance collector -> venue-separated market state -> MT5 FILE_COMMON bridge -> Guardian/read-only research consumers`

The runtime is Windows-autostarted and supervised. Relevant files remain under `research/external_intelligence/`. The Windows task is `Guardian Shared Intelligence MultiVenue V1`. Collectors are read-only; no trading API rights are used.

## 3. D025 — Liquidity Exhaustion Reclaim

Research thesis and preregistration:
- `research/campaigns/D025_LIQUIDITY_EXHAUSTION_RECLAIM_PREREGISTRATION.md`

Locked V0 mechanical rules:
- `research/campaigns/D025_LER_V0_RULES_LOCK_2026_09_04.md`
- thresholds were locked before D025 outcomes were inspected; do not tune them post hoc.

Current EA source:
- `research/ea/D025_LER_Observer_V0.mq5`
- MT5 `#property version`: **1.00**
- research generation remains **V0**;
- no trading library / order function;
- monitors BTCUSD + ETHUSD from one EA;
- state machine: `IDLE -> LEVEL_WATCH -> SWEEP -> CASCADE -> EXHAUSTION -> RECLAIM -> RETEST/ACCEPTANCE -> VALID_SIGNAL`;
- `VALID_SIGNAL` creates only a virtual trade and tracks MFE/MAE and +1R..+5R / virtual SL for up to 48h.

D025 live forward outputs remain under `FILE_COMMON/GuardianResearch/D025/` and are mirrored compactly on branch `live-status`.

## 4. Live-status GitHub sync

Compact live mirror remains installed and validated:
- branch `live-status`;
- single file `LIVE_RESEARCH_STATUS.json`;
- ~15 minute heartbeat plus significant-event refresh;
- current main branch is not flooded with live commits.

## 5. D025 automated FundedNext backtest — current state

Confirmed user target:
- account **14202634**;
- server **FundedNext-Server 2**;
- mode **Hedge**;
- company **FundedNext Ltd**.

Current launcher:
- `automation/run_d025_fundednext_backtest_v3.ps1`
- `automation/RUN_D025_FUNDEDNEXT_BACKTEST_V3.cmd`
- publisher/analyzer remain `publish_d025_backtest_results_v1.ps1` and `analyze_d025_backtest_v1.py`.

Exact live target resolved successfully from the user's machine:
- live title contained `14202634 - FundedNext-Server 2 - Hedge - FundedNext Ltd`;
- executable `D:\MT5_FundedNext\terminal64.exe`;
- MT5 data path `C:\Users\armor\AppData\Roaming\MetaQuotes\Terminal\D943DED8A972BBD3A21ED90520AE6479`.

The V3 repo-root temp-runner bug was fixed earlier by keeping the temporary patched V2 runner inside `automation/`.

### Portable verification incident at 13:37

Run `D025_FN2_CORE_20260904_133554` compiled successfully (`0 errors, 0 warnings`) and launched the isolated tester with:
- account `14202634`;
- expected server `FundedNext-Server 2`;
- BTCUSD + ETHUSD;
- `2025.01.01 -> 2026.06.28`;
- real ticks;
- live trading disabled.

Portable verification then failed with:
- `account_seen=True`
- `server_seen=False`

This indicates the portable clone recognized the correct account but the exact server string was not found verbatim in logs. FundedNext may persist equivalent server names with punctuation/spacing differences such as `FundedNext-Server2`.

Fix committed on `main`:
- V3 still requires **both account and server confirmation**;
- server matching is now normalized by lowercasing and removing all non-alphanumeric characters;
- verification checks both the portable terminal window title and the latest portable terminal logs;
- examples like `FundedNext-Server 2` and `FundedNext-Server2` therefore compare equal;
- no D025 signal rule, threshold, tester period, trading authority or risk logic changed.

Next user action: `git pull` and rerun `automation/run_d025_fundednext_backtest_v3.ps1`. Trust the run only after `CONFIRMED TARGET: 14202634 / FundedNext-Server 2` appears and later the completion/analyze/publish sequence finishes.

Portable behavior remains:
- dedicated clone `D:\MT5_Backtests\Terminals\FundedNext_14202634_D025_BT`;
- live FundedNext terminal and Guardian are untouched;
- `AllowLiveTrading=0`;
- output separated from forward-live D025 CSVs.

Results publication target:
- branch `backtest-results`;
- path `backtests/d025/<RUN_ID>/`;
- compact summary / manifest / event table only; large raw CSVs remain local with hashes recorded.

## 6. Scientific separation

D025 V0 currently uses **MT5 Core only** for signal-state transitions. Binance/Bybit continues collecting independently but does not trigger D025 V0. External observations may only be joined later with `available_at <= event_time`. Do not inject Shared Intelligence directly into live RSI or Momentum merely because the fields are available.

## 7. Next safe actions

1. Keep the correct live FundedNext MT5 window open.
2. `git pull`, then rerun `run_d025_fundednext_backtest_v3.ps1`.
3. Trust the run only after `CONFIRMED TARGET: 14202634 / FundedNext-Server 2`.
4. Completion requires later `COMPLETE.txt` / analysis / GitHub publish sequence; inspect branch `backtest-results`.
5. Keep D025 Observer 1.00 running live in parallel.
6. Compare backtest state-machine behavior with forward behavior before any strategy conclusion.
7. After sufficient Core evidence, join timestamp-valid Binance/Bybit features for Crypto+ comparisons.
8. Only after robustness/OOS/cost/red-team gates may anything become a Guardian trading candidate.

## 8. MT5 versioning rule

Use **1.00, 1.01, 1.02 ...** for this D025 EA lineage. Research labels such as V0/V1 may remain in filenames/descriptions but are not the MT5 `#property version`.

## 9. User-operation style

Provide complete copy/paste PowerShell/CMD blocks for local operations and only the necessary verification result.

## 10. Resume instructions for a fresh agent

Read, in this order:
1. `CURRENT_PROJECT_HANDOFF.md`
2. branch `live-status` -> `LIVE_RESEARCH_STATUS.json`
3. branch `backtest-results` -> newest D025 result if present
4. `research/results/D025_FUNDEDNEXT_V3_TARGETING_FIX_2026_09_04.md`
5. `research/campaigns/D025_LER_V0_RULES_LOCK_2026_09_04.md`
6. `research/ea/D025_LER_Observer_V0.mq5`
7. latest Shared Intelligence / Guardian result files
8. `CURRENT_QUEUE.json`
9. `docs/RESEARCH_STATUS.md`
10. `docs/STRATEGY_DECISIONS.md`

Then verify actual live/local state before launching or modifying anything. Real process/log state overrides a stale written status.

## 11. Continuity rule

After every material milestone, update this file in the same work session. No important current state should exist only in ChatGPT/Codex conversation context.
