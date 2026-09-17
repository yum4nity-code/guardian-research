# Edge Atlas EA01 — handoff d’exécution

Date: 2026-09-17
Base: 4391384dea505be63f158e4cee3c006d7345dba0
Branch: research/edge-atlas-2026-09-17
Status: WAITING_CODEX
Execution: NOT LAUNCHED

## Evidence

- Local admission preflight: PASS, 14/14 synthetic tests.
- No historical market data was read by the preflight.
- No 2026 worker is active; the live collector may write its separate 2026 archive, which is excluded.
- Effective autonomous queue generation 114 is empty.
- EA01 has a fail-closed runner and safety tests.
- The runner intentionally refuses execution until the local Edge Atlas adapter is supplied.

## Required local action

Codex must inspect the local orchestrator implementation and register the runner as a supported research job type without altering production or reusing an old campaign runner. The adapter must:

1. resolve the admitted XAU manifest;
2. enforce 2017-01-01 through 2022-12-31 discovery only;
3. reject 2026 at file and row level;
4. execute no more than five minutes;
5. write status before starting;
6. persist raw events and metrics atomically;
7. publish a receipt with input hashes and protected_2026_opened=false;
8. stop closed and report INFRASTRUCTURE_ERROR if the adapter is not available.

Do not activate queue generation 115 until the adapter passes cold review and synthetic tests. Do not use the current Phase B queue entry, R33, R34 or R35.

## Exact files

- Runner: research/campaigns/EDGE_ATLAS_2026_09_17/ea01_cheap_fail_v1.py
- Tests: research/campaigns/EDGE_ATLAS_2026_09_17/tests/test_ea01_cheap_fail_v1.py
- Proposal: research/autonomous/RESEARCH_QUEUE_APPEND_EDGE_ATLAS_115_PROPOSAL.json
- Manifest: research/campaigns/EDGE_ATLAS_2026_09_17/ADMITTED_DATA_MANIFEST.json
