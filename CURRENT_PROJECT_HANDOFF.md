# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-06 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 STATIC CANDIDATE / D032 DOJI ENTRY CONFIRMED BUT MANAGEMENT UNSOLVED / D029+D030+D033+D034 GOLD+D035 PRIMARY CLOSED REJECTED / D035-E1 RUNNING/PREPARED / CROSS-STRATEGY EDGE-DECAY AUTOPSY COMPLETE / BLIND NEW-FAMILY HUNT PAUSED AFTER E1 / CURRENT FUNDEDNEXT LIVE AUTO STILL OFF

Canonical protocol: `docs/RESEARCH_PROTOCOL.md`.
Historical chronology: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.
Cross-strategy autopsy: `research/results/CROSS_STRATEGY_EDGE_DECAY_AUTOPSY_2026_09_06.md`.

## MANDATORY DAILY HOUSEKEEPING — applies to every AI/agent
Every Europe/Paris calendar day with material Guardian work **must** receive an entry/update in `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md` before the agent ends the session or hands off. This applies to ChatGPT, Codex and any future AI. Do not defer it on the assumption that another agent will do it.

Record the work actually done, material decisions/rejections, next safe action, and conservative human-time evidence. If exact active time is not provable, use the ledger's `CONFIRMED SPAN` / `MINIMUM OBSERVED` / `NOT QUANTIFIED` semantics. Unattended backtests/collectors/workers are not human work time. At resume, check whether today's entry exists; if material work has happened and the entry is absent/incomplete, fix it before closing the session.

This requirement is also repeated in root `AGENTS.md` and `README.md`.

## Research standard
- No curve fitting or post-hoc rescues disguised as validation.
- Target materially large recurring edge, roughly >= +0.15R/trade and ideally +0.20R+, before production when a natural stop/R exists.
- IMPORTANT after the 2026-09-06 autopsy: keep >=~+0.15R as the **Tier-A standalone-engine** preference, but do not use it as the only possible success class. Future preregistrations may prospectively define a **Tier-B portfolio sleeve** class around roughly +0.07R to +0.10R net/trade only when bootstrap, independent time-block stability, full costs, frequency and portfolio-correlation gates are also satisfied. This is prospective only and does not rescue past failed/post-hoc branches.
- When a source has no natural stop, do not invent R post-hoc; use source/raw return metrics first.
- Guardian is execution/protection infrastructure, not alpha.
- Preserve `EXACT_REPLICATION`, `CLOSE_REPLICATION`, `ADAPTATION` labels.
- Ex-post anomalies require a new preregistered test unless a rerun is a mechanical implementation correction dictated by the frozen source specification.
- CFD transfer requires executable BID/ASK/cost handling.
- Scanner QA after D032 v1.00: output-column counts/index bounds, immediate header flush, runtime output QA, plus source-algorithm audit for nontrivial sequence construction.
- New meta-rule: managed-strategy claims must separate RAW SIGNAL EDGE, EXACT NATIVE MANAGEMENT LIFT, STRATEGY-SELECTION LIFT, GUARDIAN/ACCOUNT-STATE SELECTION LIFT and COST DRAG instead of comparing incomparable P/L and virtual entry studies.

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
- D030 Alanazi H4 Engulfing: seven-major FX rejected; ETH discovery failed untouched 2019-2023 confirmation. Canonical ETH result `research/results/D030_C1_ETHUSD_H4_ENGULFING_PRE2024_CONFIRMATION_VERDICT_2026_09_05.md`.
- D029 Moskowitz/Ooi/Pedersen TSMOM 12M/1M: full 8-market gate rejected. Canonical result `research/results/D029_TSMOM_12M1M_FULL_PRIMARY_VERDICT_2018_2023_2026_09_05.md`.
- D033 Ben Omrane & Van Oppens EURUSD M5 DT/DB M2: corrected v1.01 arm rejected 0/7 gates. Canonical result `research/results/D033_V1_01_CORRECTED_M2_VERDICT_2026_09_05.md`.
- D034 Caporale/Plastun abnormal-return Strategy 1 GOLD arm: rejected 3/7 gates. OIL untested because unavailable. Canonical result `research/results/D034_XAUUSD_ABNORMAL_RETURN_STRAT1_VERDICT_2026_09_05.md`.
- D035 Binance BTC/ETH deleveraging -> FundedNext crypto CFD lead-lag primary development: rejected 4/8 gates. Canonical result `research/results/D035_BINANCE_DELEVERAGING_FUNDEDNEXT_CFD_DISCOVERY_VERDICT_2026_09_06.md`, commit `436068e04ed5a9538cae79b8305417e08c79d3f3`.

