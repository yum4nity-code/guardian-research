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


## M5 Motion Topology M01-M08 — DISCOVERY READY

V1.1 cache audit PASSED:
- observed-run tradability support adequate across all 13 markets;
- OHLC integrity clean;
- endpoint support minimum 89,380 observations;
- joint graph support minimum 132,104 rows / 849 days;
- cross-feature finite support minimum 164,870 / 772 days.

Discovery preregistration frozen before outcome association:
- 291 exact variants
- matched scales only: 15->15, 30->30, 60->60
- event cooldown 30m
- min 200 independent episodes
- min 120 UTC days
- primary test: positive endpoint_score
- cluster-robust by UTC day
- BH q<=0.05 separately within M01-M08
- no rescue/retuning

Families:
M01 synchronized exhaustion
M02 leader stall / follower extension
M03 residual extreme + recross
M04 correlation break + recoupling
M05 breadth divergence
M06 turn cluster
M07 lead-lag turn sequence
M08 volatility exhaustion

Engine:
scripts/gef_m5_motion_topology_m01_m08_discovery.py

Runner:
automation/Run-M5MotionTopologyM01M08Discovery.ps1

Hard firewall:
2012-2014 outcomes only.
2015+ inaccessible in discovery engine.


## M5 Motion Topology M01-M08 — DISCOVERY RESULT

Run:
GEFM5D-20260923-052315

Result:
- 291/291 variants materialized
- 262 valid tests
- 6 BH discoveries
- all six discoveries are M04 correlation-break + recoupling
- M01/M02/M03/M05/M06/M07/M08: zero BH discoveries
- 2015+ remained unopened

Frozen M04 survivors:
- EURUSD <- UDXUSD rel -1 L15/H15
- GBPUSD <- UDXUSD rel -1 L15/H15
- GBPUSD <- UDXUSD rel -1 L30/H30
- AUDUSD <- UDXUSD rel -1 L15/H15
- AUDUSD <- UDXUSD rel -1 L30/H30
- USDCHF <- UDXUSD rel +1 L15/H15

Interpretation:
these are six candidate manifestations of one shared UDX/FX correlation-break/recoupling family, not six independent economic discoveries.

Parent survivor SHA256:
ba4323dabdb2e43c2a86d1ff6be53297a41847e00017f2098f328998ba195bb6

### 2015-2017 replication frozen before outcomes

Exact six variants only.
No retuning.
Replication engine reconstructs 2011-2017 causal history for UDX/EUR/GBP/AUD/CHF, requires pre-2015 parity against the frozen discovery cache, and scores only 2015-2017.

Replication gates:
- >=100 events
- >=60 UTC days
- positive mean endpoint
- one-sided cluster p <= 0.05
- same exact M04 object
- 2018+ hard forbidden

Engine:
scripts/gef_m5_motion_topology_m04_replication.py

Runner:
automation/Run-M5MotionTopologyM04Replication.ps1


## M04 2015-2017 REPLICATION RESULT

Run:
GEFM5R-20260923-053206

Parity:
exact pre-2015 corr_break and corr_break_z parity PASS for EURUSD/GBPUSD/AUDUSD/USDCHF.

Replication:
5 of 6 frozen discovery variants PASS.

PASS:
- EURUSD <- UDXUSD rel -1 L15/H15
- GBPUSD <- UDXUSD rel -1 L15/H15
- GBPUSD <- UDXUSD rel -1 L30/H30
- AUDUSD <- UDXUSD rel -1 L15/H15
- USDCHF <- UDXUSD rel +1 L15/H15

CLOSED:
- AUDUSD <- UDXUSD rel -1 L30/H30
  replication mean endpoint = -0.039066; no rescue.

Frozen replication survivor SHA256:
942eeda155a39446adecacba0171a04552d0c99fe86ac1cfb50fab30dce3b371

Interpretation:
five correlated manifestations of one UDX/FX M04 correlation-break -> recoupling phenomenon; not five independent edges.

