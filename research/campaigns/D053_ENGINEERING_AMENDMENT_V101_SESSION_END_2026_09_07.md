# D053 — Engineering Amendment v1.01 — Session-End Fallback

Date: 2026-09-07 Europe/Paris
Status: **FROZEN AFTER ENGINEERING SMOKE, BEFORE ANY COMPLETED D053 DEV SYMBOL**
Parent preregistration: `research/campaigns/D053_US_INDEX_ORB30_ENTRY_ALPHA_V0_PREREGISTRATION_2026_09_07.md`

## Trigger

The original D053 source compiled cleanly and passed the October-2023 engineering smoke on SPX500, NDX100 and US2000. The first 2024-2025 DEV symbol, SPX500, then stopped before producing a valid completed DEV symbol with `FINAL_INVALID_LIFECYCLE`: a broker day changed while an ORB trade was still open because no executable tick at/after the nominal 22:45 server-time liquidation was available on that session.

No D053 development symbol completed and no D053 development profitability score was produced before this amendment. Therefore this is an engineering/lifecycle amendment, not a response to observed D053 DEV economics.

## Frozen v1.01 amendment

All D053 signal and risk semantics remain unchanged:
- same four-symbol universe;
- same 16:30:00–16:59:59 FundedNext server-time opening range;
- same first breakout after 17:00;
- same one-trade/day rule;
- same one-trade-tick breakout buffer;
- same opposite-side opening-range stop;
- same bid/ask executable pricing;
- same 22:45 nominal forced exit;
- same spread-stress rule;
- same DEV gates and locked Jul-Aug 2026 holdout.

Only the unresolved-session lifecycle is amended:

1. If an open trade receives an executable tick at/after 22:45 server time on the same broker day, exit remains the first such tick with reason `EOD`.
2. If the market/session produces no executable tick at/after 22:45 before the next broker day begins, the trade is closed at the **last executable tick observed on the original broker day**, with reason `SESSION_END`.
3. The fallback may only use a stored tick whose broker-date key equals the trade/opening-range broker day. If no valid same-day executable tick exists, the run remains `FINAL_INVALID_LIFECYCLE`.
4. `SESSION_END` is treated as an EOD-class liquidation for lifecycle counting, but remains explicitly visible in the trade CSV.
5. No day is removed and no symbol is filtered because of an early/irregular session close.

## Scientific interpretation

This amendment does not add predictive information, alter entries, change stops, optimize an exit time, or select a market after outcomes. It makes the already-preregistered intraday liquidation rule executable on sessions whose final same-day tick occurs before 22:45.

The original statement that any broker-day change with an unresolved open trade is automatically invalid is superseded only for the exact `SESSION_END` case above. All other unresolved lifecycle failures remain engineering-invalid, not strategy losses.

## Restart policy

Because zero DEV symbols completed under v1.00, the amended v1.01 source must restart D053 DEV from SPX500 and run the full frozen four-symbol 2024-2025 DEV. The October-2023 smoke must also be rerun with the amended source before DEV is unlocked.

The Jul-Aug 2026 confirmation holdout remains unopened.
