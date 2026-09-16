# R34 — signal-feed × execution-feed result

## Verdict

`SIGNAL_FEED_DOMINANT`

The preregistered normalized median scores are `signal=0.609622` and `execution=0.028650`; the signal effect is about 21.3 times the execution effect. This is a completed causal diagnostic, not an alpha PASS or production authorization.

## E1 matrix

| Signal | Execution | 2024 trades / PF / net | 2025 trades / PF / net |
|---|---|---:|---:|
| FundedNext | FundedNext | 95 / 5.1600 / 432.1717 | 107 / 5.0418 / 1214.7940 |
| FundedNext | Dukascopy | 95 / 5.8178 / 466.0963 | 107 / 5.3246 / 1158.9960 |
| Dukascopy | FundedNext | 163 / 0.9136 / -57.4539 | 168 / 1.2122 / 249.6322 |
| Dukascopy | Dukascopy | 163 / 0.9117 / -58.7667 | 168 / 1.2256 / 263.3096 |

The FundedNext→FundedNext diagonal exactly reproduces R31 RAW for net, expectancy_bps and PF in both years. The Dukascopy→Dukascopy diagonal exactly reproduces R33 for the same fields.

## Signal similarity

- 2024: FN 95 signals; Duka 563; exact 0; cumulative ±5 min 0; cumulative ±10 min 0; FN-only 95; Duka-only 563.
- 2025: FN 107 signals; Duka 732; exact 0; cumulative ±5 min 0; cumulative ±10 min 0; FN-only 107; Duka-only 732.
- Consequently, preregistered matched-pair close/high/ATR/prior-96-high/threshold differences are not estimable; no matching window was widened after observing the result.
- Descriptive integrity check only: nearest FN→Duka signal gap was 60 minutes in each year; median nearest gap was 255 minutes in 2024 and 210 minutes in 2025.

## Integrity

- Actual program status: `COMPLETE`.
- `protected_2026_opened=false`.
- `retuning_performed=false`.
- Only R30 2023 tail data needed to construct the first corrected server hours of 2024 was additionally read; no 2026 file was opened.
- Nine output artifacts were published transactionally under `D:\MT5_Backtests\Research\Autonomous\r34_signal_execution_feed_factorial_v100`.
