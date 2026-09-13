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

## Current P0 — 2026-09-13

R4/R5 XAU promotion paths and R8-R14 prior research families are closed under their frozen hypotheses.

R14 is closed as a literature-replication benchmark: the published Bitcoin negative-shock effect was strongly recovered historically (48/48 positive, 47/48 BH-FDR replication pass), but 0 candidates survived independent BH-FDR confirmation on 2021H2-2024. Protected 2026 remained unopened. Do not rescue R14.

The active family is **R15 XAUUSD GLD intraday-momentum literature near-replication**.

External source:
Xu, Bouri, Saeed & Wen (2020), Resources Policy 69, 101830, DOI 10.1016/j.resourpol.2020.101830.

Frozen published hypothesis:
- GLD fifth half-hour return r5 predicts final half-hour r13 positively;
- published beta 0.0436, Newey-West t=3.03, R-squared 0.49%;
- Guardian maps r5 to 11:30->12:00 ET and r13 to 15:30->16:00 ET using DST-aware America/New_York timestamps.

Committed preregistration:
`research/autonomous/R15_XAUUSD_GLD_INTRADAY_MOMENTUM_PREREGISTRATION_2026_09_13.md`

Queue generation 76:
- `R15-XAUUSD-GLD-INTRADAY-MOMENTUM-PREFLIGHT r1`
- `R15-XAUUSD-GLD-INTRADAY-MOMENTUM r1`

Stage 1 is the available 2017-01-01 through 2019-05-30 overlap with the paper sample. Stage 2 is independent 2019-05-31 through 2024-12-31 confirmation. Costs enter only after confirmation; 2025 is pre-OOS; 2026 is forbidden.

If R15 is running or waiting normally, do not interfere. If Stage 1 fails, audit the XAUUSD-vs-GLD mapping and implementation; do not substitute another half-hour predictor.

## Hard operating rules

- Never deploy live automatically.
- Never open or inspect protected 2026 unless the mandate's protected-OOS preregistration conditions are satisfied.
- Distinguish scientific FAIL from infrastructure FAIL.
- Never restart a healthy job or create a duplicate run.
- Jobs are immutable by `(id, revision)` once run.
- After infrastructure failure, preserve the scientific protocol and revision only the infrastructure repair.
- Before every expensive phase: cold methodology/code audit → deterministic tests → micro/canary only if justified → expensive run only if justified.
- Before launch, answer: **If this job PASSes, does it actually answer the question required to advance?**
- Never claim a job is running only because it is queued. Require process/health/progress/published evidence.
- Prefer GitHub + the local autonomous orchestrator for this workflow.
- Codex is out of circuit unless the mandate conditions are met.
- Preserve historical artifacts; do not overwrite failed receipts or prior scientific evidence.

## Scientific rules

- For R15, published-overlap near-replication is 2017-01-01 through 2019-05-30, independent confirmation is 2019-05-31 through 2024-12-31, and 2025 is the pre-OOS temporal gate.
- Each survivor set must be frozen before the next period is computed.
- 2026 remains protected final OOS and may not be used for discovery or rescue.
- Do not same-sample rescue a failed family.
- Do not promote gross-return survivors directly to production.
- Survivors still require reject-only robustness, realistic execution/cost feasibility where not already built in, red-team review and untouched OOS before promotion.

## Communication / control

The owner prefers direct answers and does not want to act as a log courier.

If the owner says `published`, `fini`, `résultat ?`, `on en est où ?`, inspect GitHub first. Do not ask the owner to paste logs.

If a mistake is found, state it, classify its consequence, and correct the workflow rather than defending it.
