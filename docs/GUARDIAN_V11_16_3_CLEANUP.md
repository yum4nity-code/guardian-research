# Guardian v11.16.3 CLEAN MOMENTUM — cleanup report

Base: `Guardian_D017_PropFirmAuto_v11_16_2_CAPREF_FIXED.mq5`

## Removed
- ENUM_STRATEGY_MODE and frozen mode plumbing.
- Breakout signal generation.
- Pullback signal generation and structural pullback parameters.
- Forex/crypto Sweep signal generation.
- `CryptoSweepSignal()`.
- Sweep structural-entry SL helper.
- dead volume-spike entry filter and its inputs.
- dead strategy eligibility switches (`InpAllowBreakout/Pullback/Sweep/Momentum`).
- disabled generic strategy time-stop plumbing and constants.
- dead crypto sweep entry parameters.
- strategy-generic scoring branches for engines that can no longer enter.

## Preserved deliberately
- Donchian main bounds: still used by Momentum to avoid entering a fresh breakout.
- ATR/ADX/market regime/macro EMA/session/crypto context and direction filters.
- CAPREF v11.16.2 fix and self-tests.
- manual account-wide Guardian.
- PropFirmGuard/news/FTMO protections.
- legacy Breakout/Pullback/Sweep enum IDs and EXIT management only, for safe handling of positions inherited from older versions.
- legacy Breakout Donchian exit and legacy Crypto Sweep TP constant solely for that exit compatibility.

## Refactors preserving Momentum semantics
- `StrategyAllowedForProfile` + `CryptoProfileAllowsStrategy` -> `MomentumAllowedForProfile`.
- `GetStructuralSLDistance(... STRAT_MOMENTUM ...)` -> `GetMomentumSLDistance`.
- `ScoreSignalContext("Momentum ...")` -> `ScoreMomentumContext`.
- New auto positions are tagged directly `STRAT_MOMENTUM`.

## Static verification
- all removed identifiers have zero remaining references.
- braces, parentheses and brackets balance.
- simplified Momentum profile gating was exhaustively compared against the old conjunction for all profile/regime/crypto-regime combinations: zero mismatches.
- simplified Momentum score was exhaustively compared against old Momentum scoring branches: zero mismatches.
- CAPREF self-tests remain present.

Compilation in MetaEditor still required.
