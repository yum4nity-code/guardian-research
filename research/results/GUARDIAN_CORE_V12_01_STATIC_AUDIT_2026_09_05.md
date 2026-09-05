# Guardian Core v12.01 — static audit — 2026-09-05

Status: **STATIC PASS / METAEDITOR COMPILE NOT CLAIMED / NOT LIVE-APPROVED**

## Purpose

Create a strategy-neutral Guardian base after rejection of the embedded RSI and broad D017 Momentum entry families. The core must act as a Lego chassis: risk/compliance/execution stay in Guardian; future validated strategies plug into one registry and do not call `CTrade` directly.

Reference extraction source: `Guardian_D017_PropFirmAuto_v11_17_04_MANUAL_PROTECTION_HOTFIX_PLAN80_RUNNER20.mq5`.

Candidate delivered in the 2026-09-05 ChatGPT work session: `Guardian_Core_Base_v12_01_CANDIDATE.mq5`.
SHA-256: `6a74d4187e04a02f9924c48ef34a1f0eb946da0f64d66a4839701154d6ad1176`.

The candidate source is 91,590 bytes / 1,700 lines versus 377,946 bytes / 7,830 lines for the extraction source. This is not itself a measured tester-speed claim; it reflects removal of rejected strategy machinery and makes unused feature computation opt-in.

## Physically removed from executable core

- RSI entry/cycle/BUY1/BUY2/TP1/TP2/BE/trailing/runner state;
- RSI-coupled manual management;
- Momentum entry and management logic;
- Donchian/Momentum-specific signal machinery;
- strategy score/rank/grade machinery;
- strategy-specific request labels/retry state.

Static executable-code scan finds no RSI or Momentum identifiers.

## Retained generic Guardian services

- prop-firm detection and `profiles.json` account-login routing;
- runtime `rules.json` ingestion;
- FTMO Prague-midnight and FundedNext/The5ers server-midnight drawdown references;
- daily/overall drawdown protection;
- open-risk and worst-case-to-SL checks;
- observed/fallback commissions and projected-swap reserve;
- prop-aware server-request budget;
- MT5 news, rollover, weekend and emergency protection;
- symbol/account ownership;
- generic strategy intent/execution socket.

## Manual positions

The old RSI/manual management is removed. The pure base only protects a Magic-0 position lacking an SL: it computes a market-safe ATR stop and makes **one initial broker SL placement attempt**. If that attempt fails, Guardian logs/alerts and the user sets the SL. There is no automatic close solely because the initial SL placement failed. Excessive manual risk is review-only in this base.

## Optional reusable feature bus

Default OFF. When a future module explicitly needs it, it exposes strategy-neutral facts only: ATR, ATR/price, relative ATR, ADX, macro EMA, macro slope normalized by macro ATR, and spread/ATR. It contains no BUY/SELL decision.

## Binance + Bybit path

The candidate consumes the already validated bridge file `FILE_COMMON\GuardianSharedIntelligence\market_state_multivenue_v1.csv`, schema 2 / 61 fields / BTCUSD+ETHUSD. It adds a freshness gate using `InpSharedIntelMaxAgeSeconds`; stale rows remain visible diagnostically but are not returned as usable strategy intelligence. Live FILE_COMMON intelligence is disabled inside Strategy Tester.

## Lego strategy socket

Future strategy modules live behind `GuardianCore/Guardian_StrategyRegistry_v1.mqh`. Entries go through `GuardianSubmitIntent()`. Position modify/partial-close wrappers verify that the position magic belongs to the requesting strategy ID, preventing one strategy module from managing another module's or a manual position.

## Static checks passed

- parenthesis / brace / bracket balance after stripping comments and strings;
- no duplicate custom function definitions;
- combined main + empty registry scan: no unresolved `GC*`/`Guardian*` custom function call;
- local strategy registry include resolves;
- Shared Intelligence field indices cross-checked against the canonical 61-field bridge;
- no embedded auto-entry behavior exists with the empty registry.

## Required gates before replacement of live Guardian

1. MetaEditor compile main MQ5 with the `GuardianCore` subfolder beside it.
2. Empty-registry Strategy Tester smoke: zero automatic entries.
3. Drawdown/reference/HUD smoke.
4. Demo manual-position smoke: at most one initial SL request; failed initial placement must not auto-close.
5. Shared Intelligence observer smoke: advancing generations + correct fresh/stale state + zero trading effect with empty registry.
6. Only then plug a validated strategy module.
