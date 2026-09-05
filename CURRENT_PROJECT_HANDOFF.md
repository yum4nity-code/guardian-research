# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 STATIC CANDIDATE / D032 DOJI ENTRY CONFIRMED BUT MANAGEMENT UNSOLVED / D030+D029+D033 CLOSED REJECTED / D034 GOLD CLOSED REJECTED, OIL UNAVAILABLE / D035 BINANCE->FUNDEDNEXT CRYPTO LEAD-LAG PREREGISTERED+EXPORTER PREPARED / CURRENT FUNDEDNEXT LIVE AUTO STILL OFF

Canonical protocol: `docs/RESEARCH_PROTOCOL.md`.
Historical chronology: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.

## MANDATORY DAILY HOUSEKEEPING — applies to every AI/agent
Every Europe/Paris calendar day with material Guardian work **must** receive an entry/update in `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md` before the agent ends the session or hands off. This applies to ChatGPT, Codex and any future AI. Do not defer it on the assumption that another agent will do it.

Record the work actually done, material decisions/rejections, next safe action, and conservative human-time evidence. If exact active time is not provable, use the ledger's `CONFIRMED SPAN` / `MINIMUM OBSERVED` / `NOT QUANTIFIED` semantics. Unattended backtests/collectors/workers are not human work time. At resume, check whether today's entry exists; if material work has happened and the entry is absent/incomplete, fix it before closing the session.

This requirement is also repeated in root `AGENTS.md` and `README.md` so a fresh agent cannot reasonably miss it.

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

Returned XAUUSD run: 83 clean events, pooled mean executable +1.8925 bps/event, median +8.4451 bps, win 57.83%; LONG +9.6399 bps, SHORT -4.3390 bps; 2024 and 2025 negative, 2026 through June +13.9691 bps; month-cluster bootstrap approximately [-7.95,+12.62] bps/event; frozen GOLD gate 3/7 -> REJECT.

OIL is **untested**, not failed, because the target FundedNext account exposes no suitable WTI/USOIL/XTI symbol.

# D035 — Binance BTC/ETH deleveraging -> FundedNext crypto CFD lead-lag — PREPARED
User selected this cross-venue exotic hypothesis and explicitly discarded the other exotic candidates.

Canonical preregistration:
`research/campaigns/D035_BINANCE_DELEVERAGING_FUNDEDNEXT_CFD_LEADLAG_PREREGISTRATION_2026_09_05.md`
Commit: `050506aff39a321195a70ec79ed0008a2b736d7d`.

Prepared MT5 exporter:
`research/ea/D035_CFD_M1_Exporter_v1_01.mq5`
Commit: `0e8f923d1ae7529af7999f9b6e37970133e0fb19`.
User-delivered/local SHA-256: `2bd349d44845cbe726c154c5f419e2ec36763700dd245f2da6964bcb05342a96`.
Static QA: balanced syntax delimiters, 19 header fields = 19 data fields, header flush + periodic flush. MetaEditor compile not claimed.

Prepared historical analyzer delivered in the ChatGPT session:
`D035_Binance_Deleveraging_LeadLag_v1_00.py`
SHA-256: `fa22fa6a7fe735436b381ef2ec7a58f7aed8e71d526e2b679073a6981dfad133`.
Python syntax compile PASS; synthetic core smoke PASS, including recovery of an injected UTC+2 MT5 server offset. Full behavior is frozen in the preregistration and D035 handoff if the conversation artifact is unavailable to another agent.

Handoff:
`handoff/chatgpt_to_codex/2026/09/05/D035_BINANCE_DELEVERAGING_LEADLAG_PREPARED.md`
Commit: `84a42fd284cd0b4ae9ad0299379884bf856ddf09`.

Frozen source event: BTCUSDT/ETHUSDT USD-M, 5m return and 5m `sum_open_interest` change both negative and <= their strictly-prior rolling 30d 10th percentiles; 30m source cooldown; BTC/ETH events within 5m merged.

Development = 2024-01-01..2025-12-31 UTC with warm-up from 2023-11-01. Reserved confirmation = 2026-01-01..2026-06-30 and must remain untouched unless all development gates pass and a fresh confirmation preregistration exists.

Target measurement: all crypto CFDs available on the target FundedNext account, BTCUSD mandatory for mechanical server->UTC alignment. Primary cross-asset executable SHORT horizon +15m using BID entry / ASK exit; +1/+5/+30/+60/+120m frozen diagnostics. No Guardian/SL/TP/R.

Development requires all 8 frozen gates, including >=80 merged source events, >=2 non-source targets with >=40 events, >=+15bps pooled executable +15m, >=+10bps event-control differential, positive day-cluster bootstrap lower bound, positive +30m persistence, positive BTC-only and ETH-only source branches, <=35% positive-month concentration.

Do not rescue a failed D035 with percentile/horizon/target mining, direction inversion, liquidation/funding/basis/RSI/ATR filters or source-specific thresholds on the inspected 2024-2025 sample.

## Immediate execution order
1. Run D035 exporter in Strategy Tester **M1 / 1 minute OHLC**, 2023-11-01 through 2025-12-31, on **BTCUSD plus every crypto CFD available on the target FundedNext account**. No inputs.
2. Collect/zip every generated `D035_CFD_M1_*.csv`.
3. Run the frozen D035 analyzer in development mode only; do not use `--confirm`.
4. Archive the development verdict and update this handoff the same session.
5. Keep D032 Doji as a sparse confirmed-entry sleeve; do not rescue D030/D029/D033/D034 on inspected samples.
6. Pure Guardian Core v12.01 compile/smoke remains independently required before any live replacement.

Continuity rule: after every material milestone, update this handoff in the same work session.
Daily ledger rule: every Europe/Paris day with material Guardian work must be recorded in `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md` before session end/handoff.