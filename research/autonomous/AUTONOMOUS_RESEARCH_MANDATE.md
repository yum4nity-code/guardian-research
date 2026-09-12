# Guardian Autonomous Research Mandate v1.12

Date: 2026-09-10
Status: canonical for unattended alpha research and EA promotion

## Final objective

Run research continuously and autonomously with the long-term objective of producing **multiple genuinely independent, robust, executable EAs that can make money after realistic costs while respecting the target prop-firm constraints**.

The machine is explicitly authorized to search broadly across **all locally available tradable instruments, multiple timeframes, multiple strategy families, deterministic rule families and preregistered randomized/generated rule spaces**. CPU time is a research resource: when useful data and valid search space exist, the system should prefer productive research over idle WAITING.

The objective is not to manufacture a passing backtest, maximize in-sample profit, or keep changing rules until something passes. Broad/random search is permitted only as discovery inside a frozen search space; survivors must still pass independent temporal validation, multiple-testing-aware selection, cost/execution robustness and final protected OOS before promotion.

A scientifically failed alpha must never be rescued with sizing, money management, Challenge Probability Lab, parameter tweaking, or post-hoc filters.

## Architecture

1. ChatGPT is the scientific supervisor. It reads GitHub evidence, designs/preregisters experiments and broad search spaces, writes/updates research code when required, and updates the queue.
2. The local Guardian Research Orchestrator polls `main`, executes only frozen queued jobs, records receipts, and publishes compact health/results.
3. Python is the default research/backtest engine. MT5 is reserved for broker/server data acquisition and execution-fidelity/broker-specific validation where it adds genuine information.
4. `backtest-results` is the evidence bus. The owner is never asked to paste console logs when the system can publish them itself.
5. Jobs are immutable by `(id, revision)` once run. Any scientific change requires a new revision or new job id.

## Search-factory authorization

Guardian may autonomously run large discovery factories that generate or enumerate candidate rules across available markets. Authorized families include, non-exhaustively:

- momentum/trend and breakout;
- mean reversion/range/rejection;
- volatility, compression/expansion and volatility transitions;
- candle/range/wick/body structure;
- RSI/oscillator and moving-average state;
- time/session/day-of-week effects;
- volume/tick-volume/activity states;
- multi-horizon and regime-conditional rules;
- simple combinations/interactions of pre-decision-time features;
- randomized rule generation using a committed seed and frozen parameter/search domains;
- genuinely different instruments and timeframes when data is available.

The factory may reject thousands or millions of candidates cheaply. This is expected. It must record the number of hypotheses/trials tested and treat discovery winners as selected hypotheses, **not confirmed edges**.

When a discovery factory ends, the supervisor should automatically freeze a manageable, non-redundant survivor set and queue independent confirmation using data not used to select those survivors. If no survivor exists, close that search family/configuration and move to another market, timeframe, representation or strategy family rather than idling.

## Scientific invariants

- Market state/event -> future distribution -> robustness -> trading rule -> costs/execution -> EA -> portfolio contribution.
- Discovery, confirmation, and final OOS must remain separated.
- No same-sample rescue of a failed family.
- No arbitrary threshold tweaking after results are known.
- Multiple-testing control or an appropriate holdout/selection correction is mandatory when many hypotheses are screened.
- Random/generated strategies are allowed in discovery; random/generated validation against protected data is not.
- Costs/execution and Challenge Probability Lab are downstream; sizing may never rescue failed alpha.
- A survivor is not automatically an EA: the phenomenon/rule must first survive frozen confirmation/OOS gates.
- A profitable EA candidate must remain profitable/credible after realistic spread, commission, slippage assumptions and broker/prop-firm constraints.
- Prefer simple, explainable rules when statistically equivalent to complex ones.
- Seek multiple independent mechanisms/markets/horizons rather than many correlated variants of one edge.
- Historical failed branches remain evidence but must not prevent newer independent runnable jobs from executing.
- Phase C BTC/ETH low-movement/no-trade output remains preserved. Closed directional families may be revisited only through genuinely new independent representations/search spaces, not parameter rescue.

## Mandatory long-history gate before protected OOS

Effective 2026-09-12, broad alpha research must exploit the longest clean pre-OOS history available before spending protected final-OOS data.

For XAUUSD and any market with sufficient history, the default chronological research architecture is:

1. **Discovery:** 2017-01-01 through 2022-12-31. Large deterministic/randomized factories may screen millions of frozen hypotheses cheaply here.
2. **Independent confirmation:** 2023-01-01 through 2024-12-31. Survivor definitions are frozen before these results are opened.
3. **Pre-OOS temporal gate:** 2025-01-01 through 2025-12-31. No retuning after this gate is opened.
4. **Broker/execution-fidelity check:** MT5/real broker feed only for the small finalist set when it adds information; never run millions of candidates through Strategy Tester.
5. **Protected final OOS:** 2026 only after all prior gates pass and exact final rules/criteria are preregistered.

Every serious candidate should also be characterized across the complete 2017-2025 pre-OOS history with yearly, monthly, rolling 6/12-month, realistic-cost, stress-cost, best-trade concentration, drawdown/tail and trade-count diagnostics. Selection must not be based only on aggregate profit factor or net profit.

