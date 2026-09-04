# D025 2025 replication diagnostic — 2026-09-04

Source: user-supplied appended `d025_ler_trading_1_01_trades(7).csv` and `outcomes(7).csv`. New sessions were isolated by comparing them with the prior `(6)` append files, avoiding double-counting of older BTC/ETH runs.

## New 2025 sessions isolated

- BTCUSD: 503 trades, 2025-01-02 -> 2025-12-30
- ETHUSD: 557 trades, 2025-01-01 -> 2025-12-30
- GBPUSD: 360 trades, 2025-01-07 -> 2025-12-30
- USDJPY: 424 trades, 2025-01-02 -> 2025-12-30
- XAUUSD: 399 trades, 2025-01-02 -> 2025-12-29
- SOLUSD: 330 trades, 2025-04-29 -> 2025-12-30 (partial-year history only)

Total new 2025 trades: 2,573.

A +R target is counted only when its first hit timestamp is positive and occurs before `stop_utc`; fixed-TP EV below is resolved target-vs-SL only, before costs, and excludes unresolved 48h exits from the denominator.

## 2025 aggregate first-touch

| Symbol | Trades | +1R | +2R | +3R | +4R | +5R | EV 1R | EV 2R | EV 3R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BTCUSD | 503 | 52.29% | 30.82% | 21.27% | 14.71% | 11.33% | +0.063R | -0.004R | -0.038R |
| ETHUSD | 557 | 51.17% | 30.52% | 21.54% | 14.36% | 11.31% | +0.050R | -0.004R | -0.014R |
| GBPUSD | 360 | 51.67% | 29.17% | 17.50% | 11.39% | 7.78% | +0.107R | +0.033R | -0.134R |
| SOLUSD | 330 | 48.79% | 32.73% | 24.55% | 16.97% | 11.52% | -0.006R | +0.019R | +0.042R |
| USDJPY | 424 | 46.23% | 28.54% | 19.34% | 15.80% | 10.14% | -0.027R | -0.055R | -0.114R |
| XAUUSD | 399 | 41.60% | 22.56% | 15.54% | 8.77% | 5.51% | -0.100R | -0.220R | -0.260R |

## Replication against 2024 / 2026

### ETH RETEST is the strongest recurring path signal

- 2024 RETEST: EV2 +0.084R
- 2025 RETEST: EV2 +0.109R
- 2026 Jun-Jul RETEST: EV2 +0.588R

Pooled 2024-2026 ETH RETEST: 704 trades; resolved +2R first-touch probability 37.78%, EV2 +0.133R before costs. Wilson 95% CI for resolved +2R probability: ~34.18% to 41.52%, above the theoretical 33.33% break-even threshold before costs.

ETH ACCEPTANCE remains materially weaker: 2024 EV2 -0.156R, 2025 -0.145R, 2026 -0.067R.

### BTC shows a repeatable short-side early edge, not a stable global runner edge

BTC global:
- 2024 EV1 +0.024R / EV2 +0.016R
- 2025 EV1 +0.063R / EV2 -0.004R
- 2026 Jun-Jul EV1 +0.018R / EV2 +0.173R

BTC SHORT pooled 2024-2026: 625 trades; EV1 +0.096R, EV2 +0.067R, EV3 -0.076R. The 1R resolved hit probability is 54.80% (Wilson 95% CI ~50.85% to 58.69%), above 50% before costs.

### GBPUSD has a recurring short-side early edge, while path leadership is unstable

- 2024 RETEST outperformed ACCEPTANCE at 2R.
- 2025 this reversed sharply: ACCEPTANCE EV1 +0.287R / EV2 +0.240R; RETEST EV1 -0.079R / EV2 -0.168R.
- Therefore path-specific GBP rules are not yet robust.

GBP SHORT pooled 2024-2026: 421 trades; EV1 +0.121R, EV2 +0.072R, EV3 -0.020R. Resolved 1R probability 56.03% (Wilson 95% CI ~51.12% to 60.83%).

### SOL is promising but history is incomplete

2025 SOL begins only 2025-04-29. Aggregate 2025 EV2 +0.019R / EV3 +0.042R. The SHORT branch is much stronger: 2025 EV2 +0.196R / EV3 +0.235R; 2026 Jun-Jul SHORT EV2 +0.324R / EV3 +0.294R. Pooled 2025-2026 SOL SHORT: 199 trades, EV2 +0.219R, EV3 +0.246R. Treat as promising, not established, because there is no 2024 sample and only partial 2025 coverage.

### USDJPY 2026 strength does not replicate backward

- 2024 global EV2 -0.084R
- 2025 global EV2 -0.055R
- 2026 Jun-Jul EV2 +0.213R

Conclusion: current 2026 continuation is regime-specific until proven otherwise. No stable side/path split survives both 2024 and 2025 strongly enough for production promotion.

### XAU 2024 RETEST did not replicate in 2025

- 2024 RETEST EV2 +0.158R
- 2025 RETEST EV2 -0.196R
- 2025 global XAU is weak: EV1 -0.100R / EV2 -0.220R / EV3 -0.260R.

Therefore the apparent XAU RETEST edge from 2024 is rejected as a robust standalone rule at this stage.

## Cross-market conclusion

Across the five full-year common markets (BTC, ETH, GBP, USDJPY, XAU), 2024+2025 contains 4,773 trades. Pooled universal D025 is approximately flat at 1R (EV +0.011R before costs) and negative at 2R (-0.032R) and 3R (-0.106R). Therefore D025 does not show a universal fixed-TP edge across all markets.

However, enough data now exists to move beyond indiscriminate symbol collection and into a preregistered management/branch-validation stage. The strongest recurring candidates are:

1. ETH RETEST, especially around 2R continuation;
2. BTC SHORT, primarily early 1R/2R edge;
3. GBP SHORT, primarily early 1R/2R edge;
4. SOL SHORT as a promising but less mature candidate.

XAU and USDJPY should remain control / regime-sensitive markets rather than promoted edges.

## Next experiment

Do not change D025 V0 entry thresholds or the structural SL. Current CSVs cannot reconstruct a partial-at-1R + move-to-BE + runner path exactly because they do not record whether price returns to entry after +1R before later targets. Therefore the next EA revision should instrument management directly rather than infer it post hoc.

Preregister a tiny exit set only:
- full TP at +1R;
- full TP at +2R;
- one partial-at-+1R + BE remainder + runner rule, with a single frozen trailing specification;
- add +0.5R timestamp and post-+1R BE-touch timing.

No broad grid optimization and no market-specific threshold tuning from these samples.