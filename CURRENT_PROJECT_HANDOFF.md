# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 06:30 Europe/Paris
Status: ACTIVE / D026 V0 REJECTED / D017 MOMENTUM LONG-HISTORY BROAD ENGINE FAILS LARGE-EDGE STANDARD / BTC SELL MOMENTUM WATCHLIST ONLY / RSI LEGACY LONG-HISTORY RUN IN PROGRESS / FUNDEDNEXT LIVE AUTO OFF PENDING REQUEST-BUDGET FIX

This is the canonical fast-resume file. A fresh ChatGPT/Codex instance must read this first. Historical chronology/time ledger: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.

## 0. USER DIRECTIVE / RESEARCH STANDARD

- Continue autonomously when possible; interrupt only for genuinely necessary manual MT5 actions.
- Manual MT5 Strategy Tester is preferred; do not ask the user to debug shell wrappers.
- No curve fitting / no post-hoc threshold edits disguised as fixes.
- User does not want crumbs: prefer recurring pre-cost edge around >= +0.15R/trade, ideally +0.20R+, before cost/stress work.
- If an engine fails long-history validation, reject it rather than preserving it because of attractive short-window screenshots.

---

# 1. D026 PRICE EXHAUSTION RECLAIM — REJECTED

Rules were locked before results. Initial V0 1.00 had implementation conformance defects; standalone corrected 1.02 was run on BTC+ETH and produced the same first-touch population for those histories.

Final corrected report:
- `research/results/D026_V0_CORRECTED_FINAL_DIAGNOSTIC_2026_09_04.md`
- commit `e664026b1cda9317ba632cff13613fec87d22683`

Corrected BTC+ETH combined:
- +1R ~ +0.001R
- +2R ~ -0.086R
- +3R ~ -0.156R
- predeclared 40%@1R + BE runner also negative/near-zero

Decision: **D026 V0 FAILS large-edge standard. Do not retune.**

---

# 2. D017 MOMENTUM LONG-HISTORY VALIDATION — FIRST VERDICT COMPLETE

Motivation: short-window BTC Momentum-only baseline on 2026-09-02 was spectacular (+$7,353, PF 1.68, DD 1.80%, 115 trades). User requested a lightweight virtual observer over 2024-2025 to determine whether this was a durable signal edge or a favorable regime/Guardian-selection effect.

Rules lock:
- `research/campaigns/D017_MOMENTUM_LONG_HISTORY_DIAGNOSTIC_LOCK_2026_09_04.md`

Diagnostic EA:
- `research/ea/D017_Momentum_VirtualDiagnostic_1_01_STATIC_CONFORMANCE.mq5`
- pure virtual; no CTrade/orders/account/margin/tick-volume dependency
- BTC/ETH signal core copied from D017 v11.16 production

Full result report:
- `research/results/D017_MOMENTUM_LONG_HISTORY_FIRST_VERDICT_2026_09_05.md`
- commit `97d17b7f0a925571d66efd13f8d79f500a02f866`

Received CSVs contain duplicate runs. Use one canonical session per symbol:
- BTCUSD n=1,710 = 991 (2024) + 719 (2025)
- ETHUSD n=1,144 = 727 (2024) + 417 (2025)
- duplicate BTC sessions are content-identical; duplicate ETH sessions yield identical first-touch metrics (five late-2025 signal timestamps differ by seconds only)

Broad fixed first-touch EV:
- BTC: EV1 -0.015R / EV1.25 -0.001R / EV1.5 +0.013R / EV2 +0.029R / EV2.5 +0.063R / EV3 +0.074R
- ETH: EV1 -0.008R / EV1.25 -0.006R / EV1.5 +0.004R / EV2 -0.018R / EV2.5 -0.033R / EV3 -0.031R
- BTC+ETH combined: EV1 -0.012R / EV2 +0.011R / EV2.5 +0.025R / EV3 +0.032R

Year stability:
- BTC 2024 improves toward larger targets (EV3 +0.118R) but 2025 collapses to near zero (EV3 +0.014R)
- ETH 2024 near flat/slightly positive; 2025 clearly negative (EV3 -0.167R)

Predeclared BUY/SELL split:
- **BTC SELL is the only recurring clue**
  - 2024 n=359: EV2 +0.111R / EV2.5 +0.150R / EV3 +0.170R
  - 2025 n=402: EV2 +0.053R / EV2.5 +0.114R / EV3 +0.085R
  - pooled n=761: EV2 +0.080R / EV2.5 +0.131R / EV3 +0.125R
  - Wilson-style pooled EV interval: +2.5R about +0.018..+0.251R; +3R about +0.002..+0.258R
- BTC BUY not attractive; 2025 clearly negative
- ETH has no recurring useful side branch

Predeclared BE diagnostics:
- BTC overall BE@1.25 -> 3R ~ +0.054R
- ETH overall BE@1.25 -> 3R ~ -0.043R
- BTC SELL pooled BE@1 -> 3R ~ +0.135R; BE@1.25 -> 3R ~ +0.123R
- descriptive 25%@2R / BE1.25 / runner3 BTC SELL: ~+0.109R, almost identical year-by-year (~+0.112R 2024, +0.106R 2025)

