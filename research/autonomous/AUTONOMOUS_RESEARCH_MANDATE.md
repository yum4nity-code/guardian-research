# Guardian Autonomous Research Mandate v1.00

Date: 2026-09-08
Status: canonical for unattended alpha research

## Objective

Run research continuously without using the owner as a relay. The objective is **not** to keep changing rules until something passes. The objective is to discover a reproducible market phenomenon, reject weak families quickly, and promote only evidence that survives frozen gates.

## Architecture

1. ChatGPT is the scientific supervisor. It reads GitHub evidence, designs/preregisters the next experiment, writes code, and updates `research/autonomous/RESEARCH_QUEUE.json`.
2. The local Guardian Research Orchestrator polls `main`, executes only frozen queued jobs, records receipts, and publishes compact health/results.
3. Python is the default research/backtest engine. MT5 is reserved for broker/server data acquisition and later execution-fidelity validation.
4. `backtest-results` is the evidence bus. The owner is never asked to paste console logs when the system can publish them itself.

## Scientific invariants

- Market state/event -> future distribution -> robustness -> only then trading rule.
- 2024 = discovery and 2025 = internal confirmation for the current XAU branch.
- **2026 remains sealed.** `human_approved_2026` must remain false until the owner explicitly approves opening final OOS after a genuinely frozen candidate exists.
- No same-sample rescue of a failed family.
- No arbitrary threshold tweaking after results are known.
- No repeated named-strategy churn.
- Multiple-testing control is mandatory when many hypotheses are screened.
- Costs/execution and Challenge Probability Lab are downstream; sizing may never rescue failed alpha.
- Phase C BTC/ETH low-movement/no-trade output remains preserved; BTC/ETH directional 5m->1h search remains closed.

## Current branch

- Phase I-A: PASS. Historical USD high-impact news mask, XAUUSD conservative +/-5 minutes, FundedNext-Server 2, 2026 untouched.
- Phase I-B: XAUUSD M1/M5 2024-2025 data gate, same canonical MT5/server/path as I-A, news mask applied before research use.
- After I-B PASS: begin XAU phenomenon-first discovery. Do not turn the first statistical survivor directly into an EA.

## Autonomous decision loop

At every terminal result:

1. verify integrity/provenance first;
2. if infrastructure/data failed, repair the infrastructure without changing the scientific hypothesis;
3. if the scientific family failed its frozen gates, close it;
4. if evidence is suggestive but not confirmatory, run only a preregistered robustness/confirmation step logically implied before seeing the result;
5. if a family is exhausted, move to a genuinely different information representation, event type, horizon, or market mechanism;
6. if a candidate survives internal confirmation, freeze exact rules and only then prepare protected final OOS;
7. opening 2026 requires explicit owner approval and a committed preregistration/policy file first.

## Timeout/watchdog policy

Long runtime alone is not failure.

For a job with elapsed time `t`, observed progress fraction `f`, successful historical comparable durations, and optional expected duration:

- ETA from progress = `t / f` when `0 < f < 1`.
- historical baseline = P95 of successful jobs with the same `class_key`.
- hard limit = max(`min_seconds`, `2.5 * expected`, `2.5 * ETA`, `3.0 * historical_P95`).
- a job with a heartbeat/progress file is killed only when **both** elapsed time exceeds the hard limit **and** the heartbeat is stale.
- a legacy job without heartbeat may be killed after the adaptive hard limit.

Every new long-running research engine should write progress JSON containing at least `completed`, `total`, and an updated timestamp/mtime.

## Codex budget

Codex is not the orchestrator and not the scientific decision maker.

Default: **do not call Codex**.

Codex may be requested only when all are true:

1. a real code/compile/refactor blocker exists;
2. at least two deterministic repair attempts have failed, or the task is a genuinely large new MQL5 implementation where second-agent review materially reduces risk;
3. the request is tightly scoped to code, not hypothesis selection;
4. no more than one Codex assistance request is made in 24 hours unless the owner explicitly overrides the budget.

The v1.00 local orchestrator deliberately treats `codex_assist` as fail-closed. A future explicit adapter may be enabled only after its exact CLI/API contract is validated.

## Queue authority

`research/autonomous/RESEARCH_QUEUE.json` is the machine-execution queue. Jobs are immutable by `(id, revision)` once run. Scientific changes require a new revision or new job id.

The local executor never invents hypotheses. ChatGPT changes the queue after reading published evidence. This separation prevents a deterministic worker from silently data-mining.

## Owner notification policy

Do not notify the owner for normal PASS/FAIL research churn. Notify only when:

- a candidate survives a meaningful confirmation gate;
- explicit permission is needed to open protected 2026;
- an unrecoverable local/MT5/account condition blocks all progress;
- a production/live-trading change would be required.
