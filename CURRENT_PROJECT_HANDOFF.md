# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-06 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 STATIC CANDIDATE / D032 DOJI ENTRY CONFIRMED BUT MANAGEMENT UNSOLVED / D035 FAMILY CLOSED / CROSS-STRATEGY AUTOPSY COMPLETE / META-A1 MOMENTUM v1.00 PREPARED — METAEDITOR COMPILE + NON-REGRESSION NEXT / BLIND NEW-FAMILY HUNT PAUSED / FUNDEDNEXT LIVE AUTO OFF

Canonical protocol: `docs/RESEARCH_PROTOCOL.md`.
Historical chronology/time: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.
Cross-strategy autopsy: `research/results/CROSS_STRATEGY_EDGE_DECAY_AUTOPSY_2026_09_06.md`.
META-A1 lock: `research/campaigns/META_A1_MOMENTUM_ATTRIBUTION_LOCK_2026_09_06.md`.

## MANDATORY DAILY HOUSEKEEPING
Every Europe/Paris calendar day with material Guardian work must be recorded in `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md` before handoff/end of the work session. Record actual work, decisions/rejections, next action, and conservative human-time evidence. Do not count unattended tester/collector runtime as human work.

## Research standard
- No curve fitting or post-hoc rescues disguised as validation.
- Tier A preference: materially large recurring edge around >= +0.15R/trade when natural R exists.
- Prospective Tier B sleeves may be around +0.07R to +0.10R net/trade only with independent stability, bootstrap, full costs, sufficient frequency and portfolio-correlation gates.
- Guardian is execution/protection infrastructure, not alpha.
- Preserve `EXACT_REPLICATION / CLOSE_REPLICATION / ADAPTATION` labels.
- CFD transfer requires executable BID/ASK and realistic costs.
- Scanner QA after D032 bug: column/index QA, output/runtime checks, source-algorithm audit; compile/runtime must never be claimed without evidence.
- Managed-strategy attribution must separate raw signal, strategy-local selection, Guardian/account-state selection, management and cost drag.

## Pure Guardian Core v12.01
Candidate: `Guardian_Core_Base_v12_01_CANDIDATE.mq5`
SHA256: `6a74d4187e04a02f9924c48ef34a1f0eb946da0f64d66a4839701154d6ad1176`
Strategy socket: `GuardianCore/Guardian_StrategyRegistry_v1.mqh`
Template: `GuardianCore/Guardian_StrategyModule_TEMPLATE_v1.mqh`

This is the clean strategy-neutral chassis: no RSI, no Momentum embedded. It keeps risk/prop-firm/manual protection/request/news/execution infrastructure and exposes a strategy registry socket. Status remains STATIC PASS only; MetaEditor compile/smoke is required before live replacement. Do not migrate Momentum into Core until META-A1 attribution is understood.

## D032 — confirmed sparse entry sleeve
Bullish Doji Star H1, strict 144h SMA downtrend, executable LONG first ASK after signal, `1R = 2*sd(previous 24 H1 returns)`.
PRE2024 BTC+ETH+DOG confirmation: n=79, mean +133.52bps, +0.588R, win 64.56%, control differential +101.38bps, bootstrap lower >0, 7/7 PASS.
Management variants tested so far did not solve production management. Frequency is too low for a sole challenge engine.

## D035 — family closed for now
Primary D035 2024-2025: 4/8 DISCOVERY_REJECT. Small timing effect existed but broad FundedNext spreads destroyed the economic edge.
D035-E1 removed dual-source look-ahead by signaling only at the later BTC/ETH shock. XLMUSD primary: n=870, mean executable +15m +6.705bps, median 0, differential +13.490bps, raw bootstrap [+1.996,+11.549], differential bootstrap [+8.793,+18.302], +30m +3.697bps, positive 2024 and 2025. Gate 6/8 -> DO NOT ADVANCE because mean < +15bps and median not >0.
ETH/BTC diagnostics were stronger but were not the preregistered primary and must not be promoted post hoc. 2026-H1 remains untouched.
Canonical E1 result: `research/results/D035_E1_CAUSAL_DUAL_SOURCE_VERDICT_2026_09_06.md`.

## Cross-strategy edge-decay conclusion
The transition from spectacular short-window P/L to weak broad edges is explained by a mixture of regime dependence, raw-signal versus managed-system mismatch, multiple testing/symbol selection, CFD cost drag and data provenance. D032 demonstrates that the stricter process can still confirm a genuinely large edge.

