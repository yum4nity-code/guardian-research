# NEXT_AI_HANDOFF — Guardian Edge Factory

## Mission
Continue Guardian Edge Factory exactly from the current scientific state. Optimize for **fast, explicit, reproducible tests** with minimal ceremony. Prefer short vectorized campaigns, frozen specs, receipts, hashes, and immediate stop/go decisions over long monolithic research jobs.

## Operator expectations
The user values speed, autonomy, and decisive execution.
- Do not ask unnecessary clarification when repo state + mandate answer the question.
- Inspect current repo files before writing new runners.
- Give one paste-ready PowerShell block when user action is needed.
- Any job longer than a few minutes must expose progress: step/total, %, elapsed, ETA, trial count, provisional survivors, current market/candidate.
- Prefer small test -> inspect -> full.
- Do not make the user run blind computations.
- If a bug appears, patch quickly, commit, and give only the rerun block.
- Keep replies direct and concise.

## Scientific operating rules
- Risk management does not create alpha.
- Free data only unless user explicitly changes this.
- FACT / INFERENCE / HYPOTHESIS / UNKNOWN.
- Causal timestamps only. If publication timing is uncertain, lag conservatively.
- Use vectorized / cached / resumable code.
- Every campaign writes receipts with hashes, periods touched, candidate counts, runtime/errors, and explicit OOS assertions.
- Never silently retune after a freeze.
- Never open 2023-2025 without an explicit pre-OOS gate and human review.
- 2026 protected/unopened.
- For overlapping targets, use non-overlap / purging / embargo where applicable.
- Stress tails, neighboring thresholds, lag sensitivity, cost/delay, best-trade/day removal, year stability, bootstrap/nulls, and multiplicity where relevant.
- A sharp optimum is negative evidence.

## Temporal split
- Discovery: 2010-2013
- Replication: 2014-2017
- Validation: 2018-2022
- Locked OOS: 2023-2025
- Protected: 2026
Do not use later windows to choose features/thresholds/models.

## Canonical navigation
Read, in order:
1. GUARDIAN_MASTER_MANDATE.md
2. EDGE_FAMILY_MAP.md
3. CURRENT_PROJECT_HANDOFF.md
4. START_HERE_NEXT_AI.md
5. CURRENT_QUEUE.json
6. this file: NEXT_AI_HANDOFF.md
7. latest runner + latest receipt for the active lineage

Older D0xx/Rxx work is provenance only unless a canonical file points to it.

## Important historical failures — do not blindly retest
- E2_DIVERSE_SCORE_5 / LONG_18_24: final fail.
- London Gold Fix AM/PM: fail.
- Simple volatility expansion 2x/3x continuation/reversal: fail.
- XAU M5 simple price-action Mega Atlas: dead.
- GBP60 V3-V10: dead due confirmed M5 timestamp lookahead; V11 causal rebuild negative.
- XAG zret_12b H240 P97.5 reversal: validation survived but failed strict pre-OOS tail gate.
- Cross-market XAG/XAU divergence V20-V28: closed before OOS.
- Clean XAG-only extreme-return MR V29-V31: closed.
- Volatility-regime x shock V32-V37: closed before OOS; V37 failed trim-best-2%.

Do not weaken old gates to rescue dead lineages.

## Current active lineage: implied volatility state / term structure

### V38 source/timestamp audit
- Design SHA256: 55cc16eb815dd45d6c1965c0348ba278a0014a699dd616e0ed6a803a870c8b89
- Sources confirmed: VIX, VIX9D, VVIX, GVZ, OVX, CFE volume/OI
- Conservative policy: daily Cboe/CFE observation is not used same day unless explicit trustworthy timestamp exists; lag to next trading observation.
- No alpha window consumed in V38.

### V39 discovery
Run: GEF39-20260920-120810
- Family: implied volatility state / term structure
- Discovery 2010-2013 only; VIX9D term ratio from 2011
- 272 cells
- 34 screen survivors
- 20 frozen
- freeze SHA256: 902c2fbebd8fd7732a4663986ca96d89b2014930e97fd5ef6d12e88459c53ca2
- 2014+ untouched at freeze

