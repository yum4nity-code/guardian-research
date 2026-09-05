# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 CANDIDATE PREPARED / SETUP-FIRST RESEARCH PHASE / D022+D023+D027+D028 V0 REJECTED / D031 FX SCAN NON-VALIDATED WITH DISCOVERY CLUES / D032 CRYPTO H1 PREREGISTERED+CODED / CURRENT FUNDEDNEXT LIVE AUTO STILL OFF

Read this first. Historical chronology/time ledger: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.
Canonical research rules: `docs/RESEARCH_PROTOCOL.md`.

## Research standard
- No curve fitting or post-hoc threshold edits disguised as fixes.
- User wants materially large recurring pre-cost edge, roughly >= +0.15R/trade and ideally +0.20R+, before production work.
- Guardian is protection/execution infrastructure, not assumed alpha.
- Prefer documented strategy families/setups, frozen V0 definitions, multi-period/multi-market validation and cheap-fail before production integration.
- Distinguish `EXACT_REPLICATION`, `CLOSE_REPLICATION` and `ADAPTATION`. A documented family transferred to another market/timeframe/session is not to be called « proven » on our universe.
- Priority to exact/close replications whose asset class, horizon and operational rules are recoverable from primary literature. If entry/exit/stop/session/sizing rules are missing, do not invent them and still call the result a replication.
- Ex-post symbol/direction anomalies are discovery only; they can spawn a fresh preregistered confirmation experiment on untouched data, never retroactive validation.
- Diagnostics must preserve entry quality information. With a natural/source-defined initial risk, export `initial_risk`, `MFE_R`, `MAE_R`, and touches of 0.5R/1R/1.5R/2R/2.5R/3R. Without a natural stop, export MFE/MAE and normalized excursion instead of inventing R.
- Future CSVs must contain enough path information that MFE/MAE and R-touch frequencies can be analyzed later without rerunning merely to recover these diagnostics. Zero-trade/data failures must be explicit, not silent empty CSVs.
- NEW setup-first workflow: cheap scanner first (Guardian OFF) to test whether an entry/setup contains information; management design only after entry evidence; Guardian/FTMO full-chassis backtest only after standalone edge is strong enough to justify the expensive run.
- NEW CFD transfer rule: spot/futures/exchange evidence is hypothesis evidence only. No edge is considered transferred until reproduced on the target CFD feed with executable bid/ask/cost handling.
- NEW control requirement: where feasible, setup scans should include a matched control / comparable non-setup baseline so a pretty MFE curve is not confused with ordinary market drift/trend.
- NEW output contract: one Strategy Tester run = one recognizable subfolder under `FILE_COMMON\GuardianResearch\SETUP_SCANS\<EXPERIMENT>\<SYMBOL>\<RUN_TAG>\` with events, summary and run-info files.

## Pure Guardian Core v12.01 candidate
User decision: Guardian becomes a strategy-neutral Lego chassis. RSI and Momentum are physically removed even though RSI had inherited manual-management duties; manual management will be redesigned separately.

Static report: `research/results/GUARDIAN_CORE_V12_01_STATIC_AUDIT_2026_09_05.md`.
Codex handoff: `handoff/chatgpt_to_codex/2026/09/05/GUARDIAN_CORE_V12_01_CANDIDATE_PREPARED.md`.

Candidate:
- `Guardian_Core_Base_v12_01_CANDIDATE.mq5`
- SHA-256 `6a74d4187e04a02f9924c48ef34a1f0eb946da0f64d66a4839701154d6ad1176`
- `GuardianCore/Guardian_StrategyRegistry_v1.mqh` — empty strategy socket
- `GuardianCore/Guardian_StrategyModule_TEMPLATE_v1.mqh` — module template

Important: candidate is **STATIC PASS only**. MetaEditor compilation and MT5 smokes are not claimed yet; do not replace live Guardian before those gates.

Core keeps only generic services: prop-firm/profile/runtime rules, Prague/server day boundaries, drawdown/risk, costs, request budget, news/rollover/weekend/emergency protection, neutral manual initial-SL safety, optional market-feature bus, Shared Intelligence reader, generic strategy intent/execution API.

Manual semantic lock: Magic-0 position without SL => at most ONE initial broker SL placement attempt. Failure => alert/log + user sets SL. Never auto-close solely because this placement failed. No RSI TP/BE/trailing/runner logic remains.

Strategy modules must submit entries through `GuardianSubmitIntent()` and may only modify/partially close positions carrying their own Guardian-generated magic. No strategy module should call `CTrade` directly.

## Rejected / frozen old strategy evidence
### RSI legacy v11.16.11
Raw entry edge rejected across BTC, ETH, XAU and EUR. No RSI threshold tuning.

### D017 Momentum
Broad BTC/ETH and available XAU/EUR/GBP/USDJPY populations fail the large-edge standard. Weak clues remain watchlist-only.

### D025 / D026
D026 corrected V0 rejected. D025 broad XAU/Forex exploitation rejected; crypto volume-dependent branch remains quarantined because historical FundedNext tick-volume provenance is inconsistent.

## 2026-09-05 evidence-based batch verdicts
### D023 London ORB M15 — REJECT_V0
Official four-market EURUSD/GBPUSD/USDJPY/XAUUSD pool essentially flat before costs. USDJPY remains a discovery anomaly/watchlist clue only.

### D022 Relative-Value Pair Reversion M15 — REJECT_V0
AUDUSD/NZDUSD and EURUSD/GBPUSD aggregate negative, PF ~0.93 and only ~22.5% zero-return exits versus >=60% gate. Positive subsets failed stability/concentration/direction requirements.

### D027 NR7 Contraction Breakout — REJECT broad V0
Broad multi-market edge did not pass. AUDUSD SHORT NR7 and USDCAD LONG NR7 are discovery clues only.

### D028 Intraday Session Momentum — REJECT_V0
Official four-market V0 failed and ten-market extension was worse. GBPUSD SHORT remains discovery-only.

Important interpretation: these failures do NOT show that the cited academic families are fake. Most D022/D023/D027/D028 implementations were adaptations or falsification transfers rather than exact replications.

## NEW setup-first research phase
The user has already tested very many classic breakout/pullback/momentum/sweep ideas. The project should not keep presenting familiar family names as novelty. The new objective is to extract more information from entry setups by measuring path/excursion before designing exits.

### D031 FX Piercing Line / Dark Cloud Cover D1 — BROAD NOT VALIDATED
Scanner used source-based stop/R and exported MFE/MAE plus 0.5R..3R touches. Broad FX result did not establish a production-level universal edge and showed strong period dependence. Some symbol-level clues (notably EURUSD/USDCAD in the first scan) are discovery-only and cannot be retroactively selected as validation. The main success of D031 is methodological: the excursion scanner reveals entry behavior that old final-PnL-only tests could hide.

### D032 Crypto H1 Reversal Trio — PREREGISTERED / CODE PREPARED / NOT YET RUN
Preregistration: `research/campaigns/D032_CRYPTO_H1_REVERSAL_TRIO_PREREGISTRATION_2026_09_05.md`.

Research basis: Moser & Brauneis (2026), IREF 108, 105158, DOI 10.1016/j.iref.2026.105158.

Frozen first CFD campaign:
- BTC CFD
- ETH CFD
- DOGE CFD

Selected patterns, TA-Lib default definitions:
- Bullish Doji Star
- Bullish Inverted Hammer
- Bearish Hanging Man

Source horizons preserved: 1/2/3/6/9/12/15/18/24h.
Source-defined diagnostic risk: `1R = 2 * sigma(previous 24 H1 returns)`.
Trend interpretation frozen before results: 144-hour SMA (six days of H1 observations), strict monotonic `MA[t-6]..MA[t]`.

D032 outputs both source-close returns and executable CFD bid/ask returns, MFE/MAE and 0.5R..3R path diagnostics within 24h, stop breaches, feed-gap flags, plus a same-trend/no-selected-pattern control pool. No Guardian and no orders in this cheap viability stage.

Code delivered in ChatGPT work session: `D032_CRYPTO_H1_ReversalTrio_ExcursionDiagnostic_v1_00.mq5` (MetaEditor compile authority still required).

## Shared Intelligence / external data
Binance+Bybit multi-venue collection and MT5 bridge passed runtime plumbing gates. Predictive edge is NOT yet proven. Any historical use must enforce `available_at <= event_time`.

## Current live Guardian / FundedNext
The currently deployed/live lineage is still older than pure v12.01 and contains the known server-request hyperactivity mechanism tied to failed RSI BE retries. FundedNext Algo Trading remains OFF until a safe compiled/live-approved replacement exists. Do not claim v12.01 fixes production until compile/smoke gates pass.

## Immediate execution order
1. Compile `D032_CRYPTO_H1_ReversalTrio_ExcursionDiagnostic_v1_00.mq5`; compile-fix only, no methodology changes after first results are opened.
2. Run BTC, ETH and DOGE CFD using M1 chart + `Every tick based on real ticks`; source logic remains H1 internally.
3. Analyze pattern events against matched controls, source-close vs CFD executable returns, full 1→24h response curve, MFE/MAE, R-touch distribution, feed-gap sensitivity and BTC/ETH/DOGE transport consistency.
4. If D032 shows a strong recurring entry edge, freeze a separate management experiment on untouched/future data. Do not choose the best observed horizon/R level and call it validation.
5. Only after a strategy survives entry + management validation, run the expensive Guardian/FTMO drawdown/non-regression campaign.
6. Pure Guardian Core v12.01 compile/smoke work remains independently required before live replacement.

Continuity rule: after every material milestone, update this handoff in the same work session.