Surviving hypotheses:
- D032 Doji: confirmed Tier-A-sized entry edge, sparse, management unresolved.
- D023 USDJPY ORB: discovery-only ~+0.1179R/trade after approximate commission, n=489, positive 2024/2025/2026; needs fresh independent confirmation.
- D017 BTC SELL Momentum: discovery/watchlist ~+0.125R to +0.131R on larger targets, descriptive managed result ~+0.109R, n=761, positive 2024/2025; needs exact attribution/full costs and later prospective confirmation.

## META-A1 Momentum — CURRENT TASK
User explicitly designated the uploaded v11.16.19 file as the authoritative Momentum engine for this attribution work. Stop hunting v11.16.11 for META-A1 Momentum.

Authoritative source:
`Guardian_D017_PropFirmAuto_v11_16_19_RSI_RUNNER10_REQUEST_BUDGET_DOGE_UNDERRISK.mq5`
- size 314914 bytes
- 6512 lines
- SHA256 `423ebb293cfc77a44b6e95278a8e269944a52b2089d34667ba7a1bf38fa29677`

Frozen source management includes TP1 2.00R / 25%, BE trigger 1.25R, trailing 1.75 ATR. No Momentum thresholds may change. RSI is OFF for META-A1.

Prepared artifact: `META_A1_Momentum_Attribution_Pack_v1_00.zip`
- `META_A1_Momentum_Attribution_v1_00.mq5` SHA256 `f45a3189bfa577f8a9fdac2b46514f2ad59469c531b0884275c4c74e8ce8714a`
- `META_A1_Analyze_v1_00.py` SHA256 `becbb06a4f9d510538be1f7d54acaa4f8c1f1027373c31333fa67274a1f859e6`
- `META_A1_README_v1_00.txt` SHA256 `5b57889a5026f5d742d54c4063279890b9247d09fa46cd0e488aaea77666da94`
- pack SHA256 `71f5c9a09e61fdc4db1229d6fb48156ae9595ba9a00e4400129b6684d054e73d`

Static QA performed: source identity checked, brace balance PASS, duplicate key-definition checks PASS, diff audit of intended instrumentation areas, Python analyzer `py_compile` PASS, synthetic analyzer smoke PASS. **MQL5 has NOT been compiled here; MetaEditor compile is mandatory.**

Attribution layers:
- L0 RAW structural Momentum candidate before strategy-local quality/regime/context filters.
- L2 FILTERED candidate after source strategy-local gates/ranking, just before real `ExecuteTrade`.
- L3 ACTUAL source execution/Guardian/account-state/native position path, authoritative.
- SHADOW uses source management thresholds over observed bid/ask as a counterfactual diagnostic only; never label it exact broker execution.
- Execution block reasons are logged (lock/session/SL/spread/drawdown/min-risk/min-lot/Guardian/SL validity/margin/request budget/order result).

## Mandatory execution order
1. Compile `META_A1_Momentum_Attribution_v1_00.mq5` in MetaEditor. If any error, stop and fix before testing.
2. NON-REGRESSION: BTCUSD, same inputs/model for original v11.16.19 and META-A1, Momentum ON / RSI OFF, recommended 2026-07-01..2026-07-31, `Every tick based on real ticks`. Real trade count and material P/L/trade behavior must match. If they do not, stop: instrumentation changed behavior.
3. Only after non-regression PASS: BTCUSD 2024-01-01..2025-12-31, real ticks, Momentum ON / RSI OFF, META raw+filtered shadow logging ON. No threshold changes.
4. Return the four FILE_COMMON CSVs: `META_A1_MOMENTUM_EVENTS_BTCUSD.csv`, `META_A1_MOMENTUM_EXEC_BTCUSD.csv`, `META_A1_MOMENTUM_SHADOW_BTCUSD.csv`, `META_A1_MOMENTUM_ACTUAL_BTCUSD.csv`.
5. Analyze where edge is created/destroyed. If full BTC system fails 2024-2025, stop before broadening. If it survives, freeze it and only then modularize the surviving Momentum engine into Guardian Core v12.01.
6. Keep blind D036/D037 family scanning paused while META-A1 is unresolved.
7. FundedNext Algo Trading remains OFF until request-budget/retry pathology is resolved and clean replacement core is compiled/smoked.
