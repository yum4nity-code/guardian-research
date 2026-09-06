# D023 v1.08 — real compile + smoke request — 2026-09-06

Priority: **P0 / REQUIRED LOCAL MT5 ACTION**

Do not run the full 2023 confirmation yet.

## Exact source

`research/strategies/d023/D023_USDJPY_LondonORB_M15_v1_08_FUNDEDNEXT_2023_HARNESSFIX_20260906.mq5`

Expected SHA256:

`10e86306d87b6d5f1c507ae724c629c972be0f53c3e586f2fd700691fadc1de4`

Source commit:

`b0fb0bc6b557aea5c58cd56a041856a3a0bccd7b`

Static audit:

`research/results/D023_V108_2023_HARNESS_STATIC_AUDIT_2026_09_06.md`

## Required sequence

1. Synchronize the repo and verify the exact source SHA256 locally.
2. Copy/use this exact source in the relevant FundedNext MT5/MetaEditor tree without renaming or editing it.
3. Compile in the real FundedNext MetaEditor.
4. Require **0 errors / 0 warnings**. Preserve compile log/evidence and verify the EX5 corresponds to v1.08.
5. If compile fails, fix harness/observability only in a **new uniquely named version**. Do not change ORB strategy semantics.
6. If compile passes, run only this smoke:
   - USDJPY
   - M15
   - Every tick
   - 2023-03-13 through 2023-03-31
   - default FundedNext Stellar 1-Step/2-Step commission = USD 5/lot/side
   - `InpWriteCSV=true`
7. Locate and directly open:
   - `D023_V108_USDJPY_2023_STATS.csv`
   - `D023_V108_USDJPY_2023_TRADES.csv`
8. STATS must contain `INIT`, `READY`, and `FINAL`; `csv_trade_rows` must equal `trades_closed`.
9. Manually verify at least three ORB sessions and both DST regimes around the 2023-03-26 UK transition.
10. Return compile evidence, smoke logs, both CSVs (or exact accessible paths + hashes), and a concise PASS/FAIL report to ChatGPT.

## DST expectations for smoke

- 2023-03-13 through 2023-03-24 weekdays: FundedNext server UTC+3, London UTC+0 => server-London = 3h.
- from Monday 2023-03-27: FundedNext server UTC+3, London UTC+1 => server-London = 2h.

## Important TIME_1600 output convention

The frozen engine exits economically at the close of the 15:45-16:00 London M15 bar. The inherited CSV `exit_time_*` field uses that bar's opening timestamp, so `TIME_1600` rows display 15:45 London while the exit price is the 16:00 close. Treat that as an output timestamp convention during manual verification, not as a 15:45 exit.

## Hard prohibition

Do not launch `2023-01-02` through `2023-12-29` until the above compile + smoke + direct-output gate is PASS.

Do not tune D023, remove SHORT, add filters, test managers, or rescue inspected 2023 data.
