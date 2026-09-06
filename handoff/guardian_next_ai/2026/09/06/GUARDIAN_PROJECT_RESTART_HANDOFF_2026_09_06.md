# Guardian project restart handoff — 2026-09-06

## Read this first

Primary governing document:

`GUARDIAN_MASTER_MANDATE.md`

Do not begin by coding. Read the mandate, this handoff, `CURRENT_QUEUE.json`, the D023 result, the Manager Evidence Ledger and the Guardian Core baseline note.

## Mission

Guardian's objective is to become an autonomous multi-strategy CFD Prop Firm trading system that extracts durable positive expectancy after realistic costs while enforcing Prop Firm risk/compliance constraints.

Guardian infrastructure is not alpha. Strategy research must remain lightweight and separable from production Core until a strategy earns promotion.

## Immediate P0

**D023 USDJPY London ORB — prove the 2023 confirmation harness, then run untouched 2023 exactly once.**

Do NOT restart D17 as the primary alpha campaign.

Do NOT tune D023 entry parameters before the 2023 confirmation.

Do NOT immediately ask the owner to rerun the full 2023 test. The output harness must first be demonstrated reliable with a short smoke test.

## D023 frozen semantics

- USDJPY
- M15
- London OR 08:00-09:00
- first M15 close outside OR between 09:00 and 11:00 London
- enter next M15 open using executable-side spread convention
- stop at opposite OR edge
- max one signal/day
- exit at initial stop or 16:00 London
- no EMA, RSI, ATR, day, news or direction rescue filter

## D023 evidence already inspected

FundedNext/DST-aware 2024-2026 conformance run:

- n = 482
- mean net ~ +0.0915R/trade
- cumulative ~ +44.10R
- net PF ~ 1.176
- 2024 ~ +0.153R/trade
- 2025 ~ +0.055R/trade
- 2026 H1 ~ +0.034R/trade
- pooled remains positive at 1.5x commission stress (~+0.059R/trade), but 2026 H1 becomes slightly negative

Interpretation: serious candidate, not validation. Temporal decay is visible.

Authoritative result note:

`research/results/D023_USDJPY_FUNDEDNEXT_CONFORMANCE_RESULT_2026_09_06.md`

Reference engine transcription:

`research/strategies/d023/D023_USDJPY_LondonORB_M15_v1_04_FUNDEDNEXT_REFERENCE_20260906.mq5`

Important provenance note: the repository v1.04 file is a reference transcription of the engine semantics, not claimed byte-identical to the local file that actually ran. The local generated v1.04 source had SHA256:

`d42aea373b55334e6e614f7405c532b7a6be1d074623aa649153176f98e373a1`

Recover/compare the exact local source if available before treating byte identity as established.

## 2023 preregistered confirmation gates

These were frozen before 2023 was inspected:

- n >= 150
- mean net R > 0
- net PF >= 1.10
- time-aware / 5-day moving-block bootstrap target lower bound > 0
- total net R remains positive at 1.5x commission stress

Do not alter these gates after seeing 2023.

## Critical harness warning

Several attempts were made to add 2023 output diagnostics. The latest generated local file was:

`D023_USDJPY_LondonORB_M15_v1_07_FUNDEDNEXT_2023_STATSFIX_20260906.mq5`

Local SHA256:

`34ce816eef241c662d6b9fa3be3caea62bc67a25d034bf6cb86e9c67903fff01`

**This v1.07 was NEVER compile-validated. Do not run or trust it as-is.**

A later manual review revealed a likely path-string defect in the generated code: the intended `TerminalInfoString(TERMINAL_COMMONDATA_PATH)+"\\Files\\"` form was emitted in the local source as an unsafe/incorrect `"\Files\"`-style literal. Treat this as a concrete example of why compilation and smoke tests must precede long runs.

The v1.07 source is intentionally NOT promoted in GitHub as an authoritative engine.

### First engineering task

Build a NEW uniquely named harness version from the frozen v1.04 semantics, changing only observability/output behavior.

Requirements before full 2023 run:

