# Guardian Management Benchmark V1 — preregistration

Date: 2026-09-07 Europe/Paris
Status: **FROZEN EXPLORATORY CROSS-FAMILY BENCHMARK**

## Purpose

Build one reusable, deterministic benchmark that applies the **same small catalogue of standard exit-management rules** to already-observed Guardian entry datasets.

The question is not “what management maximizes one strategy?” but:

> Which simple management rules behave reasonably across several unrelated entry families without depending on one dataset?

This benchmark is **exploratory only**. It cannot rescue, relabel, confirm, or reopen any parent experiment. Any rule selected from this benchmark is seen/tuned evidence and must later be frozen and tested on fresh untouched data with exact execution before production use.

## Frozen parent datasets for V1

Use the latest local `development/trades_compact.csv` produced by the validated rich scorer for:

- D038 — NR7 volatility-contraction breakout V0;
- D039 — Inside-Day breakout V0;
- D040 — NR4 volatility-contraction breakout V0;
- D045 — D1 Donchian 20/10 benchmark V0.

All four use native Guardian Trade Path telemetry and original-R denominators. Their parent verdicts remain unchanged forever.

D041/D032-M2 is **not** folded into this generic benchmark because its stored path/paired-reference schema is different and it already received a dedicated preregistered management validation.

Default benchmark stage: `development` only. D040 confirmation 2026 H1 is deliberately excluded from V1 so that stage sizes/windows remain more comparable and no confirmation sample dominates management discovery.

## Replay boundary

The current Trade Path contract stores milestone touches, MAE before favorable milestones, post-1R/2R/3R min/max, original exit and original costs. It does **not** store a complete executable bar/tick path after every trade.

Therefore V1 only tests rules that can be classified from the saved path without allowing a hypothetical trade to continue beyond its original exit.

V1 does **not** test:

- H12/H24/H48 exits across the four datasets;
- continuous ATR/R trailing stops;
- 2.5R partials (2.5R is not a canonical saved milestone);
- wider-than-original stops;
- any rule requiring path reconstruction after the parent trade already exited.

Those belong to a future V2 using compressed bar-path or a fresh exact MT5 harness.

## Frozen management catalogue

All R values use the **parent trade's original initial-R denominator**. No rule changes entries, symbols, direction, filters, signal population, or parent verdict.

1. `BASELINE_ORIGINAL` — unchanged parent management.
2. `SL1_TP0_5` — original 1R stop, full exit at first +0.5R.
3. `SL1_TP1` — original 1R stop, full exit at first +1R.
4. `SL1_TP2` — original 1R stop, full exit at first +2R.
5. `SL1_TP3` — original 1R stop, full exit at first +3R.
6. `SL0_5_TP1` — hypothetical -0.5R stop, full exit at +1R.
7. `SL0_5_TP2` — hypothetical -0.5R stop, full exit at +2R.
8. `BE_AFTER_1R` — original lifecycle until +1R; after +1R, a recross of 0R exits at BE proxy; otherwise original exit.
9. `BE_AFTER_2R` — same after +2R.
10. `P50_AT_1R_REST_ORIGINAL` — close 50% at +1R, remainder follows original exit.
11. `P50_AT_2R_REST_ORIGINAL` — close 50% at +2R, remainder follows original exit.
12. `P50_AT_1R_BE_REST` — at +1R close 50%; remaining 50% moves to BE proxy, otherwise follows original exit.

No alternative thresholds may be inserted into V1 after results are seen.

## Intrabar/path ordering

- Rows with `path_ambiguous=1` are excluded from alternate-management comparison.
- For a fixed TP and hypothetical narrow SL, `mae_before_<TP>` determines whether the narrow stop would have occurred before the favorable milestone.
- For BE, `min_r_after_first_<milestone>_before_exit <= 0` classifies a BE recross.
- A hypothetical rule may never continue beyond the original parent exit.

## Fill and cost limitation

Alternate exits are reconstructed in **R-space**, not from the exact historical executable fill tick:

- fixed TP/SL/BE exits assume the threshold R value;
- original exit uses the actual saved `gross_r`;
- baseline `commission_r` is reused as a round-turn cost proxy for the alternate full lifecycle;
- `net_r_proxy = gross_r_proxy - original_commission_r`;
- commission stress uses `gross_r_proxy - 1.5 * original_commission_r`.

For Forex this commission proxy is generally structurally closer because commission is lot-based. For crypto/metals alternate exit notional can slightly change commission; partial exits can also change exit-side notional. Therefore **all alternate net results are explicitly proxy/exploratory, not confirmation-grade P/L**.

## Frozen outputs

Per dataset and rule:

- eligible/excluded rows;
- mean/median/total gross-R proxy;
- mean/total net-R proxy;
- proxy Profit Factor and win rate;
- mean commission-stress R proxy;
- mean-net-R delta versus that dataset's original baseline;
- total-net-R delta versus baseline.

Cross-family per rule:

- families improved vs baseline;
- families degraded vs baseline;
- equal-family mean delta R (each parent gets equal weight);
- median family delta R;
- worst family delta R;
- best family delta R;
- pooled trade-weighted delta R;
- pooled mean net-R proxy.

## Frozen ranking

Alternate rules are ranked lexicographically, not with a fitted weighted score:

1. **more parent families improved**;
2. **higher worst-family mean delta R**;
3. **higher median-family mean delta R**;
4. **higher equal-family mean delta R**;
5. **higher pooled mean delta R**;
6. stable rule name as final deterministic tie-breaker.

This deliberately prevents the largest dataset from dominating the ranking.

The benchmark does **not** declare a production winner. Its top rows are only candidates for a future exact Exit Lab.

## Promotion boundary

After V1 results are seen:

- do not add thresholds to make a rule look better;
- do not alter parent entry strategies;
- select at most a small number of standard rules for exact replay;
- freeze the selected management before any fresh validation sample is opened;
- exact MT5 execution, realistic costs, swap/weekend policy where relevant, and fresh untouched/live-forward evidence remain mandatory before Guardian integration.

## Canonical implementation

- `research/runner/management_benchmark.py`
- local output: `<workspace>/management_benchmarks/v1/<timestamp>/`
- automatic isolated publication: `backtest-results/benchmarks/management-v1/live/`
- legacy AutoSync is never used.
