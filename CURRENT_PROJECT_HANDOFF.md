# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-04 13:36 Europe/Paris
Status: ACTIVE / LIVE RESEARCH RUNNING / D025 V3 ISOLATED TESTER LAUNCHED

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

The runtime is now Windows-autostarted and supervised.

Relevant files:
- `research/external_intelligence/shared_runtime_multivenue_bridge_v1.py`
- `research/external_intelligence/run_shared_multivenue_autostart_v1.ps1`
- `research/external_intelligence/install_shared_multivenue_autostart_v1.ps1`
- `research/external_intelligence/INSTALL_SHARED_MULTIVENUE_AUTOSTART_V1.cmd`
- `research/external_intelligence/REMOVE_SHARED_MULTIVENUE_AUTOSTART_V1.cmd`

Windows scheduled task:
- name: `Guardian Shared Intelligence MultiVenue V1`
- latest user-verified state: `Running`
- `Last result 267009 / 0x41301` while Running means the scheduled task is still executing, not a failure.
- task launches hidden in background after logon.
- supervisor prevents duplicate supervised instances and restarts the runtime after abnormal exit with bounded backoff.

Important: collectors remain read-only; no API key with trading rights is used or accepted.

## 3. D025 — Liquidity Exhaustion Reclaim

Research thesis and preregistration:
- `research/campaigns/D025_LIQUIDITY_EXHAUSTION_RECLAIM_PREREGISTRATION.md`

Locked V0 mechanical rules:
- `research/campaigns/D025_LER_V0_RULES_LOCK_2026_09_04.md`
- thresholds were locked before D025 outcomes were inspected; do not tune them post hoc.

Current EA source:
- `research/ea/D025_LER_Observer_V0.mq5`
- MT5 `#property version`: **1.00**
- research generation name remains **V0**; this is separate from the MT5 build version.
- V0 contains no trading library and no order function.
- monitors BTCUSD + ETHUSD from one EA instance, regardless of host-chart symbol/timeframe.
- state machine: `IDLE -> LEVEL_WATCH -> SWEEP -> CASCADE -> EXHAUSTION -> RECLAIM -> RETEST/ACCEPTANCE -> VALID_SIGNAL`.
- `VALID_SIGNAL` creates only a virtual trade, then M1 tracks MFE/MAE and +1R..+5R / virtual SL for up to 48h.

Current live state:
- EA installed and running in MT5 on a spare USDSEK chart.
- changing the host chart H1 -> M1 produced `STOP reason=3` followed by normal restart; this is expected on chart parameter/timeframe change.
- first observed live sweeps immediately after launch:
  - BTCUSD `H1_SWING_HIGH`, depth ~0.283 ATR
  - ETHUSD `H1_SWING_HIGH`, depth ~0.109 ATR
- no active virtual trades were lost during that restart.

D025 FILE_COMMON outputs:
- `GuardianResearch/D025/d025_ler_v0_events.csv`
- `GuardianResearch/D025/d025_ler_v0_virtual_trades.csv`
- `GuardianResearch/D025/d025_ler_v0_outcomes.csv`

## 4. Live-status GitHub sync

A compact live-state mirror is installed and validated.

Architecture:

`MT5 local CSVs + Shared Intelligence runtime state -> local sync watcher -> GitHub branch live-status -> LIVE_RESEARCH_STATUS.json`

Properties:
- dedicated branch: `live-status`;
- single compact file: `LIVE_RESEARCH_STATUS.json`;
- `main` remains clean;
- watcher runs automatically in background on Windows;
- heartbeat target: every 15 minutes;
- significant D025 changes / `VALID_SIGNAL` / runtime alert can trigger an earlier refresh;
- generation ids are included for visibility but do not themselves trigger a push;
- the live-status branch is rewritten/amended to avoid commit explosion.

Validated GitHub read on 2026-09-04 after installation showed:
- D025 MT5 version `1.00`, research generation `V0`;
- `signals_are_virtual_only=true`;
- 14 D025 event rows visible at that snapshot;
- 0 virtual trades at that snapshot;
- Shared Intelligence scheduled task `Running`;
- BTC Bybit/Binance `OK/OK`, `both_core_ok=1`;
- ETH Bybit/Binance `OK/OK`, `both_core_ok=1`;
- no runtime alert.

A fresh ChatGPT instance may therefore read the `live-status` branch to recover recent research state without asking the user to paste MT5 logs.

## 5. D025 automated FundedNext backtest — current state

Confirmed user target:
- account **14202634**;
- server **FundedNext-Server 2**;
- mode **Hedge**;
- company **FundedNext Ltd**.

Superseded launchers:
- V1 selected another FundedNext installation and is superseded.
- V2 folder discovery failed on the real Server 2 installation because broker/account strings were not persisted where expected.

