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

Each candidate feature is then standardized causally in release space. Baseline states are LO <= -1 and HI >= +1.

## Targets

Guardian HistData markets with sufficient local M1 coverage; horizons 60, 120 and 240 minutes only.

## Temporal protocol

Discovery 2010-2012: minimum 18 releases, raw p <= .05, BH q <= .10; direction selected only from discovery mean.
2013 confirmation: minimum 6 releases and same directional mean > 0.
Freeze <=150 before 2014+.

Replication 2014-2017: min 20 releases, mean >0, net 1 bp >0, positive-year fraction >=.50, remove best 2 releases >0.

Pre-validation robustness: remove best 3 >0, remove best month >0, leave-one-year-out minimum >0, z0.9 >0, z1.1 >0, additional +1 calendar-day availability delay >0.

Validation 2018-2022: min 25 releases, mean >0, net 1 bp >0, positive-year fraction >=.60, remove best 3 >0, remove best 5 >0, remove best month >0, leave-one-year-out minimum >0.

STOP after validation. Do not open 2023-2025. Do not open 2026.
