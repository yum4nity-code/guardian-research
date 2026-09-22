# GEF V102 — Standalone Rates / Real Yields / Breakevens

Status: PRE-REGISTERED / READY TO RUN
Date: 2026-09-22

## Prior result

V101 sparse price × price × rates interaction family is CLOSED.

Canonical completed run:
- run_id: GEF101-20260922-142601
- engine: V101.2
- atomic shortlist: 3641
- attempted triples: 17417
- finite discovery triples: 187
- frozen before replication: 150
- replication survivors: 2
- validation survivors: 0
- 2023-2025 accessed: false
- 2026 accessed: false

Do not rescue the two V101 replication survivors and do not retune the V101 interaction family.

## V102 question

Do causally available nominal-rate, real-yield, breakeven or yield-curve states have standalone predictive information for the existing Guardian target universe that survives:

2010-2012 discovery
→ 2013 internal confirmation
→ 2014-2017 replication
→ pre-validation robustness
→ immutable freeze
→ 2018-2022 validation?

This is a standalone family test. No price condition is allowed in V102 candidate definitions.

## Source lineage

Reuse:
- V83B repaired canonical rates matrix;
- V85 frozen eligible-feature catalog;
- V85 frozen singleton state caches and train p-value ledger;
- V101.2 tested reconstruction semantics for extending rates beyond 2013.

Only features with family == rates_yields are eligible.

No V100 rank, V101 triple result, 2023-2025 result or 2026 value may influence candidate selection.

## Discovery

Candidate = exactly one rates_yields feature state:
- LO <= -1 expanding z
- HI >= +1 expanding z

Target universe = frozen V85 return targets.

2010-2012:
- minimum N 120
- finite train p
- direction determined only by discovery mean

Multiplicity:
- Benjamini-Hochberg across all finite eligible rates singleton tests.

Candidate discovery gates:
- raw train p <= 0.05
- BH q <= 0.10

2013 internal confirmation:
- minimum N 40
- same directional mean > 0

Freeze at most 200 candidates before any 2014+ scoring.

## Replication 2014-2017

Exact frozen feature/state/target/direction:
- N >= 60
- gross directional mean > 0
- net after diagnostic 1 bp > 0
- positive-year fraction >= 0.50
- trim best 1% mean > 0

No threshold changes.

## Pre-validation robustness

Using 2014-2017 only, replication survivors must additionally pass:
- trim best 2% mean > 0
- remove best 3 events mean > 0
- non-overlap mean > 0
- neighboring state z=0.9 keeps positive mean
- neighboring state z=1.1 keeps positive mean
- +1 calendar-day information-lag diagnostic keeps positive mean

Neighbor and lag checks are diagnostics only. They may reject a candidate but may never redefine it.

Freeze exact survivors and SHA before opening 2018-2022.

## Validation 2018-2022

Exact frozen definition:
- N >= 80
- gross mean > 0
- net after 1 bp > 0
- positive-year fraction >= 0.60
- trim best 1% > 0
- trim best 2% > 0
- remove best 5 events > 0
- non-overlap mean > 0

STOP after validation.

Do not open 2023-2025.
Do not open 2026.

## Outputs

D:\MT5_Backtests\Research\Autonomous\guardian_edge_factory_v102_standalone_rates\GEF102-*

- LIVE_STATUS.json
- RATE_ATOMS_ALL.csv
- FROZEN_RATES_PRE_2014.csv
- DISCOVERY_FREEZE.json
- RECONSTRUCTION_PARITY_2010_2013.csv
- REPLICATION_RESULTS.csv
- ROBUSTNESS_RESULTS.csv
- FROZEN_PRE_VALIDATION.csv
- PRE_VALIDATION_FREEZE.json
- VALIDATION_RESULTS.csv
- FINAL_SURVIVORS.csv
- RUN_RECEIPT.json
- V102_REPORT.md
