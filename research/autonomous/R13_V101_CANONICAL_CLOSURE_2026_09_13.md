# R13 v1.01 canonical closure

Date: 2026-09-13
Status: CLOSED — scientific FAIL
Source engine commit: `5725f4d6d6fedb09090145e5706700d438980265`
Backtest-results phase: `r13-btc-eth-failed-breakout-rejection-v101`

## Why v1.01 is canonical

R13 v1.00 completed successfully at the infrastructure layer but was methodology-nonconforming under `DISCOVERY_GATE_ARCHITECTURE_V1.md`: it had reintroduced E1/STRESS economic cost gates inside discovery and confirmation.

R13 v1.01 was a protocol-restoration rerun only. The original 72 signal definitions, strict beyond-channel sweep semantics, costs, input hashes, chronology and protected-2026 boundary were preserved. No signal threshold, direction, hold, channel, penetration or re-entry parameter was retuned.

The local-vs-committed engine blob was verified identical before completion:
`73b334a6942d9db07bda8e9af963b19424294152`.

## Final v1.01 result

- definitions tested: 72
- enough sample size: 66
- gross-positive definitions: 24
- gross-stable definitions: 34
- definitions passing discovery BH-FDR: 0
- frozen discovery candidates: 0
- confirmation candidates: 0
- economic candidates: 0
- 2025 pre-OOS survivors: 0
- protected 2026 opened: false
- stderr: empty

The smallest discovery BH-FDR q observed in the diagnostic review was approximately 0.92185. Among definitions already satisfying sample-size, positive-gross and gross-stability gates, the best q was approximately 0.94266. R13 therefore was not a near miss at the statistical gate.

## Classification

R13 v1.01 is a clean scientific FAIL:
- infrastructure healthy;
- protocol conforming;
- exact pre-2026 input hashes matched;
- no economic gate contaminated discovery or confirmation;
- no post-hoc rescue;
- protected 2026 remained unopened.

Do not retune or reopen R13 under the same failed-breakout hypothesis. Any future related work must be a genuinely independent hypothesis or an externally preregistered literature replication.
