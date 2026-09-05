# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 STATIC CANDIDATE / D032 DOJI ENTRY CONFIRMED BUT MANAGEMENT UNSOLVED / D030 CLOSED REJECTED / D029 CLOSED REJECTED / D033 CLOSED REJECTED / D034 GOLD ARM CLOSED REJECTED, OIL UNTESTED-UNAVAILABLE / CURRENT FUNDEDNEXT LIVE AUTO STILL OFF

Canonical protocol: `docs/RESEARCH_PROTOCOL.md`.
Historical chronology: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.

## Research standard
- No curve fitting or post-hoc rescues disguised as validation.
- Target materially large recurring edge, roughly >= +0.15R/trade and ideally +0.20R+, before production when a natural stop/R exists.
- When a source has no natural stop, do not invent R post-hoc; use source/raw return metrics first.
- Guardian is execution/protection infrastructure, not alpha.
- Preserve `EXACT_REPLICATION`, `CLOSE_REPLICATION`, `ADAPTATION` labels.
- Ex-post anomalies require a new preregistered test unless a rerun is a mechanical implementation correction dictated by the frozen source specification.
- CFD transfer requires executable BID/ASK/cost handling.
- Scanner QA after D032 v1.00: output-column counts/index bounds, immediate header flush, runtime output QA, plus source-algorithm audit for nontrivial sequence construction.

## Pure Guardian Core v12.01
Candidate: `Guardian_Core_Base_v12_01_CANDIDATE.mq5`
SHA-256: `6a74d4187e04a02f9924c48ef34a1f0eb946da0f64d66a4839701154d6ad1176`
Strategy socket: `GuardianCore/Guardian_StrategyRegistry_v1.mqh`
Template: `GuardianCore/Guardian_StrategyModule_TEMPLATE_v1.mqh`
Status remains STATIC PASS only; MetaEditor compile/smoke required before live replacement. FundedNext Algo Trading remains OFF.

## Closed / rejected families
- RSI legacy v11.16.11 raw edge: rejected.
- D017 Momentum broad: rejected.
- D022 pair reversion M15: rejected.
- D023 London ORB broad: rejected; USDJPY anomaly discovery-only.
- D025/D026 broad exploitation: rejected/quarantined.
- D027 NR7 broad: rejected.
- D028 session momentum: rejected.
- D031 FX Piercing/Dark Cloud D1 broad: not validated.
- D030 Alanazi H4 Engulfing: seven-major FX rejected; ETH discovery failed untouched 2019-2023 confirmation. Canonical ETH result `research/results/D030_C1_ETHUSD_H4_ENGULFING_PRE2024_CONFIRMATION_VERDICT_2026_09_05.md`, commit `28ce836c22edc9c19309c9194e93e3f04e9863ea`.
- D029 Moskowitz/Ooi/Pedersen TSMOM 12M/1M: full 8-market gate rejected. Canonical result `research/results/D029_TSMOM_12M1M_FULL_PRIMARY_VERDICT_2018_2023_2026_09_05.md`, commit `1613b46caa1be8ac9002778fcd58f4dd23f16fcc`.
- D033 Ben Omrane & Van Oppens EURUSD M5 DT/DB M2: corrected v1.01 arm rejected 0/7 gates. Canonical result `research/results/D033_V1_01_CORRECTED_M2_VERDICT_2026_09_05.md`, commit `3579b31e95bf30053cbabbb6ba997510d715f7b9`.
- D034 Caporale/Plastun abnormal-return Strategy 1 GOLD arm: rejected 3/7 gates. OIL could not be run because no WTI/USOIL/XTI symbol is available on the target account. Canonical GOLD result `research/results/D034_XAUUSD_ABNORMAL_RETURN_STRAT1_VERDICT_2026_09_05.md`, commit `f59d2a4cabb231c6ee50178df4e347646056dd22`.

# D032 — Crypto H1 Bullish Doji Star
Research basis: Moser & Brauneis (2026), DOI `10.1016/j.iref.2026.105158`.

