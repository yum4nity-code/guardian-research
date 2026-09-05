# Guardian Core v12.01 candidate prepared

Date: 2026-09-05
Status: **CHATGPT PREPARED / STATIC AUDIT PASS / USER METAEDITOR COMPILE REQUIRED**

User decision: Guardian must become a pure modular chassis. RSI and Momentum are to be physically removed even though RSI had inherited manual-trade management duties. Manual management will be redesigned separately.

## Candidate

`Guardian_Core_Base_v12_01_CANDIDATE.mq5`
SHA-256: `6a74d4187e04a02f9924c48ef34a1f0eb946da0f64d66a4839701154d6ad1176`

Companion include folder:
- `GuardianCore/Guardian_StrategyRegistry_v1.mqh` — empty Lego socket;
- `GuardianCore/Guardian_StrategyModule_TEMPLATE_v1.mqh` — template only.

The exact candidate bundle was delivered to the user in the ChatGPT work session. It is not claimed compiled and is not live-approved yet. Do not recreate it from memory; use the exact delivered candidate once installed locally.

## Architecture

Pure core retains only generic services: prop-firm profile/rules, drawdown/risk, cost-aware sizing, request budget, news/rollover/weekend/emergency protection, neutral manual initial-SL safety, optional generic market feature bus, Shared Intelligence reader, and generic strategy execution API.

Removed: RSI, RSI manual TP/BE/trailing/runner, Momentum, Donchian/Momentum signal machinery, strategy ranking/grade and engine-specific state.

## Manual semantic lock

For a Magic-0 position lacking an SL, pure Guardian may make exactly **one initial SL placement attempt**. If it fails, alert/log and user sets SL. Never auto-close solely because this initial placement failed. No RSI-based manual management remains.

## Binance + Bybit

The reader consumes the validated schema-2 FILE_COMMON bridge:
`GuardianSharedIntelligence\market_state_multivenue_v1.csv`

It is read-only, BTC/ETH only, freshness-gated, and disabled in Strategy Tester. No external intelligence field is allowed to authorize or veto a trade in the empty pure base.

## Strategy contract

A future strategy module detects its setup but submits entry through `GuardianSubmitIntent()`. Guardian owns risk/compliance/sizing/execution. Strategy modify/partial-close wrappers require magic ownership for that strategy ID. Strategy modules must not call `CTrade` directly.

## Codex action after user installs candidate

1. Verify SHA-256.
2. Compile once in MetaEditor; fix compile errors only, no behavioral redesign.
3. Empty-registry tester smoke => zero auto entries.
4. Check FTMO Prague-midnight / FundedNext server-midnight reference behavior.
5. Demo manual missing-SL test => at most one placement request, no forced close on failure.
6. Shared Intelligence observer smoke => advancing/fresh schema-2 generations, zero trading authority.
7. Only after PASS, make the candidate persistent in repository and begin plugging validated strategy modules.

Static report: `research/results/GUARDIAN_CORE_V12_01_STATIC_AUDIT_2026_09_05.md`.
