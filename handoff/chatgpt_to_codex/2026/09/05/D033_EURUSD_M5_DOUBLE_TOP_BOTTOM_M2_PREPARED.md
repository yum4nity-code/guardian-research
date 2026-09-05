# D033 prepared — EURUSD M5 Double Top / Double Bottom M2

Scanner delivered: `D033_EURUSD_M5_DoubleTopBottom_M2_FeatureLab_v1_00.mq5`
SHA-256: `4ad46396f14a71e2b1f30f63bd089cdf9d4a043568d80a068fb99199fc4d647c`
Status: STATIC QA PASS ONLY / NOT METAEDITOR-COMPILED BY CHATGPT.

Preregistration: `research/campaigns/D033_EURUSD_M5_DOUBLE_TOP_BOTTOM_M2_FEATURELAB_PREREGISTRATION_2026_09_05.md`

Frozen primary:
- EURUSD only;
- source M2 high/low extrema method;
- internally reconstructed M5 midpoint bars;
- 36-observation Gaussian Nadaraya-Watson window;
- Silverman bandwidth x0.20;
- source DT/DB definitions with one-point numerical equality tolerance only;
- source TP +0.50h, SL -0.20h, timeout `tf+(tf-td)`;
- executable BID/ASK spread embedded;
- no Guardian / no orders.

Development signal window: 2024-01-01 through 2026-06-30 23:59. Pre-2024 remains reserved.

Passive features only: internally calculated RSI14 M5/M15/H1, ATR14 M5, multi-horizon returns, SMA distances, RV/ranges, time-of-day, geometry, MFE/MAE. They are not filters.

Recommended tester:
- chart/test timeframe M1;
- model `1 minute OHLC`;
- start around 2023-12-15 for warm-up;
- end at least 2026-07-03 to resolve late trades;
- no input changes.

Return `EVENTS.csv`, `SUMMARY.csv`, `RUN_INFO.csv`.

Frozen advancement gate: >=250 clean resolved; mean >+0.15R; median R >0; month-block bootstrap lower >0; both DT and DB positive; >=2 of 2024/2025/2026 positive; no single event >10% positive pooled R.

If low/zero event count occurs, first audit source-equation implementation/data precision; do not silently widen the equality tolerance or change the 36-bar window after seeing results.