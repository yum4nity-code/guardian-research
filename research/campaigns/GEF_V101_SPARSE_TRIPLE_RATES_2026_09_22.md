# GEF V101 — Sparse Triple Rates Discovery

Status: PRE-REGISTERED / READY TO RUN
Date: 2026-09-22
Scope: research only, pre-2023 data only.

## Immutable V100 reference

V100 is not a new discovery test. It is the frozen forward/shadow package for the already-promoted lineage.

Canonical operator receipt:
- run_id: GEF100-20260922-094644
- status: V100_FORWARD_SHADOW_PACKAGE_FROZEN
- source_v97e: GEF97E-20260922-085850
- source_v99: GEF99-20260922-092305
- frozen panel SHA256: 0dd255ce02f1ac528ecc8b38293213d779d0647a79b2a9f065eee5ee550810f4
- frozen ranks: 7, 9
- compile: PASS, 0 errors / 0 warnings
- activation_not_before: 2027-01-02 00:00
- shadow_only: true
- real_seed_included: false
- order_sending_code_present: false
- 2026_market_values_accessed: false

V101 MUST NOT use ranks 7/9 to choose features, thresholds, markets, targets, directions or interactions. They are historical evidence only.

## Question

Does adding one causally available rates/real-yield/breakeven state to two independent price/intermarket states produce a new effect that:
1. exists in 2010-2012,
2. keeps its sign in the internal 2013 discovery holdout,
3. replicates unchanged in 2014-2017,
4. validates unchanged in 2018-2022?

## Why this test

The existing factory already scanned large singleton and pair universes. Repeating the same search would only increase data mining. V101 therefore tests a materially new bounded class:

PRICE STATE A AND PRICE STATE B AND RATES STATE -> TARGET/HORIZON/DIRECTION

Exactly three conditions:
- two fast price/intermarket conditions;
- one rates_yields condition;
- the two price conditions must come from different price families/markets;
- all three atomic conditions must independently show the same target/direction sign in the discovery window and 2013 holdout.

No four-way interactions. No black-box ML. No SL/TP/trailing optimization.

## Temporal firewall

Selection:
- 2010-2012: discovery
- 2013: internal discovery holdout

Replication:
- 2014-2017

Validation:
- 2018-2022

Forbidden:
- 2023-2025: never read by V101
- 2026+: never read by V101

The V100 lineage has historical 2023-2025 evidence, but V101 may not use that evidence for selection.

## Discovery budget

Atomic shortlist per target + direction:
- up to 10 fast-price atoms
- up to 8 rates atoms
- atomic train p <= 0.05
- train n >= 120
- 2013 n >= 40
- same directional mean > 0 in 2013

Triple discovery:
- exactly 2 price atoms + 1 rates atom
- price atoms from different price families
- train n >= 80
- 2013 n >= 20
- same direction positive in both windows
- Benjamini-Hochberg FDR q <= 0.10 across all finite triple tests
- maximum 150 frozen triples, selected only by pre-2014 information

If zero triples survive, V101 ends successfully with NO_DISCOVERY_SURVIVORS.

## Replication gate — frozen before reading 2018+

2014-2017:
- n >= 40
- gross mean > 0
- net mean after diagnostic 1 bp > 0
- positive-year fraction >= 0.50
- trim best 1% mean > 0

Write FROZEN_PRE_VALIDATION.csv and its SHA256 before any 2018-2022 file is read.

If zero candidates pass, stop. Do not open validation.

## Validation gate

2018-2022:
- n >= 60
- gross mean > 0
- net mean after diagnostic 1 bp > 0
- positive-year fraction >= 0.60
- trim best 1% mean > 0
- trim best 2% mean > 0
- remove best 3 events mean > 0
- non-overlap mean > 0

No rescue, threshold change, candidate replacement or ranking-based redefinition after validation is opened.

## State semantics

Reuse the V85/V83B scientific lineage:
- fast feature transforms identical to V92 reconstruction;
- causal expanding state with shift(1);
- LO <= -1 z, HI >= +1 z;
- fast min_periods = 5000;
- slow/rates min_periods = 500;
- Treasury nominal/real curve data gets conservative AVAILABLE_AT = observation date + 1 day;
- 5m price grid uses the existing HistData -> UTC +5h convention and resample(label="right", closed="left").

Before replication scoring, reconstructed 2010-2013 selected states must exactly match the frozen V85 state cache. Any mismatch is INFRASTRUCTURE FAIL, not a scientific rejection.

## Outputs

Under:
D:\MT5_Backtests\Research\Autonomous\guardian_edge_factory_v101_sparse_triple_rates\GEF101-<timestamp>

Expected:
- LIVE_STATUS.json
- ATOMIC_SHORTLIST.csv
- TRIPLE_DISCOVERY_ALL.csv
- FROZEN_TRIPLES_PRE_2014.csv
- DISCOVERY_FREEZE.json
- RECONSTRUCTION_PARITY_2010_2013.csv
- REPLICATION_RESULTS.csv
- FROZEN_PRE_VALIDATION.csv
- PRE_VALIDATION_FREEZE.json
- VALIDATION_RESULTS.csv
- FINAL_SURVIVORS.csv
- RUN_RECEIPT.json
- TEST101_REPORT.md

## Interpretation

A V101 survivor is a research candidate, not permission to trade and not permission to open 2023-2025 or 2026.

2023-2025 and 2026 remain outside V101 regardless of outcome.
