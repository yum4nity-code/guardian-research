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

Exact signal-time matching shows that many current 1.03 signals correspond to old 1.01 signals. For BTC 2024, among current signals matched on side/path/level within three hours, the dominant timing offsets were **+60 minutes (98 matches)** and **0 minutes (88 matches)**. Entry prices on those matches are close, so these are largely the same economic moves with different bar/time provenance rather than unrelated signals.

The signal-state code between 1.01/1.02 and 1.03 remains materially the same before the order/virtual-trade creation boundary.

## 3. Immediate mechanism identified: crypto tick-volume collapse blocks CASCADE

D025 V0 requires relative M15 tick volume `>= 1.25` for the CASCADE transition. The 1.03 event file shows that the missing crypto population is created primarily because the historical `tick_volume` series becomes abnormally flat around its rolling mean in large date blocks.

### BTCUSD 2024

- July: 120 sweeps; median relative tick volume 1.290; 65 sweeps >=1.25; 61 CASCADE events.
- **August: 117 sweeps; median 0.999; max only 1.243; zero sweeps >=1.25; zero CASCADE events; zero valid signals.**
- September: 126 sweeps; median 0.995; only 16 sweeps >=1.25; 12 CASCADE events; only 4 valid signals.
- October: relative volume normalizes again; median 1.896; 105 sweeps >=1.25; 89 CASCADE events; 43 valid signals.

The original 1.01 BTC 2024 sample nevertheless had **52 trades in August and 51 in September**. Therefore the old and current runs did not see equivalent usable tick-volume history for those months.

### ETHUSD 2024

- July: 119 sweeps; median relative volume 1.499; 73 >=1.25; 63 CASCADE events.
- **August: 121 sweeps; median 1.043; only 4 >=1.25; 2 CASCADE events; 2 valid signals.**
- **September: 117 sweeps; median 1.031; only 1 >=1.25; 3 CASCADE events; 1 valid signals.**
- October: median 1.406; 70 >=1.25; 61 CASCADE events; 25 valid signals.

Original 1.01 ETH 2024 had **47 trades in August and 48 in September**.

### BTCUSD / ETHUSD 2025

The same data-quality pattern becomes even clearer from August 2025 onward.

BTC median relative tick volume by month Aug-Dec is approximately `1.002 / 1.003 / 1.004 / 1.002 / 1.001`. Sweeps >=1.25 fall to only `11 / 10 / 2 / 3 / 5` despite roughly 96-135 sweeps per month.

ETH median relative tick volume Aug-Dec is approximately `1.025 / 1.033 / 1.023 / 1.022 / 1.053`. Sweeps >=1.25 fall to `4 / 7 / 1 / 0 / 9`.

That behavior is inconsistent with a healthy high-frequency tick-volume series and mechanically disables a large fraction of D025 crypto CASCADE transitions.

### Control markets

XAUUSD does not show the same collapse in Aug-Sep 2024: median relative tick volume remains about 1.35 in August and 1.62 in September, with many sweeps above 1.25. This matches the fact that XAU 1.03 recovers about 94% of the old 1.01 signal population. USDJPY is also much closer to its prior population.

## 4. Strategy Tester setting confirmed from user screenshot

At 2026-09-04 19:48 Europe/Paris, the user showed the FundedNext Strategy Tester Settings for `D025_LER_VirtualPath_1_03.ex5`.

Confirmed settings:
- timeframe M1;
- date range 2024-01-01 -> 2025-12-31;
- Forward = No;
- Delays = Zero latency, ideal execution;
- **Modelling = `Every tick`**.

Crucially, the screenshot does **not** show `Every tick based on real ticks`.

In MT5, `Every tick` is the generated/modelled tick mode; `Every tick based on real ticks` is the high-fidelity mode that uses recorded real-tick history when available. Because D025's CASCADE filter explicitly depends on M15 `tick_volume`, this is now the leading explanation for the flattened/synthetic crypto relative-volume blocks observed in 1.03.

