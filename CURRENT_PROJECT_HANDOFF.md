# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / EVIDENCE-FIRST STRATEGY RESET / D026 REJECTED / LEGACY RSI ENTRY EDGE REJECTED ACROSS BTC+ETH+XAU+EUR / D017 MOMENTUM BROAD REJECTED ON AVAILABLE BTC+ETH+XAU+EUR+GBP+JPY / D023 ORB NEXT / D022+D027+D028 QUEUED / FUNDEDNEXT LIVE AUTO OFF PENDING REQUEST-BUDGET FIX

Read this first. Historical chronology/time ledger: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.

## Research standard
- No curve fitting or post-hoc threshold edits disguised as fixes.
- User wants materially large recurring pre-cost edge, roughly >= +0.15R/trade and ideally +0.20R+, before production work.
- Distinguish raw signal, native engine filters/management, and Guardian operational selection. Guardian can improve or worsen results but must not be assumed to rescue a weak raw population.
- Manual MT5 Strategy Tester is the preferred execution path when an MQ5 diagnostic is used; cheap-fail event studies are also acceptable when input provenance/costs are explicit.
- Current pivot: prefer strategy families with published or long practitioner evidence, freeze one V0 before results, and reject quickly if they fail our markets/costs.

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

### XAU / Forex partial batch
Report: `research/results/D017_MOMENTUM_XAU_FOREX_PARTIAL_BATCH_2026_09_05.md`.
Canonical sessions:
- XAUUSD 676
- EURUSD 476
- GBPUSD 444
- USDJPY 536
- USDCAD unavailable on current FundedNext, so deferred rather than substituted with another broker/source.

Broad fixed EV (+1R / +2R / +2.5R / +3R):
- XAU: -0.037 / -0.033 / +0.010 / +0.003R
- EUR: +0.032 / -0.048 / -0.152 / -0.220R
- GBP: -0.053 / -0.088 / -0.049 / -0.024R
- JPY: +0.013 / +0.014 / -0.039 / -0.024R

Decision: broad XAU/EUR/GBP/USDJPY Momentum REJECT under large-edge standard. EUR SELL +1 and USDJPY SELL +1/+2 remain weak watchlist clues only. XAU BUY 2025 is regime-specific only. No Guardian rescue assumed.

## RSI Sniper legacy v11.16.11 — ENTRY EDGE REJECTED ACROSS FOUR ASSETS
Rules lock: `research/campaigns/RSI_SNIPER_11_16_11_LONG_HISTORY_DIAGNOSTIC_LOCK_2026_09_04.md`.
BTC+ETH report: `research/results/RSI_SNIPER_111611_LONG_HISTORY_BTC_ETH_2026_09_05.md`.
XAU+EUR report: `research/results/RSI_SNIPER_111611_XAU_EUR_2026_09_05.md`.

Accepted legs: BTC 5104, ETH 4416, XAU 2515, EUR 2004.
XAU pooled EV1 -0.147R / EV2 -0.202R / EV2.5 -0.196R / EV3 -0.172R; both years negative.
EUR pooled EV1 -0.069R / EV2 -0.044R / EV2.5 -0.043R / EV3 -0.070R; 2024 negative and 2025 only near-flat/tiny positive pockets.
BUY2 apparent pockets are sparse and non-replicating.

Decision: raw legacy RSI entry edge REJECTED on BTC/ETH/XAU/EUR. No threshold tuning. Exact native management (40% RSI50, BE net, 1.50 ATR trail, RSI70 partial, runner) remains technically untested end-to-end and is optional only if specifically requested.

## Shared Intelligence / external data
Binance+Bybit multi-venue collection and MT5 bridge are implemented and passed runtime gates. Available BTC/ETH facts include spot/perp, basis, OI, funding, long/short liquidation windows, returns and cross-venue dislocation. Predictive edge is NOT yet proven. Archive depth is accumulating from implementation onward; all future research must enforce `available_at <= event_time`.

## Evidence-based strategy slate — 2026-09-05
Canonical slate: `research/results/STRATEGY_RESEARCH_SLATE_2026_09_05.md`.

Target today: **four independent V0 families**, not many parameter variants.

### Priority 1 — D023 London ORB M15
Already preregistered/engine prepared before today's results.
Universe: EURUSD, GBPUSD, USDJPY, XAUUSD.
Opening range 08:00-09:00 London; first M15 close breakout 09:00-11:00; entry next bar; stop opposite range edge; exit stop or 16:00; max one trade/day/symbol.
External basis: Holmberg/Lonnback/Lundstrom 2013 Finance Research Letters + classic ORB literature.
No RSI/EMA/ATR/news/day filter in V0.

