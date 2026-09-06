# META-A1 — Momentum exact-attribution lock

Date: 2026-09-06 Europe/Paris
Status: PREPARED / COMPILE + NON-REGRESSION REQUIRED BEFORE LONG RUN

## Purpose

Explain where the previously profitable managed D017 Momentum P/L comes from before any migration into the clean Guardian Core. This is an attribution experiment, not a new strategy search and not a parameter optimization.

## Authoritative Momentum reference

By explicit user decision on 2026-09-06, the authoritative Momentum lineage for META-A1 is the uploaded:

`Guardian_D017_PropFirmAuto_v11_16_19_RSI_RUNNER10_REQUEST_BUDGET_DOGE_UNDERRISK.mq5`

Exact uploaded-source identity:
- size: 314914 bytes
- lines: 6512
- SHA256: `423ebb293cfc77a44b6e95278a8e269944a52b2089d34667ba7a1bf38fa29677`

The prior v11.16.11 recovery blocker is retired **for Momentum attribution**. Do not spend more time hunting v11.16.11 for META-A1 Momentum unless the user later reverses this source decision.

## Clean Guardian Core relationship

`Guardian_Core_Base_v12_01_CANDIDATE.mq5` remains a separate strategy-neutral chassis. Do **not** transplant Momentum into Core before attribution. First prove the instrumented v11.16.19 is behaviorally identical to its source and then measure the edge layers. Only a surviving Momentum engine may later be modularized into the Core strategy socket.

## Frozen Momentum management

No Momentum strategy thresholds are changed. In particular preserve source values including:
- TP1 = 2.00R
- TP1 close = 25%
- BE trigger = 1.25R
- trailing = 1.75 ATR

All existing Momentum signal, quality, profile/regime, crypto extension/direction, BTC-context, spread/SL, risk, margin, account-state and request-budget logic remains source-derived.

RSI is disabled for the META-A1 Momentum experiment.

## Attribution layers

META-A1 logs:
- **L0_RAW**: core structural Momentum candidate before quality/profile-regime/crypto-extension/direction/BTC-context filters.
- **L2_FILTERED**: candidate after the source strategy-local gates/ranking immediately before the real `ExecuteTrade` path.
- **L3_ACTUAL**: real source execution/management path including Guardian/account state, executable broker prices, requests, risk and native position management.
- **SHADOW management**: counterfactual diagnostic using source management thresholds on observed bid/ask. This is not authoritative broker execution and must not be mislabeled exact-native execution.

Execution blocks are logged so rejected L2 candidates can be attributed to lock/session/SL/spread/drawdown/min-risk/min-lot/Guardian/SL-validity/margin/request-budget/order rejection stages.

## Delivered v1.00

Pack: `META_A1_Momentum_Attribution_Pack_v1_00.zip`

Contents:
- `META_A1_Momentum_Attribution_v1_00.mq5`
- `META_A1_Analyze_v1_00.py`
- `META_A1_README_v1_00.txt`

Hashes:
- MQ5 SHA256: `f45a3189bfa577f8a9fdac2b46514f2ad59469c531b0884275c4c74e8ce8714a`
- analyzer SHA256: `becbb06a4f9d510538be1f7d54acaa4f8c1f1027373c31333fa67274a1f859e6`
- README SHA256: `5b57889a5026f5d742d54c4063279890b9247d09fa46cd0e488aaea77666da94`
- ZIP SHA256: `71f5c9a09e61fdc4db1229d6fb48156ae9595ba9a00e4400129b6684d054e73d`

Static QA performed before delivery:
- source hash/size checked;
- lexical brace balance PASS;
- duplicate key-definition checks PASS;
- diff audit limited to META instrumentation/default Momentum-on RSI-off harness and hook points;
- Python analyzer `py_compile` PASS;
- synthetic analyzer smoke PASS.

**Not yet compiled in MetaEditor.** MetaEditor compile is mandatory before any Strategy Tester run.

## Mandatory non-regression gate

Before 2024-2025 attribution, compare the untouched v11.16.19 source and META-A1 v1.00 on the same BTCUSD short window, same tester model and same inputs, with Momentum ON / RSI OFF.

Recommended window: 2026-07-01 through 2026-07-31, Strategy Tester `Every tick based on real ticks`.

Required outcome: same real trade count and same material P/L/trade behavior. Logging/shadow diagnostics may differ because they exist only in META-A1. If real trades/P&L differ, STOP; fix instrumentation before any long run.

## Long-run gate

Only after non-regression PASS:
- BTCUSD
- 2024-01-01 through 2025-12-31
- `Every tick based on real ticks`
- Momentum ON
- RSI OFF
- META observer + raw/filtered shadows ON
- no threshold changes

Collect the four FILE_COMMON CSV outputs:
- `META_A1_MOMENTUM_EVENTS_BTCUSD.csv`
- `META_A1_MOMENTUM_EXEC_BTCUSD.csv`
- `META_A1_MOMENTUM_SHADOW_BTCUSD.csv`
- `META_A1_MOMENTUM_ACTUAL_BTCUSD.csv`

The long run answers whether P/L lift comes from raw entry, strategy-local selection, Guardian/account-state selection, management, or execution/cost drag. If the fully reconstructed BTC system does not survive 2024-2025, stop before broadening to other symbols.

## Prohibitions

- no threshold tuning on 2024-2025;
- no migration to Guardian Core before attribution;
- no reclassification of shadow P/L as exact broker execution;
- no new D036/D037 family merely to keep searching while META-A1 is unresolved.
