# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-06 Europe/Paris
Status: ACTIVE / PURE GUARDIAN CORE V12.01 STATIC CANDIDATE / D032 DOJI ENTRY CONFIRMED BUT MANAGEMENT UNSOLVED / D035 FAMILY CLOSED / D17 MOMENTUM LINEAGE REOPENED / BANGER LAB V1 PREPARED / DERIBIT 0DTE OBSERVER PREPARED / FUNDEDNEXT LIVE AUTO OFF

Canonical protocol: `docs/RESEARCH_PROTOCOL.md`.
Historical chronology/time: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.
Cross-strategy autopsy: `research/results/CROSS_STRATEGY_EDGE_DECAY_AUTOPSY_2026_09_06.md`.
Banger slate: `research/results/GUARDIAN_BANGER_LAB_V1_2026_09_06.md`.

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

This is the clean strategy-neutral chassis: no RSI, no Momentum embedded. It keeps risk/prop-firm/manual protection/request/news/execution infrastructure and exposes a strategy registry socket. Status remains STATIC PASS only; MetaEditor compile/smoke is required before live replacement. Do not migrate a Momentum engine into Core until the exact surviving D17 behavior is fixed and attributed.

## Surviving evidence
### D032 — confirmed sparse reversal entry
Bullish Doji Star H1, strict 144h SMA downtrend, executable LONG first ASK after signal, `1R = 2*sd(previous 24 H1 returns)`.
PRE2024 BTC+ETH+DOG confirmation: n=79, mean +133.52bps, +0.588R, win 64.56%, control differential +101.38bps, bootstrap lower >0, 7/7 PASS. Management variants tested so far did not solve production management. Frequency is too low for a sole challenge engine.

### D023 — USDJPY London ORB watchlist
Broad four-market V0 failed, but USDJPY discovery/watchlist was ~+0.1179R/trade after approximate commission, n=489, positive 2024/2025/2026. Rule remains frozen; no rescue filters. Needs fresh independent confirmation before portfolio promotion.

### D017 — BTC Momentum watchlist
Broad raw Momentum was not strong enough across BTC+ETH. BTC SELL remained the recurring clue: roughly +0.125R to +0.131R at larger fixed targets, n=761, positive in 2024 and 2025; descriptive managed result around +0.109R before full cost attribution. Old short-window full managed Momentum test was materially stronger than raw diagnostics.

## D035 — family closed
Primary 2024-2025: 4/8 reject. Causal E1 XLM primary: n=870, executable +15m +6.705bps, differential +13.490bps, 6/8 -> DO NOT ADVANCE because primary economic mean <15bps and median not >0. ETH/BTC diagnostics were not preregistered primary and were not promoted. Preserve 2026-H1 untouched.

## D17 MOMENTUM LINEAGE — CURRENT STATE
The earlier handoff treated uploaded v11.16.19 as authoritative. That is no longer safe as a sole lineage anchor: subsequent short-window tests produced inconsistent/abnormal behavior and the user explicitly reopened the search for the historical/live D17 branch.

Important anchors now known:
- GitHub contains `candidates/for_guardian/Guardian_D017_PropFirmAuto_v11_16_MOMENTUM_PROD.mq5` (production-candidate lineage anchor).
- `docs/GUARDIAN_V11_16_5_TO_11_16_11_CHANGELOG.md` records v11.16.11 as the strategy-switch build and states that the v11.16.11 change added top-level Momentum/RSI switches without changing strategy parameters.
- User reports the D17 currently running on FTMO is behaving reasonably, specifically the stop that ratchets in the profitable direction. Treat this as operational observation, not statistical validation.
- Source inspection of the later lineage shows the Momentum manager at TP1 2.00R / 25%, true-net BE around 1.25R and ATR trail 1.75 that only improves the stop. Preserve these values for attribution; do not retune them on inspected samples.

### META-A1 status
The v11.16.19-based `META_A1_Momentum_Attribution_Pack_v1_00.zip` remains a useful instrumented artifact but is **not currently the authoritative next test** until source lineage/non-regression is resolved. Do not spend another long backtest merely because the old handoff said to. First identify/replicate the actual D17 behavior to be attributed.

## BANGER LAB V1 — current research slate
Canonical report: `research/results/GUARDIAN_BANGER_LAB_V1_2026_09_06.md`.
Commit adding report: `8786bb393c3641fcef0997452501a0af9e9d061f`.

### GUARDIAN HYDRA V0
Portfolio architecture, not an alpha claim. Intended independent sleeves:
1. D17 Momentum + exact native ratchet manager.
2. USDJPY London ORB after untouched confirmation.
3. D032 confirmed sparse Bullish Doji H1 reversal.
4. BTC Deribit 0DTE expiry reversal after exchange-data replication and CFD transfer.

Frozen research risk proposal before any portfolio replay: M 0.25%, ORB 0.20%, Doji 0.20%, Expiry 0.15%, account open-risk cap 1.00%, no dynamic performance sizing. Use existing D024 overlap framework after >=2 sleeves independently validate.

### BANGER priority 1 — D17 Native Ratchet attribution
For identical frozen D17 entries compare only predeclared counterfactuals:
- NATIVE exact manager;
- FIXED-3R;
- TIMEBOX with initial SL and no profit manager.
No alternative trail/BE/TP parameter grid. Export MFE/MAE, touch ordering, exact SL ratchet path, TP1/BE events, full costs and Guardian/account-state blocks.

### BANGER priority 2 — BTC Deribit 0DTE expiry reversal
2026 Finance Research Letters evidence documents a BTC return reversal around Deribit option expiration, concentrated on high ATM open-interest days. Working-paper rule defines ATM within +/-2.5% at 07:00 UTC and uses top-decile ATM OI. Our first CFD transfer V0 is explicitly an ADAPTATION: prior-only expanding 90th percentile, short 07:00->08:00 then long 08:00->09:00, executable CFD bid/ask + commission, 1.5x cost stress, no indicator filters.

Read-only forward observer added:
`research/external_intelligence/deribit_expiry_observer_v1.py`
Commit: `51633a2ce1dece72a05c07e11b08bacd2b288825`.
Static validation here: Python `py_compile` PASS and deterministic self-test PASS. **Live Deribit network execution was not run in this environment.** Collector requires no keys and sends no trades.

### BANGER priority 3 — Liquidation Cascade Exhaustion Reclaim
New hypothesis distinct from D035 follow-through: large 5m BTC drop + large OI contraction + extreme long-liquidation burst on Binance+Bybit, then wait for M5 reclaim before LONG; structural stop at cascade low and fixed 120m primary time exit. Historical OI availability is the bottleneck; do not fabricate long history or reuse Binance's 30-day REST window as if it were multi-year evidence.

## Immediate execution order
1. Do not change the live FTMO D17 solely because raw backtests disappointed; preserve its current manager while lineage is reconstructed.
2. Resolve exact D17 source/non-regression using the GitHub MOMENTUM_PROD anchor and any matching live/local source; then run native-manager attribution before long new Momentum scans.
3. Run untouched confirmation for frozen USDJPY D023 when a genuinely unused period/feed is available.
4. Start Deribit 07:00 UTC OI forward collection; separately source provenance-clean 2021-2023 option-chain OI for historical replication.
5. Keep D032 Doji as confirmed sparse sleeve; do not overfit its manager.
6. Test Cascade Reclaim only when synchronized OI/liquidation history is adequate.
7. Activate D024 portfolio overlap/equity replay only after at least two sleeves independently validate.
8. FundedNext Algo Trading remains OFF until request-budget/retry pathology is resolved and clean replacement core is compiled/smoked.
