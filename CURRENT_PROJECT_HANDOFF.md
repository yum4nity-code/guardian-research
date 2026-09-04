# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-04 13:58 Europe/Paris
Status: ACTIVE / D025 LIVE OBSERVER RUNNING / FUNDEDNEXT AUTOMATION SUSPENDED

This is the canonical fast-resume file for a fresh ChatGPT/Codex instance. Read it first, then verify actual live/local state before changing anything.

## 1. Live Guardian / Shared Intelligence

- Guardian 17 lineage = v11.17.x multi-venue Shared Intelligence observer.
- Shared Intelligence is read-only and has NO trading effect.
- Architecture: Bybit + Binance collectors -> venue-separated state -> FILE_COMMON bridge -> Guardian/research consumers.
- Windows autostart task: `Guardian Shared Intelligence MultiVenue V1`.
- Live-status mirror: branch `live-status`, file `LIVE_RESEARCH_STATUS.json`, ~15 min heartbeat plus significant-event refresh.

## 2. D025 LER observer

- Source: `research/ea/D025_LER_Observer_V0.mq5`.
- MT5 version: `1.00`; research generation: V0.
- No trading library / no order function.
- BTCUSD + ETHUSD from one EA instance.
- State machine: `IDLE -> LEVEL_WATCH -> SWEEP -> CASCADE -> EXHAUSTION -> RECLAIM -> RETEST/ACCEPTANCE -> VALID_SIGNAL`.
- VALID_SIGNAL creates only a virtual trade; M1 then tracks MFE/MAE, +1R..+5R, virtual SL, horizons to 48h.
- Locked rules: `research/campaigns/D025_LER_V0_RULES_LOCK_2026_09_04.md`; do not tune V0 thresholds post hoc.

## 3. Exact FundedNext target

User-confirmed live MT5 target:
- account: `14202634`
- server: `FundedNext-Server 2`
- mode: Hedge
- company: FundedNext Ltd

Resolved from the actual live window/process:
- executable: `D:\MT5_FundedNext\terminal64.exe`
- MT5 data path: `C:\Users\armor\AppData\Roaming\MetaQuotes\Terminal\D943DED8A972BBD3A21ED90520AE6479`

Launcher history:
- V1 chose another FundedNext installation; superseded.
- V2 generic file/log discovery failed on Server 2.
- V3 correctly bound the exact live window/data path and compiled the harness with `0 errors, 0 warnings`, but portable verification remained unreliable because server text was absent from portable logs.
- V4 introduced another delegation/self-patching failure and still did not produce a user-verified running backtest.

## 4. FundedNext automation status: SUSPENDED

Do NOT ask the user to run V1/V2/V3/V4 again.

The user can launch MT5 backtests manually and originally wanted automation only to save time. The automation attempt instead cost time, so it is suspended until it can be validated independently before any new command is given to the user.

Operational rule for future agents:
- Never give the user a local PowerShell/CMD command for this project merely because the code looks plausible.
- Do not ask the user to serve as the debugger for unverified launcher iterations.
- If a new automation is proposed, first reduce it to a simple architecture, inspect the exact current files, perform every validation available from the assistant side, and clearly state any part that cannot be independently verified on the user's Windows/MT5 environment.
- If end-to-end validation on the real environment is not possible, prefer manual MT5 steps that the user already knows over presenting an unverified command as ready.
- The user may manually run D025 backtests; assistant should focus on preparing the correct EA/configuration and analyzing results rather than repeatedly relaunching fragile wrappers.

Do not claim that any V1-V4 FundedNext run completed successfully. No trusted `COMPLETE.txt` / published D025 backtest result has yet been verified from these launcher attempts.

## 5. Scientific separation

D025 V0 signal transitions use MT5 Core only. Binance/Bybit data continues collecting independently but does not trigger V0. Later Crypto+ comparisons must join external data only with `available_at <= event_time`.

Do not inject Shared Intelligence directly into live RSI or Momentum merely because the fields are available.

## 6. Next safe action

- Leave D025 Observer 1.00 running live.
- For historical D025 testing, use the user's normal manual MT5 Strategy Tester workflow unless/until a launcher has been independently validated.
- When the user provides tester outputs/CSV results, analyze them and publish clean research conclusions/results to GitHub.
- Do not alter locked V0 thresholds based on the first results.

## 7. Resume order for a fresh agent

1. this file
2. branch `live-status` -> `LIVE_RESEARCH_STATUS.json`
3. branch `backtest-results` -> newest D025 result if present
4. locked D025 V0 rules
5. current D025 EA source
6. latest relevant Shared Intelligence / Guardian result files
7. `CURRENT_QUEUE.json`
8. `docs/RESEARCH_STATUS.md`
9. `docs/STRATEGY_DECISIONS.md`

## 8. Continuity rule

After every material milestone, update this handoff in the same work session. No important current state should exist only in conversation context.
