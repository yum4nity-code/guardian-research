# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 STATIC CANDIDATE / D032 DOJI ENTRY CONFIRMED BUT MANAGEMENT UNSOLVED / D030 FX+ETH CLOSED REJECTED / D029 TSMOM CLOSED REJECTED / D033 EURUSD M5 DOUBLE TOP-BOTTOM M2 PREPARED / CURRENT FUNDEDNEXT LIVE AUTO STILL OFF

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

Canonical full result: `research/results/D029_TSMOM_12M1M_FULL_PRIMARY_VERDICT_2018_2023_2026_09_05.md`
Result commit: `1613b46caa1be8ac9002778fcd58f4dd23f16fcc`

Full primary pool: n=540, pooled mean executable -6.93 bps/event, pooled mean source-scaled +0.0075%/month/event, month-block bootstrap roughly [-1.7%, +1.75%], 2021-2023 pooled mean negative. Frozen gate 4/7 -> **REJECT**. No same-sample RSI/ATR/SMA/lookback rescue.

# D033 — EURUSD M5 Double Top / Double Bottom, source M2 — PREPARED
Primary source: Ben Omrane & Van Oppens (2006), *Empirical Economics* 30(4), 947–971, DOI `10.1007/s00181-005-0007-8`.

Preregistration: `research/campaigns/D033_EURUSD_M5_DOUBLE_TOP_BOTTOM_M2_FEATURELAB_PREREGISTRATION_2026_09_05.md`
Preregistration commit: `1980970f343aa9d9536fea058b9dbab09b1337a1`
Prepared handoff: `handoff/chatgpt_to_codex/2026/09/05/D033_EURUSD_M5_DOUBLE_TOP_BOTTOM_M2_PREPARED.md`
Prepared handoff commit: `71ac4f7374f84e2cbb532586e39a4cf004e8f55e`

Delivered scanner:
- `D033_EURUSD_M5_DoubleTopBottom_M2_FeatureLab_v1_00.mq5`
- SHA-256 `4ad46396f14a71e2b1f30f63bd089cdf9d4a043568d80a068fb99199fc4d647c`
- Guardian OFF / no orders / not MetaEditor-compiled by ChatGPT.

Frozen primary arm:
- EURUSD only;
- five-minute midpoint bars reconstructed internally from tester BID/ASK;
- 36-observation rolling window;
- source M2 extrema method: high curve maxima, low curve minima;
- Gaussian Nadaraya-Watson smoothing with Silverman bandwidth x0.20;
- projected extrema +/-1 observation and alternating sequence;
- source DT/DB quantitative definitions, exact equal-extrema equation with one MT5 point numerical tolerance only;
- source final journal pre-trend condition >=2/3*h;
- DT SHORT / DB LONG at pattern completion;
- source TP 0.50h, SL 0.20h, timeout `tf+(tf-td)`;
- executable BID/ASK spread embedded.

Development signal window: 2024-01-01 through 2026-06-30 23:59. Pre-2024 remains reserved for confirmation.

Passive feature lab only: internally computed RSI14 M5/M15/H1, ATR14 M5, 15m/1h/4h/24h returns, SMA20/50/200 distances, RV/ranges, time-of-day, pattern geometry, MFE/MAE. Features never filter v1.00.

Frozen advancement gate on clean M2 DT+DB EURUSD: >=250 resolved; mean >+0.15R; median R >0; month-block bootstrap lower >0; DT and DB both positive; >=2 of 2024/2025/2026 positive; no single event >10% of positive pooled R.

Static QA before delivery: braces/parens/brackets balanced; EVENTS header/row 61/61 columns; SUMMARY 14 columns; immediate header flush + runtime FileSize QA. If event count is unexpectedly near zero, audit implementation/data precision first; do not silently widen source equality tolerance after results.

## Immediate execution order
1. Compile `D033_EURUSD_M5_DoubleTopBottom_M2_FeatureLab_v1_00.mq5`.
2. Run **EURUSD only** first: M1 / `1 minute OHLC`, tester start around 2023-12-15, end at least 2026-07-03; no input changes.
3. Return `EVENTS.csv`, `SUMMARY.csv`, `RUN_INFO.csv`.
4. Decide D033 strictly against the frozen M2 gate. Do not mine the passive feature fields on 2024-2026.
5. If D033 passes, freeze exact rule and confirm on untouched pre-2024 history before any Guardian integration.
6. Keep D032 Doji as sparse confirmed-entry sleeve, not sole challenge engine.
7. Pure Guardian Core v12.01 compile/smoke remains independently required before live replacement.

Continuity rule: after every material milestone, update this handoff in the same work session.
