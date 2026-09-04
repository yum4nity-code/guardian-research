# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-04 20:35 Europe/Paris
Status: ACTIVE / D025 1.03 CRYPTO POPULATION MECHANISM IDENTIFIED: TICK-VOLUME COLLAPSE BLOCKS CASCADE / UNDERLYING TESTER-DATA PROVENANCE STILL TO CONFIRM / SHARED INTELLIGENCE LIVE READ-ONLY / FUNDEDNEXT LIVE AUTO SUSPENDED PENDING REQUEST-BUDGET FIX

This is the canonical fast-resume file for a fresh ChatGPT/Codex instance. Read it first, then verify actual live/local state before changing anything.

Historical chronology, planning and work-time ledger: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.

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

## 4. FundedNext server-request anomaly — HIGH PRIORITY

Live observation 2026-09-04:
- FundedNext HUD reached about `5629/2000 (281.4%) | HARD LIMIT | PROTECTION ONLY`.
- FTMO Guardian had only about `32/2000 (1.6%) | NORMAL` after long runtime.

Known mechanism capable of runaway:
- Guardian counter is account/day scoped and increments before CTrade send, so rejected attempts still count locally.
- `SRP_EMERGENCY` and `SRP_PROTECTION` bypass hard budget by design.
- strongest static suspect: repeated `RSI_BE_RETRY` / common-stop protection work evaluated tick-by-tick while unapplied.

This proves a runaway-capable path, not that every one of 5629 attempts reached FundedNext.

Operational rule:
- FundedNext Algo Trading remains OFF until bounded retry/backoff/dedup patch is built and validated.
- Shared Intelligence may remain ON.
- Do not reset the counter merely to clear HUD.
- Audit all `SRP_PROTECTION` retry loops; preserve true emergency protection bypass.

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

Long BTC/ETH test with market entry, structural SL, no TP, forced 48h exit lost badly. Correct conclusion:
- REJECT that exit construction.
- Do NOT reject D025 entry from that P/L alone.

Original full-year 1.01 sessions directly re-opened from prior conversation uploads:
- BTC 2024 = 614 unique trades; BTC 2025 = 503.
- ETH 2024 = 615; ETH 2025 = 557.
- XAU 2024 = 450; XAU 2025 = 399.
- USDJPY 2024 = 442; USDJPY 2025 = 424.
- No duplicate event IDs in those full-year sessions.

Earlier branch diagnostics before costs:
- ETH RETEST repeatedly positive in the original 1.01 population.
- BTC SHORT modest recurring early edge.
- GBP SHORT recurring early edge.
- SOL SHORT promising but less mature.
- XAU RETEST 2024 did not replicate in 2025.
- USDJPY 2026 strength did not robustly replicate backward.

Universal D025 fixed TP is not accepted.

## 7. D025 1.02 Path Diagnostic — historical instrumentation / causal diagnosis superseded

Source: `research/ea/D025_LER_Trading_1_02_PathDiagnostic.mq5`.

Added +0.5R, +1R..+5R, first return to entry after +1R and same-M1 path ambiguity.

The 0.05% real-order combined 2024-2025 sessions produced much smaller BTC/ETH populations than the original 1.01 separate-year sessions.

Previous interpretation that lot minimum/account/margin/order execution was the main cause is **SUPERSEDED**. 1.03 virtual shows the low signal population persists with zero orders.

Keep `research/results/D025_1_02_005PCT_RERUN_DIAGNOSTIC_2026_09_04.md` only as historical evidence; do not reuse its old causal conclusion.

## 8. D025 1.03 Virtual Path Diagnostic — CURRENT MILESTONE

Canonical source is now committed:
- `research/ea/D025_LER_VirtualPath_1_03.mq5`
- creation commit `0a54a018b3b5bfcfcd8fbbac7c7bbee1bbb4d664`

Characteristics:
- no CTrade;
- no orders or positions;
- no lot sizing, margin, equity or execution-success dependency;
- locked V0 signal chain;
- structural stop only as virtual reference;
- +0.5R, +1R..+5R, stop, BE-after-1R, 48h path;
- overlapping virtual trades allowed;
- same-M1 ambiguity explicit.

User supplied cumulative 1.03 CSVs containing five complete 2024-2025 sessions: BTCUSD, ETHUSD, DOGUSD, XAUUSD, USDJPY.

1.03 trade counts:
- BTC 499 = 298 in 2024 + 201 in 2025.
- ETH 553 = 358 + 195.
- DOG 595 = 302 + 293.
- XAU 798 = 432 + 366.
- USDJPY 793 = 401 + 392.

Zero `VALID_SIGNAL_REJECTED_BAD_RISK`; zero `VALID_SIGNAL_REJECTED_NO_SLOT`. Every VALID_SIGNAL became a virtual trade.

Comparison:
- BTC 1.03 499 vs 1.02 real-order 490 vs original 1.01 separate-year total 1,117.
- ETH 553 vs 544 vs 1,172.
- XAU 798 vs 798 vs 849.
- USDJPY 793 vs 791 vs 866.

### Mechanism now identified: historical crypto tick-volume collapse

D025 CASCADE requires relative M15 tick volume >=1.25. Current 1.03 event data shows large BTC/ETH historical segments where relative tick volume collapses to ~1.0 and becomes nearly flat, mechanically preventing CASCADE.

BTC 2024:
- Jul median relvol ~1.290, 65/120 sweeps >=1.25, 61 CASCADEs.
- **Aug median ~0.999, max 1.243, 0/117 >=1.25, 0 CASCADEs, 0 signals.**
- Sep median ~0.995, only 16/126 >=1.25, 12 CASCADEs, 4 signals.
- Oct median ~1.896, 105/134 >=1.25, 89 CASCADEs, 43 signals.

