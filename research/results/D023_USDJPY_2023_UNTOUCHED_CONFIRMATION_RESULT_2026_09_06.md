# D023 USDJPY London ORB — untouched 2023 confirmation result — 2026-09-06

## Provenance

AutoSync v1.04 published run:

`backtests/inbox/2026/09/06/20260906_151852_D023_V108_USDJPY_c6c4489100ff`

Manifest validation:
- source: `D023_USDJPY_LondonORB_M15_v1_08_FUNDEDNEXT_2023_HARNESSFIX_20260906.mq5`
- source version: `1.08`
- symbol/timeframe: USDJPY / PERIOD_M15
- trades_closed = csv_trade_rows = published_trades_rows = 195
- FundedNext Stellar 1-Step/2-Step Forex commission = USD 5/lot/side

Frozen confirmation sample: 2023-01-02 through 2023-12-29.

## Frozen gates scored

Using `net_r` from the published CSV and the frozen 5-day circular moving-block bootstrap convention already present in repo (`seed=20260905`, `reps=5000`, `block_days=5`) on the zero-filled weekday series from 2023-01-02 through 2023-12-29:

| Gate | Threshold | Result | Pass? |
|---|---:|---:|---|
| Trade count | n >= 150 | **195** | PASS |
| Mean net R | > 0 | **-0.198176 R/trade** | FAIL |
| Net PF | >= 1.10 | **0.708428** | FAIL |
| 5-day block-bootstrap lower 5% bound of zero-filled weekday daily mean R | > 0 | **-0.268783 R/day** | FAIL |
| 1.5x commission stress total/mean | > 0 | **-44.512458 R total / -0.228269 R/trade** | FAIL |

Additional diagnostics:
- baseline total net R: **-38.644330 R**
- baseline daily mean on 260 zero-filled weekdays: **-0.148632 R/day**
- baseline win rate: **31.28%**
- baseline median net R: **-1.036306 R**
- baseline gross-profit R / gross-loss R: **93.893558 / 132.537888**
- 1.5x commission stress PF: **0.674614**

## Verdict

**REJECT / UNCONFIRMED — 1/5 frozen gates passed.**

This is not a borderline confirmation miss. The untouched 2023 sample is materially negative while the inspected FundedNext/DST-aware 2024-2026 clue was positive. Treat D023 USDJPY London ORB as regime-unstable / non-confirmed in its frozen form. Per preregistration: do not rescue with direction/day/EMA/RSI/ATR/news filters, do not remove SHORT, and do not tune on 2023.

Next safe action: close D023 as the current P0 alpha candidate, preserve it as evidence, and advance to the next preregistered independent strategy family rather than mining 2023 for a rescue.
