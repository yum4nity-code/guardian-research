# R27 Economic / Tradability Classification — 2026-09-16

## Status

R27 is a statistically confirmed XAUUSD volatility-regime phenomenon.

Standalone directional CFD alpha status: **NOT ESTABLISHED / NOT DIRECTLY PROMOTABLE**

R27 remains eligible as:
- a confirmed regime feature;
- a future filter/input for separately preregistered directional strategies;
- a volatility-state signal for risk/execution research.

It is not yet an executable standalone trade.

## Why this classification is required

R27 confirms a statement about expected absolute movement:

- bottom10 prior-48-M5 realised-volatility compression
- subsequent 4b/8b absolute movement remains below the same-clock unconditional
  absolute-movement baseline

The primary confirmed estimands are functions of absolute returns.

A linear XAUUSD CFD position has directional PnL driven by signed return.

Therefore a reduction in E[|r|] does not, by itself, imply:
- E[r] > 0 for a long;
- E[r] < 0 for a short;
- positive expectancy for any frozen directional CFD position.

No direction was preregistered or confirmed by R27.

Creating one after observing R27 would be a new scientific question.

## Repository doctrine consistency

The existing XAU directional-confirmation policy explicitly classifies
non-directional movement/volatility outcomes as non-directional behavior rather
than directional alpha.

R27 is treated consistently with that doctrine.

## Why no artificial PnL backtest is allowed here

The following would introduce a new, unconfirmed mechanism rather than
economically translate the confirmed R27 estimator:

- arbitrarily going long or short during bottom10 compression;
- choosing direction from the preceding return after seeing results;
- grid/market-making rules;
- breakout/fade rules;
- SL/TP geometry;
- straddle proxies on a single linear CFD;
- selecting an existing strategy only because R27 improves its historical PnL.

Any such mapping requires a separately preregistered hypothesis.

## Instrument limitation

A directly monetizable short-volatility implementation would normally require
an instrument/payoff with volatility convexity, such as options or another
explicit volatility structure.

The current Guardian / FTMO target is XAUUSD CFD, a linear directional
instrument. Simultaneously long and short the same linear CFD does not create a
short-volatility payoff; absent other structure it only adds execution costs.

Therefore R27 cannot be promoted to a standalone FTMO/Guardian EA solely from
its confirmed absolute-movement result.

## Economic conclusion

R27:
- statistical phenomenon: CONFIRMED
- standalone directional edge: NOT ESTABLISHED
- standalone XAUUSD CFD tradability: NOT PROMOTED
- regime/filter research value: RETAINED

This is not a scientific failure of R27.

It is a classification of what the confirmed estimand can and cannot support.

## Next permitted study

The missing question is directional:

> Conditional on the exact confirmed R27 bottom10 compression state, is signed
> forward XAUUSD return different from its same-clock unconditional signed
> baseline?

That question becomes R28.

R28 must:
- use a new research identifier;
- preregister its signed estimator before calculating it;
- use discovery data first;
- freeze any discovered sign before independent confirmation;
- leave 2025 and 2026+ unopened.

## Still prohibited

- inventing a long/short rule from R27 post hoc
- PnL optimization
- SL/TP/entry search
- using bottom20 as a rescue
- 2025 opening
- 2026+ opening
- Guardian/live deployment
