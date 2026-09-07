# Guardian Management Benchmark V2

**Exploratory late-protection replay only — not confirmation-grade. V1 remains immutable.**

Datasets: D038, D039, D040, D045 (1,803 frozen development trades)

## Cross-family ranking

| Rank | Rule | Improved | Worst ΔR | Median ΔR | Equal-family ΔR | Pooled ΔR/trade |
|---:|---|---:|---:|---:|---:|---:|
| 1 | BE_AFTER_3R | 1/4 | -0.000000 | -0.000000 | -0.000000 | -0.000000 |
| 2 | SL1_TP5 | 1/4 | -0.048002 | -0.036558 | -0.027529 | -0.033946 |
| 3 | LOCK1_AFTER_2R | 1/4 | -0.051787 | -0.041597 | -0.032151 | -0.038597 |
| 4 | LOCK1_AFTER_3R | 1/4 | -0.053968 | -0.041625 | -0.033599 | -0.039374 |
| 5 | P25_AT_3R_LOCK2_REST | 1/4 | -0.059345 | -0.046073 | -0.037369 | -0.043621 |
| 6 | LOCK2_AFTER_3R | 1/4 | -0.062273 | -0.048031 | -0.035636 | -0.044425 |
| 7 | P25_AT_3R_REST_ORIGINAL | 0/4 | -0.012640 | -0.011034 | -0.010642 | -0.010302 |
| 8 | P25_AT_2R_REST_ORIGINAL | 0/4 | -0.015190 | -0.013278 | -0.012734 | -0.012095 |
| 9 | P25_AT_2R_LOCK1_REST | 0/4 | -0.054031 | -0.042626 | -0.036848 | -0.041043 |

## Boundary

Results are R-threshold proxies using original round-turn commission. No V2 rule may alter parent verdicts or be treated as production evidence.
Time exits, continuous trailing and exact 2.5R partials remain unsupported without richer path/MT5 replay.
