# START HERE — NEXT GUARDIAN AI

You are taking over Guardian. **Current state is 2026-09-20.**

## Read in this order
1. `CURRENT_PROJECT_HANDOFF.md`
2. `EDGE_FAMILY_MAP.md`
3. `GUARDIAN_MASTER_MANDATE.md`
4. `docs/RESEARCH_PROTOCOL.md`
5. relevant runner/result provenance only after the current state is understood

Do not reconstruct current state from old D0xx/Rxx handoffs, stale queue entries, or historical Codex exchanges.

## Current P0
Finish the **volatility-regime × price-shock** family.

V32 discovery is complete on 2010–2013 only: 192 cells -> 56 screen survivors -> 16 frozen candidates.

The next runner is:
`automation/Run-GuardianEdgeFactoryV33.ps1`

V33 performs exact 2014–2017 replication of all 16 frozen candidates, no retuning, requires all four years, and stops before validation.

If V33 has already run, inspect its receipt/results before doing anything:
- 0 survivors -> close the family and update `EDGE_FAMILY_MAP.md`;
- survivors -> run a pre-validation robustness gate on 2014–2017 before opening 2018–2022.

## Protected periods
- discovery 2010–2013
- replication 2014–2017
- validation 2018–2022
- locked OOS 2023–2025
- protected 2026

Never spend a later period to rescue an earlier failure.

## Closed recent branches
- GBP60 old lineage: timestamp lookahead, dead.
- XAG zret H240: failed strict tail robustness, no OOS.
- XAU/XAG cross-market V20–V28: closed; XAU added insufficient incremental information.
- XAG-only V29–V31: 7 replicated, 0 robust; closed before validation.

## Research strategy
The canonical possibility-space map is `EDGE_FAMILY_MAP.md`. Do not generate endless nearby price transforms. After the active family, prioritize external-information families: implied vol/term structure, rates/real yields, CFTC, macro/FOMC, Treasury auctions.

## Hard rules
- causal availability timestamps;
- freeze before each new temporal period;
- no same-sample rescue;
- realistic costs/non-overlap before promotion;
- progress reporting for nontrivial jobs;
- preserve negative evidence;
- no automatic OOS opening;
- no live deployment without explicit approval.
