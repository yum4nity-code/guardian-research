# D032-E1 RSI(14) M15 diagnostic — prepared

Date: 2026-09-05
Status: PREREGISTERED / MQ5 DELIVERED / NOT METAEDITOR-COMPILED BY CHATGPT

Canonical preregistration:
`research/campaigns/D032_E1_DOJI_RSI14_M15_DIAGNOSTIC_PREREGISTRATION_2026_09_05.md`

Delivered MQ5:
`D032_E1_DojiStar_RSI14M15_Diagnostic_v1_00.mq5`

SHA-256:
`1e9baab77335989aa87856116eab2a280c47e9c5b8200ed32cdee972b751f9c4`

## Method
- Entry remains the confirmed D032-C1 Bullish Doji Star H1 setup.
- RSI(14) on M15 is recorded only; there is no RSI filter.
- RSI uses the last fully closed M15 bar at the H1 signal boundary (`CopyBuffer` shift 1), preventing use of the forming M15 candle.
- PRE2024 only: 2018-07-01 through 2023-12-30 23:00 signal window.
- POST2024 is intentionally reserved for a later threshold-validation run if one threshold is frozen after PRE2024 analysis.
- Endpoint: executable +24h return plus pre24 MFE_R/MAE_R and timestamps.
- No orders, Guardian OFF.

## QA performed
- brace balance 0; parenthesis balance 0; bracket balance 0;
- `RSI_EVENTS.csv` header = 32 data columns; event row = 32 data columns;
- `SUMMARY.csv` header = 13 data columns; summary row = 13 data columns;
- direct FileWrite headers, immediate FileFlush, runtime file-size QA;
- no indexed header array.

No MetaEditor compilation is claimed.

## User execution
Compile first. Run BTCUSD, ETHUSD and DOGUSD on M1 with `1 minute OHLC`, tester interval 2018-07-01 through 2024-01-01. Do not change RSI period or add a threshold. Return each run folder with RSI_EVENTS.csv, SUMMARY.csv and RUN_INFO.csv.