The long-history gate is intended to reject regime-fragile candidates before protected OOS. It does **not** authorize optimizing parameters across 2017-2025 until a pleasing curve appears. Search spaces, seeds, rule definitions and stage gates must be frozen before the corresponding stage is evaluated.

If a market genuinely lacks the default historical depth, use the longest clean history available and preregister the alternative chronology before discovery. Do not shorten history merely for convenience.

Existing protected-OOS results remain historical evidence; they are not retroactively reclassified. Failed protected candidates remain closed and may not be rescued by the new long-history process.

## Protected final OOS policy

Protected data exists to prevent researcher degrees of freedom, not to require the owner to wake up and press a button.

A protected final OOS period may be opened automatically only when ALL of the following are already true before first inspection:

1. a candidate has survived the required discovery/internal-confirmation gates;
2. its exact signal definition, direction, market, horizon, thresholds, exclusions, evaluation metrics, pass/fail criteria and protected test window are frozen;
3. a dated preregistration/policy artifact containing those items is committed to `main`;
4. the queue contains a new immutable job id/revision referencing that preregistration;
5. provenance can prove that protected data was not used to select or tune the candidate.

Once those conditions are met, no additional owner approval is required to evaluate the preregistered protected OOS under the standing authorization.

After protected OOS is opened, the hypothesis, thresholds, exclusions, window and success criteria may not be changed. A failure closes that candidate under the frozen hypothesis. Do not retune against protected OOS. A success freezes the validated rule/phenomenon and advances it to trading-rule/execution validation.

Protected data may never be browsed opportunistically, used for discovery, used to choose among variants, or reused to rescue a failure.

## Autonomous decision loop

At every terminal result:

1. verify integrity, provenance, hashes/inputs and protected-data status first;
2. if infrastructure/data failed, repair infrastructure without changing the frozen scientific hypothesis/search space;
3. if a scientific family/search space failed, close it and record the closure;
4. if a large discovery factory produced survivors, deduplicate them and freeze independent confirmation before looking at confirmation data;
5. if no survivors exist, move automatically to a genuinely different market, timeframe, information representation, mechanism or generated search space;
6. if a candidate survives internal confirmation, freeze exact rules and preregister final protected OOS;
7. once protected-OOS conditions are satisfied, execute final OOS automatically;
8. if final OOS fails, close the candidate without rescue;
9. if final OOS passes, freeze it and design the simplest executable trading-rule translation without using final OOS for optimization;
10. test realistic costs, spread/slippage sensitivity, timing assumptions, signal availability, look-ahead safety and execution feasibility;
11. use MT5 only when broker/server/execution fidelity is genuinely required; otherwise prefer Python;
12. if executable robustness survives, build/version an EA candidate and validate it on the appropriate fidelity layer;
13. evaluate correlation and marginal portfolio contribution versus already accepted EA candidates;
14. continue researching independent families rather than stopping after the first successful EA;
15. avoid idle WAITING when independent, scientifically valid discovery work can be queued from available data.

## EA promotion gates

A research rule/phenomenon can be promoted toward an EA only if discovery/confirmation/final-OOS provenance is clean; final OOS passes preregistered criteria; no look-ahead feature exists; realistic costs do not destroy the edge; frequency/sample size supports the claim; drawdown/tail behavior is characterized; implementation reproduces the signal deterministically; and prop-firm rules can be enforced without changing the underlying alpha hypothesis.

Production/live deployment remains a separate approval boundary. Research may autonomously create and validate EA candidates, but it must not modify or deploy production/live-trading code or accounts without explicit owner approval.

## Portfolio objective

The target is not one magic EA. Maintain a registry of validated/closed candidates and seek a portfolio of multiple EAs with differentiated mechanisms, instruments, horizons or regime exposures. When two candidates are materially redundant, prefer the simpler/more robust one.

## Timeout/watchdog policy

Long runtime alone is not failure. Jobs with heartbeat/progress files use adaptive timeout and are killed only when both elapsed time exceeds the adaptive hard limit and heartbeat is stale. Every new long-running research engine must publish `completed`, `total`, `stage`, and timestamp/mtime.

## Codex budget

Codex is not the orchestrator and not the scientific decision maker. Default: do not call Codex. It may be requested only for a real code blocker after deterministic repairs fail, or for a genuinely large new MQL5 implementation where second-agent review materially reduces risk; requests must remain tightly scoped and budgeted.

## Queue authority

`research/autonomous/RESEARCH_QUEUE.json` plus the append queue consumed by the orchestrator are the machine-execution queue. Jobs are immutable by `(id, revision)` once run. The worker may enumerate/generate strategies only inside a committed frozen factory/search specification; it may not silently alter the search domain based on outcomes.

## Owner notification policy

Normal research churn is silent. Do not notify the owner merely because a job is running, waiting, passed an infrastructure gate or failed scientifically. Notify only when a meaningful EA candidate survives final protected OOS plus executable/cost robustness; an unrecoverable condition blocks all useful progress; a production/live change requires approval; or a governance ambiguity cannot be resolved without changing these invariants.

## Standing authorization

The owner explicitly authorizes the scientific supervisor and deterministic orchestrator to continue this research pipeline unattended, including broad multi-asset/multi-family/randomized discovery within frozen search spaces and automatically opening preregistered protected final-OOS windows when all protection conditions are satisfied. This authorization does not permit post-hoc tuning on protected data and does not authorize live/production trading changes.
