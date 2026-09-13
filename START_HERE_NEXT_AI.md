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

R4/R5 XAU promotion paths and R8-R12 BTC/ETH families are closed under their frozen hypotheses.

R12 BTC/ETH volatility-compression channel breakout completed normally but was a clean **scientific FAIL**: 4/72 definitions survived frozen 2018-2022 discovery and 0 survived untouched 2023-2024 confirmation; exact pre-2026 input hashes matched and protected 2026 remained unopened. The orchestrator PASS receipt means executor exit 0 only and does not reverse that scientific FAIL.

The active research family is now **R13 BTC/ETH failed-breakout rejection**, a genuinely independent reversal family rather than a rescue of R12. Its committed preregistration is:
`research/autonomous/R13_BTC_ETH_FAILED_BREAKOUT_REJECTION_PREREGISTRATION_2026_09_13.md`

Queue append generation 74 contains:
- `R13-BTC-ETH-FAILED-BREAKOUT-REJECTION-PREFLIGHT r1`: deterministic cold methodology/code tests.
- `R13-BTC-ETH-FAILED-BREAKOUT-REJECTION r1`: executes only after preflight PASS, uses 2018-2022 discovery frozen before isolated 2023-2024 confirmation, then a frozen 2025 pre-OOS gate, and forbids 2026.

If either R13 job is running or waiting normally, do not interfere or notify the owner.

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

- For R13, discovery is 2018-2022, confirmation is 2023-2024, and 2025 is the pre-OOS temporal gate.
- Each survivor set must be frozen before the next period is computed.
- 2026 remains protected final OOS and may not be used for discovery or rescue.
- Do not same-sample rescue a failed family.
- Do not promote gross-return survivors directly to production.
- Survivors still require reject-only robustness, realistic execution/cost feasibility where not already built in, red-team review and untouched OOS before promotion.

## Communication / control

The owner prefers direct answers and does not want to act as a log courier.

If the owner says `published`, `fini`, `résultat ?`, `on en est où ?`, inspect GitHub first. Do not ask the owner to paste logs.

If a mistake is found, state it, classify its consequence, and correct the workflow rather than defending it.
