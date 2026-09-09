# Guardian Autonomous Research Mandate v1.10

Date: 2026-09-09
Status: canonical for unattended alpha research and EA promotion

## Final objective

Run research continuously and autonomously with the long-term objective of producing **multiple genuinely independent, robust, executable EAs that can make money after realistic costs while respecting the target prop-firm constraints**.

The objective is not to manufacture a passing backtest, maximize in-sample profit, or keep changing rules until something passes. The pipeline must discover reproducible market phenomena, reject weak families quickly, validate survivors out of sample, convert only validated phenomena into executable trading rules, validate execution/cost robustness, and ultimately build a diversified portfolio of EAs whose sources of edge are not merely duplicates of one another.

A scientifically failed alpha must never be rescued with sizing, money management, Challenge Probability Lab, parameter tweaking, or post-hoc filters.

## Architecture

1. ChatGPT is the scientific supervisor. It reads GitHub evidence, designs/preregisters the next experiment, writes/updates research code when required, and updates `research/autonomous/RESEARCH_QUEUE.json`.
2. The local Guardian Research Orchestrator polls `main`, executes only frozen queued jobs, records receipts, and publishes compact health/results.
3. Python is the default research/backtest engine. MT5 is reserved for broker/server data acquisition and execution-fidelity/broker-specific validation where it adds genuine information.
4. `backtest-results` is the evidence bus. The owner is never asked to paste console logs when the system can publish them itself.
5. Jobs are immutable by `(id, revision)` once run. Any scientific change requires a new revision or new job id.

## Scientific invariants

- Market state/event -> future distribution -> robustness -> trading rule -> costs/execution -> EA -> portfolio contribution.
- Discovery, confirmation, and final OOS must remain separated.
- No same-sample rescue of a failed family.
- No arbitrary threshold tweaking after results are known.
- No repeated named-strategy churn.
- Multiple-testing control is mandatory when many hypotheses are screened.
- Costs/execution and Challenge Probability Lab are downstream; sizing may never rescue failed alpha.
- A survivor is not automatically an EA: the phenomenon must first survive its frozen confirmation/OOS gates.
- A profitable EA candidate must remain profitable/credible after realistic spread, commission, slippage assumptions and broker/prop-firm constraints.
- Prefer simple, explainable rules when statistically equivalent to complex ones.
- Seek multiple independent mechanisms/markets/horizons rather than many correlated variants of one edge.
- Phase C BTC/ETH low-movement/no-trade output remains preserved; BTC/ETH directional 5m->1h search remains closed unless genuinely new independent information justifies reopening it through preregistration.

## Protected final OOS policy

Protected data exists to prevent researcher degrees of freedom, **not to require the owner to wake up and press a button**.

A protected final OOS period, including protected 2026 data, may be opened automatically only when ALL of the following are already true before first inspection:

1. a candidate has survived the required discovery/internal-confirmation gates;
2. its exact signal definition, direction, market, horizon, thresholds, exclusions, evaluation metrics, pass/fail criteria and protected test window are frozen;
3. a dated preregistration/policy artifact containing those items is committed to `main`;
4. the queue contains a new immutable job id/revision referencing that preregistration;
5. provenance can prove that protected data was not used to select or tune the candidate.

Once those conditions are met, **no additional owner approval is required to open and evaluate the preregistered protected OOS**.

After protected OOS is opened, the hypothesis, thresholds, exclusions, window and success criteria may not be changed. A failure closes that candidate/family under the frozen hypothesis. Do not retune against protected OOS. A success freezes the validated phenomenon and advances it to trading-rule/execution validation.

Protected data may never be browsed opportunistically, used for discovery, used to choose among variants, or reused to rescue a failure.

## Autonomous decision loop

At every terminal result:

1. verify integrity, provenance, hashes/inputs and protected-data status first;
2. if infrastructure/data failed, repair infrastructure without changing the frozen scientific hypothesis;
3. if the scientific family failed its frozen gates, close it and record the closure;
4. if evidence is suggestive but not confirmatory, run only a preregistered robustness/confirmation step logically justified without seeing future/protected results;
5. if a family is exhausted, move to a genuinely different information representation, event type, horizon, market mechanism or instrument;
6. if a candidate survives internal confirmation, freeze exact rules and preregister final protected OOS;
7. once the Protected final OOS policy conditions are satisfied, execute final OOS automatically;
8. if final OOS fails, close the candidate without rescue;
9. if final OOS passes, freeze the phenomenon and autonomously design the simplest causal/executable trading-rule translation without using final OOS for optimization;
10. test realistic costs, spread/slippage sensitivity, timing assumptions, signal availability, look-ahead safety and execution feasibility;
11. use MT5 only when broker/server/execution fidelity is genuinely required; otherwise prefer Python;
12. if executable robustness survives, build/version an EA candidate and validate it on the appropriate fidelity layer;
13. evaluate correlation and marginal portfolio contribution versus already accepted EA candidates so the final system seeks diversified sources of edge;
14. continue researching independent families rather than stopping after the first successful EA.

## EA promotion gates

A research phenomenon can be promoted toward an EA only if:

- discovery/confirmation/final-OOS provenance is clean;
- final OOS passes its preregistered criteria;
- no look-ahead or unavailable-at-decision-time feature exists;
- realistic costs do not destroy the edge;
- trade frequency/sample size is sufficient for the claimed use;
- drawdown/tail behavior is characterized rather than hidden by average returns;
- implementation can reproduce the research signal deterministically;
- prop-firm rules can be enforced without changing the underlying alpha hypothesis.

Production/live deployment remains a separate approval boundary. Research may autonomously create and validate EA candidates, but it must not modify or deploy production/live-trading code or accounts without explicit owner approval.

## Portfolio objective

The target is not one magic EA. Maintain a registry of validated/closed candidates and seek a portfolio of multiple EAs with differentiated mechanisms, instruments, horizons or regime exposures. When two candidates are materially redundant, prefer the simpler/more robust one rather than counting both as independent successes.

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

The local orchestrator treats `codex_assist` as fail-closed unless an explicitly validated adapter is enabled.

## Queue authority

`research/autonomous/RESEARCH_QUEUE.json` is the machine-execution queue. Jobs are immutable by `(id, revision)` once run. Scientific changes require a new revision or new job id.

The local executor never invents hypotheses. ChatGPT changes the queue after reading published evidence. This separation prevents a deterministic worker from silently data-mining.

## Owner notification policy

Normal research churn is silent. Do not notify the owner merely because a job is running, waiting, passed an infrastructure gate, failed scientifically, or because another autonomous experiment was queued.

Notify the owner only when:

- a candidate has survived **final protected OOS and subsequent executable/cost robustness sufficiently to become a meaningful EA candidate**;
- an unrecoverable local/MT5/account/data condition blocks all useful progress;
- a production/live-trading change or deployment requires explicit approval;
- a scientific governance ambiguity cannot be resolved without changing these invariants.

Do **not** stop merely to request permission to open protected OOS when the preregistration conditions above are satisfied.

## Standing authorization

The owner explicitly authorizes the scientific supervisor and deterministic orchestrator to continue this research pipeline unattended under this mandate, including automatically opening preregistered protected 2026 final-OOS windows when all protection conditions are satisfied. This authorization does not permit post-hoc tuning on protected data and does not authorize live/production trading changes.