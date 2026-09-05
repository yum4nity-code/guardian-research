# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 STATIC CANDIDATE / D032 DOJI ENTRY CONFIRMED BUT MANAGEMENT UNSOLVED / D030 CLOSED REJECTED / D029 CLOSED REJECTED / D033 CORRECTED M2 CLOSED REJECTED / D034 GOLD-OIL ABNORMAL-RETURN MOMENTUM PREPARED / CURRENT FUNDEDNEXT LIVE AUTO STILL OFF

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
- D033 Ben Omrane & Van Oppens EURUSD M5 DT/DB M2: corrected v1.01 exact arm rejected 0/7 gates. Canonical result `research/results/D033_V1_01_CORRECTED_M2_VERDICT_2026_09_05.md`, commit `3579b31e95bf30053cbabbb6ba997510d715f7b9`.

# D032 — Crypto H1 Bullish Doji Star
Research basis: Moser & Brauneis (2026), DOI `10.1016/j.iref.2026.105158`.

Frozen underlying signal: Bullish Doji Star H1, strict 144h SMA downtrend, executable LONG first ASK after signal, `1R = 2*sd(previous 24 H1 returns)`, source reference +24h.

D032-C1 PRE2024 confirmation: **PASS**. Canonical result `research/results/D032_C1_DOJI_STAR_H1_CORE_CONFIRMATION_VERDICT_2026_09_05.md`, commit `c0ef788f5e16cdb6a402cef9a0e29fa05e7691f2`.

Core BTC+ETH+DOG PRE2024: n=79, mean +133.52 bps, median +93.43 bps, win 64.56%, mean +0.588R, same-trend control ~+32.13 bps, Doji-control differential ~+101.38 bps, bootstrap lower >0, gate 7/7 PASS.

Not production-ready. Management/entry-localization attempts -1R/+3R/24h, post24 1R runner, RSI<30 and 6h reclaim-high did not solve the problem. Keep as sparse research sleeve only.

# D033 — EURUSD M5 Double Top / Double Bottom, Ben Omrane & Van Oppens M2 — CLOSED REJECTED
Primary source: Ben Omrane & Van Oppens (2006), *Empirical Economics* 30(4), 947–971, DOI `10.1007/s00181-005-0007-8`.

Corrected v1.01 EURUSD 2024-2026 clean run: n=125, mean -0.817458R, median -1.415525R, mean executable -0.987138 bps, win 24%; DT and DB both negative; month-block bootstrap entirely negative; frozen gate 0/7 -> REJECT. Do not rescue with equality/session/RSI/TP-SL retuning.

Canonical result: `research/results/D033_V1_01_CORRECTED_M2_VERDICT_2026_09_05.md`, commit `3579b31e95bf30053cbabbb6ba997510d715f7b9`.

# D034 — Gold/Oil intraday abnormal-return momentum — PREPARED
Primary source: Caporale & Plastun (2021), *Financial Markets and Portfolio Management* 35, 353–368, DOI `10.1007/s11408-021-00380-w`.

Preregistration: `research/campaigns/D034_GOLD_OIL_INTRADAY_ABNORMAL_RETURN_MOMENTUM_PREREGISTRATION_2026_09_05.md`
Commit: `3e3166bf08f03bf958de573f98250f98697dc9d6`.

Prepared handoff: `handoff/chatgpt_to_codex/2026/09/05/D034_GOLD_OIL_ABNORMAL_RETURN_MOMENTUM_PREPARED.md`
Commit: `cbcc562de4e33070407d11febaee19d2342a6cea`.

Delivered scanner:
- `D034_GoldOil_AbnormalReturn_Momentum_FeatureLab_v1_00.mq5`
- SHA-256 `842ca596a017229c27857030589c0f5b432e52313364f7f7a27c73890da138fe`
- Guardian OFF / no orders / not MetaEditor-compiled by ChatGPT.

Classification is deliberately `ADAPTATION_CAUSAL_CFD_TRANSFER`, not exact replication. The article specifies dynamic abnormal-return thresholding with `k=2` and source timing parameters, but does not expose a sufficiently explicit causal live-trading lookback `n` for exact transfer. D034 freezes prior 252 completed D1 open-to-close returns before testing; no future data.

Frozen D034 rule:
- XAU/GOLD and WTI/USOIL/XTI only;
- upper abnormal threshold = prior252 mean + 2sd; lower = mean - 2sd;
- current-day cumulative return uses current midpoint versus first midpoint quote of broker/server calendar day;
- GOLD source timing applied to server clock: positive >=17:00, negative >=19:00;
- OIL: positive >=16:00, negative >=19:00;
- first threshold crossing after timing enters in anomaly direction;
- max one trade/day;
- no SL/TP/trailing;
- close at last observed executable quote of same server calendar day;
- spread embedded;
- signal days 2024-01-01 through 2026-06-30.

Because source Strategy 1 has no natural stop, D034 does NOT invent R. Primary outcome is executable bps/percent. Passive diagnostics only: Z60/Z120/Z252, reconstructed RSI14 H1, ATR14 H1/D1, 1h/4h/8h/24h returns, prior-day return, current-day range, D1 SMA20/50/200 distances, MFE/MAE.

Frozen per-market advancement gate: >=40 clean resolved events; mean executable >+15 bps/event; median >0; month-block bootstrap lower >0; both directions positive when n>=10 each; >=2 positive calendar years; no event >20% of positive pooled bps. No same-sample timing/k/lookback/RSI/stop rescue.

Static QA before delivery: braces/parens/brackets balanced; EVENTS header/row 49/49; SUMMARY 12/12; immediate header flush + runtime FileSize QA.

## Immediate execution order
1. Compile `D034_GoldOil_AbnormalReturn_Momentum_FeatureLab_v1_00.mq5`.
2. Run XAUUSD (or GOLD symbol) and the available WTI/USOIL/XTI symbol separately.
3. Tester M1 / `1 minute OHLC`; start about 2022-11-01 or earlier, end at least 2026-07-02; no input changes.
4. Return EVENTS/SUMMARY/RUN_INFO from each market and decide strictly from the preregistered gate.
5. If D034 fails, close it and move to another independent family rather than mining timing or feature thresholds.
6. Keep D032 as sparse confirmed-entry sleeve, not sole challenge engine.
7. Pure Guardian Core v12.01 compile/smoke remains independently required before live replacement.

Continuity rule: after every material milestone, update this handoff in the same work session.