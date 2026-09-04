# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-04 19:55 Europe/Paris
Status: ACTIVE / AUTONOMOUS WORK DIRECTIVE: D026 PRICE-ONLY DESIGN+CODE + D025 XAU/FOREX EXPLOITATION / D025 CRYPTO VOLUME DATA QUARANTINED / FUNDEDNEXT LIVE AUTO OFF PENDING REQUEST-BUDGET FIX

This is the canonical fast-resume file for a fresh ChatGPT/Codex instance. Read it first, then verify actual live/local state before changing anything.

Historical chronology, planning and work-time ledger: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.

## 0. CURRENT USER DIRECTIVE — DO NOT LOSE THIS

User explicitly authorized autonomous work on TWO parallel research tracks and does not want to be interrupted for micro-decisions:

### Track A — D026 Price-Only Exhaustion/Reclaim
Goal: create a new crypto-capable strategy that does NOT depend on broker tick volume, while keeping the useful structural idea behind D025.

Assistant may autonomously:
- design and freeze D026 rules BEFORE looking at D026 results;
- code a virtual/diagnostic EA;
- static-audit it;
- document methodology and acceptance criteria;
- prepare the BTC/ETH backtest protocol;
- continue until the only remaining dependency is the user's manual MT5 test launch.

Do NOT ask the user to make small design choices unless genuinely unavoidable. The user should only be needed when a manual MT5 run becomes indispensable.

Scientific constraints:
- no D025 threshold retuning disguised as D026;
- no broker tick-volume dependency;
- prioritize price structure, ATR-normalized range/body/progress, sweep, exhaustion, reclaim/retest;
- rules frozen pre-result;
- no broad parameter optimization;
- large edge required, not crumbs;
- later costs/stress tests mandatory before production.

### Track B — D025 XAU / Forex exploitation
Goal: extract the maximum scientifically defensible value from existing D025 XAU/Forex datasets without asking user for unnecessary reruns.

Assistant may autonomously:
- re-open prior CSVs from conversation/library;
- isolate sessions/symbol/year/path/side;
- compare 2024 vs 2025 and available 2026 diagnostics;
- evaluate fixed TP and path branches from already-recorded first-touch data;
- identify robust/rejected branches;
- document results and decisions in GitHub;
- avoid pretending spread/commission/slippage are already included where they are not.

Current priority non-crypto markets: XAUUSD, GBPUSD, USDJPY, EURUSD where available.

The user said, effectively: write all of this in the handoff and work until these two tracks are pushed as far as possible. Respect that continuity even if model/conversation limits force a new instance.

## 1. Live Guardian / Shared Intelligence

- Guardian 17 lineage = v11.17.x multi-venue Shared Intelligence observer.
- Shared Intelligence is READ-ONLY and has NO direct trading effect.
- Architecture: Binance + Bybit collectors -> venue-separated state -> FILE_COMMON bridge -> Guardian/research consumers.
- Windows autostart task: `Guardian Shared Intelligence MultiVenue V1`.
- Live-status mirror: branch `live-status`, file `LIVE_RESEARCH_STATUS.json`.
- BTCUSD + ETHUSD are the current external-intelligence scope.
- Aspirator/Shared Intelligence is unrelated to Guardian server-request counts and may stay running.

## 2. D025 LER Core

- D025 = Liquidity Exhaustion Reclaim.
- Original observer source: `research/ea/D025_LER_Observer_V0.mq5`.
- V0 entry rules are LOCKED: `research/campaigns/D025_LER_V0_RULES_LOCK_2026_09_04.md`.
- State machine: `IDLE -> LEVEL_WATCH -> SWEEP -> CASCADE -> EXHAUSTION -> RECLAIM -> RETEST/ACCEPTANCE -> VALID_SIGNAL`.
- Do NOT tune V0 thresholds post hoc.
- Structural SL remains part of the definition of R and must not be tightened merely to improve backtest output.
- Critical frozen CASCADE rule includes M15 relative tick volume >= `1.25` versus previous-20 mean.

## 3. Exact FundedNext target

User-confirmed MT5 target:
- account `14202634`
- server `FundedNext-Server 2`
- Hedge
- company FundedNext Ltd
- executable `D:\MT5_FundedNext\terminal64.exe`
- data path `C:\Users\armor\AppData\Roaming\MetaQuotes\Terminal\D943DED8A972BBD3A21ED90520AE6479`

FundedNext automation wrappers V1/V2/V3/V4 are SUSPENDED. Do not ask the user to debug launcher/shell wrappers. Normal manual MT5 Strategy Tester workflow is the preferred path.

## 4. FundedNext server-request anomaly — HIGH PRIORITY OPERATIONS ISSUE

