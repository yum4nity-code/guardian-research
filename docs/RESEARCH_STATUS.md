# Research Status

**Canonical status: 2026-09-20**

For current alpha-research state, this document is subordinate to `CURRENT_PROJECT_HANDOFF.md` and `EDGE_FAMILY_MAP.md`. Historical Rxx/D0xx/live-runtime material remains in Git history and research artifacts and must not be mistaken for the current Edge Factory queue.

## Active
- **GEF V32/V33 — volatility-regime × price-shock**: EXPLORING.
- V32 discovery 2010–2013: 192 cells, 56 screen survivors, 16 frozen.
- V33 is the current next action: exact 2014–2017 replication of all 16; no retuning; all four years required; stop before 2018.
- Runner: `automation/Run-GuardianEdgeFactoryV33.ps1`.

## Recently closed
- GBP60 V3–V10: DEAD — timestamp lookahead confirmed; causal rebuild negative.
- XAG zret H240: CLOSED before locked OOS — failed strict tail robustness.
- XAU/XAG V20–V28: CLOSED before locked OOS — cross-market divergence had insufficient incremental information over XAG mean reversion after forensic attribution.
- XAG-only V29–V31: CLOSED before validation — 12 frozen, 7 replicated, 0 robust.

## Protected data
- 2018–2022: validation only for a lineage that first survives replication + pre-validation robustness.
- 2023–2025: locked OOS; currently unopened for active lineage.
- 2026: protected final OOS.

## Research map
See `EDGE_FAMILY_MAP.md` for the 28-family possibility-space map. Most external-information families remain untouched. Priority after the active lineage: implied vol/term structure -> rates/real yields/breakevens -> CFTC -> macro/FOMC -> Treasury auctions.

## Data / causal constraints
Causal timestamp availability is mandatory. CFTC publication lag must be enforced. Revised macro requires vintage-correct data where relevant. EIA is blocked from alpha use until AVAILABLE_AT is built. Generic cost surfaces are sensitivity analyses, not broker-cost evidence.

## Repository note
Older detailed status reports are intentionally retained in Git history and dated research artifacts for provenance. They are no longer duplicated here because doing so made the current operational state ambiguous.
