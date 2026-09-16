# R27 Independent Confirmation Result — 2026-09-16

## Status

Infrastructure / execution: **PASS**

Scientific confirmation gate: **PASS**

R27 advances to the next research stage.

## Frozen contract

Research:
- R27 XAUUSD volatility-compression persistence

Confirmation window:
- 2019-07-01 through 2024-12-31

Primary state:
- bottom10

Primary metrics:
1. persistence_4b
2. persistence_8b

Frozen joint gate:
- persistence_4b mean > 0
- persistence_4b complete-estimator delete-one-UTC-day jackknife t > +2.0
- persistence_8b mean > 0
- persistence_8b complete-estimator delete-one-UTC-day jackknife t > +2.0

All four conditions were required.

## Execution evidence

Orchestrator job:
- R27-XAU-CONFIRMATION r1

Source commit:
- 46ad63ffe215ceb9a034aa5b696146e0c3f0e77f

Orchestrator:
- version 1.03

Execution:
- status PASS
- exit code 0
- duration 1136.0686868000193 seconds
- stderr empty

Data:
- 1,437 source days
- 413,856 emitted M5 rows
- 5,398 bottom10 events

Safety:
- pre_oos_2025_opened: false
- protected_2026_opened: false
- protected_2026_untouched: true

## Primary confirmation result

persistence_4b:
- mean +0.0001418936981217318
- +1.418936981217318 bp
- complete-estimator jackknife t +13.196076261387917
- required replicates 1,437
- valid replicates 1,437
- undefined delete days 0
- mean condition PASS
- t > +2 condition PASS

persistence_8b:
- mean +0.00019220689242209195
- +1.9220689242209195 bp
- complete-estimator jackknife t +11.99183401060178
- required replicates 1,437
- valid replicates 1,437
- undefined delete days 0
- mean condition PASS
- t > +2 condition PASS

Overall joint gate:
- PASS

## Discovery-origin comparison

R22 discovery bottom10, expressed in R27 persistence sign:

4b:
- discovery persistence +0.00015638882587303937
- discovery t +18.92675989606528
- confirmation persistence +0.0001418936981217318
- confirmation t +13.196076261387917

8b:
- discovery persistence +0.00020790988129736705
- discovery t +17.74653252800569
- confirmation persistence +0.00019220689242209195
- confirmation t +11.99183401060178

The sign, magnitude order and strong complete-jackknife significance replicate
independently in the confirmation period.

## Scientific interpretation

R27 confirms the preregistered phenomenon:

After a bottom-10 prior-48-M5 realised-volatility compression state, subsequent
absolute XAUUSD movement over 4 and 8 M5 bars remains below the same-clock
unconditional baseline.

This is a confirmed statistical phenomenon.

It is not yet an executable trading edge.

The confirmation result does not establish:
- net profitability
- entry direction
- spread/slippage tolerance
- stop-loss/target geometry
- feasible trade frequency after execution constraints
- prop-firm compatibility

Those belong to a separately frozen economic/tradability stage.

## Independence limitation

The confirmation-period payload bytes had previously been opened by R21/R26, but
neither run computed R22/R27 events or confirmation statistics before R27
preregistration.

R27 therefore had outcome-unseen confirmation, though not virgin-byte
confirmation.

2025 remains fully unopened.

## Frozen decision

R27 survives statistical confirmation.

Permitted next:
- design and preregister an economic/tradability gate using only already-opened
  discovery + confirmation periods

Still prohibited until that gate is frozen and reviewed:
- 2025 pre-OOS opening
- 2026+
- parameter rescue
- state/horizon rescue
- PnL optimization
- Guardian integration
- live deployment

## Queue state

Generation 100 closes the confirmation executor:
- all R27 jobs disabled
- completed confirmation cannot be silently rerun
- 2025 and 2026+ remain closed
