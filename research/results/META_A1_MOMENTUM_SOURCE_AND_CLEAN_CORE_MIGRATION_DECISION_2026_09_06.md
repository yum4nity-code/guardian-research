# META-A1 — Momentum source and clean-core migration decision

Date: 2026-09-06

## User source-of-truth decision
The user explicitly confirms that the latest supplied file is the correct Momentum engine and directs the project not to spend further time recovering v11.16.11 for Momentum attribution.

Canonical Momentum behavioral reference for META-A1:
`Guardian_D017_PropFirmAuto_v11_16_19_RSI_RUNNER10_REQUEST_BUDGET_DOGE_UNDERRISK.mq5`

Local supplied-file identity checked in this session:
- size: 314,914 bytes
- lines: 6,512
- SHA-256: `423ebb293cfc77a44b6e95278a8e269944a52b2089d34667ba7a1bf38fa29677`

This decision applies to the Momentum lineage. It does not assert that every later RSI-specific modification in v11.16.19 is the exact historical RSI baseline.

## Clean Guardian comparison
The previously prepared `Guardian_Core_Base_v12_01_CANDIDATE.mq5` remains the strategy-neutral destination architecture, not the historical attribution baseline.

Clean-core identity:
- SHA-256: `6a74d4187e04a02f9924c48ef34a1f0eb946da0f64d66a4839701154d6ad1176`
- no embedded RSI or Momentum strategy
- strategy registry/socket
- Guardian-owned prop-firm routing, drawdown/risk, server-request budget, news/session protection, manual protection, reusable feature bus and read-only shared intelligence

## Scientific separation
Do **not** port Momentum into v12.01 first and then use the result to explain the historical P/L. That would mix a strategy change with a Guardian architecture change.

META-A1 must proceed in two stages:

### Stage A — attribution inside the v11.16.19 behavioral reference
Instrument a diagnostic copy without changing Momentum thresholds or decisions. Log nested checkpoints:
1. raw Momentum condition;
2. Momentum-local acceptance after profile/regime/quality/direction/BTC-alignment logic;
3. Guardian/account/execution acceptance;
4. actual filled trade and exact native Momentum management outcome.

Preserve native Momentum management exactly, including the current reference values such as TP1/partial, BE trigger and ATR trail. Disable RSI for Momentum-only attribution by configuration, not by deleting/changing Momentum code.

First require parity between unmodified v11.16.19 and the instrumented copy on the same BTC reference window. Trade count and managed P/L must match apart from logging-only effects.

Then run BTCUSD 2024-2025 and quantify where the apparent edge is created or destroyed: raw signal, strategy selection, Guardian/account selection, native management and costs.

### Stage B — migrate the proven Momentum semantics into Pure Guardian Core v12.01
Only after Stage A attribution/parity, create a Momentum strategy module for the clean strategy socket. Initially preserve the exact Momentum behavior rather than replacing it with superficially equivalent feature-bus logic.

Strategy module owns:
- Momentum signal definition;
- strategy-local profile/regime/direction filters needed for exact parity;
- Momentum SL rule;
- TP1/BE/trailing decisions.

Pure Guardian Core owns:
- prop-firm/compliance rules;
- risk and drawdown surface;
- account/symbol exposure;
- server-request budget and request priorities;
- order submission/modification/partial-close mechanics;
- news/session/manual protection;
- generic reusable observations.

Run non-regression parity between the reference engine and clean-core+Momentum module. Any trade-set difference must be explained before production use.

## Immediate rule
Stop the v11.16.11 Momentum source hunt. Use v11.16.19 as the Momentum reference and Pure Guardian Core v12.01 as the migration target.