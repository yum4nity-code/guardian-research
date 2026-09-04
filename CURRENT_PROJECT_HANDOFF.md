# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-04 13:56 Europe/Paris
Status: ACTIVE / D025 LIVE OBSERVER RUNNING / FUNDEDNEXT BACKTEST V4 STABLE

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
- V2 generic file/log discovery failed on Server 2; not used directly for this target.
- V3 correctly binds to the exact live window and data path, then builds the portable clone. It compiled the D025 harness with `0 errors, 0 warnings` and launched the isolated tester.
- Portable logs confirmed `account_seen=True` but did not expose a usable server label (`server_seen=False`).
- V4 initially tried to self-patch V3 and failed after V3 changed (`V2 portable target verification block changed`). This brittle self-patching layer has now been removed.

## 4. Current FundedNext launcher: V4 stable

Use only:
- `automation/run_d025_fundednext_backtest_v4.ps1`
- `automation/RUN_D025_FUNDEDNEXT_BACKTEST_V4.cmd`

Current implementation:
- V4 is now a thin stable delegate to V3; it no longer edits V3 or V2 source text itself.
- V3 first MUST bind the source to the exact running live window whose title contains BOTH account `14202634` and server `FundedNext-Server 2`.
- V3 maps that exact process to the MT5 data folder via `origin.txt`.
- The portable clone is created from that verified source.
- Portable verification now requires exact account `14202634`; `serverSeen` remains telemetry only because FundedNext portable logs may omit the server label.
- Server identity is supplied by the earlier exact live-window provenance check, which already required both account and server.
- Live terminal / Guardian are not closed or commandeered.
- `AllowLiveTrading=0`; D025 itself has no order functions.

Default test:
- BTCUSD + ETHUSD
- host BTCUSD M1
- `2025.01.01 -> 2026.06.28`
- Model=4 real ticks
- no optimization / no threshold search

Expected success line:
`CONFIRMED TARGET: 14202634 / FundedNext-Server 2 (verified live-window provenance + portable account)`

Then the script waits for `COMPLETE.txt`, analyzes results, and publishes compact outputs to branch `backtest-results` under `backtests/d025/<RUN_ID>/`. Large raw CSVs stay local with hashes in the manifest.

## 5. Scientific separation

D025 V0 signal transitions use MT5 Core only. Binance/Bybit data continues collecting independently but does not trigger V0. Later Crypto+ comparisons must join external data only with `available_at <= event_time`.

Do not inject Shared Intelligence directly into live RSI or Momentum merely because the fields are available.

## 6. Next action

1. Keep the correct live FundedNext MT5 window open.
2. `git pull`.
3. Run `automation/run_d025_fundednext_backtest_v4.ps1`.
4. Trust the run after the V4/V3 confirmation line above.
5. Completion requires `COMPLETE.txt` -> analyzer -> GitHub publish.
6. Keep D025 Observer 1.00 running live in parallel.

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
