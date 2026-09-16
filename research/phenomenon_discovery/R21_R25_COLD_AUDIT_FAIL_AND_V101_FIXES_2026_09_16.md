# R21-R25 independent cold-audit FAIL and v1.01 corrective record — 2026-09-16

## Audit provenance

Independent reviewer verdict on commit \`f0213f86dc74a2e2955224143d2b1405b969efa9\`: **FAIL**.

No historical backtest was authorized from that commit. Generation 81 remains historical failed-audit evidence and is archived.

## Corrective versioning

The failed v1.00 files are preserved for audit provenance.
Corrections are implemented in new v1.01 files:
- \`xau_edge_discovery_r21_r25_v1_01.py\`
- \`test_xau_edge_discovery_r21_r25_v1_01.py\`
- \`build_xau_m5_discovery_slice_v1_01.py\`
- \`test_build_xau_m5_discovery_slice_v1_01.py\`

No real historical discovery has been run.

## HIGH findings addressed

1. **Syntax invalid in v1.00**
   - v1.01 is syntactically valid locally under Python bytecode compilation.
   - The malformed output newline in v1.00 is not reused.

2. **Incorrect CR1 finite-sample correction**
   - v1.01 uses the intercept-only one-way day-cluster CR1 factor \`G/(G-1)\`.
   - The erroneous extra \`(N-1)/N\` multiplier is removed.
   - A numeric regression test fixes the expected formula.

3. **2025 physical lock not guaranteed**
   - v1.01 engine is discovery-only and fails on every row after 2019-06-30.
   - v1.01 builder has no arbitrary stage/date mode.
   - Payload bytes are touched only after an explicit \`2004-11-08 <= date <= 2019-06-30\` gate.
   - A regression test includes an invalid 2025 payload and proves its decode function is never called.

4. **Confirmation accessible / R22 baseline not frozen**
   - Confirmation is removed from v1.01 entirely.
   - No \`--stage confirmation\` path exists.
   - A later separately audited version is required after discovery survivors and R22 baseline/freeze semantics are explicitly recorded.

5. **Queue window schema mismatch**
   - Generation 82 uses \`end_exclusive: 2019-07-01T00:00:00Z\`.
   - No \`end_inclusive\` field is used.

6. **Effective queue not globally closed**
   - Legacy generation 16 is archived.
   - Canonical \`RESEARCH_QUEUE.json\` is reset to generation 82, \`human_approved_2026=false\`, with zero base jobs.
   - Generation-82 append contains only four R21-R25 staging jobs, all \`enabled=false\`.
   - A dedicated test loads the queue through the real orchestrator loader/validator and asserts zero enabled jobs.

## MEDIUM findings addressed

- R22 zero standard deviation is retained as valid maximum compression rather than silently dropped.
- Forward returns require every intervening M5 interval to equal exactly 300 seconds.
- R24 last eligible bar timestamp is 09:55 New York, whose close is 10:00.
- R24 requires every M5 bar from 08:35 through the breakout event; a gap before breakout invalidates the day.
- R22 primary inference replaces fixed-baseline event CR1 with a delete-one-UTC-day jackknife of the **complete estimator**, recomputing event mean and same-clock baseline after each deleted day.
- R25 output now reports descriptive fill counts, valid denominators and probabilities.

## Gate state

- Local Python bytecode compilation of v1.01 engine/builder/tests: PASS.
- Local synthetic audit-regression tests for v1.01 engine: PASS.
- Local synthetic discovery-builder tests: PASS.
- Effective generation 82: intended fail-closed; repository test added.
- Independent cold re-audit of the new commit: **PENDING**.
- Historical discovery execution: **NOT AUTHORIZED**.
- 2025: **NOT OPENED / NOT AUTHORIZED**.
- 2026+: **NOT OPENED / NOT AUTHORIZED**.
- Live/real deployment: **NOT AUTHORIZED**.
