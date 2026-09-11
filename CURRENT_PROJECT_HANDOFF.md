# Guardian Research — CURRENT PROJECT HANDOFF

## CURRENT CANONICAL CONTINUITY SNAPSHOT — 2026-09-11 R4/R5

The current R4/R5 state is canonically captured in:

`handoff/2026/09/11/GUARDIAN_R4_R5_CURRENT_HANDOFF_2026_09_11.md`

Commit:
`8d3c054449aacd15f6a4da8efd1f74273d5e6fca`

That dated handoff **supersedes older R4/economic-feasibility top sections below for resume purposes**.

Current essentials:
- R4 causal-capture forensic audit: PASS_INTERPRETABLE; ~99.5% of B->C degradation is ENTRY_DELTA.
- R4 close-to-close family closed.
- R5 causal next-open r2 currently running from queue generation 44.
- Last local progress snapshot: 100000/150000 discovery trials, 4088 discovery candidates, still in 2024 discovery.
- GitHub queue generation 45 has all append jobs disabled so nothing new should auto-start after the current R5 run.
- Do not power off at 150000 discovery alone; wait for the same job's 2025 confirmation to complete.
- On completion: cold-audit R5 semantics/provenance/statistics before any new phase or protected 2026.
- No Codex. No live deployment.

---

## Current scoped handoff — 2026-09-11 economic feasibility protocol

Owner revised the economic scope: FundedNext remains UNRESOLVED / DISABLED and optional; missing historical Bid/Ask permits explicitly conditional feasibility screening, not verified historical fills. The earlier BLOCKED preflight is preserved as historical evidence.

Final owner decisions and implementation now live in `research/protocols/pre_oos_economic_feasibility_screen_v2/` and `research/autonomous/pre_oos_economic_feasibility_v1_00.py`. No artificial hours/day restrictions or +60-second latency. Chronological clean/raw horizon counters, first-available M1 raw reference, 500 unchanged source rules, one-ounce sleeves, exact frozen E1/stress gates. Code cold audit PASS for realistic-backtest selection only; 43 synthetic tests PASS, zero failures; final smoke PASS on eight IDs/1,148 ledger rows with no calibration. Same-author audit, not independent review. Four pinned CSV reads, no protected data. R4 recertification remains mandatory before protected OOS authorization; existing 500 and consolidation untouched.

Implementation published in a322ee9d99dcd456161d64db600b5ad52c9fe2a7. Queue generation 36 adds exactly PRE-OOS-ECONOMIC-FEASIBILITY-SCREEN r1, with every earlier job unchanged. Depends on R4 source r1 and consolidation publication r2 receipts, both PASS; the 32-only integrity audit is not a filter/dependency. Output `D:\MT5_Backtests\Research\Autonomous\pre_oos_economic_feasibility_r1`; progress `D:\MT5_Backtests\Research\Autonomous\progress\PRE-OOS-ECONOMIC-FEASIBILITY-SCREEN-R1.json`. No matching process, output, progress or receipt existed before registration; orchestrator PID 7580 was active. Next safe action: let that orchestrator fetch/launch, then inspect actual status. No manual full process, automatic OOS dependency or live operation. Historical handoff sections below retain their original context; earlier BLOCKED preflight is not erased.

Last updated: 2026-09-08 Europe/Paris
Status: **ACTIVE / D053 REJECTED / D054 UNCONFIRMED-CLOSED / NO CURRENT ALPHA P0 / QUEUE RECONCILED / CHALLENGE LAB PREREGISTERED PIPELINE V1.01 CANONICAL**


## Strategy factory infrastructure handoff — 2026-09-10

STRATEGY-FACTORY-MULTI-ASSET-RANDOM r2 failed on temporary Windows PermissionError in atomic_json (receipt 15:09:50 UTC). Queue generation 31 registers r3 using immutable v1_02 with bounded replace retries only; distinct output/progress R3 paths. Seed 260911, 250000 trials, inputs and all scientific logic are unchanged; no 2026 analysis, retuning or live deployment. Seven regression tests PASS. No r2/r3 process found before registration; existing orchestrator PID 7580 owns launch after push. Preserve r2 artifacts and receipt. Next: observe r3 health/progress; do not start another engine. The existing publisher phase label is preserved by the atomic-only scope.


## 2026-09-11 — Issue #3 economic/execution gate BLOCKED

The 500 published R4 survivors remain the reference population; 32 frozen are secondary only. Cold preflight is BLOCKED before economic implementation: conflicting official FundedNext commission-side descriptions and no positively identified account model; no executable Bid/Ask in the four HCC-derived XAUUSD M1/M5 datasets. M5 spread is from the last M1, not an entry quote. Historical R4 inventory includes two 2026 files and the loader reads before filtering, so the hardcoded untouched flag is not proof of no access; this audit did not open them. Source publication equality is verified after LF normalization; all four pre-2026 dataset hashes match Phase I-B provenance. No new PnL, retuning, engine, job, protected OOS or live changes.

Evidence: `research/results/issue_3_economic_preflight_v1/COLD_AUDIT.md` and `data_provenance_audit.json`. Autonomous queue remains generation 34. Next safe action: resolve exact FundedNext model/commission sides, verify symbol units and execution-feed convention, then complete frozen protocol, validator, tests, smoke and second cold audit before any queue activation. Human time NOT QUANTIFIED; automated audit time is not human time.

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
