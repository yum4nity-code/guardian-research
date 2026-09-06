# D038 NR7 — DEV final rich closeout

Date: 2026-09-07 Europe/Paris
Status: **CLOSED — REJECT_V0 / REUSABLE PATH EVIDENCE RETAINED**

## Frozen decision

Experiment: `D038-NR7-VOLATILITY-CONTRACTION-BREAKOUT-V0`
Source SHA256: `e99bbe8817ed0e2c74c9aa757e8dbc5877fe0f2a5d7cd660112bf242cda79eb8`
EX5 SHA256: `32ecb804a722bf6d7c2959baecf0002a365abe1ef796e2e52397de0aa55422bd`
DEV batch: `20260906T225212Z`
Period: 2024-01-02 through 2025-12-31
Symbols: BTCUSD, ETHUSD, EURUSD, GBPUSD, USDJPY, XAUUSD

Frozen verdict: **REJECT_V0**.
Confirmation 2026 H1: **UNOPENED**.

Only failed DEV gate:
- aggregate n >= 480: **459 — FAIL**.

Passed gates:
- each symbol >= 50;
- aggregate mean net R >= +0.05;
- aggregate PF >= 1.10;
- >=4/6 positive symbols;
- 2024 positive;
- 2025 positive;
- commission-stress total positive;
- positive-symbol contribution concentration <=60%;
- zero integrity events.

Changing the count gate after seeing the result is forbidden. D038 V0 stays rejected.

## Decision metrics

- n: **459**
- mean net R: **+0.179491**
- total net R: **+82.3865R**
- PF: **1.5549**
- win rate: **49.24%**
- average winner: **+1.0215R**
- average loser: **-0.6372R**
- payoff ratio: **1.603**
- 1.5x commission stress: **+77.1874R**, PF ~**1.511**
- realized-close max drawdown: **20.3004R**
- recovery factor: **4.058**
- longest winning streak: **8**
- longest losing streak: **11**

## Symbol totals

- BTCUSD: +12.6989R
- ETHUSD: -7.6044R
- EURUSD: +30.7646R
- GBPUSD: +6.1077R
- USDJPY: +25.2397R
- XAUUSD: +15.1799R

Five of six symbols were positive.

## Time stability

2024:
- n=227
- +64.8838R
- mean +0.2858R
- PF ~1.9066

2025:
- n=232
- +17.5026R
- mean +0.07544R
- PF ~1.2276

The edge weakened materially in 2025 but remained positive in aggregate.

17 months were positive and 7 negative.

Persistent symbol observations, descriptive only:
- USDJPY positive in both years;
- XAUUSD positive in both years;
- EURUSD positive in both years, but 2024 contains a +24.55R outlier;
- ETHUSD negative in both years;
- BTCUSD positive in 2024 and slightly negative in 2025;
- GBPUSD positive in both years but near-flat in 2025.

No post-hoc symbol deletion is allowed inside D038.

## Fat-tail concentration

The strategy is materially dependent on rare large winners:
- top 1% = 5 trades = +42.0478R = **51.0%** of total net R;
- top 5% = 23 trades = +81.3996R = **98.8%** of total net R;
- top 10% = 46 trades = +119.8068R = **145.4%** of total net R.

This makes aggressive profit capping or premature trailing especially dangerous without separate validation.

## Native Trade Path

Path telemetry was integrity-clean: 459 path rows, zero path calculation failures, zero ambiguous rows.

MFE:
- all trades mean ~+0.915R, median ~+0.567R;
- winners mean ~+1.483R, median ~+1.173R;
- losers mean ~+0.363R, median ~+0.303R.

MAE:
- all trades mean ~0.535R, median ~0.503R;
- winners mean ~0.280R, median ~0.207R;
- losers mean ~0.782R, median ~0.845R.

Milestone touch rates:
- +0.5R: 250 / 459 = **54.47%**;
- +1R: 150 / 459 = **32.68%**;
- +2R: 40 / 459 = **8.71%**;
- +3R: 11 / 459 = **~2.40%**;
- +5R: 2 / 459 = **~0.44%**.

Among 233 losing trades:
- 44 (18.88%) had first touched +0.5R;
- 12 (5.15%) had first touched +1R;
- 1 (~0.43%) had first touched +2R;
- none reached +3R/+5R.

## D038 follow-up

D038 V0 itself is closed. Its evidence remains valid for transversal research.

One separate Exit Lab hypothesis has been locked:
`research/campaigns/D038_EXIT_LAB_E1_BE_AFTER_1R_2026_09_07.md`

E1 asks whether moving the protective stop to entry **only after first +1R** reduces giveback while preserving the rare fat-tail winners. This is a new management experiment and cannot rescue D038 V0.

## Published evidence

Final bundle:
`backtests/d038/development/20260906T225212Z` on branch `backtest-results`.

Finalize published commit:
`81ca497ae6cbd58403d6598ddf38dbde81e5215c`.

Corrected native-Trade-Path rich-score event:
`backtests/d038/live/events/development/rich-score/20260906T230626Z/`.

The complete rich score and compact path-aware trades are retained there for future Exit Lab and cross-strategy analysis.