Decision:
- **Broad D017 Momentum FAILS large-edge standard on BTC/ETH.**
- Do NOT keep broad engine merely because short-window P/L was exceptional.
- **BTC SELL Momentum remains WATCHLIST/HYPOTHESIS ONLY** because it repeats positive across both years, but pooled ~+0.13R is below user threshold and before full costs.
- No threshold retuning. If ever followed up, use a prospectively locked BTC SELL-only or exact-native-manager test, not a threshold sweep.

---

# 3. RSI SNIPER LEGACY v11.16.11 LONG-HISTORY — RUNNING NOW

Purpose: validate the RSI lineage associated with the same spectacular 2026-09-02 BTC isolation baseline (RSI-only +$9,451, PF 1.19, 621 trades) over 2024-2025.

Rules lock:
- `research/campaigns/RSI_SNIPER_11_16_11_LONG_HISTORY_DIAGNOSTIC_LOCK_2026_09_04.md`

Campaign protocol / audit:
- `research/campaigns/D017_RSI_LONG_HISTORY_CAMPAIGN_PROTOCOL_2026_09_04.md`
- `research/results/D017_RSI_LONG_HISTORY_STATIC_AUDIT_2026_09_04.md`

Original diagnostic 1.01 had a file-output flaw: folders/files were only opened when logging an event and FileOpen failure was silent. User ran BTC+ETH but no RSI CSV files existed anywhere (confirmed by recursive PowerShell search).

Corrected user-facing build:
- `RSI_Sniper_EntryPathDiagnostic_v11_16_11_1_02_FILEBOOTSTRAP.mq5`
- creates `FILE_COMMON\GuardianResearch\RSILegacy111611\` and all 3 CSV headers immediately at OnInit
- logs exact physical path / fails loudly if bootstrap cannot create files

User has launched the corrected RSI runs. Wait for cumulative trio:
- `rsi_111611_virtual_events.csv`
- `rsi_111611_virtual_trades.csv`
- `rsi_111611_virtual_outcomes.csv`

First analysis must remain predeclared only:
- integrity/counts
- 2024 vs 2025
- BUY1 vs BUY2
- fixed +0.5/+1/+1.25/+1.5/+2/+2.5/+3R
- BE@1 -> 2/3R
- BE@1.25 -> 2/3R
- RSI50/70 before structural stop
- exclude same-M1 ambiguities
- no threshold optimizer

If legacy RSI survives strongly, next experiment is a separate current v11.17 diagnostic because live recross/cost-aware/SL semantics changed materially. Do not assume legacy survival validates current RSI.

---

# 4. D025 STATUS

D025 XAU/Forex final exploitation is complete:
- report `research/results/D025_XAU_FOREX_FINAL_EXPLOITATION_2026_09_04.md`
- XAU broad reject; USDJPY broad reject
- EURUSD SHORT -> +2R and GBPUSD SHORT -> +1R remain only prospective watchlist clues; neither meets large-edge standard

D025 crypto volume-dependent historical results remain QUARANTINED because FundedNext historical M15 tick-volume provenance is inconsistent. Do not lower the frozen 1.25 relative-volume threshold to compensate.

---

# 5. SHARED INTELLIGENCE

Binance + Bybit Shared Intelligence remains READ-ONLY and has no current trading effect. Keep collector running. Future Crypto+ studies must use strict `available_at <= event_time` joins.

---

# 6. FUNDEDNEXT LIVE GUARDIAN REQUEST BUG — HIGH PRIORITY OPERATIONS ISSUE

FundedNext HUD observed ~5629/2000 requests vs FTMO ~32/2000.

Exact live lineage source in Library:
`Guardian_D017_PropFirmAuto_v11_17_04_MANUAL_PROTECTION_HOTFIX_PLAN80_RUNNER20.mq5`

Known runaway-capable mechanism:
- RSI TP1 completes but BE NET can fail
- pending BE is retried every management tick
- retry uses unlimited `SRP_PROTECTION`
- request counter increments before send

FundedNext Algo Trading remains OFF until bounded/deduplicated/backoff fix is implemented and audited. Do not claim v11.17.07 exists yet.

Manual SL behavior correction: Guardian makes ONE initial SL placement attempt; if it fails, user manually places SL. Do not claim auto-close.

Quick Strike remains separate: profitable Guardian-managed <30s exits must be logged/understood, but never weaken safety merely to exceed 30s.

---

# 7. IMMEDIATE NEXT STEP

Wait for corrected RSI BTC+ETH cumulative CSV trio, analyze it immediately using the frozen protocol, then decide:
- if RSI strong and recurring -> current-RSI follow-up;
- if RSI weak -> reject legacy RSI and return to genuinely new strategy families;
- compare final RSI result against D017 broad failure and BTC SELL-only watchlist clue.

## Continuity rule

After every material milestone, update this handoff in the same work session. Important state must never exist only in conversation context.