### 2018-2022 independent validation frozen

Five exact survivors only.
Build causal state continuously from 2011.
Before validation, freeze a 2011-2017 parity reference that must reproduce the published replication results.
Validation engine then requires exact pre-2018 corr_break/corr_break_z parity.

Per-variant validation gates:
- >=250 episodes
- >=150 UTC days
- mean endpoint > 0
- one-sided cluster p <= 0.05
- >=4/5 positive calendar years
- leave-one-year-out minimum mean > 0
- trim-best-1% mean > 0
- trim-best-2% mean > 0

Family validates only if >=3 of 5 variants pass all gates.
Negative-control shifts +/-60m are diagnostic only.
No TP/SL/session/cost optimization.

2023-2025 remains locked.
2026 remains protected.


### M04 validation gate correction before 2018-2022 access
The initially added hard validation gates (4/5 positive years, LOO positivity, trim-best positivity and 3/5 family threshold) were removed before any 2018-2022 outcome access because they were stricter than the original M5 validation philosophy and would move the rejection threshold after replication.

Hard pass/fail now only requires:
- >=250 episodes
- >=150 UTC days
- mean endpoint_score > 0
- one-sided cluster-robust p <= 0.05

Annual means, leave-one-year-out, trim-best 1%/2% and +/-60m placebos remain mandatory diagnostics only.
No new family-level mechanical threshold.


### M04 pre-2018 reference frozen — validation ready
Reference run:
GEFM5P-20260923-055333

- 736,416 rows
- corr_break and corr_break_z for EURUSD/GBPUSD/AUDUSD/USDCHF versus UDXUSD
- SHA256: 49eb9c029247ee2418cc06cac3cacd44c1a692e46b537e982c00b3ef0b016c84
- replication aggregate parity PASS for all six original replication variants
- numerical differences are floating-point epsilon only
- no 2018+ access

2018-2022 validation engine v1.1 is now cleared to run.
2023-2025 remains locked.
2026 remains protected.


## M04 2018-2022 VALIDATION RESULT

Run:
GEFM5V-20260923-055623

Primary validation passes under the amended simple gates:
- EURUSD <- UDXUSD rel -1 L15/H15
  - N 1,718 / 409 days
  - mean endpoint +0.148072
  - p_one 0.001598
- AUDUSD <- UDXUSD rel -1 L15/H15
  - N 3,395 / 1,109 days
  - mean endpoint +0.067403
  - p_one 0.046833

Failed:
- GBPUSD L15: positive mean but p=0.053625
- GBPUSD L30: p=0.192687
- USDCHF L15: p=0.389629

Diagnostics:
- EURUSD remains positive after trimming the best 1% and 2% of endpoint events.
- AUDUSD becomes negative after trim-best 1% and 2%, indicating tail sensitivity.
- -60m placebo is also positive for EURUSD and AUDUSD, so the effect appears broader than a razor-thin event timestamp.
- EURUSD validation event counts are highly concentrated in 2018; later years are sparse. This is a diagnostic caveat, not a post-hoc hard fail.

No 2023-2025 or 2026 access.
Human gate required before any locked OOS.


## M04 locked OOS 2023-2025 — human gate approved

Owner approved proceeding after 2018-2022 validation.

Frozen candidates:
- EURUSD <- UDXUSD rel -1 L15/H15
- AUDUSD <- UDXUSD rel -1 L15/H15

No other candidate is eligible.

Locked OOS hard gates per variant:
- >=100 episodes
- >=60 UTC days
- mean endpoint > 0
- one-sided cluster p <= 0.05

Yearly, LOO, trim-best and +/-60m outputs are diagnostics only.

Before OOS:
freeze a 2011-2022 pre-2023 reference and reproduce published validation aggregates.

2026 remains forbidden.

Reference runner:
automation/Freeze-M04Pre2023Reference.ps1

Locked OOS runner:
automation/Run-M5MotionTopologyM04LockedOOS.ps1


