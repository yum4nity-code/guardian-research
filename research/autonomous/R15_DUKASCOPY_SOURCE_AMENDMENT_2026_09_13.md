# R15 Dukascopy source amendment

Date: 2026-09-13
Status: FROZEN BEFORE ANY R15 MARKET RESULT

## Reason

The intended FundedNext XAUUSD source cannot support the published-period recovery stage.

A read-only terminal-depth probe showed:
- M1 requests before 2025 returned no usable in-window history;
- M5 has no usable data overlapping the paper end date of 2019-05-30.

Therefore the FundedNext source is scientifically incapable of testing whether the published GLD clock-time effect is present during the paper era. No R15 market result has been generated, so changing the data source now is pre-result infrastructure repair rather than post-result rescue.

## Replacement source

Use Dukascopy XAUUSD BID M1 daily candle files from the public historical feed.

Frozen source URL pattern:
`https://datafeed.dukascopy.com/datafeed/XAUUSD/YYYY/MM0/DD/BID_candles_min_1.bi5`

where `MM0` is the zero-based month used by Dukascopy.

Only the candle timestamp and OPEN integer are required. All R15 returns are ratios/log-ratios, so the unknown absolute point multiplier cancels and is intentionally not used.

The downloader must:
- request only 2004-11-08 through 2025-12-31;
- never request a 2026 URL;
- parse only valid 24-byte candle records;
- require second-of-day in [0, 86400);
- convert timestamps to America/New_York;
- retain only exact local 11:30, 12:00, 15:30 and 16:00 opens;
- persist a compact boundary dataset and SHA256 provenance manifest;
- fail closed on malformed records or transient download failures after bounded retries;
- treat genuine missing/holiday files as non-eligible days, not synthetic prices.

## R15 chronology after this amendment

Because Dukascopy provides XAUUSD M1 deep enough to cover the paper era, Stage 1 now uses the full published GLD sample dates:

- Stage 1 near-replication: 2004-11-08 through 2019-05-30 inclusive.
- Stage 2 independent confirmation: 2019-05-31 through 2024-12-31 inclusive.
- Stage 3 economic translation: unchanged and only after Stage 2 passes.
- Stage 4 pre-OOS: calendar 2025.
- Protected final OOS: 2026 remains forbidden.

This remains a cross-instrument near-replication because the paper used GLD while Guardian uses XAUUSD. The hypothesis, r5/r13 New York clock mapping, regression direction, HAC convention, confirmation gates, downstream costs, 2025 gates and no-rescue rules are unchanged.

No alternate half-hour may replace r5 if the near-replication fails.
