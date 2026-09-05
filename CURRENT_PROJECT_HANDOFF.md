# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / D026 REJECTED / LEGACY RSI ENTRY EDGE REJECTED / D017 MOMENTUM BTC+ETH BROAD REJECTED / XAU+EUR+GBP+JPY BROAD REJECTED / WEAK WATCHLIST CLUES ONLY / USDCAD MOMENTUM STILL MISSING / FUNDEDNEXT LIVE AUTO OFF PENDING REQUEST-BUDGET FIX

Read this first. Historical chronology/time ledger: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.

## Research standard
- No curve fitting or post-hoc threshold edits disguised as fixes.
- User wants materially large recurring pre-cost edge, roughly >= +0.15R/trade and ideally +0.20R+, before production work.
- Distinguish raw signal, native engine filters/management, and Guardian operational selection. Guardian can improve or worsen results but must not be assumed to rescue a weak raw population.
- Manual MT5 Strategy Tester is the preferred execution path.

## D026 Price Exhaustion Reclaim — REJECTED
Final corrected report: `research/results/D026_V0_CORRECTED_FINAL_DIAGNOSTIC_2026_09_04.md` (commit `e664026b1cda9317ba632cff13613fec87d22683`). Corrected BTC+ETH combined roughly +0.001R at +1R, -0.086R at +2R, -0.156R at +3R. Do not retune.

## D017 Momentum — long-history status
Rules lock: `research/campaigns/D017_MOMENTUM_LONG_HISTORY_DIAGNOSTIC_LOCK_2026_09_04.md`.
EA: `research/ea/D017_Momentum_VirtualDiagnostic_1_01_STATIC_CONFORMANCE.mq5`.

### BTC + ETH
Report: `research/results/D017_MOMENTUM_LONG_HISTORY_FIRST_VERDICT_2026_09_05.md`.
Canonical populations: BTC 1710, ETH 1144.
Broad combined fixed EV: ~-0.012R +1R / +0.011R +2R / +0.025R +2.5R / +0.032R +3R. Broad crypto Momentum fails.
Only recurring crypto clue: BTC SELL pooled n=761, ~+0.080R +2R / +0.131R +2.5R / +0.125R +3R; positive both years but below user's edge threshold. WATCHLIST ONLY.

### XAU / Forex partial batch received 2026-09-05
Report: `research/results/D017_MOMENTUM_XAU_FOREX_PARTIAL_BATCH_2026_09_05.md` (commit `d66d6b94ecdcf027170fb619b6f3f128e44867bb`).
Canonical sessions present:
- XAUUSD 676 = 327 (2024) +349 (2025)
- EURUSD 476 =239+237
- GBPUSD 444 =178+266
- USDJPY 536 =247+289
- USDCAD is NOT present in the supplied cumulative CSVs yet.

Broad fixed EV (+1R / +2R / +2.5R / +3R):
- XAU: -0.037 / -0.033 / +0.010 / +0.003R
- EUR: +0.032 / -0.048 / -0.152 / -0.220R
- GBP: -0.053 / -0.088 / -0.049 / -0.024R
- JPY: +0.013 / +0.014 / -0.039 / -0.024R

Year stability:
- XAU flips: 2024 negative; 2025 becomes positive. XAU BUY 2025 reaches ~+0.196R at +2.5R / +0.190R at +3R, but 2024 BUY is negative. Descriptive regime clue only, not robust.
- EUR degrades sharply in 2025. EUR SELL +1R is mildly positive both years (~+0.043R / +0.065R), pooled ~+0.052R only.
- GBP has no robust useful branch.
- USDJPY is strongly positive in 2024 at larger targets (up to ~+0.217R at +3R) then strongly negative in 2025 (~-0.223R at +3R). USDJPY SELL +1R remains mildly positive both years (~+0.044R / +0.095R), pooled ~+0.075R; +2R pooled ~+0.045R. Too small.

Decision current partial batch:
- broad XAU/EUR/GBP/USDJPY Momentum: REJECT under large-edge standard.
- EUR SELL +1R and USDJPY SELL +1R/+2R: weak watchlist clues only.
- XAU BUY 2025: regime-specific clue only, cannot be promoted without prospective regime logic.
- exact Guardian/news/account/portfolio filtering has NOT been applied; do not credit it in advance.
- USDCAD remains the only requested non-crypto Momentum market not yet in the CSV batch.

## RSI Sniper legacy v11.16.11 — ENTRY EDGE REJECTED
Rules lock: `research/campaigns/RSI_SNIPER_11_16_11_LONG_HISTORY_DIAGNOSTIC_LOCK_2026_09_04.md`.
Final entry-path report: `research/results/RSI_SNIPER_111611_LONG_HISTORY_BTC_ETH_2026_09_05.md` (commit `732e30012de1d9c0439e480dbdab26ff9d73564f`).
Accepted legs: BTC 5104, ETH 4416, total 9520. Fixed first-touch EV is negative across targets and repeats negative in both 2024 and 2025. BTC around -0.143R +1R / -0.115R +3R. ETH around -0.106R +1R / -0.104R +3R. BE variants remain negative. BUY2 does not provide a robust rescue.
Decision: raw legacy RSI entry edge REJECTED. Exact fully managed legacy strategy is not strictly disproven because production management after RSI50 (40% partial, BE, ATR trail, RSI70 partial, runner) was not replayed end-to-end. If revisited, only do one unchanged exact native-management emulator; no threshold tuning.

## D025
XAU/Forex final exploitation complete and broad rejected. Weak prospective clues only: EURUSD SHORT -> +2R and GBPUSD SHORT -> +1R, neither clears large-edge standard. Crypto volume-dependent historical branch remains QUARANTINED because FundedNext historical tick-volume provenance is inconsistent; do not lower the frozen relative-volume threshold.

## FundedNext live Guardian request bug
Live source lineage: `Guardian_D017_PropFirmAuto_v11_17_04_MANUAL_PROTECTION_HOTFIX_PLAN80_RUNNER20.mq5`.
Known runaway mechanism: RSI TP1 completes, BE NET can fail, pending BE retries every management tick through unlimited `SRP_PROTECTION`. FundedNext Algo Trading remains OFF until bounded/deduplicated/backoff fix is implemented and audited. Do not claim v11.17.07 exists yet.
Manual SL correction: Guardian makes ONE initial SL placement attempt; if it fails user manually places SL. No automatic close solely because initial placement failed.
Quick Strike: profitable Guardian-managed exits under 30 seconds can count; never weaken safety merely to cross 30s.

## Immediate next step
1. If user has run USDCAD Momentum, receive the updated cumulative D017 CSV trio and analyze USDCAD immediately.
2. Do not rerun XAU/EUR/GBP/JPY; those sessions are already in the latest files.
3. After USDCAD, decide whether any Momentum branch deserves a prospectively locked Guardian/news/portfolio-selection replay. Current evidence does NOT justify assuming Guardian will create a large edge from the rejected broad populations.
4. RSI exact native-manager replay is optional, not primary, unless user explicitly chooses to preserve that line.

Continuity rule: after every material milestone, update this handoff in the same work session.