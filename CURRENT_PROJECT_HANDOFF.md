# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 STATIC CANDIDATE / D032 DOJI STAR CORE ENTRY CONFIRMED / D032 MANAGEMENT AND ENTRY LOCATION NOT YET SOLVED / D032-E1 RSI DIAGNOSTIC COMPLETE / D032-E2 RSI<30 FILTER FAILED / CURRENT FUNDEDNEXT LIVE AUTO STILL OFF

Read this first. Historical chronology/time ledger: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.
Canonical research rules: `docs/RESEARCH_PROTOCOL.md`.

## Research standard
- No curve fitting or post-hoc threshold edits disguised as fixes.
- Target a materially large recurring edge, roughly >= +0.15R/trade and ideally +0.20R+, before production.
- Guardian is execution/protection infrastructure, not alpha.
- Setup-first: establish entry information first, then management, then Guardian/prop-firm integration.
- Preserve exact/close/adaptation labels.
- Ex-post anomalies may spawn fresh preregistered tests but are not retroactive validation.
- With a natural/source risk, export R, MFE_R, MAE_R and first-touch ordering.
- CFD transfer requires reproduction on target CFD feed with executable bid/ask and costs.
- Future scanner QA after D032 v1.00 bug: header/data column counts, array bounds, immediate header flush, runtime output QA; structural brace checks alone are insufficient.

## Pure Guardian Core v12.01
Guardian is now a strategy-neutral Lego chassis. RSI and Momentum strategy logic are physically removed from the candidate.

Candidate: `Guardian_Core_Base_v12_01_CANDIDATE.mq5`
SHA-256: `6a74d4187e04a02f9924c48ef34a1f0eb946da0f64d66a4839701154d6ad1176`
Strategy socket: `GuardianCore/Guardian_StrategyRegistry_v1.mqh`
Template: `GuardianCore/Guardian_StrategyModule_TEMPLATE_v1.mqh`

Status remains STATIC PASS only. MetaEditor compile/smoke gates are still required before replacing the older live lineage. FundedNext Algo Trading remains OFF.

## Frozen/rejected research
- RSI legacy v11.16.11 raw entry edge: rejected.
- D017 Momentum broad: rejected.
- D022 pair reversion M15: rejected.
- D023 London ORB M15 broad: rejected; USDJPY anomaly discovery-only.
- D025/D026 broad exploitation: rejected/quarantined as previously documented.
- D027 NR7 broad: rejected.
- D028 session momentum: rejected.
- D031 FX Piercing/Dark Cloud D1 broad: not validated.

Do not recycle these as supposedly new strategy ideas without new evidence.

# D032 — Crypto H1 Bullish Doji Star
Research basis: Moser & Brauneis (2026), IREF 108, 105158, DOI 10.1016/j.iref.2026.105158.

Frozen entry:
- Bullish Doji Star H1, TA-Lib-default numerical definition reimplemented;
- strict 144-hour SMA downtrend, `MA[t-6] > ... > MA[t]`;
- executable LONG at first ASK after signal;
- source risk normalization `1R = 2 * sample stdev(previous 24 H1 returns)`;
- source/primary reference horizon = +24h.

## D032 discovery 2024-2026
Core BTC/ETH/DOG discovery showed a strong Doji candidate. Inverted Hammer and Hanging Man were buried.

Discovery clean core Doji n=77, mean executable +24h about +111.6 bps, mean about +0.726R. This was discovery only and led to preregistered C1 confirmation.

## D032-C1 pre-2024 core confirmation — PASS
Canonical result: `research/results/D032_C1_DOJI_STAR_H1_CORE_CONFIRMATION_VERDICT_2026_09_05.md`
Commit: `c0ef788f5e16cdb6a402cef9a0e29fa05e7691f2`

Historical real ticks were unavailable, so pre-2024 runs used M1 + `1 minute OHLC`. This is acceptable as supporting confirmation of the +24h endpoint, but not authoritative for exact intraminute first-touch management.

Core BTC+ETH+DOG:
- clean n=79;
- mean executable +24h = +133.52 bps/event;
- median = +93.43 bps;
- win rate = 64.56%;
- mean source-risk-normalized +24h = +0.588R/event;
- same-trend control mean ~+32.13 bps;
- Doji-control differential ~+101.38 bps;
- month-block bootstrap lower bound remained >0;
- preregistered primary gate passed 7/7.

