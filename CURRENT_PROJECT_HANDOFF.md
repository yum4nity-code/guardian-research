# Guardian Research — CURRENT PROJECT HANDOFF

**Canonical current state: 2026-09-22**

## Closed / frozen lineages
- V100 forward/shadow frozen, 2026 protected.
- Rates standalone closed after V103 forensic 0/5.
- CFTC standalone closed after V105 report-level forensic 0/7.
- ALFRED closed operationally after V107.4: source support existed (104 features, max 209 events) but release->target bridge still yielded zero tradable discovery samples. No alpha conclusion. Do not reopen without a separate architecture rewrite.

## V108 — ACTIVE

Treasury auction source forensic only.

Why Treasury next:
- V106 found 56 Treasury-auction features already represented in V85 taxonomy.
- V106 could not safely inspect the underlying source tables.
- The older V80 policy already used the conservative causal rule auction_date + 1 calendar day.

V108:
- runs zero edge trials;
- reads zero market returns;
- scans every Treasury-auction candidate file;
- handles CSV/parquet/XLS/XLSX/JSON/XML/ZIP where possible;
- identifies auction_date and useful numeric auction fields;
- writes source/schema diagnostics;
- creates a <=2022 normalized preview only if causally parsable;
- always exits with a receipt, ready or not.

If V108 says READY, next campaign can be an event-level Treasury alpha test.
If V108 says NOT_READY, choose another family; do not patch blindly.
