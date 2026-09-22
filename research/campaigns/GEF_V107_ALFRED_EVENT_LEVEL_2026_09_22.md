# GEF V107 — ALFRED first-vintage event-level discovery

Status: PRE-REGISTERED / READY TO RUN
Date: 2026-09-22

## Source decision

V106 audited 127 candidate source files and found only alfred_vintage ready for research:
- 53 candidate files
- 39 safely inspectable tables
- coverage 2000-2022
- 39 tables with causal vintage semantics
- V85 features: 0

Therefore V107 builds a new standalone ALFRED family directly from the audited normalized revision-summary tables.

## Causality

Canonical rule inherited from V80C:
- only first_vintage and first_value are allowed;
- AVAILABLE_AT = first_vintage + 1 calendar day at 00:00 UTC, conservative;
- forbidden leakage fields: last_vintage, last_value, was_revised, vintage_count and any final/revised value;
- transforms are computed strictly in first-vintage order using only prior released first-values.

## Statistical unit

ALFRED releases are sparse macro information events. V107 counts exactly one observation per distinct ALFRED release/vintage event and never counts every carried-forward 5-minute bar as independent.

At each release AVAILABLE_AT, entry is the first actually tradable frozen target timestamp at or after availability.

## Candidate features

For each usable revision-summary series:
- level: first_value
- d1: current first_value minus previous released first_value
- d3: current first_value minus value three releases earlier
- z24: rolling 24-release z-score computed from prior releases only

V107.2 state design is support-aware and fixed before any finite alpha test: d1/d3 use NEG versus POS release changes; level/z24 use below-versus-above the prior expanding median. No magnitude threshold is optimized.

## Targets

Guardian HistData markets with sufficient local M1 coverage; horizons 60, 120 and 240 minutes only.

## Temporal protocol

Discovery 2010-2013: minimum 12 release-events spanning at least 3 calendar years, raw p <= .05, BH q <= .10; direction selected only from discovery mean. Freeze <=150 before 2014+.

Replication 2014-2017: min 12 releases, mean >0, net 1 bp >0, positive-year fraction >=.50, remove best 2 releases >0.

Pre-validation robustness: remove best 3 >0, remove best month >0, leave-one-year-out minimum >0, +1 calendar-day availability delay >0, +2 calendar-day availability delay >0.

Validation 2018-2022: min 15 releases, mean >0, net 1 bp >0, positive-year fraction >=.60, remove best 3 >0, remove best 5 >0, remove best month >0, leave-one-year-out minimum >0.

STOP after validation. Do not open 2023-2025. Do not open 2026.


## V107.1 sparse-event design correction

The first V107.0 run stopped with "No finite ALFRED discovery tests" before any candidate p-value table existed.

Root cause: the preregistered support requirements (18 discovery extreme-state events plus a separate 2013 holdout) were structurally incompatible with monthly/quarterly macro release frequency.

V107.1 changes the temporal design before any finite alpha test:
- discovery becomes 2010-2013 as one discovery block;
- minimum discovery support = 8 release-events spanning >=3 years;
- replication minimum = 8 events;
- validation minimum = 10 events;
- the z=1 state definition, BH correction, target horizons, directions and robustness gates are unchanged.

Physical firewall correction:
- V107.0 loaded price histories through 2022 before failing, although it did not form or score any finite discovery test;
- V107.1 loads prices only through 2013 before the discovery freeze, through 2017 only after that freeze, and through 2022 only after the pre-validation freeze;
- 2023-2025 and 2026 remain unopened.


## V107.2 state redesign after zero-test V107.1

V107.1 again produced zero finite discovery tests, before any p-value table or candidate freeze.

The issue is therefore the rare-event state definition itself, not the temporal split.

V107.2 replaces extreme z states with predeclared high-support event states:
- d1/d3: NEG if change <0, POS if change >0;
- level/z24: below/above the expanding median computed from prior releases only.

Support gates are increased to 12 discovery events, 12 replication events and 15 validation events.

Because V107.0 and V107.1 produced no finite discovery tests, no return-based result was used to choose this redesign.


## V107.3 final redesign after zero-support V107.2

V107.2 again produced zero finite discovery tests before any p-value table or candidate freeze.

Root causes identified:
1. V106 found 39 safely inspectable ALFRED tables, but V107.0-2 consumed only 13 revision-summary parquet files.
2. Splitting already sparse macro releases into discrete state buckets destroyed support.

V107.3 therefore:
- audits every parquet/csv table under DataLake/normalized/alfred_pre2023;
- accepts only causally defensible first-release representations:
  - first_vintage + first_value; or
  - earliest realtime_start/vintage per observation with the corresponding first value;
- writes ALFRED_SOURCE_DIAGNOSTICS.csv before alpha work;
- writes EVENT_SUPPORT_2010_2013.csv before reading discovery returns;
- if no feature has >=12 causal release-events spanning >=3 discovery years, exits cleanly with COMPLETE_V107_NO_DISCOVERY_SUPPORT;
- uses a symmetric event strategy instead of splitting states:
  position sign = sign(causal feature score) × one discovery-frozen orientation;
- d1/d3 causal score = sign(change);
- level/z24 causal score = sign(current value minus prior expanding median);
- all candidate observations remain one distinct ALFRED first-release event.

The temporal market-return firewall remains physical:
- discovery prices <=2013 only;
- 2014-2017 prices loaded only after discovery freeze;
- 2018-2022 prices loaded only after pre-validation freeze;
- 2023-2025 and 2026 forbidden.

No return-based result from V107.0, V107.1 or V107.2 was available or used to choose this redesign because all three stopped before a finite discovery test existed.
