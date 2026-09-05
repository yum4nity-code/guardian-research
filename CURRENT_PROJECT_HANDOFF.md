# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 STATIC CANDIDATE / D032 DOJI ENTRY CONFIRMED BUT MANAGEMENT UNSOLVED / D030 ALANAZI H4 ENGULFING CLOSE-REPLICATION PREPARED / CURRENT FUNDEDNEXT LIVE AUTO STILL OFF

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
- Scanner QA after the D032 v1.00 failure: verify output-column counts/index bounds, immediate header flush and runtime output QA before delivery.

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

## D032-C1 confirmation — PASS
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

Interpretation: **ENTRY EDGE CONFIRMED ON PRE-2024 BAR CONFIRMATION / BUILD MANAGEMENT**, not production-ready. Historical real ticks were unavailable; old intervals use M1 + `1 minute OHLC`.

Transport LINK/XRP failed; ADA exploratory also negative. Doji is market-dependent, core remains BTC/ETH/DOG.

## D032 management / entry-location attempts
- Source-derived -1R/+3R/24h management failed confirmation (~+0.118R pooled, bootstrap lower <0).
- D032-M1 post24 1R runner added essentially nothing (~+0.0045R incremental) -> reject.
- Diagnostic 1.5R post24 trail looked better (~+0.109R) but is unvalidated.
- Immediate-entry winners often travel deeply adverse; a very wide catastrophe stop destroys much of stop-normalized expectancy.
- D032-E1 RSI(14) M15 diagnostic showed no monotonic relationship.
- D032-E2 RSI<30 POST2024 failed sample-size/concentration gates and did not improve MAE. Result commit `635ebddb73237cd4451fc99aaf7e669e000ab45a`.
- D032-E3 6h reclaim-high delayed entry failed the central mechanism: pooled paired delta about -0.391R and median MAE worsened from about -1.02R to -1.36R. Result commit `50887f08479b0be9733d3a1de15369a87a3d67f0`.

Conclusion: underlying Doji directional information remains real enough to retain as a sparse sleeve candidate, but entry/risk management is unresolved. Do not deploy yet and do not keep mining RSI/reclaim thresholds on the same data.

# D030 — Alanazi FX H4 Bullish/Bearish Engulfing — PREPARED
Primary source: Ahmed S. Alanazi (2020), *The European Journal of Finance* 26(15), 1484–1505, DOI `10.1080/1351847X.2020.1748679`.

Preregistration: `research/campaigns/D030_FX_ENGULFING_H4_ALANAZI_CLOSE_REPLICATION_PREREGISTRATION_2026_09_05.md`
Preregistration commit: `93fd6808ca10d8303078b9f559bd88de0d7c7a0c`
Prepared handoff: `handoff/chatgpt_to_codex/2026/09/05/D030_FX_ENGULFING_H4_ALANAZI_PREPARED.md`
Prepared handoff commit: `9c106e2e2b17a386933bcf3fe6b2a1da6102913c`

The full article methodology was recovered before user testing. Important source facts:
- pattern is a **full-candle/wick engulf**, not merely body engulf;
- bullish Eq.5: CC bullish, PC bearish, CC high > PC high, CC low < PC low, CC close > PC open;
- bearish Eq.6 is the mirror;
- no trend filter: the paper deliberately treats every occurrence as a reversal;
- next H4 candle open entry: ASK long / BID short;
- stop = exactly 5 pips beyond CC low/high;
- target = exactly 1:1;
- spread and rollover were material in the source;
- paper H4 OOS sample 2015–2018 had 3,047 major-pair trades; seven-major portfolio positive in aggregate.

Classification remains `CLOSE_REPLICATION_CFD_TRANSFER` because our target is FundedNext CFD, historical real ticks are absent on old intervals, H4 midpoint quote bars are reconstructed from tester BID/ASK ticks, and exact historical rollover is not reconstructed in the first pass.

Delivered scanner:
- `D030_FX_Engulfing_H4_Alanazi_CloseReplication_v1_01.mq5`
- SHA-256 `e7748717273afcd4d4477bee5de97ae9ab590c30953ebc546ad71a3f0a7ebb6e`
- virtual only / no orders / Guardian OFF
- M1 tester + `1 minute OHLC`, internally constructs H4 BID/ASK quote bars and source-like midpoint OHLC.

An internal draft v1.00 was discarded before delivery after the full paper was recovered; do not use it. v1.01 implements the recovered 5-pip / 1:1 / full-wick source rule.

Static QA v1.01:
- braces/parentheses/brackets balanced;
- no risky local struct reference aliases;
- EVENTS header/row = 39 data columns;
- SUMMARY header/row = 20;
- immediate header flush + runtime FileSize header QA.

ChatGPT has NOT MetaEditor-compiled the scanner.

## D030 frozen target-CFD gate
Primary seven majors: EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD.
Frozen signal window: 2024-01-01 through 2026-08-31 23:59; tester may run later to resolve late signals.

Advance only if pooled core satisfies:
1. >=300 resolved clean trades;
2. mean executable risk-normalized result > +0.15R/trade after embedded spread;
3. month-block bootstrap 95% lower bound >0;
4. >=4/7 majors positive mean executable R;
5. fixed-size pip result after spread >0;
6. no one pair >40% of positive pooled executable R.

If fixed-size pips look source-like but risk-normalized R fails, classify it academically interesting but reject it as a Guardian/prop-challenge engine in this form. No same-sample trend/RSI/stop/target rescue.

## Immediate execution order
1. Compile `D030_FX_Engulfing_H4_Alanazi_CloseReplication_v1_01.mq5` in MetaEditor.
2. Run the seven majors on M1 / `1 minute OHLC`, tester start 2024-01-01 and end at least 2026-09-05, no input changes.
3. Return `EVENTS.csv`, `SUMMARY.csv`, `RUN_INFO.csv` from each run. Analyze event rows using the frozen signal cutoff <= 2026-08-31.
4. Decide D030 strictly from preregistered pooled gates; pair anomalies are discovery only.
5. Keep D032 as a sparse confirmed-entry research sleeve, but do not spend the whole project forcing its management.
6. Continue an independent higher-frequency engine search in parallel if D030 is too weak or too slow.
7. Pure Guardian Core v12.01 compile/smoke remains independently required before any live replacement.

Continuity rule: after every material milestone, update this handoff in the same work session.