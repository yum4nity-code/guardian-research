# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-04 18:50 Europe/Paris
Status: ACTIVE / D025 1.03 VIRTUAL PATH RERUNS STARTING / SHARED INTELLIGENCE LIVE READ-ONLY / FUNDEDNEXT LIVE AUTO SUSPENDED PENDING REQUEST-BUDGET FIX

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

Therefore keep two issues separate:
1. SL-placement failure/retry safety.
2. Quick Strike exposure from any Guardian-managed profitable closure inside 30 seconds.

Requirement:
- log entry time, elapsed seconds, venue, reason and P/L sign for Guardian-managed <30s exits;
- evaluate FundedNext-specific early BE/SL handling only if risk-neutral;
- never intentionally leave an unsafe trade open just to pass 30 seconds.

GitHub issue: #2.

## 6. D025 Trading 1.01 — what it proved

Source: `research/ea/D025_LER_Trading_1_01.mq5`.

Long BTC/ETH test with market entry, structural SL, no TP, forced 48h exit lost badly. Correct conclusion:
- REJECT that exit construction.
- Do NOT reject D025 entry from that P/L alone.

First-touch and later cross-asset work showed D025 has no universal fixed-TP edge across all markets. Branch/regime separation matters.

Recurring observations before costs:
- ETH RETEST = strongest repeatedly positive branch; pooled +2R EV around +0.133R before costs.
- BTC SHORT = modest recurring early edge; around +0.096R at 1R pooled.
- GBP SHORT = recurring early edge; around +0.121R at 1R pooled.
- SOL SHORT = promising and larger in available sample, but less mature / no 2024 sample and current FundedNext symbol availability is uncertain.
- XAU RETEST 2024 did not replicate in 2025.
- USDJPY 2026 strength did not robustly replicate backward.

Universal D025 fixed TP is not accepted.

## 7. D025 1.02 Path Diagnostic — instrumentation valid, real-order sample biased

Source: `research/ea/D025_LER_Trading_1_02_PathDiagnostic.mq5`.

Added observational path fields:
- first +0.5R;
- +1R..+5R;
- first return to entry after +1R (`be_after1_utc`);
- same-M1 BE/target ambiguity flag.

A 0.05% real-order rerun did NOT remove crypto selection bias:
- BTC population only about 44% of prior expected 2024+2025 signal population.
- ETH only about 46%.
- GBP/USDJPY/XAU were around 91–94% controls.

Conclusion:
- 1.02 instrumentation is useful.
- Real-order path sampling is NOT scientifically clean for BTC/ETH because lot minimum/account/margin/execution state can filter signals.
- Do not ask for more BTC/ETH real-order 0.05 reruns.

Report: `research/results/D025_1_02_005PCT_RERUN_DIAGNOSTIC_2026_09_04.md`.

## 8. D025 1.03 Virtual Path Diagnostic — CURRENT TEST EA

Current user-facing source created in conversation: `D025_LER_VirtualPath_1_03.mq5`.

Purpose:
- keep the locked V0 signal chain and structural stop;
- remove ALL actual CTrade/order dependence;
- no lot sizing, no margin, no account equity dependency, no live P/L effect;
- create a virtual record for every VALID_SIGNAL;
- virtual entry = modeled market side at signal (Ask long / Bid short);
- track structural stop, +0.5R, +1R..+5R, BE-after-1R and 48h path;
- overlapping virtual trades allowed;
- same-M1 ordering ambiguity must remain explicit.

User has compiled/started using this manually; do not claim MetaEditor compile on behalf of assistant beyond user-confirmed successful use/output.

### Current rerun request

Run 2024-01-01 -> 2025-12-31 with default inputs `48 / 1 / true`.

Priority:
1. BTCUSD
2. ETHUSD
3. XAUUSD
4. GBPUSD
5. USDJPY
6. EURUSD

SOL is optional only if the symbol is available again on FundedNext. User currently cannot find SOL there.

For each symbol collect ALL THREE CSVs:
- events
- trades
- outcomes

First validation: BTC/ETH virtual signal population must recover the missing sample versus 1.02 real-order runs. If counts remain unexpectedly low, inspect signal/session logic before requesting broad reruns.

## 9. D025 management research standard

Do not optimize dozens of exits.

Current conceptual candidates remain narrow:
- full TP +1R;
- full TP +2R;
- partial around +1R then BE/runner path observation.

But the user has explicitly set a higher bar: **do not settle for crumbs**.

Interpret current pre-cost EV as signal-quality diagnostics only. Spread, commission and slippage are NOT yet fully applied to those R-EV figures.

Acceptance philosophy:
- tiny pre-cost edge is not enough;
- seek a broad, repeated structural advantage across years/branches;
- then apply realistic spread + commission + slippage;
- stress costs upward before production consideration.

Do not curve-fit entry thresholds or invent retrospective filters.

## 10. Shared Intelligence relation to D025

Current D025 Core does NOT use Binance/Bybit data for entry, SL or exit.

External Intelligence is a later Crypto+ research layer only:
- spot/perp;
- OI;
- funding;
- liquidations;
- basis/dislocation;
- Binance/Bybit agreement/divergence;
- quality/staleness.

Future comparison must be `D025 Core` vs `D025 Core + external state`, joined strictly with `available_at <= event_time`.

Current collector has already produced thousands of raw observations and continues building forward BTC/ETH history. Do not use current live snapshot as historical truth in Strategy Tester.

## 11. Project planning / work-time ledger

New canonical living file:
- `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`

It reconstructs Guardian history back to the initial manual-trade-manager conversations in mid-August 2026, including pre-GitHub work. Historical hours are labelled as confirmed activity spans/minimums/unknown when precise active time cannot be justified.

From now on maintain:
- session start/end;
- human active time;
- unattended backtest/collector runtime separately;
- done/decision/rejected/next items.

## 12. Resume order

1. `CURRENT_PROJECT_HANDOFF.md`
2. `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`
3. current D025 1.03 virtual-path source/output
4. `research/results/D025_1_02_005PCT_RERUN_DIAGNOSTIC_2026_09_04.md`
5. `research/results/D025_2025_REPLICATION_DIAGNOSTIC_2026_09_04.md`
6. latest FundedNext request-budget audit / current Guardian v11.17.x source
7. `research/results/D025_ENTRY_QUALITY_DIAGNOSTIC_2026_09_04.md`
8. `research/results/D025_CROSS_ASSET_FIRST_TOUCH_DIAGNOSTIC_2026_09_04.md`
9. branch `live-status` -> `LIVE_RESEARCH_STATUS.json`
10. `docs/STRATEGY_DECISIONS.md`
11. locked D025 V0 rules

## 13. Continuity rule

After every material milestone, update this handoff in the same work session. Keep the planning/time ledger current as well. No important state should exist only in conversation context.