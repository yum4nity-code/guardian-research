# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 STATIC CANDIDATE / D032 DOJI ENTRY CONFIRMED BUT MANAGEMENT UNSOLVED / D030 FX REJECTED / D030-C1 ETH TRANSPORT CONFIRMATION FAILED / CURRENT FUNDEDNEXT LIVE AUTO STILL OFF

Canonical protocol: `docs/RESEARCH_PROTOCOL.md`.
Historical chronology: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.

## Research standard
- No curve fitting or post-hoc rescues disguised as validation.
- Target materially large recurring edge, roughly >= +0.15R/trade and ideally +0.20R+, before production.
- Guardian is execution/protection infrastructure, not alpha.
- Setup-first: entry evidence -> management -> robustness/costs -> Guardian/prop-firm integration.
- Preserve `EXACT_REPLICATION`, `CLOSE_REPLICATION`, `ADAPTATION` labels.
- Ex-post symbol/direction anomalies are discovery only and require a new preregistered test.
- With a source/natural risk, preserve R, MFE_R, MAE_R and first-touch ordering.
- CFD transfer requires target-feed executable BID/ASK/cost handling.
- Scanner QA after D032 v1.00: verify output-column counts/index bounds, immediate header flush and runtime output QA before delivery.

## Pure Guardian Core v12.01
Guardian is a strategy-neutral Lego chassis. RSI and Momentum strategy logic are physically removed.

Candidate: `Guardian_Core_Base_v12_01_CANDIDATE.mq5`
SHA-256: `6a74d4187e04a02f9924c48ef34a1f0eb946da0f64d66a4839701154d6ad1176`
Strategy socket: `GuardianCore/Guardian_StrategyRegistry_v1.mqh`
Template: `GuardianCore/Guardian_StrategyModule_TEMPLATE_v1.mqh`

Status remains STATIC PASS only. MetaEditor compile/smoke gates are required before replacing the older live lineage. FundedNext Algo Trading remains OFF.

## Frozen/rejected research
- RSI legacy v11.16.11 raw edge: rejected.
- D017 Momentum broad: rejected.
- D022 pair reversion M15: rejected.
- D023 London ORB M15 broad: rejected; USDJPY anomaly discovery-only.
- D025/D026 broad exploitation: rejected/quarantined as documented.
- D027 NR7 broad: rejected.
- D028 session momentum: rejected.
- D031 FX Piercing/Dark Cloud D1 broad: not validated.

Do not recycle these as supposedly new strategy ideas without genuinely new evidence.

# D032 — Crypto H1 Bullish Doji Star
Research basis: Moser & Brauneis (2026), IREF 108, 105158, DOI `10.1016/j.iref.2026.105158`.

Frozen underlying signal:
- Bullish Doji Star H1, TA-Lib-default numerical definition reimplemented;
- strict 144-hour SMA downtrend;
- original executable LONG at first ASK after signal;
- source normalization `1R = 2 * sample stdev(previous 24 H1 returns)`;
- source reference horizon = original signal +24h.

D032-C1 PRE2024 confirmation: **PASS**.
Canonical result: `research/results/D032_C1_DOJI_STAR_H1_CORE_CONFIRMATION_VERDICT_2026_09_05.md`
Commit: `c0ef788f5e16cdb6a402cef9a0e29fa05e7691f2`

Core BTC+ETH+DOG PRE2024:
- clean n=79;
- mean executable +24h = +133.52 bps/event;
- median +93.43 bps;
- win rate 64.56%;
- mean +0.588R/event;
- same-trend control ~+32.13 bps;
- month-block bootstrap lower bound >0;
- preregistered entry gate passed 7/7.

Interpretation: entry directional information confirmed on bar-based PRE2024 confirmation, but strategy is not production-ready. Historical real ticks are unavailable on old FundedNext intervals.

Transport LINK/XRP failed; ADA exploratory also negative. Core remains BTC/ETH/DOG.

