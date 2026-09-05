# D032-E3 reclaim-high delayed-entry diagnostic — prepared

Date: 2026-09-05
Status: PREREGISTERED / MQ5 DELIVERED / NOT METAEDITOR-COMPILED BY CHATGPT

Canonical preregistration:
`research/campaigns/D032_E3_DOJI_RECLAIM_HIGH_ENTRY_DIAGNOSTIC_PREREGISTRATION_2026_09_05.md`

Delivered MQ5:
`D032_E3_DojiStar_ReclaimHigh_EntryDiagnostic_v1_00.mq5`

SHA-256:
`5984207c00b196bdac02c652f6e0ad7240eed955ddb55787f0d726167b935d23`

## Frozen primary candidate
- Underlying D032 Bullish Doji Star H1 signal unchanged.
- Immediate baseline: first ASK after signal close.
- Delayed trigger: first tick BID >= closed Doji H1 high.
- Trigger window: 6h from signal_end.
- Fill: contemporaneous ASK.
- No SL/TP/trailing.
- Exit: exact BID at original signal_end +24h.
- PRE2024 and POST2024 epoch labels exported.

## Purpose
Test whether price confirmation materially reduces adverse excursion while preserving enough +24h expectancy to support realistic stop-based risk sizing.

## QA performed before delivery
- brace balance = 0
- parenthesis balance = 0
- bracket balance = 0
- ENTRY_EVENTS.csv header = 48 columns
- ENTRY_EVENTS.csv row = 48 columns
- SUMMARY.csv header = 19 columns
- SUMMARY.csv row = 19 columns
- direct FileWrite headers; no indexed header arrays
- immediate FileFlush after CSV headers
- runtime minimum header/info file-size QA included
- event array declaration verified

No MetaEditor compilation is claimed by ChatGPT.

## Recommended user run
Compile first. Then run BTCUSD, ETHUSD and DOGUSD on M1 with `1 minute OHLC`, tester interval covering 2018-07-01 through at least 2026-06-27. No input changes.

Optional transport runs LNKUSD/XRPUSD may be supplied, but they do not alter the core advancement gate.

Return each run folder with:
- ENTRY_EVENTS.csv
- SUMMARY.csv
- RUN_INFO.csv
