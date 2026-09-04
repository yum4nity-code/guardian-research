# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-04 20:53 Europe/Paris
Status: ACTIVE / D026 FIRST DATA RECEIVED BUT V0 1.00 IMPLEMENTATION NON-CONFORMANT TO PRE-RESULT LOCK / V0 1.01 CONFORMANCE FIX COMMITTED / CORRECTED BTC+ETH RERUN NEEDED / D025 XAU-FOREX COMPLETE / D025 CRYPTO VOLUME DATA QUARANTINED / FUNDEDNEXT LIVE AUTO OFF PENDING REQUEST-BUDGET FIX

This is the canonical fast-resume file. A fresh ChatGPT/Codex instance must read this first. Historical chronology/time ledger: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.

## 0. USER DIRECTIVE / CONTINUITY

The user explicitly authorized autonomous work and does NOT want interruptions for micro-decisions. Continue independently until a manual MT5 action is genuinely necessary. Do not ask the user to restate prior project context after conversation/model limits.

Current research philosophy:
- no curve fitting;
- no post-hoc threshold changes disguised as fixes;
- do not settle for crumbs;
- prefer materially large recurring pre-cost edge (roughly >= +0.15R/trade, ideally +0.20R+) before production work;
- costs/stress must later be applied;
- manual MT5 Strategy Tester is the preferred execution path; do not ask the user to debug shell wrappers.

---

# 1. D026 PRICE EXHAUSTION RECLAIM — CURRENT PRIMARY RESEARCH TRACK

D026 is a NEW strategy, not a retuned D025. Baseline is price/time/ATR only: no broker tick volume and no Binance/Bybit dependency.

## 1.1 Frozen V0 rules — LOCKED BEFORE ANY D026 RESULT

File:
- `research/campaigns/D026_PRICE_EXHAUSTION_RECLAIM_V0_RULES_LOCK_2026_09_04.md`
- creation commit `1137ffbe669504b1aa6b518480b94598f98e3f0c`

Core state machine:
`IDLE -> WATCH -> SWEEP -> DISPLACEMENT -> EXHAUSTION -> RECLAIM -> RETEST/ACCEPTANCE -> VALID_SIGNAL`

Frozen thresholds:
- watch 0.50 x H1 ATR(14)
- fresh sweep 0.10 x H1 ATR
- structural stop buffer 0.10 x H1 ATR beyond worst sequence extreme
- displacement M15 range >=1.25 x previous-20 mean range
- directional body >=0.20 x H1 ATR
- body/range efficiency >=0.55
- bearish LONG-reclaim displacement closes in bottom 30%; bullish SHORT-reclaim in top 30%
- displacement may be sweep bar or next 2 CLOSED M15 bars
- exhaustion next 3 CLOSED M15: extra outward progress <=0.20 x displacement range AND current range <=0.80 x displacement range
- reclaim next 4 CLOSED M15
- RETEST relevant extreme within +/-0.15 H1 ATR around level and close on reclaimed side, or ACCEPTANCE = two consecutive reclaimed-side closes
- validation next 4 CLOSED M15 after reclaim
- cooldown 4h

Explicit exclusions: tick/real volume, OI, funding, liquidations, RSI/EMA/MACD, session filters, symbol-specific thresholds, long/short asymmetry, post-hoc regime switches.

## 1.2 Original diagnostic implementation V0 1.00

File:
- `research/ea/D026_PriceExhaustionReclaim_Virtual_V0_1_00.mq5`
- commit `d4e55b0a61a152158a6de20e24b356eb3c0cdc23`

User successfully compiled/ran it (proven by the produced CSVs). Pure virtual observer: no CTrade/orders/positions/balance/margin/lot/tick-volume dependency.

Predeclared analyzer created before results:
- `research/analysis/analyze_d026_per_v0.py`
- commit `7495d3edc7d3ef6cd3c1b61c660299f72cd4760a`

Analyzer scope only: integrity/counts, fixed +1R/+2R/+3R first-touch EV, year/side/path splits, Wilson-style uncertainty, and one 40%@+1R + 60% BE runner family to +2R/+3R. No threshold optimizer.

## 1.3 FIRST USER DATA RECEIVED — FIVE MARKETS

User supplied cumulative V0 1.00 files:
- `d026_per_virtual_v0_events.csv`
- `d026_per_virtual_v0_trades.csv`
- `d026_per_virtual_v0_outcomes.csv`

Sessions 2024-01-01 -> 2025-12-31:
- BTCUSD 560 signals = 283 in 2024 + 277 in 2025
- ETHUSD 618 = 332 + 286
- DOGUSD 525 = 269 + 256
- LNKUSD 562 = 264 + 298
- XAUUSD 649 = 357 + 292
- total 2,914 signals
- events 66,241 rows
- outcomes 14,555 rows