Management/entry localization attempts:
- -1R/+3R/24h management failed confirmation.
- post24 1R runner rejected.
- 1.5R post24 trail only diagnostic/unvalidated.
- RSI(14) M15 diagnostic showed no monotonic relation; RSI<30 POST2024 failed sample/concentration gates and did not improve MAE.
- 6h reclaim-high delayed entry rejected: paired delta ~-0.391R and MAE worsened.

Conclusion: keep Doji as sparse research sleeve; do not deploy. Entry/risk management unresolved.

# D030 — Alanazi H4 Bullish/Bearish Engulfing
Primary source: Alanazi (2020), *European Journal of Finance* 26(15), 1484–1505, DOI `10.1080/1351847X.2020.1748679`.

Recovered source rule:
- full-wick engulf, not body-only;
- no trend filter;
- next H4 executable open entry;
- stop exactly 5 pips beyond engulfing candle extreme;
- target exactly 1:1;
- spread embedded via BID/ASK in scanner;
- historical swap not reconstructed.

Scanner: `D030_FX_Engulfing_H4_Alanazi_CloseReplication_v1_01.mq5`
Classification: `CLOSE_REPLICATION_CFD_TRANSFER`.

## D030 seven-major FX test — REJECT
Primary seven-major pooled result failed the project gate: about 2,136 trades, mean around -0.035R/trade, fixed-size pip result negative, only 2/7 pairs positive. Do not rescue with same-sample trend/RSI/RR tuning.

User-added diagnostics showed ETHUSD 2024-2026 at about +0.161R/trade with positive bootstrap lower bound, while BTC/XAU/DOG/LNK/XRP did not meet the primary edge standard. ETH therefore spawned a separately preregistered untouched PRE2024 confirmation.

## D030-C1 ETHUSD PRE2024 transport confirmation — FAIL
Preregistration: `research/campaigns/D030_C1_ETHUSD_H4_ENGULFING_TRANSPORT_CONFIRMATION_PREREGISTRATION_2026_09_05.md`
Prereg commit: `495ceda0ab53857ce768cf391c49489a067017dc`
Result: `research/results/D030_C1_ETHUSD_H4_ENGULFING_PRE2024_CONFIRMATION_VERDICT_2026_09_05.md`
Result commit: `28ce836c22edc9c19309c9194e93e3f04e9863ea`

PRE2024 ETH 2019-2023 unchanged-rule result:
- completed n=321;
- win rate 50.779%;
- mean executable result **+0.039619R/trade**;
- total scanner pip result -57,603;
- LONG n=136 mean **-0.025722R**;
- SHORT n=185 mean **+0.087654R**;
- 2019-2021 mean **-0.002493R**;
- 2022-2023 mean **+0.074753R**;
- month-block bootstrap 95% interval approx **[-0.0845R, +0.1676R]**;
- largest positive event only ~2.86% of total positive R.

Frozen gate: sample-size and concentration pass; +0.15R mean, bootstrap lower>0, both-directions-positive and both-halves-positive all fail. **2/6 gates pass => REJECT ETH transport confirmation.**

Data-quality diagnostic: 51/321 events had post-entry feed-gap flags. No-gap subset n=270 mean only ~+0.01268R, so cleaner data do not rescue the result. Historical swap stress is unnecessary because the pre-swap confirmation already fails.

Decision lock: do not tune ETH trend, direction, RR, candle size, sessions or stop distance on the same PRE2024 confirmation data.

## Immediate execution order
1. D030/ETH confirmation is closed and rejected in exact form.
2. Keep D032 Doji as confirmed-entry research sleeve but do not force more same-family threshold mining.
3. Move to the next independent documented candidate rather than rescuing D030.
4. Prefer a candidate with enough event frequency for prop-challenge use.
5. Pure Guardian Core v12.01 compile/smoke remains independently required before live replacement.

Continuity rule: after every material milestone, update this handoff in the same work session.