### M04 pre-2023 reference frozen — locked OOS ready
Reference run:
GEFM5LREF-20260923-061953

- 1,262,304 rows
- EURUSD/AUDUSD corr_break and corr_break_z vs UDXUSD
- SHA256: c5d64fa7d7e375fa1434a4989317c7b2eff92d0239e7a6c48709bd42d6c90c23
- validation aggregate parity PASS for both locked candidates
- floating-point differences only
- no 2023-2025 access
- no 2026 access

Locked OOS 2023-2025 is cleared to run for:
- EURUSD <- UDXUSD L15/H15
- AUDUSD <- UDXUSD L15/H15


## M04 LOCKED OOS 2023-2025 — FINAL RESULT

Locked OOS candidates tested:
- EURUSD <- UDXUSD L15/H15
- AUDUSD <- UDXUSD L15/H15

Result:
- EURUSD: N=135 / 116 days, mean endpoint -0.045687, p_one=1.000000 -> FAIL
- AUDUSD: N=1,467 / 612 days, mean endpoint +0.069732, p_one=0.103388 -> FAIL

No candidate passes the frozen locked-OOS gate.
M04 lineage is CLOSED.
No rescue, retuning, alternate timing, pair substitution or 2026 access.

Diagnostics:
- EURUSD is unstable across 2023-2025 and its +60m placebo is stronger than the frozen event timestamp.
- AUDUSD remains positive overall and in leave-one-year-out diagnostics, but loses significance and turns negative in 2025; it is also tail-sensitive.
These diagnostics do not override the locked-OOS failure.


## 2026-09-23 — Full mini-edge severity audit completed

Local extraction reviewed:
- 2,149 result files
- 8,654,240 metric observations
- 924 automatic positive-but-rejected flags
- 0 extraction errors
- no research rerun or market-data modification

Main conclusion:
Guardian repeatedly conflated edge existence with standalone production readiness. Several positive and repeatable effects were under-classified because they missed large-edge magnitude, PF, trade-count, robustness or repeated-significance gates. This does not invalidate the many genuine rejects that later turned negative or failed timing/event-unit repairs.

Already confirmed phenomena that remain important:
- V112 AUDUSD H21 120m SHORT — locked OOS 2023-2025 confirmed.
- D032-C1 Bullish Doji Star H1 entry — primary confirmation passed; management remains unresolved.

Highest-interest retrospective mini-edge candidates:
- EA01-XR-RSI-LONG-V1 XAU OOS 2023-2025: n654, +0.0622R at cost 0.10, PF 1.087; killed by PF>=1.10 hurdle while stress mean stayed positive.
- R5E-023 XAU M5: 2024/2025 and stress positive; historical FAIL came only from <100 trades/year.
- D035-E1 causal dual-source response: +6.705 bps executable at +15m, bootstrap lower >0, both 2024/2025 positive; old +15bp standalone hurdle blocked advancement.
- D017 BTC SELL Momentum, D025 ETH RETEST, D025 EURUSD SHORT +2R: recurring positive effects below the old large-edge standard.
- ATLAS-IV A4_02: positive internal holdout/control-relative information at ordinary cost; fails standalone stress/tail gates and is better treated as ensemble/covariate material.
- V111 C1/C5/C7/C8: positive pre-OOS calendar candidates rejected by one or two additional forensic robustness diagnostics; not retroactive OOS passes.

Weak covariate clues only:
- M04 AUDUSD/UDX L15
- M04 GBPUSD/UDX L15
- D030 ETH H4 Engulfing
- D034 XAU abnormal return

Do not revive:
- V102/V103 rates carried-row lineages without a genuinely new event-level design
- V104/V105 CFTC carried-row lineages
- V93 BCO candidate invalidated by corrected time semantics
- F14-V2 after negative 2023-2025 OOS
- R13 low-power/FDR-noise family
- phase IF/IJ candidates with strong 2026 half-year sign flips

Canonical audit:
research/results/GUARDIAN_MINI_EDGE_FULL_AUDIT_2026_09_23.md

