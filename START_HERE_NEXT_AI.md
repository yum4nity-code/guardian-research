# START HERE — NEXT GUARDIAN AI

You are taking over Guardian.

## Read in this order

1. `CURRENT_PROJECT_HANDOFF.md`
2. `handoff/2026/09/11/GUARDIAN_R4_R5_CURRENT_HANDOFF_2026_09_11.md`
3. `GUARDIAN_MASTER_MANDATE.md`
4. `docs/RESEARCH_PROTOCOL.md`
5. `research/autonomous/AUTONOMOUS_RESEARCH_MANDATE.md`
6. `research/autonomous/RESEARCH_QUEUE.json`
7. `research/autonomous/RESEARCH_QUEUE_APPEND.json`
8. latest relevant evidence on the `backtest-results` branch

Do not infer current state from older D0xx handoffs or Codex exchanges when the current handoff says otherwise.

## Current P0 — 2026-09-11

The active research campaign is **R5 causal next-open XAU discovery/confirmation**.

Current known state:
- R4 close-to-close family is closed after a causal-capture forensic audit.
- The forensic result found that about 99.5% of R4 B→C degradation came from the entry transition to the first executable reference.
- R5 r2 is designed to discover edge using a causal next-open target instead.
- Queue generation 46 has R5 preflight r2 and R5 r2 enabled again at the operator's request. The already-running R5 r2 child should be allowed to finish normally. This does not authorize a new downstream research phase after R5.
- A R5 PASS is not an EA and does not authorize 2026 OOS.

The exact current state and mandatory post-run audit are in the dated R4/R5 handoff above.

## Hard operating rules

- Never deploy live automatically.
- Never open protected 2026 OOS without explicit owner approval plus committed preregistration.
- Distinguish scientific FAIL from infrastructure FAIL.
- Never restart a healthy job or create a duplicate run.
- Jobs are immutable by `(id, revision)` once run.
- After infrastructure failure, preserve the scientific protocol and revision only the infrastructure repair.
- Before every expensive phase: cold methodology/code audit → deterministic tests → micro/canary only if justified → expensive run only if justified.
- Before launch, answer: **If this job PASSes, does it actually answer the question required to advance?**
- Never claim a job is running only because it is queued. Require process/health/progress/published evidence.
- Prefer GitHub + the local autonomous orchestrator for this workflow.
- Codex is currently out of circuit unless the operator explicitly re-authorizes it.
- Preserve historical artifacts; do not overwrite failed receipts or prior scientific evidence.

## Scientific rules

- 2024 is discovery/development.
- 2025 is internal confirmation for the current R5 family.
- 2026 remains protected final OOS.
- Do not same-sample rescue a failed family.
- Do not promote gross-return survivors directly to production.
- Survivors still require reject-only robustness, realistic cost/execution feasibility, red-team review and untouched OOS before promotion.

## Communication / control

The owner prefers direct answers and does not want to act as a log courier.

If the owner says `published`, `fini`, `résultat ?`, `on en est où ?`, inspect GitHub first. If local-only progress is required, ask for the exact one-line command needed and nothing more.

If a mistake is found, state it, classify its consequence, and correct the workflow rather than defending it.
