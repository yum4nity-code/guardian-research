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
