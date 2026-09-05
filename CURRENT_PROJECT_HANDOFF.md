# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / D026 REJECTED / D017 MOMENTUM BTC+ETH BROAD FAILS LARGE-EDGE STANDARD / BTC SELL WATCHLIST / MOMENTUM XAU+FOREX EXPANSION RUNNING / LEGACY RSI ENTRY-PATH FAILS / FUNDEDNEXT LIVE AUTO OFF PENDING REQUEST-BUDGET FIX

This is the canonical fast-resume file. Read this first. Historical chronology/time ledger: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.

## 0. USER DIRECTIVE / RESEARCH STANDARD

- Continue autonomously when possible; interrupt only for genuinely necessary manual MT5 actions.
- Manual MT5 Strategy Tester is preferred; do not ask the user to debug shell wrappers.
- No curve fitting / no post-hoc threshold edits disguised as fixes.
- User does not want crumbs: prefer recurring pre-cost edge around >= +0.15R/trade, ideally +0.20R+, before cost/stress work.
- Distinguish raw signal, native strategy filters/management, and Guardian operational selection. Guardian can materially improve or worsen a population but must not be assumed to rescue a zero/negative raw edge.

---

# 1. D026 PRICE EXHAUSTION RECLAIM — REJECTED

Final corrected report:
- `research/results/D026_V0_CORRECTED_FINAL_DIAGNOSTIC_2026_09_04.md`
- commit `e664026b1cda9317ba632cff13613fec87d22683`

Corrected BTC+ETH combined:
- +1R ~ +0.001R
- +2R ~ -0.086R
- +3R ~ -0.156R

Decision: **FAIL / do not retune.**

---

# 2. D017 MOMENTUM LONG-HISTORY

## BTC + ETH first verdict

Rules lock:
- `research/campaigns/D017_MOMENTUM_LONG_HISTORY_DIAGNOSTIC_LOCK_2026_09_04.md`

Diagnostic EA:
- `research/ea/D017_Momentum_VirtualDiagnostic_1_01_STATIC_CONFORMANCE.mq5`
- pure virtual; no CTrade/orders/account/margin/tick-volume dependency

Report:
- `research/results/D017_MOMENTUM_LONG_HISTORY_FIRST_VERDICT_2026_09_05.md`
- commit `97d17b7f0a925571d66efd13f8d79f500a02f866`

Canonical unique populations:
- BTCUSD n=1,710 = 991 (2024) + 719 (2025)
- ETHUSD n=1,144 = 727 (2024) + 417 (2025)

Broad fixed first-touch EV:
- BTC: EV1 -0.015R / EV2 +0.029R / EV2.5 +0.063R / EV3 +0.074R
- ETH: EV1 -0.008R / EV2 -0.018R / EV2.5 -0.033R / EV3 -0.031R
- combined: EV1 -0.012R / EV2 +0.011R / EV2.5 +0.025R / EV3 +0.032R

BTC 2024 improves toward +3R (~+0.118R) but BTC 2025 collapses near zero. ETH 2025 is clearly negative.

Predeclared BUY/SELL split:
- **BTC SELL is the only recurring clue**
  - 2024: EV2 +0.111R / EV2.5 +0.150R / EV3 +0.170R
  - 2025: EV2 +0.053R / EV2.5 +0.114R / EV3 +0.085R
  - pooled n=761: EV2 +0.080R / EV2.5 +0.131R / EV3 +0.125R
- BTC SELL pooled BE@1 -> 3R ~+0.135R; BE@1.25 -> 3R ~+0.123R

Decision so far:
- broad BTC/ETH Momentum fails the large-edge standard;
- BTC SELL remains WATCHLIST/HYPOTHESIS ONLY;
- this is NOT a rejection of Momentum on all asset classes.

## Cross-asset expansion — RUNNING

User correctly noted Momentum could be strong on XAU/Forex even if weak on crypto. Same diagnostic already contains the non-crypto D17 branch and does not require a new EA.

User has launched / is launching same 2024-01-01 -> 2025-12-31, M1, Every tick, defaults on:
1. XAUUSD
2. EURUSD
3. GBPUSD
4. USDJPY
5. USDCAD

Do not rerun BTC/ETH. CSVs are cumulative. Analyze XAU/Forex as soon as user supplies updated `d017_momentum_virtual_events/trades/outcomes.csv`.

Important interpretation: non-crypto diagnostic retains native Momentum session/filter logic (07-17, ADX/ATR/Donchian/spread etc.), but does NOT include all Guardian news/account/prop-firm blockers or exact realized management. Cross-asset raw/native-filter edge first, then Guardian selection only if worth it.

---

# 3. RSI SNIPER LEGACY v11.16.11 — ENTRY-PATH AUDIT COMPLETE

Purpose: test the legacy closed-bar RSI lineage associated with the strong 2026-09-02 short-window BTC result.

Rules lock:
- `research/campaigns/RSI_SNIPER_11_16_11_LONG_HISTORY_DIAGNOSTIC_LOCK_2026_09_04.md`

Campaign/audit:
- `research/campaigns/D017_RSI_LONG_HISTORY_CAMPAIGN_PROTOCOL_2026_09_04.md`
- `research/results/D017_RSI_LONG_HISTORY_STATIC_AUDIT_2026_09_04.md`

