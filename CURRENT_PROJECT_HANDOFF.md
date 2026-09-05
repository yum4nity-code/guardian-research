# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 CANDIDATE PREPARED / EVIDENCE-FIRST STRATEGY RESET / RSI RAW ENTRY REJECTED / D017 MOMENTUM BROAD REJECTED / D022+D023+D027+D028 V0 REJECTED / D029 NEXT / CURRENT FUNDEDNEXT LIVE AUTO STILL OFF

Read this first. Historical chronology/time ledger: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.
Canonical research rules: `docs/RESEARCH_PROTOCOL.md`.

## Research standard
- No curve fitting or post-hoc threshold edits disguised as fixes.
- User wants materially large recurring pre-cost edge, roughly >= +0.15R/trade and ideally +0.20R+, before production work.
- Guardian is protection/execution infrastructure, not assumed alpha.
- Prefer documented strategy families, one frozen V0 per family, multi-period/multi-market validation and cheap-fail before production integration.
- NEW: distinguish `EXACT_REPLICATION`, `CLOSE_REPLICATION` and `ADAPTATION`. A documented family transferred to another market/timeframe/session is not to be called « proven » on our universe.
- NEW: priority to exact/close replications whose asset class, horizon and operational rules are recoverable from primary literature. If entry/exit/stop/session/sizing rules are missing, do not invent them and still call the result a replication.
- NEW: ex-post symbol/direction anomalies are discovery only; they can spawn a fresh preregistered confirmation experiment on untouched data, never retroactive validation.
- NEW: diagnostics must preserve entry quality information. With a natural initial stop, export `initial_risk`, `MFE_R`, `MAE_R`, `exit_R`, and touches of 0.5R/1R/1.5R/2R/2.5R/3R. Without a natural stop, export MFE/MAE and normalized excursion (ATR/bps/volatility) instead of inventing R.
- NEW: future CSVs must contain enough path information that MFE/MAE and R-touch frequencies can be analyzed later without rerunning merely to recover these diagnostics. Zero-trade/data failures must be explicit, not silent empty CSVs.

## NEW — Pure Guardian Core v12.01 candidate
User decision: Guardian becomes a strategy-neutral Lego chassis. RSI and Momentum are physically removed even though RSI had inherited manual-management duties; manual management will be redesigned separately.

Static report: `research/results/GUARDIAN_CORE_V12_01_STATIC_AUDIT_2026_09_05.md`.
Codex handoff: `handoff/chatgpt_to_codex/2026/09/05/GUARDIAN_CORE_V12_01_CANDIDATE_PREPARED.md`.

Candidate delivered in the 2026-09-05 ChatGPT work session:
- `Guardian_Core_Base_v12_01_CANDIDATE.mq5`
- SHA-256 `6a74d4187e04a02f9924c48ef34a1f0eb946da0f64d66a4839701154d6ad1176`
- `GuardianCore/Guardian_StrategyRegistry_v1.mqh` — empty strategy socket
- `GuardianCore/Guardian_StrategyModule_TEMPLATE_v1.mqh` — module template

Important: candidate is **STATIC PASS only**. MetaEditor compilation and MT5 smokes are not claimed yet; do not replace live Guardian before those gates.

Core keeps only generic services: prop-firm/profile/runtime rules, Prague/server day boundaries, drawdown/risk, costs, request budget, news/rollover/weekend/emergency protection, neutral manual initial-SL safety, optional market-feature bus, Shared Intelligence reader, generic strategy intent/execution API.

Manual semantic lock: Magic-0 position without SL => at most ONE initial broker SL placement attempt. Failure => alert/log + user sets SL. Never auto-close solely because this placement failed. No RSI TP/BE/trailing/runner logic remains.

Feature bus is opt-in/default OFF: ATR, ATR%, relative ATR, ADX, macro EMA, macro slope/ATR, spread/ATR. These are facts, not signals.

Shared Intelligence path is wired read-only to `FILE_COMMON\GuardianSharedIntelligence\market_state_multivenue_v1.csv`, schema 2 / 61 fields / BTC+ETH. Freshness is enforced; stale state is not returned as usable strategy intelligence. Live external intelligence is disabled in Strategy Tester.

Strategy modules must submit entries through `GuardianSubmitIntent()` and may only modify/partially close positions carrying their own Guardian-generated magic. No strategy module should call `CTrade` directly.

## Rejected / frozen old strategy evidence
### RSI legacy v11.16.11
Raw entry edge rejected across BTC, ETH, XAU and EUR. Reports:
- `research/results/RSI_SNIPER_111611_LONG_HISTORY_BTC_ETH_2026_09_05.md`
- `research/results/RSI_SNIPER_111611_XAU_EUR_2026_09_05.md`
No RSI threshold tuning. Exact old post-RSI50 native manager is not worth carrying into pure core; only revisit as a separate historical research experiment if explicitly requested.

