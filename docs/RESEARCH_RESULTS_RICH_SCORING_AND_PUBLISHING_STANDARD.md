# Guardian Research — Rich Scoring & Results Publishing Standard

Date: 2026-09-06
Status: REQUIRED NEXT ITERATION OF THE DETERMINISTIC RESEARCH RUNNER

## Purpose

Every valid research run should become a reusable research asset, not just a PASS/FAIL verdict.

The runner must keep two outputs strictly separate:

1. **Decision scoring** — frozen preregistered gates only. This alone decides REJECT / CANDIDATE_CONFIRM / CONFIRMED.
2. **Rich analytics** — descriptive data retained for future hypotheses, trade-path research and exit-management research. Rich analytics must never retroactively change the frozen verdict of the experiment that produced the data.

A rejected experiment may therefore remain scientifically useful as data, but it must not be rescued by post-hoc tuning on its opened sample.

## Required decision bundle

For every completed integrity-valid batch, preserve:

- experiment id and stage;
- source version and canonical source SHA256;
- EX5 SHA256;
- tester model and dates;
- exact symbols;
- batch receipt identity;
- per-run STATS/TRADES SHA256;
- frozen gate thresholds;
- measured gate values;
- boolean gate outcomes;
- final verdict;
- confirmation-opened flag;
- integrity-event count;
- cost model and stress multiplier.

Decision output should remain compact and immutable, e.g. `decision_score.json`.

## Required rich analytics

Where the available evidence supports them, compute and retain at least:

### Performance

- n trades;
- gross R and net R totals;
- mean, median and standard deviation of net R;
- net-R quantiles (p05, p25, p50, p75, p95);
- profit factor;
- win rate;
- average winner / average loser;
- payoff ratio;
- best / worst trade;
- cumulative-R max drawdown;
- longest winning / losing streak;
- commission R total and share of gross edge;
- commission-stress results.

### Stability

- per symbol;
- per year;
- per month;
- symbol x year matrix;
- positive/negative symbol count;
- positive/negative period count;
- contribution concentration;
- tail contribution: share of total R produced by top 1%, 5% and 10% trades.

Time-of-day and day-of-week breakdowns may be computed descriptively, but they are not permission to add filters to the originating experiment.

### Trade-path telemetry

Future strategy harnesses should emit sufficient path telemetry so the common dataset can calculate:

- MFE in R;
- MAE in R;
- maximum favorable/adverse price excursion;
- whether 0.5R / 1R / 2R / 3R / 5R were reached;
- first-hit ordering between adverse and favorable R levels;
- time to 0.5R / 1R / 2R / 3R / 5R;
- maximum adverse excursion before first reaching +1R / +2R / +3R;
- retracement from MFE before exit;
- excursion after each R milestone;
- trade duration;
- exit reason.

This telemetry is the input for the future **Trade Path Dataset** and **Exit Lab**. It must be analysis data, not an implicit optimization of the originating experiment.

D037 v1.02 does not currently contain all MFE/MAE/path fields. Its 2,377 validated DEV trade rows must be retained. A later deterministic path-enrichment process may reconstruct additional telemetry from trusted market data without changing the recorded D037 `REJECT_V0` verdict. Future harnesses should capture these fields natively where practical.

## GitHub publication target

Validated result bundles should be machine-published to the existing `backtest-results` branch.

Recommended layout:

`backtests/<experiment_id>/<stage>/<run_id>/`

Compact published files:

- `SUMMARY.md` — human-readable result;
- `decision_score.json` — frozen gates and verdict;
- `analytics.json` — rich descriptive metrics;
- `manifest.json` — provenance and hashes;
- `trades_compact.csv` — compact trade-level data when reasonably small;
- optional `trade_path_compact.csv` when path telemetry is available and compact.

Large raw tester logs, reports or event datasets remain on the research PC. Their path, SHA256 and byte size must be recorded in `manifest.json`.

## Publisher safety requirements

The publisher is part of the deterministic runner and is **not** legacy AutoSync.

It must:

- publish only evidence that has passed runner integrity validation;
- publish rejected as well as accepted experiments;
- preserve exact source/run/result hashes;
- be idempotent for the same run id and payload hash;
- never modify Guardian Core;
- never use legacy AutoSync v1/v2 as fallback;
- never alter the user's dirty working tree on the research branch;
- use an isolated checkout/worktree or equivalent isolated publish directory for `backtest-results`;
- fail closed on merge/push conflict rather than resetting the research checkout;
- never use `git reset --hard` on the user's active research working tree;
- record the resulting Git commit SHA in the local publish receipt.

## Ergonomic target

The normal end-of-experiment workflow should become:

`batch -> decision score -> rich analytics -> publish -> state update`

The user should not need to copy/paste CSV contents or manually upload result files to GitHub.

A future one-command form should be equivalent to:

`guardian-research finalize <experiment> --stage development`

where `finalize` consumes the already validated batch, produces decision + analytics bundles, publishes the compact result bundle to `backtest-results`, and updates local receipts. Opening confirmation remains a separate lifecycle decision and must not happen automatically.
