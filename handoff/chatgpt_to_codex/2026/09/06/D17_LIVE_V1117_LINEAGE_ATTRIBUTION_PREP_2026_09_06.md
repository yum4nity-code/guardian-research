# D17 live v11.17 lineage + attribution prep — 2026-09-06

STATUT: SOURCE LIVE IDENTIFIEE / ATTRIBUTION VIRTUELLE PREPAREE / WAITING USER COMPILE

## SOURCE LIVE
User supplied the exact FTMO EA currently in use. Archive identity:
- header filename: `Guardian_D017_PropFirmAuto_v11_16_12_RSI_FILL_RECONCILE.mq5`
- `#property version "11.17"`
- SHA256 `875a56e95e5ab4282442e410e4e80f1c776aa9f974d4a3ce9dc5b12505cf8327`
- source contains two auto sleeves: Momentum + RSI Sniper.

Historical comparison anchor:
- `Guardian_D017_PropFirmAuto_v11_16_MOMENTUM_PROD.mq5`
- SHA256 `bdd2ee0493f0a613177941de4c08e29c6453a715d13fd3b660c42cb3ac2fec09`

## LINEAGE VERDICT
Live v11.17 Momentum is a CLOSE LINEAGE, not exact behavioral identity with v11.16 MOMENTUM_PROD.

Raw BTC/ETH continuation setup is preserved: M5/H1, EMA200 slope +/-0.05 ATR, ADX20, relative ATR, trend/high-vol-trend, Donchian72 anti-breakout, EMA50 extension/direction, 0.70 ATR impulse, structural SL +0.25 ATR, crypto floor 1.25 ATR/cap 3.50 ATR, spread <=12% SL.

Material entry change: live v11.17 defaults to `CRYPTO_REGIME_BNS_JUMP_ONLY`. Legacy SHOCK/PRE_SHOCK remains only fail-safe when BNS cannot be computed. When BNS is ready, high volatility alone is no longer blocked; only an extreme BNS jump z>=3.090232306 whose dominant M1 return lies inside the last closed setup bar vetoes a new crypto Momentum entry. Therefore current BTC/ETH entry samples can differ materially from v11.16.

Execution/account-selection changes also exist: Momentum grade scaling disabled (exec factor 1.0), artificial minimum auto-risk defaults to 0, consecutive-loss cooldown default 3->0, Guardian daily stop 4.8->4.5, continuous DD risk scaling, request-budget gating, margin guard and lot-step/max-volume handling. Treat these as Guardian/execution layer, not raw alpha.

Native manager geometry remains TP1 +2R / intended 25%, BE +1.25R, 1.75 ATR one-way trail once per setup bar. BE cost model is newer (observed commission/fee + estimated exit + signed swap + one tick safety). No active Momentum time-stop exists in live source. Do not use TIMEBOX=60m.

## PREPARED DIAGNOSTIC
Created standalone no-order candidate:
`D017_Momentum_LiveV1117_Attribution_v1_100_20260906.mq5`
SHA256 `0e181ad3f65ee0dd370db834dcdfed40ae8a3f806073da9e3639e4277d3338d3`

Purpose:
- BTC/ETH Momentum only, no RSI;
- exact live-v11.17 BNS entry veto for majors;
- identical frozen virtual entries sent to `NATIVE_RATCHET` and `FIXED_3R`;
- native ordering TP1 -> BE -> trail;
- broker volume-step compatibility for partial TP1 when virtual lot sizing is available;
- broker stop-distance validity for BE/trail;
- one trail update per setup bar;
- no native timebox; raw 48h horizon is observation only and never closes variants;
- open variants are marked `END_TEST_CENSORED` only at tester end;
- crypto fallback commission 0.0325%/side + one tick BE safety; swap/slippage deliberately not invented.

## NEXT
1. User compiles this diagnostic in MetaEditor: require 0 errors / 0 warnings.
2. Then run frozen BTCUSD Every tick long-history blocks; no parameter changes.
3. Analyze BUY/SELL separately; BTC SELL is preregistered clue, not a post-hoc rescue.
4. After virtual manager attribution, run exact live EA with RSI OFF as execution-control to quantify account/request/margin/lot effects.

NE PAS FAIRE: tune BNS window/z, tune 2R/25%/1.25R/1.75ATR, reintroduce TIMEBOX, mix RSI, or treat old v11.16 results as exact validation of live v11.17.