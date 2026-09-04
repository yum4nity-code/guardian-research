# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-04 20:25 Europe/Paris
Status: ACTIVE / D025 XAU-FOREX EXPLOITATION COMPLETE / D026 V0 PREP COMPLETE, WAITING ONLY FOR USER MT5 COMPILE + BTC/ETH RUNS / D025 CRYPTO VOLUME DATA QUARANTINED / FUNDEDNEXT LIVE AUTO OFF PENDING REQUEST-BUDGET FIX

This is the canonical fast-resume file. A fresh ChatGPT/Codex instance must read this first. Historical chronology/time ledger: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.

## 0. USER DIRECTIVE / CONTINUITY

The user explicitly authorized autonomous work and does NOT want interruptions for micro-decisions. Continue independently until a manual MT5 action is genuinely necessary.

The two authorized research tracks were:
1. D026 price-only strategy design/code/audit until MT5 backtests are the only blocker.
2. D025 XAU/Forex exploitation using existing datasets, without unnecessary reruns.

Both have now been pushed as far as possible without the user's MT5 terminal.

Do not ask the user to restate this after context/model limits.

---

# 1. D026 PRICE EXHAUSTION RECLAIM — CURRENT PRIMARY RESEARCH TRACK

D026 is a NEW strategy, not a retuned D025. Its baseline deliberately has no broker tick-volume dependency and no Binance/Bybit dependency.

## Rules lock — DONE BEFORE RESULTS

File:
- `research/campaigns/D026_PRICE_EXHAUSTION_RECLAIM_V0_RULES_LOCK_2026_09_04.md`
- creation commit `1137ffbe669504b1aa6b518480b94598f98e3f0c`

Frozen V0 architecture:
- objective levels: PDH/PDL/PWH/PWL + latest confirmed H1/H4 swing highs/lows;
- H1 ATR(14);
- M15 state machine;
- M1 path measurement;
- no round numbers;
- no volume/OI/funding/liquidation/RSI/EMA/session/symbol-specific gate.

Frozen thresholds:
- watch distance `0.50 x H1 ATR`;
- fresh sweep `0.10 x H1 ATR`;
- structural SL buffer `0.10 x H1 ATR` beyond worst sequence extreme;
- displacement range >= `1.25 x` mean previous 20 closed M15 ranges;
- directional body >= `0.20 x H1 ATR`;
- body/range efficiency >= `0.55`;
- LONG-reclaim bearish displacement close in bottom 30% of bar;
- SHORT-reclaim bullish displacement close in top 30%;
- exhaustion within next 3 M15: extra outward progress <= `0.20 x displacement range` AND current range <= `0.80 x displacement range`;
- reclaim within next 4 M15;
- validation within next 4 M15 by RETEST within `0.15 ATR` or ACCEPTANCE = two consecutive reclaimed-side closes;
- cooldown 4h.

State machine:
`IDLE -> WATCH -> SWEEP -> DISPLACEMENT -> EXHAUSTION -> RECLAIM -> RETEST/ACCEPTANCE -> VALID_SIGNAL`.

Virtual entry = validating CLOSED M15 close. 1R = abs(entry - structural SL). Same-M1 ordering ambiguity must never be guessed.

## D026 diagnostic EA — DONE

File:
- `research/ea/D026_PriceExhaustionReclaim_Virtual_V0_1_00.mq5`
- creation commit `d4e55b0a61a152158a6de20e24b356eb3c0cdc23`

