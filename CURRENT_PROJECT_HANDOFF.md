# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 STATIC CANDIDATE / D032 DOJI ENTRY CONFIRMED BUT MANAGEMENT UNSOLVED / D030 FX+ETH CLOSED REJECTED / D029 TSMOM PARTIAL: 6/8 PRIMARY MARKETS RUN, BTC+ETH DISCOVERY CLUES / CURRENT FUNDEDNEXT LIVE AUTO STILL OFF

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

# D029 — Moskowitz/Ooi/Pedersen TSMOM 12M/1M + feature lab — PARTIAL
Primary source: Moskowitz, Ooi & Pedersen (2012), *Journal of Financial Economics* 104, 228–250, DOI `10.1016/j.jfineco.2011.11.003`.

Preregistration: `research/campaigns/D029_TSMOM_12M1M_FEATURELAB_PREREGISTRATION_2026_09_05.md`, commit `1572fa66121ebecb557459eaad7593fa8af5c46e`.
Prepared handoff: `handoff/chatgpt_to_codex/2026/09/05/D029_TSMOM_12M1M_FEATURELAB_PREPARED.md`, commit `d4c79d27b3d2ef39384d5a479f638800fd1ade9b`.
Scanner: `D029_TSMOM_12M1M_FeatureLab_v1_00.mq5`, SHA-256 `9f8538606f22689acc55cb22dffd135e6f723aab0dd25ede5a89563644d1429a`.

Frozen rule: monthly sign of own prior 12 completed calendar-month CFD return; LONG positive / SHORT negative; hold one month; executable quote entry/exit; spread embedded; EWMA ex-ante vol `delta=60/61`, annualization 261; source-like multiplier `0.40/exante_vol`; no historical swap/commission in first pass.

Frozen development window 2018-2023; 2024-2026 reserved.

Frozen primary 8-market universe: EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD, XAUUSD. Crypto BTC/ETH/DOG are secondary adaptations.

## D029 supplied batch 2026-09-05
Received correct primary runs for EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD; also USDCNH exploratory plus BTCUSD, ETHUSD, DOGUSD. **USDCAD and XAUUSD are missing**, so full preregistered verdict remains open.

Partial six-primary FX pool:
- 432 resolved events;
- pooled mean executable +1.98 bps/event;
- pooled mean source-scaled +0.312%/month;
- 2018-2020 +0.455%, 2021-2023 +0.168%;
- five of six available primaries positive source-scaled mean; USDCHF negative;
- equal-weight monthly six-market portfolio annualized mean ~3.74%, annualized vol ~27.50%, Sharpe ~0.136;
- 6-month block-bootstrap 95% interval of monthly mean ~[-1.10%, +1.86%], so critical lower-bound gate currently fails.

Partial result: `research/results/D029_TSMOM_12M1M_FEATURELAB_PARTIAL_2018_2023_2026_09_05.md`, commit `e2e28fb9c05f7cf7e0401c206dacea0500543c1e`.

Crypto discovery:
- BTC n=66, mean +454.7 bps/month, source-scaled +2.858%/month, but median ~flat and block-bootstrap lower <0; 2019 and 2023 weak/negative.
- ETH n=62, mean +425.9 bps/month, source-scaled +1.779%/month, median +1.248%, but block-bootstrap lower <0; 2020 and 2023 negative.
- BTC+ETH overlap equal-weight annualized Sharpe ~0.70 but block-bootstrap lower still <0.
- DOG n=15, source-scaled mean negative.

BTC/ETH are interesting adaptation clues only; do not call confirmed. A 2024-2026 confirmation must be separately frozen before inspection if pursued.

Feature-lab warning: D1 diagnostics are mostly usable and show no strong consistent cross-market predictive relationship. On several older-feed symbol segments H4 RSI/ATR are exactly identical to D1 for long blocks, indicating tester/history timeframe contamination. Do NOT use v1.00 H4 feature fields for conclusions. H4 features never affected TSMOM signals/results. Future scanners should reconstruct H4 internally or add explicit timeframe QA.

## Immediate execution order
1. Run **USDCAD and XAUUSD only** with the same D029 v1.00 scanner, M1 / `1 minute OHLC`, 2017 warm-up through 2024-01-02; signal window remains hard-locked 2018-2023.
2. After those two runs, finalize the frozen 8-market D029 source-like gate. Do not substitute USDCNH for USDCAD.
3. If broad D029 fails, close without feature-threshold mining.
4. BTC/ETH may separately undergo preregistered 2024-2026 adaptation confirmation, but TSMOM remains too slow to be sole challenge engine.
5. Keep D032 Doji as sparse confirmed-entry research sleeve; do not force same-family threshold mining.
6. Pure Guardian Core v12.01 compile/smoke remains independently required before live replacement.

Continuity rule: after every material milestone, update this handoff in the same work session.
