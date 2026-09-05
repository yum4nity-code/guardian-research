# D030 FX Engulfing H4 — Alanazi close-replication scanner prepared

Date: 2026-09-05
Status: PREPARED / NOT METAEDITOR-COMPILED BY CHATGPT

Preregistration: `research/campaigns/D030_FX_ENGULFING_H4_ALANAZI_CLOSE_REPLICATION_PREREGISTRATION_2026_09_05.md`
Preregistration commit: `93fd6808ca10d8303078b9f559bd88de0d7c7a0c`

Delivered scanner:
- `D030_FX_Engulfing_H4_Alanazi_CloseReplication_v1_01.mq5`
- SHA-256: `e7748717273afcd4d4477bee5de97ae9ab590c30953ebc546ad71a3f0a7ebb6e`
- 15,276 bytes / 346 lines

## Important correction before delivery
An internal draft v1.00 was discarded before user delivery after the full Alanazi article methodology was recovered. That draft incorrectly used real-body engulfing, a 10-pip buffer and 1R/2R/3R diagnostics. The paper actually specifies:
- full candle/wick engulf (`CC high > PC high` and `CC low < PC low`), plus candle colours and close beyond PC open;
- no trend filter;
- next H4 candle open executable entry;
- stop exactly 5 pips beyond CC low/high;
- target exactly 1:1.

v1.01 implements the recovered published rule. Do not resurrect the discarded draft.

## Scanner behavior
- virtual event scanner only; no orders and Guardian OFF;
- tester M1 / `1 minute OHLC`, internal H4 construction;
- reconstructs H4 BID and ASK OHLC from tester ticks, then source-like midpoint OHLC `(bid+ask)/2` for pattern detection;
- bullish entry at next H4 first ASK; bearish at next H4 first BID;
- stop 5 pips beyond CC midpoint low/high;
- target equal to entry-stop distance (1:1);
- executable exit side used for stop/target path;
- stop checked before target on the same generated tick sample as a conservative ambiguity rule;
- logs binary ±1R outcome and actual executable realized R/pips separately;
- logs MFE/MAE, duration and feed gaps;
- spread embedded; exact historical rollover not reconstructed.

## Static QA completed
- parentheses balance: 0
- braces balance: 0
- brackets balance: 0
- no local `Ev &e = ...` reference aliases
- EVENTS header = 39 data columns; EVENTS row = 39
- SUMMARY header = 20 data columns; SUMMARY row = 20
- direct CSV headers + immediate `FileFlush`
- runtime header-size QA via `FileSize`

MetaEditor compilation has **not** been performed by ChatGPT. User compilation remains the first runtime gate.

## User run set
Primary seven majors:
`EURUSD`, `GBPUSD`, `USDJPY`, `USDCHF`, `USDCAD`, `AUDUSD`, `NZDUSD`.

Tester:
- chart TF M1
- model `1 minute OHLC`
- run from 2024-01-01 through at least 2026-09-05 so signals through the frozen 2026-08-31 cutoff have time to resolve
- no input changes.

Return `EVENTS.csv`, `SUMMARY.csv`, `RUN_INFO.csv` for each symbol. Final analysis must enforce signal cutoff <= 2026-08-31 23:59 and preregistered pooled gates. Pair-level anomalies are discovery only.