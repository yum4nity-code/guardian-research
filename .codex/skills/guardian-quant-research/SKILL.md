---
name: guardian-quant-research
description: GUARDIAN-specific protocol for robust quantitative strategy research. Use for hypothesis generation, backtests, OOS validation, robustness checks, FTMO-oriented evaluation, and research receipts. Enforces holdout integrity, anti-look-ahead rules, realistic costs, reproducibility, and strict separation between discovery and validation.
---

# GUARDIAN Quant Research

Treat research integrity as a hard constraint. A profitable result is not useful if the protocol makes it impossible to distinguish signal from leakage, selection bias, or overfitting.

## Protect data and holdouts

- Never rewrite, normalize in place, truncate, or mutate raw historical source files.
- Use project manifests and receipts to determine allowed research windows.
- Any protected holdout is off limits until explicit human authorization. Treat 2026 as protected whenever the active GUARDIAN protocol marks it locked.
- Do not inspect a protected period merely to understand a failure.
- Validate point-in-time correctness, symbol mapping, timezone/DST handling, sessions, missing bars and duplicates before judging an edge.

## Separate discovery from validation

- Define the hypothesis, market, direction, features, entry/exit logic, parameter ranges, costs, metrics and pass/fail gates before opening OOS results.
- IS is for discovery. OOS is for evaluation, not iterative optimization.
- If logic or thresholds change after OOS inspection, create a new candidate/version. Do not silently preserve the old validation claim.
- Never rescue a failed OOS result by tuning on the same OOS window.

## Model execution realistically

Include material frictions:
- spread and commission;
- slippage assumptions;
- latency/bar-close assumptions;
- stop/limit fill rules;
- lot/step constraints where relevant;
- session closures and weekend behavior;
- prop-firm/broker rules loaded from a versioned configuration.

Before deployment conclusions, verify current FTMO rules from an authoritative source. Do not treat remembered rules as timeless.

## Evidence required

Report when applicable:
- trade count and exposure;
- win rate and payoff ratio;
- mean/median return per trade;
- annual/subperiod stability;
- max drawdown and drawdown duration;
- Sharpe, Sortino and Calmar;
- tail loss/CVaR where meaningful;
- baseline/control comparison;
- effect size with uncertainty;
- parameter sensitivity;
- regime dependence;
- concentration by day, hour, symbol, or a small number of trades.

Call out results dominated by very few observations.

## Robustness

Use tests that can falsify the hypothesis:
- walk-forward/rolling validation;
- parameter perturbation and neighborhood stability;
- bootstrap or Monte Carlo resampling;
- alternate realistic cost assumptions;
- alternate defensible data/execution assumptions;
- multiple-hypothesis or selection-bias controls when many candidates were searched;
- deflated Sharpe or equivalent selection-aware metrics when appropriate.

Define in advance what outcome makes the candidate fail.

## Reproducibility receipt

Every meaningful run should record:
- run_id and timestamp;
- code commit/hash;
- candidate ID;
- data identifiers and windows;
- timezone/session assumptions;
- parameters;
- random seed if any;
- transaction-cost assumptions;
- trade count;
- core metrics;
- predefined gates;
- PASS / FAIL / INCONCLUSIVE;
- exact verdict reason;
- whether a protected holdout was accessed.

Check for an equivalent active job before launching a duplicate when run-state tracking exists.

## Interpretation rules

- Failure is information. Record it; do not bury it.
- A statistical edge is not automatically tradable.
- A tradable edge is not automatically FTMO-compatible.
- Prefer simple, stable effects to fragile high-return parameter combinations.
- Do not claim causality from correlation without a design that supports it.
- Keep hypothesis generation, confirmation and deployment approval as separate stages.

## Final output

End research reports with:
1. Hypothesis tested.
2. Data actually accessed.
3. Protocol/leakage checks.
4. Results and uncertainty.
5. Robustness results.
6. Failure modes/caveats.
7. Verdict against predeclared gates.
8. Exact next permitted action.

If the protocol is compromised, the verdict is INVALID regardless of PnL.
