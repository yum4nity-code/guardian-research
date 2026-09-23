# V111 AUDUSD H21 SHORT 240m — Endpoint-extension OOS + FTMO Pipeline

Date: 2026-09-23
Status: FROZEN BEFORE 240m 2023-2025 OUTCOME

## Scientific caveat

AUDUSD H21 as a structural family is not fully untouched in 2023-2025 because the 120m endpoint was already opened in V112.
The 240m endpoint itself remains unconsumed.
Therefore a positive result here is classified as:
- endpoint persistence / horizon-extension evidence,
- not a brand-new independent family confirmation.

No parameter may be changed.

## Frozen provenance

Select exactly one V111 row from GEF111-20260922-163321:
- target_market: AUDUSD
- cell_type: hour
- H21
- horizon_min: 240
- orientation: -1 / SHORT
- expected pre-OOS n = 1033
- historical mean approximately +1.304 bp
- historical net after nominal 1 bp approximately +0.304 bp
- historical leave-one-year-out minimum approximately +1.033 bp
- historical month bootstrap q2.5 approximately +0.542 bp
- old rejection reason: trim-best-5% gate

## Stage A — 240m endpoint evaluation

Window:
- 2023-01-01 through 2025-12-31
- 2026 blocked

Source semantics:
- HistData M1
- raw vendor time +5h
- 5min right-labelled / left-closed
- SHORT H21 -> H01 (+240m)

Report V2-style diagnostics, but label the result as endpoint-extension evidence rather than independent family confirmation.

If mean <= 0: stop.

## Stage B — FTMO execution, only if Stage A mean > 0

Alignment:
- integer offsets -8h..+8h
- >=90% two-leg M1 coverage
- choose minimum median absolute source-vs-FTMO two-leg price difference
- never choose alignment by PnL

Execution:
- first FTMO tick at/after mapped entry and exit boundaries
- SHORT = sell BID, cover ASK
- observed spread embedded

This 4h hold may cross rollover depending on the empirical mapping.
Record current swap metadata only; do not substitute current swap for historical swap.

## Firewalls

- 2026 raw data: BLOCKED
- alternate hour/horizon/direction: BLOCKED
- rescue filtering: BLOCKED
- PnL-based alignment: BLOCKED
- live deployment: BLOCKED
