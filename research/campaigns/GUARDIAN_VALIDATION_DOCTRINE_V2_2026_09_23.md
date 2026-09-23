# GUARDIAN Validation Doctrine V2 — Edge Existence != Production Readiness

Date: 2026-09-23
Status: FROZEN BEFORE ANY NEW RESEARCH RESUMES
Owner decision: research pause remains in force while historical evidence is reclassified under this taxonomy.

## Problem corrected

Guardian historically used several thresholds designed for a large standalone production edge as if failure of those thresholds meant "no edge".
That conflated four different questions:

1. Does predictive information exist?
2. Is the effect economically positive after ordinary costs?
3. Does it add value when combined with other signals?
4. Is it strong enough and operationally safe to deploy alone?

V2 separates those questions.

Historical formal verdicts are never rewritten. V2 adds a second classification layer only.

## Layer 0 — Discovery credibility

Large searches remain strict here.

Required:
- causal/as-of semantics;
- frozen target and signal definitions;
- no protected-window leakage;
- explicit search universe / trial count;
- multiplicity / data-snooping control appropriate to the family;
- valid statistical unit;
- minimum support declared before outcomes where practical.

BH/FDR, DSR/PBO or an equivalent selection-aware mechanism may be used depending on the experiment.

A discovery failure is not rescued by nearby parameter search on the same opened sample.

## Layer 1 — Edge existence on fresh data

The frozen candidate is evaluated on a genuinely later or otherwise independent sample.

The point estimate is classified, not simply passed/killed:

### NEGATIVE
Fresh-sample effect is <= 0 in the frozen economic/predictive direction.

### POSITIVE_UNCERTAIN
Fresh-sample effect is > 0 but its uncertainty interval includes zero.

This state is RETAINED as evidence.
It is not called confirmed and it is not discarded solely because p > 0.05.

### POSITIVE_CONFIRMED
Fresh-sample effect is > 0 and a prospectively declared one-sided 90% lower confidence bound is > 0
(or an equivalent one-sided cluster test has p <= 0.10).

The 0.10 level is a confidence LABEL, not a universal survival gate.
A POSITIVE_UNCERTAIN effect may still proceed to ensemble-value research.

### SPARSE_POSITIVE
Point estimate > 0 but sample support is too small for reliable uncertainty estimation.
It remains a hypothesis/clue only.

Support thresholds affect confidence labels, not whether a positive observation is erased from the evidence map.

## Layer 2 — Economic size

Applied separately from existence.

### COVARIATE_ONLY
Predictive effect exists or remains positive, but ordinary executable costs consume most/all standalone expectancy.

### MINI_EDGE
Frozen candidate has positive expectancy after the baseline realistic cost model.
No universal PF 1.10 or +0.15R minimum is required to receive this label.

### STANDALONE_CANDIDATE
Effect clears separately frozen project-specific production-size thresholds, such as PF, expectancy, frequency and stress margin.

Cost stress is a robustness label:
- STRESS_POSITIVE
- STRESS_FRAGILE

Stress failure does not retroactively erase a baseline predictive effect.

## Layer 3 — Ensemble / incremental value

Mini-edges may be useful because their value can come from independence rather than individual magnitude.

Before combination:
- signal definitions remain frozen;
- overlap and correlation are measured;
- candidate combinations are preregistered;
- incremental effect is evaluated out-of-fold / blocked in time where possible;
- no "best subset" search on the same evaluation window.

Possible states:
- REDUNDANT
- DIVERSIFYING
- INCREMENTAL_POSITIVE
- INCREMENTAL_CONFIRMED

A +0.03R signal can be valuable if it is sufficiently independent of other positive signals.

## Layer 4 — Production readiness

Only this layer may use hard operational thresholds such as:
- PF >= project target;
- max drawdown;
- FTMO daily/max-loss compatibility;
- realistic spread/slippage/commission/swap;
- minimum trade frequency;
- concentration limits;
- execution/timezone parity;
- data availability;
- failure-mode safety.

Failure here means NOT PRODUCTION READY.
It does NOT mean "no edge".

## Temporal diagnostics

Yearly signs, leave-one-year-out, trims, rolling windows and placebo shifts are diagnostics unless explicitly preregistered as Layer-1 confidence criteria.

They must not be added as new death gates after results are opened.

## Repeated significance

Do not require p<0.05 independently at discovery, replication, validation and locked OOS.

Discovery handles the broad multiple-testing burden.
Fresh blocks then estimate persistence and uncertainty.

A later positive point estimate with p=0.08 is recorded as positive evidence with uncertainty, not silently converted to zero.

## Historical results

Original PASS/FAIL/KILL/REJECT labels remain untouched for provenance.

Add:
- v2_existence_class
- v2_economic_class
- v2_ensemble_status
- v2_production_status

No historical parameter can be changed merely because V2 is more permissive.

## Protected data

V2 does not authorize opening any protected 2026 sample.
Every new protected-window access still requires a separate human gate and frozen protocol.

## Current research pause

New alpha search remains paused.

Allowed during the pause:
- read-only audit of already-open historical/OOS outputs;
- reclassification under V2;
- exact parity checks;
- preregistration of future diagnostics/ensemble experiments.

Not allowed:
- parameter rescue;
- new threshold sweep;
- new market outcome search;
- protected-2026 access.