ETH 2024:
- Jul median ~1.499, 73/119 >=1.25, 63 CASCADEs.
- **Aug median ~1.043, only 4/121 >=1.25, 2 CASCADEs, 2 signals.**
- **Sep median ~1.031, only 1/117 >=1.25, 3 CASCADEs, 1 signal.**
- Oct median ~1.406, 70/131 >=1.25, 61 CASCADEs, 25 signals.

Original 1.01 had 52 BTC trades in Aug 2024 + 51 in Sep, and 47 ETH + 48 respectively, proving the old runs saw materially different usable volume/bar provenance.

2025 current 1.03 makes the issue even clearer: from Aug-Dec BTC/ETH median relative volume stays near 1.00 and very few sweeps exceed 1.25.

XAU control does NOT collapse the same way in Aug-Sep 2024 and recovers ~94% of prior signal count. USDJPY is also much closer.

**Immediate missing-signal mechanism: PROVEN — collapsed/synthetic historical tick volume blocks frozen CASCADE filter.**

**Underlying reason the old and current histories differ: NOT YET PROVEN.** Candidate categories: tester modeling mode, historical feed/cache/data availability, terminal/broker provenance. Frequent old-vs-new BTC 2024 signal timing offsets of +60min and 0min support a provenance/configuration difference.

Do NOT change the 1.25 threshold to compensate for bad/synthetic history.

Full report: `research/results/D025_1_03_VIRTUAL_PATH_DIAGNOSTIC_2026_09_04.md`, updated commit `501776124b59e6fd1b17d0b44bce1cca387d4ab3`.

## 9. Current 1.03 outcome observations — PRELIMINARY ONLY

Resolved fixed-TP EV, before spread/commission/slippage, in the current 1.03 population:
- BTC global: EV0.5 +0.007R; EV1 +0.046R; EV2 -0.002R; EV3 -0.125R.
- ETH global: -0.039R; -0.053R; -0.090R; -0.100R.
- DOG global: -0.115R; -0.106R; -0.170R; -0.272R.
- XAU global: +0.021R; -0.011R; -0.068R; -0.148R.
- USDJPY global: -0.029R; -0.036R; -0.043R; -0.137R.

Interesting but not promotable while crypto data provenance is unresolved:
- BTC SHORT pooled current 1.03: n=256, EV1 ~+0.174R, EV2 ~+0.192R; 2024 very strong, 2025 much weaker.
- XAU RETEST pooled: EV1 ~+0.104R, EV2 ~+0.077R; weaker in 2025.
- DOG SHORT pooled: EV1 ~+0.076R, EV2 ~+0.068R.
- ETH RETEST current 1.03 does not confirm the original 1.01 finding.

Runner path among +1R winners, non-ambiguous cases: +2R before BE roughly 47-53% across tested symbols. No production management rule is authorized from this alone.

## 10. D025 management research standard

User requirement: **do not settle for crumbs**.

Current diagnostics remain before full trading costs. Spread, commission and slippage are not yet fully included in the R-EV figures.

Acceptance philosophy:
- tiny pre-cost edge is not enough;
- seek a broad, repeated structural advantage across years/branches;
- then apply realistic spread + commission + slippage;
- stress costs upward before production consideration;
- no curve fitting, no retrospective entry-threshold tuning.

## 11. Immediate D025 next step — NO BROAD RERUNS

Do NOT ask the user to run GBP/EUR/other broad 1.03 batches yet.

The strategy code no longer needs a broad rerun to explain the count difference. The next diagnostic is only to identify **why the current tester/history supplies flattened crypto tick volume** compared with the old 1.01 runs.

Simplest next evidence: current Strategy Tester **Settings** showing modeling mode + date range. No shell commands. If modeling mode does not explain it, investigate historical feed/cache/server provenance next.

## 12. Shared Intelligence relation to D025

Current D025 Core does NOT use Binance/Bybit data for entry, SL or exit.

External Intelligence is a later Crypto+ research layer only: spot/perp, OI, funding, liquidations, basis/dislocation, Binance/Bybit agreement/divergence, quality/staleness.

Future comparison must be `D025 Core` vs `D025 Core + external state`, joined strictly with `available_at <= event_time`.

Current collector has already produced thousands of raw observations and continues building forward BTC/ETH history. Do not use current live snapshot as historical truth in Strategy Tester.

## 13. Project planning / work-time ledger

Canonical living file: `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`.

It reconstructs Guardian history back to mid-August 2026 and distinguishes confirmed activity spans, minimum observed time and unknown historical duration. Going forward track human active time separately from unattended backtest/collector runtime.

## 14. Resume order

1. `CURRENT_PROJECT_HANDOFF.md`
2. `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`
3. `research/results/D025_1_03_VIRTUAL_PATH_DIAGNOSTIC_2026_09_04.md`
4. `research/ea/D025_LER_VirtualPath_1_03.mq5`
5. current 1.03 virtual CSVs
6. original 1.01 full-year CSV sessions from conversation files
7. `research/results/D025_2025_REPLICATION_DIAGNOSTIC_2026_09_04.md`
8. latest FundedNext request-budget audit / current Guardian v11.17.x source
9. branch `live-status` -> `LIVE_RESEARCH_STATUS.json`
10. `docs/STRATEGY_DECISIONS.md`
11. locked D025 V0 rules

## 15. Continuity rule

After every material milestone, update this handoff in the same work session. Keep the planning/time ledger current as well. No important state should exist only in conversation context.