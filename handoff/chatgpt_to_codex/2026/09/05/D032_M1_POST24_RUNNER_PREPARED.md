# D032-M1 post-24h runner management — prepared

Date: 2026-09-05
Status: PREREGISTERED / MQ5 DELIVERED / NOT METAEDITOR-COMPILED BY CHATGPT

Canonical preregistration:
`research/campaigns/D032_M1_DOJI_POST24_RUNNER_PREREGISTRATION_2026_09_05.md`

Delivered MQ5:
`D032_M1_DojiStar_Post24_RunnerDiagnostic_v1_00.mq5`

SHA-256:
`6c55da90607d5431b92f9a59b2439ffa2e504b93621be78137dc99ab4fdef583`

## Frozen primary candidate
- Entry unchanged from confirmed D032-C1.
- At +24h: net ex-swap <=0 => close.
- At +24h: net ex-swap >0 => full position becomes runner.
- Net-BE floor plus 1.0R trailing distance from post-24h peak BID.
- No TP.
- Timeout at +48h.
- Baseline comparator remains full exit at +24h.

## Frozen diagnostics
- 0.5R and 1.5R trails to +48h.
- 1.0R trail to +72h.
- raw 24/30/36/42/48/60/72h returns.
- pre-24h first-hit flags for -1.5R/-2R/-2.5R; no hard stop is imposed in this experiment.

## Weekend / swap
Post-24h feed/weekend gaps are retained and flagged. RUN_INFO records current raw broker swap mode, long swap property and triple-swap day. Exact historical swap is not claimed; summary results are net ex-swap and require later swap stress.

## Tester limitation
FundedNext old real ticks are unavailable. Recommended tester mode: M1 + `1 minute OHLC`. Any trailing-stop result is provisional with respect to intraminute first-touch ordering and requires later real-tick/live-forward confirmation.

## QA performed before delivery
- structural brace balance: 0
- structural parenthesis balance: 0
- structural bracket balance: 0
- `MANAGEMENT_EVENTS.csv` header: 58 columns
- event row: 58 columns
- `SUMMARY.csv` header: 14 columns
- summary row: 14 columns
- headers are direct `FileWrite` calls, not indexed arrays
- immediate `FileFlush` after headers
- runtime header-size QA included

No MetaEditor compilation is claimed by ChatGPT.

## User run
Compile first. Then run only BTCUSD, ETHUSD and DOGUSD on M1 with `1 minute OHLC`, recommended tester interval 2018-07-01 through 2026-06-27 (or the latest available end covering 2026-06-26). Return each run folder containing MANAGEMENT_EVENTS.csv, SUMMARY.csv and RUN_INFO.csv.
