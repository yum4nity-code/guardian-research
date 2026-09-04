# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-04 14:18 Europe/Paris
Status: ACTIVE / D025 LIVE OBSERVER RUNNING / D025 TRADING 1.01 CREATED / FUNDEDNEXT AUTOMATION SUSPENDED

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
- If end-to-end validation on the real environment is not possible, prefer the user's normal manual MT5 workflow.

## 5. D025 Trading 1.01 — manual Strategy Tester EA

Created on main:
- `research/ea/D025_LER_Trading_1_01.mq5`
- MT5 version `1.01`.

Purpose:
- produce normal MT5 trades/equity/PF/DD in the user's manual Strategy Tester runs;
- one symbol per run, selected directly in Strategy Tester via `_Symbol` (e.g. BTCUSD run, then ETHUSD run);
- no hidden second symbol and no multi-symbol ambiguity in the report.

Trading logic:
- preserves the current D025 V0 state-machine thresholds and sequence;
- market entry only on `VALID_SIGNAL` after RETEST or ACCEPTANCE;
- structural SL = worst sweep extreme +/- `0.10 * H1 ATR`, same structural rule as V0;
- no TP;
- forced close after `InpMaxHoldHours`, default 48h;
- risk sizing by account equity and actual stop distance, default `InpRiskPercent=0.50`;
- default magic `25090401`;
- keeps dedicated D025 trading CSV logs for events, trades and MFE/MAE/+1R..+5R outcomes.

Important: this EA is technically capable of trading if attached to a live chart. The user explicitly does not want artificial live-trading blocks; operational separation is simply to use it in Strategy Tester and not attach it live.

Validation status:
- source has been created and committed on GitHub;
- it has NOT yet been compiled in the user's MetaEditor environment, so do not claim compile success until the user reports it.

## 6. Research note — missed post-shock reaction

User observation from live ETHUSD M1 on 2026-09-04: after a very large bearish impulse, Guardian showed no obvious post-move reaction/trade. The screenshot also showed regime/pre-shock diagnostics and an extension block, so this may be an intentional consequence of current filters rather than a bug.

Keep as a later research question, not an immediate live-rule change:
- study whether a distinct post-shock / exhaustion / mean-reversion setup should activate after extreme one-way crypto moves;
- quantify the move first (ATR extension, velocity, volume/tick-volume shock, liquidation/OI/funding context where available), then measure forward returns and adverse excursion;
- compare this candidate separately against D025 rather than silently loosening Momentum/RSI/Guardian filters;
- no implementation until backtested and independently validated.

## 7. Scientific separation

D025 V0 signal transitions use MT5 Core only. Binance/Bybit data continues collecting independently but does not trigger V0. Later Crypto+ comparisons must join external data only with `available_at <= event_time`.

Do not inject Shared Intelligence directly into live RSI or Momentum merely because the fields are available.

## 8. Next safe action

- Leave D025 Observer 1.00 running live.
- For historical D025 testing, use `D025_LER_Trading_1_01.mq5` through the user's normal manual MT5 workflow.
- Run BTCUSD and ETHUSD separately first; analyze each independently before any combined portfolio interpretation.
- When the user provides compile output or tester output, inspect it directly and fix only concrete errors.
- Do not alter locked V0 thresholds based on first results.

## 9. Resume order for a fresh agent

1. this file
2. branch `live-status` -> `LIVE_RESEARCH_STATUS.json`
3. branch `backtest-results` -> newest D025 result if present
4. `research/ea/D025_LER_Trading_1_01.mq5`
5. locked D025 V0 rules
6. current observer source
7. latest relevant Shared Intelligence / Guardian result files
8. `CURRENT_QUEUE.json`
9. `docs/RESEARCH_STATUS.md`
10. `docs/STRATEGY_DECISIONS.md`

## 10. Continuity rule

After every material milestone, update this handoff in the same work session. No important current state should exist only in conversation context.
