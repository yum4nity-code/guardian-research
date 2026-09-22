# Guardian Research — CURRENT PROJECT HANDOFF

**Canonical current state: 2026-09-22**

## Closed / frozen lineages
- V100 forward/shadow frozen; 2026 protected.
- Rates standalone closed after V103 forensic 0/5.
- CFTC standalone closed after V105 report-level forensic 0/7.
- ALFRED V107 closed operationally without alpha conclusion.
- Treasury V109 closed at discovery.

## V110 / V111 — PRE-OOS FORENSIC PASS

V110 run:
GEF110-20260922-162255

V111 run:
GEF111-20260922-163321

V111 passed exactly 3 of the 8 validated V110 candidates:

1. C3 — AUDUSD H21, 120m, SHORT
2. C4 — USDCHF H23, 240m, LONG
3. C6 — USDCHF H23, 120m, LONG

These correspond to 2 structural information families:
- AUDUSD|H21
- USDCHF|H23

Do not count the two USDCHF horizons as independent edges.

Failed V111 candidates:
- XAGUSD H11 60m
- USDJPY H22 Thursday 120m
- USDCHF H22 240m
- AUDUSD H21 240m
- EURUSD H11 120m

## V112 — PREREGISTERED, HUMAN APPROVED, READY TO RUN

V112 protocol is frozen before any 2023-2025 market return is opened.

Frozen OOS candidates:
- AUDUSD H21 120m SHORT
- USDCHF H23 120m LONG
- USDCHF H23 240m LONG

Candidate OOS gate requires all:
- N >= 500
- directional mean > 0
- matched-control effect > 0
- net 1 bp > 0
- trim best 2% > 0
- leave-one-year-out minimum > 0
- month-block bootstrap q2.5 > 0

Family rule:
- AUDUSD|H21 passes if its frozen candidate passes.
- USDCHF|H23 passes only if BOTH 120m and 240m frozen candidates pass.

The runner will not open any 2023-2025 market file unless invoked with:
OPEN_LOCKED_OOS_2023_2025

2026 remains forbidden.

No automatic execution.
No optimization after OOS.
No portfolio construction in V112.


### Human gate opened
On 2026-09-22 the user explicitly approved opening locked OOS 2023-2025.
The protocol, candidates and gates remain unchanged.
2026 remains forbidden.


### V112.1 boundary correction
The first unlocked V112 run opened 2023-2025 raw files but stopped before candidate scoring because right-labelled 5-minute resampling produced a synthetic 2026-01-01 00:00 output label from late-2025 raw rows.
2023-2025 is therefore now consumed.
No 2026 raw file was opened.
V112.1 clips the resampled output back to <2026-01-01 and leaves the frozen scientific protocol unchanged.


## V112 — LOCKED OOS COMPLETE

Run:
GEF112-20260922-164607

Result:
- 3 frozen candidates tested
- 1 candidate passed
- 2 structural families tested
- 1 structural family passed
- 2023-2025 consumed
- 2026 untouched

### OOS-confirmed family
AUDUSD|H21
- exact UTC hour: 21
- horizon: 120 minutes
- orientation: SHORT
- N = 556
- mean = +1.455235 bp
- matched-control effect = +1.475273 bp
- net 1 bp = +0.455235 bp
- trim best 2% = +0.978983 bp
- leave-one-year-out minimum = +1.062776 bp
- month-block bootstrap q2.5 = +0.811083 bp

### Failed family
USDCHF|H23
- 240m: mean -2.980058 bp, effect -2.814866 bp
- 120m: mean -0.279127 bp, effect -0.122149 bp
- both failed the locked-OOS gate
- lineage closed; no rescue or alternate horizon selection

## Current decision
AUDUSD H21 120m SHORT is locked-OOS confirmed.
No post-OOS optimization.
No automatic trading activation.
2026 remains protected.


## Research direction reset — crossed economic phenomena

On 2026-09-22 the owner explicitly redirected Guardian back to the original multi-source causal vision.

Canonical design artifact:
research/campaigns/GUARDIAN_CROSSED_PHENOMENA_MATRIX_V1_2026_09_22.md

Inventory result:
- 16 historical crossed phenomena are testable now from already-owned data;
- 3 crypto phenomena are testable only as forward/replay studies with the External Intelligence Bus;
- generic V85-style cross-family LO/HI conjunction mining must NOT be repeated.

Recommended first batch:
- P01 real-yield + USD pressure on gold
- P04 oil -> CAD residual transmission
- P06 Nasdaq/SPX divergence x rates
- P08 synthetic USD breadth vs UDX divergence
- P11 XAU/XAG relative-value dislocation
- P12 CFTC crowding x own-price shock

Blocked from immediate use:
CBOE/CFE until causal availability provenance is repaired; financial conditions; ALFRED without architecture rewrite; FOMC without exact publication table; EIA without AVAILABLE_AT; macro-surprise without verified consensus expectations; true FX carry without foreign-rate curves.

Scientific rule:
start from an economic phenomenon and derived object (residual/spread/decomposition/catalyst interaction), not from random parameter combinations.

