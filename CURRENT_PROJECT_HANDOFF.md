# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-04 14:44 Europe/Paris
Status: ACTIVE / D025 LIVE OBSERVER RUNNING / D025 TRADING 1.01 EXIT CONSTRUCTION FAILED / D025 ENTRY QUALITY UNRESOLVED / FUNDEDNEXT AUTOMATION SUSPENDED

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

Source:
- `research/ea/D025_LER_Trading_1_01.mq5`
- MT5 version `1.01`.
- one symbol per run via `_Symbol`.
- locked V0 signal chain, market entry on VALID_SIGNAL, structural SL, no TP, 48h forced exit, default 0.50% equity risk.
- technically capable of live trading if attached to a chart; user explicitly does not want an artificial live block.

Manual backtest results supplied by user, FundedNext, M1, 2025-01-01 -> 2026-06-28, initial deposit 10,000 USD:
- BTCUSD: final balance 6,695.65 USD, net -3,304.35 USD. Detailed PF/DD/win-rate not captured.
- ETHUSD: net -4,547.95 USD; PF 0.31; expected payoff -26.91; equity DD max 45.85% / 4,616.03 USD; 169 trades; 20 winners / 149 losers; win rate 11.83%; gross profit 2,001.43 vs gross loss -6,549.38; average win 100.07 vs average loss -42.81; Sharpe -5.00.

Correct interpretation:
- these runs prove that the specific tradable construction `structural SL + no TP + forced exit at 48h` is bad;
- they do NOT establish that D025 entries are bad, because the exit rule was deliberately crude and can dominate realized P&L;
- do not throw away the entry hypothesis on the basis of these account-level results;
- entry quality must be evaluated independently with event-study metrics: MFE/MAE after entry, probability of reaching +0.5R/+1R/+2R/+3R before SL, time-to-MFE, excursion by horizon, and path/level-family splits;
- only after that entry-quality study can D025 signal quality be accepted/rejected;
- no threshold retuning is justified before this separation is done.

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

- Leave D025 Observer 1.00 running live if continued event collection is desired.
- Do not repeat the same D025 Trading 1.01 account-level backtest unchanged; it already tells us the 48h/no-TP construction loses heavily.
- Next D025 task is specifically entry-quality analysis, independent of the 48h exit: MFE/MAE, first-R thresholds before SL, time-to-hit, failure funnel, and level/path contribution.
- If the entries show edge, then formulate and preregister an exit/management hypothesis separately rather than concluding from the arbitrary 48h close.
- Keep the separate post-shock/exhaustion idea as its own hypothesis rather than morphing D025 thresholds.

## 9. Resume order for a fresh agent

1. this file
2. branch `live-status` -> `LIVE_RESEARCH_STATUS.json`
3. `docs/STRATEGY_DECISIONS.md`
4. branch `backtest-results` -> newest D025 result if present
5. `research/ea/D025_LER_Trading_1_01.mq5`
6. locked D025 V0 rules
7. current observer source
8. latest relevant Shared Intelligence / Guardian result files
9. `CURRENT_QUEUE.json`
10. `docs/RESEARCH_STATUS.md`

## 10. Continuity rule

After every material milestone, update this handoff in the same work session. No important current state should exist only in conversation context.