Research remains PAUSED. Next step is to freeze a new doctrine separating:
1. edge existence,
2. economic size,
3. ensemble/incremental value,
4. production readiness.
No historical verdict is retroactively changed and no protected-2026 opening is authorized.


## 2026-09-23 — EA01 XAU RSI LONG V2 read-only OOS audit

Existing 2023-2025 OOS ledger verified by exact file hashes and aggregate parity. No strategy rerun and no 2026 access.

EA01-XR-RSI-LONG-V1:
- n=654 non-overlap trades
- cost 0.10 mean +0.06216R/trade, PF 1.08683
- cost 0.20 mean +0.01576R/trade, PF 1.02133
- all three leave-one-year-out means remain positive
- 66.7% of months positive
- month-cluster one-sided 90% lower bound = -0.02196R; bootstrap P(mean<=0)=0.1703
- trimming best 1% flips mean to -0.01816R; trimming best 2% -> -0.07622R
- cumulative max drawdown at cost 0.10 = -34.99R

Doctrine V2 classification:
- existence: POSITIVE_UNCERTAIN
- economic size: MINI_EDGE
- stress: STRESS_POSITIVE
- ensemble: NOT TESTED
- production: NOT PRODUCTION READY

Historical KILL remains preserved. New interpretation: the old PF>=1.10 threshold was too binary for edge-existence taxonomy, but later read-only robustness shows the signal is materially tail-dependent. Keep as an ensemble candidate; do not promote as standalone alpha.


## 2026-09-23 — R5E-023 existing protected 2026 OOS reviewed

A previously completed, preregistered protected Jan-Aug 2026 OOS exists on the backtest-results branch. No rerun was performed.

R5E-023 frozen candidate:
- full OOS n=89
- E1 expectancy +0.3328 engine units, PF 1.0255, net +29.62
- STRESS expectancy -2.0017, PF 0.8598, net -178.16
- Jan-Apr E1 expectancy +6.6509
- May-Aug E1 expectancy -5.8449
- E1 best-trade-removed net -74.47
- day-bootstrap p05 -5.6973
- frozen verdict FAIL

Interpretation:
The earlier 2024/2025 positive robustness was not enough. Protected 2026 shows a strong regime reversal, stress failure and tail dependence. R5E-023 is CLOSED and removed from the active mini-edge shortlist.


## 2026-09-23 — D035-E1 reclassified under Validation Doctrine V2

Existing E1 remains explicitly exploratory same-sample, not confirmation.

Causal correction:
- BTC and ETH frozen D035 shocks both required within <=5m.
- Tradable signal timestamp moved to the later/second shock.
- XLMUSD remained the frozen primary target.

Existing 2024-2025 XLM result:
- causal dual events 973; executable +15m rows 870
- mean executable SHORT +15m +6.705 bps
- median 0.000 bps
- control mean -6.786 bps
- event-control differential +13.490 bps
- raw day-cluster 95% interval [+1.996,+11.549] bps
- differential 95% interval [+8.793,+18.302] bps
- +30m mean +3.697 bps
- 2024 +4.104 bps; 2025 +9.935 bps

V2 interpretation:
- causal discovery credibility SUPPORTED
- fresh existence NOT_YET_FRESHLY_TESTED
- economic size MINI_EDGE_CANDIDATE
- not production ready

A fresh 2026-H1 confirmation protocol is frozen at:
research/campaigns/D035_C1_2026H1_FRESH_CONFIRMATION_PREREG_V2_2026_09_23.md

No D035 2026 result exists on the backtest-results branch. No 2026-H1 data was opened in this step. Human gate remains required before execution.


## 2026-09-23 — D035-C1 2026-H1 fresh confirmation authorized

Owner explicitly approved opening the frozen 2026-H1 sample after reviewing the V2 preregistration.