Integrity is good:
- zero `VALID_SIGNAL_REJECTED_BAD_RISK`
- zero `VALID_SIGNAL_REJECTED_NO_SLOT`
- valid-signal transition counts equal trade counts for every symbol
- every trade has outcome rows
- only a handful of final 48h snapshots are absent at the end-of-test boundary.

Descriptive predeclared overall EV from V0 1.00 (PRE-COST, BUT NOT VALID FOR FINAL STRATEGY VERDICT BECAUSE OF IMPLEMENTATION DEFECT BELOW):
- BTC: EV1 +0.011R, EV2 -0.117R, EV3 -0.176R
- ETH: -0.009R, -0.058R, -0.138R
- DOG: -0.004R, +0.077R, -0.040R
- LNK: -0.037R, -0.042R, -0.048R
- XAU: -0.007R, -0.009R, -0.101R

40%@1R + BE runner is near-zero/negative overall: BTC -0.050/-0.098 to 2R/3R; ETH +0.008/-0.034; DOG +0.023/-0.041; LNK -0.012/-0.024; XAU -0.041/-0.109.

Most side/path effects flip by year. One descriptive LNK SHORT +3R hint repeats positive in 2024 (~+0.115R) and 2025 (~+0.200R), pooled ~+0.164R, but DO NOT promote it because the population is contaminated by the implementation defect and it was discovered after viewing the sample.

Full first-run report:
- `research/results/D026_V0_FIRST_RUN_CONFORMANCE_FINDING_2026_09_04.md`
- commit `aedad0ab87319c141414b4b38964d2e74d2b5a5b`

## 1.4 CRITICAL IMPLEMENTATION CONFORMANCE DEFECT FOUND AFTER FIRST DATA

The pre-result rules lock remains unchanged. A static re-read of V0 1.00 exposed implementation errors:

A. State deadlines are off by one because the code evaluates the transition before checking `bars_in_state > N`:
- DISPLACEMENT can occur on a third subsequent M15 bar instead of only next 2;
- EXHAUSTION can occur on a fourth instead of next 3;
- RECLAIM can occur on a fifth instead of next 4;
- VALIDATION can occur on a fifth instead of next 4.

B. RETEST proximity is too permissive:
- old LONG test `low <= level + 0.15ATR` accepts arbitrarily deep lows;
- old SHORT test `high >= level - 0.15ATR` accepts arbitrarily high highs;
- frozen wording requires the relevant extreme itself within +/-0.15 ATR of level.

Scientific consequence: V0 1.00 first-run data are a valid smoke/instrumentation dataset, but **NOT a valid final D026 strategy sample**. Do not issue a production/rejection verdict from it and do not retune thresholds from it.

## 1.5 V0 1.01 CONFORMANCE FIX — COMMITTED, RULES UNCHANGED

File:
- `research/ea/D026_PriceExhaustionReclaim_Virtual_V0_1_01_CONFORMANCEFIX.mq5`
- commit `d0c15e2f901a73f51d09cd08394b3371e625b5c8`

Implementation-only wrapper. It includes V0 1.00 and replaces only:
- exact 2/3/4/4 closed-M15 state windows;
- RETEST as true +/-0.15 ATR relevant-extreme band;
- corrected timer path calling the conformant state machine.

No frozen threshold changed. Keep the wrapper in the same MetaEditor folder as V0 1.00 so the include resolves.

### ONLY USER ACTION CURRENTLY NEEDED FOR D026

Compile/run **V0 1.01 CONFORMANCEFIX**, not V0 1.00.

First corrected pass only:
1. BTCUSD, tester M1, 2024-01-01 -> 2025-12-31, Every tick, inputs `48 / 1 / true`.
2. ETHUSD, same settings.

Do NOT rerun DOG/LNK/XAU yet. The logger uses the same cumulative D026 CSV filenames, but sessions are unique; downstream analysis must isolate the NEW corrected BTC/ETH sessions from the five old V0 1.00 sessions.

If corrected BTC/ETH remain broadly flat/negative, reject D026 V0 rather than tuning it. If a large recurring branch survives both years, then design the next clean prospective validation.

---

# 2. D025 XAU / FOREX EXPLOITATION — COMPLETE

Final report:
- `research/results/D025_XAU_FOREX_FINAL_EXPLOITATION_2026_09_04.md`
- commit `e4cc482df9a29fcf6acf10d5c3d4ebc30b2716ad`

