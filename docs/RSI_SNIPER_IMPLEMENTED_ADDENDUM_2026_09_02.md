# RSI Sniper — implemented addendum (2026-09-02)

This addendum records the production behavior actually implemented after `docs/RSI_SNIPER_SPEC_V1.md`. Where the original draft still labels a point as unresolved, this addendum is the current operational reference until the canonical spec is rewritten.

## Current production state

- Guardian line: v11.16.11.
- Strategy sleeve: `RSI_SNIPER`.
- Dedicated timeframe: M1 independent of Momentum setup timeframe.
- Direction: BUY only.
- RSI: 14.
- ARM: confirmed transition from >=30 to <30.
- BUY1: confirmed closed-M1 recross >30.
- Reset after completed/failed cycle: RSI must first return >=40, then a new distinct <30 episode is required before a new BUY1 can arm.
- Manual BUY under RSI30 may be adopted as `M-BUY1`; manual BUY at/above RSI30 remains under normal Guardian manual management.

## BUY2 LAST — current implemented rule

BUY2 is optional and belongs to the same RSI cycle. There is no BUY3.

Current eligibility:

1. BUY1 cycle is active and TP1 has not occurred.
2. A second oversold episode forms before TP1.
3. Price retests the first episode low within the current tolerance.
4. Retest tolerance: 0.50 ATR M1.
5. Bullish RSI divergence is mandatory in the current baseline.
6. BUY2 executes only after a confirmed closed-M1 recross >30.
7. A rejected BUY2 candidate does not permanently consume the opportunity; a later valid candidate may retry while the cycle remains eligible.
8. BUY1 stop is not tightened merely to create BUY2 capacity before BUY2 actually executes.
9. BUY2 uses remaining cycle-risk budget; it is not an independent 0.25% trade.
10. After BUY2, both legs must use the validated common stop; if common-stop update fails, leg2 is rolled back.

### Current live research concern

Live observations show the BUY1 structural stop can sit so close to the first episode low that the second oversold episode reaches the stop before BUY2 can obtain its required >30 confirmation. A USDCAD case armed BUY2 and passed price retest but failed mandatory divergence immediately before SL. This is a research question, not a production-rule change yet.

Measure at minimum:
- BUY1 stopped before TP1;
- subset already in a second RSI<30 episode;
- subset with BUY2 armed;
- subset passing retest but failing divergence;
- whether a valid >30 recross would have occurred after the original SL time;
- distance between BUY1 SL and first/second episode lows.

## Risk and sizing

- RSI cycle target risk: 0.25% of reference capital.
- Broker max-volume exception introduced in v11.16.9:
  - if `SYMBOL_VOLUME_MAX` prevents reaching target risk, Guardian may trade at broker max volume when actual risk is >=50 USD;
  - actual risk below 50 USD is blocked;
  - the rule never authorizes over-risk.
- Post-fill risk is logged separately from pre-fill estimated risk.
- Current RSI spread/SL maximum: 25%.
- BUY1 may widen the execution stop for spread constraints, up to 1 ATR M1, with lot recalculation intended to preserve risk.

Live examples:
- LNK max-volume actual risk ~32 USD: blocked.
- SOL max-volume actual risk ~192 USD: allowed and executed.

## Exit management

### TP1

- Trigger: RSI50 event.
- Close 40% of total RSI cycle volume.
- TP partial handling is latched/idempotent for retries.
- Compute cycle-aware BE NET including realized partial PnL and expected exit costs.
- Trailing becomes active after TP1 in current baseline.

### TP2

- Trigger: RSI70 event.
- Second profit-management stage; remaining runner is preserved according to current production implementation.

### Cycle reset / anti-reentry

After SL or cycle termination, Guardian does not immediately buy again just because RSI remains oversold. Current sequence is:

`cycle end -> COOLDOWN -> closed M1 RSI >=40 -> IDLE -> new closed M1 cross below 30 -> ARMED -> closed M1 recross >30 -> new BUY1`

This is the intended anti-reentry reset.

## Notifications — current semantics

Lifecycle notifications apply to RSI, Momentum and managed manual trades.

- WHITE: entry.
- GREEN: TP1; RSI TP1/BE stage.
- BLUE: TP2, BE/protected exit, SL/trailing after TP1/TP2.
- RED: SL before any TP / dry loss, whatever the strategy.
- Strategy name must be visible (`RSI_SNIPER`, `MOMENTUM`, `MANUAL`).
- Daily PnL is included in dollars and percent.
- Journal remains verbose; phone push is compact.
- Telegram/WebRequest integration is removed from the current Guardian baseline.

## Reliability fixes already implemented

- M1 event watermark only advances after successful processing.
- Restart/owner recovery hardened.
- Cycle-id persistence/recovery hardened.
- Fill-price retrieval uses deal/position/fallback hierarchy; live fallback cases must still be monitored because an Ask fallback can equal the eventual deal without proving deal retrieval succeeded.
- Every BUY1/BUY2 block after a confirmed signal must emit an explicit diagnostic reason; `UNSPECIFIED_RETURN_FALSE` is a final fail-safe telemetry code.

## Strategy switches

v11.16.11 exposes:
- `InpEnableMomentum`
- `InpEnableRSISniper`

An engine switched OFF must not open new entries, but existing positions/cycles remain protected and managed.

## Research freeze

Do not change yet without isolated evidence:
- RSI structural stop;
- confirmed recross >30;
- lot/risk architecture beyond the already-authorized >=50 USD max-volume exception;
- spread/rollover/cooldown guards;
- BUY2 divergence requirement;
- Momentum strategy rules.

Primary RSI research candidates remain:
1. trailing activation timing after TP1;
2. minimum oversold depth (30 / 27.5 / 25, optionally 22.5 only if justified);
3. BUY2 versus structural-stop architecture after measurement.
