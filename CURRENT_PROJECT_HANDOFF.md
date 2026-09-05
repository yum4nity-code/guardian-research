# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 STATIC CANDIDATE / D032 DOJI STAR CORE ENTRY CONFIRMED / D032-E2 RSI<30 FAILED / D032-E3 RECLAIM-HIGH ENTRY FIX REJECTED / ENTRY-RISK MANAGEMENT STILL UNSOLVED / CURRENT FUNDEDNEXT LIVE AUTO STILL OFF

Read this first. Historical chronology/time ledger: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.
Canonical research rules: `docs/RESEARCH_PROTOCOL.md`.

## Research standard
- No curve fitting or post-hoc threshold edits disguised as fixes.
- Target materially large recurring edge, roughly >= +0.15R/trade and ideally +0.20R+, before production.
- Guardian is execution/protection infrastructure, not alpha.
- Setup-first: establish entry information first, then management, then Guardian/prop-firm integration.
- Preserve `EXACT_REPLICATION`, `CLOSE_REPLICATION`, `ADAPTATION` labels.
- Ex-post anomalies may spawn fresh preregistered tests but are not retroactive validation.
- With a natural/source risk, export R, MFE_R, MAE_R and first-touch ordering.
- CFD transfer requires reproduction on target CFD feed with executable bid/ask and costs.
- Scanner QA after D032 v1.00 bug: verify header/data column counts, array/index bounds, immediate header flush, and runtime output QA before delivery.

## Pure Guardian Core v12.01
Guardian is a strategy-neutral Lego chassis. RSI and Momentum strategy logic are physically removed from the candidate.

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

Frozen underlying signal:
- Bullish Doji Star H1, TA-Lib-default numerical definition reimplemented;
- strict 144-hour SMA downtrend, `MA[t-6] > ... > MA[t]`;
- original executable baseline LONG at first ASK after signal;
- source risk normalization `1R = 2 * sample stdev(previous 24 H1 returns)`;
- source/primary reference horizon = original signal +24h.

## D032 discovery and confirmation
Discovery 2024-2026 core BTC/ETH/DOG: clean n=77, mean executable +24h about +111.6 bps, about +0.726R. Inverted Hammer and Hanging Man were buried.

D032-C1 pre-2024 core confirmation: **PASS**.
Canonical result: `research/results/D032_C1_DOJI_STAR_H1_CORE_CONFIRMATION_VERDICT_2026_09_05.md`
Commit: `c0ef788f5e16cdb6a402cef9a0e29fa05e7691f2`

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

Historical real ticks were unavailable; confirmation used M1 + `1 minute OHLC`. Interpretation: **ENTRY EDGE CONFIRMED ON PRE-2024 BAR CONFIRMATION / BUILD MANAGEMENT**, not production-ready.

## D032 transport
- LINK/LNK pre-2024 transport: FAIL, mean ~-118.7 bps, -0.690R.
- XRP pre-2024 transport: FAIL, mean ~-200.1 bps, -0.535R.
- ADA unregistered exploratory diagnostic also negative.

Conclusion: Doji is not a universal crypto effect. Primary core remains BTC/ETH/DOG.

## Management work
- Frozen `-1R / +3R / 24h` management failed confirmation: pooled core ~+0.118R, bootstrap lower bound <0. Do not adopt.
- D032-M1 post-24h 1R runner added essentially nothing pooled (~+0.0045R incremental) and is rejected.
- 1.5R post-24h trail looked better PRE2024 (~+0.109R incremental) but was diagnostic only and is not validated.
- Immediate-entry path diagnostics show many future winners travel deeply negative before +24h. -1R is clearly too tight. A -3.5R catastrophe-stop clue looked less destructive but makes stop-normalized expectancy much less attractive.

Key interpretation: D032 has confirmed directional information, but **entry localization / risk management remains the main unresolved problem**.

## D032-E1 RSI(14) M15 diagnostic PRE2024
Result: `research/results/D032_E1_RSI14_M15_DIAGNOSTIC_PRE2024_2026_09_05.md`
Commit: `6a312ff1bc9232c8b029282301211c3d858f0145`

