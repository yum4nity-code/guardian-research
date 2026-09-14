# R15 XAU fastfill transition cold audit

Date: 2026-09-14
Status: STATIC AUDIT PASS / local execution still required

Owner decision: stop the slow sequential R15 Dukascopy acquisition, preserve everything already downloaded, inventory the exact remaining dates, and complete only the missing portion with a faster method.

## Safety architecture

Original cache remains immutable:
`D:\\MT5_Backtests\\Research\\Autonomous\\r15_dukascopy_xauusd_v1\\payload_cache\\`

New fastfill cache is separate:
`D:\\MT5_Backtests\\Research\\Autonomous\\xauusd_dukascopy_fastfill_v1\\payload_cache\\`

The transition never overwrites or deletes the original `.bi5` payloads.

## Exact missing-date inventory

`inventory_r15_xau_cache_before_fastfill_v1_00.py`:
- reads the frozen progress file after the sequential downloader is stopped;
- validates every existing original `.bi5` payload by LZMA decode and 24-byte record structure;
- hashes every original payload;
- uses the sequential progress `last_date` as the completed-prefix boundary;
- classifies absent weekdays on or before that boundary as already-attempted missing/holiday dates;
- preserves valid probe/future cache files already present beyond the prefix;
- writes an explicit `to_fetch` date list containing only unresolved weekdays after the frozen prefix;
- hard-rejects protected 2026+ payloads.

This avoids incorrectly redownloading known holiday/404 days from the already completed prefix.

## Faster acquisition

`r15_xau_dukascopy_fastfill_v1_00.py`:
- reads only the frozen `to_fetch` list;
- writes only to the separate fastfill cache;
- default 8 concurrent workers, hard capped at 12;
- curl HTTP/1.1 primary, urllib fallback;
- bounded retries;
- successful files written atomically;
- real HTTP 404 persisted as explicit `.missing.json` markers;
- an individual unresolved transport error does not destroy prior progress: the run continues, reports INCOMPLETE at the end, and a rerun reuses all successful cached fastfill files;
- 2026 is hard-forbidden.

## Two-cache compatibility / merge

`build_r15_xau_union_from_two_caches_v1_00.py`:
- verifies every original payload still matches the SHA256 frozen in the inventory;
- reads the original cache plus fastfill cache without physically concatenating or mutating either;
- any duplicate date must have identical SHA256 or the merge fails;
- every weekday must resolve to either a valid payload or an explicit known-missing/holiday classification;
- any unresolved date fails closed;
- exact R15 New York boundaries are derived from the union;
- a master payload index with source path + SHA256 is persisted;
- the resulting R15 manifest is compatible with the unchanged R15 v1.01 scientific engine;
- 2026 rows remain forbidden.

## Scientific compatibility

No R15 hypothesis, clock mapping, regression, confirmation period, economic gate, 2025 pre-OOS rule or protected-2026 rule changes.

The optimization changes data transport only.

## Deterministic preflight

`test_r15_xau_fastfill_union_v1_00.py` checks:
- original payload structural validation and hashing;
- 2026 fastfill guard;
- fastfill cache reuse;
- persisted 404 marker semantics;
- strict duplicate-hash mismatch guard;
- unresolved-date completeness guard;
- original-cache freeze hash guard;
- separate destination cache;
- parallel worker implementation;
- Windows curl console suppression.

Do not start the fastfill until the old sequential downloader has been uniquely identified and stopped, its process tree is gone, and the progress snapshot/inventory are written.
