# R26 Independent Confirmation Result — 2026-09-16

## Status

Infrastructure / execution: **PASS**

Scientific confirmation gate: **FAIL**

R26 does not advance.

## Frozen contract

Research:
- R26 COMEX opening-range breakout reversal

Confirmation window:
- 2019-07-01 through 2024-12-31

Frozen primary metrics:
1. reversal_2b
2. reversal_4b

Frozen joint gate:
- reversal_2b mean > 0
- reversal_2b day-clustered t > +2.0
- reversal_4b mean > 0
- reversal_4b day-clustered t > +2.0

All four conditions were required.

## Execution evidence

Orchestrator job:
- R26-XAU-CONFIRMATION r1

Source commit:
- 97e31c3e8bd95b970b3ec50561aacd7f9077fcbf

Orchestrator:
- version 1.03

Execution:
- status PASS
- exit code 0
- duration 30.008623600006104 seconds
- stderr empty

Data:
- 1,437 source days
- 413,856 emitted M5 rows
- 1,352 R26 events

Safety:
- pre_oos_2025_opened: false
- protected_2026_opened: false
- protected_2026_untouched: true

## Primary confirmation result

reversal_2b:
- mean +0.00006245276678524023
- +0.6245276678524023 bp
- day-clustered t +1.847727211281781
- mean condition: PASS
- t > +2 condition: FAIL

reversal_4b:
- mean +0.00003413179040851612
- +0.3413179040851612 bp
- day-clustered t +0.7032756601472466
- mean condition: PASS
- t > +2 condition: FAIL

Overall joint gate:
- FAIL

## Discovery-origin vs confirmation

Discovery-origin R24 symmetric reversal:
- reversal_2b mean +0.00004904292813144948; t +1.8977738256000094
- reversal_4b mean +0.00008173435133260174; t +2.2952902975103644

R26 independent confirmation:
- reversal_2b mean +0.00006245276678524023; t +1.847727211281781
- reversal_4b mean +0.00003413179040851612; t +0.7032756601472466

Interpretation:
- reversal sign remains positive at both primary horizons
- 2b is close to but below the frozen threshold
- 4b significance collapses materially
- the preregistered joint confirmation therefore fails

This is a scientific confirmation failure, not an infrastructure failure.

## Independence limitation

The confirmation-period payload bytes had previously been opened for R21, but no
R24/R26 confirmation metric was computed or viewed before R26 preregistration.

R26 therefore had outcome-unseen confirmation, but not virgin-byte confirmation.
This limitation remains attached to the result.

## Frozen decision

R26 is closed in this research branch.

Not permitted:
- promoting reversal_8b or reversal_16b after seeing confirmation
- changing opening-range times
- changing breakout search end
- adding breakout-distance thresholds
- weekday/news/volatility filters
- sign relabel
- rerunning/replacing the completed result
- economic gate
- 2025 pre-OOS opening
- 2026+ opening
- Guardian/live integration

Any future study inspired by these results requires a new research identifier and
fresh preregistration.

## Queue state

Generation 97 closes R26:
- all R26 jobs disabled
- no further R26 market-data job authorized
- 2025 and 2026+ remain closed
