# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-04 15:55 Europe/Paris
Status: ACTIVE / D025 LIVE OBSERVER RUNNING / D025 ENTRY QUALITY MIXED-NOT-REJECTED / FUNDEDNEXT LIVE AUTO SUSPENDED PENDING REQUEST-BUDGET FIX

This is the canonical fast-resume file for a fresh ChatGPT/Codex instance. Read it first, then verify actual live/local state before changing anything.

## 1. Live Guardian / Shared Intelligence

- Guardian 17 lineage = v11.17.x multi-venue Shared Intelligence observer.
- Shared Intelligence is read-only and has NO trading effect.
- Architecture: Bybit + Binance collectors -> venue-separated state -> FILE_COMMON bridge -> Guardian/research consumers.
- Windows autostart task: `Guardian Shared Intelligence MultiVenue V1`.
- Live-status mirror: branch `live-status`, file `LIVE_RESEARCH_STATUS.json`.

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
- executable: `D:\MT5_FundedNext\terminal64.exe`
- MT5 data path: `C:\Users\armor\AppData\Roaming\MetaQuotes\Terminal\D943DED8A972BBD3A21ED90520AE6479`

FundedNext automation V1/V2/V3/V4 remains SUSPENDED. Never ask the user to retry those wrappers or debug unverified shell commands. Prefer normal manual MT5 workflow.

## 4. FundedNext server-request anomaly — HIGH PRIORITY

Live user observation 2026-09-04:
- FundedNext HUD reached about `5629/2000 (281.4%) | HARD LIMIT | PROTECTION ONLY`.
- FTMO live Guardian had been running since morning and showed only `32/2000 (1.6%) | NORMAL`.
- Therefore thousands of requests are not normal Guardian baseline behavior and are specific to the FundedNext account/runtime episode.

Static audit of current Guardian request-budget code:
- counter is account/day scoped via MT5 Global Variables;
- it counts Guardian-side CTrade attempts plus deduplicated observed Magic-0 manual entries; it is NOT the prop firm's proprietary server counter;
- attempts are reserved/incremented before send, so broker-rejected attempts still increase Guardian's counter;
- `SRP_EMERGENCY` and `SRP_PROTECTION` are intentionally allowed beyond the 2000 hard budget;
- this makes repeated protection retries capable of driving the counter far above 2000;
- strongest identified structural suspect: `RSI_BE_RETRY` is evaluated tick-by-tick while BE remains unapplied, and uses `SRP_PROTECTION`; `RSIApplyCommonStop` can issue one PositionModify per RSI leg per retry.

Important: this proves a mechanism capable of runaway counting/requests, but does NOT prove all 5629 were actually received by FundedNext nor that every excess request came from RSI_BE_RETRY.

Operational state:
- FundedNext live Algo Trading should stay OFF until retry/backoff/dedup patch is made and validated.
- Shared Intelligence collector can stay ON; it is unrelated/read-only.
- Do NOT reset the live request counter merely to clear the HUD.
- Needed patch: bounded retry cadence/backoff for non-emergency protection operations, especially RSI_BE_RETRY; emergency close must remain able to pass.

## 5. D025 Trading 1.01 — manual Strategy Tester EA

Source:
- `research/ea/D025_LER_Trading_1_01.mq5`
- MT5 version `1.01`.
- one symbol per run via `_Symbol`.
- locked V0 signal chain, market entry on VALID_SIGNAL, structural SL, no TP, 48h forced exit, default 0.50% equity risk.

### Long pre-OOS-style run supplied by user

FundedNext, M1, 2025-01-01 -> 2026-06-28, initial deposit 10,000 USD:
- BTCUSD: final balance 6,695.65 USD, net -3,304.35 USD.
- ETHUSD: net -4,547.95 USD; PF 0.31; equity DD max 45.85%; 169 trades; 20 winners / 149 losers; win rate 11.83%; Sharpe -5.00.

Correct interpretation: reject only `structural SL + no TP + forced exit at 48h`; do NOT reject D025 entries.

### Entry-quality diagnostic from long-run CSVs

399 opened trades total: 230 BTCUSD, 169 ETHUSD. Count a +R hit only when its first timestamp is before `stop_utc`.

