# GEF V110 — UTC intraday/calendar structure

Status: PRE-REGISTERED / READY TO RUN
Date: 2026-09-22

## Motivation

Treasury standalone closed at discovery in V109: 15,870 finite tests, 0 frozen, no 2014+ market returns accessed.

V110 moves to a source-free family with trivial causal timing: deterministic UTC calendar structure.

No London/New York session labels are used because historical DST/session semantics are not needed for this test.

## Statistical unit

One candidate occurrence = one exact top-of-hour market event.

No 5-minute carry-forward repetition.

Targets use exact tradable 5-minute bars at entry and at +30/+60/+120/+240 minutes. Missing exact exit bars are rejected rather than bridged across market closures.

## Frozen calendar cells

Candidate cells are fixed before returns are examined:

1. UTC hour: 24 cells.
2. UTC hour × weekday: 24 × 5 = 120 cells.
3. UTC hour × month-position:
   - START: calendar day 1-5
   - MID: calendar day 6-25
   - END: calendar day 26-end
   24 × 3 = 72 cells.
4. UTC hour × quarter-end window:
   - calendar month in Mar/Jun/Sep/Dec and day >=20
   24 cells.

Total structural cells: 240.

Control samples:
- hour: all other UTC hours;
- hour×weekday: same UTC hour, other weekdays;
- hour×month-position: same UTC hour, other month-position buckets;
- hour×quarter-end: same UTC hour outside quarter-end window.

The tested effect is candidate mean minus its matched control mean.

## Discovery

2010-2013 only.

For every market × horizon × structural cell:
- candidate N >=120;
- control N >=120;
- candidate spans >=3 years;
- direction/orientation = sign(candidate mean - control mean), discovery only;
- directional candidate trade mean >0;
- Welch two-sample p <=.05;
- BH q <=.05 across every finite V110 discovery test.

Freeze <=150 candidates before any 2014+ market returns.

## Replication 2014-2017

Required:
- candidate N >=120;
- matched-control directional effect >0;
- directional trade mean >0;
- net 1 bp >0;
- positive-year fraction >=.50;
- trim best 1% >0.

## Pre-validation robustness

Required:
- trim best 2% >0;
- remove best 10 events >0;
- leave-one-year-out minimum trade mean >0;
- entry delayed +5 minutes >0;
- entry delayed +10 minutes >0.

Freeze exact survivors before 2018+.

## Validation 2018-2022

Required:
- candidate N >=150;
- matched-control directional effect >0;
- directional trade mean >0;
- net 1 bp >0;
- positive-year fraction >=.60;
- trim best 1% >0;
- trim best 2% >0;
- remove best 10 events >0;
- leave-one-year-out minimum >0.

STOP after validation.

Do not open 2023-2025.
Do not open 2026.

If survivors exist, run a separate final pre-OOS forensic.