Current launcher:
- `automation/run_d025_fundednext_backtest_v3.ps1`
- `automation/RUN_D025_FUNDEDNEXT_BACKTEST_V3.cmd`
- `automation/publish_d025_backtest_results_v1.ps1`
- `automation/analyze_d025_backtest_v1.py`

V3 targeting:
- binds to the live MT5 window whose title contains both account and server;
- maps that process to the exact MT5 data path through `origin.txt`;
- then creates a separate portable clone for the test;
- live FundedNext terminal / Guardian are not closed or commandeered.

Resolved exact live target from the user's machine:
- PID `15104`;
- title contained `14202634 - FundedNext-Server 2 - Hedge - FundedNext Ltd`;
- executable `D:\MT5_FundedNext\terminal64.exe`;
- MT5 data path `C:\Users\armor\AppData\Roaming\MetaQuotes\Terminal\D943DED8A972BBD3A21ED90520AE6479`.

Earlier V3 temp-runner repo-root bug was fixed on `main`: temporary patched V2 runner is now written inside `automation/`, so the D025 source resolves from the repository correctly.

### 2026-09-04 13:36 user-verified launch

The rerun progressed successfully beyond compilation and entered the isolated tester workflow. Screenshot evidence showed:
- harness compile: `0 errors, 0 warnings`;
- step `5/8 Launch isolated Strategy Tester` reached;
- run id: `D025_FN2_CORE_20260904_133554`;
- account: `14202634`;
- server: `FundedNext-Server 2`;
- period: `2025.01.01 -> 2026.06.28`;
- symbols: `BTCUSD + ETHUSD`;
- model: `real ticks`;
- live trading: `DISABLED`;
- script entered `6/8 Verify exact portable target and wait for completion`.

At this snapshot the script had **not yet printed** `CONFIRMED TARGET` and had **not yet completed** the backtest. Do not claim completion until either the exact portable-target confirmation appears and later `COMPLETE.txt` / GitHub results are produced, or an error is reported.

Portable behavior:
- dedicated clone `D:\MT5_Backtests\Terminals\FundedNext_14202634_D025_BT`;
- isolated D025 harness preserves all locked V0 thresholds;
- BTCUSD + ETHUSD, host BTCUSD M1, `Model=4` real ticks;
- default period `2025.01.01 -> 2026.06.28`;
- `AllowLiveTrading=0`; D025 contains no order functions;
- tester output is separated from forward-live D025 CSVs.

Results publication target:
- branch `backtest-results`;
- path `backtests/d025/<RUN_ID>/`;
- compact summary / manifest / event table only; large raw CSVs remain local with hashes recorded.

## 6. Scientific separation

D025 V0 currently uses **MT5 Core only** for signal-state transitions. Binance/Bybit continues collecting independently but does not trigger D025 V0.

Reason: preserve attribution and later compare, without lookahead:
- Core
- Core + OI
- Core + liquidations
- Core + spot/perp dislocation
- preregistered multi-venue combination

External observations may only be joined if `available_at <= event_time`.

Do not inject Shared Intelligence directly into live RSI or Momentum merely because the fields are available.

## 7. Next safe actions

1. Leave the current V3 PowerShell run alone while it verifies the portable target and executes the backtest.
2. Trust the run only after `CONFIRMED TARGET: 14202634 / FundedNext-Server 2` appears.
3. Completion requires the later `COMPLETE.txt` / analysis / GitHub publish sequence; inspect `backtest-results` after completion.
4. If V3 errors before confirmation/completion, preserve the error lines and fix the launcher; do not manually alter D025 thresholds.
5. Keep D025 Observer 1.00 running live in parallel.
6. Compare backtest state-machine behavior with forward behavior before any strategy conclusion.
7. After sufficient Core evidence, join timestamp-valid Binance/Bybit features for Crypto+ comparisons.
8. Only after robustness/OOS/cost/red-team gates may anything become a Guardian trading candidate.

## 8. MT5 versioning rule

For this project, `#property version` must use a MetaEditor-compatible simple numeric version. Use **1.00, 1.01, 1.02 ...** for this D025 EA lineage rather than semantic/build strings. Research labels such as V0/V1 may remain in filenames/descriptions but are not the MT5 `#property version`.

## 9. User-operation style

The user is not expected to infer shell commands. For local operations, provide complete copy/paste PowerShell/CMD blocks and explain only the necessary verification result.

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

After every material milestone (new active version, user compile/deploy validation, gate pass/fail, change in architecture, new live research component, change of backtest state, or change of next safe action), update this file in the same work session. No important current state should exist only in ChatGPT/Codex conversation context.
