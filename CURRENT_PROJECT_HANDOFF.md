# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 STATIC CANDIDATE / D032 DOJI ENTRY CONFIRMED BUT MANAGEMENT UNSOLVED / D030 CLOSED REJECTED / D029 CLOSED REJECTED / D033 V1.00 INVALIDATED FOR SOURCE-FIDELITY BUG / D033 V1.01 CORRECTION READY / CURRENT FUNDEDNEXT LIVE AUTO STILL OFF

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

# D032 — Crypto H1 Bullish Doji Star
Research basis: Moser & Brauneis (2026), DOI `10.1016/j.iref.2026.105158`.

Frozen underlying signal: Bullish Doji Star H1, strict 144h SMA downtrend, executable LONG first ASK after signal, `1R = 2*sd(previous 24 H1 returns)`, source reference +24h.

D032-C1 PRE2024 confirmation: **PASS**. Canonical result `research/results/D032_C1_DOJI_STAR_H1_CORE_CONFIRMATION_VERDICT_2026_09_05.md`, commit `c0ef788f5e16cdb6a402cef9a0e29fa05e7691f2`.

Core BTC+ETH+DOG PRE2024: n=79, mean +133.52 bps, median +93.43 bps, win 64.56%, mean +0.588R, same-trend control ~+32.13 bps, Doji-control differential ~+101.38 bps, bootstrap lower >0, gate 7/7 PASS.

Not production-ready. Management/entry-localization attempts -1R/+3R/24h, post24 1R runner, RSI<30 and 6h reclaim-high did not solve the problem. Keep as sparse research sleeve only.

# D033 — EURUSD M5 Double Top / Double Bottom, Ben Omrane & Van Oppens M2
Primary source: Ben Omrane & Van Oppens (2006), *Empirical Economics* 30(4), 947–971, DOI `10.1007/s00181-005-0007-8`.

Preregistration: `research/campaigns/D033_EURUSD_M5_DOUBLE_TOP_BOTTOM_M2_FEATURELAB_PREREGISTRATION_2026_09_05.md`, commit `1980970f343aa9d9536fea058b9dbab09b1337a1`.

Frozen primary arm remains unchanged:
- EURUSD M5 midpoint reconstruction;
- rolling 36 observations;
- M2 high-curve maxima / low-curve minima;
- Gaussian Nadaraya-Watson, Silverman x0.20;
- source +/-1 projection;
- source DT/DB equations and one-point equality tolerance;
- pretrend >=2/3*h;
- DT short / DB long;
- TP 0.50h, SL 0.20h, timeout `tf+(tf-td)`;
- executable BID/ASK spread embedded;
- passive feature lab never filters signals.

## D033 v1.00 returned run — provisional negative, but NOT valid final verdict
User supplied EURUSD 2024-2026 v1.00 output:
- 127 events; clean no-gap n=126;
- DT n=69, mean -0.288864R, median -1.270718R;
- DB n=58, mean -1.130671R, median -1.424674R;
- pooled mean -0.673311R, median -1.382488R;
- pooled mean executable -0.929607 bps;
- clean mean -0.657055R;
- years: 2024 -0.829616R, 2025 +0.064470R, 2026 -1.314087R;
- month-block bootstrap 95% interval approx [-1.063, -0.246]R;
- source-mid result also weak: DT ~+0.085 bps, DB ~-0.846 bps.

However, audit against Appendix B.2 found a deterministic source-fidelity implementation error in v1.00: the alternation routine replaced a selected extremum with a later more-extreme extremum of the same type. The source requires retaining the selected first extremum, skipping same-type candidates, and then taking the chronologically first later opposite-type extremum.

Therefore v1.00 must **not** be called a valid close-replication rejection. Audit/result: `research/results/D033_V1_00_IMPLEMENTATION_AUDIT_AND_PROVISIONAL_FAIL_2026_09_05.md`, commit `fbe27a2901f7dedc7729ac3c711ac7f34518664a`.

## D033 v1.01 correction
Corrected scanner: `D033_EURUSD_M5_DoubleTopBottom_M2_FeatureLab_v1_01.mq5`
SHA-256: `8281951c4b7745dac0f9660808294dc447c351a20cd2679d116b5384551796b3`

Only the Appendix B.2 alternation procedure changed. No equality tolerance, 36-bar window, kernel rule, pretrend, TP/SL, timeout, signal window, spread handling or feature rule changed. Static token-aware balance QA: braces/parens/brackets all 0. ChatGPT has not MetaEditor-compiled it.

Original frozen D033 gate remains unchanged: >=250 clean resolved trades; mean >+0.15R; median >0; month-block bootstrap lower >0; DT and DB both positive; >=2 positive calendar years; no single event >10% of total positive R.

## Immediate execution order
1. Compile `D033_EURUSD_M5_DoubleTopBottom_M2_FeatureLab_v1_01.mq5`.
2. Rerun EURUSD only with identical tester settings/dates as v1.00: M1 / `1 minute OHLC`, warm-up before 2024, enough tail after 2026-06-30; no input changes.
3. Return EVENTS/SUMMARY/RUN_INFO.
4. Decide D033 only from v1.01 corrected implementation. Do not tune feature thresholds on 2024-2026.
5. If corrected D033 fails, move to the next independent family rather than rescuing DT/DB.
6. Keep D032 as sparse confirmed-entry sleeve, not sole challenge engine.

Continuity rule: after every material milestone, update this handoff in the same work session.
