# Live FTMO D17 source recovered — 2026-09-06

STATUT: SOURCE_LIVE_RECOVERED / ATTRIBUTION_NEXT

## EXACT LIVE SOURCE PROVIDED BY USER

- Runtime/source filename header: `Guardian_D017_PropFirmAuto_v11_16_12_RSI_FILL_RECONCILE.mq5`
- `#property version`: `11.17`
- Archived exact user-provided source snapshot in ChatGPT Library as `/Guardian/Production/Guardian_D017_LIVE_FTMO_20260906_v11_17.mq5`
- SHA256 of exact snapshot: `875a56e95e5ab4282442e410e4e80f1c776aa9f974d4a3ce9dc5b12505cf8327`
- Source length: 8334 lines (wc -l)

## IMPORTANT IDENTITY RESULT

This is NOT the old GitHub `MOMENTUM_PROD` file verbatim. It is a later live lineage with two AUTO strategies (`MOMENTUM` + `RSI_SNIPER`) and later infrastructure changes including prop-aware server-request budgeting, observed cost model, live RSI lifecycle, Shared Intelligence observer and the v11.17 BNS crypto jump policy.

Therefore future D17 attribution must distinguish:
1. exact live v11.17 Momentum behavior in this source;
2. historical GitHub `Guardian_D017_PropFirmAuto_v11_16_MOMENTUM_PROD.mq5` behavior;
3. any separate v11.16.11 historical baseline.

Do not call these sources identical merely because the Momentum manager constants match.

## MOMENTUM MANAGER CONFIRMED IN LIVE SOURCE

- TP1 = `2.00R`
- TP1 partial close = `25%`
- BE trigger = `1.25R`
- trail = `1.75 ATR`
- TP1 incompatible-volume behavior remains: TP1 state is marked done when the broker minimum/step prevents the partial close.
- trail is one-way only: candidate SL must improve the current SL and be broker-valid.
- trail update is gated by `GetProfileSetupTF("PORTFOLIO")` bar through `TRAILBAR`; not every tick.

## TIME-STOP RESOLUTION

The exact live v11.17 source contains no `InpEnableStrategyTimeStop` and no `InpMomentumMaxMinutes` symbol. It has no Momentum 60-minute native exit to replicate.

Historical GitHub `MOMENTUM_PROD` does contain `InpMomentumMaxMinutes=60`, but explicitly marks it legacy/inactive and locks `InpEnableStrategyTimeStop=false`.

Conclusion: remove `TIMEBOX=60m` from any claim of native D17 management. For V0 attribution use NATIVE vs FIXED-3R plus raw path diagnostics, unless a separate exogenous frozen horizon is preregistered as a non-native counterfactual.

## NEXT P0

1. Freeze exact live v11.17 Momentum entry semantics from this source without RSI interaction.
2. Diff entry/gating semantics against historical `MOMENTUM_PROD`, especially crypto regime/gating changes.
3. Run same-entry attribution with exact native manager vs FIXED-3R + raw MFE/MAE/touch-order diagnostics and full target CFD costs.
4. Keep RSI out of the D17 attribution population.
5. Do not retune 2R/25%, 1.25R or 1.75 ATR on inspected samples.

## GUARDIAN CORE STATUS

`Guardian Core v12.01` has separately been user-compiled successfully at 0 errors / 0 warnings and should remain frozen as the strategy-neutral baseline. Do not mix this source-recovery task with Core refactoring.
