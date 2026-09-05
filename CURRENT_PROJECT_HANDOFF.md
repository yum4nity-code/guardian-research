# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 CANDIDATE PREPARED / SETUP-FIRST RESEARCH PHASE / D022+D023+D027+D028 V0 REJECTED / D031 FX BROAD NON-VALIDATED / D032 CRYPTO FIRST CFD SCAN COMPLETE WITH DOJI STAR DISCOVERY CANDIDATE / CURRENT FUNDEDNEXT LIVE AUTO STILL OFF

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
- Setup-first workflow: cheap scanner first (Guardian OFF) to test whether an entry/setup contains information; management design only after entry evidence; Guardian/FTMO full-chassis backtest only after standalone edge is strong enough to justify the expensive run.
- CFD transfer rule: spot/futures/exchange evidence is hypothesis evidence only. No edge is considered transferred until reproduced on the target CFD feed with executable bid/ask/cost handling.
- Control requirement: where feasible, setup scans should include a matched/comparable non-setup baseline so a pretty MFE curve is not confused with ordinary market drift/trend.
- Output contract: one Strategy Tester run = one recognizable subfolder under `FILE_COMMON\GuardianResearch\SETUP_SCANS\<EXPERIMENT>\<SYMBOL>\<RUN_TAG>\` with events, summary and run-info files.
- New implementation QA rule after D032 v1.00 failure: before delivery, verify output-column count/index bounds and ensure CSV headers are physically written/flushed; do not rely only on brace/parenthesis structural checks.
- New first-touch rule: summary R-touch rates must distinguish `ever touched within window` from `target touched before -1R`. Production/research decisions use first-touch ordering when a stop exists.

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

## Setup-first research phase
The user has already tested very many classic breakout/pullback/momentum/sweep ideas. The project should not keep presenting familiar family names as novelty. The objective is to extract more information from entry setups by measuring path/excursion before designing exits.

### D031 FX Piercing Line / Dark Cloud Cover D1 — BROAD NOT VALIDATED
Scanner used source-based stop/R and exported MFE/MAE plus 0.5R..3R touches. Broad FX result did not establish a production-level universal edge and showed strong period dependence. Some symbol-level clues (notably EURUSD/USDCAD in the first scan) are discovery-only and cannot be retroactively selected as validation. The main success of D031 is methodological: the excursion scanner reveals entry behavior that old final-PnL-only tests could hide.

### D032 Crypto H1 Reversal Trio — FIRST CFD SCAN COMPLETE
Preregistration: `research/campaigns/D032_CRYPTO_H1_REVERSAL_TRIO_PREREGISTRATION_2026_09_05.md`.
First verdict: `research/results/D032_CRYPTO_H1_REVERSAL_TRIO_FIRST_CFD_VERDICT_2026_09_05.md`.

Research basis: Moser & Brauneis (2026), IREF 108, 105158, DOI 10.1016/j.iref.2026.105158.

Frozen first CFD campaign:
- BTC CFD
- ETH CFD
- DOGE CFD

Additional user-supplied LNK/XRP runs are transport diagnostics only and do not alter the frozen-core verdict.

Selected patterns, TA-Lib default definitions:
- Bullish Doji Star
- Bullish Inverted Hammer
- Bearish Hanging Man

Source horizons preserved: 1/2/3/6/9/12/15/18/24h.
Source-defined diagnostic risk: `1R = 2 * sigma(previous 24 H1 returns)`.
Trend interpretation frozen before results: 144-hour SMA (six days of H1 observations), strict monotonic `MA[t-6]..MA[t]`.

#### D032 implementation note
`v1.00` had an output-only header-index bug (`headers[58]`/`headers[59]` on a 58-element array) causing immediate runtime failure and BOM-only CSVs. `v1.01` fixed only that output defect; research/signal logic remained unchanged. The failed v1.00 batch contains no evidence.

The v1.01 event rows are usable, but its built-in `SUMMARY.csv` has two interpretation/accounting limitations:
1. 24h return sums omit missing horizons but the divisor still includes all completed events, so recompute means from event rows with valid horizons.
2. Built-in hit rates mean `ever touched within 24h`; they can include a target reached after a prior -1R breach. First-touch probabilities must be reconstructed from event timestamps.
No rerun is required for the completed v1.01 batch because event-level rows preserve the needed data.

#### D032 frozen-core corrected result
For clean rows (`feed_gap=0`, `missing_horizons=0`, valid 24h executable result), 380 / 508 frozen-core pattern events remain.

**Bullish Doji Star = strong discovery candidate, not yet validated.**
- clean n = 77 (BTC 32 / ETH 30 / DOG 15)
- executable 24h mean = +111.6 bps; median = +79.7 bps; win rate = 61.0%
- source-close 24h mean = +127.6 bps
- executable 24h mean expressed in source-defined risk = +0.726R/event
- BTC mean +50.7 bps; ETH +159.4; DOG +145.8
- pooled yearly executable mean: 2024 +92.0 bps, 2025 +132.7, 2026 pre-OOS +72.9
- broad same-trend control differential at 24h about +138.7 bps/event
- response curve strengthens toward the source 24h horizon rather than depending on one isolated hour
- correct target-before-stop rates: 0.5R 64.9%, 1R 48.1%, 1.5R 35.1%, 2R 32.5%, 2.5R 27.3%, 3R 23.4%
- seen-sample 3R stop/target/24h-timeout diagnostic expectancy ~+0.318R/event, but 3R selection is post-hoc discovery only and cannot be called validated
- month-block bootstrap 24h executable mean lower bound remains positive (~+24.7 bps), while the 3R-management bootstrap lower bound is slightly negative (~-0.014R)

**Bullish Inverted Hammer = no broad recurring edge.** Clean core n=74; weak 24h mean, negative median, negative mean in R, severe 2024->2025/2026 sign deterioration. Do not rescue/tune.

**Bearish Hanging Man = weak/inconsistent.** Clean core n=229; small raw 24h mean, negative mean in R, ETH negative, fixed-target first-touch diagnostics not attractive. Do not promote.

Approximately one quarter of frozen-core pattern events intersect CFD feed gaps/missing exact horizons. Treat this as meaningful CFD-transfer evidence, not a nuisance to silently interpolate away.

Decision: promote Doji Star Bullish to a **new preregistered confirmation / management-design experiment**. Do not choose the observed best TP/horizon and validate it on the same 2024-2026 sample.

## Shared Intelligence / external data
Binance+Bybit multi-venue collection and MT5 bridge passed runtime plumbing gates. Predictive edge is NOT yet proven. Any historical use must enforce `available_at <= event_time`.

## Current live Guardian / FundedNext
The currently deployed/live lineage is still older than pure v12.01 and contains the known server-request hyperactivity mechanism tied to failed RSI BE retries. FundedNext Algo Trading remains OFF until a safe compiled/live-approved replacement exists. Do not claim v12.01 fixes production until compile/smoke gates pass.

## Immediate execution order
1. Freeze a new Doji-Star confirmation experiment before inspecting any new confirmation outcomes. Preserve the original 24h source horizon as the primary confirmation target; any 3R/management rule is secondary discovery and must be separately frozen.
2. Use untouched/future data if available. Do not reuse the seen 2024-2026 core sample as confirmation evidence.
3. Correct future scanner summaries so valid-horizon denominators and target-before-stop ordering are native, not reconstructed offline.
4. If Doji Star confirmation survives on BTC/ETH/DOGE CFD with costs, design a standalone management experiment; only then proceed to expensive Guardian/FTMO drawdown/non-regression testing.
5. D033 commodities setup scan remains next independent setup family after the Doji confirmation is frozen.
6. Pure Guardian Core v12.01 compile/smoke work remains independently required before live replacement.

Continuity rule: after every material milestone, update this handoff in the same work session.
