# D025 Trading 1.02 Path Diagnostic — frozen plan — 2026-09-04

## Purpose

Trading 1.02 is a diagnostic successor to `research/ea/D025_LER_Trading_1_01.mq5`.

It does **not** change the locked D025 V0 entry state machine or the structural stop. It also does not execute a take-profit. Actual trade handling remains structural SL or the existing forced time exit. The only intended change is additional path observation so that exit-management hypotheses can be evaluated without silently changing entries.

Source: `research/ea/D025_LER_Trading_1_02_PathDiagnostic.mq5`.

## New observations

The 1.02 outcomes CSV adds:

- `hit05_utc`: first +0.5R touch;
- existing +1R .. +5R first-touch timestamps;
- `be_after1_utc`: first return to the original entry price after +1R has become available;
- `be_after1_ambiguous_same_m1`: YES when the M1 OHLC bar cannot establish whether +1R / a higher runner target or BE happened first;
- existing `ambiguous_same_m1` remains for simultaneous positive-target/original-stop crossings inside one M1 bar.

New CSV names are versioned separately as `d025_ler_trading_1_02_*` so old 1.01 append files are not mixed with the new schema.

## What this enables

After reruns, compare only a very small preregistered management set first:

1. full TP at +1R;
2. full TP at +2R;
3. partial at +1R (40% frozen candidate), move the 60% remainder to BE, then observe continuation as runner.

Do not optimize trailing distance yet. First establish how often the +1R remainder is stopped at BE before +2R/+3R and how much continuation survives. A trailing rule can be preregistered only after that path distribution is measured.

## Focused rerun matrix

Do not rerun every symbol collected so far. Re-run the branch candidates plus one negative/control market:

- ETHUSD: 2024 full year and 2025 full year;
- BTCUSD: 2024 full year and 2025 full year;
- GBPUSD: 2024 full year and 2025 full year;
- SOLUSD: available 2025 sample (history begins late April in prior dataset);
- XAUUSD: 2024 full year and 2025 full year as a control because the 2024 RETEST result failed 2025 replication.

That is 9 primary reruns. The already-inspected Jun-Jul 2026 window may be repeated later as a regime comparison, but it is not required before the first path-management analysis.

## Frozen scientific constraints

- No D025 entry-threshold changes.
- No structural-SL changes.
- No symbol-specific threshold tuning from these reruns.
- Same tester data/model settings as prior comparable runs where possible.
- Exclude same-M1 ambiguous path cases from any ordering-dependent conclusion, or report them separately.
- Costs/slippage must be included before any production profitability claim.

## Validation state

The source has been written and statically inspected for the intended fields and path logic. No MetaEditor compile has been claimed in this research session; compile remains to be confirmed by the user in MT5/MetaEditor before reruns.
