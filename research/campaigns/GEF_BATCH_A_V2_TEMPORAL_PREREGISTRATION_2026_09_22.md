# Guardian Crossed Economic Phenomena — Batch A V2 temporal preregistration

Date: 2026-09-22
Status: FROZEN BEFORE V2 COMPUTE

## Why V2 exists

Batch A V1 materialized all 66 variants but produced zero valid tests because its 2010-2012 common-data support was not adequate for the preregistered statistical-unit gates.

V1 exposed invalid discovery coefficients/p-values for 2010-2012. Therefore V2 is a NEW lineage and does not reuse those years for fitting.

No V1 threshold, sign, market, horizon or coefficient is inherited.

## Window selection rule

Window selection uses source coverage only, never returns or alpha.

Choose the earliest four consecutive post-exposure years satisfying stable common price coverage for the crossed-price phenomena.

Coverage audit result supports:
- warm-up: 2012
- discovery: 2013-01-01 through 2016-12-31
- untouched temporal holdout: 2017-01-01 through 2017-12-31

The V2 discovery engine MUST NOT read 2018+ market returns.

Future windows are preregistered now but not opened by V2 discovery:
- replication: 2018-2019
- validation: 2020-2022
- locked OOS: 2023-2025 only after full pre-OOS human gate
- protected: 2026

## Economic lineages

Exactly the same six economic phenomena:
- P01 real-yield + USD pressure on gold
- P04 oil -> CAD residual transmission
- P06 Nasdaq/SPX divergence x real rates
- P08 synthetic USD breadth vs UDX divergence
- P11 XAU/XAG relative-value dislocation
- P12 CFTC crowding x own-price shock

Exactly 66 predeclared variants:
P01 9, P04 6, P06 9, P08 6, P11 3, P12 33.

## V2 data reconstruction

V2 must reconstruct from raw/canonical sources rather than extend the old V83B matrix:
- HistData M1 only for 2012-2017 in this discovery engine;
- Treasury nominal/real curve raw XML through 2017 only;
- CFTC Futures Only raw archives through 2017 only.

2018+ files must not be read.

### Price semantics
HistData raw timestamp +5h fixed UTC conversion, inherited from the existing architecture.
M1 -> 5m:
resample("5min", label="right", closed="left").last()

Decision rows:
exact top-of-hour 5m labels.

Before V2 scoring, reconstructed 2013 60m returns and 60/120/240m forward targets must reproduce the frozen V83/V83B 2013 layers within numerical tolerance.

### Rates
Use the existing V102/V103 Treasury reconstruction:
- official nominal and real curve XML;
- REAL 5Y / 10Y / 30Y;
- d1 changes;
- conservative AVAILABLE_AT = observation_date + 1 calendar day.

For V2 interaction standardization:
- standardize the distinct daily REAL d1 observations themselves;
- expanding prior mean/std;
- min 126 observations;
- shift(1);
- then as-of carry the z-score from AVAILABLE_AT to decision time.

Do not infer a new release time.

### CFTC
Use existing V104/V105 raw archive normalization:
- Futures Only reports;
- exact frozen market mappings;
- noncommercial net % OI;
- z52 = rolling 52 reports, min 26;
- AVAILABLE_AT = next Sunday after report_date, exactly as V104;
- as-of carry only after AVAILABLE_AT.

Statistical clustering is by distinct CFTC report_date.

## Common derived objects

Causal rolling beta:
- 60m top-of-hour returns;
- 480 hourly observations;
- minimum 240 paired observations;
- rolling covariance / variance;
- shift(1).

Fast z:
- expanding prior mean/std;
- min 250 hourly observations;
- shift(1).

Event threshold:
|z| >= 1.5.

Event cooldown:
240 minutes.

No threshold or lookback search.

## Models

Unchanged from V1:
- P01 interaction REAL d1 z × UDX 60m z on XAU|UDX forward residual.
- P04 oil-shock z on USDCAD|UDX forward residual.
- P06 NSX|SPX current residual z × REAL d1 z on NSX|SPX forward residual.
- P08 UDX-vs-synthetic-USD breadth divergence z -> UDX/XAU/XAG forward return.
- P11 XAU|XAG residual z -> future XAU|XAG residual.
- P12 CFTC noncomm crowding z52 × own-price shock z -> own-market forward return.

## Inference

Discovery 2013-2016:
- N >= 120
- independent clusters >= 80
- cluster-robust OLS
- P01/P04/P06/P08/P11 clusters = UTC calendar day
- P12 clusters = distinct CFTC report_date
- BH-FDR q <= 0.05 separately inside each lineage

Only BH discoveries may access 2017.

Holdout 2017:
- N >= 40
- clusters >= 20
- coefficient sign frozen from discovery
- same sign required
- one-sided cluster-robust p <= 0.10

STOP after 2017.

## Anti-rescue rule

If V2 still lacks statistical support, do not lower N, cluster, BH, event threshold, cooldown or holdout gates.

If a source reconstruction fails parity, classify INFRASTRUCTURE and fix only the reconstruction.
