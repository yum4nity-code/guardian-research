# Guardian Crossed Economic Phenomena — Batch A common protocol

Date: 2026-09-22
Status: FROZEN BEFORE COMPUTE

## Temporal firewall
- discovery fit: 2010-01-01 through 2012-12-31
- temporal holdout: 2013-01-01 through 2013-12-31
- 2014+ market returns: forbidden in this discovery engine
- 2023-2025: forbidden for design/selection of these new lineages
- 2026: forbidden

## Common causal rules
- all rolling moments are shifted by one observation before use;
- all slow data are joined as-of, never forward;
- rates keep the existing conservative availability semantics already embedded in the V83/V83B layer;
- CFTC uses the existing exact causal mapping and AVAILABLE_AT semantics;
- targets remain separate from predictors;
- missing exact observations are not forward-filled inside fast price returns.

## Common market-time grid
Discovery models use exact top-of-hour rows from the frozen 5-minute causal architecture.

Horizons:
- 60 minutes
- 120 minutes
- 240 minutes

For a horizon H, only timestamps aligned to a non-overlapping H-minute epoch grid are used.

## Causal rolling beta
For a target A and control B:
beta_t = Cov(rA_60m, rB_60m) / Var(rB_60m)

- computed on exact top-of-hour 60m returns;
- rolling lookback = 480 hourly observations;
- minimum = 240 valid paired observations;
- shifted by one hour.

Forward residual target:
epsilon_fwd(A|B,h) = rA_fwd_h - beta_t * rB_fwd_h

## Causal z-score
Fast continuous objects:
- expanding prior mean/sd;
- minimum 250 observations;
- shifted by one observation.

Slow daily-rate changes:
- collapse to one daily observation before standardization;
- expanding prior mean/sd;
- minimum 126 daily observations;
- shifted by one day;
- map backward/as-of to decision time.

## Event threshold
Where a phenomenon is event-based:
|z| >= 1.5

No threshold search.

Cooldown:
- P04 oil shocks: 240 minutes
- P08 USD breadth divergence: 240 minutes
- P11 XAU/XAG residual dislocation: 240 minutes
- P12 price shock: 240 minutes

Only the first qualifying event after cooldown is admitted.

## Inference
- continuous hourly phenomena: cluster-robust OLS by UTC calendar day;
- event phenomena: cluster-robust OLS by UTC calendar day;
- P12: cluster by distinct CFTC state/report instance, not by 5-minute row.

Minimum discovery evidence:
- at least 120 usable observations/events;
- at least 80 independent clusters.

Minimum 2013 holdout evidence:
- at least 40 usable observations/events;
- at least 20 independent clusters.

## Discovery / holdout gate
Within each phenomenon lineage separately:
1. fit all predeclared variants on 2010-2012;
2. use two-sided cluster-robust p-values;
3. BH-FDR q <= 0.05 within the lineage;
4. freeze coefficient sign from discovery;
5. 2013 must have same sign;
6. one-sided cluster-robust p <= 0.10 in that frozen sign;
7. no variant is promoted merely because another parameterization failed.

If no variant survives, that lineage closes at discovery.

## No pooled multiplicity laundering
The six lineages have separate economic hypotheses and separate predeclared trial families.
A global Batch-A summary must still report:
- total valid tests across all six;
- discoveries by lineage;
- null/survival rate by lineage.

No result from one lineage changes another lineage's threshold or model.

## Stop
The Batch-A discovery engine stops after 2013 holdout.
It must not read 2014+ market returns.
