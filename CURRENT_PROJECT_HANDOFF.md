# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 STATIC CANDIDATE / D032 DOJI ENTRY CONFIRMED BUT MANAGEMENT UNSOLVED / D030 FX+ETH CLOSED REJECTED / D029 TSMOM CLOSED REJECTED / CURRENT FUNDEDNEXT LIVE AUTO STILL OFF

Canonical protocol: `docs/RESEARCH_PROTOCOL.md`.
Historical chronology: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.

## Research standard
- No curve fitting or post-hoc rescues disguised as validation.
- Target materially large recurring edge, roughly >= +0.15R/trade and ideally +0.20R+, before production when a natural stop/R exists.
- When a source has no natural stop, do not invent R post-hoc; validate source metrics first, then freeze separate risk management.
- Guardian is execution/protection infrastructure, not alpha.
- Setup-first: entry evidence -> management -> robustness/costs -> Guardian/prop-firm integration.
- Preserve `EXACT_REPLICATION`, `CLOSE_REPLICATION`, `ADAPTATION` labels.
- Ex-post anomalies require a new preregistered test.
- CFD transfer requires target-feed executable BID/ASK/cost handling.
- Scanner QA after D032 v1.00: output-column counts/index bounds, immediate header flush, runtime output QA.

## Pure Guardian Core v12.01
Candidate: `Guardian_Core_Base_v12_01_CANDIDATE.mq5`
SHA-256: `6a74d4187e04a02f9924c48ef34a1f0eb946da0f64d66a4839701154d6ad1176`
Strategy socket: `GuardianCore/Guardian_StrategyRegistry_v1.mqh`
Template: `GuardianCore/Guardian_StrategyModule_TEMPLATE_v1.mqh`

Guardian is strategy-neutral; RSI/Momentum strategy logic removed. Status remains STATIC PASS only. MetaEditor compile/smoke still required before replacing older live lineage. FundedNext Algo Trading remains OFF.

## Frozen/rejected research
- RSI legacy v11.16.11 raw edge: rejected.
- D017 Momentum broad: rejected.
- D022 pair reversion M15: rejected.
- D023 London ORB M15 broad: rejected; USDJPY anomaly discovery-only.
- D025/D026 broad exploitation: rejected/quarantined.
- D027 NR7 broad: rejected.
- D028 session momentum: rejected.
- D031 FX Piercing/Dark Cloud D1 broad: not validated.
- D030 Alanazi H4 Engulfing: FX broad rejected; ETH 2024-2026 discovery failed preregistered 2019-2023 confirmation. Closed; do not rescue/tune same sample.
- D029 Moskowitz/Ooi/Pedersen TSMOM 12M/1M CFD transfer: full eight-market primary gate rejected. Closed; do not rescue with same-sample feature mining.

# D032 — Crypto H1 Bullish Doji Star
Research basis: Moser & Brauneis (2026), IREF 108, 105158, DOI `10.1016/j.iref.2026.105158`.

Frozen underlying signal: Bullish Doji Star H1, strict 144h SMA downtrend, executable LONG first ASK after signal, `1R = 2*sd(previous 24 H1 returns)`, source reference +24h.

D032-C1 PRE2024 confirmation: **PASS**.
Canonical result: `research/results/D032_C1_DOJI_STAR_H1_CORE_CONFIRMATION_VERDICT_2026_09_05.md`
Commit: `c0ef788f5e16cdb6a402cef9a0e29fa05e7691f2`

Core BTC+ETH+DOG PRE2024: n=79, mean +133.52 bps, median +93.43 bps, win 64.56%, mean +0.588R, same-trend control ~+32.13 bps, Doji-control differential ~+101.38 bps, bootstrap lower >0, primary entry gate 7/7 pass.

Not production-ready. Historical real ticks unavailable on old intervals. LINK/XRP transport failed; ADA exploratory failed.

Management/entry-localization attempts rejected/unresolved: -1R/+3R/24h, post24 1R runner, RSI<30, and 6h reclaim-high. Keep Doji as sparse research sleeve only.

# D030 — Alanazi H4 Engulfing — CLOSED REJECTED
Source: Alanazi (2020), *European Journal of Finance*, DOI `10.1080/1351847X.2020.1748679`.

