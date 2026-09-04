# D025 1.03 BTC real-ticks control — 2026-09-04

User reran BTCUSD only after the modelling-mode diagnostic and supplied cumulative 1.03 `events`, `trades`, and `outcomes` CSVs.

## Result

The cumulative files contain two BTCUSD 1.03 sessions:
- `D025V103_BTCUSD_1704067200_352847843`
- `D025V103_BTCUSD_1704067200_356767468`

Each session contains exactly:
- 499 virtual trades;
- 12,873 event rows;
- 2,495 outcome rows.

After removing `session_id`, the two BTC sessions are **exactly identical row-for-row** in all three files: trades, events, and outcomes.

Therefore switching the Strategy Tester modelling mode for the BTC control did **not** change any D025-observed bar/path data or any signal/outcome. The previous leading hypothesis that `Every tick` versus `Every tick based on real ticks` was the cause of the missing BTC population is rejected for this EA/feed/control.

## Scientific implication

The immediate mechanism remains valid: large current-history blocks have flattened relative M15 tick volume near 1.0, which blocks the frozen CASCADE rel-volume >=1.25 gate.

But the modelling-mode switch does not repair it. The unresolved cause is now more specifically **historical data/feed/bar-volume provenance**, not intrabar tester modelling mode.

Do not ask the user for more broad reruns. Next investigation should reconcile the original 1.01 high-population BTC sessions against the current FundedNext historical bar/tick-volume provenance and test-period/data source, without changing D025 thresholds.