# D032 — Crypto H1 Bullish Doji Star
Research basis: Moser & Brauneis (2026), DOI `10.1016/j.iref.2026.105158`.

Frozen underlying signal: Bullish Doji Star H1, strict 144h SMA downtrend, executable LONG first ASK after signal, `1R = 2*sd(previous 24 H1 returns)`, source reference +24h.

D032-C1 PRE2024 confirmation: **PASS**. Canonical result `research/results/D032_C1_DOJI_STAR_H1_CORE_CONFIRMATION_VERDICT_2026_09_05.md`.

Core BTC+ETH+DOG PRE2024: n=79, mean +133.52 bps, median +93.43 bps, win 64.56%, mean +0.588R, same-trend control ~+32.13 bps, Doji-control differential ~+101.38 bps, bootstrap lower >0, gate 7/7 PASS.

Not production-ready. Management/entry-localization attempts -1R/+3R/24h, post24 1R runner, RSI<30 and 6h reclaim-high did not solve the problem. Keep as sparse research sleeve only.

# D035 — Binance BTC/ETH deleveraging -> FundedNext crypto CFD lead-lag — PRIMARY CLOSED REJECTED
Canonical preregistration: `research/campaigns/D035_BINANCE_DELEVERAGING_FUNDEDNEXT_CFD_LEADLAG_PREREGISTRATION_2026_09_05.md`.
Canonical result: `research/results/D035_BINANCE_DELEVERAGING_FUNDEDNEXT_CFD_DISCOVERY_VERDICT_2026_09_06.md`.

Development remained 2024-01-01..2025-12-31; 2026-H1 remains untouched.

Returned pack quality:
- 5,558 merged BTC/ETH source events;
- 38,622 target-event rows;
- 9 eligible FundedNext crypto CFDs: ADAUSD, BTCUSD, DOGUSD, ETHUSD, LNKUSD, LTCUSD, XLMUSD, XMRUSD, XRPUSD;
- Binance daily metrics complete for both BTC and ETH; no missing days/duplicate rows in returned QA;
- BTC/ETH 1m archive coverage complete for the loaded period;
- server->UTC alignment 114/114 weeks usable, mean weekly correlation ~0.996.

Frozen D035 gate:
- G1 event count PASS;
- G2 target count PASS;
- G3 pooled executable +15m FAIL: **-25.448 bps**;
- G4 event-control differential +15m FAIL: **+5.179 bps** vs +10 bps requirement;
- G5 day-cluster bootstrap lower >0 PASS: **[+3.033,+7.385] bps**;
- G6 pooled executable +30m FAIL: **-25.438 bps**;
- G7 BTC-only and ETH-only branches both positive FAIL: BTC-only **-3.281 bps**, ETH-only **+3.283 bps**;
- G8 month concentration PASS: max ~8.08%.

Final: **4/8 -> DISCOVERY_REJECT**. There is a small statistically detectable timing effect, but it is not economically large enough after executable FundedNext spreads in the broad CFD pool. BTCUSD and ETHUSD individually remain positive at +15m (~+5.86/+5.43 bps) but below the preregistered +15 bps hurdle.

## D035-E1 — causal dual-source exploratory diagnostic — PREREGISTERED / PREPARED
Reason: rows labelled `BTCUSD+ETHUSD` in the original development output look strong but are not causally tradable as measured because the first source timestamp receives the dual label when the second arrives up to five minutes later.

Preregistration:
`research/campaigns/D035_E1_CAUSAL_DUAL_SOURCE_DIAGNOSTIC_PREREGISTRATION_2026_09_06.md`
Commit: `e6ddd6989f49bbdba4581c575d9b9e5deec3ab9e`.

Analyzer:
`research/analysis/D035_E1_CausalDualConfirm_v1_00.py`
Commit: `4f95cc088478d520a28a95d376b6d08d357c544c`.
Delivered pack: `D035_E1_CausalDual_Pack_v1_00.zip`.
Python syntax compile PASS. The local runner includes progress percentage, elapsed time, ETA and per-CFD checkpoints.

