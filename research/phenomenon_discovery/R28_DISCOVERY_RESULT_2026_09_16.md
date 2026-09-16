# R28 Directional Discovery Result — 2026-09-16

## Status

Infrastructure / execution: **PASS**

Scientific discovery gate: **FAIL**

R28 does not advance to confirmation.

## Frozen contract

Research:
- R28 XAUUSD directional drift inside the confirmed R27 bottom10 compression state

Discovery window:
- 2004-11-08 through 2019-06-30

Primary metrics:
1. directional_excess_4b
2. directional_excess_8b

Frozen discovery gate:
- both means nonzero
- both horizons have the same sign
- abs(complete-estimator delete-one-UTC-day jackknife t) > 2.0 at 4b
- abs(complete-estimator delete-one-UTC-day jackknife t) > 2.0 at 8b

All conditions were required.

## Execution evidence

Orchestrator job:
- R28-XAU-DISCOVERY r1

Source commit:
- 1cbc9a0cafb37d4440199f5d57df47b46f80355d

Execution:
- status PASS
- exit code 0
- duration 3286.854551800003 seconds
- stderr empty

Data:
- 3,820 source days
- 1,100,160 emitted M5 rows
- 14,645 bottom10 R28 events

Safety:
- confirmation_opened false
- pre_oos_2025_opened false
- protected_2026_opened false
- protected_2026_untouched true

## Primary result

directional_excess_4b:
- mean -4.854271374062158e-06
- -0.04854271374062158 bp
- complete-jackknife t -0.7658432829100201
- required replicates 3,820
- valid replicates 3,820
- undefined delete days 0

directional_excess_8b:
- mean +7.248238240213489e-07
- +0.007248238240213489 bp
- complete-jackknife t +0.07751058364997827
- required replicates 3,820
- valid replicates 3,820
- undefined delete days 0

## Gate evaluation

- both means nonzero: PASS
- same sign at 4b and 8b: FAIL
- abs(t_4b) > 2: FAIL
- abs(t_8b) > 2: FAIL
- frozen confirmation sign: NONE

Overall:
- FAIL

## Scientific interpretation

The confirmed R27 compression-persistence regime does not show a stable
same-clock-adjusted directional drift at the preregistered 4b and 8b horizons.

The 4b estimate is slightly negative.
The 8b estimate is essentially zero and slightly positive.
The signs disagree and both complete-jackknife t-statistics are far below the
required threshold.

This means the confirmed R27 volatility-regime phenomenon does not, by itself,
supply a standalone directional XAUUSD CFD edge through this preregistered R28
mapping.

R27 remains scientifically confirmed as a non-directional regime feature.

## Frozen decision

R28 is closed.

Not permitted:
- choosing the 4b negative sign
- choosing the 8b positive sign
- testing bottom20 as a rescue
- trying 1b/2b/16b after the result
- session/weekday/news filters
- conditioning direction on prior return
- threshold/lookback tuning
- opening confirmation
- opening 2025
- opening 2026+
- PnL optimization
- Guardian/live integration

Any later attempt to derive directional alpha from R27 must be a new
preregistered study with a genuinely new directional mechanism rather than a
rescue of R28.

## Queue state

Generation 103 closes R28:
- all R28 jobs disabled
- no R28 confirmation authorized
- 2025 and 2026+ remain closed
