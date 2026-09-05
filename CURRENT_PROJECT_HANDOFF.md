# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 STATIC CANDIDATE / D032 DOJI ENTRY CONFIRMED BUT MANAGEMENT UNSOLVED / D030 FX+ETH CLOSED REJECTED / D029 TSMOM 12M1M FEATURE-LAB PREPARED / CURRENT FUNDEDNEXT LIVE AUTO STILL OFF

Canonical protocol: `docs/RESEARCH_PROTOCOL.md`.
Historical chronology: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.

## Research standard
- No curve fitting or post-hoc rescues disguised as validation.
- Target materially large recurring edge, roughly >= +0.15R/trade and ideally +0.20R+, before production when a natural stop/R exists.
- When a source has no natural stop, do not invent R post-hoc; validate the source metric first, then freeze a separate risk-management study.
- Guardian is execution/protection infrastructure, not alpha.
- Setup-first: entry evidence -> management -> robustness/costs -> Guardian/prop-firm integration.
- Preserve `EXACT_REPLICATION`, `CLOSE_REPLICATION`, `ADAPTATION` labels.
- Ex-post symbol/direction anomalies are discovery only and require a new preregistered test.
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
- Doji-control differential ~+101.38 bps;
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

# D030 — Alanazi H4 Bullish/Bearish Engulfing — CLOSED REJECTED
Primary source: Alanazi (2020), *European Journal of Finance* 26(15), 1484–1505, DOI `10.1080/1351847X.2020.1748679`.

Recovered exact-form close-replication rule: full-wick engulf, no trend filter, next-H4 executable entry, stop 5 pips beyond engulfing-candle extreme, target 1:1.

Seven-major FX pooled test failed. User-added ETH 2024-2026 discovery looked positive but preregistered untouched 2019-2023 confirmation failed: n=321, mean +0.039619R, bootstrap crossed zero, LONG negative, early half negative. Cleaner no-gap subset ~+0.01268R. Do not rescue/tune same sample.

Canonical ETH confirmation result:
`research/results/D030_C1_ETHUSD_H4_ENGULFING_PRE2024_CONFIRMATION_VERDICT_2026_09_05.md`
Commit `28ce836c22edc9c19309c9194e93e3f04e9863ea`.

# D029 — Moskowitz/Ooi/Pedersen TSMOM 12M/1M + feature lab — PREPARED
Primary source: Moskowitz, Ooi & Pedersen (2012), *Journal of Financial Economics* 104, 228–250, DOI `10.1016/j.jfineco.2011.11.003`.

Preregistration:
`research/campaigns/D029_TSMOM_12M1M_FEATURELAB_PREREGISTRATION_2026_09_05.md`
Commit `1572fa66121ebecb557459eaad7593fa8af5c46e`.

Prepared handoff:
`handoff/chatgpt_to_codex/2026/09/05/D029_TSMOM_12M1M_FEATURELAB_PREPARED.md`
Commit `d4c79d27b3d2ef39384d5a479f638800fd1ade9b`.

Delivered scanner:
- `D029_TSMOM_12M1M_FeatureLab_v1_00.mq5`
- SHA-256 `9f8538606f22689acc55cb22dffd135e6f723aab0dd25ede5a89563644d1429a`
- Guardian OFF / no orders.

Frozen source-like rule:
- monthly signal;
- sign of own prior 12 completed calendar-month CFD return;
- LONG positive / SHORT negative;
- hold one calendar month;
- first executable quote entry/exit;
- spread embedded;
- EWMA ex-ante daily volatility with `delta=60/61`, annualization 261;
- source-like multiplier `0.40/exante_vol`;
- historical swap/commission not reconstructed in first pass.

Frozen development signal window: **2018-01-01 through 2023-12-31**. 2024-2026 is reserved for validation if development is interesting.

Primary recommended source-like CFD universe:
EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD, XAUUSD.
Crypto BTCUSD/ETHUSD/DOGUSD are secondary adaptation diagnostics only.

Feature lab fields are logged but NEVER filter signals in D029: RSI14 D1/H4, ATR14 D1/H4, 5/20/60/120/252d returns, RV20/RV60, SMA20/50/200 distances, z20, 252d range position, previous-month range, MFE/MAE.

Static QA before delivery:
- 729 lines;
- braces/parens/brackets balanced;
- EVENTS header/row = 40 data columns;
- SUMMARY header/row = 15;
- direct FileWrite headers + immediate flush + runtime FileSize QA;
- MetaEditor compilation NOT claimed by ChatGPT.

## Immediate execution order
1. Compile `D029_TSMOM_12M1M_FeatureLab_v1_00.mq5`.
2. First batch: EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD, XAUUSD. BTCUSD/ETHUSD/DOGUSD optional secondary diagnostics.
3. Tester: M1 / `1 minute OHLC`; start preferably 2017-01-01 or earliest available history to warm up the 12m signal/EWMA; run through at least 2024-01-02. Signal eligibility is hard-locked to 2018-2023.
4. Return `EVENTS.csv`, `SUMMARY.csv`, `RUN_INFO.csv` for each symbol.
5. Evaluate source-like transfer first. Do not mine RSI/SMA/ATR thresholds on 2018-2023; feature relationships can only spawn a separately frozen 2024-2026 validation.
6. Keep D032 Doji as sparse confirmed-entry sleeve but do not force more same-family threshold mining.
7. Pure Guardian Core v12.01 compile/smoke remains independently required before live replacement.

Continuity rule: after every material milestone, update this handoff in the same work session.
