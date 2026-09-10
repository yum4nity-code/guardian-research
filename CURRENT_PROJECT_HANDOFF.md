# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-08 Europe/Paris
Status: **ACTIVE / D053 REJECTED / D054 UNCONFIRMED-CLOSED / NO CURRENT ALPHA P0 / QUEUE RECONCILED / CHALLENGE LAB PREREGISTERED PIPELINE V1.01 CANONICAL**


## Strategy factory infrastructure handoff — 2026-09-10

STRATEGY-FACTORY-MULTI-ASSET-RANDOM r2 failed on temporary Windows PermissionError in atomic_json (receipt 15:09:50 UTC). Queue generation 31 registers r3 using immutable v1_02 with bounded replace retries only; distinct output/progress R3 paths. Seed 260911, 250000 trials, inputs and all scientific logic are unchanged; no 2026 analysis, retuning or live deployment. Seven regression tests PASS. No r2/r3 process found before registration; existing orchestrator PID 7580 owns launch after push. Preserve r2 artifacts and receipt. Next: observe r3 health/progress; do not start another engine. The existing publisher phase label is preserved by the atomic-only scope.

## Canonical resume

Read first:
1. this file;
2. `CURRENT_QUEUE.json`;
3. latest `backtest-results` branch evidence for the newest Dxxx campaign;
4. `START_HERE_NEXT_AI.md` and `GUARDIAN_MASTER_MANDATE.md`;
5. `docs/RESEARCH_PROTOCOL.md`.

`CURRENT_QUEUE.json` was reconciled on 2026-09-08. Its stale D036 active-primary state was removed. Real/newer run evidence still wins if a future interruption causes metadata lag again.

## Current alpha state

- D053 formal verdict: `D053_REJECT_V0`.
- D054 latest confirmation state: `D054_UNCONFIRMED_CLOSE`.
- No alpha P0 is currently promoted.
- Do not same-sample rescue D053/D054 or reopen other rejected families merely because historical files remain.
- Next alpha action: select and preregister a genuinely independent family.

## Challenge Probability Lab — core engine v1.00

Purpose:

> Estimate the probability that a strategy/portfolio reaches the challenge target before a daily or overall drawdown breach, and select risk for **passing the challenge** rather than maximizing terminal profit.

Core files:
- `research/challenge_probability_lab/challenge_probability_lab_v1_00.py`
- `research/challenge_probability_lab/test_challenge_probability_lab_v1_00.py`
- `research/challenge_probability_lab/guardian_reference_profile_v1_00.json`
- `research/challenge_probability_lab/README.md`
- `research/results/CHALLENGE_PROBABILITY_LAB_V1_00_IMPLEMENTATION_REPORT_2026_09_07.md`

Core validation already completed:
- Python compile PASS;
- 8/8 engine unit tests PASS;
- real Guardian CSV-schema smoke PASS.

Frozen default risk grid:
- 0.10%
- 0.15%
- 0.20%
- 0.25%
- 0.33%
- 0.50%

per trade.

## Challenge trade export contract v1

Canonical file:
`research/challenge_probability_lab/CHALLENGE_TRADE_EXPORT_CONTRACT_V1.md`

Future Lab-ready confirmation/OOS trades must contain at least:
- `run_stage`
- `symbol`
- `entry_time`
- `exit_time`
- `net_r`
- `challenge_day`
- `adverse_r`

`challenge_day` must use the actual prop-firm daily-loss reset rule. `adverse_r` is signed worst adverse excursion in R and must be `<= 0`.

Run metadata must preserve day basis, R denominator, cost basis, floating-equity availability and the export-contract identifier.

## Lower-level automatic gate v1.00

Files:
- `research/challenge_probability_lab/post_validation_challenge_gate_v1_00.py`
- `research/challenge_probability_lab/test_post_validation_challenge_gate_v1_00.py`

Behavior:
- `challenge_lab_eligible=false` -> skip;
- malformed/missing eligibility -> fail closed;
- canonical future export without `challenge_day` -> fail closed;
- eligible canonical export -> run Lab and write `challenge_gate_manifest.json` plus JSON/CSV/Markdown results;
- legacy export requires explicit `--allow-legacy-atomic-export` and remains lower fidelity.

Gate validation already completed: 4/4 gate tests PASS in addition to the 8/8 core tests.

## NEW canonical bridge — preregistered post-validation pipeline v1.01

