# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-04 17:10 Europe/Paris
Status: ACTIVE / D025 ENTRY QUALITY BRANCH-DEPENDENT / 2025 REPLICATION ANALYZED / FUNDEDNEXT LIVE AUTO SUSPENDED PENDING REQUEST-BUDGET FIX

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

Full diagnostic: `research/results/D025_ENTRY_QUALITY_DIAGNOSTIC_2026_09_04.md`.

### June-July 2026 cross-asset diagnostic

Latest-window first-touch highlights:
- BTCUSD 112 trades: +1R 50.00%, +2R 38.39%, +3R 22.32%.
- ETHUSD 102 trades: +1R 52.94%, +2R 40.20%, +3R 28.43%.
- EURUSD 55 trades: +1R 52.73%, +2R 23.64%, +3R 16.36%.
- SOLUSD 65 trades: +1R 53.85%, +2R 36.92%, +3R 26.15%.
- DOGE/LNK weak in aggregate.

Notable path splits:
- ETH RETEST: +1R 64.81%, +2R 50.00%, +3R 38.89%.
- SOL ACCEPTANCE: +1R 58.06%, +2R 45.16%, +3R 29.03%.

Full report: `research/results/D025_CROSS_ASSET_FIRST_TOUCH_DIAGNOSTIC_2026_09_04.md`.

## 6. 2024 full-year replication

User supplied full-year 2024 sessions for BTC, ETH, GBPUSD, USDJPY and XAUUSD: 2,530 trades total.

Global 2024 fixed-TP behavior was weak/near-flat, but branch splits were informative:
- ETH RETEST EV2 about +0.084R while ACCEPTANCE was negative.
- GBP RETEST EV2 about +0.084R, but this path result did not persist in 2025.
- XAU RETEST EV2 about +0.158R, but this also failed replication in 2025.
- BTC SHORT showed a modest early edge.
- USDJPY global continuation was weak.

## 7. 2025 replication — NEW MATERIAL MILESTONE

New sessions isolated from appended `(7)` CSVs by comparison with prior `(6)` files, avoiding double-counting older overlapping BTC/ETH runs:
- BTCUSD 503 trades, full 2025
- ETHUSD 557 trades, full 2025
- GBPUSD 360 trades, full 2025
- USDJPY 424 trades, full 2025
- XAUUSD 399 trades, full 2025
- SOLUSD 330 trades, 2025-04-29 -> 2025-12-30 only

Total new 2025 trades: 2,573.

2025 global first-touch / resolved fixed-TP EV before costs:
- BTC: +1R 52.29%, +2R 30.82%, +3R 21.27%; EV1 +0.063R, EV2 -0.004R, EV3 -0.038R.
- ETH: +1R 51.17%, +2R 30.52%, +3R 21.54%; EV1 +0.050R, EV2 -0.004R, EV3 -0.014R.
- GBP: +1R 51.67%, +2R 29.17%, +3R 17.50%; EV1 +0.107R, EV2 +0.033R, EV3 -0.134R.
- SOL: +1R 48.79%, +2R 32.73%, +3R 24.55%; EV1 -0.006R, EV2 +0.019R, EV3 +0.042R.
- USDJPY: EV1 -0.027R, EV2 -0.055R, EV3 -0.114R.
- XAU: EV1 -0.100R, EV2 -0.220R, EV3 -0.260R.

Replication verdicts:
- **ETH RETEST is the strongest recurring D025 branch**: EV2 positive in 2024 (+0.084R), 2025 (+0.109R), and Jun-Jul 2026 (+0.588R). Pooled 2024-2026: 704 RETEST trades; resolved +2R hit probability 37.78%; EV2 +0.133R before costs.
- **BTC SHORT has a recurring early edge**: pooled 2024-2026 625 trades; EV1 +0.096R, EV2 +0.067R, EV3 negative.
- **GBP SHORT has a recurring early edge**: pooled 421 trades; EV1 +0.121R, EV2 +0.072R, EV3 ~flat/negative. GBP path leadership flips between 2024 and 2025, so do not promote ACCEPTANCE/RETEST as a GBP rule.
- **SOL SHORT is promising but less mature**: 2025 EV2 +0.196R / EV3 +0.235R; Jun-Jul 2026 also strong. No 2024 sample and 2025 starts late April.
- **USDJPY 2026 strength is not robust backward**: 2024/2025 global EV2 negative.
- **XAU RETEST 2024 failed replication**: 2025 RETEST EV2 negative; do not promote XAU path rule.

Across the five full-year common markets BTC/ETH/GBP/USDJPY/XAU, 2024+2025 gives 4,773 trades. Universal D025 is approximately flat at 1R (EV +0.011R before costs) and negative at 2R (-0.032R) / 3R (-0.106R). Therefore there is no universal fixed-TP edge across all markets; edge is branch/regime dependent.

Full report: `research/results/D025_2025_REPLICATION_DIAGNOSTIC_2026_09_04.md`, commit `e30334bf44fb1551943c151a640da4487fe1c8cd`.

## 8. Scientific separation / next D025 step

Enough data now exists to stop indiscriminate symbol collection and move to a preregistered management/branch-validation stage.

Do NOT change D025 V0 entry thresholds or structural SL. Current CSVs cannot reconstruct partial-at-1R + move-to-BE + runner exactly because they do not record a post-+1R return to entry before later targets.

Next clean EA/research step:
- add +0.5R timestamp tracking;
- add post-+1R BE-touch timing/state;
- test only a tiny preregistered exit set: full TP +1R, full TP +2R, and one fixed partial-at-1R + BE remainder + runner/trail construction;
- keep one frozen trailing rule; no broad grid optimization;
- validate the recurring branches (ETH RETEST, BTC SHORT, GBP SHORT, SOL SHORT) without changing entry thresholds.

D025 V0 signal transitions remain MT5 Core only. Binance/Bybit data collects independently. Later Crypto+ comparisons must join external data only with `available_at <= event_time`.

## 9. Research note — missed post-shock reaction

Live ETHUSD observation 2026-09-04: extreme bearish impulse followed by no obvious Guardian reaction/trade. Keep as a separate later post-shock/exhaustion/mean-reversion research hypothesis. Do not silently loosen Momentum/RSI filters.

## 10. Resume order

1. this file
2. `research/results/D025_2025_REPLICATION_DIAGNOSTIC_2026_09_04.md`
3. latest FundedNext request-budget audit / current Guardian 11.17.x source
4. `research/results/D025_ENTRY_QUALITY_DIAGNOSTIC_2026_09_04.md`
5. `research/results/D025_CROSS_ASSET_FIRST_TOUCH_DIAGNOSTIC_2026_09_04.md`
6. branch `live-status` -> `LIVE_RESEARCH_STATUS.json`
7. `docs/STRATEGY_DECISIONS.md`
8. `research/ea/D025_LER_Trading_1_01.mq5`
9. locked D025 V0 rules
10. current observer source

## 11. Continuity rule

After every material milestone, update this handoff in the same work session. No important current state should exist only in conversation context.
