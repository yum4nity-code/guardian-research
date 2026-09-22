# GEF V106 — Remaining causal-source audit

Status: PRE-REGISTERED / READY TO RUN
Date: 2026-09-22

Purpose: choose the next research family from real local data provenance, not from assumptions.

V106 performs ZERO edge trials and reads ZERO 2023+ market returns.

## Prior closure
V105 CFTC final pre-OOS forensic:
- 7 candidates audited
- 5 unique information families
- 0 pre-OOS passes
- 2023-2025 not accessed
- 2026 not accessed

CFTC standalone lineage is closed before locked OOS.

## Families audited

Priority candidates:
1. financial_conditions
2. treasury_auctions
3. fomc_fed / macro event sources
4. alfred_vintage / macro vintage sources
5. CFE volume/open-interest
6. remaining Cboe volatility sources, for provenance only

## Audit outputs

- exact frozen V85 family counts;
- candidate DataLake files by family;
- safe-window classification;
- schema/date-column inspection for files explicitly pre-2023 or bounded <=2022;
- earliest/latest source dates when safely inspectable;
- whether a causal availability field already exists;
- whether a release/event timestamp exists;
- whether the source plausibly extends through 2022;
- explicit blocked reasons.

V106 must not infer alpha or select thresholds.

## Decision rule

Recommended next family is the first family in this order with:
- at least one safely inspectable source;
- coverage reaching 2018-2022 or a clearly complete <=2022 event archive;
- defensible AVAILABLE_AT / release timestamp semantics, or enough raw fields to build them without guessing.

Order:
financial_conditions -> treasury_auctions -> fomc_fed -> alfred_vintage -> cfe_volume_oi.

If none qualifies, return NO_READY_FAMILY and list exact missing data/semantics.

2023-2025 and 2026 remain protected.
