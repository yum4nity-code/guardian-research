# Guardian Research — CURRENT PROJECT HANDOFF

**Canonical current state: 2026-09-22**

## Closed / frozen lineages
- V100 forward/shadow frozen; 2026 protected.
- Rates standalone closed after V103 forensic 0/5.
- CFTC standalone closed after V105 report-level forensic 0/7.
- ALFRED V107 closed operationally without alpha conclusion after repeated source/target-bridge failures.

## V108 Treasury audit — SOURCE IS READY

Run GEF108-20260922-160137 originally wrote NOT_READY because the normalized preview took only head(500) from each table before measuring coverage.

The actual V108 schema evidence is authoritative:
- raw Treasury auction table: 9,496 rows, 1979-10-31 to 2022-12-29;
- normalized Treasury auction table: 9,496 rows, 1979-10-31 to 2022-12-29;
- auction_date available;
- bid_to_cover available;
- high yield/rate available.

Correction artifact:
research/results/GEF108_TREASURY_READY_CORRECTION_2026_09_22.json

## V109 — ACTIVE

Standalone Treasury auction event-level research.

Canonical source:
D:\MT5_Backtests\DataLake\normalized\treasury_auctions_pre2023\treasury_auctions_PRE2023.csv

Rules:
- one auction = one statistical observation;
- AVAILABLE_AT = auction_date + 1 calendar day;
- normalize inside security_type × security_term buckets;
- source feature catalog frozen using <=2013 source support only;
- semantic auction fields only, plus predeclared acceptance/share ratios;
- LEVEL score = sign(current minus prior expanding bucket median);
- D1 score = sign(current minus previous same-bucket auction);
- position = event score × discovery-frozen orientation;
- target entry uses first actual tradable 5-minute bar after availability;
- target exit at +60/+120/+240m, rejecting closures/gaps >30 minutes.

Temporal firewall:
2010-2013 discovery -> freeze -> 2014-2017 replication -> robustness -> freeze -> 2018-2022 validation -> STOP.

No 2023-2025.
No 2026.

If V109 validates survivors, run a separate final pre-OOS forensic.
