# R27 — volatility compression persistence — preregistration 2026-09-16

## Origin

R27 is a new XAUUSD study inspired by the R22 discovery result.

R22 preregistered the hypothesis that unusually low recent realised volatility
would be followed by larger absolute movement. That expansion hypothesis failed
strongly: the observed effect was in the opposite direction.

R27 does not relabel R22 as a success. It preregisters the inverse phenomenon as
a new study before any R27 confirmation metric is computed.

## Independence disclosure

The 2019-07-01 through 2024-12-31 payload bytes have already been opened for R21
and R26 confirmation. Neither executor computed R22/R27 events or R27
confirmation metrics.

Therefore R27's confirmation outcome is unseen before preregistration, but the
period is not virgin-byte data.

2025 remains unopened.
2026+ remains protected and unopened.

## Discovery-origin observation

R22 discovery window:
- 2004-11-08 through 2019-06-30

Frozen primary R22 state/horizons:
- bottom10 compression state
- 4b and 8b horizons

Observed R22 excess absolute movement versus same-clock unconditional baseline:

bottom10 / 4b:
- excess_abs_4b mean -0.00015638882587303937
- complete-estimator delete-one-UTC-day jackknife t -18.92675989606528
- 3 positive / 13 negative years

bottom10 / 8b:
- excess_abs_8b mean -0.00020790988129736705
- complete-estimator delete-one-UTC-day jackknife t -17.74653252800569
- 2 positive / 14 negative years

The bottom20 secondary state was also negative, but R27 does not promote it to a
primary state.

## Frozen hypothesis

After an unusually low prior-48-M5 realised close-to-close volatility state,
subsequent absolute movement remains below its same-clock unconditional baseline
over the next 4 and 8 M5 bars.

In other words, volatility compression tends to persist rather than immediately
expand.

## Frozen event definition

Exactly reuse the reviewed R22 event extractor.

- M5 close-to-close returns
- trailing 48 contiguous M5 returns
- sample stdev of those prior 48 returns
- current event-bar return excluded
- normalization against the prior 20 available UTC trading/data days
- current day excluded from the normalization distribution
- nearest-rank percentile logic unchanged
- bottom10 is the sole primary compression state
- first qualifying event per UTC hour/state
- zero standard deviation retained
- no session, weekday, news, direction or magnitude filter

The bottom20 state may be reported descriptively only and cannot rescue bottom10.

## Frozen baseline

For each primary horizon, retain the exact R22 same-clock unconditional baseline:

- same confirmation stage
- same UTC minute-of-day
- same forward horizon
- absolute forward close-to-close return
- complete-estimator delete-one-UTC-day jackknife
- every required delete-one-day replication must be valid
- any undefined required replication makes clustered SE/t unavailable and the
  relevant primary gate fails closed

No baseline re-estimation rule may be changed after confirmation opens.

## Frozen response

R22 defined:

excess_abs_h = compressed-event absolute forward return
               - same-clock unconditional baseline

R27 defines the sign-inverted persistence effect:

persistence_h = -excess_abs_h
              = same-clock unconditional baseline
                - compressed-event absolute forward return

Positive persistence means the compressed event remains quieter than baseline.

## Primary confirmation metrics

Primary state:
- bottom10 only

Joint primary metrics:
1. persistence_4b
2. persistence_8b

Frozen confirmation gate:
- persistence_4b mean > 0
- persistence_4b complete-estimator jackknife t > +2.0
- persistence_8b mean > 0
- persistence_8b complete-estimator jackknife t > +2.0

All four conditions are required.

Equivalent raw R22 sign requirements:
- excess_abs_4b mean < 0 and t < -2.0
- excess_abs_8b mean < 0 and t < -2.0

## Descriptive only

May be reported but cannot rescue a failed primary gate:
- bottom10 1b / 2b / 16b
- all bottom20 metrics
- naive t-statistics
- yearly stability

No horizon/state/session threshold may be changed after confirmation opens.

## Confirmation window

Frozen:
- start: 2019-07-01
- end: 2024-12-31

Reuse the already-audited sealed confirmation builder:
- exact 1,437 source days
- 2019-07-01 first payload
- 2024-12-31 last payload
- 2025 payload bytes unopened
- 2026+ hard sealed

## Promotion rule

PASS only if both 4b and 8b primary persistence metrics pass the complete
jackknife gate unchanged.

On FAIL:
- no bottom20 rescue
- no 1b/2b/16b promotion
- no percentile threshold change
- no session filter
- no immediate 2025 inspection

On PASS:
- only then design an economic/tradability gate before considering 2025.

## Still prohibited

- PnL optimization
- entry/SL/TP search
- Guardian integration
- live deployment
- 2025 inspection
- 2026+ inspection