Interpretation: ENTRY EDGE CONFIRMED ON PRE-2024 BAR CONFIRMATION / BUILD MANAGEMENT. Not yet a production strategy.

## D032 transport
- LINK/LNK pre-2024 transport: FAIL, mean ~-118.7 bps, -0.690R.
- XRP pre-2024 transport: FAIL, mean ~-200.1 bps, -0.535R.
- ADA was unregistered exploratory diagnostic and also negative.

Conclusion: Doji is not a universal crypto effect. Core remains BTC/ETH/DOG.

## Management work
The originally frozen `-1R / +3R / 24h` management failed confirmation: pooled core ~+0.118R and bootstrap lower bound <0. Do not adopt it.

D032-M1 tested a post-24h runner concept on PRE2024:
- +24h negative/flat => close;
- +24h positive => BE floor + 1R trail to +48h.

Primary 1R runner added essentially nothing pooled (~+0.0045R incremental) and is rejected.

A 1.5R post-24h trail was only a diagnostic and looked better PRE2024 (~+0.109R incremental pooled), but is not validated.

Pre24 path diagnostics showed that many future winners travel deeply negative before the +24h payoff. A -1R stop was clearly too tight. A -3.5R catastrophe-stop clue looked less destructive, but this is not yet validated and, when risk is normalized to such a wide stop, the apparent edge becomes much less spectacular.

Key interpretation: the Doji has confirmed directional information, but the exact immediate entry price may be poor. Management/entry-location remains unresolved.

# D032-E1 — RSI(14) M15 diagnostic PRE2024
Result: `research/results/D032_E1_RSI14_M15_DIAGNOSTIC_PRE2024_2026_09_05.md`
Commit: `6a312ff1bc9232c8b029282301211c3d858f0145`

Purpose: record RSI(14) M15 without filtering, to see whether oversold context explains entry quality.

Primary clean core remains n=79. There is no monotonic continuous RSI relationship: RSI correlations versus +24h R/bps, MAE and MFE are near zero.

The standard oversold subset RSI<30 looked attractive on PRE2024 but was highly outlier-sensitive and did not clearly improve MAE. This led to preregistered POST2024 validation rather than threshold tuning.

# D032-E2 — RSI(14) M15 <30 POST2024 conditional validation — FAIL
Preregistration: `research/campaigns/D032_E2_RSI14_M15_LT30_POST2024_VALIDATION_PREREGISTRATION_2026_09_05.md`
Preregistration commit: `19d32093cd804005852f7d6df4633d5001a45a2f`
Result: `research/results/D032_E2_RSI14_M15_LT30_POST2024_VERDICT_2026_09_05.md`
Result commit: `635ebddb73237cd4451fc99aaf7e669e000ab45a`

Frozen primary core BTC/ETH/DOG POST2024:
- 77 clean Doji events;
- only 5 clean fresh-M15 RSI<30 events, below the preregistered minimum 8;
- pooled RSI<30 mean +176.21 bps, median +112.41 bps, mean +1.359R, win rate 60%;
- BTC n=2 +3.882R mean, ETH n=2 +0.158R, DOG n=1 -1.282R;
- one BTC event at +6.879R contributes ~82.5% of total positive pooled RSI<30 R, violating the <=60% concentration gate;
- contemporaneous unfiltered clean-core mean = ~+0.731R.

Preregistered gate fails on sample size and concentration. Under the interpretation lock: **discard RSI<30 as an entry filter and do not tune neighboring RSI thresholds on POST2024.**

MAE also does not improve: RSI<30 winners median pre24 MAE ~-1.38R versus ~-0.84R for all contemporaneous clean-core winners. Therefore RSI<30 does not solve the stop-distance / entry-localization problem.

Transport diagnostics do not rescue it: LNK n=3 mean -0.023R; XRP n=2 mean ~+0.004R with very poor MAE.

## Immediate execution order
1. Keep D032 underlying Doji entry edge as confirmed, but do not deploy it yet.
2. Stop RSI-threshold work on this dataset. No 25/29/30/32/35 mining.
3. Next D032 research question is execution timing / entry localization while freezing the Doji signal itself; avoid solving this merely by widening the stop.
4. In parallel, continue the independent higher-frequency strategy search because D032 remains too sparse to be the sole prop-challenge engine.
5. D033 commodity setup work remains the next independent family unless a better documented high-frequency candidate is selected.
6. Pure Guardian Core v12.01 compile/smoke remains independently required before any live replacement.

Continuity rule: after every material milestone, update this handoff in the same work session.