Frozen underlying signal: Bullish Doji Star H1, strict 144h SMA downtrend, executable LONG first ASK after signal, `1R = 2*sd(previous 24 H1 returns)`, source reference +24h.

D032-C1 PRE2024 confirmation: **PASS**. Canonical result `research/results/D032_C1_DOJI_STAR_H1_CORE_CONFIRMATION_VERDICT_2026_09_05.md`, commit `c0ef788f5e16cdb6a402cef9a0e29fa05e7691f2`.

Core BTC+ETH+DOG PRE2024: n=79, mean +133.52 bps, median +93.43 bps, win 64.56%, mean +0.588R, same-trend control ~+32.13 bps, Doji-control differential ~+101.38 bps, bootstrap lower >0, gate 7/7 PASS.

Not production-ready. Management/entry-localization attempts -1R/+3R/24h, post24 1R runner, RSI<30 and 6h reclaim-high did not solve the problem. Keep as sparse research sleeve only.

# D034 — Gold/Oil intraday abnormal-return momentum — GOLD CLOSED REJECTED / OIL UNTESTED
Primary source: Caporale & Plastun (2021), *Financial Markets and Portfolio Management* 35, 353–368, DOI `10.1007/s11408-021-00380-w`.

Preregistration: `research/campaigns/D034_GOLD_OIL_INTRADAY_ABNORMAL_RETURN_MOMENTUM_PREREGISTRATION_2026_09_05.md`, commit `3e3166bf08f03bf958de573f98250f98697dc9d6`.
Prepared scanner: `D034_GoldOil_AbnormalReturn_Momentum_FeatureLab_v1_00.mq5`, SHA-256 `842ca596a017229c27857030589c0f5b432e52313364f7f7a27c73890da138fe`.
Classification: `ADAPTATION_CAUSAL_CFD_TRANSFER`.

Frozen rule: prior252 D1 mean +/-2sd abnormal threshold; GOLD positive timing >=17:00 and negative >=19:00 server clock; enter in anomaly direction; one trade/day; no SL/TP; exit last executable quote same server day; spread embedded; signal window 2024-01-01 through 2026-06-30.

Returned XAUUSD run:
- all 83 events clean;
- pooled mean executable **+1.8925 bps/event**;
- median +8.4451 bps;
- win 57.83%;
- LONG n=37 mean +9.6399 bps, win 67.57%;
- SHORT n=46 mean -4.3390 bps;
- 2024 mean -1.4951 bps;
- 2025 mean -4.1560 bps;
- 2026 through June mean +13.9691 bps;
- month-cluster bootstrap 95% approximately **[-7.95, +12.62] bps/event**;
- largest positive-event concentration ~9.60%;
- frozen GOLD gate **3/7 -> REJECT**.

Interpretation: weak positive pooled/median behavior exists, but economically too small, bootstrap crosses zero, shorts are negative, and year stability fails. LONG-only is also below the +15 bps gate and was not preregistered as a separate strategy. Do not rescue with timing, k, lookback, direction, RSI/SMA filters, or invented SL/TP on the same 2024-2026 sample.

OIL is **untested**, not failed, because the target FundedNext account exposes no suitable WTI/USOIL/XTI symbol.

Canonical GOLD result: `research/results/D034_XAUUSD_ABNORMAL_RETURN_STRAT1_VERDICT_2026_09_05.md`, commit `f59d2a4cabb231c6ee50178df4e347646056dd22`.

## Immediate execution order
1. Do not spend more time rescuing D030/D029/D033/D034 on already-inspected samples.
2. Keep D032 Doji as a sparse confirmed-entry sleeve, not sole challenge engine.
3. Select the next independent, reasonably active documented family rather than another parameter variant of rejected breakout/momentum/reversal work.
4. Pure Guardian Core v12.01 compile/smoke remains independently required before live replacement.

Continuity rule: after every material milestone, update this handoff in the same work session.