### D017 Momentum
Broad BTC/ETH and available XAU/EUR/GBP/USDJPY populations fail the large-edge standard. Reports:
- `research/results/D017_MOMENTUM_LONG_HISTORY_FIRST_VERDICT_2026_09_05.md`
- `research/results/D017_MOMENTUM_XAU_FOREX_PARTIAL_BATCH_2026_09_05.md`
Weak clues remain watchlist-only. USDCAD is unavailable on current FundedNext and is deferred, not substituted with another broker/source.

### D025 / D026
D026 corrected V0 rejected. D025 broad XAU/Forex exploitation rejected; crypto volume-dependent branch remains quarantined because historical FundedNext tick-volume provenance is inconsistent.

## 2026-09-05 evidence-based batch verdicts
### D023 London ORB M15 — REJECT_V0
Official four-market EURUSD/GBPUSD/USDJPY/XAUUSD pool ended essentially flat before costs: ~2,018 trades, ~+0.001R/trade gross, PF ~1.002. USDJPY remains a discovery anomaly/watchlist clue only, not validation of ORB broadly.

### D022 Relative-Value Pair Reversion M15 — REJECT_V0
AUDUSD/NZDUSD and EURUSD/GBPUSD diagnostic completed. Aggregate ~120 events, net negative overall, PF ~0.93 and only ~22.5% zero-return exits versus >=60% gate. AUDUSD/NZDUSD had a positive subset but failed stability/concentration/direction-dependence requirements; do not rescue post hoc.

### D027 NR7 Contraction Breakout — REJECT broad V0
Broad multi-market edge did not pass. AUDUSD SHORT NR7 and USDCAD LONG NR7 are discovery clues/watchlist only; they are too small for production and require new preregistered untouched-data confirmation before any further claim.

### D028 Intraday Session Momentum — REJECT_V0
Official four-market EURUSD/GBPUSD/USDJPY/XAUUSD V0 failed: only 2/4 positive, aggregate PF below gate and negative/unstable aggregate expectancy before full commission stress. Ten-market extension was worse overall. GBPUSD SHORT is a discovery anomaly only, not a validated sleeve.

Important interpretation: these failures do NOT show that the cited academic families are fake. Most D022/D023/D027/D028 implementations were adaptations or falsification transfers rather than exact replications. Going forward the project must label this distinction explicitly and prioritize faithful primary-source replication.

## Shared Intelligence / external data
Binance+Bybit multi-venue collection, venue-separated state and MT5 bridge have passed runtime plumbing gates. Available BTC/ETH facts include spot/perp, basis, OI, funding, liquidation windows, returns and cross-venue dislocation. Predictive edge is NOT yet proven. Archive depth is accumulating; any future historical use must enforce `available_at <= event_time`.

## Evidence-based strategy slate — next state
Canonical review: `research/results/STRATEGY_RESEARCH_SLATE_2026_09_05.md`.
Completed/rejected V0s: D022, D023, D027, D028.

Next candidate:
1. **D029 Classic TSMOM benchmark** — before execution, verify that the test is a faithful literature-style implementation rather than another loosely adapted intraday strategy. The literature basis is materially stronger than the rejected fast adaptations, but cadence is slow and it may be a diversifier/sanity benchmark rather than the main challenge engine.
2. **D030 H4 bullish/bearish engulfing replication** — high-interest reserve only after exact published methodology is recovered. Do not invent missing entry/exit/stop/trend/gap conventions.
3. Any specialized clue such as USDJPY ORB, AUDUSD-short NR7, USDCAD-long NR7 or GBPUSD-short D028 requires a NEW preregistration and untouched confirmation data; none is currently approved for Guardian.

D021 MICRO-REV remains prepared but is behind stronger direct-evidence work; do not rewrite/tune its frozen engine without an explicitly new hypothesis.

## Current live Guardian / FundedNext
The currently deployed/live lineage is still older than pure v12.01 and contains the known server-request hyperactivity mechanism tied to failed RSI BE retries. FundedNext Algo Trading remains OFF until a safe compiled/live-approved replacement exists. Do not claim v12.01 fixes production until compile/smoke gates pass.

Quick Strike remains conceptually separate: profitable Guardian-managed exits under 30 seconds can count; never weaken protection merely to cross 30 seconds.

## Immediate execution order
1. Compile `Guardian_Core_Base_v12_01_CANDIDATE.mq5` with its `GuardianCore` folder; compile-fix only.
2. Empty-registry tester smoke => zero auto entries; verify drawdown/reference/request/HUD behavior.
3. Demo manual missing-SL smoke => one attempt max, no forced close on failure.
4. Shared Intelligence observer smoke => fresh/stale schema-2 generations and zero trading effect with empty registry.
5. Before D029, audit the primary TSMOM methodology and freeze an exact/close-replication spec. Include mandatory MFE/MAE and R-touch diagnostics whenever a natural R exists; otherwise use normalized excursion metrics.
6. Only validated strategy modules get plugged into pure Guardian.

Continuity rule: after every material milestone, update this handoff in the same work session.