Seven-major FX pool failed. User-added ETH 2024-2026 looked positive but untouched 2019-2023 confirmation failed: n=321, mean +0.0396R, bootstrap crossed zero, LONG negative, early temporal half negative. Cleaner no-gap subset ~+0.0127R.

Canonical ETH confirmation result: `research/results/D030_C1_ETHUSD_H4_ENGULFING_PRE2024_CONFIRMATION_VERDICT_2026_09_05.md`, commit `28ce836c22edc9c19309c9194e93e3f04e9863ea`.

# D029 — Moskowitz/Ooi/Pedersen TSMOM 12M/1M — CLOSED REJECTED
Primary source: Moskowitz, Ooi & Pedersen (2012), *Journal of Financial Economics* 104, 228–250, DOI `10.1016/j.jfineco.2011.11.003`.

Preregistration: `research/campaigns/D029_TSMOM_12M1M_FEATURELAB_PREREGISTRATION_2026_09_05.md`, commit `1572fa66121ebecb557459eaad7593fa8af5c46e`.
Scanner: `D029_TSMOM_12M1M_FeatureLab_v1_00.mq5`, SHA-256 `9f8538606f22689acc55cb22dffd135e6f723aab0dd25ede5a89563644d1429a`.

Frozen source-like rule: monthly sign of prior 12 completed calendar-month CFD return; LONG positive / SHORT negative; hold one month; executable entry/exit; spread embedded; EWMA ex-ante volatility `delta=60/61`, annualization 261; source-like multiplier `0.40/exante_vol`; historical swap/commission not reconstructed.

Frozen 2018-2023 primary universe: EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD, XAUUSD. XAU history supplied only from 2021 in this scanner.

Canonical full result: `research/results/D029_TSMOM_12M1M_FULL_PRIMARY_VERDICT_2018_2023_2026_09_05.md`
Result commit: `1613b46caa1be8ac9002778fcd58f4dd23f16fcc`

Full primary pool:
- n=540 resolved monthly events;
- pooled mean executable directional return **-6.93 bps/event**;
- pooled mean source-scaled return **+0.0075%/month/event**, essentially flat;
- month-block bootstrap 95% interval roughly **[-1.7%, +1.75%]** monthly, lower bound far below zero;
- 5/8 markets positive source-scaled mean;
- 2018-2020 pooled mean +0.315%, 2021-2023 pooled mean **-0.262%**;
- no positive-market concentration breach.

New missing-market runs:
- USDCAD n=72, mean executable -16.57 bps, source-scaled -0.643%/month;
- XAUUSD n=36 (2021-2023 only), mean executable -94.58 bps, source-scaled -2.341%/month.

Frozen gate: 4/7 pass, 3/7 fail -> **REJECT**. Fails executable mean >0, bootstrap lower >0, and both temporal halves positive. Do not tune 12M/1M with RSI/ATR/SMA/lookback/holding filters on the same 2018-2023 sample.

Crypto secondary adaptations from D029 remain discovery-only: BTC and ETH looked better than FX but their block-bootstrap lower bounds crossed zero; DOG was negative. Any crypto continuation requires separately preregistered 2024-2026 validation and is unlikely to solve challenge-frequency needs because the strategy is monthly.

Feature-lab warning: D1 diagnostics were mostly usable; on several older-feed segments H4 RSI/ATR fields were contaminated/duplicated with D1. H4 diagnostics never affected TSMOM signals. Future feature labs should reconstruct higher-timeframe bars internally or add explicit timeframe QA.

## Immediate execution order
1. D029 and D030 are closed; do not spend more same-sample cycles rescuing them.
2. Keep D032 Doji as a sparse confirmed-entry research sleeve, but management remains unresolved and it cannot be the sole challenge engine.
3. Resume the independent documented-strategy pipeline with priority on materially higher-frequency candidates and enough expected trade count for prop challenges.
4. Any new scanner should continue logging useful context features without letting them silently become post-hoc filters.
5. Pure Guardian Core v12.01 compile/smoke remains independently required before live replacement.

Continuity rule: after every material milestone, update this handoff in the same work session.
