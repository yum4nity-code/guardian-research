# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 STATIC CANDIDATE / D032 DOJI ENTRY CONFIRMED BUT MANAGEMENT UNSOLVED / D030 BROAD FX REJECTED / D030-C1 ETH H4 TRANSPORT CONFIRMATION PREREGISTERED / CURRENT FUNDEDNEXT LIVE AUTO STILL OFF

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
- Scanner QA after D032 v1.00: verify output columns/index bounds, immediate header flush, and runtime output QA before delivery.

## Pure Guardian Core v12.01
Guardian is a strategy-neutral Lego chassis. RSI and Momentum strategy logic are physically removed.

Candidate: `Guardian_Core_Base_v12_01_CANDIDATE.mq5`
SHA-256: `6a74d4187e04a02f9924c48ef34a1f0eb946da0f64d66a4839701154d6ad1176`
Strategy socket: `GuardianCore/Guardian_StrategyRegistry_v1.mqh`
Template: `GuardianCore/Guardian_StrategyModule_TEMPLATE_v1.mqh`

Status remains STATIC PASS only. MetaEditor compile/smoke gates are required before replacing the older live lineage. FundedNext Algo Trading remains OFF.

## Frozen/rejected research
- RSI legacy v11.16.11: rejected.
- D017 Momentum broad: rejected.
- D022 pair reversion M15: rejected.
- D023 London ORB M15 broad: rejected; USDJPY anomaly discovery-only.
- D025/D026 broad exploitation: rejected/quarantined.
- D027 NR7 broad: rejected.
- D028 session momentum: rejected.
- D031 FX Piercing/Dark Cloud D1 broad: not validated.

# D032 — Crypto H1 Bullish Doji Star
Research basis: Moser & Brauneis (2026), IREF 108, 105158, DOI `10.1016/j.iref.2026.105158`.

Frozen underlying signal: Bullish Doji Star H1; strict 144h SMA downtrend; executable LONG first ASK after signal; `1R=2*sample stdev(previous 24 H1 returns)`; source horizon original signal +24h.

## D032-C1 confirmation — PASS
Canonical result: `research/results/D032_C1_DOJI_STAR_H1_CORE_CONFIRMATION_VERDICT_2026_09_05.md`
Commit: `c0ef788f5e16cdb6a402cef9a0e29fa05e7691f2`

PRE2024 core BTC+ETH+DOG clean n=79; mean +133.52bps; median +93.43bps; win 64.56%; mean +0.588R; same-trend control ~+32.13bps; bootstrap lower >0; primary gate 7/7 PASS.

Interpretation: ENTRY EDGE CONFIRMED ON PRE2024 BAR CONFIRMATION / BUILD MANAGEMENT, not production-ready. LINK/XRP transports failed; ADA exploratory negative.

## D032 management / entry attempts
- -1R/+3R/24h management failed confirmation (~+0.118R, bootstrap lower <0).
- Post24 1R runner added ~+0.0045R -> reject.
- 1.5R post24 trail looked better but remains unvalidated.
- RSI(14) M15 continuous diagnostic: no useful monotonic relationship.
- RSI<30 POST2024 failed sample-size/concentration and did not improve MAE. Result commit `635ebddb73237cd4451fc99aaf7e669e000ab45a`.
- 6h reclaim-high delayed entry worsened both paired return and MAE. Result commit `50887f08479b0be9733d3a1de15369a87a3d67f0`.

Keep D032 as a sparse directional sleeve candidate; management/entry localization remains unresolved. Do not keep mining RSI/reclaim thresholds on the same data.

# D030 — Alanazi H4 full-wick Engulfing
Primary source: Ahmed S. Alanazi (2020), *The European Journal of Finance* 26(15), 1484–1505, DOI `10.1080/1351847X.2020.1748679`.

Scanner: `D030_FX_Engulfing_H4_Alanazi_CloseReplication_v1_01.mq5`
SHA-256: `e7748717273afcd4d4477bee5de97ae9ab590c30953ebc546ad71a3f0a7ebb6e`
Preregistration commit: `93fd6808ca10d8303078b9f559bd88de0d7c7a0c`

