# D025 1.03 Virtual Path Diagnostic — 2026-09-04

Source: user-supplied cumulative 1.03 files:
- `d025_ler_virtual_1_03_events.csv`
- `d025_ler_virtual_1_03_trades.csv`
- `d025_ler_virtual_1_03_outcomes.csv`

The files contain five complete 2024-01-01 -> 2025-12-31 sessions:
- BTCUSD
- ETHUSD
- DOGUSD
- XAUUSD
- USDJPY

Purpose: verify whether removing all real-order/account/lot/margin dependencies restores the larger 1.01 signal population, and obtain clean path instrumentation (+0.5R, +1R..+5R, stop, BE-after-1R).

## 1. Signal population result — IMPORTANT CORRECTION

1.03 virtual VALID_SIGNAL counts:

| Symbol | 1.03 virtual trades | 2024 | 2025 | prior 1.02 real-order 0.05% | prior 1.01 separate-year total | 1.03 / prior 1.01 |
|---|---:|---:|---:|---:|---:|---:|
| BTCUSD | 499 | 298 | 201 | 490 | 1,117 | 44.7% |
| ETHUSD | 553 | 358 | 195 | 544 | 1,172 | 47.2% |
| XAUUSD | 798 | 432 | 366 | 798 | 849 | 94.0% |
| USDJPY | 793 | 401 | 392 | 791 | 866 | 91.6% |

There were **zero** `VALID_SIGNAL_REJECTED_BAD_RISK` and **zero** `VALID_SIGNAL_REJECTED_NO_SLOT` events in 1.03. Every logged VALID_SIGNAL became a virtual trade.

### Consequence

The earlier explanation that BTC/ETH were mainly missing because of real-order execution, lot minimums, margin or account state is **falsified / incomplete**.

Removing the entire trading layer changed BTC from 490 -> 499 and ETH from 544 -> 553 only. XAU and USDJPY were virtually unchanged. Therefore the major BTC/ETH population discrepancy exists **upstream of order execution**.

Do NOT request more broad 1.03 reruns until the population discrepancy is reconciled.

## 2. Comparison against the original 1.01 sessions

The original user-supplied 1.01 CSVs were re-opened directly from prior conversation uploads, not reconstructed from summary text.

Original full-year sessions:
- BTCUSD 2024: 614 unique event/trade IDs
- BTCUSD 2025: 503
- ETHUSD 2024: 615
- ETHUSD 2025: 557
- XAUUSD 2024: 450
- XAUUSD 2025: 399
- USDJPY 2024: 442
- USDJPY 2025: 424

No duplicate event IDs were found in those full-year 1.01 sessions, so the larger counts are not explained by duplicate rows inside a session.

Exact signal-time matching shows that many current 1.03 signals correspond to old 1.01 signals, but not all. In 2024, BTC/ETH/USDJPY also show a frequent ~60-minute timestamp displacement relative to old records, while XAU is much more stable. This is a strong provenance/test-clock/configuration clue, but it does not by itself explain the missing population.

The signal-state code between 1.01/1.02 and 1.03 was statically compared around the state machine and remains materially the same before the order/virtual-trade creation boundary. Therefore the next investigation should focus on **tester/data/provenance differences** before changing D025 rules.

Candidates to verify, without assuming one is the cause:
- Strategy Tester modeling/configuration differences between the original 1.01 separate-year runs and the current combined 2024-2025 runs;
- historical data/feed/cache differences, especially crypto;
- tester-time / `TimeGMT()` behavior and timestamp mapping;
- any symbol-history coverage or data-generation difference between the runs.

Do not tune D025 entry thresholds to compensate for this discrepancy.

## 3. Preliminary 1.03 path diagnostics — NOT YET A PRODUCTION SAMPLE

Method: target hit counts only if the first target timestamp precedes original `stop_utc`; exact same-M1 target/stop ties are not forced into an arbitrary ordering. Fixed-TP EV is resolved target-vs-stop only and remains **before spread, commission and slippage**.

| Symbol | n | +0.5R EV | +1R EV | +2R EV | +3R EV | +2R before BE after +1R* |
|---|---:|---:|---:|---:|---:|---:|
| BTCUSD | 499 | +0.007R | +0.046R | -0.002R | -0.125R | 52.9% |
| ETHUSD | 553 | -0.039R | -0.053R | -0.090R | -0.100R | 52.1% |
| DOGUSD | 595 | -0.115R | -0.106R | -0.170R | -0.272R | 48.3% |
| XAUUSD | 798 | +0.021R | -0.011R | -0.068R | -0.148R | 47.0% |
| USDJPY | 793 | -0.029R | -0.036R | -0.043R | -0.137R | 50.7% |

`*` Among +1R winners with non-ambiguous BE-after-1 path; probability is resolved +2R-before-BE vs BE-before-+2R.

These aggregate results contain no large universal edge and should **not** supersede the earlier 1.01 branch findings until the population mismatch is resolved.

## 4. Interesting branch observations inside the current 1.03 population

These are exploratory only because the population provenance problem is unresolved.

Pooled 2024-2025 current 1.03:
- BTC SHORT: n=256, EV1 about +0.174R, EV2 about +0.192R, EV3 about +0.028R.
- XAU RETEST: n=417, EV1 about +0.104R, EV2 about +0.077R.
- DOG SHORT: n=275, EV1 about +0.076R, EV2 about +0.068R.
- ETH RETEST: n=296, EV1 about +0.031R, EV2 about -0.038R.

Year split warns against premature promotion:
- BTC SHORT is very strong in current 2024 sample (EV1 ~+0.279R, EV2 ~+0.364R) but much weaker in current 2025 (EV1 ~+0.020R, EV2 ~-0.077R).
- ETH RETEST is positive in current 2024 but negative in current 2025.
- XAU RETEST is positive in current 2024 but weaker/negative at 2R in current 2025.

This reinforces the user's requirement: **do not accept crumbs and do not promote a regime-specific branch merely because a pooled number looks attractive**.

## 5. Decision

- 1.03 virtual path instrumentation: **VALID**.
- Real-order/min-volume hypothesis as main cause of BTC/ETH low count: **REJECTED / INCOMPLETE**.
- Current 1.03 BTC/ETH population equivalence to old 1.01: **NOT VALIDATED**.
- Additional broad reruns: **PAUSE** until tester/data/provenance mismatch is understood.
- D025 V0 entry thresholds: **FROZEN**.
- Cost modeling: still pending; no production decision until spread + commission + slippage and stress-cost tests are applied to a reconciled signal population.

## 6. Next action

Reconcile one controlled BTC comparison first: original 1.01 full-year 2024 configuration/data provenance vs 1.03 full-year 2024 under the exact same tester model/settings/history environment. The objective is not another strategy result; it is to explain why one locked signal engine produced 614 vs 298 valid trades.

Only after that discrepancy is explained should GBP/EUR/other 1.03 reruns be requested.