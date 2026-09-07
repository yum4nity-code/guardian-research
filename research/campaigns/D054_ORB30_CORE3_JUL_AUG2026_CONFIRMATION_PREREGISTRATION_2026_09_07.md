# D054 — ORB30 Core-3 Jul-Aug 2026 Confirmation — Preregistration

Date: 2026-09-07 Europe/Paris
Status: **PREREGISTERED BEFORE D053 DESCRIPTIVE AUDIT AND BEFORE ANY JUL-AUG 2026 D054 OUTCOME**
Classification: DERIVED HYPOTHESIS / INDEPENDENT OOS CONFIRMATION

## Origin

D053 tested one frozen ORB30 rule on SPX500, NDX100, US30 and US2000 over 2024-2025. D053 was formally rejected because its month-block bootstrap 95% lower bound was below zero, despite passing 11/12 frozen gates.

D053 discovery evidence showed:
- SPX500 +36.99092103R over 511 trades;
- NDX100 +48.08397678R over 512 trades;
- US30 +46.20623668R over 509 trades;
- US2000 -4.70956931R over 510 trades.

D054 does **not** rewrite, rescue or re-score D053. It states a new derived hypothesis explicitly selected from D053 discovery evidence: the same ORB30 rule may transport robustly as a Core-3 cluster on SPX500, NDX100 and US30.

The Core-3 choice is therefore known to be post-D053 discovery. Its evidentiary burden is paid entirely on untouched Jul-Aug 2026 data.

## Frozen universe

Exactly:
- SPX500
- NDX100
- US30

US2000 is not part of D054. This does not change D053's historical verdict or universe.

No symbol may be dropped or added after D054 confirmation is opened.

## Frozen source / strategy semantics

D054 reuses the **exact D053 v1.01 canonical source bytes** and EX5 semantics. No D054-specific trading source is created.

Canonical source:
`research/strategies/d053/D053_USIndex_ORB30_Tick_M15_v1_00.mq5`

Frozen normalized source SHA-256:
`d39182cc7bd0376322fee474ec7c321b9e1f5d4db93cdb6ff301f0fb60aba7ad`

Frozen Git blob:
`7da58ecf8968d6814b634be0ee0043b9616fb6c6`

The source allowlist is a superset including US2000, but the D054 manifest and runner execute only the three frozen D054 markets. This is intentional: reusing exact D053 code avoids any semantic drift.

Rules remain exactly:
- M15 tester, Model 0 / Every tick;
- FundedNext server-time opening range 16:30:00 through 16:59:59;
- executable ASK high and BID low define the opening range;
- from 17:00, first breakout +1 trade tick wins;
- LONG enters executable ASK, SHORT executable BID;
- initial stop is the opposite opening-range executable extreme;
- one trade maximum per symbol/server day;
- no re-entry, reversal, TP, BE, trailing, partial, trend, volume, ATR, weekday or volatility filter;
- normal liquidation at first executable tick at/after 22:45 server time;
- D053 v1.01 `SESSION_END` fallback remains unchanged when no 22:45-or-later same-day tick exists;
- no real orders.

## Cost model

Unchanged from D053:
- executable bid/ask spread is already embedded;
- no additional explicit index commission;
- 1.5x spread stress subtracts the same frozen additional observed-spread penalty;
- no swap because positions are intraday / same-session closed.

## Discovery data boundary

2024-01-02 through 2025-12-31 is **discovery data already seen in D053**.

D054 must not rerun it as if it were OOS and must not use it for a new formal pass/fail gate. It may be referenced only as the provenance for selecting the Core-3 hypothesis.

## Engineering smoke

Before touching holdout, compile exact source and run engineering-only smoke:

Window:
`2023-10-02` through `2023-10-31`

Symbols:
- SPX500
- NDX100
- US30

Smoke passes only if:
- compile = 0 errors / 0 warnings;
- each symbol has usable opening ranges and at least one closed trade;
- opened == closed == CSV rows;
- no invalid price/risk/PnL/path/lifecycle event;
- source SHA and output identity match.

Smoke economics are not interpreted.

## Frozen independent confirmation

Holdout window:
`2026-07-01` through `2026-08-31`

This window was not opened by D053 because D053 failed its DEV bootstrap gate. D054 is preregistered before opening it.

All confirmation gates are required:

1. aggregate n >= **100**;
2. every symbol n >= **20**;
3. aggregate mean net R > **0**;
4. aggregate PF >= **1.05**;
5. aggregate total net R > **0**;
6. 1.5x spread-stress total net R > **0**;
7. **3/3 symbols** total net R > 0;
8. LONG and SHORT attribution is reported, but neither direction is allowed to be removed post hoc;
9. day-block bootstrap 95% lower bound of aggregate mean net R > **0**;
10. integrity events = **0**.

No threshold may be rounded, waived or changed after holdout is opened.

Pass:
`D054_CONFIRMED_CORE3_ENTRY_ALPHA`

Failure of any scientific gate:
`D054_UNCONFIRMED_CLOSE`

Engineering/data failure:
`D054_ENGINEERING_INCOMPLETE` and no scientific verdict.

## D053 descriptive audit boundary

A detailed D053 audit may run immediately before D054 in the same operator command using only the already-seen 2024-2025 D053 trade CSVs. It may analyze month stability, rolling windows, weekdays, entry latency, exit reasons, opening-range/risk descriptors and a US-vs-Europe DST mismatch proxy.

The D054 universe, rule, gates and holdout are frozen **before that audit is run**. Therefore audit findings cannot alter D054.

If the audit suggests a different hypothesis such as New-York-clock DST alignment, that must become D055 or later and may not change D054.

## Decision policy

Forbidden:
- removing a losing D054 symbol after holdout results;
- selecting only LONG or SHORT;
- modifying OR duration/time, breakout buffer, stop or exit;
- adding any context/filter;
- changing gates;
- treating D053 discovery data as fresh confirmation;
- opening another post-hoc Jul-Aug variant after seeing D054.

A D054 confirmation, if achieved, establishes entry-alpha evidence only. It does not authorize production integration or management optimization without separate review.