Live observation 2026-09-04:
- FundedNext HUD reached about `5629/2000 (281.4%) | HARD LIMIT | PROTECTION ONLY`.
- FTMO Guardian had only about `32/2000 (1.6%) | NORMAL` after long runtime.

Exact live lineage source found in Library:
- `Guardian_D017_PropFirmAuto_v11_17_04_MANUAL_PROTECTION_HOTFIX_PLAN80_RUNNER20.mq5`.

Confirmed runaway-capable path:
- after TP1, if BE NET is not applied, `RSIManageCycleTick()` calls `RSI_BE_RETRY` again whenever the condition remains true;
- `RSI_BE_RETRY` uses `SRP_PROTECTION`;
- `SRP_PROTECTION` bypasses the hard request budget by design.

Operational rule:
- FundedNext Algo Trading remains OFF until bounded retry/backoff/dedup patch is built and validated.
- Shared Intelligence may remain ON.
- Do not reset the counter merely to clear HUD.
- True emergency protection must retain priority; routine BE retries must not behave as unlimited emergency traffic.

A v11.17.07 patch is a separate high-priority operational track, but the current user directive explicitly prioritizes autonomous D026 + D025 XAU/Forex research while no manual input is needed.

## 5. FundedNext Quick Strike — corrected requirement

User correction 2026-09-04:
- Guardian does NOT auto-close a manual position when initial SL placement fails.
- Guardian currently makes one SL placement attempt; if it fails, the user places the SL manually.

Keep two issues separate:
1. SL-placement failure/retry safety.
2. Quick Strike exposure from any Guardian-managed profitable closure inside 30 seconds.

Requirement:
- log entry time, elapsed seconds, venue, reason and P/L sign for Guardian-managed <30s exits;
- evaluate FundedNext-specific early BE/SL handling only if risk-neutral;
- never intentionally leave an unsafe trade open just to pass 30 seconds.

GitHub issue: #2.

## 6. D025 Trading 1.01 — baseline findings

Source: `research/ea/D025_LER_Trading_1_01.mq5`.

Original full-year 1.01 sessions directly re-opened from prior conversation uploads:
- BTC 2024 = 614 unique trades; BTC 2025 = 503.
- ETH 2024 = 615; ETH 2025 = 557.
- XAU 2024 = 450; XAU 2025 = 399.
- USDJPY 2024 = 442; USDJPY 2025 = 424.
- GBP 2024 = 409; GBP 2025 = 360.
- SOL 2025 partial-year = 330.

Earlier branch diagnostics before costs:
- ETH RETEST repeatedly positive in original 1.01 population.
- BTC SHORT modest recurring early edge.
- GBP SHORT recurring early edge.
- SOL SHORT promising but less mature.
- XAU RETEST 2024 did not replicate in 2025.
- USDJPY 2026 strength did not robustly replicate backward.
- universal D025 fixed TP is not accepted.

## 7. D025 1.02 / 1.03 crypto data diagnosis — CURRENT CORRECTION

1.02 real-order low BTC/ETH population was initially blamed mainly on order/min-lot/margin selection. 1.03 virtual disproved that as the main cause.

1.03 virtual current combined 2024-2025 counts:
- BTC 499 = 298 + 201.
- ETH 553 = 358 + 195.
- DOG 595 = 302 + 293.
- XAU 798 = 432 + 366.
- USDJPY 793 = 401 + 392.

No BAD_RISK/NO_SLOT virtual rejections.

Mechanism identified:
- crypto historical relative tick volume collapses toward ~1.0 in large blocks;
- frozen CASCADE condition `rel_tick_volume >=1.25` then cannot fire;
- BTC Aug 2024: 117 sweeps, median relvol ~0.999, max 1.243, zero CASCADE, zero signal;
- ETH Aug/Sep 2024 similarly nearly dead;
- XAU control does not show the same collapse and recovers ~94% of old population.

Strategy Tester screenshot showed `Every tick`. A controlled BTC rerun with `Every tick based on real ticks` was then supplied by user.

IMPORTANT NEW RESULT:
- BTC real-ticks control produced the SAME 499-trade cumulative population / same data content apart from session identity as the earlier run;
- therefore switching MT5 modelling mode does **not** solve the D025 crypto data problem;
- hypothesis `Every tick vs real ticks` as primary cause is REJECTED;
- remaining issue is historical feed/tick-volume provenance/availability from FundedNext/MT5 history, not D025 order execution and not simply tester model selection.

D025 crypto historical results that depend on this relative-volume gate are QUARANTINED until a trustworthy volume source/provenance exists. Do not lower 1.25 to compensate.

## 8. D025 XAU/Forex — ACTIVE AUTONOMOUS RESEARCH TRACK