The original 1.01 output bootstrap was flawed. User reran with file-bootstrap correction; signal semantics remained `V11_16_11_CLOSED_BAR`.

Final BTC+ETH entry-path report:
- `research/results/RSI_SNIPER_111611_LONG_HISTORY_BTC_ETH_2026_09_05.md`
- commit `732e30012de1d9c0439e480dbdab26ff9d73564f`

Accepted virtual legs:
- BTC 5,104 = 4,922 BUY1 + 182 BUY2
- ETH 4,416 = 4,258 BUY1 + 158 BUY2
- total 9,520

Pooled fixed first-touch EV:
- BTC: +0.5R -0.147 / +1R -0.143 / +1.25R -0.144 / +1.5R -0.131 / +2R -0.136 / +2.5R -0.134 / +3R -0.115
- ETH: +0.5R -0.122 / +1R -0.106 / +1.25R -0.100 / +1.5R -0.108 / +2R -0.120 / +2.5R -0.116 / +3R -0.104

The negative result repeats in both 2024 and 2025. BUY1 is negative throughout. Sparse BUY2 cells occasionally turn positive but do not replicate across years and are not a rescue.

BE managers also remain negative:
- BTC BE@1 -> 3R ~ -0.068R; BE@1.25 -> 3R ~ -0.078R
- ETH BE@1 -> 3R ~ -0.067R; BE@1.25 -> 3R ~ -0.073R

RSI50 before structural stop:
- BTC ~46.9%
- ETH ~50.6%

RSI70 before structural stop:
- BTC ~21.8%
- ETH ~24.5%

### Critical management caveat

This observer deliberately retires sensing at RSI50 and is an ENTRY-PATH study, not an exact replay of the production v11.16.11 manager. Production closes 40% at RSI50, applies BE + 1.50 ATR trailing, later closes most remainder at RSI70 and keeps a runner.

The event stream does contain actual RSI50 trigger price. Descriptive first-RSI50-or-stop return is still negative:
- BTC BUY1 pooled ~ -0.10R
- ETH BUY1 pooled ~ -0.08R

Therefore the legacy entry itself does NOT have a large robust fixed-R edge. The old positive MT5 strategy result, if reproducible on long history, would have to come materially from post-RSI50 management and/or Guardian/account-state selection.

Decision:
- legacy RSI raw ENTRY EDGE BTC: REJECT
- legacy RSI raw ENTRY EDGE ETH: REJECT
- BUY1 broad: REJECT
- BUY2 standalone rescue: REJECT
- do NOT tune RSI thresholds from this sample
- do NOT overclaim that the exact fully managed legacy strategy is disproven; it has not yet been replayed end-to-end

If preserving RSI is important later, the only scientifically clean follow-up is one unchanged exact native-management virtual emulator (40% RSI50, BE-net, 1.50 ATR trail, RSI70 partial, runner) over the same sample. Do not jump directly to v11.17 tuning.

---

# 4. D025 STATUS

D025 XAU/Forex final exploitation complete:
- report `research/results/D025_XAU_FOREX_FINAL_EXPLOITATION_2026_09_04.md`
- XAU broad reject; USDJPY broad reject
- EURUSD SHORT -> +2R and GBPUSD SHORT -> +1R remain only prospective watchlist clues; neither meets large-edge standard

D025 crypto volume-dependent historical results remain QUARANTINED because FundedNext historical M15 tick-volume provenance is inconsistent. Do not lower the frozen 1.25 relative-volume threshold.

---

# 5. SHARED INTELLIGENCE

Binance + Bybit Shared Intelligence remains READ-ONLY and has no current trading effect. Future Crypto+ joins must use strict `available_at <= event_time`.

---

# 6. FUNDEDNEXT LIVE GUARDIAN REQUEST BUG — HIGH PRIORITY OPERATIONS ISSUE

FundedNext HUD observed ~5629/2000 requests vs FTMO ~32/2000.

Exact live lineage:
`Guardian_D017_PropFirmAuto_v11_17_04_MANUAL_PROTECTION_HOTFIX_PLAN80_RUNNER20.mq5`

Known runaway-capable mechanism:
- RSI TP1 completes but BE NET can fail
- pending BE retried every management tick
- retry uses unlimited `SRP_PROTECTION`

FundedNext Algo Trading remains OFF until bounded/deduplicated/backoff fix is implemented and audited. Do not claim v11.17.07 exists yet.

Manual SL correction: Guardian makes ONE initial SL placement attempt; if it fails, user manually places SL. No automatic close solely because placement failed.

Quick Strike: profitable Guardian-managed <30s exits can count; never weaken safety to cross 30s.

---

# 7. IMMEDIATE NEXT STEP

Primary dependency now: finish and analyze the D017 Momentum XAU + Forex batch.

Then decide whether any non-crypto Momentum branch clears the user's large-edge threshold. Only branches with meaningful raw/native-filter edge deserve exact Guardian/news/portfolio-management replay.

RSI is no longer the primary research dependency unless user explicitly chooses to fund an exact legacy native-manager replay.

## Continuity rule

After every material milestone, update this handoff in the same work session. Important state must never exist only in conversation context.