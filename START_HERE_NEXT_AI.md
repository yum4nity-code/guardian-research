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

R4/R5 XAU promotion paths and R8-R13 prior BTC/ETH families are closed under their frozen hypotheses.

R13 v1.01 is the canonical R13 result: **clean scientific FAIL** under the corrected staged architecture. 72 definitions were tested; 66 met minimum sample size, 24 were gross-positive, 34 gross-stable, and 0 passed BH-FDR discovery. Infrastructure was healthy, exact pre-2026 hashes matched, and protected 2026 remained unopened. R13 v1.00 remains historical methodology-nonconforming evidence only.

The active research family is now **R14 Bitcoin hourly negative-shock literature replication**. It is the first implementation of the mandated literature-first branch rather than another blind parameter sweep.

External benchmark:
Miralles-Quirós & Miralles-Quirós (2022), “Intraday Bitcoin price shocks: when bad news is good news”, DOI 10.1080/15140326.2022.2151253.

Committed preregistration:
`research/autonomous/R14_BITCOIN_HOURLY_NEGATIVE_SHOCK_REPLICATION_PREREGISTRATION_2026_09_13.md`

Queue append generation 75 contains:
- `R14-BITCOIN-HOURLY-NEGATIVE-SHOCK-REPLICATION-PREFLIGHT r1`: deterministic cold methodology/code tests.
- `R14-BITCOIN-HOURLY-NEGATIVE-SHOCK-REPLICATION r1`: closest-feasible published-effect replication on 2017-08-17 through 2021-06-30, frozen independent 2021H2-2024 confirmation, downstream causal/economic translation, frozen 2025 pre-OOS, and protected 2026 forbidden.

The published grid is fixed at 48 negative-shock cells: 0.5/1/1.5/2.5/3.5/5% hourly log-return filters x 1/2/3/4/5/6/12/24h horizons. Do not add or remove thresholds after results.

If R14 is running or waiting normally, do not interfere or notify the owner. If the published effect fails to reproduce, audit implementation and the Binance-vs-Kraken/data-window difference before interpreting the result as an absent anomaly.

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

- For R14, published-effect near-replication is 2017-08-17 through 2021-06-30, independent confirmation is 2021-07-01 through 2024-12-31, and 2025 is the pre-OOS temporal gate.
- Each survivor set must be frozen before the next period is computed.
- 2026 remains protected final OOS and may not be used for discovery or rescue.
- Do not same-sample rescue a failed family.
- Do not promote gross-return survivors directly to production.
- Survivors still require reject-only robustness, realistic execution/cost feasibility where not already built in, red-team review and untouched OOS before promotion.

## Communication / control

The owner prefers direct answers and does not want to act as a log courier.

If the owner says `published`, `fini`, `résultat ?`, `on en est où ?`, inspect GitHub first. Do not ask the owner to paste logs.

If a mistake is found, state it, classify its consequence, and correct the workflow rather than defending it.