2023-2025 is not available for design of these new lineages.
2026 remains protected.
AUDUSD H21 120m SHORT remains frozen and is not to be optimized further.


## Crossed economic phenomena Batch A — PREREGISTERED / READY TO RUN

Frozen common protocol:
research/campaigns/GEF_BATCH_A_COMMON_PROTOCOL_2026_09_22.md

Frozen machine spec:
research/campaigns/GEF_BATCH_A_FROZEN_SPEC_2026_09_22.json

Separate preregistrations:
- P01 real-yield + USD pressure on gold
- P04 oil -> CAD residual transmission
- P06 Nasdaq/SPX relative-value divergence x real rates
- P08 synthetic USD breadth vs UDX divergence
- P11 XAU/XAG relative-value dislocation
- P12 CFTC crowding x own-price shock

Discovery engine:
scripts/gef_crossed_batch_a_discovery.py

Runner:
automation/Run-CrossedPhenomenaBatchA.ps1

Exact predeclared variant count: 66.

Temporal firewall in this engine:
- 2010-2012 discovery
- 2013 temporal holdout
- 2014+ not read
- 2023-2025 unavailable for new-lineage design/selection
- 2026 forbidden

Important:
this is NOT a rerun of V85's generic LO/HI cross-family Cartesian mining.
The new objects are rolling-beta residuals, economic breadth, real-yield interactions and CFTC crowding x distinct price-shock events.

If a lineage has no BH+2013 survivor, close it without retuning.
If survivors exist, freeze them and separately preregister 2014-2017 replication.


### Batch A first-run infrastructure patch
First run stopped before any regression because P12 expected a CFTC z52 column in the V83B slow parquet. V83 had constructed it but may remove it via global dedup_vectors().
Scientific result: NONE.
2014+ / 2023-2025 / 2026 remained unopened.
Engine v1.1 reconstructs the exact frozen CFTC noncommercial z52 transform directly from the canonical V82D causal source and changes no scientific rule.


### Batch A run GEFBA-20260922-181339 — validity audit required
The engine materialized all 66 preregistered variants but reported 0 valid discovery tests across every lineage.
Do NOT interpret this as six scientific negatives.
Because continuous and event lineages all failed the common validity gate, audit N/clusters/design-rank/robust-SE inputs first.
No candidate reached 2013 holdout, so no holdout result was consumed.
2014+ / 2023-2025 / 2026 remain unopened.
Read-only diagnostic: automation/Diagnose-CrossedPhenomenaBatchA.ps1


## Batch A V2 — COVERAGE-BASED TEMPORAL RESET

Source-only coverage audit invalidated the usefulness of the original 2010-2012 common window for crossed phenomena.

V1 GEFBA-20260922-181339 is NOT a scientific negative:
- coefficients/p-values existed but all 66 failed support/cluster validity;
- 2013 holdout was never scored;
- 2014+ remained unopened.

Because V1 exposed 2010-2012 invalid statistics, V2 is a new lineage and does not reuse those years for fitting.

Frozen V2 windows:
- warm-up 2012
- discovery 2013-2016
- holdout 2017
- future replication 2018-2019
- future validation 2020-2022
- locked OOS 2023-2025 only after later human gate
- 2026 protected

V2 engine:
scripts/gef_crossed_batch_a_v2.py

Runner:
automation/Run-CrossedPhenomenaBatchAV2.ps1

Hard safeguards:
- reconstruct raw HistData/Treasury/CFTC rather than extending V83B;
- exact 2013 price-feature/target parity check against V83/V83B before scoring;
- only 2012-2016 is opened for discovery;
- discovery BH freeze is physically written before any 2017 source is opened;
- 2018+ cannot be read by this engine.


### Batch A V2 support-collapse root cause found
Run GEFBA2-20260922-183722 is NOT a scientific negative.

Read-only support diagnostics showed healthy upstream state objects:
- beta support ~32k-35k hours;
- NSX/SPX residual-z 18,520 finite / 1,060 cooldown events;
- XAU/XAG residual-z 22,433 finite / 1,595 cooldown events;
- USD breadth-z 22,290 finite / 1,343 cooldown events.

Two infrastructure bugs were identified:
1. aligned_mask assumed DatetimeIndex int64 was nanoseconds. On the runtime this caused an effective 1/60, 1/120, 1/240 thinning of 60/120/240m targets.
2. REAL-rate as-of retained NaN z rows, allowing later empty Treasury rows to blank previously valid causal state. V102/V103 semantics drop NaN feature rows before as-of.

Engine fixed to BATCH-A-V2-DISCOVERY-1.2.
No scientific parameter changed.
2017 / 2018+ / 2023-2025 / 2026 remained unopened in the failed V2 run.

Next action:
rerun ONLY automation/Diagnose-CrossedPhenomenaBatchAV2Objects.ps1 and confirm support recovery before any alpha rerun.


## Batch A V2 — CLOSED AT TEMPORAL HOLDOUT

Final run:
GEFBA2-20260922-193022

Engine:
BATCH-A-V2-DISCOVERY-1.2