Characteristics:
- pure virtual observer;
- no CTrade include;
- no order/position calls;
- no balance/margin/lot dependency;
- no tick_volume or real_volume dependency;
- output folder: `FILE_COMMON\GuardianResearch\D026\`;
- outputs: `d026_per_virtual_v0_events.csv`, `...trades.csv`, `...outcomes.csv`;
- tracks +0.5R, +1R..+5R, original SL, BE-after-1R, MFE/MAE, 1/4/8/24/48h, ambiguity flags.

Inputs only:
- `InpMaxHoldHours = 48`
- `InpTimerSeconds = 1`
- `InpVerbose = true`

Static audit:
- local source 678 lines;
- SHA-256 `653fe5ed9ecaf6419aa7bebf7ba6bd49939b0947ced19b0ba06919b75d9aa2da`;
- bracket/brace/parenthesis balance OK;
- executable scan: tick_volume=0, real_volume=0, AccountInfoDouble=0, OrderSend=0, PositionOpen/Modify/Close=0, Trade.mqh include=0.

IMPORTANT: static audit only. Do NOT claim successful MetaEditor compile until user confirms it.

## Predeclared analyzer — DONE BEFORE D026 RESULTS

File:
- `research/analysis/analyze_d026_per_v0.py`
- commit `7495d3edc7d3ef6cd3c1b61c660299f72cd4760a`

Analyzer is intentionally narrow:
- integrity/session counts;
- fixed +1R/+2R/+3R first-touch EV;
- year/side/path splits;
- Wilson-style uncertainty;
- one predeclared management family only: 40% at +1R, remaining 60% at BE, runner to +2R or +3R;
- same-M1 ambiguous paths excluded.

No threshold optimizer is authorized for V0.

## Static audit + exact test protocol

File:
- `research/results/D026_V0_STATIC_AUDIT_AND_TEST_PROTOCOL_2026_09_04.md`
- commit `037baf2118c7426700687512c81a8e1df2403075`

### ONLY USER ACTION NOW NEEDED FOR D026

When convenient:
1. compile `D026_PriceExhaustionReclaim_Virtual_V0_1_00.mq5` manually in MetaEditor;
2. run BTCUSD M1, 2024-01-01 -> 2025-12-31, inputs `48 / 1 / true`;
3. run ETHUSD same settings;
4. send cumulative `events + trades + outcomes` after both.

`Every tick` is sufficient for D026 V0 because its entry logic uses closed M15 OHLC/ATR and path logic uses closed M1 high/low. Do NOT require real-tick mode.

Do not request broader markets before BTC/ETH first verdict.

Acceptance bar remains high: tiny positive EV is insufficient; seek preferably >= ~+0.15R pre-cost and ideally ~+0.20R+ on a branch that repeats across years, then apply spread/commission/slippage and stress costs.

---

# 2. D025 XAU / FOREX EXPLOITATION — COMPLETE FOR CURRENT FROZEN ENTRY

Final report:
- `research/results/D025_XAU_FOREX_FINAL_EXPLOITATION_2026_09_04.md`
- commit `e4cc482df9a29fcf6acf10d5c3d4ebc30b2716ad`

Actual 1.01 / 1.02 / 1.03 CSVs were re-opened; no new broad reruns were requested.

## Final decisions

### XAUUSD
- 2024 overall nearly flat at +1R and negative beyond;
- 2025 clearly negative;
- 2024 RETEST and LONG effects fail 2025 replication;
- 1.02 n=798 remains negative overall;
- 40%@+1R + BE runner negative.

Decision: **REJECT D025 XAU production branch**.

### USDJPY
- 2024/2025 broad results flat-negative;
- Jun-Jul 2026 strength does not replicate backwards;
- 1.02 n=791 remains negative overall;
- partial+BE runner negative.

Decision: **REJECT broad D025 USDJPY production branch**.

### GBPUSD
Recurring original 1.01 SHORT early-target hint:
- 2024 SHORT EV1 ~+0.070R;
- 2025 SHORT EV1 ~+0.183R;
- Jun-Jul26 SHORT EV1 ~+0.118R;
- pooled original n421, EV1 ~+0.121R pre-cost.

But newer 1.02 GBP SHORT weakens materially: EV1 ~+0.050R, EV2 negative. Path leadership flips by year.

Decision: **GBP SHORT +1R = WATCHLIST ONLY, not production**. Broad GBP rejected.

### EURUSD
Strongest surviving non-crypto D025 watchlist hypothesis:
- 1.02 2024 SHORT EV2 ~+0.146R;
- 1.02 2025 SHORT EV2 ~+0.122R;
- pooled 2024-25 SHORT EV2 ~+0.136R pre-cost;
- tiny Jun-Jul26 SHORT sample supportive but insufficient.

Uncertainty remains large and monthly stability is weak. Costs are not deducted.

Decision: **EUR SHORT +2R = PRIMARY WATCHLIST ONLY, not production**.

### Partial +1R / BE runner
1.02 resolved EV for 40%@+1R + 60% BE runner:
- XAU -> +2R: ~-0.053R; -> +3R: ~-0.128R
- GBP: ~+0.017R / -0.012R
- USDJPY: ~-0.034R / -0.082R
- EUR: ~+0.047R / -0.020R

Decision: **REJECT this D025 non-crypto management rule**.

## D025 XAU/Forex conclusion

No branch meets the user's required large-edge standard. Do not spend more time optimizing exits on the same frozen population to manufacture a prettier result.

Prospective watchlist only:
1. EURUSD SHORT -> +2R.
2. GBPUSD SHORT -> +1R.

No further broad D025 XAU/Forex reruns are needed at this stage.

---

# 3. D025 CRYPTO DATA ISSUE — QUARANTINED

D025 V0 locked source/rules remain unchanged.

Critical D025 CASCADE gate = M15 relative tick volume >=1.25 vs prior-20 mean.

Current 1.03 virtual combined populations:
- BTC 499 = 298 in 2024 + 201 in 2025;
- ETH 553 = 358 + 195;
- DOG 595;
- XAU 798;
- USDJPY 793.

Original 1.01 separate-year totals were much larger for BTC/ETH:
- BTC 1117;
- ETH 1172.

Real-order/min-lot/margin hypothesis was falsified because virtual 1.03 still had the same low crypto signal population.

Mechanism identified:
- large historical BTC/ETH periods show relative tick volume collapsing near 1.0;
- frozen 1.25 CASCADE gate then mechanically cannot fire;
- e.g. BTC Aug 2024: 117 sweeps, median relvol ~0.999, max 1.243, zero CASCADE, zero signals.

User performed one controlled BTC rerun with `Every tick based on real ticks`. Result was effectively identical to prior `Every tick` data apart from session identity.

Therefore:
- `Every tick` vs `real ticks` is NOT the primary cause;
- remaining issue = FundedNext/MT5 historical tick-volume/feed provenance/availability;
- D025 crypto historical volume-dependent conclusions are QUARANTINED;
- do NOT lower the 1.25 threshold to compensate for bad/synthetic history.

D026 exists specifically to test a clean price-only alternative without waiting for this issue.

---

# 4. SHARED INTELLIGENCE

Binance + Bybit Shared Intelligence remains READ-ONLY and has no current trading effect.

Architecture:
Binance + Bybit collectors -> venue-separated state -> FILE_COMMON -> Guardian/research consumers.

Current external-intelligence scope BTC + ETH. Keep collector running.

Baseline D026 must NOT use this data. Later Crypto+ studies may compare D026 Core vs D026 + external features using strict `available_at <= event_time` anti-lookahead joins.

---

# 5. FUNDEDNEXT LIVE GUARDIAN REQUEST BUG — STILL HIGH PRIORITY, NOT YET PATCHED

FundedNext HUD observed about `5629/2000` while FTMO was ~32/2000.

Exact live lineage source found in Library:
`Guardian_D017_PropFirmAuto_v11_17_04_MANUAL_PROTECTION_HOTFIX_PLAN80_RUNNER20.mq5`.

Confirmed runaway-capable mechanism:
- after RSI TP1, failed BE NET application leaves `g_rsi_be_push_done=false`;
- `RSIManageCycleTick()` retries `RSI_BE_RETRY` while condition remains true;
- retry uses `SRP_PROTECTION`;
- `SRP_PROTECTION` bypasses request hard limit by design.

Broader `SRP_PROTECTION` audit must cover manual SL/BE, Momentum BE and other protection loops before patching only one callsite.

Operational rule:
- FundedNext Algo Trading stays OFF until bounded/deduplicated/backoff fix is built and validated;
- true emergency safety may keep priority;
- routine BE retries must not have unlimited hard-limit bypass.

Potential v11.17.07 concept already agreed in principle:
- initial protective attempt preserved;
- routine deferred BE retries use bounded/dedup/backoff cadence such as 5s -> 15s -> 60s -> 5min;
- retry priority should be profit-protection rather than unlimited emergency protection where safety is not worsened.

Do NOT claim this patch is already finished. It is not yet committed.

---

# 6. FUNDEDNEXT QUICK STRIKE — USER-CORRECTED REQUIREMENT

User-confirmed behavior:
- Guardian does NOT auto-close a manual position simply because initial SL placement fails;
- current behavior: one SL-placement attempt, then user manually places SL if it failed.

Separate concern:
- Guardian-managed profitable exits inside 30 seconds can create Quick Strike exposure.

Future patch must:
- log entry time, elapsed seconds, reason, venue and P/L sign for Guardian-managed <30s exits;
- never intentionally leave unsafe risk open merely to cross 30 seconds;
- integrate any retry logic with request-budget safeguards.

GitHub issue #2 contains the corrected requirement.

---

# 7. NEXT RESUME ORDER

1. `CURRENT_PROJECT_HANDOFF.md`
2. `research/results/D026_V0_STATIC_AUDIT_AND_TEST_PROTOCOL_2026_09_04.md`
3. `research/campaigns/D026_PRICE_EXHAUSTION_RECLAIM_V0_RULES_LOCK_2026_09_04.md`
4. `research/ea/D026_PriceExhaustionReclaim_Virtual_V0_1_00.mq5`
5. `research/analysis/analyze_d026_per_v0.py`
6. `research/results/D025_XAU_FOREX_FINAL_EXPLOITATION_2026_09_04.md`
7. `research/results/D025_1_03_VIRTUAL_PATH_DIAGNOSTIC_2026_09_04.md`
8. latest Guardian request-budget audit + exact current Guardian source
9. `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`
10. `docs/STRATEGY_DECISIONS.md`

## Immediate dependency

Research is now blocked only by the user's manual MT5 action for D026: compile the V0 EA and run BTCUSD + ETHUSD 2024-2025. Do not ask for anything else first unless compile errors occur.

## Continuity rule

After every material milestone, update this handoff in the same work session. Important state must never exist only in conversation context.