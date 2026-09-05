# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-05 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 CANDIDATE PREPARED / EVIDENCE-FIRST STRATEGY RESET / RSI RAW ENTRY REJECTED / D017 MOMENTUM BROAD REJECTED / D023 ORB NEXT / D022+D027+D028 QUEUED / CURRENT FUNDEDNEXT LIVE AUTO STILL OFF

Read this first. Historical chronology/time ledger: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.

## Research standard
- No curve fitting or post-hoc threshold edits disguised as fixes.
- User wants materially large recurring pre-cost edge, roughly >= +0.15R/trade and ideally +0.20R+, before production work.
- Guardian is protection/execution infrastructure, not assumed alpha.
- Prefer documented strategy families, one frozen V0 per family, multi-period/multi-market validation and cheap-fail before production integration.

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

## Shared Intelligence / external data
Binance+Bybit multi-venue collection, venue-separated state and MT5 bridge have passed runtime plumbing gates. Available BTC/ETH facts include spot/perp, basis, OI, funding, liquidation windows, returns and cross-venue dislocation. Predictive edge is NOT yet proven. Archive depth is accumulating; any future historical use must enforce `available_at <= event_time`.

## Evidence-based strategy slate
Canonical review: `research/results/STRATEGY_RESEARCH_SLATE_2026_09_05.md`.
Target today: four independent V0 families, not parameter variants.

1. **D023 London ORB M15** — EURUSD/GBPUSD/USDJPY/XAUUSD. Existing preregistration and engine. London 08:00-09:00 opening range, first M15 close breakout 09:00-11:00, next-bar entry, opposite range stop, stop-or-16:00 exit. No rescue filters in V0.
2. **D022 Relative-Value Pair Reversion M15** — AUDUSD/NZDUSD and EURUSD/GBPUSD, corrected engine v2, no symbol substitution after results.
3. **D027 NR7 Contraction Breakout** — preregistered 2026-09-05, same four EUR/GBP/JPY/XAU markets.
4. **D028 Intraday Session Momentum** — preregistered 2026-09-05, same four markets.
5. Optional benchmark **D029 Classic TSMOM** — literature-style slow benchmark/diversifier, not primary challenge engine.

D021 MICRO-REV remains prepared but is behind the stronger direct-evidence slate; do not rewrite/tune its frozen engine.

## Current live Guardian / FundedNext
The currently deployed/live lineage is still older than pure v12.01 and contains the known server-request hyperactivity mechanism tied to failed RSI BE retries. FundedNext Algo Trading remains OFF until a safe compiled/live-approved replacement exists. Do not claim v12.01 fixes production until compile/smoke gates pass.

Quick Strike remains conceptually separate: profitable Guardian-managed exits under 30 seconds can count; never weaken protection merely to cross 30 seconds.

## Immediate execution order
1. Compile `Guardian_Core_Base_v12_01_CANDIDATE.mq5` with its `GuardianCore` folder; compile-fix only.
2. Empty-registry tester smoke => zero auto entries; verify drawdown/reference/request/HUD behavior.
3. Demo manual missing-SL smoke => one attempt max, no forced close on failure.
4. Shared Intelligence observer smoke => fresh/stale schema-2 generations and zero trading effect with empty registry.
5. In strategy research: D023 -> D022 if exact symbols available -> D027 -> D028 -> optional D029.
6. Only validated strategy modules get plugged into pure Guardian.

Continuity rule: after every material milestone, update this handoff in the same work session.