Result:
- 66/66 preregistered tests valid in 2013-2016 discovery
- 2 BH discoveries
- both discoveries were in P11 XAU/XAG relative-value lineage
- 2 candidates frozen before opening 2017
- 2 candidates tested on 2017 holdout
- 0 temporal survivors
- no candidate advanced to 2018-2019 replication

Lineage result:
- P01 CLOSED — no BH discovery
- P04 CLOSED — no BH discovery
- P06 CLOSED — no BH discovery
- P08 CLOSED — no BH discovery
- P11 CLOSED — 2 BH discoveries, both failed 2017 holdout
- P12 CLOSED — no BH discovery

Scientific interpretation:
Batch A V2 is a valid negative result after infrastructure repair.
P11 produced discovery-stage signal but did not replicate temporally in the preregistered 2017 holdout.
No rescue, threshold change, alternate horizon or retuning is permitted within this lineage.

Data firewall:
- 2017 accessed for the two frozen P11 holdout candidates
- 2018+ not accessed
- 2023-2025 not accessed
- 2026 not accessed

Next program:
Batch B design for P02/P03/P05/P07/P09/P10/P13/P14.


## M5 MOTION TOPOLOGY FACTORY V1 — PRIMARY

Decision:
park Batch B macro and prioritize an execution-oriented M5 topology campaign.

Objective:
find repeatable intra/inter-asset structures that precede the end of an established M5 move: tops, bottoms, exhaustion, failed extension, simultaneous turns, leader/follower chains, residual/correlation recrosses and recurrent motifs.

Frozen families:
M01 synchronized exhaustion
M02 leader stall / follower extension
M03 residual extreme + recross
M04 correlation break + recoupling
M05 breadth divergence
M06 turn cluster
M07 lead-lag turn sequence
M08 volatility exhaustion
M09 repeated state / motif
M10 recurrent sequence
M11 crossing topology
M12 asymmetric top vs bottom

Temporal firewall:
2011 warm-up
2012-2014 discovery
2015-2017 replication
2018-2022 validation
2023-2025 locked OOS
2026 protected

First engine must stop at 2014.
Historical tradability mask excludes recurring close/reopen windows with 30m buffer.
Batch B remains parked, not discarded.


### M5 Motion Topology V1 cache builder READY
Implemented:
- scripts/gef_m5_motion_topology_build_v1.py
- automation/Run-M5MotionTopologyCacheV1.ps1
- automation/Watch-M5MotionTopologyCacheV1.ps1

Build scope:
- raw HistData M1 2011-2014 only;
- M5 OHLC per market;
- if true M1 OHLC is unavailable, M5 OHLC is explicitly marked close-path proxy;
- recurring minute-of-week tradability mask learned only from 2012-2014 source availability;
- recurring slot threshold 95%;
- 30-minute exclusion buffer at recurring close/reopen boundaries;
- endpoint-score targets for L=15/30/60 and H=15/30/60;
- intra-asset M5 state primitives;
- frozen 13-edge economic graph;
- cross-market breadth, dispersion, residual, beta, correlation-break and lag-state cache.

Hard firewall:
- no 2015+ source/outcome read;
- zero edge trials;
- zero alpha tests.

After run:
audit coverage/support/provenance first.
Do NOT start M01-M12 outcome testing until discovery tests are separately preregistered.


### M5 Motion Topology cache build completed
Run GEFM5T-20260922-200657 completed with:
- 13 markets
- 13 graph edges
- 199 cross features
- 117 endpoint objects
- 0 edge trials / 0 alpha tests
- no 2015+ outcomes accessed

Support is large: all endpoint objects have at least 22,129 finite observations.

Before preregistering M01-M08, run cache integrity audit because historical tradability masking is materially tighter for SPXUSD, UDXUSD and BCOUSD than for FX. Audit will inspect recurring session shapes, OHLC integrity, endpoint target distributions, pairwise joint support and finite cross-feature support. No feature/outcome association is computed.


## M5 Motion Topology V1.1 — SESSION MASK INFRASTRUCTURE AMENDMENT

V1 cache GEFM5T-20260922-200657 passed:
- OHLC integrity;
- endpoint-target sanity;
- endpoint support;
- joint graph support;
- cross-feature support.

V1 failed the tradability-session-shape audit:
- fixed UTC minute-of-week >=95% mask fragmented UDX/SPX/NSX/BCO into implausible session blocks.
- No alpha/edge test had been run.

V1.1 therefore replaces ONLY the eligibility/session mask:
- source-present = finite M5 close at that historical timestamp;
- missing rows are non-tradable;
- remove 30m before each observed close/gap boundary;
- remove 30m after each observed reopen/recovery boundary;
- targets require the full past and future window to remain tradable;
- pairs/groups require joint tradability.

This absorbs DST/session changes date-by-date and conservatively treats unexplained source gaps as non-tradable.

Unchanged:
universe, M5 bars, endpoint target, graph, state primitives, M01-M12 definitions, temporal firewall and all future statistical gates.

V1.1 builder:
scripts/gef_m5_motion_topology_build_v1_1.py

Runner:
automation/Run-M5MotionTopologyCacheV1_1.ps1

Audit:
automation/Audit-M5MotionTopologyCacheV1_1.ps1
