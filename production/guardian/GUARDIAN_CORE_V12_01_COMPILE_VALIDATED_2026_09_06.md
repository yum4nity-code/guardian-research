# Guardian Core v12.01 — compile-validated baseline

Date: 2026-09-06
Status: **COMPILE-VALIDATED / PURE CORE BASELINE**

## Validation

User compiled the exact compile-fix snapshot in MetaEditor under the FundedNext MT5 installation and reported:

- `0 errors`
- `0 warnings`

This is user-reported real MetaEditor validation; it is not a CI compile.

## Baseline layout

The validated layout intentionally keeps the local `.mqh` files in the same `MQL5\\Experts\\...` directory as the `.mq5`. Do not move them into `MQL5\\Include` or rename them without creating a new baseline/hash.

Files:

- `Guardian_Core_Base_v12_01_COMPILEFIX_20260906.mq5`
- `Guardian_StrategyRegistry_v1_EMPTY_20260906.mqh`
- `Guardian_StrategyModule_TEMPLATE_v1_20260906.mqh`
- `README_COMPILEFIX_20260906.txt`

The core includes the empty registry with:

`#include "Guardian_StrategyRegistry_v1_EMPTY_20260906.mqh"`

## SHA256

- Core MQ5: `c15c2f04da78f9a4841cc461224bd62db35a110e1c2ff3ed15c6a0fd9c27e826`
- Empty registry: `91878d5a600a52dde0185558641f88aba37168c3b35aad772230489faae32a27`
- Strategy template: `8d444d0475c5628bedeeb3cdc510efebd57692e58d299d0c13d009568a7318d4`
- README: `c9c38a4b2f3c3961ed7fcce67c2988f9da24e8530d687eac7e422549d5821215`

## Baseline invariants

- No embedded RSI strategy.
- No embedded Momentum strategy.
- Empty strategy registry = no autonomous strategy entry logic.
- Guardian risk / prop-firm / drawdown / manual protection / news / request-budget infrastructure remains the reusable base.
- Strategy modules must plug into the registry instead of modifying the core unless a core bug or prop-rule change requires it.

## Artifact archive

The exact validated ZIP is archived in the ChatGPT Library at:

`/Guardian/Production/Guardian_Core_v12_01_COMPILE_VALIDATED_20260906.zip`

## Next Codex action when available

Recover/copy the exact validated snapshot from the user's local MT5 tree or the archived artifact and commit the source files themselves under a stable production Core path. Preserve the hashes above. Do not silently reformat or relocate includes before that source snapshot is committed.