### Priority 2 — D022 Relative-Value Pair Reversion M15
Existing preregistration and corrected engine v2.
Pairs frozen before results: AUDUSD/NZDUSD and EURUSD/GBPUSD.
External family basis: Gatev/Goetzmann/Rouwenhorst 2006 Review of Financial Studies.
If one of the frozen required symbols is unavailable, defer rather than substitute post-hoc.

### Priority 3 — D027 NR7 Contraction Breakout
New preregistration: `research/campaigns/D027_NR7_CONTRACTION_BREAKOUT_V0_PREREGISTRATION_2026_09_05.md`.
Universe: EURUSD, GBPUSD, USDJPY, XAUUSD.
Prior Europe/London trading day must be strict NR7; next day first M15 close beyond prior NR7 high/low from 07:00-16:00; entry next bar; stop opposite NR7 edge; exit stop or 16:00; one trade max.
Basis: Toby Crabel narrow-range contraction/expansion framework. No indicator filters.

### Priority 4 — D028 Intraday Session Momentum
New preregistration: `research/campaigns/D028_INTRADAY_SESSION_MOMENTUM_V0_PREREGISTRATION_2026_09_05.md`.
Universe: EURUSD, GBPUSD, USDJPY, XAUUSD.
Signal = direction of exactly 08:00-08:30 London; trade same direction 16:30-17:00; one trade/day; no signal threshold in V0.
Basis: Gao et al. 2018 JFE; Elaut et al. 2018 Journal of Financial Markets (FX); Jin et al. 2020 Journal of Futures Markets. Counter-evidence from Rosa 2022 retained explicitly; this is a falsifiable test, not assumed edge.

### Priority 5 optional benchmark — D029 Classic TSMOM
New preregistration: `research/campaigns/D029_CLASSIC_TSMOM_BENCHMARK_V0_PREREGISTRATION_2026_09_05.md`.
Literature-style 252-day sign-of-return benchmark, deliberately separate from D017 impulse Momentum.
Basis: Moskowitz/Ooi/Pedersen 2012 JFE and Hurst/Ooi/Pedersen 2017 JPM.
Strongest external evidence but too slow to be the primary challenge engine; use as sanity benchmark/diversifier if cheap to run.

### D021 MICRO-REV
Not deleted; deprioritized behind the stronger direct external-evidence slate. Existing engine must not be rewritten/tuned.

## New analysis implementation
`research/analysis/analyze_d027_d028_price_action_v1.py`
Locally syntax-checked and synthetic end-to-end smoke-tested before commit. Pre-commit SHA-256: `627a4202d0af971c530c737241ab4f192d6a9ca7babc53326799b97d7160d376`.

Capabilities:
- exact four-symbol M15 input set EURUSD/GBPUSD/USDJPY/XAUUSD;
- UTC bid OHLC + spread in price units;
- Europe/London DST-aware;
- provenance SHA-256;
- fail-closed OOS guard;
- D027 + D028 independently;
- 1.5x spread+commission stress;
- frozen moving-block bootstrap: 5-day blocks, 5000 reps, seed 20260905;
- monthly concentration and year splits;
- refuses a fully costed candidate verdict when round-trip commission price-unit inputs are missing.

Synthetic smoke validates plumbing only, not profitability.

## D025
XAU/Forex final exploitation complete and broad rejected. Weak prospective clues only. Crypto volume-dependent history remains quarantined due FundedNext tick-volume provenance. Shared Intelligence may later support a new leakage-safe external-data event study, but no current predictive credit.

## FundedNext live Guardian request bug
Known runaway mechanism: RSI TP1 completes, BE NET can fail, pending BE retries every management tick through unlimited `SRP_PROTECTION`. FundedNext Algo Trading remains OFF until bounded/deduplicated/backoff fix is implemented and audited. Do not claim v11.17.07 exists yet.
Manual SL correction: ONE initial Guardian SL placement attempt; if it fails, user manually places SL. No automatic close solely for that failure.
Quick Strike: profitable Guardian-managed exits under 30 seconds can count; never weaken safety merely to cross 30s.

## Immediate next execution order
1. D023 London ORB M15.
2. D022 Pair Reversion if the exact frozen symbols are available; otherwise defer without substitution.
3. D027 NR7 Contraction Breakout.
4. D028 Intraday Session Momentum.
5. Optional D029 classic TSMOM benchmark if data/execution cost is cheap.
6. Continue Shared Intelligence archive in the background; do not use young live archive as fake historical evidence.

Continuity rule: after every material milestone, update this handoff in the same work session.
