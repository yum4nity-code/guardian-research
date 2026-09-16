# R21 Independent Confirmation Result — 2026-09-16

## Status

Infrastructure / execution: **PASS**

Scientific confirmation gate: **FAIL**

R21 does not advance.

## Frozen contract

Research:
- R21 COMEX 15-minute unconditional drift

Confirmation window:
- 2019-07-01 through 2024-12-31

Primary metric:
- post_15m

Frozen gate:
- mean > 0
- day-clustered t > +2.0

Descriptive metrics:
- post_30m
- post_60m
- post_120m
- yearly sign stability

Descriptive metrics cannot rescue a failed primary.

## Execution evidence

Orchestrator job:
- R21-XAU-CONFIRMATION r1

Source commit:
- 81c08015a0ffd614985fb5445bee85a17d03dc43

Orchestrator:
- version 1.03

Execution:
- status PASS
- exit code 0
- duration 60.024045600002864 seconds
- stderr empty

Data:
- 1,437 source days
- 413,856 emitted M5 rows
- 1,437 R21 events

Safety:
- pre_oos_2025_opened: false
- protected_2026_opened: false
- protected_2026_untouched: true

## Primary confirmation result

post_15m:
- mean: +0.00003477260504570511
- mean in basis points: +0.3477260504570511 bp
- day-clustered t: +0.610477337333653

Gate evaluation:
- mean > 0: PASS
- day-clustered t > +2.0: FAIL
- overall scientific gate: FAIL

## Discovery vs confirmation

Discovery:
- mean +0.0001111702926410998
- +1.111702926410998 bp
- day-clustered t +2.8805394619816034
- 3,820 events/days

Confirmation:
- mean +0.00003477260504570511
- +0.3477260504570511 bp
- day-clustered t +0.610477337333653
- 1,437 events/days

Interpretation:
- the sign remains positive
- the estimated effect magnitude shrinks materially
- clustered significance collapses below the frozen threshold

This is a confirmation failure, not an infrastructure failure.

## Frozen decision

R21 is closed in this research branch.

Not permitted:
- changing the 08:20 anchor
- changing the 15-minute horizon
- selecting 30m/60m/120m after the result
- weekday/news/volatility/session filtering
- sign flipping
- rerunning or replacing the completed confirmation result
- economic-gate promotion
- 2025 pre-OOS opening
- 2026+ opening
- Guardian/live integration

A future idea inspired by R21 must be a separately preregistered study with a
new research identifier and must not be described as a rescue of R21.

## Queue state

Generation 94 closes the run:
- all R21 confirmation jobs disabled
- no further market-data job authorized
- 2025 and 2026+ remain closed