This does not yet prove what model was used by the old 1.01 runs, so the provenance question is not fully closed. It does, however, identify a clean controlled next test.

## 5. Preliminary 1.03 path diagnostics — NOT YET A PRODUCTION SAMPLE

Method: target hit counts only if the first target timestamp precedes original `stop_utc`; exact same-M1 target/stop ties are not forced into an arbitrary ordering. Fixed-TP EV is resolved target-vs-stop only and remains **before spread, commission and slippage**.

| Symbol | n | +0.5R EV | +1R EV | +2R EV | +3R EV | +2R before BE after +1R* |
|---|---:|---:|---:|---:|---:|---:|
| BTCUSD | 499 | +0.007R | +0.046R | -0.002R | -0.125R | 52.9% |
| ETHUSD | 553 | -0.039R | -0.053R | -0.090R | -0.100R | 52.1% |
| DOGUSD | 595 | -0.115R | -0.106R | -0.170R | -0.272R | 48.3% |
| XAUUSD | 798 | +0.021R | -0.011R | -0.068R | -0.148R | 47.0% |
| USDJPY | 793 | -0.029R | -0.036R | -0.043R | -0.137R | 50.7% |

`*` Among +1R winners with non-ambiguous BE-after-1 path; probability is resolved +2R-before-BE vs BE-before-+2R.

These aggregate results contain no large universal edge and should **not** supersede the earlier 1.01 branch findings until the population/data mismatch is resolved.

## 6. Interesting branch observations inside the current 1.03 population

These are exploratory only because the crypto population provenance problem is unresolved.

Pooled 2024-2025 current 1.03:
- BTC SHORT: n=256, EV1 about +0.174R, EV2 about +0.192R, EV3 about +0.028R.
- XAU RETEST: n=417, EV1 about +0.104R, EV2 about +0.077R.
- DOG SHORT: n=275, EV1 about +0.076R, EV2 about +0.068R.
- ETH RETEST: n=296, EV1 about +0.031R, EV2 about -0.038R.

Year split warns against premature promotion:
- BTC SHORT is very strong in current 2024 sample (EV1 ~+0.279R, EV2 ~+0.364R) but much weaker in current 2025 (EV1 ~+0.020R, EV2 ~-0.077R).
- ETH RETEST is positive in current 2024 but negative in current 2025.
- XAU RETEST is positive in current 2024 but weaker/negative at 2R in current 2025.

## 7. Decision

- 1.03 virtual path instrumentation: **VALID**.
- Real-order/min-volume hypothesis as main cause of BTC/ETH low count: **REJECTED / INCOMPLETE**.
- Immediate missing-signal mechanism: **IDENTIFIED — collapsed/synthetic relative tick-volume history blocks CASCADE**.
- Current tester mode for these 1.03 runs: **CONFIRMED `Every tick`, not real-ticks mode**.
- Leading underlying cause: generated/modelled tick-volume provenance; **needs one real-ticks control run to confirm causality**.
- Current 1.03 BTC/ETH population equivalence to old 1.01: **NOT VALIDATED**.
- D025 V0 entry thresholds: **FROZEN**.
- Cost modeling: still pending; no production decision until spread + commission + slippage and stress-cost tests are applied to a reconciled signal population.

## 8. Next action — ONE CONTROL RUN ONLY

Run **BTCUSD only**, 2024-01-01 -> 2024-12-31, with the same 1.03 EA and inputs, but switch `Modelling` from `Every tick` to **`Every tick based on real ticks`**.

Do not run ETH/GBP/EUR/etc yet.

For that single control run, collect:
- events;
- trades;
- outcomes.

Key success check: August/September BTC relative-volume activity and total 2024 signal count. If real ticks restore substantial CASCADE activity and move the signal population toward the original 614, the provenance cause is confirmed. If not, investigate FundedNext historical feed/server availability next.