# D023 v1.08 — 2023 confirmation harness static audit — 2026-09-06

## Status

**STATIC-AUDITED / NOT COMPILE-VALIDATED / FULL 2023 RUN BLOCKED**

This note covers harness and observability only. It does not change or score D023 strategy semantics.

## Source under audit

`research/strategies/d023/D023_USDJPY_LondonORB_M15_v1_08_FUNDEDNEXT_2023_HARNESSFIX_20260906.mq5`

SHA256 of the prepared source bytes:

`10e86306d87b6d5f1c507ae724c629c972be0f53c3e586f2fd700691fadc1de4`

GitHub commit introducing the source:

`b0fb0bc6b557aea5c58cd56a041856a3a0bccd7b`

## Provenance recovered

The exact local v1.07 file archived in the user's ChatGPT Library was recovered and materialized. Its SHA256 is:

`34ce816eef241c662d6b9fa3be3caea62bc67a25d034bf6cb86e9c67903fff01`

This exactly matches the SHA256 recorded in the 2026-09-06 restart handoff, establishing that the audited v1.07 is the same historical generated file referenced by the warning.

The concrete v1.07 defect is confirmed: its FILE_COMMON display path literal was emitted as an unsafe/invalid `"\Files\"`-style string. It also retained stale `v1.06` log labels inside `OnInit`, which could misidentify the executed diagnostic.

## v1.08 changes — harness only

v1.08 changes only observability/output behavior:

- corrected FILE_COMMON display path to `TerminalInfoString(TERMINAL_COMMONDATA_PATH)+"\\Files\\"`;
- new unique source/version identity;
- deterministic distinct outputs:
  - `D023_V108_USDJPY_2023_TRADES.csv`
  - `D023_V108_USDJPY_2023_STATS.csv`;
- wrong tester timeframe now fails initialization instead of merely warning;
- `InpWriteCSV=false` fails initialization because a confirmation run without evidence is invalid;
- STATS is opened first and an `INIT` row is written/flushed immediately;
- TRADES is then created, header written and flushed;
- STATS receives `READY` only after both outputs exist;
- if TRADES creation fails, STATS receives `FATAL_TRADES_OPEN` and initialization fails;
- source filename, version, symbol, timeframe, FundedNext cost model and output paths are logged;
- `FINAL` counters are written/flushed at deinitialization;
- trade rows are flushed immediately.

## Strategy non-regression static comparison

Against the recovered exact v1.07, the following source regions are byte-identical:

- calendar / FundedNext clock / London DST / cost functions / state section;
- `WriteTrade`;
- complete `OnTick` strategy path.

Static SHA fingerprints of the compared text regions:

- calendar-cost-state: `3a4ceb6f7dafbdb4...` in both;
- `WriteTrade`: `53a6ab35fa4a060f...` in both;
- `OnTick`: `44f899b3c642d948...` in both.

Therefore no ORB entry, stop, time-exit, spread, commission or daily signal rule was intentionally changed by v1.08.

## Static syntax sanity

A local lexical sanity scan found:

- no unclosed string literal;
- no unclosed character literal;
- no unclosed block comment;
- balanced `{}`, `()` and `[]` delimiters;
- exactly two corrected `\\Files\\` path literals;
- exactly one `INIT`, one `READY` and one `FINAL` status write;
- frozen OR window, breakout window and 15:45-bar/16:00-close exit markers present once.

This is **not** a MetaEditor compile and must not be described as one.

## Known timestamp convention to inspect

The inherited engine calls `WriteTrade(b.time, b.close, "TIME_1600")` on the M15 bar whose London open time is 15:45 and whose close finishes at 16:00.

Therefore, for `TIME_1600` rows:

- exit price = close of the 15:45-16:00 London M15 bar, matching the frozen 16:00 exit semantics;
- `exit_time_server` / `exit_time_london` currently carry the bar-open timestamp, so the London CSV timestamp displays 15:45.

This is an inherited output timestamp convention, not evidence of a 15:45 economic exit. The smoke inspection must verify this explicitly. Do not change strategy semantics to make the label prettier.

## Required real compile gate

Before any smoke run, the exact v1.08 source above must be compiled in the relevant FundedNext MetaEditor installation.

Required evidence:

- exact source filename shown;
- source SHA256 matches `10e86306d87b6d5f1c507ae724c629c972be0f53c3e586f2fd700691fadc1de4` before compile;
- MetaEditor result: **0 errors / 0 warnings**;
- generated EX5 corresponds to this source/version.

Until this exists, compile status is **UNKNOWN**.

## Required short smoke — do not score alpha

Recommended smoke interval:

**USDJPY / M15 / Every tick / 2023-03-13 through 2023-03-31**

Reason: this short interval crosses the US-vs-UK DST mismatch and then the UK DST transition, so it tests the clock conversion without consuming another full-year run.

Expected clock behavior from the frozen conformance model:

- 2023-03-13 through 2023-03-24 weekdays: FundedNext server UTC offset `+3`, London offset `+0`, therefore server minus London = 3 hours;
- from Monday 2023-03-27: FundedNext server `+3`, London `+1`, therefore server minus London = 2 hours.

Smoke pass requirements:

1. STATS exists immediately and contains `INIT` then `READY`;
2. TRADES exists at the logged deterministic path;
3. run finishes with `FINAL` in STATS;
4. `bars_2023`, weekday bars and OR-complete counters are non-zero;
5. `csv_trade_rows == trades_closed`;
6. direct inspection of actual CSV bytes/rows succeeds;
7. manually verify at least three London sessions against M15 bars:
   - exactly 08:00, 08:15, 08:30, 08:45 form the range;
   - first strict close outside 09:00 <= t < 11:00 creates the signal;
   - entry is the next M15 open on executable spread side;
   - stop is the opposite OR edge;
   - stop or 16:00 London close is respected;
8. explicitly inspect rows on both sides of 2023-03-26 UK DST transition;
9. verify no mixed old output is present and the source/version in STATS is v1.08.

If any harness/output/clock check fails, stop and create a new uniquely named harness version. Do not run the full 2023 confirmation.

## Full 2023 confirmation remains blocked

Only after compile 0/0 + smoke PASS + direct output inspection may the untouched full interval `2023-01-02` through `2023-12-29` be run once and scored against the preregistered gates.

No tuning, no direction filter, no manager experiment and no rescue filter before that score.