Frozen E1 mechanics:
- same D035 BTC/ETH single-source shock definitions and 30m cooldown;
- require BTC and ETH shocks within <=5 minutes;
- tradable signal timestamp = **later/second qualifying source shock**;
- exploratory sample remains 2024-2025 only;
- primary cross-asset target frozen to **XLMUSD**; other CFDs diagnostics only;
- +15m primary, same +1/+5/+30/+60/+120 diagnostics;
- 2026-H1 remains untouched.

E1 advancement requires 8/8 on XLMUSD: >=200 events, mean executable +15m >=15bps, median >0, raw day-cluster bootstrap lower >0, event-control differential >=10bps, differential bootstrap lower >0, +30m >0, and both 2024/2025 +15m means >0.

D035 primary remains REJECT regardless of E1. Only an E1 8/8 result permits a fresh D035-C1 preregistration before touching 2026-H1.

# 2026-09-06 cross-strategy edge-decay autopsy — META DECISION
Canonical report: `research/results/CROSS_STRATEGY_EDGE_DECAY_AUTOPSY_2026_09_06.md`, commit `e1b062a164a19134c3f8c1a2ae83bfd77cb42186`.

Main conclusion: the transition from spectacular short-window P/L to weak broad edges is not explained by one cause. Evidence identifies a combination of **regime dependence, raw-signal vs native-manager/account-selection mismatch, multiple-testing/symbol selection, CFD cost drag, and data provenance**. D032 proves the stricter process can still confirm a large edge.

Most important surviving evidence:
- **D032 Doji entry**: Tier-A-sized confirmed entry edge, but sparse and management unresolved.
- **D023 USDJPY ORB**: discovery-only but unusually stable; n=489, ~+0.1179R/trade after approximate commission, positive 2024/2025/2026. Requires a new untouched confirmation; do not reinterpret D023 broad V0.
- **D017 BTC SELL Momentum**: discovery/watchlist but recurring; n=761, ~+0.125R to +0.131R at larger fixed targets, descriptive native-like management ~+0.109R, positive both 2024/2025. Requires exact-native attribution/full costs and later prospective confirmation.
- **D035 BTC/ETH**: small positive executable response only ~+5-6bps; microstructure observation, not enough cost cushion unless E1 is materially stronger.

Critical unresolved attribution question: the profitable 2026-09-02 RSI/Momentum short-window P/L and later raw-signal long-history diagnostics were not identical experiments. RSI raw entry is clearly negative over 2024-2025 while the short managed test was profitable; Momentum broad signal decays materially but account-state/native management may have supplied selection lift. Do not call the old P/L false until exact native replay decomposes it.

Next meta-experiment after D035-E1: build a frozen **META-A1 exact edge-attribution replay** for legacy RSI and D017 Momentum with nested L0 raw signal -> L1 exact native manager -> L2 strategy-local gates -> L3 Guardian/account-state selection, plus explicit cost drag and year splits. No thresholds may change.

## Immediate execution order
1. Let the already-started D035-E1 run finish on the same 2024-2025 data. Do not touch 2026-H1.
2. If E1 returns 8/8, preregister D035-C1 before opening 2026-H1. If E1 fails, close the dual-source branch.
3. **After E1, pause blind new-family scanning.** Do not immediately create D036/D037 merely to keep searching.
4. Prepare META-A1 exact-native edge attribution for the previously profitable legacy RSI and D017 Momentum lineages. Measure management/selection lift rather than comparing raw entry EV with full managed P/L.
5. Preserve USDJPY ORB and BTC SELL Momentum as Tier-B hypotheses only. Any confirmation must be separately preregistered on untouched data and include full realistic costs; no same-sample threshold mining.
6. Keep D032 Doji as the one confirmed sparse entry sleeve; future work must solve causal risk management without altering the confirmed pattern definition.
7. Pure Guardian Core v12.01 compile/smoke remains independently required before any live replacement.
8. FundedNext Algo Trading remains OFF until request-budget/retry pathology is resolved and replacement core is compiled/smoked.

Continuity rule: after every material milestone, update this handoff in the same work session.
Daily ledger rule: every Europe/Paris day with material Guardian work must be recorded in `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md` before session end/handoff.