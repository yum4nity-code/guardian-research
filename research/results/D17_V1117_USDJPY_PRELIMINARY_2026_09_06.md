# D17 live v11.17 — USDJPY preliminary attribution — 2026-09-06

Input session: `D017M100_USDJPY_1704067200_502459375`
Period: 2024-01-01 -> 2025-12-31
Diagnostic: `D017_Momentum_LiveV1117_Attribution_v1_100_20260906.mq5`

## Population
- 524 virtual entries
- 293 BUY / 231 SELL
- 235 entries in 2024 / 289 in 2025

## Raw manager comparison from v1.100
- FIXED_3R: 0.0000R/trade gross, exactly 0R total (131 x +3R, 393 x -1R)
- NATIVE_RATCHET: +0.033824R/trade gross, +17.724R total
- Paired manager delta: +0.033824R/trade; bootstrap 95% approximately -0.068R to +0.135R, so not statistically established.

## Important diagnostic defect discovered
v1.100 intentionally returned zero commission for non-crypto and its virtual TrueBEPrice only included the safety tick outside crypto. The live v11.17 fallback true-BE includes estimated entry + exit commission.

Therefore the v1.100 USDJPY result is PRELIMINARY only. It cannot be called an exact live-manager profitability test.

## External current-FTMO cost sanity estimate
Using the current FTMO Forex commission $2.50/lot/side and the 0.7% currency-conversion adjustment for USDJPY on a USD account, a post-hoc estimate from the CSV gives roughly:
- FIXED_3R: -0.0455R/trade
- NATIVE_RATCHET: -0.0091R/trade

This estimate does NOT repair the incorrect v1.100 BE placement. A rerun is mandatory.

## Stability warning
Preliminary Native after current cost estimate:
- 2024: about +0.117R/trade
- 2025: about -0.111R/trade
Strong sign reversal remains the main concern.

## Next action
Compile and rerun the same frozen USDJPY test with `D017_Momentum_LiveV1117_Attribution_v1_101_COSTFIX_20260906.mq5` before testing more non-crypto symbols. v1.101 adds:
- Forex fallback commission $2.50/lot/side
- Metals CFD 0.0007% notional/side
- FTMO currency conversion adjustment input default 0.70%
- non-crypto true-BE using estimated entry + exit commission, matching live fallback semantics
- cost logging in R for all supported asset classes
- no trail/entry parameter changes

Swap/slippage remain deliberately unmodeled in the virtual diagnostic.
