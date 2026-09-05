# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / D026 REJECTED / LEGACY RSI ENTRY EDGE REJECTED ACROSS BTC+ETH+XAU+EUR / D017 MOMENTUM BTC+ETH BROAD REJECTED / XAU+EUR+GBP+JPY BROAD REJECTED / WEAK WATCHLIST CLUES ONLY / USDCAD MOMENTUM UNAVAILABLE ON CURRENT FUNDEDNEXT / FUNDEDNEXT LIVE AUTO OFF PENDING REQUEST-BUDGET FIX

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
- USDCAD is not currently offered on the user's FundedNext account, so no comparable backtest can be run now.

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

## RSI Sniper legacy v11.16.11 — ENTRY EDGE REJECTED ACROSS FOUR ASSETS
Rules lock: `research/campaigns/RSI_SNIPER_11_16_11_LONG_HISTORY_DIAGNOSTIC_LOCK_2026_09_04.md`.
BTC+ETH report: `research/results/RSI_SNIPER_111611_LONG_HISTORY_BTC_ETH_2026_09_05.md` (commit `732e30012de1d9c0439e480dbdab26ff9d73564f`).
XAU+EUR report: `research/results/RSI_SNIPER_111611_XAU_EUR_2026_09_05.md` (commit `7ceeca8707342292a058a3214d1bc41384a6e8bd`).

Accepted legs:
- BTC 5104
- ETH 4416
- XAU 2515 = 2409 BUY1 +106 BUY2
- EUR 2004 = 1940 BUY1 +64 BUY2

BTC/ETH fixed first-touch entry EV was already negative across targets and both years.

New XAU result:
- pooled EV1 -0.147R / EV2 -0.202R / EV2.5 -0.196R / EV3 -0.172R
- 2024 negative; 2025 negative; BE variants remain negative
- RSI50 before stop ~44.3%; RSI70 before stop ~19.5%
- BUY2 2025 looks superficially strong but n=49 and reverses sign versus 2024; reject as rescue/noise.

New EUR result:
- pooled EV1 -0.069R / EV2 -0.044R / EV2.5 -0.043R / EV3 -0.070R
- 2024 clearly negative; 2025 roughly flat with tiny positives at some targets
- pooled BE managers ~0R; 2025 BE variants ~+0.08 to +0.11R but 2024 remains negative, so not robust and below the user's large-edge standard
- RSI50 before stop ~46.3%; RSI70 before stop ~20.1%
- BUY2 pooled looks better but only n=64 total and is driven by n=20 in 2025; 2024 does not replicate.

Decision:
- raw legacy RSI entry edge REJECTED on BTC, ETH, XAU and EUR.
- no threshold tuning from these samples.
- exact fully managed legacy strategy is still not strictly disproven because production management after RSI50 (40% partial, BE, 1.50 ATR trail, RSI70 partial, runner) was not replayed end-to-end. If revisited, only do one unchanged exact native-management emulator.

## Shared Intelligence / external data
The Binance+Bybit multi-venue plumbing is implemented and has passed runtime/bridge gates. It currently collects/derives spot/perp, basis, OI, funding, liquidation and return/dislocation features for BTC/ETH. These features have not yet been proven to add predictive edge; historical depth is only accumulating from implementation onward unless separate historical provider data are obtained. Do not call the plumbing useless, but do not credit predictive value until event studies prove incremental value with strict `available_at <= event_time`.

## D025
XAU/Forex final exploitation complete and broad rejected. Weak prospective clues only: EURUSD SHORT -> +2R and GBPUSD SHORT -> +1R, neither clears large-edge standard. Crypto volume-dependent historical branch remains QUARANTINED because FundedNext historical tick-volume provenance is inconsistent; do not lower the frozen relative-volume threshold.

## FundedNext live Guardian request bug
Live source lineage: `Guardian_D017_PropFirmAuto_v11_17_04_MANUAL_PROTECTION_HOTFIX_PLAN80_RUNNER20.mq5`.
Known runaway mechanism: RSI TP1 completes, BE NET can fail, pending BE retries every management tick through unlimited `SRP_PROTECTION`. FundedNext Algo Trading remains OFF until bounded/deduplicated/backoff fix is implemented and audited. Do not claim v11.17.07 exists yet.
Manual SL correction: Guardian makes ONE initial SL placement attempt; if it fails user manually places SL. No automatic close solely because initial placement failed.
Quick Strike: profitable Guardian-managed exits under 30 seconds can count; never weaken safety merely to cross 30s.

## Immediate next step
1. Do not spend more time on raw RSI threshold tweaking; four-asset entry evidence is sufficient to reject the raw family.
2. USDCAD Momentum is deferred until it is available again on FundedNext; do not substitute a different broker/source just to fill the grid.
3. Primary research direction should move to prospectively locked, documented setups and/or setup-detection research, while keeping Guardian as the execution/protection layer.
4. Shared Intelligence crypto data should be exploited via prospective/event-study feature tests once enough history exists or a valid historical external-data source is obtained.
5. Exact RSI native-manager replay remains optional only if the user specifically wants to test whether management, not entry edge, created the old positive short-window strategy result.

Continuity rule: after every material milestone, update this handoff in the same work session.