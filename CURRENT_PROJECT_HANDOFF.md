# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-04 13:00 Europe/Paris
Status: ACTIVE / LIVE RESEARCH RUNNING

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

A compact live-state mirror is now installed and validated.

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

## 5. Scientific separation

D025 V0 currently uses **MT5 Core only** for signal-state transitions. Binance/Bybit continues collecting independently but does not trigger D025 V0.

Reason: preserve attribution and later compare, without lookahead:
- Core
- Core + OI
- Core + liquidations
- Core + spot/perp dislocation
- preregistered multi-venue combination

External observations may only be joined if `available_at <= event_time`.

Do not inject Shared Intelligence directly into live RSI or Momentum merely because the fields are available.

## 6. Next safe actions

Priority sequence:

1. Let D025 Observer 1.00 run continuously and accumulate genuine M15 state transitions.
2. Verify that SWEEP sequences correctly fail or progress to CASCADE/EXHAUSTION/RECLAIM/VALID_SIGNAL; do not alter locked thresholds based on early outcomes.
3. Build the automated D025 analysis layer that reads the three CSVs and produces counts, funnel conversion, MFE/MAE, R-hit timing, failure reasons, ambiguity counts and per-symbol/per-level breakdowns.
4. Only after sufficient Core observations, join timestamp-valid Binance/Bybit features for Crypto+ event-study comparisons.
5. Only after robustness/OOS/cost/red-team gates may anything become a Guardian trading candidate.

## 7. MT5 versioning rule

For this project, `#property version` must use a MetaEditor-compatible simple numeric version. Use **1.00, 1.01, 1.02 ...** for this D025 EA lineage rather than semantic/build strings such as `0.100`, `11.1706`, etc. Research labels such as V0/V1 may remain in filenames/descriptions but are not the MT5 `#property version`.

## 8. User-operation style

The user is not expected to infer shell commands. For local operations, provide complete copy/paste PowerShell/CMD blocks and explain only the necessary verification result.

## 9. Resume instructions for a fresh agent

Read, in this order:
1. `CURRENT_PROJECT_HANDOFF.md` (this file)
2. branch `live-status` -> `LIVE_RESEARCH_STATUS.json`
3. `research/campaigns/D025_LER_V0_RULES_LOCK_2026_09_04.md`
4. `research/ea/D025_LER_Observer_V0.mq5`
5. latest relevant files under `research/results/` for Shared Intelligence / Guardian v11.17.x
6. `CURRENT_QUEUE.json`
7. `docs/RESEARCH_STATUS.md`
8. `docs/STRATEGY_DECISIONS.md`

Then verify actual live/local state before launching or modifying anything. Real process/log state always overrides a stale written status.

## 10. Continuity rule

After every material milestone (new active version, user compile/deploy validation, gate pass/fail, change in architecture, new live research component, or change of next safe action), update this file in the same work session. No important current state should exist only in ChatGPT/Codex conversation context.
