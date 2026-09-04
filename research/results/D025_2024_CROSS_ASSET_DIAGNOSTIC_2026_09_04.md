# D025 2024 cross-asset first-touch diagnostic — 2026-09-04

Source: user-supplied cumulative `d025_ler_trading_1_01_trades(6).csv` and `d025_ler_trading_1_01_outcomes(6).csv`. Isolated the five sessions whose entries are in calendar year 2024: BTCUSD, ETHUSD, GBPUSD, USDJPY, XAUUSD.

Method: a +kR hit counts only when the first positive `hit{k}_utc` occurs before `stop_utc` (or no stop was recorded). Simple fixed-TP EV uses resolved target-vs-SL cases only, before costs, slippage, and unresolved 48h exits. This is diagnostic, not authorization to tune entry thresholds post hoc.

## Aggregate 2024

2,530 trades total.

- +1R before SL: 47.51%
- +2R: 29.33%
- +3R: 19.13%
- +4R: 13.12%
- +5R: 9.45%
- resolved EV: TP1 +0.001R, TP2 -0.019R, TP3 -0.111R, TP4 -0.209R

## By symbol

| Symbol | Trades | +1R | +2R | +3R | +4R | +5R | EV1 | EV2 | EV3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BTCUSD | 614 | 49.35% | 31.43% | 20.52% | 12.21% | 9.12% | +0.024R | +0.016R | -0.077R |
| ETHUSD | 615 | 46.50% | 30.08% | 18.86% | 14.63% | 10.89% | -0.032R | -0.014R | -0.133R |
| GBPUSD | 409 | 46.94% | 30.07% | 20.54% | 15.40% | 11.00% | -0.010R | +0.025R | -0.064R |
| USDJPY | 442 | 47.96% | 27.15% | 18.33% | 11.54% | 8.37% | +0.019R | -0.084R | -0.136R |
| XAUUSD | 450 | 46.44% | 26.89% | 17.11% | 11.78% | 7.56% | +0.007R | -0.055R | -0.152R |

## Path split

### BTCUSD
- ACCEPTANCE 301: +1R 48.84%, +2R 30.56%, +3R 19.93%, +4R 9.63%, +5R 5.65%; EV1 +0.046R, EV2 +0.038R, EV3 -0.044R.
- RETEST 313: +1R 49.84%, +2R 32.27%, +3R 21.09%, +4R 14.70%, +5R 12.46%; EV1 +0.003R, EV2 -0.003R, EV3 -0.105R.
Interpretation: aggregate BTC is close to breakeven at 1R/2R. RETEST carries a fatter 4R/5R tail but does not establish a positive simple TP3 EV in 2024.

### ETHUSD
- ACCEPTANCE 267: +1R 42.32%, +2R 24.34%, +3R 14.61%, +4R 10.49%, +5R 8.61%; EV1 -0.103R, EV2 -0.156R, EV3 -0.278R.
- RETEST 348: +1R 49.71%, +2R 34.48%, +3R 22.13%, +4R 17.82%, +5R 12.64%; EV1 +0.021R, EV2 +0.084R, EV3 -0.035R.
Interpretation: ETH 2024 is materially path-dependent. RETEST is the only branch with a positive simple 2R diagnostic EV; ACCEPTANCE is clearly weak in this sample.

### GBPUSD
- ACCEPTANCE 189: +1R 47.62%, +2R 26.46%, +3R 17.46%, +4R 13.76%, +5R 9.52%; EV1 +0.035R, EV2 -0.051R, EV3 -0.165R.
- RETEST 220: +1R 46.36%, +2R 33.18%, +3R 23.18%, +4R 16.82%, +5R 12.27%; EV1 -0.047R, EV2 +0.084R, EV3 +0.015R.
Interpretation: GBPUSD RETEST is the strongest non-gold continuation branch in the 2024 sample, with positive simple EV at 2R and roughly flat/slightly positive at 3R. Needs replication before any production split.

### USDJPY
- ACCEPTANCE 213: +1R 46.01%, +2R 22.54%, +3R 14.55%, +4R 11.27%, +5R 8.45%; EV1 +0.021R, EV2 -0.186R, EV3 -0.253R.
- RETEST 229: +1R 49.78%, +2R 31.44%, +3R 21.83%, +4R 11.79%, +5R 8.30%; EV1 +0.018R, EV2 ~0.000R, EV3 -0.043R.
Interpretation: 2024 does not support USDJPY as a runner candidate in aggregate. The edge, if any, is short-horizon/1R-like; RETEST improves continuation but not enough to establish robust 2R+ edge.

### XAUUSD
- ACCEPTANCE 226: +1R 41.59%, +2R 19.03%, +3R 11.95%, +4R 9.29%, +5R 7.52%; EV1 -0.078R, EV2 -0.291R, EV3 -0.368R.
- RETEST 224: +1R 51.34%, +2R 34.82%, +3R 22.32%, +4R 14.29%, +5R 7.59%; EV1 +0.090R, EV2 +0.158R, EV3 +0.042R.
Interpretation: XAUUSD is strongly path-dependent in 2024. RETEST is clearly superior to ACCEPTANCE and is the cleanest 2024 branch at 1R-3R.

## Side split highlights

- BTCUSD SHORT: +1R 53.17%, +2R 34.14%; EV1 +0.083R, EV2 +0.063R. BTC LONG is weaker.
- ETHUSD SHORT: +2R 32.69%; EV2 +0.038R. Long side weaker.
- GBPUSD SHORT: +1R 50.95%, +2R 30.48%; EV1 +0.070R, EV2 +0.067R. Long side weaker.
- USDJPY LONG: +1R 52.53%; EV1 +0.129R. SHORT side is weak at 1R/2R.
- XAUUSD LONG: +1R 53.70%, +2R 30.56%; EV1 +0.154R, EV2 +0.082R. XAU SHORT is clearly weak.

These side/path observations are post-hoc diagnostics only. Do not convert them directly into production filters without replication on 2025 / other untouched windows.

## Pre-registered replication questions for 2025

Before inspecting 2025 results, test whether these exact 2024 observations replicate:
1. BTC remains near-flat at simple 1R/2R, with SHORT stronger than LONG and RETEST carrying a fatter tail.
2. ETH RETEST remains materially better than ACCEPTANCE, especially around 2R.
3. GBPUSD RETEST remains positive around 2R-3R.
4. USDJPY remains primarily a short-horizon/1R candidate rather than a runner.
5. XAUUSD RETEST, especially LONG, remains materially stronger than ACCEPTANCE/SHORT.

If these do not replicate, treat them as 2024 regime effects rather than stable D025 rules.