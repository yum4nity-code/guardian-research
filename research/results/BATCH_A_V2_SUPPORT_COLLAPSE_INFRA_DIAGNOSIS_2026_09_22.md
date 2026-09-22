# Batch A V2 support-collapse infrastructure diagnosis

Date: 2026-09-22
Affected run: GEFBA2-20260922-183722
Scientific interpretation: NONE

## Evidence

The read-only object-support audit showed healthy underlying objects:
- rolling-beta support: ~32k-35k hours across 2013-2016;
- NSX/SPX residual-z: 18,520 finite rows, 1,060 cooldown events;
- XAU/XAG residual-z: 22,433 finite rows, 1,595 cooldown events;
- USD breadth-z: 22,290 finite rows, 1,343 cooldown events.

But forward target support after alignment was only:
- ~417 observations at 60m;
- ~205 at 120m;
- ~105 at 240m.

That 1/60, 1/120, 1/240 pattern identifies a datetime-unit bug in aligned_mask().
The code assumed times.view("int64") was nanoseconds. The runtime's pandas datetime integer resolution is not guaranteed to be ns.

Fix:
explicit conversion to numpy datetime64[m] before modulo.

## Second infrastructure defect

Rate support was only 176 distinct days for REAL 5Y/10Y and 144 for REAL 30Y.

V2 as-of source retained rows with NaN z. merge_asof could therefore select a later NaN row and blank a previously valid causal state.

V102/V103 semantics drop NaN feature rows before as-of.

Fix:
dropna(subset=["AVAILABLE_AT","z"]) before rate as-of.

## Scientific invariants

No economic hypothesis, variant, threshold, window, horizon, gate, BH rule or holdout rule changed.

2017 remained unopened in the failed V2 run.
2018+ remained unopened.
2023-2025 remained unopened.
2026 remained unopened.

Engine after both infrastructure fixes:
BATCH-A-V2-DISCOVERY-1.2

Before rerunning alpha tests, rerun the read-only object-support diagnostic and confirm target/rate support is restored.