Use existing datasets first. Do not request reruns merely for convenience.

Known 2024 first-touch EV (pre-cost):
- GBP n409: EV1 about -0.010R, EV2 +0.025R, EV3 -0.064R; RETEST better than ACCEPTANCE; GBP SHORT observationally better.
- USDJPY n442: EV1 +0.019R, EV2 -0.084R, EV3 -0.136R; RETEST better than ACCEPTANCE; LONG observationally better.
- XAU n450: EV1 +0.007R, EV2 -0.055R, EV3 -0.152R; XAU RETEST 2024 was strong (EV1 ~+0.090, EV2 ~+0.158, EV3 ~+0.042), but side LONG also looked better.

Known 2025 replication (pre-cost):
- GBP n360: EV1 +0.107R, EV2 +0.033R, EV3 -0.134R.
- USDJPY n424: EV1 -0.027R, EV2 -0.055R, EV3 -0.114R.
- XAU n399: EV1 -0.100R, EV2 -0.220R, EV3 -0.260R.
- XAU RETEST did NOT replicate; do not promote.
- GBP SHORT pooled 2024+2025+small 2026 had recurring early edge around EV1 +0.121R, EV2 +0.072R, EV3 around flat/negative; path leadership flips by year, so path-specific GBP rule is not validated.
- USDJPY 2026 strength failed backward replication; do not promote universal USDJPY branch.

Autonomous task now: reopen actual CSVs, quantify confidence/sample consistency, isolate side/path/year and produce a final XAU/Forex verdict report. Require large margin; no crumbs.

## 9. D026 Price-Only Exhaustion/Reclaim — ACTIVE AUTONOMOUS DESIGN TRACK

D026 is NEW. It is not a patch to D025 and must receive its own rules lock before any D026 result is inspected.

Design intent:
- preserve structural concept: liquidity sweep -> directional displacement -> measurable exhaustion -> reclaim -> confirmation/retest;
- remove broker tick-volume completely;
- use only reproducible OHLC/time/ATR-derived quantities available from MT5 price history;
- crypto-first BTC/ETH applicability, but portable to other venues/brokers;
- no dependency on Binance/Bybit for baseline D026; external data can later be a separate Crypto+ layer.

The assistant is authorized to decide the initial frozen thresholds using documented/structural reasoning, not retrospective result optimization, then code a virtual logger and prepare BTC/ETH tests.

Only when D026 source is frozen/audited and manual tester execution is genuinely needed should the user be asked to run BTC/ETH and return events/trades/outcomes.

## 10. D025/D026 management research standard

User requirement: **do not settle for crumbs**.

Pre-cost EV is not production EV. Spread, commission, slippage and stress-cost tests must later be applied.

Acceptance philosophy:
- broad pre-cost advantage should preferably be >= ~+0.15R/trade and ideally ~+0.20R+ before considering production work;
- consistency across years/regimes/branches matters more than one pooled good number;
- small sample branches must not be promoted;
- no curve fitting / no broad parameter sweep;
- same-M1 ordering ambiguity must remain explicit in path diagnostics.

## 11. Shared Intelligence relation

Current D025 Core and future baseline D026 do NOT use Binance/Bybit data for entry/SL/exit.

External Intelligence is a later optional Crypto+ layer:
- spot/perp;
- OI;
- funding;
- liquidations;
- basis/dislocation;
- Binance/Bybit agreement/divergence;
- quality/staleness.

Any later event study must join strictly with `available_at <= event_time`.

## 12. Project planning / work-time ledger

Canonical living file: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.

Update it after material D025/D026 milestones. Track human active time separately from unattended MT5/collector runtime.

## 13. Resume order

1. `CURRENT_PROJECT_HANDOFF.md`
2. `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`
3. D026 rules-lock / source / audit created after this directive
4. D025 XAU/Forex final exploitation report created after this directive
5. `research/results/D025_1_03_VIRTUAL_PATH_DIAGNOSTIC_2026_09_04.md`
6. `research/ea/D025_LER_VirtualPath_1_03.mq5`
7. current 1.03 virtual CSVs
8. original 1.01/1.02 CSV sessions from conversation/library
9. latest FundedNext request-budget audit / current Guardian source
10. branch `live-status` -> `LIVE_RESEARCH_STATUS.json`
11. `docs/STRATEGY_DECISIONS.md`
12. locked D025 V0 rules

## 14. Continuity rule

After every material milestone, update this handoff in the same work session. Keep planning/time ledger current. No important state should exist only in conversation context. If context/model limits interrupt the work, the next instance must continue the D026 + D025 XAU/Forex autonomous directive rather than asking the user to restate it.