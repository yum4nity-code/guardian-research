# D017 Momentum — long-history diagnostic lock

Date: 2026-09-04
Status: LOCKED BEFORE LONG-HISTORY RESULTS / RESEARCH ONLY / NO LIVE ORDERS

## Purpose

Validate whether the D017 Momentum entry engine that previously looked exceptional over short windows has a stable intrinsic edge over 2024-01-01 through 2025-12-31.

This is not a new strategy and not an optimization campaign. The diagnostic extracts the production Momentum signal from `Guardian_D017_PropFirmAuto_v11_16_MOMENTUM_PROD.mq5` and removes Guardian account-state / prop-firm execution machinery so the signal can be tested quickly and without sample-selection from lot, margin or account drawdown.

## Initial validation scope

First mandatory symbols:
- BTCUSD
- ETHUSD

Period:
- 2024-01-01 -> 2025-12-31

Tester:
- chart M1 is acceptable; engine internally uses the production setup/macro timeframes.
- `Every tick`.

## Frozen BTC/ETH signal definition copied from D017 v11.16

- setup TF: M5
- macro TF: H1
- H1 EMA(200) trend filter
- H1 EMA slope normalized by H1 ATR(14): bullish > +0.05 ATR, bearish < -0.05 ATR
- M5 ATR(14)
- M5 ADX(14), trend threshold 20
- relative ATR = current closed M5 ATR / mean prior 30 ATR values
- market regime must be TREND or HIGH_VOL_TREND
- crypto shock state must be NORMAL under the frozen D017 thresholds:
  - SHOCK if ATR-rel >= 2.40 or signal-candle range >= 2.00 ATR
  - PRE_SHOCK if ATR-rel >= 1.80 or signal-candle range >= 1.60 ATR
  - post-shock behavior follows the production implementation
- setup EMA(50) extension block at >= 3.00 ATR
- quality filter:
  - ATR% >= 0.03%
  - ATR% <= 3.00% for crypto majors
  - signal candle range <= 1.50 ATR
- Donchian anti-breakout: 72 M5 bars, starting at shift 2
- Momentum BUY:
  - macro bullish
  - bar 2 bullish
  - bar-2 body >= 0.70 ATR
  - bar 1 close > bar 2 close
  - bar 1 close > bar 1 open
  - bar 1 close < Donchian high
  - not extended
- Momentum SELL = exact inverse
- crypto direction confirmation with EMA(50):
  - BUY: close1 > EMA1 > EMA3; close1 > close2; low1 >= low3
  - SELL: close1 < EMA1 < EMA3; close1 < close2; high1 <= high3
- structural SL distance:
  - BUY structural reference = bar-2 low
  - SELL structural reference = bar-2 high
  - +0.25 ATR buffer
  - crypto floor 1.25 ATR
  - crypto cap 3.50 ATR
- production spread gate retained: spread <= 12% of SL distance
- production broker minimum stop-distance validity check retained
- crypto production session = 24/7

## Deliberate exclusions

The virtual diagnostic does NOT use:
- actual orders
- lots / min-lot / margin
- account drawdown
- max position counts
- daily crypto trade cap
- loss-streak cooldown
- news restrictions
- request budgets
- execution success / broker retcodes

These are Guardian/compliance/execution constraints, not the intrinsic Momentum signal.

## Post-signal path telemetry

For 48h after each virtual signal:
- MFE / MAE
- first structural-SL touch
- first +0.5R, +1R, +1.25R, +1.5R, +2R, +2.5R, +3R, +4R, +5R
- first return to entry after +1R
- first return to entry after +1.25R
- same-M1 ambiguity flags
- 1h/4h/8h/24h/48h snapshots

## Predeclared analysis

Before seeing long-history results, evaluate:
- overall and 2024/2025 separately
- BUY vs SELL
- fixed first-touch EV for 0.5/1/1.25/1.5/2/2.5/3R
- BE@1R -> 2R/3R
- BE@1.25R -> 2R/3R
- descriptive comparator: 25% banked at +2R, BE armed at +1.25R, remaining 75% aiming +3R. This is NOT the exact production ATR trailing rule and must be labelled as such.

Do not optimize thresholds after seeing results. A materially large recurring edge is required; tiny positive EV is insufficient.
