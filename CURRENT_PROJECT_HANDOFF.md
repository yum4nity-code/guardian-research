# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 STATIC CANDIDATE / D032 DOJI ENTRY CONFIRMED BUT MANAGEMENT UNSOLVED / D030 CLOSED REJECTED / D029 CLOSED REJECTED / D033 CORRECTED M2 CLOSED REJECTED / NEXT INDEPENDENT FAMILY: COMMODITY ABNORMAL-CANDLE H1 / CURRENT FUNDEDNEXT LIVE AUTO STILL OFF

Canonical protocol: `docs/RESEARCH_PROTOCOL.md`.
Historical chronology: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.

## Research standard
- No curve fitting or post-hoc rescues disguised as validation.
- Target materially large recurring edge, roughly >= +0.15R/trade and ideally +0.20R+, before production when a natural stop/R exists.
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
- D033 Ben Omrane & Van Oppens EURUSD M5 DT/DB M2: corrected v1.01 exact arm rejected 0/7 gates. Canonical result `research/results/D033_V1_01_CORRECTED_M2_VERDICT_2026_09_05.md`, commit `3579b31e95bf30053cbabbb6ba997510d715f7b9`.

# D032 — Crypto H1 Bullish Doji Star
Research basis: Moser & Brauneis (2026), DOI `10.1016/j.iref.2026.105158`.

Frozen underlying signal: Bullish Doji Star H1, strict 144h SMA downtrend, executable LONG first ASK after signal, `1R = 2*sd(previous 24 H1 returns)`, source reference +24h.

D032-C1 PRE2024 confirmation: **PASS**. Canonical result `research/results/D032_C1_DOJI_STAR_H1_CORE_CONFIRMATION_VERDICT_2026_09_05.md`, commit `c0ef788f5e16cdb6a402cef9a0e29fa05e7691f2`.

Core BTC+ETH+DOG PRE2024: n=79, mean +133.52 bps, median +93.43 bps, win 64.56%, mean +0.588R, same-trend control ~+32.13 bps, Doji-control differential ~+101.38 bps, bootstrap lower >0, gate 7/7 PASS.

Not production-ready. Management/entry-localization attempts -1R/+3R/24h, post24 1R runner, RSI<30 and 6h reclaim-high did not solve the problem. Keep as sparse research sleeve only.

# D033 — EURUSD M5 Double Top / Double Bottom, Ben Omrane & Van Oppens M2 — CLOSED REJECTED
Primary source: Ben Omrane & Van Oppens (2006), *Empirical Economics* 30(4), 947–971, DOI `10.1007/s00181-005-0007-8`.

Preregistration: `research/campaigns/D033_EURUSD_M5_DOUBLE_TOP_BOTTOM_M2_FEATURELAB_PREREGISTRATION_2026_09_05.md`, commit `1980970f343aa9d9536fea058b9dbab09b1337a1`.

Frozen primary arm:
- EURUSD M5 midpoint reconstruction;
- rolling 36 observations;
- M2 high-curve maxima / low-curve minima;
- Gaussian Nadaraya-Watson, Silverman x0.20;
- source +/-1 projection and Appendix B.2 chronological alternation;
- source DT/DB equations and one-point equality tolerance;
- pretrend >=2/3*h;
- DT short / DB long;
- TP 0.50h, SL 0.20h, timeout `tf+(tf-td)`;
- executable BID/ASK spread embedded;
- passive feature lab never filters signals.

v1.00 was invalidated for a source-fidelity alternation bug and is not a valid verdict. v1.01 corrected only that deterministic Appendix B.2 step.

Corrected v1.01 EURUSD 2024-2026 run:
- raw resolved n=126; clean no-gap n=125;
- clean mean executable **-0.817458R/trade**;
- clean median **-1.415525R/trade**;
- clean mean executable **-0.987138 bps/trade**;
- win rate 24.0%; 34 TP / 91 SL;
- DT n=69 mean -0.565607R; DB n=56 mean -1.127774R;
- 2024 -1.122742R; 2025 +0.163927R; 2026 -1.337520R;
- month-block bootstrap 95% approx **[-1.248R, -0.345R]**;
- largest positive event ~12.35% of total positive R.

Frozen gate: **0/7 PASS -> REJECT**. Do not widen equal-extrema tolerance, alter the 36-bar window/kernel, retune TP/SL, or mine passive RSI/SMA/ATR/session features on 2024-2026 to rescue D033.

Canonical result: `research/results/D033_V1_01_CORRECTED_M2_VERDICT_2026_09_05.md`, commit `3579b31e95bf30053cbabbb6ba997510d715f7b9`.

## Immediate execution order
1. Close D033; no same-sample rescue.
2. Move to the next independent documented family: commodity abnormal-candle strategy, preferably H1 XAU and Oil/WTI transfer, based on Caporale & Plastun (2021). Recover/freeze exact source rule before coding.
3. Include passive feature diagnostics in the next scanner only if they do not filter the primary rule; avoid the D029 H4-history contamination by reconstructing needed higher/lower timeframe features internally with QA.
4. Keep D032 as sparse confirmed-entry sleeve, not sole challenge engine.
5. Pure Guardian Core v12.01 compile/smoke remains independently required before live replacement.

Continuity rule: after every material milestone, update this handoff in the same work session.