# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-06 Europe/Paris
Status: **ACTIVE / D023 P0 / V1.08 HARNESS STATIC-AUDITED / REAL COMPILE+SMOKE PENDING / FULL 2023 BLOCKED**

## Canonical entrypoint

Read first:

1. `START_HERE_NEXT_AI.md`
2. `GUARDIAN_MASTER_MANDATE.md`
3. `handoff/guardian_next_ai/2026/09/06/GUARDIAN_PROJECT_RESTART_HANDOFF_2026_09_06.md`
4. `CURRENT_QUEUE.json`

The Sep-6 restart handoff supersedes older execution-order text in historical handoffs.

## Current P0 — D023 USDJPY London ORB

D023 is the current primary research candidate.

FundedNext/DST-aware inspected 2024-2026 conformance remains:

- n = 482;
- mean net about +0.0915R/trade;
- cumulative about +44.10R;
- net PF about 1.176;
- positive 2024, 2025 and 2026 H1, but weakening through time.

This is **CANDIDATE evidence, not validation**.

Frozen strategy semantics remain unchanged:

- USDJPY M15;
- London OR 08:00-09:00, exactly four M15 bars;
- first strict M15 close outside OR from 09:00 inclusive to 11:00 exclusive;
- enter next M15 open on executable spread side;
- stop opposite OR edge;
- maximum one trade/day;
- exit at stop or close of the M15 bar finishing 16:00 London;
- no EMA/RSI/ATR/day/news/direction rescue filters.

Do not remove SHORT because LONG looked stronger on inspected data.

## Untouched 2023 confirmation gates — frozen

All are required for CONFIRM:

- n >= 150;
- mean net R > 0;
- net PF >= 1.10;
- 5-day moving-block bootstrap lower 5% bound of zero-filled weekday daily mean net R > 0;
- total/mean result remains positive under 1.5x commission.

Do not alter these after seeing 2023.

## Active harness — v1.08

Source:

`research/strategies/d023/D023_USDJPY_LondonORB_M15_v1_08_FUNDEDNEXT_2023_HARNESSFIX_20260906.mq5`

SHA256:

`10e86306d87b6d5f1c507ae724c629c972be0f53c3e586f2fd700691fadc1de4`

Source commit:

`b0fb0bc6b557aea5c58cd56a041856a3a0bccd7b`

Static audit:

`research/results/D023_V108_2023_HARNESS_STATIC_AUDIT_2026_09_06.md`

Local-action handoff:

`handoff/chatgpt_to_codex/2026/09/06/D023_V108_2023_HARNESS_COMPILE_SMOKE_REQUEST_2026_09_06.md`

### Provenance resolved

The exact historical local v1.07 source was recovered from the user's ChatGPT Library. SHA256:

`34ce816eef241c662d6b9fa3be3caea62bc67a25d034bf6cb86e9c67903fff01`

This exactly matches the SHA recorded in the restart handoff. Its broken `"\Files\"`-style path string and stale v1.06 log labels are therefore confirmed defects in the actual warned-about v1.07.

### v1.08 scope

v1.08 changes harness/observability only. Static comparison against exact v1.07 found the calendar/DST/cost/state section, `WriteTrade`, and complete `OnTick` strategy path byte-identical.

v1.08 adds/fixes:

- correct `\\Files\\` path literal;
- unique source/version/output names;
- hard fail on wrong timeframe or disabled CSV;
- STATS `INIT` flushed before TRADES creation;
- `READY` only after both output files exist;
- `FATAL_TRADES_OPEN` evidence if TRADES cannot be created;
- exact source/version/symbol/timeframe/cost/output paths in logs/STATS;
- flushed trade rows and `FINAL` counters.

**Important: v1.08 has NOT yet been compiled in real MetaEditor. Static syntax sanity is not compilation.**

## Next safe action — mandatory

Codex/user local step:

1. sync repo;
2. verify v1.08 SHA256 exactly;
3. real compile in the relevant FundedNext MetaEditor;
4. require **0 errors / 0 warnings**;
5. run only USDJPY M15 Every tick smoke `2023-03-13` through `2023-03-31`;
6. directly inspect `D023_V108_USDJPY_2023_STATS.csv` and `D023_V108_USDJPY_2023_TRADES.csv`;
7. require STATS `INIT -> READY -> FINAL`, nonzero counters and `csv_trade_rows == trades_closed`;
8. manually verify at least three ORB sessions;
9. verify DST behavior on both sides of the 2023-03-26 UK transition;
10. return compile evidence + smoke outputs for audit.

Expected smoke clock behavior:

- weekdays 2023-03-13 through 2023-03-24: FundedNext UTC+3, London UTC+0, server-London = 3h;
- from Monday 2023-03-27: FundedNext UTC+3, London UTC+1, server-London = 2h.

Inherited output convention: a `TIME_1600` exit uses the close price of the 15:45-16:00 London bar, but the CSV `exit_time_*` records that M15 bar's opening timestamp (15:45). Do not misread this as an economic 15:45 exit.

### Hard block

**Do NOT run full `2023-01-02` through `2023-12-29` yet.**

If compile or smoke fails, create a new uniquely named harness version and change harness/observability only. Do not touch ORB semantics.

Only after compile 0/0 + smoke PASS + direct CSV/manual clock validation may the untouched full 2023 confirmation be run exactly once.

## D17 Momentum

D17 Momentum is closed as a current alpha candidate after broad attribution across BTCUSD, ETHUSD, EURUSD, GBPUSD, USDJPY, XAUUSD and USDCAD.

Preserve D17 only for source lineage and Manager Evidence Ledger. Do not restart a rescue campaign or tune inspected D17 samples.

Manager evidence remains useful, but a dedicated Manager Lab should wait for similar management weakness on an independent confirmed strategy family.

## Guardian Core

Guardian Core v12.01 is the stable compile-validated pure infrastructure baseline.

Canonical note:

`production/guardian/GUARDIAN_CORE_V12_01_COMPILE_VALIDATED_2026_09_06.md`

Keep Core stable during strategy research. Strategies integrate through the registry/API; do not turn Core back into the research laboratory.

## FundedNext runtime issue

FundedNext request/retry hyperactivity is a separate runtime/compliance problem.

FundedNext AUTO remains OFF until request budgeting, deduplication, retry/backoff behavior and safety are bounded and verified. Do not mix this runtime issue into D023 alpha conclusions.

## Communication / persistence

After every material milestone:

- update `CURRENT_QUEUE.json`;
- update this handoff;
- update `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md` for the Europe/Paris workday;
- persist local-action requests through the ChatGPT/Codex handoff + inbox mechanism when needed.

For D023 run results report concisely:

**VERDICT — N — expectancy — PF — stability/cost issue — next action**
