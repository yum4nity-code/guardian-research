# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-06 Europe/Paris
Status: **ACTIVE / D023 REJECTED ON UNTOUCHED 2023 / AUTOSYNC V1.04 RUNTIME-VALIDATED / NEXT INDEPENDENT P0 TO SELECT**

## Canonical entrypoint

Read first:

1. `START_HERE_NEXT_AI.md`
2. `GUARDIAN_MASTER_MANDATE.md`
3. `handoff/guardian_next_ai/2026/09/06/GUARDIAN_PROJECT_RESTART_HANDOFF_2026_09_06.md`
4. `CURRENT_QUEUE.json`

The Sep-6 restart handoff supersedes older execution-order text in historical handoffs.

## Latest material milestone — D023 untouched 2023 confirmation

D023 USDJPY London ORB has now completed its preregistered untouched 2023 confirmation and **FAILED materially**.

Published AutoSync run:

`backtests/inbox/2026/09/06/20260906_151852_D023_V108_USDJPY_c6c4489100ff`

Result artifact:

`research/results/D023_USDJPY_2023_UNTOUCHED_CONFIRMATION_RESULT_2026_09_06.md`

Frozen gates scored:

- n >= 150: **PASS — 195**
- mean net R > 0: **FAIL — -0.198176 R/trade**
- net PF >= 1.10: **FAIL — 0.708428**
- 5-day moving-block bootstrap lower 5% bound of zero-filled weekday daily mean net R > 0: **FAIL — -0.268783 R/day**
- result remains positive at 1.5x commission: **FAIL — -44.512458 R total / -0.228269 R/trade**

Baseline total net R: **-38.644330 R**.

Verdict: **REJECT / UNCONFIRMED — 1/5 gates passed.**

This is not a borderline miss. D023 was positive in inspected FundedNext/DST-aware 2024-2026 evidence but materially negative in untouched 2023, so treat the frozen strategy as regime-unstable / non-confirmed. Per preregistration: do not remove SHORT, do not add day/direction/EMA/RSI/ATR/news rescue filters, and do not tune on 2023.

D023 is closed as the current P0 alpha candidate. Preserve for evidence only.

## D023 lineage / harness

Frozen strategy semantics used for the failed confirmation:

- USDJPY M15;
- London OR 08:00-09:00, exactly four M15 bars;
- first strict M15 close outside OR from 09:00 inclusive to 11:00 exclusive;
- enter next M15 open on executable spread side;
- stop opposite OR edge;
- maximum one trade/day;
- exit at stop or close of the M15 bar finishing 16:00 London;
- no EMA/RSI/ATR/day/news/direction filters.

Active confirmation harness source:

`research/strategies/d023/D023_USDJPY_LondonORB_M15_v1_08_FUNDEDNEXT_2023_HARNESSFIX_20260906.mq5`

Canonical Git source commit:

`b0fb0bc6b557aea5c58cd56a041856a3a0bccd7b`

Git source SHA256 recorded at creation:

`10e86306d87b6d5f1c507ae724c629c972be0f53c3e586f2fd700691fadc1de4`

The user compiled v1.08 successfully in the FundedNext MetaEditor and ran the preregistered smoke before the full confirmation. Smoke 2023-03-13..2023-03-31 validated deterministic outputs and the expected UK DST transition behavior.

## GitHub AutoSync — v1.04 runtime validated

Installed watcher:

`automation/Guardian_Backtest_CSV_AutoSync_v1_04_D023_NATIVEGITFIX_PUBLICSAFE.ps1`

Commit introducing v1.04:

`4dc8b740a387faa98a5666e684674cdb7350652e`

Runtime proof now exists:

- Windows Startup installation succeeded;
- v1.04 shut down old v1.02/v1.03 watcher state during installation;
- D023 smoke auto-published successfully to `backtest-results`;
- untouched full-2023 run auto-published successfully to `backtest-results`;
- source/version/symbol/timeframe and row-count checks passed;
- `trades_closed == csv_trade_rows == published_trades_rows`;
- Windows username path was redacted in published STATS;
- GitHub push commit was produced by `Guardian Backtest Bot` without user running `-Once` after the backtest.

Important implementation history:

- v1.02 failed because the PowerShell function parameter `$Args` collided with automatic `$args` and produced empty Git invocations.
- v1.03 fixed `GitArgs` but Windows PowerShell promoted normal Git stderr such as `From https://...` to terminating errors under `$ErrorActionPreference='Stop'`.
- v1.04 isolates Git with `System.Diagnostics/Start-Process` style stdout/stderr handling and trusts the native process exit code.

Normal operation now: user runs the relevant MT5 backtest; watcher stays resident and auto-publishes finalized D023 CSV pairs. No per-backtest PowerShell command is required. Windows reboot + session-login autostart is configured; actual reboot-cycle proof has not yet been explicitly observed in-chat.

## Next safe action

Do **not** rerun, rescue or tune D023.

Select/reconcile the next preregistered independent strategy family from `CURRENT_QUEUE.json` / current research slate, preserving the evidence-first rule:

1. independent documented hypothesis;
2. frozen rules before untouched confirmation;
3. cheap smoke/output validation first;
4. one untouched confirmation;
5. no post-hoc rescue on failed held-out data.

Do not let the separate FundedNext request/retry compliance issue become an excuse to mix alpha and infrastructure research.

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

FundedNext AUTO remains OFF until request budgeting, deduplication, retry/backoff behavior and safety are bounded and verified. Do not mix this runtime issue into alpha conclusions.

## Communication / persistence

After every material milestone:

- update `CURRENT_QUEUE.json`;
- update this handoff;
- update `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md` for the Europe/Paris workday;
- persist local-action requests through the ChatGPT/Codex handoff + inbox mechanism when needed.

For confirmation results report concisely:

**VERDICT — N — expectancy — PF — stability/cost issue — next action**
