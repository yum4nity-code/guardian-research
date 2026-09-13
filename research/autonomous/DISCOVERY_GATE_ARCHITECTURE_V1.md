# Guardian Discovery Gate Architecture v1

Date: 2026-09-13
Status: canonical for NEW research families after R11

## Why this correction exists

Cold audit of R8-R11 found no evidence of a mechanical `survivor_count=0` bug, but found a methodological bottleneck shared by the recent engines: discovery simultaneously required sample-size, profitability after realistic cost, profitability after stress cost, multi-year economic positivity and a stringent p-value. This mixes phenomenon discovery with downstream economic/execution robustness and makes a zero-candidate result diagnostically opaque.

Historical R8-R11 verdicts remain frozen. This policy MUST NOT be used to rescue, retune, reclassify or reopen those failed families.

## Canonical stage separation for future families

### 1. Discovery

Question: does a causal phenomenon exist strongly enough to justify independent confirmation?

Discovery gates may include:
- preregistered minimum sample size appropriate to the horizon/frequency;
- causal/no-look-ahead and data-integrity requirements;
- gross directional effect greater than zero in the hypothesized direction;
- a preregistered statistical selection rule with multiple-testing awareness appropriate to the search size;
- a light stability diagnostic sufficient to reject effects caused entirely by one tiny subperiod.

Discovery MUST NOT require profitability under both realistic and stress trading costs as a selection condition. Cost metrics may be recorded diagnostically, but they are not discovery gates.

### 2. Independent confirmation

Question: does the exact frozen phenomenon reproduce on untouched confirmation data?

- Candidate definitions freeze before confirmation is inspected.
- No threshold, direction, horizon, exclusion or feature retuning is permitted.
- Confirmation uses its own preregistered sample-size/statistical/stability criteria and multiple-testing correction where applicable.
- Confirmation is about reproducibility of the phenomenon, not position sizing or prop-firm optimization.

### 3. Economic/execution robustness

Question: is the independently reproduced phenomenon plausibly tradable?

Only after confirmation, apply the appropriate frozen checks, including as relevant:
- realistic round-trip cost;
- stress cost;
- spread/slippage/commission sensitivity;
- overlap/one-position semantics;
- best-trade removal and concentration;
- drawdown/tail diagnostics;
- signal availability and executable timing.

A failure here closes the candidate. Costs or sizing must never rescue a failed alpha.

### 4. Pre-OOS 2025

Exact rule and economic assumptions remain frozen. Require preregistered temporal robustness. No retuning after opening 2025.

### 5. Protected final OOS 2026

Existing protected-OOS policy is unchanged. 2026 may only be opened under the canonical mandate conditions. This architecture does not grant any new permission to inspect protected data.

## Mandatory diagnostic funnel

Every new discovery factory MUST persist metrics for ALL tested definitions, not only passing candidates. At minimum publish aggregate counts for:

1. definitions tested;
2. definitions meeting minimum sample size;
3. definitions with gross effect in hypothesized direction;
4. definitions passing the discovery statistical rule;
5. definitions passing discovery stability;
6. frozen discovery candidates;
7. confirmation candidates;
8. candidates surviving realistic costs;
9. candidates surviving stress costs;
10. pre-OOS survivors.

Where practical, persist a compact per-definition diagnostics table containing candidate/rule id, trade count, gross mean/effect, p-value or test statistic, stability diagnostic and cost means. This diagnostic evidence MUST NOT be used to post-hoc retune a failed frozen family.

A terminal `0 candidates` result is insufficient on its own: the result artifact must identify the dominant rejection gate(s).

## R8-R11 retrospective audit

Run a DIAGNOSTIC-ONLY audit using only already-authorized pre-2026 data and the exact historical frozen definitions. The audit may recompute intermediate metrics to identify where definitions were rejected. It MUST NOT:
- alter historical PASS/FAIL verdicts;
- promote any retrospectively observed candidate;
- change thresholds after seeing outcomes;
- open or inspect 2026;
- feed retrospectively selected R8-R11 variants into confirmation/OOS as if prospectively selected.

The audit output should report per family: tested count, sample-size pass count, gross-positive count, realistic-cost-positive count, stress-cost-positive count, stability pass count, statistical pass count, original all-gates pass count, and the dominant bottleneck.

## Engineering requirement

All substantial future factory changes still require the mandate's mandatory cold audit and regression tests before execution. Tests must explicitly verify that economic/stress-cost conditions are not accidentally reintroduced into discovery selection.

## Scientific intent

This change lowers no final standard. It separates three distinct questions in the correct order:

1. Is there a phenomenon?
2. Does it reproduce independently?
3. Is it economically executable after realistic costs?

Final EA promotion and production/live approval boundaries remain unchanged. Never deploy to live/real without explicit owner approval.
