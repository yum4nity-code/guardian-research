# Phenomenon Discovery - Phase D verdict and Phase E-A pivot

Date: 2026-09-08

## Phase D verdict

Phase D completed and published on `backtest-results`.

- exact three-clause quintile rules: 35,750
- directional outcomes tested: 2
- total universe tests: 71,500
- 2024 frozen shortlist: 100 candidates
- 2025 screen passes: 0
- distinct passes: 0
- 2026: untouched

Verdict: **REJECT the exact three-clause static-state directional family.**

Do not add a fourth static clause or tune the failed 2024 shortlist on 2025. The result is consistent with severe instability/overfit in static directional state combinations.

Phase C remains useful as a separate result: robust low-movement/no-trade regime filters existed, but no robust directional state survived.

## Scientific pivot

The next research step changes the representation rather than increasing rule complexity.

Phase E focuses on:

1. derivative context not present in the Phase A-D matrix:
   - Bybit mark price;
   - index price;
   - premium index;
   - mark-index basis;
   - already-settled funding only;
2. temporal transitions rather than static cells:
   - regime changes;
   - OI transitions;
   - premium/basis reversals;
   - funding-state changes;
   - interactions between transitions.

This is not authorization to open 2026.

## Phase E-A gate

Phase E-A is dataset construction only. It downloads 2024-2025 Bybit derivative context, joins it causally to the existing Phase A feature matrix, checks exact 5m continuity and verifies that no funding record used is later than `feature_available_at_ms`.

No Phase E rule search is allowed until the Phase E-A integrity report is PASS.

Canonical launcher:

`research/phenomenon_discovery/START_PHASE_EA_DERIVATIVE_CONTEXT_V1_00.ps1`

Expected compact publication target:

`backtest-results/phenomenon-discovery/phase-ea-derivative-context/`

Raw derivative CSVs remain local; only manifests and integrity evidence are published.