1. unique source version and filenames;
2. real MetaEditor compile: 0 errors / 0 warnings;
3. `INIT` stats row written and flushed immediately;
4. exact output paths logged;
5. deterministic distinct TRADES and STATS files;
6. `FINAL` counters written and flushed;
7. short 2023 smoke run;
8. inspect output files directly;
9. manually check several ORB sessions, DST conversion, entry/stop/exit prices;
10. only then ask the owner for the full 2023 run.

The owner has already repeated unnecessary tests due harness mistakes. Avoid another preventable rerun.

## D17 status

D17 Momentum is closed as a current alpha candidate after broad testing across BTCUSD, ETHUSD, EURUSD, GBPUSD, USDJPY, XAUUSD and USDCAD.

Do not rescue/tune D17 on inspected data.

D17 remains valuable for manager research.

Manager evidence ledger:

`research/MANAGER_EVIDENCE_LEDGER.md`

Current cross-market manager observation: the native ratchet improved 5/7 D17 markets and hurt 2/7, often rescuing fixed-stop losers while clipping large winners. This is evidence for future manager research, not evidence for a universal manager.

Manager Lab should begin only if a similar management weakness appears on an independent strategy family such as D023.

## Guardian Core

Compile-validated pure Core baseline:

`production/guardian/GUARDIAN_CORE_V12_01_COMPILE_VALIDATED_2026_09_06.md`

The exact validated package is archived outside GitHub in the user's ChatGPT Library:

`/Guardian/Production/Guardian_Core_v12_01_COMPILE_VALIDATED_20260906.zip`

Reported real MetaEditor validation: 0 errors / 0 warnings.

Core source SHA256 from the validated package:

`c15c2f04da78f9a4841cc461224bd62db35a110e1c2ff3ed15c6a0fd9c27e826`

Keep Core stable during strategy research. Strategy modules should integrate through the registry/API rather than expanding Core into an indicator/strategy monolith.

## Guardian architecture invariants

- Strategy -> Intent -> Guardian validation -> execution
- Prop Firm compliance remains separate from alpha logic
- current auto risk target max ~0.25% per trade
- max total open account risk ~1%
- manual protection must not close a trade merely because the first missing-SL placement attempt failed
- do not reintroduce removed strategy logic into pure Core

Relevant interface lineage:

- `GuardianEvaluateIntent`
- `GuardianSubmitIntent`
- `GuardianModifyPosition`
- `GuardianPartialClose`

## FundedNext

The current account context used for recent D023 testing is FundedNext.

Guardian already has Prop Firm routing/detection logic; standalone research diagnostics do not inherit it automatically.

Keep FundedNext runtime engineering separate from alpha research.

Known unresolved issue: abnormal request/retry volume. FundedNext AUTO should remain off until dedup/retry/backoff/request-budget behavior is bounded and verified.

## Research doctrine

- documented strategies preferred
- simple, low-dimensional rules
- sufficient trade frequency is a selection criterion
- realistic CFD costs
- no blind indicator soup
- no post-hoc rescue filters presented as validation
- optimization allowed; circular validation forbidden
- preserve untouched data
- red-team before promotion
- automate repetitive output discovery/statistics

## Immediate sequence for the next AI

1. read `GUARDIAN_MASTER_MANDATE.md`;
2. read this handoff;
3. read current queue;
4. read D023 conformance result;
5. read v1.04 reference engine;
6. inspect Manager Evidence Ledger;
7. inspect Core baseline note;
8. create a NEW D023 2023 diagnostic harness version with output-only changes;
9. compile it for real;
10. smoke-test it;
11. verify both output files;
12. only then request the full 2023 confirmation;
13. evaluate against the frozen gates without changing them;
14. if confirmed, proceed to robustness and manager attribution; if rejected, do not rescue-filter the same sample.

## Communication requirement

Be concise with the owner. For run results use:

**VERDICT — N — expectancy — PF — stability/cost issue — next action**

If you make an error, state it immediately and quantify its consequence. Never make the owner discover your engineering mistake through repeated long tests.
