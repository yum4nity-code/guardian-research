# RSI Sniper v11.16.11 — long-history diagnostic lock

Date: 2026-09-04
Status: LOCKED BEFORE LONG-HISTORY RESULTS / RESEARCH ONLY / NO LIVE ORDERS

## Purpose

Validate the RSI Sniper version associated with the earlier spectacular short-window tests before deciding whether the strategy deserves to stay in Guardian.

The reference lineage is `Guardian_D017_PropFirmAuto_v11_16_11_STRATEGY_SWITCHES.mq5`. This deliberately tests the legacy closed-bar recross version first. Later v11.17 introduced live-tick recross, BUY1 0.50 ATR stop buffer and cost-aware entry changes; those are a separate follow-up if the legacy hypothesis survives.

## Initial validation scope

First mandatory symbols:
- BTCUSD
- ETHUSD

Period:
- 2024-01-01 -> 2025-12-31

Tester:
- M1
- `Every tick`

## Frozen legacy RSI signal definition

- RSI(14), M1
- ATR(14), M1
- long-only cycle reversal
- oversold threshold 30
- reset threshold 40
- TP1 information level RSI50
- TP2 information level RSI70

BUY1:
1. Arm when previous closed RSI >=30 and new closed RSI <30.
2. During oversold episode, record minimum RSI and minimum low.
3. Entry signal only after CLOSED-bar recross: previous RSI <=30 and new RSI >30.
4. structural stop = oversold-episode low - 0.15 ATR.
5. Production broker minimum stop-distance validity check retained.
6. Legacy spread gate = spread <=25% of SL distance.
7. If BUY1 spread gate fails, production behavior may widen the stop only enough to satisfy the 25% gate, with extra widening capped at 1.00 ATR.

BUY2 LAST CHANCE, before RSI50 only:
1. After an active BUY1, arm on a second crossing below RSI30.
2. Record second-episode RSI minimum and low.
3. On closed-bar recross above 30 require:
   - RSI bullish divergence: second RSI minimum > first RSI minimum;
   - low retest: second low <= first low + 0.50 ATR.
4. proposed BUY2 stop = second low - 0.15 ATR, but common stop may never loosen BUY1: common stop = max(existing common stop, proposed BUY2 stop).
5. BUY2 keeps the same 25%-of-SL spread gate and does not use BUY1 auto-widen.

Production session gate retained:
- crypto 24/7
- non-crypto 07:00-17:00 tester/server time, weekend blocked

## Observer-specific sensing rule

This campaign is an ENTRY-EDGE diagnostic, not an exact account-concurrency reproduction. Each leg is tracked independently for R-path quality.

To prevent the observer from remaining locked indefinitely by a runner it does not simulate, sensing for a cycle is retired after RSI50 is reached, after common-stop touch, or after 48h. New sensing then waits for the normal >=40 reset. This may produce more independent later episodes than a real account with a long-lived runner; therefore conclusions concern signal quality first, not final portfolio trade count.

## Deliberate exclusions

No:
- actual orders
- lot/min-lot/margin constraints
- account drawdown / max positions
- news / prop-firm rules
- loss-streak cooldown
- opposite Momentum sleeve blocking
- broker execution failure
- exact TP1/TP2 cash accounting or ATR trailing

## Post-signal path telemetry per BUY1 / BUY2 leg

For 48h:
- MFE / MAE
- structural-SL first touch
- +0.5R, +1R, +1.25R, +1.5R, +2R, +2.5R, +3R, +4R, +5R
- return to entry after +1R and +1.25R
- first RSI50 and RSI70 after entry
- same-M1 ambiguity flags
- 1h/4h/8h/24h/48h snapshots

## Predeclared analysis

- overall / 2024 / 2025
- BUY1 vs BUY2
- fixed-target EV at 0.5/1/1.25/1.5/2/2.5/3R
- BE@1R -> 2R/3R
- BE@1.25R -> 2R/3R
- RSI50-before-stop and RSI70-before-stop rates

No threshold sweep. If the legacy signal does not show a large recurring pre-cost edge, do not rescue it by post-hoc tuning. If it survives, then build and test a separate current-v11.17 live-recoss diagnostic.
