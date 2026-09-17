# EA01 cheap-fail V0 — frozen preregistration

- Input: admitted Dukascopy XAUUSD BID M1 only, aggregated causally to UTC M5.
- Discovery only: `2017-01-01T00:00:00Z` through `2023-01-01T00:00:00Z` exclusive.
- Signal: three consecutive non-zero M5 close-to-close moves with identical sign.
- Entry: next M5 bar open, after the third signal bar is fully available.
- Variants: reversal baseline and continuation control only.
- ATR: Wilder ATR(14), using information available before entry; initialised causally.
- Stop: 1.5 ATR from entry. Exit: close of the third M5 bar beginning with the entry bar.
- Intrabar convention: the stop has priority on every held bar, including the timed-exit bar.
- No overlap restriction, threshold selection, confirmation, pre-OOS, OOS or 2026 access.
- Operational bound: adapter timeout and admitted estimate must both be at most 300 seconds.
- This document authorizes preparation and synthetic testing only; execution requires a separately enabled queue job.