Frozen scope:
- Binance BTCUSDT + ETHUSDT source shocks only
- both shocks within <=5m
- signal timestamp = later/second shock
- XLMUSD only as target
- SHORT
- +15m primary, +30m diagnostic
- 2026-01-01 through 2026-06-30 only

Added:
- human authorization JSON
- locked Python confirmation engine
- PowerShell runner

Runner hard-limits the CFD input directory to BTCUSD (timezone calibration only) and XLMUSD. It refuses extra target exports and does not access Jul-Dec 2026.

No live deployment is authorized.


## 2026-09-23 — D035 pivoted from FundedNext to FTMO

FundedNext C1 is closed as an execution-environment pivot, not a statistical failure. No FundedNext 2026 target result was produced.

FTMO supports XLMUSD, allowing the exact D035-E1 primary target to remain frozen.

New branch: D035-F1 FTMO transport confirmation.
- source rule unchanged: causal BTC+ETH deleveraging shocks within <=5m
- signal timestamp unchanged: later/second shock
- target unchanged: XLMUSD
- direction unchanged: SHORT
- primary horizon unchanged: +15m
- diagnostic: +30m
- window: 2026-H1 only
- BTCUSD used only for FTMO server->UTC calibration
- observed FTMO BID/ASK spread embedded
- FTMO crypto commission: 0.0325% per side, deducted exactly from entry/exit notional

Scientific caveat: the frozen source engine has already revealed 254 source events in 2026-H1, but no FTMO XLM target outcome has been inspected. F1 is therefore fresh target-outcome/feed transport confirmation.

Artifacts:
- research/campaigns/D035_F1_FTMO_TRANSPORT_CONFIRMATION_2026H1_PREREG_2026_09_23.md
- research/ea/D035_FTMO_CFD_M1_Exporter_v1_00.mq5
- scripts/run_d035_f1_ftmo_transport_2026h1_v1.py
- automation/Run-D035F1FTMO2026H1.ps1


## 2026-09-23 — New recovered candidate: V69 USDCHF Friday LONG

Mini-edge ZIP extraction recovered a genuinely locked-OOS-passing calendar edge:
USDCHF LONG from Friday daily close to next available daily close.

Evidence:
- 2018-2022 independent validation: n259, +5.554 bps gross, 66.8% hit, all 5 years positive, robust after trimming best 1/2% and best 5 events.
- 2023-2025 locked OOS: n155, +4.639 bps gross, 69.68% hit, all 3 years positive, trim1 +4.069, trim2 +3.653, remove-best5 +3.467.
- 2026 untouched.

Doctrine V2: fresh-OOS-confirmed mini-edge candidate, not production ready.

Execution economics remain unresolved because the historical gate used gross close-to-close returns and did not deduct weekend swap/carry, real bid/ask or slippage.


## ChatGPT execution-audit note — 2026-09-23
- Active auxiliary audit runner: `tools/RUN_V69_V112_EXECUTION_AUDIT_v1_02.cmd`.
- Scope: V69 USDCHF Friday LONG and V112 AUDUSD H21 SHORT 120m execution economics on FTMO broker history, capped at 2025-12-31.
- v1.02 fixes PowerShell/Python bootstrap failure from v1.01 and enforces an FTMO account guard.
- No 2026 access, no retuning, no production promotion.
- Next safe action for this audit: run v1.02 with only FTMO MT5 open, then review the resulting ZIP.


## ChatGPT execution-audit parity result — 2026-09-23
- FTMO v1.02 audit completed with 2026 closed, but both V69 and V112 failed source-level gross parity against the original locked-OOS results.
- V69: expected n=155 / +4.639075 bps gross; reconstructed n=156 / -2.033943 bps gross.
- V112: expected n=556 / +1.455235 bps gross; reconstructed n=622 / -0.069812 bps gross.
- Therefore the negative executable numbers from v1.02 are not valid strategy-rejection evidence. The reconstruction/session/data semantics are mismatched.
- Next safe action: exact source/eligibility/timestamp forensic and gross-parity reproduction before any cost verdict.
