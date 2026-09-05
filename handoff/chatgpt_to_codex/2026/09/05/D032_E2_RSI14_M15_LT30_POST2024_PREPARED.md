# D032-E2 RSI(14) M15 <30 POST2024 validation — prepared

Date: 2026-09-05
Status: PREREGISTERED / MQ5 DELIVERED / NOT METAEDITOR-COMPILED BY CHATGPT

Canonical preregistration:
`research/campaigns/D032_E2_RSI14_M15_LT30_POST2024_VALIDATION_PREREGISTRATION_2026_09_05.md`

PRE2024 diagnostic result:
`research/results/D032_E1_RSI14_M15_DIAGNOSTIC_PRE2024_2026_09_05.md`

Delivered MQ5:
`D032_E2_DojiStar_RSI14M15_LT30_POST2024_v1_00.mq5`

SHA-256:
`e5ed150c209369202b2561a09e444f7abe7fdf6e9706eff8d363c160761cb768`

## Frozen test
- Entry unchanged from D032-C1.
- POST2024 signals: 2024-01-01 through 2026-06-25 23:00.
- RSI(14) M15, PRICE_CLOSE.
- Every Doji is recorded.
- Primary RSI subset requires the last closed M15 bar to be exactly signal_end-15 minutes and RSI <30.0000.
- No neighboring threshold can replace <30 after results are opened.
- Primary core: BTCUSD / ETHUSD / DOGUSD.
- Secondary transport: LNK/LINK and XRP.
- Primary endpoint: executable +24h return; MFE/MAE diagnostics retained.
- No orders / Guardian OFF.

## Static QA
- braces balance: 0
- parentheses balance: 0
- brackets balance: 0
- RSI_EVENTS header: 34 columns
- RSI_EVENTS row: 34 columns
- SUMMARY header: 16 columns
- SUMMARY row: 16 columns
- direct FileWrite headers + immediate FileFlush
- runtime file-size header QA retained

No MetaEditor compilation is claimed.

## User run
Compile first. Run on M1 with `1 minute OHLC`, tester interval covering at least 2024-01-01 through 2026-06-27. Recommended symbols: BTCUSD, ETHUSD, DOGUSD, LNKUSD, XRPUSD. Return RSI_EVENTS.csv, SUMMARY.csv and RUN_INFO.csv from each run.
