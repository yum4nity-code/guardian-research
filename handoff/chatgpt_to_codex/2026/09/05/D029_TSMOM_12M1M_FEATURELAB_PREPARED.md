# D029 TSMOM 12M/1M feature-lab prepared

Date: 2026-09-05

Prepared scanner:
- `D029_TSMOM_12M1M_FeatureLab_v1_00.mq5`
- SHA-256 `9f8538606f22689acc55cb22dffd135e6f723aab0dd25ede5a89563644d1429a`
- research only; Guardian OFF; no orders.

Preregistration:
- `research/campaigns/D029_TSMOM_12M1M_FEATURELAB_PREREGISTRATION_2026_09_05.md`
- commit `1572fa66121ebecb557459eaad7593fa8af5c46e`

Frozen signal window: 2018-01-01 through 2023-12-31. Reserved validation window if promising: 2024-2026.

Source-like core:
- sign of own prior 12 completed calendar-month return;
- LONG positive / SHORT negative;
- one-calendar-month holding;
- first executable quote entry/exit;
- spread embedded;
- EWMA ex-ante daily volatility with `delta=60/61`, annualization 261;
- source-like multiplier `0.40/exante_vol`.

Important CFD-transfer deviations:
- CFD raw return replaces futures/forward excess return;
- monthly signal uses MT5 BID bars;
- historical swap and commission are not reconstructed.

Extra telemetry is diagnostic only and does not filter signals: RSI14 D1/H4, ATR14 D1/H4, 5/20/60/120/252d returns, RV20/RV60, SMA20/50/200 distances, z20, 252d range position, previous-month range, MFE/MAE.

QA before delivery:
- 729 lines;
- braces/parens/brackets balanced;
- EVENTS header = 40 data columns and event row = 40;
- SUMMARY header = 15 data columns and row = 15;
- direct FileWrite headers + immediate FileFlush + runtime FileSize QA;
- no MetaEditor compilation claimed by ChatGPT.

Recommended first batch: EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD, XAUUSD. BTCUSD/ETHUSD/DOGUSD are secondary crypto adaptations only.