Final decisions:
- XAU broad D025: REJECT
- USDJPY broad: REJECT
- GBP broad: REJECT; GBP SHORT +1R only WATCHLIST (~+0.12R original pre-cost, weaker in newer population)
- EUR broad: REJECT; EUR SHORT +2R PRIMARY WATCHLIST (~+0.14R pooled pre-cost, uncertainty/cost margin too weak)
- 40%@1R + BE runner non-crypto: REJECT

No branch meets the user's required large-edge standard. Do not spend more time optimizing the same frozen D025 XAU/Forex population.

---

# 3. D025 CRYPTO DATA ISSUE — QUARANTINED

D025 CASCADE uses M15 relative tick volume >=1.25 vs prior-20 mean.

Current 1.03 virtual populations: BTC 499, ETH 553, DOG 595, XAU 798, USDJPY 793. Original 1.01 BTC/ETH totals were 1,117 / 1,172.

Mechanism proven: historical BTC/ETH tick-volume collapses toward ~1.0 in large blocks, mechanically disabling CASCADE. BTC Aug 2024 example: 117 sweeps, median relvol ~0.999, max 1.243, zero CASCADE, zero signals.

One controlled BTC `Every tick based on real ticks` rerun was effectively identical to the prior `Every tick` data, so tester modelling mode is not the primary cause. Remaining issue is FundedNext/MT5 historical feed/tick-volume provenance/availability.

D025 crypto volume-dependent historical conclusions remain QUARANTINED. Do not lower 1.25 to compensate.

---

# 4. SHARED INTELLIGENCE

Binance + Bybit Shared Intelligence remains READ-ONLY and has no current trading effect. Keep collector running. Baseline D026 must not use it. Later Crypto+ event studies may join with strict `available_at <= event_time`.

---

# 5. FUNDEDNEXT LIVE GUARDIAN REQUEST BUG — HIGH PRIORITY OPERATIONS ISSUE

FundedNext HUD observed ~5629/2000 vs FTMO ~32/2000.

Exact live lineage source in Library:
`Guardian_D017_PropFirmAuto_v11_17_04_MANUAL_PROTECTION_HOTFIX_PLAN80_RUNNER20.mq5`.

Confirmed runaway-capable mechanism:
- after RSI TP1, failed BE NET application leaves `g_rsi_be_push_done=false`;
- `RSIManageCycleTick()` retries `RSI_BE_RETRY` while pending;
- retry uses `SRP_PROTECTION`;
- `SRP_PROTECTION` bypasses request hard limit by design.

FundedNext Algo Trading stays OFF until bounded/deduplicated/backoff patch is built and validated. True emergency safety may retain priority; routine deferred BE must not behave as unlimited emergency traffic.

Potential v11.17.07 direction: initial protective attempt preserved; routine retries deduped/backed off (e.g. 5s -> 15s -> 60s -> 5m), retcode-aware, profit-protection priority where safety is not worsened; audit all `SRP_PROTECTION` retry loops.

Do NOT claim patch is finished yet.

---

# 6. FUNDEDNEXT QUICK STRIKE — CORRECTED REQUIREMENT

Guardian does NOT auto-close a manual position simply because initial SL placement fails. Current behavior: one SL placement attempt; if it fails the user manually places SL.

Quick Strike is separate: log Guardian-managed profitable <30s exits with entry time, elapsed seconds, venue, reason and P/L sign. Never leave an unsafe trade open merely to cross 30 seconds. GitHub issue #2 contains corrected requirement.

---

# 7. RESUME ORDER

1. `CURRENT_PROJECT_HANDOFF.md`
2. `research/results/D026_V0_FIRST_RUN_CONFORMANCE_FINDING_2026_09_04.md`
3. `research/campaigns/D026_PRICE_EXHAUSTION_RECLAIM_V0_RULES_LOCK_2026_09_04.md`
4. `research/ea/D026_PriceExhaustionReclaim_Virtual_V0_1_01_CONFORMANCEFIX.mq5`
5. original `research/ea/D026_PriceExhaustionReclaim_Virtual_V0_1_00.mq5`
6. `research/analysis/analyze_d026_per_v0.py`
7. first-run D026 cumulative CSVs (five old V0 1.00 sessions) and then isolate new corrected BTC/ETH sessions
8. `research/results/D025_XAU_FOREX_FINAL_EXPLOITATION_2026_09_04.md`
9. D025 1.03 volume-provenance report
10. latest Guardian request-budget audit/current Guardian source
11. `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`
12. `docs/STRATEGY_DECISIONS.md`

## Immediate dependency

The next scientifically necessary user action is only the corrected D026 V0 1.01 BTC+ETH MT5 run. Do not ask for DOG/LNK/XAU reruns first.

## Continuity rule

After every material milestone, update this handoff in the same work session. Important state must never exist only in conversation context.