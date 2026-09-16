# R28 — directional drift inside confirmed compression-persistence state — preregistration 2026-09-16

## Origin

R28 is a new XAUUSD directional study motivated by the confirmed R27
non-directional volatility-regime phenomenon.

R27 established that bottom10 prior-48-M5 volatility compression predicts
persistently lower subsequent absolute movement than the same-clock baseline.

R27 did not test or establish signed return.

R28 asks the missing directional question before any R28 signed metric is
calculated.

## Data stages

Discovery:
- 2004-11-08 through 2019-06-30

Independent confirmation if and only if discovery survives:
- 2019-07-01 through 2024-12-31

Protected / unopened:
- 2025
- 2026+

The confirmation-period bytes have previously been opened for unrelated R21,
R26 and R27 computations. No R28 signed conditional-drift metric has been
computed or viewed before this preregistration.

## Frozen conditioning state

Exactly reuse the reviewed R22/R27 compression event definition.

Primary state:
- bottom10 only

Definition:
- XAUUSD M5
- sample stdev of previous 48 contiguous M5 close-to-close returns
- current event-bar return excluded from the 48-return volatility estimate
- percentile reference built from prior 20 available UTC trading/data days
- current day excluded
- nearest-rank percentile logic unchanged
- bottom10 threshold unchanged
- first qualifying event per UTC hour/state
- zero stdev retained
- no session, weekday, news, direction or magnitude filter

bottom20 is not part of R28.

## Frozen signed outcome

For each bottom10 event and each primary horizon h:

signed_fwd_h =
    close[event+h] / close[event] - 1

using the same contiguous-M5 forward-return rule as R21-R25.

## Frozen same-clock signed baseline

For every M5 bar in the same stage and each primary horizon h:

baseline observation =
    signed forward return at horizon h

Baseline observations are grouped by UTC minute-of-day.

For the event set, the complete estimator is:

directional_excess_h =
    mean(event signed_fwd_h)
    - event-frequency-weighted mean(same-clock signed baseline_h)

The same UTC-minute weighting logic as R22 is used, except signed forward return
replaces absolute forward return.

## Frozen inference

For each primary horizon, use a complete-estimator delete-one-UTC-day jackknife.

Required replication days:
- union of all baseline days and event days

For each deleted UTC day:
- remove that day's events
- remove that day's baseline observations
- re-estimate the event-frequency-weighted same-clock baseline
- recompute the full event-minus-baseline estimator

Fail closed:
- if any required delete-one-day replication is undefined, clustered SE/t is
  unavailable and that horizon cannot survive.

No naive independent-event t-statistic may be used as the primary inference.

## Primary horizons

Joint primary horizons:
1. 4b = 20 minutes
2. 8b = 40 minutes

These are fixed because they are the two independently confirmed R27 persistence
horizons.

1b / 2b / 16b are not tested as primary R28 outcomes.

## Discovery survival rule

R28 discovery survives only if:

1. directional_excess_4b mean is nonzero;
2. directional_excess_8b mean is nonzero;
3. 4b and 8b means have the same sign;
4. abs(complete-jackknife t_4b) > 2.0;
5. abs(complete-jackknife t_8b) > 2.0.

If all conditions pass:
- freeze the common discovery sign before opening confirmation;
- confirmation must use that sign unchanged.

If any condition fails:
- R28 closes;
- no sign, horizon, state or session rescue.

## Confirmation rule, if discovery survives

Let S be the sign frozen from discovery (+1 or -1).

Confirmation PASS requires both:

S * directional_excess_4b mean > 0
S * complete-jackknife t_4b > +2.0

and

S * directional_excess_8b mean > 0
S * complete-jackknife t_8b > +2.0

Both horizons are required.

## Descriptive reporting

Permitted after primary statistics are computed:
- event count
- day count
- naive signed-return summaries
- yearly stability of directional_excess only if implemented without changing
  the primary estimator

Descriptive outputs cannot rescue the joint primary gate.

## No tuning

Do not introduce:
- bottom20
- different percentiles
- different lookbacks
- different horizons
- directional conditioning from prior return
- weekday/session/news filters
- breakout/fade logic
- magnitude thresholds
- SL/TP
- PnL or transaction-cost optimization

## Economic meaning

If R28 survives discovery and independent confirmation, it would supply the
missing directional component needed before a causal CFD tradability gate can be
designed.

If R28 fails, R27 remains a useful confirmed non-directional regime feature but
does not become a standalone directional XAUUSD CFD edge.

## Protection

- 2025 remains unopened.
- 2026+ remains hard sealed.
- No Guardian/live integration is authorized by this study.