### V40 frozen replication
Run: GEF40-20260920-120933
- Replication: 2014-2017 only
- 20 candidates -> 12 pass
- survivor SHA256: dd23ecbcc8a6adde23518fe491c34dc7b012cbbf9c0cc13f32d4e1969fb14d3f
- 2018+ untouched

### V41 pre-validation robustness
Run: GEF41-20260920-121057
- 12 -> 5 robust
- survivor SHA256: 4bb33cbb287b3f0b65542fd9cbb89ec8a0c85d97206f6def3343a759f6dd6f66
- Robustness included: +1 info lag, trim 1%, trim 2%, remove best 3 events, non-overlap, year stability, monthly sign-flip null.
- 2018+ untouched

### V42 final pre-validation forensic
Run: GEF42-20260920-121948
- 5/5 pass
- family max-stat p = 0.009398120375924815
- survivor SHA256: e5cc99538c1061df70e9e9242675e115f8a3887ecc1e43a1bd795bd21ec18491
- stress: lag1/2/3, neighboring tail 15/85, leave-one-year-out, remove each quarter-season, family-wise max-stat null
- 2018+ untouched

### V43 immutable freeze — CURRENT STATE
Run: GEF43-20260920-122453
Status: FROZEN_AWAITING_VALIDATION
- source V42 SHA256: e5cc99538c1061df70e9e9242675e115f8a3887ecc1e43a1bd795bd21ec18491
- manifest SHA256: 7f91a922b5bf12d067c4d7bdba271903c38f19f2b24103bd4ac1ea9d33ac097b
- validation gate SHA256: 1aa64b6d46ca1f465c1ef68f89e1f67cbc92fa633f10ab3f9a4dbf15cc58836e
- validation 2018-2022 NOT ACCESSED
- locked OOS 2023-2025 NOT ACCESSED
- protected 2026 NOT ACCESSED

Frozen candidates:
1. IV-01 VIX -> NSXUSD | chg1 | upper tail .90 | 5d | continuation
2. IV-02 VIX -> SPXUSD | chg1 | upper tail .90 | 5d | continuation
3. IV-03 VIX -> NSXUSD | level_pct | upper tail .90 | 5d | continuation
4. IV-04 VIX9D -> NSXUSD | chg5 | lower tail .10 | 5d | reversal
5. IV-05 VIX -> NSXUSD | chg5 | upper tail .90 | 1d | continuation

Frozen signal semantics:
- Cboe daily observation
- feature computed past-only
- mandatory shift(1) before spot-date join
- daily spot close on joined date after mandatory Cboe lag
- forward log return at frozen trading-day horizon

Frozen validation gate (2018-2022):
Per candidate:
- minimum events: 80
- gross mean bp > 0
- positive-year fraction >= 0.60
- trim best 1% mean > 0
- trim best 2% mean > 0
- remove best 5 events mean > 0
- non-overlap mean > 0
- extra information lag +1 observation mean > 0
Family rule:
- report all 5
- no replacement / rescue / threshold or window change after validation opens
- regardless of result, STOP before 2023-2025 and request human review

## NEXT ACTION
Build V44 as an **independent validation runner** for exactly the V43 manifest and V43 gate.
Requirements:
- verify manifest SHA 7f91a922...
- verify gate SHA 1aa64b6d...
- independently reconstruct feature logic; do not import cached validation results
- access only 2018-2022 plus necessary historical warmup
- output all gate metrics candidate by candidate
- do not retune, rank, replace, or rescue
- write immutable receipt including whether every gate passed
- explicitly assert 2023-2025=false and 2026=false
- progress throughout
- STOP after V44. Do not build/open locked OOS in same run.

## Coding traps already seen
Pandas Series attribute collisions:
- NEVER use r.tail, r.mode, etc. for CSV columns.
- Always use r["tail"], r["mode"], r["horizon_days"].

## Background machine processes
Small persistent watchers may exist (status sync, research orchestrator, Binance/Bybit OI, prop-firm rules, CSV sync). Do not kill them unless proven conflicting.

## Interaction contract
The next AI should behave as an execution partner, not a lecturer:
- inspect -> decide -> patch/commit -> give concise run block
- preserve scientific gates
- keep OOS scarce
- do not repeat generic warnings
- when results arrive, interpret quickly and move to the next scientifically justified step