- BTCUSD: +1R 102/230 = 44.35%; +2R 56/230 = 24.35%; +3R 30/230 = 13.04%; +4R 16/230 = 6.96%; +5R 10/230 = 4.35%.
- ETHUSD: +1R 60/169 = 35.50%; +2R 33/169 = 19.53%; +3R 23/169 = 13.61%; +4R 14/169 = 8.28%; +5R 10/169 = 5.92%.

Path split long run:
- BTC ACCEPTANCE: +1R 54.69%, +2R 32.81%, +3R 17.19%.
- BTC RETEST: +1R 31.37%, +2R 13.73%, +3R 7.84%.
- ETH ACCEPTANCE: +1R 28.74%, +2R 17.24%, +3R 11.49%.
- ETH RETEST: +1R 42.68%, +2R 21.95%, +3R 15.85%.

Raw 48h MFE/MAE is contaminated after SL because the EA continues observation; first-touch timestamps are the valid metric.

Full diagnostic: `research/results/D025_ENTRY_QUALITY_DIAGNOSTIC_2026_09_04.md` commit `8037b357e4c57619df828855bfe0736304238e94`.

### Same-period June-July 2026 cross-check (FTMO tester)

User ran D025 Trading 1.01 on the same roughly 2026-06-01 -> 2026-07-30 window for BTC and ETH, initial deposit 100,000 USD.

BTCUSD:
- MT5 report: net +3,473.31 USD; PF 1.08; equity DD max 13.40%; 112 trades.
- First-touch before SL: +1R 56/112 = 50.00%; +2R 43/112 = 38.39%; +3R 25/112 = 22.32%; +4R 18/112 = 16.07%; +5R 15/112 = 13.39%.
- ACCEPTANCE vs RETEST nearly identical at +1R (50% each); +2R 39.66% vs 37.04%; +3R 22.41% vs 22.22%.

ETHUSD:
- MT5 report screenshot: net +452.25 USD; PF 1.01; equity DD max 16.39%; 102 trades; 23 profit trades / 79 loss trades.
- First-touch before SL: +1R 54/102 = 52.94%; +2R 41/102 = 40.20%; +3R 29/102 = 28.43%; +4R 17/102 = 16.67%; +5R 12/102 = 11.76%.
- ACCEPTANCE (48): +1R 39.58%; +2R 29.17%; +3R 16.67%.
- RETEST (54): +1R 64.81%; +2R 50.00%; +3R 38.89%.

Interpretation:
- this second window strengthens the case that D025 entries contain useful information even though the arbitrary 48h/no-TP management can obscure it;
- ETH RETEST again outperforms ETH ACCEPTANCE directionally, consistent with the earlier long-run split, but do NOT tune entry thresholds/path rules from this observation yet;
- the run extends past the previous 2026-06-28 pre-OOS cutoff, so July must not be treated as untouched OOS for later D025 tuning.
- highest-value missing measurement remains +0.5R first-touch.

## 6. Scientific separation / next D025 step

D025 V0 signal transitions use MT5 Core only. Binance/Bybit data collects independently. Later Crypto+ comparisons must join external data only with `available_at <= event_time`.

Do not inject Shared Intelligence directly into live RSI/Momentum merely because fields are available.

Next clean D025 experiment:
- add +0.5R timestamp tracking;
- keep entry thresholds frozen;
- test only a tiny preregistered exit set (e.g. full TP 0.5R, full TP 1R, one partial-at-1R + runner);
- no broad optimization grid.

## 7. Research note — missed post-shock reaction

Live ETHUSD observation 2026-09-04: extreme bearish impulse followed by no obvious Guardian reaction/trade. Keep as a separate later post-shock/exhaustion/mean-reversion research hypothesis. Do not silently loosen Momentum/RSI filters.

## 8. Resume order

1. this file
2. latest FundedNext request-budget audit / current Guardian 11.17.x source
3. `research/results/D025_ENTRY_QUALITY_DIAGNOSTIC_2026_09_04.md`
4. branch `live-status` -> `LIVE_RESEARCH_STATUS.json`
5. `docs/STRATEGY_DECISIONS.md`
6. `research/ea/D025_LER_Trading_1_01.mq5`
7. locked D025 V0 rules
8. current observer source
9. latest Shared Intelligence result files
10. `CURRENT_QUEUE.json`

## 9. Continuity rule

After every material milestone, update this handoff in the same work session. No important current state should exist only in conversation context.
