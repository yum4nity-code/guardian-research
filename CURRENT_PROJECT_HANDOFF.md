# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-04 13:20 Europe/Paris
Status: ACTIVE / LIVE RESEARCH RUNNING / D025 BACKTEST AUTOMATION READY

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

## 5. D025 automated FundedNext backtest

Automation is now prepared on `main`:
- `automation/run_d025_fundednext_backtest_v1.ps1`
- `automation/analyze_d025_backtest_v1.py`
- `automation/RUN_D025_FUNDEDNEXT_BACKTEST_V1.cmd`

Default run:
- auto-detect the MT5 terminal/data folder with strongest FundedNext evidence;
- compile a generated **backtest-only** D025 harness derived from `D025_LER_Observer_V0.mq5`;
- preserve all locked V0 thresholds;
- isolate tester CSVs under `FILE_COMMON/GuardianResearch/D025/Backtests/<RUN_ID>/` so live forward CSVs are never mixed with tester data;
- test BTCUSD + ETHUSD from one multi-symbol EA;
- host chart BTCUSD M1;
- period `2025.01.01 -> 2026.06.28` by default;
- Strategy Tester `Model=4` = Every tick based on real ticks;
- `AllowLiveTrading=0`, no order functions in D025, `ShutdownTerminal=0`;
- no optimization / no threshold search;
- wait for an EA-written `COMPLETE.txt` sentinel rather than closing the FundedNext terminal;
- analyze funnel, failures, MFE/MAE, R-hit timing, BTC/ETH and level breakdowns automatically.

Results publication:
- dedicated GitHub branch: `backtest-results`;
- one finite commit per completed run;
- path: `backtests/d025/<RUN_ID>/`;
- always publish `SUMMARY.md`, `summary.json`, `manifest.json`;
- publish `events_compact.csv` only if <= 5 MB;
- large raw CSVs remain local under `D:\MT5_Backtests\Research\D025\Backtests\<RUN_ID>\raw\`, with SHA256 and byte sizes recorded in the manifest.

The `backtest-results` branch contains `BACKTEST_RESULTS_README.md`. A fresh agent must inspect the newest D025 run there after the user launches the automation.

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

Priority sequence:

1. Run the first D025 FundedNext Core backtest with the automation above and inspect the automatically published summary; do not alter locked thresholds from the result.
2. Keep D025 Observer 1.00 running live in parallel and accumulate genuine forward M15 state transitions.
3. Compare backtest state-machine behavior with forward behavior for obvious implementation/replay artifacts before making any strategy conclusion.
4. After sufficient Core evidence, join timestamp-valid Binance/Bybit features for Crypto+ event-study comparisons.
5. Only after robustness/OOS/cost/red-team gates may anything become a Guardian trading candidate.

## 8. MT5 versioning rule

For this project, `#property version` must use a MetaEditor-compatible simple numeric version. Use **1.00, 1.01, 1.02 ...** for this D025 EA lineage rather than semantic/build strings such as `0.100`, `11.1706`, etc. Research labels such as V0/V1 may remain in filenames/descriptions but are not the MT5 `#property version`.

## 9. User-operation style

The user is not expected to infer shell commands. For local operations, provide complete copy/paste PowerShell/CMD blocks and explain only the necessary verification result.

## 10. Resume instructions for a fresh agent

Read, in this order:
1. `CURRENT_PROJECT_HANDOFF.md` (this file)
2. branch `live-status` -> `LIVE_RESEARCH_STATUS.json`
3. branch `backtest-results` -> newest `backtests/d025/<RUN_ID>/SUMMARY.md` and `summary.json` if any run exists
4. `research/campaigns/D025_LER_V0_RULES_LOCK_2026_09_04.md`
5. `research/ea/D025_LER_Observer_V0.mq5`
6. latest relevant files under `research/results/` for Shared Intelligence / Guardian v11.17.x
7. `CURRENT_QUEUE.json`
8. `docs/RESEARCH_STATUS.md`
9. `docs/STRATEGY_DECISIONS.md`

Then verify actual live/local state before launching or modifying anything. Real process/log state always overrides a stale written status.

## 11. Continuity rule

After every material milestone (new active version, user compile/deploy validation, gate pass/fail, change in architecture, new live research component, change of backtest state, or change of next safe action), update this file in the same work session. No important current state should exist only in ChatGPT/Codex conversation context.
