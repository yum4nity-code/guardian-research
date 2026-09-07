# Guardian Management Benchmark V2 — late-protection preregistration

Date: 2026-09-07 Europe/Paris
Status: **FROZEN EXPLORATORY CROSS-FAMILY BENCHMARK — SECOND PASS**

## Why V2 is separate from V1

Management Benchmark V1 was frozen and executed before its ranking was known. Its results are now seen evidence. V1 found that early fixed TP, narrow stop, early break-even and early 50% partial structures generally degraded the four parent families, while `BE_AFTER_2R` was approximately neutral/slightly positive across families.

Therefore V2 is deliberately a **new exploratory benchmark**, not an amendment to V1. Adding late-protection rules into V1 after seeing V1 would erase the audit trail between rules chosen before and after the first benchmark outcome.

V1 remains immutable historical evidence. V2 may use V1 only as hypothesis-generation context and can never be called independent confirmation.

## Scientific question

> When an entry has already earned substantial favorable excursion, can a small set of simple late-protection rules preserve more of the original strategy edge than the early-management rules tested in V1?

The aim is not to maximize one strategy. We again prefer cross-family robustness over pooled P/L.

## Frozen parent datasets

Exactly the same archived development datasets as V1:

- D038 — NR7 volatility-contraction breakout V0 — 459 rows;
- D039 — Inside-Day breakout V0 — 441 rows;
- D040 — NR4 volatility-contraction breakout V0 — 758 rows;
- D045 — D1 Donchian 20/10 benchmark V0 — 145 rows.

Total frozen rows: **1,803**.

D041/D032-M2 remains outside this generic benchmark because it uses a different paired-reference management-validation schema.

Parent strategy verdicts remain unchanged forever.

## Replay boundary

V2 uses only fields already persisted in the native Trade Path dataset:

- original gross/net R and commission R;
- MFE/MAE;
- milestone touches 0.5R/1R/2R/3R/5R;
- MAE before each favorable milestone;
- `min_r_after_first_1r_before_exit`;
- `min_r_after_first_2r_before_exit`;
- `min_r_after_first_3r_before_exit`;
- original exit;
- path ambiguity flag.

A hypothetical V2 rule may **never continue beyond the parent trade's original exit**.

Rows with `path_ambiguous=1` are excluded from alternate-management comparison.

## Frozen V2 catalogue

All R values use the parent trade's original initial-R denominator.

1. `BASELINE_ORIGINAL` — unchanged parent management.
2. `BE_AFTER_3R` — original lifecycle until +3R; after +3R, a recross to 0R exits at break-even proxy; otherwise original exit.
3. `LOCK1_AFTER_2R` — after +2R, protect +1R; if post-2R path reaches <=+1R, exit at +1R proxy; otherwise original exit.
4. `LOCK1_AFTER_3R` — after +3R, protect +1R; otherwise original exit.
5. `LOCK2_AFTER_3R` — after +3R, protect +2R; otherwise original exit.
6. `P25_AT_2R_REST_ORIGINAL` — close 25% at +2R; remaining 75% follows original exit.
7. `P25_AT_3R_REST_ORIGINAL` — close 25% at +3R; remaining 75% follows original exit.
8. `P25_AT_2R_LOCK1_REST` — close 25% at +2R; remaining 75% gets +1R floor after +2R.
9. `P25_AT_3R_LOCK2_REST` — close 25% at +3R; remaining 75% gets +2R floor after +3R.
10. `SL1_TP5` — original 1R stop, full exit at first +5R; if +5R is never reached, retain original exit unless the saved path proves the 1R stop threshold was reached first.

No other threshold may be inserted into V2 after results are seen.

## Why these rules

V2 intentionally samples **structures**, not a numerical grid:

- pure late BE (`BE_AFTER_3R`);
- late profit locking at roughly half/two-thirds of already-earned excursion (`LOCK1_AFTER_2R`, `LOCK1_AFTER_3R`, `LOCK2_AFTER_3R`);
- small partials rather than the V1 50% early partials;
- late partial + floor combinations;
- a very distant hard TP to test whether even a 5R cap truncates valuable tails.

There is no 2.5R rule because 2.5R is not a persisted canonical milestone. The current Guardian crypto 40% at 2.5R therefore requires an exact future harness, not interpolation.

## Rules deliberately NOT tested in V2 compact replay

The current dataset cannot safely reconstruct:

- H12/H24/H48 fixed time exits across all four families;
- continuous ATR/Chandelier/R trailing;
- exact 2.5R partials;
- wider-than-original stops;
- any exit that requires knowing the executable path after the parent's original exit.

Those require compressed per-bar path or dedicated MT5 replay and must be a later exact Exit Lab, not guessed from compact telemetry.

## Fill and cost boundary

As in V1, alternate exits are R-threshold proxies:

- a triggered floor/BE/TP assumes the stated R threshold;
- original exits retain actual saved `gross_r`;
- original round-turn `commission_r` is reused as a proxy;
- `net_r_proxy = gross_r_proxy - original_commission_r`;
- commission stress = `gross_r_proxy - 1.5 * original_commission_r`.

Partial exits therefore remain approximate, especially for crypto/metals where alternate exit notional changes commission. V2 is **not confirmation-grade P/L**.

## Frozen outputs and ranking

Per dataset/rule:

- input/eligible/excluded rows;
- mean/median/total gross-R proxy;
- mean/median/total net-R proxy;
- proxy PF and win rate;
- commission-stress proxy;
- mean and total net-R delta versus the same-row baseline;
- classification counts.

Cross-family ranking is the same lexicographic rule as V1:

1. more parent families improved;
2. higher worst-family mean delta R;
3. higher median-family mean delta R;
4. higher equal-family mean delta R;
5. higher pooled trade-weighted mean delta R;
6. stable rule name tie-breaker.

The largest dataset therefore cannot dominate the ranking merely by having more rows.

## Promotion boundary

V2 can only nominate candidate management structures for exact future replay. It cannot:

- change any D038/D039/D040/D045 verdict;
- confirm `BE_AFTER_2R` from V1;
- declare a production manager;
- justify parameter tuning on these same 1,803 seen trades.

If a V2 structure is materially broad and useful, the next scientific step is to freeze **at most one or two** candidates and test them with exact executable MT5/bar-path logic on fresh evidence.

## Canonical implementation

- `research/runner/management_benchmark_v2.py`
- `research/runner/management_benchmark_v2_offline.py`
- local output: `<workspace>/management_benchmarks/v2/<timestamp>/`
- isolated publication: `backtest-results/benchmarks/management-v2/live/`
- no MT5;
- no legacy AutoSync.
