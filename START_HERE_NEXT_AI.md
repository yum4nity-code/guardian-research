# START HERE — NEXT GUARDIAN AI

You are taking over Guardian.

## Read in this order

1. `CURRENT_PROJECT_HANDOFF.md`
2. `GUARDIAN_MASTER_MANDATE.md`
3. `docs/RESEARCH_PROTOCOL.md`
4. `research/autonomous/AUTONOMOUS_RESEARCH_MANDATE.md`
5. `research/autonomous/RESEARCH_QUEUE.json`
6. `research/autonomous/RESEARCH_QUEUE_APPEND.json`
7. latest relevant evidence on the `backtest-results` branch, including Phase I-B, Phase I-C and autonomous-research-orchestrator

Do not infer current state from older D0xx handoffs or Codex exchanges when `CURRENT_PROJECT_HANDOFF.md` says otherwise.

## Current P0 — 2026-09-12

R4 and R5 are closed for tradable-alpha promotion.

R5 causal-next-open discovery/confirmation produced 96 frozen gross survivors, but the frozen pre-OOS economic robustness result is **scientific FAIL: 0/96** under inherited E1/STRESS costs using first-available execution. The orchestrator's PASS receipt only means executor exit 0; it does not reverse the scientific FAIL. Protected 2026 remained unopened.

The active research family is now **R6 XAU low-turnover structured rolling-range breakout**, a genuinely independent family rather than an R5 retune/rescue. Its committed preregistration is:
`research/autonomous/R6_XAU_LOW_TURNOVER_BREAKOUT_PREREGISTRATION_2026_09_12.md`

Queue append generation 52 contains:
- `R6-XAU-LOW-TURNOVER-BREAKOUT-PREFLIGHT r1`: cold methodology/code audit + deterministic no-market-data tests.
- `R6-XAU-LOW-TURNOVER-BREAKOUT r1`: executes only after preflight PASS, uses 2024 discovery frozen before isolated 2025 confirmation, and forbids 2026.

If either R6 job is running or waiting normally, do not interfere or notify the owner.

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
- Codex is out of circuit unless the operator explicitly re-authorizes it.
- Preserve historical artifacts; do not overwrite failed receipts or prior scientific evidence.

## Scientific rules

- 2024 is discovery/development for the active R6 family.
- The entire 2024 R6 discovery set must be frozen before any 2025 confirmation computation.
- 2025 is internal confirmation.
- 2026 remains protected final OOS.
- Do not same-sample rescue a failed family.
- Do not promote gross-return survivors directly to production.
- Survivors still require reject-only robustness, realistic execution/cost feasibility where not already built in, red-team review and untouched OOS before promotion.

## Communication / control

The owner prefers direct answers and does not want to act as a log courier.

If the owner says `published`, `fini`, `résultat ?`, `on en est où ?`, inspect GitHub first. Do not ask the owner to paste logs.

If a mistake is found, state it, classify its consequence, and correct the workflow rather than defending it.