Frozen source-like rules: H4 full-wick engulfing, no trend filter, next-H4 executable entry, stop 5 pips beyond engulfing candle extreme, TP 1:1, spread embedded, Guardian OFF. Historical swap not included in first-pass summary.

## D030 primary seven-major FX result — REJECT
Canonical result: `research/results/D030_ALANAZI_H4_TARGET_CFD_FIRST_VERDICT_2026_09_05.md`
Result commit: `8eadf40481b9609120b17e8c4bd582c93267e67e`
Frozen signal cutoff <=2026-08-31.

Seven-major pooled:
- n=2,136 completed trades
- mean executable R = -0.0348/trade
- fixed-size total = -2,797.3 pips, -1.31 pips/trade
- only USDJPY (+0.0237R) and USDCHF (+0.0593R) positive
- month-block bootstrap 95% approx [-0.0823,+0.0162]

Broad FX core fails decisively. Do not rescue same sample with trend/RSI/RR/direction tuning.

## User-added D030 transports
These are ADAPTATION / transport diagnostics and do not rescue the FX replication.

- ETHUSD: strongest discovery anomaly. Frozen-window n=225, mean +0.1605R, win 57.33%; LONG +0.1243R, SHORT +0.1991R; yearly means 2024 +0.3260, 2025 +0.0670, 2026 +0.1271; month-block bootstrap 95% approx [+0.0370,+0.2819]. No-gap sensitivity remains positive. This is discovery only because symbol was examined outside the frozen primary FX core.
- BTCUSD: n=218, +0.0524R; bootstrap crosses zero -> do not promote.
- XAUUSD: n=288, +0.0372R overall -> fail. LONG-only +0.1708R versus SHORT -0.0946R is a post-hoc watchlist clue only.
- DOGUSD -0.0859R; LNKUSD -0.0214R; XRPUSD -0.0129R -> no promotion.
- EURJPY +0.0621R; USDCNH -0.0527R -> no promotion.

### ETH cost caveat
D030 embeds spread but not historical swap. Discovery run reports current ETH swap mode points, long=-385, short=-385, triple-rollover day=5. Mean holding ~24.95h, median ~9.86h, ~28% >=24h. A rough current-spec rollover stress materially reduces the apparent +0.1605R edge, so ETH is not production-ready even if the signal is interesting.

## D030-C1 ETH transport confirmation — PREREGISTERED
Preregistration: `research/campaigns/D030_C1_ETHUSD_H4_ENGULFING_TRANSPORT_CONFIRMATION_PREREGISTRATION_2026_09_05.md`
Commit: `495ceda0ab53857ce768cf391c49489a067017dc`

Untouched window: 2019-01-01 through 2023-12-31. Exact D030 v1.01 signal/stop/target rules; no tuning. ETH only.

Frozen primary gate:
1. >=250 completed eligible trades;
2. mean executable R >+0.15R/trade;
3. month-block bootstrap 95% lower bound >0;
4. LONG and SHORT mean R both >0;
5. 2019-2021 and 2022-2023 means both >0;
6. no single event >10% of total positive R.

A PASS remains pre-swap only and must undergo a separately frozen rollover stress before production consideration.

## Immediate execution order
1. For D030-C1, run existing v1.01 scanner on ETHUSD, M1 / `1 minute OHLC`, tester covering 2019-01-01 through at least 2024-01-02; no input changes. Eligibility by signal timestamp <=2023-12-31.
2. Return ETH `EVENTS.csv`, `SUMMARY.csv`, `RUN_INFO.csv`; decide strictly from preregistered C1 gate.
3. Do not pursue broad D030 FX V0 further.
4. XAU LONG-only remains a clue, not validation; do not optimize on the seen 2024-2026 sample.
5. Continue independent higher-frequency strategy research because both D032 and D030-ETH are too sparse/uncertain to be the sole challenge engine.
6. Pure Guardian Core v12.01 compile/smoke remains independently required before live replacement.

Continuity rule: after every material milestone, update this handoff in the same work session.