Canonical entrypoint:
`research/challenge_probability_lab/post_validation_pipeline_v1_01.py`

Supporting files:
- `research/challenge_probability_lab/test_post_validation_pipeline_v1_01.py`
- `research/challenge_probability_lab/challenge_pipeline_policy_template_v1_00.json`
- compatibility predecessor: `post_validation_pipeline_v1_00.py`

### Why v1.01 exists

Historical scorers must stay frozen. Do **not** modify D037 or another completed scorer merely to inject Challenge Lab fields after its result is known.

Also, accepting `--accepted-verdict CONFIRM` or choosing seed/risk grid after observing the result leaves an avoidable ex-post degree of freedom.

v1.01 closes both problems by requiring a **pre-registered policy JSON** committed before the protected result is opened.

The policy freezes:
- exact scorer verdict(s) allowed to advance;
- exact expected OOS/confirmation stage;
- scorer verdict/stage/gates keys;
- whether missing gates are permitted for an explicitly legacy scorer;
- Monte-Carlo paths per risk;
- deterministic seed;
- complete risk grid;
- SHA256 of the frozen challenge profile.

Placeholder policy values are rejected at runtime.

### v1.01 flow

1. read untouched frozen scorer JSON;
2. read preregistered policy JSON;
3. verify policy validity;
4. verify frozen challenge profile SHA256;
5. exact-match scorer verdict + expected stage;
6. require every persisted scorer gate to be literally `true` unless missing gates were preregistered as a legacy exception;
7. write `challenge_lab_eligibility.json` with scorer/policy/profile SHA256 provenance;
8. call `post_validation_challenge_gate_v1_00.py`;
9. rejected/unconfirmed -> skip, no risk optimization;
10. eligible -> run frozen Challenge Lab policy automatically.

### v1.01 validation completed 2026-09-08

Local policy checks: **6/6 PASS** covering:
- valid `CONFIRM` + all gates true;
- `UNCONFIRMED` blocked;
- wrong stage blocked;
- false gate blocked;
- placeholder policy rejected;
- invalid/empty risk grid rejected.

Integration checks:
- canonical CONFIRM path -> PASS;
- policy values correctly propagated to lower-level gate;
- six risk values propagated;
- 20,000 paths and deterministic seed propagated;
- challenge profile byte tampering -> **SHA256 mismatch / fail closed PASS**.

This means the Lab is now not merely implemented; it has a scientifically safer bridge from frozen scorer to challenge-risk decision.

## DD exactness boundary

Current fidelity levels:
- `ATOMIC_CLOSED_EQUITY`
- `ATOMIC_PLUS_INDIVIDUAL_ADVERSE_R`

`adverse_r` improves intratrade DD detection but cannot reconstruct simultaneous adverse excursions of overlapping positions.

Exact prop-firm floating DD still requires synchronized portfolio mark-to-market/equity snapshots. Never label current atomic probabilities as exact floating-equity compliance probabilities.

## Queue state

`CURRENT_QUEUE.json` now has:
- `active_primary: null`;
- P0 READY: `NEXT-INDEPENDENT-ALPHA-FAMILY`;
- Challenge Probability Lab Pipeline v1.01 marked `VALIDATED` infrastructure;
- D036 / D053 / D054 represented as closed/rejected evidence rather than active work.

## Guardian production / compliance separation

Guardian Core v12.01 remains the compile-validated pure infrastructure baseline. Challenge Lab work did **not** modify `production/guardian/` or live trading semantics.

FundedNext request/retry hyperactivity remains separate compliance/runtime work. FundedNext AUTO stays off until that issue is bounded.

## Next safe actions

1. Select/preregister the next genuinely independent alpha family.
2. From its first harness design, include canonical `challenge_day` + signed `adverse_r` in the trade export.
3. Before opening protected confirmation/OOS evidence, instantiate and commit a campaign-specific policy from `challenge_pipeline_policy_template_v1_00.json`.
4. Keep the scorer itself frozen; after scoring, run `post_validation_pipeline_v1_01.py` automatically.
5. If alpha/OOS fails, the Lab must skip. Do not use sizing to rescue it.
6. If alpha/OOS succeeds, the frozen policy determines the six-risk Challenge simulation and pass-optimal risk.
7. Later v2: add synchronized portfolio floating-equity/mark-to-market snapshots for exact concurrent DD reconstruction.
8. Keep Guardian Core v12.01 stable unless a separate production change is explicitly justified and validated.
