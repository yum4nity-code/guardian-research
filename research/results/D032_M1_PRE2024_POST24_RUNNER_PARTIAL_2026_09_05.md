# D032-M1 — pre-2024 post-24h runner partial result

Date: 2026-09-05
Status: PARTIAL / PRE2024 EPOCH ONLY / PRIMARY 1R-48H RUNNER NOT ADVANCING ON THIS EPOCH
Classification: MANAGEMENT_DEVELOPMENT_POST24_PREREGISTERED

Canonical preregistration: `research/campaigns/D032_M1_DOJI_POST24_RUNNER_PREREGISTRATION_2026_09_05.md`

## Execution scope actually received
The uploaded run set contains BTCUSD, ETHUSD, DOGUSD core plus ADA/LNK/XRP diagnostics. All RUN_INFO files show the tester stopped in 2023. The preregistered POST2024 epoch (2024-01-01 through 2026-06-23 signals) was therefore **not run** in this batch.

Core PRE2024 clean/eligible counts are unchanged from D032-C1: BTC 33, ETH 32, DOG 14; pooled n=79.

## Frozen primary candidate
At +24h, non-positive trades close. Positive trades become full-position runners with net-BE floor + 1.0R trailing distance, no TP, timeout +48h.

PRE2024 results versus the already confirmed +24h full-exit baseline:

| Symbol | n | Baseline +24h mean | 1R->48h runner mean | Paired delta |
|---|---:|---:|---:|---:|
| BTCUSD | 33 | +1.1111R | +1.1099R | -0.0011R |
| ETHUSD | 32 | +0.0428R | +0.1034R | +0.0606R |
| DOGUSD | 14 | +0.5985R | +0.4881R | -0.1104R |
| **Pooled** | **79** | **+0.5875R** | **+0.5920R** | **+0.0045R** |

Month-block bootstrap of the paired pooled delta (33 calendar-month blocks, 20,000 resamples) gives an approximate 95% interval of **-0.141R to +0.172R**. The lower bound is below zero.

The preregistered advancement rule also requires at least 2/3 core symbols to have positive paired mean delta. PRE2024 has only ETH positive; BTC is essentially flat/slightly negative and DOG is negative.

**Interpretation:** the frozen 1.0R trail to 48h provides essentially no incremental value over simply exiting at +24h on the PRE2024 epoch. It fails the stability and bootstrap requirements on this epoch.

## Frozen diagnostics (not eligible to replace the primary after seeing outcomes)
Pooled PRE2024 paired deltas versus +24h baseline:
- 0.5R trail to 48h: **-0.0070R**; month-block 95% interval about **-0.080R to +0.075R**.
- 1.5R trail to 48h: **+0.1095R**; all three core symbols positive in point estimate (BTC +0.0745R, ETH +0.1574R, DOG +0.0822R), but month-block 95% interval about **-0.201R to +0.492R**. This is discovery-only and may seed a fresh preregistered candidate; it is not validated here.
- 1.0R trail to 72h: identical pooled mean to the 48h primary (+0.0045R delta), because almost all qualifying runners had already exited by 48h. No evidence of added value from extending this trail to 72h in PRE2024.

## Pre-24h hard-stop diagnostics
Among all 79 clean core events:
- -1.5R was touched before +24h in 48.1%;
- -2.0R in 40.5%;
- -2.5R in 32.9%.

Crucially, among the 51 events that were actually profitable at +24h:
- 16/51 (31.4%) had first traded through -1.5R;
- 10/51 (19.6%) had first traded through -2.0R;
- 7/51 (13.7%) had first traded through -2.5R.

This confirms that a conventional pre-24h stop can remove a material share of eventual winners. A new hard-stop rule must therefore be developed separately and cannot be chosen only from these same outcomes.

## Swap/weekend limitation
Summary results remain net ex-swap. RUN_INFO records current raw broker swap properties, but the scanner does not reconstruct historical swap exactly. Old-period tester model is M1 `1 minute OHLC`; trailing first-touch conclusions remain provisional versus real ticks.

## Non-core diagnostics
ADA, LNK and XRP were unregistered for the primary management verdict and remain negative on their +24h baselines; their runner deltas are also negative in this batch. They do not alter the BTC/ETH/DOG primary management conclusion.

## Next required execution
To complete the preregistered D032-M1 development experiment, run BTCUSD, ETHUSD and DOGUSD on the POST2024 epoch only, with tester dates covering 2024-01-01 through at least 2026-06-27, M1 + `1 minute OHLC`, same MQ5 and unchanged inputs.

Do not promote the diagnostic 1.5R trail before the POST2024 results are collected and a fresh validation design is frozen.