No monotonic continuous RSI relationship. RSI<30 looked attractive on PRE2024 but was highly outlier-sensitive and did not clearly improve MAE.

## D032-E2 RSI(14) M15 <30 POST2024 validation — FAIL
Preregistration: `research/campaigns/D032_E2_RSI14_M15_LT30_POST2024_VALIDATION_PREREGISTRATION_2026_09_05.md`
Result: `research/results/D032_E2_RSI14_M15_LT30_POST2024_VERDICT_2026_09_05.md`
Result commit: `635ebddb73237cd4451fc99aaf7e669e000ab45a`

Core POST2024:
- 77 clean Doji events;
- only 5 clean fresh-M15 RSI<30 events, below minimum 8;
- pooled RSI<30 mean +176.21 bps, median +112.41 bps, mean +1.359R, win rate 60%;
- one BTC event at +6.879R contributes ~82.5% of positive pooled RSI<30 R, violating <=60% concentration gate;
- RSI<30 winner median MAE ~-1.38R versus ~-0.84R for all contemporaneous clean-core winners.

Decision lock: **discard RSI<30 as an entry filter; do not tune neighboring RSI thresholds on the same data.**

## D032-E3 reclaim-high delayed entry — REJECT
Preregistration: `research/campaigns/D032_E3_DOJI_RECLAIM_HIGH_ENTRY_DIAGNOSTIC_PREREGISTRATION_2026_09_05.md`
Preregistration commit: `d3c5bbfb80e1bcc231207b7c1215419fc2c55b43`
Result: `research/results/D032_E3_RECLAIM_HIGH_POST2024_EARLY_REJECTION_2026_09_05.md`
Result commit: `50887f08479b0be9733d3a1de15369a87a3d67f0`

Frozen rule: wait up to 6h after the Doji for first `BID >= closed Doji high`, then enter at contemporaneous ASK; compare against immediate ASK entry at the same original +24h endpoint.

User supplied POST2024 runs (2024-01-01 through 2026-06-24) on BTC/ETH/DOG plus LNK/XRP diagnostics.

Core clean reclaim-triggered n=59:
- BTC 23, ETH 25, DOG 11;
- pooled reclaim mean +0.679R, median +50.09 bps, win rate 64.4%;
- all 3 core symbols positive raw reclaim mean R;
- concentration fine: largest positive event ~8.5% of total positive reclaim R.

But the timing rule makes execution materially worse versus immediate entry:
- mean paired reclaim-minus-baseline delta = **-0.391R/event**;
- median paired delta = **-0.349R/event**;
- BTC delta -0.387R, ETH -0.366R, DOG -0.458R.

Most importantly, the intended MAE improvement fails in the opposite direction:
- paired immediate-entry median MAE = **-1.017R**;
- reclaim-entry median MAE = **-1.364R**;
- change = **-0.347R**, i.e. about 0.35R MORE adverse instead of >=0.25R less adverse;
- median MAE worsens on BTC, ETH and DOG individually.

Decision: **reject reclaim-high as the entry-localization fix.** Do not retune the same sample to 1h/3h/12h windows or nearby trigger levels. Positive raw reclaim return is inherited from the underlying Doji edge; the delayed trigger itself destroys entry quality.

PRE2024 E3 rescue runs are not required: POST2024 already fails the candidate's central mechanism on all three core markets, so cheap-fail and move on.

## Immediate execution order
1. Keep the underlying D032 Doji directional edge as confirmed, but do not deploy it yet.
2. Stop RSI-threshold work and reclaim-high timing work on the same historical data.
3. For D032, next work must be structurally different: either an execution concept capable of entering LOWER rather than higher after the Doji, or immediate entry with separately frozen risk management. Do not just widen the stop without measuring stop-normalized expectancy.
4. Continue independent higher-frequency strategy research in parallel; D032 remains too sparse to be the sole prop-challenge engine.
5. D033 commodity setup work remains the next independent family unless replaced by a better documented higher-frequency candidate.
6. Pure Guardian Core v12.01 compile/smoke remains independently required before any live replacement.

Continuity rule: after every material milestone, update this handoff in the same work session.
